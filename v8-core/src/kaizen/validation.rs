//! V8 Kaizen Continuous Improvement Engine — Purged WFA & Atomic One-Shot Frozen OOS Gate.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §5 (Purged WFA & Atomic One-Shot Frozen OOS Burn)
//! - `HYPOTHESIS_LAB_PROTOCOL.md` §3–4 (Paired OOS delta vs simpler incumbent baseline)
//! - `V8_CONSTITUTION.md` Rule 5, 11, 15
//! - arXiv:2602.10785 (*Walk-Forward Optimization Window Selection, Trial Accounting, and Out-of-Sample Reliability*)

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use sha1::{Digest, Sha1};

use crate::evaluation::TradeRow;
use crate::kaizen::diagnosis::{ExpertId, VariantId};
use crate::state::fsum;

/// Time range representing start and end boundaries in nanoseconds.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TimeRange {
    pub start_ts_ns: i64,
    pub end_ts_ns: i64,
}

impl TimeRange {
    pub fn new(start_ts_ns: i64, end_ts_ns: i64) -> Self {
        Self {
            start_ts_ns,
            end_ts_ns,
        }
    }
}

/// Specification for a single purged walk-forward analysis fold.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WfaFoldSpec {
    pub fold_id: String,
    pub train_range: TimeRange,
    pub purge_range: TimeRange,
    pub test_range: TimeRange,
}

/// Specification for a multi-fold WFA campaign.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WfaCampaignSpec {
    pub campaign_id: String,
    pub base_expert_id: ExpertId,
    pub challenger_family_id: String,
    pub folds: Vec<WfaFoldSpec>,
    pub max_allowable_drawdown_r: f64,
    pub min_majority_ratio: f64,
}

/// Verdict for an individual WFA fold.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FoldVerdict {
    /// Paired delta is positive (U_challenger > U_baseline) and drawdown within allowable limit.
    Pass,
    /// Paired delta is non-positive (U_challenger <= U_baseline).
    FailNegativeDelta,
    /// Drawdown exceeded maximum allowable ceiling during the fold.
    FailCatastrophicDrawdown,
}

/// Evaluation receipt for a single WFA fold.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WfaFoldReceipt {
    pub fold_id: String,
    pub train_range: TimeRange,
    pub purge_range: TimeRange,
    pub test_range: TimeRange,
    pub chosen_variant: VariantId,
    pub baseline_utility: f64,
    pub challenger_utility: f64,
    pub paired_delta: f64,
    pub paired_uncertainty: f64,
    pub max_drawdown_r: f64,
    pub cost_drag_r: f64,
    pub verdict: FoldVerdict,
}

/// Campaign-level WFA verdict.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum WfaCampaignVerdict {
    /// Majority of folds passed with paired advantage and zero catastrophic drawdown events.
    PassMajorityFolds,
    /// Minority of folds passed with paired advantage.
    FailMinorityFolds,
    /// Immediate veto: at least one fold incurred catastrophic drawdown (Catastrophic Veto Rule).
    FailCatastrophicVeto,
}

/// Comprehensive campaign evaluation receipt.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WfaCampaignReceipt {
    pub campaign_id: String,
    pub total_folds: usize,
    pub passing_folds: usize,
    pub failing_folds: usize,
    pub mean_paired_delta: f64,
    pub fold_receipts: Vec<WfaFoldReceipt>,
    pub verdict: WfaCampaignVerdict,
}

/// Purged Walk-Forward Analysis evaluation engine.
pub struct PurgedWfaEngine;

impl PurgedWfaEngine {
    /// Computes max peak-to-trough drawdown in R units from an ordered trade series.
    pub fn compute_max_drawdown_r(trades: &[TradeRow]) -> f64 {
        if trades.is_empty() {
            return 0.0;
        }
        let mut peak = 0.0f64;
        let mut cum_pnl = 0.0f64;
        let mut max_dd = 0.0f64;

        for t in trades {
            cum_pnl += t.net_r;
            if cum_pnl > peak {
                peak = cum_pnl;
            }
            let dd = peak - cum_pnl;
            if dd > max_dd {
                max_dd = dd;
            }
        }
        max_dd
    }

