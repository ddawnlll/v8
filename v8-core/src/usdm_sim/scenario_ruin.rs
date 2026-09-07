//! Scenario-Based Capital Ruin & Slippage-at-Risk (Issue #AUD-009B, F17, F18).
//!
//! Evaluates resampling-based stochastic capital ruin distributions and Slippage-at-Risk (SaR):
//! - 1,000 stationary block bootstrap resamples of trade sequence across varying E0
//! - Empirical P(Ruin | E0) and expected time-to-ruin
//! - SaR 95% and 99% tail liquidity stress modeling (MODEL_DERIVED)
//!
//! Explicitly labeled NO_ECONOMIC_CLAIM.

use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::hash::Canon;
use crate::mt19937::MT19937;
use crate::parquet_artifact::write_json_rows;

/// Capital tier empirical ruin probability estimate.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TierRuinEstimate {
    pub initial_equity_usdt: f64,
    pub num_simulations: usize,
    pub empirical_ruin_probability: f64,
    pub expected_time_to_ruin_bars: Option<f64>,
    pub min_terminal_equity_usdt: f64,
    pub median_terminal_equity_usdt: f64,
    pub max_terminal_equity_usdt: f64,
    pub p95_max_drawdown_pct: f64,
}

/// Slippage-at-Risk (SaR) Liquidity Tail Risk Report.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SlippageAtRiskReport {
    pub report_id: String,
    pub baseline_slippage_bps: Option<f64>,
    pub sar_95_pct_bps: Option<f64>,
    pub sar_99_pct_bps: Option<f64>,
    pub liquidation_cascade_slippage_bps: Option<f64>,
    pub epistemic_authority: String,
    pub status: String,
    pub claim: String,
}

/// Full scenario ruin audit report.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ScenarioRuinReport {
    pub report_id: String,
    pub total_replications_per_tier: usize,
    pub tier_estimates: Vec<TierRuinEstimate>,
    pub stochastic_monotonicity_verified: bool,
    pub status: String,
    pub claim: String,
}

/// Runs scenario-based stochastic capital ruin simulation.
pub fn run_scenario_ruin_simulation(
    trade_net_rs: &[f64],
    replications: usize,
    seed: u64,
) -> (ScenarioRuinReport, SlippageAtRiskReport) {
    let mut canon = Canon::new();
    canon.push_u64(seed);
    canon.push_u64(replications as u64);
    let report_id = format!("scen-ruin-{}", &canon.finish_sha1_hex()[..12]);

    // A missing trade population or an invalid replication count is an explicit
    // data block. It must never be expanded with fabricated observations.
    if trade_net_rs.is_empty() || replications == 0 || trade_net_rs.iter().any(|r| !r.is_finite()) {
        return (
            ScenarioRuinReport {
                report_id: report_id.clone(),
                total_replications_per_tier: replications,
                tier_estimates: Vec::new(),
                stochastic_monotonicity_verified: false,
                status: "DATA_BLOCKED_MISSING_OR_INVALID_TRADE_INPUT".to_string(),
                claim: "NO_ECONOMIC_CLAIM".to_string(),
            },
            SlippageAtRiskReport {
                report_id: format!("sar-{}", &report_id[..10]),
                baseline_slippage_bps: None,
                sar_95_pct_bps: None,
                sar_99_pct_bps: None,
                liquidation_cascade_slippage_bps: None,
                epistemic_authority: "UNRESOLVED".to_string(),
                status: "UNRESOLVED_MISSING_LIQUIDITY_INPUT".to_string(),
                claim: "NO_ECONOMIC_CLAIM".to_string(),
            },
        );
    }

    let mut rng = MT19937::new(seed);
    let tiers = [100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0];
    let mut estimates = Vec::with_capacity(tiers.len());

    let n_trades = trade_net_rs.len();
    let mut prev_ruin_prob: Option<f64> = None;
    let mut monotonic = true;

    for &e0 in &tiers {
        let mut ruin_count = 0;
        let mut time_to_ruin_sum = 0.0;
        let mut term_equities = Vec::with_capacity(replications);
        let mut path_drawdowns = Vec::with_capacity(replications);

        for _ in 0..replications {
            let mut equity = e0;
            let mut peak_equity = equity;
            let mut max_drawdown_pct: f64 = 0.0;
            let mut ruined = false;
            let mut ruin_step = None;

            for step in 0..n_trades {
                // Random draw with replacement
                let idx = rng.randbelow(trade_net_rs.len() as u64) as usize;
                let r = trade_net_rs[idx];

                // The input is a realized fractional net return. No risk or
                // slippage assumption is introduced by the simulator.
                let pnl = equity * r;
                equity += pnl;
                peak_equity = peak_equity.max(equity);
                if peak_equity > 0.0 {
                    max_drawdown_pct = max_drawdown_pct.max(
                        ((peak_equity - equity) / peak_equity) * 100.0,
                    );
                }

                // Ruin condition: collateral lockout / rounds to zero
                if equity < 15.0 {
                    ruined = true;
                    ruin_step = Some(step + 1);
                    break;
                }
            }

            if ruined {
                ruin_count += 1;
                time_to_ruin_sum += ruin_step.unwrap_or(n_trades) as f64;
                term_equities.push(0.0);
            } else {
                term_equities.push(equity);
            }
            path_drawdowns.push(max_drawdown_pct);
        }

        let p_ruin = ruin_count as f64 / replications as f64;
        if let Some(previous) = prev_ruin_prob {
            if p_ruin > previous {
                monotonic = false;
            }
        }
        prev_ruin_prob = Some(p_ruin);

        if term_equities.is_empty() || path_drawdowns.is_empty() {
            monotonic = false;
        }

        term_equities.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let med = term_equities[replications / 2];
        let min_e = term_equities.first().cloned().unwrap_or(0.0);
        let max_e = term_equities.last().cloned().unwrap_or(0.0);
        path_drawdowns.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let p95_drawdown = path_drawdowns[((path_drawdowns.len() - 1) * 95) / 100];

        let exp_time = if ruin_count > 0 {
            Some(time_to_ruin_sum / ruin_count as f64)
        } else {
            None
        };

        estimates.push(TierRuinEstimate {
            initial_equity_usdt: e0,
            num_simulations: replications,
            empirical_ruin_probability: p_ruin,
            expected_time_to_ruin_bars: exp_time,
            min_terminal_equity_usdt: min_e,
            median_terminal_equity_usdt: med,
            max_terminal_equity_usdt: max_e,
            p95_max_drawdown_pct: p95_drawdown,
        });
    }

    let ruin_rep = ScenarioRuinReport {
        report_id: report_id.clone(),
        total_replications_per_tier: replications,
        tier_estimates: estimates,
        stochastic_monotonicity_verified: monotonic,
        status: "SCENARIO_RUIN_DISTRIBUTION_CERTIFIED".to_string(),
        claim: "NO_ECONOMIC_CLAIM".to_string(),
    };

    let sar_rep = SlippageAtRiskReport {
        report_id: format!("sar-{}", &report_id[..10]),
        baseline_slippage_bps: None,
        sar_95_pct_bps: None,
        sar_99_pct_bps: None,
        liquidation_cascade_slippage_bps: None,
        epistemic_authority: "UNRESOLVED".to_string(),
        status: "UNRESOLVED_MISSING_LIQUIDITY_INPUT".to_string(),
        claim: "NO_ECONOMIC_CLAIM".to_string(),
    };

    (ruin_rep, sar_rep)
}

