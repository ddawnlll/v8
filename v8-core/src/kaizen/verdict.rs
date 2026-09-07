//! Kaizen Sovereign Verdict Engine (D-132, Rule 33, PH2-003A.3).
//!
//! Enforces:
//! 1. Sole normative verdict authority in V8.
//! 2. Certification of multiple-testing adjustments (SPA / DSR / WRC).
//! 3. Constitutional fail-closed default (NoEconomicClaim).

use serde::{Deserialize, Serialize};
use crate::authority::{Authority, EvidenceAuthority, DecisionAuthority, RealizationStatus};
use crate::claims::{ClaimRegistry, StatutoryClaimClass, StatutoryClaimRecord};
use crate::hash::Canon;

/// Sovereign Normative Verdict emitted solely by the Kaizen Verdict Engine.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum KaizenVerdict {
    /// Statistically certified predictive edge across multiple out-of-sample regimes.
    SupportedEdge {
        dsr_pvalue: f64,
        spa_pvalue: f64,
        wrc_pvalue: f64,
        certified_regimes_count: usize,
    },
    /// Validated research observation or diagnostic without certified economic edge.
    NoEconomicClaim {
        reason: String,
    },
    /// Anomaly, leak, or constitutional violation blocking any claim.
    ClaimBlocked {
        violation_code: String,
        details: String,
    },
}

impl KaizenVerdict {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::SupportedEdge { .. } => "SUPPORTED_EDGE",
            Self::NoEconomicClaim { .. } => "NO_ECONOMIC_CLAIM",
            Self::ClaimBlocked { .. } => "CLAIM_BLOCKED",
        }
    }
}

/// Sovereign Verdict Authority.
pub struct KaizenVerdictEngine;

impl KaizenVerdictEngine {
    pub const SIGNIFICANCE_ALPHA: f64 = 0.05;

    /// Evaluates statistical evidence to emit the sole authoritative verdict.
    pub fn evaluate_verdict(
        dsr_pvalue: f64,
        spa_pvalue: f64,
        wrc_pvalue: f64,
        regimes_tested: usize,
        has_cashflow_reconciliation: bool,
        zero_synthetic_certified: bool,
    ) -> KaizenVerdict {
        if !zero_synthetic_certified {
            return KaizenVerdict::ClaimBlocked {
                violation_code: "RULE_12_SYNTHETIC_LEAK".to_string(),
                details: "Synthetic fixtures or mock metrics detected in evaluation pipeline".to_string(),
            };
        }

        if !has_cashflow_reconciliation {
            return KaizenVerdict::NoEconomicClaim {
                reason: "PHYSICAL_CASHFLOW_NOT_RECONCILED: Lacks double-entry ledger certification".to_string(),
            };
        }

        // Rule: All 3 multiple-testing p-values must strictly pass the significance alpha
        if dsr_pvalue <= Self::SIGNIFICANCE_ALPHA
            && spa_pvalue <= Self::SIGNIFICANCE_ALPHA
            && wrc_pvalue <= Self::SIGNIFICANCE_ALPHA
            && regimes_tested >= 3
        {
            KaizenVerdict::SupportedEdge {
                dsr_pvalue,
                spa_pvalue,
                wrc_pvalue,
                certified_regimes_count: regimes_tested,
            }
        } else {
            KaizenVerdict::NoEconomicClaim {
                reason: format!(
                    "MULTIPLE_TESTING_HURDLE_UNMET: DSR={dsr_pvalue:.4}, SPA={spa_pvalue:.4}, WRC={wrc_pvalue:.4}, Regimes={regimes_tested}"
                ),
            }
        }
    }

    /// Issues an authoritative claim record through the central ClaimRegistry.
    pub fn issue_verdict_claim(
        registry: &mut ClaimRegistry,
        verdict: &KaizenVerdict,
        claim_value: f64,
        units: &str,
        receipt_parents: Vec<String>,
        implementer_receipt: &str,
        auditor_receipt: &str,
        timestamp_utc: i64,
    ) -> Result<StatutoryClaimRecord, String> {
        let (claim_class, authority) = match verdict {
            KaizenVerdict::SupportedEdge { .. } => (
                StatutoryClaimClass::SupportedEdge,
                Authority::new(
                    EvidenceAuthority::Observed,
                    DecisionAuthority::ExecutionAuthorized,
                    RealizationStatus::CashflowSettled,
                ),
            ),
            KaizenVerdict::NoEconomicClaim { .. } => (
                StatutoryClaimClass::DiagnosticSignal,
                Authority::counterfactual_diagnostic(),
            ),
            KaizenVerdict::ClaimBlocked { .. } => {
                return Err("CANNOT_REGISTER_BLOCKED_CLAIM".to_string());
            }
        };

        let mut c = Canon::new();
        c.push_str("KaizenVerdictReceipt");
        c.push_str(verdict.as_str());
        c.push_str(implementer_receipt);
        c.push_str(auditor_receipt);
        c.push_i64(timestamp_utc);
        let verdict_receipt = c.finish_blake3_hex();

        registry.register_claim(
            claim_class,
            claim_value,
            units,
            authority,
            receipt_parents,
            Some(implementer_receipt.to_string()),
            Some(auditor_receipt.to_string()),
            Some(verdict_receipt),
            timestamp_utc,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_verdict_engine_fails_closed_on_synthetic_leak() {
        let verdict = KaizenVerdictEngine::evaluate_verdict(
            0.01, 0.01, 0.01, 5, true, false, // Synthetic leak!
        );
        assert!(matches!(verdict, KaizenVerdict::ClaimBlocked { .. }));
    }

    #[test]
    fn test_verdict_engine_demands_all_three_pvalues_pass() {
        // WRC fails (0.08 > 0.05)
        let verdict = KaizenVerdictEngine::evaluate_verdict(
            0.01, 0.01, 0.08, 5, true, true,
        );
        assert!(matches!(verdict, KaizenVerdict::NoEconomicClaim { .. }));

        // All pass
        let passing = KaizenVerdictEngine::evaluate_verdict(
            0.02, 0.03, 0.04, 4, true, true,
        );
        assert!(matches!(passing, KaizenVerdict::SupportedEdge { .. }));
    }
}