    /// Evaluates a single WFA fold given baseline and challenger trade logs.
    pub fn evaluate_fold(
        fold_spec: &WfaFoldSpec,
        chosen_variant: &str,
        baseline_trades: &[TradeRow],
        challenger_trades: &[TradeRow],
        max_allowable_drawdown_r: f64,
    ) -> WfaFoldReceipt {
        let baseline_utility = if baseline_trades.is_empty() {
            0.0
        } else {
            fsum(&baseline_trades.iter().map(|t| t.net_r).collect::<Vec<_>>())
        };

        let challenger_utility = if challenger_trades.is_empty() {
            0.0
        } else {
            fsum(&challenger_trades.iter().map(|t| t.net_r).collect::<Vec<_>>())
        };

        let cost_drag_r = if challenger_trades.is_empty() {
            0.0
        } else {
            fsum(
                &challenger_trades
                    .iter()
                    .map(|t| t.fee_paid + t.slippage_paid + t.funding_paid)
                    .collect::<Vec<_>>(),
            )
        };

        let paired_delta = challenger_utility - baseline_utility;
        let max_drawdown_r = Self::compute_max_drawdown_r(challenger_trades);

        // Clustered standard error approximation
        let n = challenger_trades.len().max(1);
        let paired_uncertainty = (1.0 / (n as f64).sqrt()) * 0.1;

        let verdict = if max_drawdown_r > max_allowable_drawdown_r {
            FoldVerdict::FailCatastrophicDrawdown
        } else if paired_delta > 0.0 {
            FoldVerdict::Pass
        } else {
            FoldVerdict::FailNegativeDelta
        };

        WfaFoldReceipt {
            fold_id: fold_spec.fold_id.clone(),
            train_range: fold_spec.train_range.clone(),
            purge_range: fold_spec.purge_range.clone(),
            test_range: fold_spec.test_range.clone(),
            chosen_variant: chosen_variant.to_string(),
            baseline_utility,
            challenger_utility,
            paired_delta,
            paired_uncertainty,
            max_drawdown_r,
            cost_drag_r,
            verdict,
        }
    }

    /// Evaluates the complete multi-fold WFA campaign with catastrophic veto enforcement.
    pub fn evaluate_campaign(
        spec: &WfaCampaignSpec,
        fold_receipts: Vec<WfaFoldReceipt>,
    ) -> WfaCampaignReceipt {
        let total_folds = fold_receipts.len();
        let mut passing_folds = 0usize;
        let mut failing_folds = 0usize;
        let mut has_catastrophic_veto = false;
        let mut deltas = Vec::with_capacity(total_folds);

        for r in &fold_receipts {
            deltas.push(r.paired_delta);
            match r.verdict {
                FoldVerdict::Pass => passing_folds += 1,
                FoldVerdict::FailNegativeDelta => failing_folds += 1,
                FoldVerdict::FailCatastrophicDrawdown => {
                    failing_folds += 1;
                    has_catastrophic_veto = true;
                }
            }
        }

        let mean_paired_delta = if total_folds > 0 {
            fsum(&deltas) / total_folds as f64
        } else {
            0.0
        };

        let verdict = if has_catastrophic_veto {
            WfaCampaignVerdict::FailCatastrophicVeto
        } else if total_folds > 0 && (passing_folds as f64 / total_folds as f64) >= spec.min_majority_ratio {
            WfaCampaignVerdict::PassMajorityFolds
        } else {
            WfaCampaignVerdict::FailMinorityFolds
        };

        WfaCampaignReceipt {
            campaign_id: spec.campaign_id.clone(),
            total_folds,
            passing_folds,
            failing_folds,
            mean_paired_delta,
            fold_receipts,
            verdict,
        }
    }
}

// ---------------------------------------------------------------------------
// Atomic Dataset-Level Holdout Burning State Machine
// ---------------------------------------------------------------------------

/// State of a frozen out-of-sample dataset in the holdout registry.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum HoldoutState {
    /// Dataset is sealed and untouched.
    Untouched,
    /// Access is reserved and burned BEFORE data bytes are released.
    ReservedAndBurned,
    /// Evaluation completed successfully.
    Completed,
    /// Process aborted or crashed after burn reservation.
    FailedAfterBurn,
}

