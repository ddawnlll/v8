//! V8 Kaizen Continuous Improvement Engine — Forensic Attribution & Multi-Tag Failure Taxonomy.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §2.1–2.2
//! - `HYPOTHESIS_LAB_PROTOCOL.md` §1–4
//! - `EVALUATION_EVIDENCE_SYSTEM.md` §1–4
//! - `LEARNING_PROTOCOL.md` §1–4
//! - arXiv:2603.29086 (*Execution Cost Realism and Algorithmic Ranking Invariance*)

use serde::{Deserialize, Serialize};

use crate::evaluation::TradeRow;
use crate::mt19937::MT19937;
use crate::state::fsum;

pub type ExpertId = String;
pub type VariantId = String;

/// Failure tags in the Kaizen multi-tag failure taxonomy.
///
/// Failure tags are not mutually exclusive (Invariant I1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FailureTag {
    /// Empirical sample gross return is negative (signal / directional underperformance).
    ObservedGrossNegative,
    /// Gross return is positive, but net return is non-positive due to friction (fees, slippage, funding).
    CostDominated,
    /// Performance collapses under parameter perturbation or high sensitivity.
    ParameterFragile,
    /// Performance collapses in specific market regimes (e.g. chop, high volatility).
    RegimeFragile,
}

/// Validity classification of the empirical evidence.
///
/// Separates data / attribution validity from economic strategy evaluation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum EvidenceValidity {
    /// Evidence meets all coverage, effective sample size, and attribution requirements.
    Valid,
    /// Population divergence or insufficient execution share violates attribution safety (D-027).
    AttributionUnsafe {
        execution_share: f64,
        population_divergence_p: f64,
    },
    /// Event count or effective independent episode count is below the preregistered threshold.
    InsufficientEvidence {
        observed_events: u64,
        effective_episodes: f64,
    },
}

/// Replication readiness status for a diagnosed expert variant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ReplicationStatus {
    /// Valid evidence with viable gross/net economics, ready for OOS / WFA replication.
    CandidateForReplication,
    /// Valid evidence showing fatal failure (e.g. gross negative return or cost unviability).
    Unviable,
    /// Validity gate failed or ambiguous evidence requires further data / investigation.
    PendingInvestigation,
}

/// Regime-specific forensic breakdown.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RegimeForensics {
    pub regime_name: String,
    pub observed_events: u64,
    pub effective_episodes: f64,
    pub gross_r: f64,
    pub fee_r: f64,
    pub slippage_r: f64,
    pub funding_r: f64,
    pub net_r: f64,
    pub is_fragile: bool,
    pub tags: Vec<FailureTag>,
}

/// Full forensic diagnostic assessment of an expert variant.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ForensicAssessment {
    pub expert_id: ExpertId,
    pub variant_id: VariantId,
    pub tags: Vec<FailureTag>,
    pub validity: EvidenceValidity,
    pub replication_status: ReplicationStatus,
    pub gross_r: f64,
    pub fee_r: f64,
    pub slippage_r: f64,
    pub funding_r: f64,
    pub net_r: f64,
    pub regime_breakdown: Vec<RegimeForensics>,
}

/// Dependence-aware evidence requirements.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceRequirement {
    pub min_events: u64,
    pub min_effective_episodes: f64,
    pub dependence_unit: String,
    pub min_execution_share: f64,
    pub max_divergence_p: f64,
}

impl Default for EvidenceRequirement {
    fn default() -> Self {
        Self {
            min_events: 30,
            min_effective_episodes: 8.0,
            dependence_unit: "session".to_string(),
            min_execution_share: 0.20,
            max_divergence_p: 0.05,
        }
    }
}

/// Canonical forensic error types.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ForensicsError {
    IncompleteTelemetry(String),
    InvalidInput(String),
}

impl std::fmt::Display for ForensicsError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::IncompleteTelemetry(msg) => write!(f, "INCOMPLETE_TELEMETRY: {msg}"),
            Self::InvalidInput(msg) => write!(f, "INVALID_INPUT: {msg}"),
        }
    }
}

impl std::error::Error for ForensicsError {}

/// Forensic analysis engine.
pub struct ExpertForensics;

impl ExpertForensics {
    /// Computes effective independent episodes given event count and max hold bars (METH-4).
    pub fn compute_effective_episodes(n_events: u64, max_hold_bars: u64) -> f64 {
        if max_hold_bars == 0 || n_events == 0 {
            0.0
        } else {
            n_events as f64 / max_hold_bars as f64
        }
    }

