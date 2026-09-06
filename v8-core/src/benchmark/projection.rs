//! CapitalOutcomeProjection & Firewall Boundary (D-153 §89–94, Rule 57.6).
//!
//! Enforces:
//! - Diagnostic View Only: Benchmark scores NEVER emit readiness claims.
//! - Non-realized PnL Protection: CapitalOutcomeProjection produces counterfactual
//!   outcome distributions, explicitly marked as NOT realized PnL.
//! - Rejects forward economic claims if statistical credibility or sample size is insufficient.
//! - Rejects synthetic-only populations as probability weights (BFS-004).
//! - Rejects unmodeled large capacity scaling (BFS-018).
//! - Suppresses underpowered quantiles on small dependent samples (BFS-022).
//! - 10,000 Monte Carlo bootstrap future paths ($1,000 baseline) with Risk of Ruin %.

use serde::{Deserialize, Serialize};
use rayon::prelude::*;
use crate::benchmark::receipt::BenchmarkReceipt;
use crate::benchmark::types::ProjectionGrade;
use crate::mt19937::MT19937;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProjectedOutcomeBand {
    pub percentile: f64,
    pub return_bps: f64,
    pub max_drawdown_bps: f64,
    pub terminal_capital_usd: f64,
}

/// 10,000 Monte Carlo / Bootstrap Simulated Futures Profile
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MonteCarloFutureResult {
    pub n_simulations: usize,
    pub horizon_trades: usize,
    pub initial_capital_usd: f64,
    pub p5_terminal_usd: f64,
    pub p5_return_pct: f64,
    pub p25_terminal_usd: f64,
    pub p25_return_pct: f64,
    pub p50_terminal_usd: f64,
    pub p50_return_pct: f64,
    pub p75_terminal_usd: f64,
    pub p75_return_pct: f64,
    pub p95_terminal_usd: f64,
    pub p95_return_pct: f64,
    pub risk_of_ruin_pct: f64, // Probability of equity <= 70% of initial capital (30% drawdown)
    pub worst_scenario_return_pct: f64,
    pub best_scenario_return_pct: f64,
    pub conditional_notice: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CapitalOutcomeProjection {
    pub policy_id: String,
    pub benchmark_receipt_id: String,
    pub is_realized_pnl: bool, // MUST ALWAYS BE FALSE (Rule 12, Rule 30)
    pub initial_capital_usd: f64,
    pub projection_grade: ProjectionGrade,
    pub sample_size: usize,
    pub outcome_bands: Vec<ProjectedOutcomeBand>,
    pub epistemic_status: String,
    pub forward_claim_authorized: bool, // FALSE for diagnostic/synthetic
    pub monte_carlo_futures: Option<MonteCarloFutureResult>,
}

impl CapitalOutcomeProjection {
    /// Projects empirical counterfactual outcomes from physical trade returns.
    ///
    /// Derives quantiles purely from the passed evaluated return series.
    /// Zero hardcoded metrics permitted (Constitution Rule 5).
    pub fn project_from_returns(
        receipt: &BenchmarkReceipt,
        trade_returns_bps: &[f64],
        initial_capital_usd: f64,
        has_synthetic_population_only: bool,
    ) -> Result<Self, String> {
        // Enforce credibility floor
        if receipt.composite_capability_score < 0.20 {
            return Err("Cannot project outcome: composite capability score is below minimum credibility floor (0.20)".into());
        }

        // BFS-004: Synthetic frequency cannot be used as future probability
        if has_synthetic_population_only {
            return Err("Projection rejected: synthetic populations cannot be used as probability weights for forward capital claims (BFS-004)".into());
        }

        // BFS-018: Reject large capital scaling without an audited capacity model
        if initial_capital_usd > 100_000.0 {
            return Err(format!(
                "Projection scope rejected: capital scale ${:.0} exceeds baseline without liquidity capacity model (BFS-018)",
                initial_capital_usd
            ));
        }

        let n = trade_returns_bps.len();
        if n < 5 {
            return Err("Insufficient trade sample size for capital projection (minimum 5 trades required)".into());
        }

        // BFS-022: P95 from tiny sample (<25 trades) must be suppressed or flagged
        let suppress_extreme_quantiles = n < 25;

        // Sort returns to compute empirical quantiles
        let mut sorted = trade_returns_bps.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let percentiles = if suppress_extreme_quantiles {
            vec![0.25, 0.50, 0.75]
        } else {
            vec![0.05, 0.25, 0.50, 0.75, 0.95]
        };

        // Compute cumulative drawdown profile from the supplied series.
        let mut running_equity = initial_capital_usd;
        let mut peak_equity = initial_capital_usd;
        let mut max_dd_bps = 0.0;

        for &ret_bps in trade_returns_bps {
            let pnl = running_equity * (ret_bps / 10_000.0);
            running_equity += pnl;
            if running_equity > peak_equity {
                peak_equity = running_equity;
            }
            let dd_bps = if peak_equity > 0.0 {
                ((peak_equity - running_equity) / peak_equity) * 10_000.0
            } else {
                0.0
            };
            if dd_bps > max_dd_bps {
                max_dd_bps = dd_bps;
            }
        }

        let mut outcome_bands = Vec::new();
        for &p in &percentiles {
            let idx = (((n as f64 - 1.0) * p).round() as usize).min(n - 1);
            let ret_bps = sorted[idx];
            let terminal = initial_capital_usd * (1.0 + (ret_bps / 10_000.0));
            outcome_bands.push(ProjectedOutcomeBand {
                percentile: p,
                return_bps: ret_bps,
                max_drawdown_bps: max_dd_bps,
                terminal_capital_usd: terminal,
            });
        }

        let allows_claim = receipt.projection_grade.allows_forward_probability();
        let epistemic_status = if allows_claim {
            format!("Empirically certified projection grade {:?}", receipt.projection_grade)
        } else {
            "DIAGNOSTIC_ONLY: counterfactual scenario projection with zero economic promotion authority".to_string()
        };

        // Run 10,000 Monte Carlo bootstrap future paths (if sample size is adequate)
        let mc_futures = if !suppress_extreme_quantiles {
            Some(Self::simulate_monte_carlo_futures(
                trade_returns_bps,
                initial_capital_usd,
                10_000,
                n.min(252),
                42,
            )?)
        } else {
            None
        };

        Ok(Self {
            policy_id: receipt.policy_id.clone(),
            benchmark_receipt_id: receipt.receipt_id.clone(),
            is_realized_pnl: false, // Invariant: projection is strictly counterfactual!
            initial_capital_usd,
            projection_grade: receipt.projection_grade,
            sample_size: n,
            outcome_bands,
            epistemic_status,
            forward_claim_authorized: allows_claim,
            monte_carlo_futures: mc_futures,
        })
    }

    /// Simulates 10,000 future paths using deterministic MT19937 bootstrap sampling.
    ///
    /// Computes terminal capital percentiles (P5, P25, P50, P75, P95) and Risk of Ruin %
    /// (probability of equity falling to <= 70% of initial capital).
    pub fn simulate_monte_carlo_futures(
        trade_returns_bps: &[f64],
        initial_capital_usd: f64,
        n_simulations: usize,
        horizon_trades: usize,
        seed: u64,
    ) -> Result<MonteCarloFutureResult, String> {
        if trade_returns_bps.is_empty()
            || trade_returns_bps.iter().any(|value| !value.is_finite())
        {
            return Err("DATA_BLOCKED_MISSING_OR_INVALID_TRADE_RETURNS".to_string());
        }
        if !initial_capital_usd.is_finite() || initial_capital_usd <= 0.0 {
            return Err("BLOCKED_INVALID_INITIAL_CAPITAL".to_string());
        }
        if n_simulations == 0 || horizon_trades == 0 {
            return Err("BLOCKED_INVALID_MONTE_CARLO_DIMENSIONS".to_string());
        }
        let n_trades = trade_returns_bps.len();
        let ruin_threshold = initial_capital_usd * 0.70; // 30% drawdown

        // Parallel Monte Carlo simulation across scenarios with deterministic per-simulation seed.
        // Seed mixing uses splitmix64 constant for independent, reproducible streams per scenario.
        let results: Vec<(f64, bool)> = (0..n_simulations)
            .into_par_iter()
            .map(|sim_idx| {
                let sim_seed = seed
                    .wrapping_add((sim_idx as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15))
                    .wrapping_add(1);
                let mut rng = MT19937::new(sim_seed);
                let mut equity = initial_capital_usd;
                let mut breached_ruin = false;

                for _ in 0..horizon_trades {
                    let idx = rng.randbelow(n_trades as u64) as usize;
                    let ret_bps = trade_returns_bps[idx];
                    equity += equity * (ret_bps / 10_000.0);
                    if equity <= ruin_threshold {
                        breached_ruin = true;
                    }
                }

                (equity, breached_ruin)
            })
            .collect();

        let mut ruin_count = 0usize;
        let mut terminal_equities = Vec::with_capacity(n_simulations);
        for (equity, breached_ruin) in results {
            if breached_ruin {
                ruin_count += 1;
            }
            terminal_equities.push(equity);
        }

        terminal_equities.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let quant = |p: f64| -> f64 {
            let idx = (((n_simulations as f64 - 1.0) * p).round() as usize).min(n_simulations - 1);
            terminal_equities[idx]
        };

        let ret_pct = |terminal: f64| -> f64 {
            ((terminal - initial_capital_usd) / initial_capital_usd) * 100.0
        };

        let p5 = quant(0.05);
        let p25 = quant(0.25);
        let p50 = quant(0.50);
        let p75 = quant(0.75);
        let p95 = quant(0.95);
        let worst = terminal_equities.first().copied().unwrap_or(initial_capital_usd);
        let best = terminal_equities.last().copied().unwrap_or(initial_capital_usd);

        let risk_of_ruin = (ruin_count as f64 / n_simulations as f64) * 100.0;

        Ok(MonteCarloFutureResult {
            n_simulations,
            horizon_trades,
            initial_capital_usd,
            p5_terminal_usd: p5,
            p5_return_pct: ret_pct(p5),
            p25_terminal_usd: p25,
            p25_return_pct: ret_pct(p25),
            p50_terminal_usd: p50,
            p50_return_pct: ret_pct(p50),
            p75_terminal_usd: p75,
            p75_return_pct: ret_pct(p75),
            p95_terminal_usd: p95,
            p95_return_pct: ret_pct(p95),
            risk_of_ruin_pct: risk_of_ruin,
            worst_scenario_return_pct: ret_pct(worst),
            best_scenario_return_pct: ret_pct(best),
            conditional_notice: "Conditional historical projection, NOT future profit guarantee. Liquidity capacity capped at $100k.".into(),
        })
    }

    /// Backwards compatible helper for existing receipt-based projection checks
    pub fn project_from_receipt(
        _receipt: &BenchmarkReceipt,
        _confidence_level: f64,
    ) -> Result<Self, String> {
        Err("DATA_BLOCKED_NO_VERIFIED_TRADE_RETURN_ARTIFACT".to_string())
    }
}