/// Access key uniquely identifying a holdout query.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct HoldoutAccessKey {
    pub holdout_id: String,
    pub dataset_hash: String,
    pub research_lineage_id: String,
}

/// Canonical holdout error types.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HoldoutError {
    AlreadyBurned {
        dataset_hash: String,
        state: HoldoutState,
    },
    DatasetNotFound(String),
    StateTransitionViolation(String),
    EvaluationFailed(String),
}

impl std::fmt::Display for HoldoutError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::AlreadyBurned {
                dataset_hash,
                state,
            } => {
                write!(
                    f,
                    "HOLDOUT_ALREADY_BURNED: dataset {dataset_hash} is in state {state:?}"
                )
            }
            Self::DatasetNotFound(hash) => write!(f, "DATASET_NOT_FOUND: {hash}"),
            Self::StateTransitionViolation(msg) => {
                write!(f, "STATE_TRANSITION_VIOLATION: {msg}")
            }
            Self::EvaluationFailed(msg) => write!(f, "EVALUATION_FAILED: {msg}"),
        }
    }
}

impl std::error::Error for HoldoutError {}

/// Immutable audit receipt produced upon reserving and evaluating a holdout.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HoldoutBurnReceipt {
    pub receipt_id: String,
    pub access_key: HoldoutAccessKey,
    pub reserved_ts_ns: i64,
    pub final_state: HoldoutState,
    pub audit_signature: String,
}

/// Global registry managing dataset-level holdout access and atomic burns.
///
/// Invariant I2 (Atomic Burn): Keyed strictly to physical dataset_hash, preventing bypasses
/// via newly generated experiment IDs or lineage IDs.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HoldoutBurnRegistry {
    pub dataset_states: HashMap<String, HoldoutState>,
    pub receipts: Vec<HoldoutBurnReceipt>,
}

