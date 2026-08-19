//! V8 Kaizen Continuous Improvement Engine — Dual-Counter Research Accounting & Lineage Ledger.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §3.2 (Dual-Counter Research Accounting)
//! - `EVALUATION_EVIDENCE_SYSTEM.md` §2
//! - arXiv:2606.01650 (*Post-Selection Inference, Covariance Lineage, and Overfitting Penalties in Quantitative Strategy Search*)

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

use crate::kaizen::diagnosis::VariantId;

/// Single registered trial entry in the global research debt ledger.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrialEntry {
    pub trial_id: String,
    pub family_id: String,
    pub variant_id: VariantId,
    pub variant_hash: String,
    pub dataset_lineage: String,
    pub parameter_lineage: HashMap<String, f64>,
    pub selection_lineage: Vec<String>,
    pub return_series_covariance_ref: Option<String>,
    pub research_choice_id: u64,
    pub evaluation_attempts: u64,
}

/// Global trial ledger managing lifetime research debt and candidate lineage.
///
/// Invariants:
/// - I1: Observation != Change (Ledger is purely observational/accounting, cannot mutate live strategies).
/// - I2: Idempotent Debt under Replay: Rerunning an existing variant hash increments evaluation attempts
///   without inflating the research choice counter (D-046, arXiv:2606.01650).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GlobalTrialLedger {
    pub entries: Vec<TrialEntry>,
    /// Index into `entries` keyed by `variant_hash`.
    pub variant_to_entry_idx: HashMap<String, usize>,
    pub total_research_choices: u64,
    pub total_evaluation_attempts: u64,
}

impl GlobalTrialLedger {
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers or updates a trial execution.
    ///
    /// If `variant_hash` has not been seen before, increments `total_research_choices` (+1)
    /// and `total_evaluation_attempts` (+1).
    /// If `variant_hash` has already been registered, increments ONLY `total_evaluation_attempts` (+1),
    /// leaving `total_research_choices` unchanged (Idempotent Debt Invariant I2).
    pub fn record_trial(
        &mut self,
        family_id: &str,
        variant_id: &str,
        variant_hash: &str,
        dataset_lineage: &str,
        parameter_lineage: HashMap<String, f64>,
        selection_lineage: Vec<String>,
        covariance_ref: Option<&str>,
    ) -> &TrialEntry {
        if let Some(&idx) = self.variant_to_entry_idx.get(variant_hash) {
            // Replay / Deterministic CI execution: idempotent research debt
            self.entries[idx].evaluation_attempts += 1;
            self.total_evaluation_attempts += 1;
            &self.entries[idx]
        } else {
            // New research choice: increments research debt counter
            self.total_research_choices += 1;
            self.total_evaluation_attempts += 1;

            let trial_id = format!("trial_{:08}", self.total_research_choices);
            let entry = TrialEntry {
                trial_id,
                family_id: family_id.to_string(),
                variant_id: variant_id.to_string(),
                variant_hash: variant_hash.to_string(),
                dataset_lineage: dataset_lineage.to_string(),
                parameter_lineage,
                selection_lineage,
                return_series_covariance_ref: covariance_ref.map(str::to_string),
                research_choice_id: self.total_research_choices,
                evaluation_attempts: 1,
            };

            let idx = self.entries.len();
            self.entries.push(entry);
            self.variant_to_entry_idx.insert(variant_hash.to_string(), idx);
            &self.entries[idx]
        }
    }

    /// Retrieves an entry by variant hash.
    pub fn get_by_hash(&self, variant_hash: &str) -> Option<&TrialEntry> {
        self.variant_to_entry_idx
            .get(variant_hash)
            .and_then(|&idx| self.entries.get(idx))
    }

    /// Returns the active multiplicity penalty factor based on total research choices.
    pub fn research_choice_count(&self) -> u64 {
        self.total_research_choices
    }

    /// Returns total evaluation executions (including CI replays).
    pub fn evaluation_attempt_count(&self) -> u64 {
        self.total_evaluation_attempts
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kaizen::challenger::{ChallengerFamilySpec, DiscreteParameterRange};
    use crate::kaizen::diagnosis::{
        EvidenceValidity, FailureTag, ForensicAssessment, ReplicationStatus,
    };
    use crate::kaizen::hypothesis::{FalsificationRule, FindingGenerator, HypothesisGenerator};

    #[test]
    fn test_forensic_assessment_to_hypothesis_record_zero_mutation() {
        let assessment = ForensicAssessment {
            expert_id: "bollinger_breakout".to_string(),
            variant_id: "v1".to_string(),
            tags: vec![FailureTag::CostDominated],
            validity: EvidenceValidity::Valid,
            replication_status: ReplicationStatus::PendingInvestigation,
            gross_r: 1.2,
            fee_r: 0.8,
            slippage_r: 0.3,
            funding_r: 0.2,
            net_r: -0.1,
            regime_breakdown: vec![],
        };

        let findings = FindingGenerator::from_assessment(&assessment, 1_700_000_000);
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].primary_failure_tag, FailureTag::CostDominated);