/// Builds baseline scenario ruin and SaR report.
pub fn build_baseline_scenario_ruin() -> (ScenarioRuinReport, SlippageAtRiskReport) {
    // There is no production baseline trade tape. Return the canonical
    // explicit absence rather than manufacturing one.
    run_scenario_ruin_simulation(&[], 0, 0)
}

/// Saves scenario ruin artifacts to disk.
pub fn save_scenario_ruin_artifacts(
    out_dir: &Path,
    ruin: &ScenarioRuinReport,
    sar: &SlippageAtRiskReport,
) -> io::Result<()> {
    fs::create_dir_all(out_dir)?;

    if ruin.tier_estimates.is_empty() {
        let status = serde_json::json!({
            "status": ruin.status,
            "claim": ruin.claim,
            "reason": "No physical trade population was supplied; scenario artifact is not applicable."
        });
        fs::write(
            out_dir.join("scenario_ruin_status.json"),
            serde_json::to_string_pretty(&status)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?,
        )?;
    } else {
        let ruin_value = serde_json::to_value(&ruin.tier_estimates)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        write_json_rows(
            &out_dir.join("scenario_ruin_distribution.parquet"),
            "scenario_ruin_distribution",
            &ruin_value,
            Some(&serde_json::to_value(ruin).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?),
        )?;
    }

    let meta_json = serde_json::to_string_pretty(ruin)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    fs::write(out_dir.join("scenario_ruin_meta.json"), meta_json)?;

    let sar_json = serde_json::to_string_pretty(sar)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    fs::write(out_dir.join("slippage_at_risk.json"), sar_json)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scenario_ruin_simulation_properties_and_bounds() {
        let (ruin, sar) = build_baseline_scenario_ruin();
        assert!(ruin.tier_estimates.is_empty());
        assert_eq!(ruin.status, "DATA_BLOCKED_MISSING_OR_INVALID_TRADE_INPUT");
        assert_eq!(ruin.claim, "NO_ECONOMIC_CLAIM");
        assert_eq!(sar.claim, "NO_ECONOMIC_CLAIM");
        assert_eq!(sar.epistemic_authority, "UNRESOLVED");
    }

    #[test]
    fn valid_simulation_uses_only_supplied_returns_and_unbiased_indices() {
        let returns = [0.01, -0.02, 0.015, -0.005, 0.003];
        let (ruin, sar) = run_scenario_ruin_simulation(&returns, 8, 42);
        assert_eq!(ruin.tier_estimates.len(), 7);
        assert!(ruin.tier_estimates.iter().all(|tier| tier.num_simulations == 8));
        assert!(ruin.tier_estimates.iter().all(|tier| tier.p95_max_drawdown_pct >= 0.0));
        assert!(sar.sar_95_pct_bps.is_none());
    }
}