impl HoldoutBurnRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers a dataset in the registry with `Untouched` state.
    pub fn register_dataset(&mut self, dataset_hash: &str) {
        self.dataset_states
            .entry(dataset_hash.to_string())
            .or_insert(HoldoutState::Untouched);
    }

    /// Retrieves the current holdout state of a dataset hash.
    pub fn get_state(&self, dataset_hash: &str) -> Option<HoldoutState> {
        self.dataset_states.get(dataset_hash).copied()
    }

    /// Atomically reserves a holdout, burns access, releases data to the evaluator,
    /// and transitions to final state.
    ///
    /// Ordering Invariant:
    /// Untouched -> ReservedAndBurned -> Evaluator -> Completed (or FailedAfterBurn)
    pub fn reserve_and_evaluate<F, R>(
        &mut self,
        access_key: HoldoutAccessKey,
        now_ns: i64,
        evaluator: F,
    ) -> Result<(R, HoldoutBurnReceipt), HoldoutError>
    where
        F: FnOnce() -> Result<R, String>,
    {
        let current_state = self
            .dataset_states
            .get(&access_key.dataset_hash)
            .copied()
            .unwrap_or(HoldoutState::Untouched);

        // Fail-closed check: Any state other than Untouched is strictly rejected (Invariant I2)
        if current_state != HoldoutState::Untouched {
            return Err(HoldoutError::AlreadyBurned {
                dataset_hash: access_key.dataset_hash.clone(),
                state: current_state,
            });
        }

        // 1. Atomic State Transition: Untouched -> ReservedAndBurned BEFORE releasing bytes
        self.dataset_states
            .insert(access_key.dataset_hash.clone(), HoldoutState::ReservedAndBurned);

        // 2. Execute evaluation
        let eval_result = evaluator();

        // 3. Transition to final state based on result
        let final_state = match &eval_result {
            Ok(_) => HoldoutState::Completed,
            Err(_) => HoldoutState::FailedAfterBurn,
        };
        self.dataset_states
            .insert(access_key.dataset_hash.clone(), final_state);

        // Generate cryptographic audit signature
        let mut hasher = Sha1::new();
        hasher.update(access_key.holdout_id.as_bytes());
        hasher.update(access_key.dataset_hash.as_bytes());
        hasher.update(access_key.research_lineage_id.as_bytes());
        hasher.update(now_ns.to_le_bytes());
        hasher.update(format!("{final_state:?}").as_bytes());
        let digest = hasher.finalize();
        let audit_signature: String = digest.iter().map(|b| format!("{:02x}", b)).collect();

        let receipt = HoldoutBurnReceipt {
            receipt_id: format!("burn_rcpt_{}", &audit_signature[..12]),
            access_key: access_key.clone(),
            reserved_ts_ns: now_ns,
            final_state,
            audit_signature,
        };

        self.receipts.push(receipt.clone());

        match eval_result {
            Ok(output) => Ok((output, receipt)),
            Err(err_msg) => Err(HoldoutError::EvaluationFailed(err_msg)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dummy_trade(net_r: f64) -> TradeRow {
        TradeRow {
            trade_id: "t_dummy".to_string(),
            candidate_id: "c_dummy".to_string(),
            symbol: "BTCUSDT".to_string(),
            expert_id: "bollinger_breakout".to_string(),
            direction: "LONG".to_string(),
            entry_ts_ns: 1_700_000_000_000,
            exit_ts_ns: 1_700_000_100_000,
            entry_price: 50_000.0,
            exit_price: 51_000.0,
            gross_r: net_r + 0.1,
            net_r,
            fee_paid: 0.05,
            slippage_paid: 0.03,
            funding_paid: 0.02,
            exit_reason: "TAKE_PROFIT".to_string(),
            duration_bars: 10,
            mfe_r: 1.0,
            mae_r: -0.1,
        }
    }

    #[test]
    fn test_paired_delta_wfa_majority_pass() {
        let mut folds = Vec::new();
        let mut receipts = Vec::new();

        for i in 0..5 {
            let fold_spec = WfaFoldSpec {
                fold_id: format!("fold_{i}"),
                train_range: TimeRange::new(0, 100),
                purge_range: TimeRange::new(100, 110),
                test_range: TimeRange::new(110, 200),
            };
            folds.push(fold_spec.clone());

            // Challenger beats baseline in 4 out of 5 folds
            let baseline_net = 0.5;
            let challenger_net = if i == 0 { 0.2 } else { 1.2 };

            let b_trades = vec![dummy_trade(baseline_net)];
            let c_trades = vec![dummy_trade(challenger_net)];

            let receipt = PurgedWfaEngine::evaluate_fold(
                &fold_spec,
                "challenger_v2",
                &b_trades,
                &c_trades,
                3.0, // max allowable dd
            );
            receipts.push(receipt);
        }

        let campaign_spec = WfaCampaignSpec {
            campaign_id: "wfa_bb_test".to_string(),
            base_expert_id: "bollinger_breakout".to_string(),
            challenger_family_id: "family_v2".to_string(),
            folds,
            max_allowable_drawdown_r: 3.0,
            min_majority_ratio: 0.60,
        };

        let campaign_receipt = PurgedWfaEngine::evaluate_campaign(&campaign_spec, receipts);
        assert_eq!(campaign_receipt.passing_folds, 4);
        assert_eq!(campaign_receipt.failing_folds, 1);
        assert_eq!(
            campaign_receipt.verdict,
            WfaCampaignVerdict::PassMajorityFolds
        );
    }

    #[test]
    fn test_catastrophic_veto_overrides_majority_pass() {
        let mut folds = Vec::new();
        let mut receipts = Vec::new();

        for i in 0..5 {
            let fold_spec = WfaFoldSpec {
                fold_id: format!("fold_{i}"),
                train_range: TimeRange::new(0, 100),
                purge_range: TimeRange::new(100, 110),
                test_range: TimeRange::new(110, 200),
            };
            folds.push(fold_spec.clone());

            // In fold 4, challenger incurs catastrophic drawdown (-4.0R > max allowable 3.0R)
            let (b_net, c_trades) = if i == 4 {
                (0.5, vec![dummy_trade(-4.5), dummy_trade(1.0)])
            } else {
                (0.5, vec![dummy_trade(1.5)])
            };

            let b_trades = vec![dummy_trade(b_net)];
            let receipt = PurgedWfaEngine::evaluate_fold(
                &fold_spec,
                "challenger_v2",
                &b_trades,
                &c_trades,
                3.0, // max allowable dd ceiling
            );
            receipts.push(receipt);
        }

        let campaign_spec = WfaCampaignSpec {
            campaign_id: "wfa_veto_test".to_string(),
            base_expert_id: "bollinger_breakout".to_string(),
            challenger_family_id: "family_v2".to_string(),
            folds,
            max_allowable_drawdown_r: 3.0,
            min_majority_ratio: 0.60,
        };

        let campaign_receipt = PurgedWfaEngine::evaluate_campaign(&campaign_spec, receipts);
        // Even though 4/5 folds had positive paired delta, catastrophic drawdown triggers immediate veto
        assert_eq!(
            campaign_receipt.verdict,
            WfaCampaignVerdict::FailCatastrophicVeto
        );
    }

    #[test]
    fn test_atomic_holdout_burn_rejects_secondary_access() {
        let mut registry = HoldoutBurnRegistry::new();
        let dataset_hash = "dataset_btc_oos_frozen_hash_12345";
        registry.register_dataset(dataset_hash);

        let access_key_1 = HoldoutAccessKey {
            holdout_id: "oos_2025_q1".to_string(),
            dataset_hash: dataset_hash.to_string(),
            research_lineage_id: "lineage_exp_001".to_string(),
        };

        // First access succeeds and burns the holdout
        let (eval_score, receipt) = registry
            .reserve_and_evaluate(access_key_1, 1_700_000_000, || Ok(0.85f64))
            .expect("First reservation must succeed");

        assert_eq!(eval_score, 0.85);
        assert_eq!(receipt.final_state, HoldoutState::Completed);
        assert_eq!(
            registry.get_state(dataset_hash),
            Some(HoldoutState::Completed)
        );

        // Attempting secondary access with a DIFFERENT experiment/lineage ID must fail closed
        let access_key_2 = HoldoutAccessKey {
            holdout_id: "oos_2025_q1".to_string(),
            dataset_hash: dataset_hash.to_string(),
            research_lineage_id: "bypass_attempt_exp_999".to_string(),
        };

        let err = registry
            .reserve_and_evaluate(access_key_2, 1_700_000_100, || Ok(0.99f64))
            .expect_err("Secondary query must be fail-closed rejected");

        match err {
            HoldoutError::AlreadyBurned {
                dataset_hash: h,
                state,
            } => {
                assert_eq!(h, dataset_hash);
                assert_eq!(state, HoldoutState::Completed);
            }
            other => panic!("Expected AlreadyBurned error, got {:?}", other),
        }
    }

    #[test]
    fn test_crash_resilience_cannot_reopen_failed_after_burn() {
        let mut registry = HoldoutBurnRegistry::new();
        let dataset_hash = "dataset_eth_oos_frozen_hash_67890";
        registry.register_dataset(dataset_hash);

        let access_key = HoldoutAccessKey {
            holdout_id: "oos_2025_eth".to_string(),
            dataset_hash: dataset_hash.to_string(),
            research_lineage_id: "lineage_crash_test".to_string(),
        };

        // Evaluation crashes/fails mid-flight
        let err = registry
            .reserve_and_evaluate(access_key.clone(), 1_700_000_000, || -> Result<f64, String> {
                Err("Runtime panic during evaluation".to_string())
            })
            .expect_err("Evaluation failure expected");

        match err {
            HoldoutError::EvaluationFailed(_) => (),
            other => panic!("Expected EvaluationFailed, got {:?}", other),
        }

        assert_eq!(
            registry.get_state(dataset_hash),
            Some(HoldoutState::FailedAfterBurn)
        );

        // Secondary attempt cannot reopen dataset even though previous evaluation failed
        let second_err = registry
            .reserve_and_evaluate(access_key, 1_700_000_200, || Ok(1.0f64))
            .expect_err("FailedAfterBurn cannot be reopened");

        match second_err {
            HoldoutError::AlreadyBurned { state, .. } => {
                assert_eq!(state, HoldoutState::FailedAfterBurn);
            }
            other => panic!("Expected AlreadyBurned, got {:?}", other),
        }
    }
}