        let param = DiscreteParameterRange::new("min_atr_mult", vec![1.0, 1.5, 2.0])
            .expect("Valid range");
        let challenger_spec = ChallengerFamilySpec::new(
            "bb_cost_filter",
            "bollinger_breakout",
            "v1",
            "Add ATR volatility filter to reduce churn in chop",
            vec![param],
        )
        .expect("Valid challenger spec");

        let rule = FalsificationRule::new("delta_net_r", 0.15, Some(0.20), Some(0.60))
            .expect("Valid rule");

        let hypothesis = HypothesisGenerator::generate(
            &findings[0],
            "Filter entries when ATR < threshold to avoid fee drag",
            rule,
            &challenger_spec,
            1_700_000_000,
        )
        .expect("Valid hypothesis record");

        assert_eq!(hypothesis.expert_id, "bollinger_breakout");
        assert_eq!(hypothesis.challenger_family_id, "bb_cost_filter");
        assert_eq!(hypothesis.falsification_rule.metric_target, "delta_net_r");
        assert_eq!(hypothesis.falsification_rule.threshold, 0.15);
    }

    #[test]
    fn test_dual_counter_research_accounting_idempotence() {
        let mut ledger = GlobalTrialLedger::new();

        // 1. Evaluate 10 distinct variants -> 10 research choices, 10 eval attempts
        for i in 0..10 {
            let mut params = HashMap::new();
            params.insert("threshold".to_string(), i as f64);
            let var_hash = format!("hash_distinct_{i}");
            ledger.record_trial(
                "family_1",
                &format!("var_{i}"),
                &var_hash,
                "dataset_btc_2024",
                params,
                vec!["selection_step_1".to_string()],
                Some("cov_ref_001"),
            );
        }

        assert_eq!(ledger.research_choice_count(), 10);
        assert_eq!(ledger.evaluation_attempt_count(), 10);

        // 2. Rerun the SAME variant 5 times in CI -> evaluation attempts increases by 5,
        // while research choices remains 10 (Invariant I2)
        let mut replay_params = HashMap::new();
        replay_params.insert("threshold".to_string(), 0.0);
        for _ in 0..5 {
            ledger.record_trial(
                "family_1",
                "var_0",
                "hash_distinct_0",
                "dataset_btc_2024",
                replay_params.clone(),
                vec!["selection_step_1".to_string()],
                Some("cov_ref_001"),
            );
        }

        assert_eq!(ledger.research_choice_count(), 10);
        assert_eq!(ledger.evaluation_attempt_count(), 15);

        let entry_0 = ledger.get_by_hash("hash_distinct_0").expect("Found");
        assert_eq!(entry_0.evaluation_attempts, 6); // 1 initial + 5 replays
        assert_eq!(entry_0.research_choice_id, 1);
    }

    #[test]
    fn test_ledger_stores_covariance_and_lineage() {
        let mut ledger = GlobalTrialLedger::new();
        let mut params = HashMap::new();
        params.insert("stop_loss_mult".to_string(), 2.5);
        params.insert("take_profit_mult".to_string(), 4.0);

        let entry = ledger.record_trial(
            "family_breakout",
            "var_sl25_tp40",
            "hash_abc_123",
            "dataset_hash_deadbeef",
            params.clone(),
            vec!["parent_v1".to_string(), "pruned_by_sharpe".to_string()],
            Some("covariance_matrix_ref_789"),
        );

        assert_eq!(entry.family_id, "family_breakout");
        assert_eq!(entry.dataset_lineage, "dataset_hash_deadbeef");
        assert_eq!(entry.parameter_lineage, params);
        assert_eq!(
            entry.selection_lineage,
            vec!["parent_v1".to_string(), "pruned_by_sharpe".to_string()]
        );
        assert_eq!(
            entry.return_series_covariance_ref,
            Some("covariance_matrix_ref_789".to_string())
        );
    }
}