    /// Computes population divergence p-value between executed and rejected trade net returns.
    ///
    /// Uses a seeded permutation difference test (MT19937).
    pub fn compute_population_divergence_p(
        executed_net_r: &[f64],
        rejected_net_r: &[f64],
        seed: u64,
    ) -> f64 {
        let n_exec = executed_net_r.len();
        let n_rej = rejected_net_r.len();
        if n_exec == 0 || n_rej == 0 {
            return 1.0;
        }

        let mean_exec = fsum(executed_net_r) / n_exec as f64;
        let mean_rej = fsum(rejected_net_r) / n_rej as f64;
        let observed_diff = (mean_exec - mean_rej).abs();

        let mut combined = Vec::with_capacity(n_exec + n_rej);
        combined.extend_from_slice(executed_net_r);
        combined.extend_from_slice(rejected_net_r);

        let total_n = combined.len();
        let n_permutations = 1000u64;
        let mut rng = MT19937::new(seed);
        let mut exceed = 0u64;

        for _ in 0..n_permutations {
            let perm = rng.sample(total_n as u64);
            let mut sample_exec_sum = 0.0;
            let mut sample_rej_sum = 0.0;
            for (idx, &p_idx) in perm.iter().enumerate() {
                let val = combined[p_idx as usize];
                if idx < n_exec {
                    sample_exec_sum += val;
                } else {
                    sample_rej_sum += val;
                }
            }
            let diff = ((sample_exec_sum / n_exec as f64) - (sample_rej_sum / n_rej as f64)).abs();
            if diff >= observed_diff {
                exceed += 1;
            }
        }

        exceed as f64 / n_permutations as f64
    }

