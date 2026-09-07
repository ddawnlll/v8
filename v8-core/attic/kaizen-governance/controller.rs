//! Kaizen Sovereign Controller (D-132, Rule 33, PH2-003A.3).
//!
//! Central sovereign controller managing hypothesis generation, research debt,
//! execution simulation coordination, independent audit verification, and final verdict issuance.

use serde::{Deserialize, Serialize};
use crate::claims::ClaimRegistry;
use super::research_debt::GlobalTrialLedger;
use super::verdict::{KaizenVerdict, KaizenVerdictEngine};

/// Kaizen Sovereign Controller Configuration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KaizenControllerConfig {
    pub max_research_debt_trials: usize,
    pub min_regimes_for_supported_edge: usize,
    pub strict_double_entry_enforcement: bool,
}

impl Default for KaizenControllerConfig {
    fn default() -> Self {
        Self {
            max_research_debt_trials: 100_000,
            min_regimes_for_supported_edge: 3,
            strict_double_entry_enforcement: true,
        }
    }
}

/// The Sovereign Kaizen Controller.
#[derive(Debug)]
pub struct KaizenController {
    pub config: KaizenControllerConfig,
    pub trial_ledger: GlobalTrialLedger,
    pub claim_registry: ClaimRegistry,
}

impl KaizenController {
    pub fn new(config: KaizenControllerConfig) -> Self {
        Self {
            config,
            trial_ledger: GlobalTrialLedger::new(),
            claim_registry: ClaimRegistry::new(),
        }
    }

    /// Evaluates a research hypothesis submission and issues an authoritative claim record.
    pub fn process_hypothesis_evaluation(
        &mut self,
        hypothesis_id: &str,
        dsr_pvalue: f64,
        spa_pvalue: f64,
        wrc_pvalue: f64,
        regimes_tested: usize,
        has_cashflow_reconciliation: bool,
        zero_synthetic_certified: bool,
        measured_edge_bps: f64,
        implementer_receipt: &str,
        auditor_receipt: &str,
        timestamp_utc: i64,
    ) -> Result<(KaizenVerdict, String), String> {
        let verdict = KaizenVerdictEngine::evaluate_verdict(
            dsr_pvalue,
            spa_pvalue,
            wrc_pvalue,
            regimes_tested,
            has_cashflow_reconciliation,
            zero_synthetic_certified,
        );

        let claim = KaizenVerdictEngine::issue_verdict_claim(
            &mut self.claim_registry,
            &verdict,
            measured_edge_bps,
            "bps",
            vec![format!("hyp_{hypothesis_id}")],
            implementer_receipt,
            auditor_receipt,
            timestamp_utc,
        )?;

        Ok((verdict, claim.claim_id))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kaizen_controller_orchestration() {
        let mut controller = KaizenController::new(KaizenControllerConfig::default());
        let (verdict, claim_id) = controller
            .process_hypothesis_evaluation(
                "hyp_trend_01",
                0.01,
                0.02,
                0.03,
                4,
                true,
                true,
                15.5,
                "impl_receipt_777",
                "auditor_receipt_888",
                1_000_000,
            )
            .unwrap();

        assert!(matches!(verdict, KaizenVerdict::SupportedEdge { .. }));
        assert!(!claim_id.is_empty());
        assert!(controller.claim_registry.get_claim(&claim_id).is_some());
    }
}