    /// Evaluates forensics on an expert variant given its executed trades, capacity rejections,
    /// regime slices, and parameter sensitivity.
    pub fn assess(
        expert_id: &str,
        variant_id: &str,
        executed_trades: &[TradeRow],
        portfolio_rejected_count: u64,
        rejected_net_r: Option<&[f64]>,
        regimes: &[(&str, &[TradeRow])],
        parameter_fragile: bool,
        max_hold_bars: u64,
        req: &EvidenceRequirement,
    ) -> Result<ForensicAssessment, ForensicsError> {
        if max_hold_bars == 0 {
            return Err(ForensicsError::InvalidInput(
                "max_hold_bars must be positive".to_string(),
            ));
        }

        // Validate trade records for incomplete telemetry (NaN/infinity/missing IDs)
        for t in executed_trades {
            if t.trade_id.is_empty()
                || t.gross_r.is_nan()
                || t.gross_r.is_infinite()
                || t.net_r.is_nan()
                || t.net_r.is_infinite()
                || t.fee_paid.is_nan()
                || t.slippage_paid.is_nan()
                || t.funding_paid.is_nan()
            {
                return Err(ForensicsError::IncompleteTelemetry(format!(
                    "Trade {} has corrupted or incomplete telemetry",
                    t.trade_id
                )));
            }
        }

        let n_events = executed_trades.len() as u64;
        let effective_episodes = Self::compute_effective_episodes(n_events, max_hold_bars);

        let gross_r = if n_events > 0 {
            fsum(&executed_trades.iter().map(|t| t.gross_r).collect::<Vec<_>>())
        } else {
            0.0
        };
        let fee_r = if n_events > 0 {
            fsum(&executed_trades.iter().map(|t| t.fee_paid).collect::<Vec<_>>())
        } else {
            0.0
        };
        let slippage_r = if n_events > 0 {
            fsum(&executed_trades.iter().map(|t| t.slippage_paid).collect::<Vec<_>>())
        } else {
            0.0
        };
        let funding_r = if n_events > 0 {
            fsum(&executed_trades.iter().map(|t| t.funding_paid).collect::<Vec<_>>())
        } else {
            0.0
        };
        let net_r = if n_events > 0 {
            fsum(&executed_trades.iter().map(|t| t.net_r).collect::<Vec<_>>())
        } else {
            0.0
        };

        // 1. Evidence Validity Evaluation
        let total_candidate_events = n_events + portfolio_rejected_count;
        let execution_share = if total_candidate_events > 0 {
            n_events as f64 / total_candidate_events as f64
        } else {
            0.0
        };

        let exec_net_series: Vec<f64> = executed_trades.iter().map(|t| t.net_r).collect();
        let divergence_p = match rejected_net_r {
            Some(rej) if !rej.is_empty() && !exec_net_series.is_empty() => {
                Self::compute_population_divergence_p(&exec_net_series, rej, 42)
            }
            _ => 1.0,
        };

        let is_attribution_unsafe = (total_candidate_events > 0
            && execution_share < req.min_execution_share)
            || (rejected_net_r.is_some()
                && !rejected_net_r.unwrap().is_empty()
                && divergence_p < req.max_divergence_p);

        let validity = if is_attribution_unsafe {
            EvidenceValidity::AttributionUnsafe {
                execution_share,
                population_divergence_p: divergence_p,
            }
        } else if n_events < req.min_events || effective_episodes < req.min_effective_episodes {
            EvidenceValidity::InsufficientEvidence {
                observed_events: n_events,
                effective_episodes,
            }
        } else {
            EvidenceValidity::Valid
        };

        // 2. Regime Breakdown
        let mut regime_breakdown = Vec::new();
        let mut any_regime_fragile = false;

        for (r_name, r_trades) in regimes {
            let r_n = r_trades.len() as u64;
            let r_eff = Self::compute_effective_episodes(r_n, max_hold_bars);
            let r_gross = fsum(&r_trades.iter().map(|t| t.gross_r).collect::<Vec<_>>());
            let r_fee = fsum(&r_trades.iter().map(|t| t.fee_paid).collect::<Vec<_>>());
            let r_slip = fsum(&r_trades.iter().map(|t| t.slippage_paid).collect::<Vec<_>>());
            let r_fund = fsum(&r_trades.iter().map(|t| t.funding_paid).collect::<Vec<_>>());
            let r_net = fsum(&r_trades.iter().map(|t| t.net_r).collect::<Vec<_>>());

            let mut r_tags = Vec::new();
            if r_gross < 0.0 {
                r_tags.push(FailureTag::ObservedGrossNegative);
            }
            if r_gross > 0.0 && r_net <= 0.0 {
                r_tags.push(FailureTag::CostDominated);
            }

            // Regime is fragile if it incurs significant losses while aggregate is otherwise active
            let is_fragile = r_net < 0.0 || (r_gross <= 0.0 && r_n > 0);
            if is_fragile {
                r_tags.push(FailureTag::RegimeFragile);
                any_regime_fragile = true;
            }

            regime_breakdown.push(RegimeForensics {
                regime_name: r_name.to_string(),
                observed_events: r_n,
                effective_episodes: r_eff,
                gross_r: r_gross,
                fee_r: r_fee,
                slippage_r: r_slip,
                funding_r: r_fund,
                net_r: r_net,
                is_fragile,
                tags: r_tags,
            });
        }

        // 3. Strategy Failure Tag Assignment (Multi-label)
        let mut tags = Vec::new();
        if gross_r < 0.0 {
            tags.push(FailureTag::ObservedGrossNegative);
        }
        if gross_r > 0.0 && net_r <= 0.0 {
            tags.push(FailureTag::CostDominated);
        }
        if parameter_fragile {
            tags.push(FailureTag::ParameterFragile);
        }
        if any_regime_fragile {
            tags.push(FailureTag::RegimeFragile);
        }

        // 4. Replication Status (Invariant I2: Validity != Valid => ReplicationStatus != CandidateForReplication)
        let replication_status = match validity {
            EvidenceValidity::InsufficientEvidence { .. } => ReplicationStatus::PendingInvestigation,
            EvidenceValidity::AttributionUnsafe { .. } => ReplicationStatus::PendingInvestigation,
            EvidenceValidity::Valid => {
                if tags.contains(&FailureTag::ObservedGrossNegative) || net_r <= 0.0 {
                    ReplicationStatus::Unviable
                } else if tags.is_empty() && net_r > 0.0 {
                    ReplicationStatus::CandidateForReplication
                } else if net_r > 0.0 && !tags.contains(&FailureTag::ObservedGrossNegative) {
                    // Has gross positive edge, but flagged for regime or parameter fragility
                    ReplicationStatus::PendingInvestigation
                } else {
                    ReplicationStatus::Unviable
                }
            }
        };

        // Check invariant I2 explicitly
        if validity != EvidenceValidity::Valid {
            debug_assert_ne!(replication_status, ReplicationStatus::CandidateForReplication);
        }

        Ok(ForensicAssessment {
            expert_id: expert_id.to_string(),
            variant_id: variant_id.to_string(),
            tags,
            validity,
            replication_status,
            gross_r,
            fee_r,
            slippage_r,
            funding_r,
            net_r,
            regime_breakdown,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dummy_trade(
        id: &str,
        gross_r: f64,
        net_r: f64,
        fee: f64,
        slippage: f64,
        funding: f64,
    ) -> TradeRow {
        TradeRow {
            trade_id: id.to_string(),
            candidate_id: format!("c_{id}"),
            symbol: "BTCUSDT".to_string(),
            expert_id: "bollinger_breakout".to_string(),
            direction: "LONG".to_string(),
            entry_ts_ns: 1_700_000_000_000,
            exit_ts_ns: 1_700_000_100_000,
            entry_price: 50_000.0,
            exit_price: 51_000.0,
            gross_r,
            net_r,
            fee_paid: fee,
            slippage_paid: slippage,
            funding_paid: funding,
            exit_reason: "TAKE_PROFIT".to_string(),
            duration_bars: 10,
            mfe_r: 1.5,
            mae_r: -0.2,
        }
    }

    #[test]
    fn test_multi_label_capability() {
        // Expert with gross > 0, net < 0 (CostDominated), regime collapse in chop (RegimeFragile),
        // and high parameter sensitivity (ParameterFragile) simultaneously receives all three tags.
        let mut trades = Vec::new();
        for i in 0..40 {
            trades.push(dummy_trade(
                &format!("t_{i}"),
                0.5,   // gross_r > 0
                -0.1,  // net_r < 0
                0.3,   // fee
                0.2,   // slippage
                0.1,   // funding
            ));
        }

        let chop_trades = vec![dummy_trade("chop_1", -0.5, -0.9, 0.2, 0.1, 0.1)];
        let trend_trades = vec![dummy_trade("trend_1", 1.5, 1.0, 0.2, 0.1, 0.2)];
        let regimes = vec![
            ("chop", chop_trades.as_slice()),
            ("trend", trend_trades.as_slice()),
        ];

        let req = EvidenceRequirement::default();
        let assessment = ExpertForensics::assess(
            "exp_1",
            "var_1",
            &trades,
            0,
            None,
            &regimes,
            true, // parameter_fragile
            2,    // max_hold_bars
            &req,
        )
        .expect("Assessment should succeed");

        assert!(assessment.tags.contains(&FailureTag::CostDominated));
        assert!(assessment.tags.contains(&FailureTag::RegimeFragile));
        assert!(assessment.tags.contains(&FailureTag::ParameterFragile));
        assert!(!assessment.tags.contains(&FailureTag::ObservedGrossNegative));
        assert_eq!(assessment.validity, EvidenceValidity::Valid);
    }

    #[test]
    fn test_attribution_unsafe_validity_gate_fires_on_divergence() {
        // Divergence between executed and rejected population
        let mut exec_trades = Vec::new();
        for i in 0..40 {
            exec_trades.push(dummy_trade(&format!("e_{i}"), 1.0, 0.8, 0.1, 0.05, 0.05));
        }

        // Rejected population is wildly different (all heavily negative)
        let rejected_net_r: Vec<f64> = (0..40).map(|_| -2.5).collect();

        let req = EvidenceRequirement {
            min_events: 30,
            min_effective_episodes: 5.0,
            dependence_unit: "session".to_string(),
            min_execution_share: 0.20,
            max_divergence_p: 0.05,
        };

        let assessment = ExpertForensics::assess(
            "exp_1",
            "var_1",
            &exec_trades,
            10,
            Some(&rejected_net_r),
            &[],
            false,
            2,
            &req,
        )
        .expect("Assessment should succeed");

        match assessment.validity {
            EvidenceValidity::AttributionUnsafe {
                population_divergence_p,
                ..
            } => {
                assert!(population_divergence_p < 0.05);
            }
            other => panic!("Expected AttributionUnsafe, got {:?}", other),
        }

        // AttributionUnsafe does NOT falsely tag signal logic as ObservedGrossNegative
        assert!(!assessment.tags.contains(&FailureTag::ObservedGrossNegative));
        assert_eq!(assessment.replication_status, ReplicationStatus::PendingInvestigation);
    }

    #[test]
    fn test_insufficient_evidence_triggers_pending_investigation() {
        // Too few events (5 trades when 30 required)
        let mut trades = Vec::new();
        for i in 0..5 {
            trades.push(dummy_trade(&format!("t_{i}"), 1.0, 0.8, 0.1, 0.05, 0.05));
        }

        let req = EvidenceRequirement {
            min_events: 30,
            min_effective_episodes: 8.0,
            dependence_unit: "session".to_string(),
            min_execution_share: 0.20,
            max_divergence_p: 0.05,
        };

        let assessment = ExpertForensics::assess(
            "exp_1",
            "var_1",
            &trades,
            0,
            None,
            &[],
            false,
            2,
            &req,
        )
        .expect("Assessment should succeed");

        match assessment.validity {
            EvidenceValidity::InsufficientEvidence { observed_events, .. } => {
                assert_eq!(observed_events, 5);
            }
            other => panic!("Expected InsufficientEvidence, got {:?}", other),
        }

        assert_eq!(assessment.replication_status, ReplicationStatus::PendingInvestigation);
    }

    #[test]
    fn test_incomplete_telemetry_fails_closed() {
        let mut trades = vec![dummy_trade("t_1", 1.0, 0.8, 0.1, 0.05, 0.05)];
        trades[0].gross_r = f64::NAN;

        let req = EvidenceRequirement::default();
        let err = ExpertForensics::assess(
            "exp_1",
            "var_1",
            &trades,
            0,
            None,
            &[],
            false,
            2,
            &req,
        )
        .expect_err("NaN telemetry must fail closed");

        match err {
            ForensicsError::IncompleteTelemetry(_) => (),
            other => panic!("Expected IncompleteTelemetry error, got {:?}", other),
        }
    }
}
