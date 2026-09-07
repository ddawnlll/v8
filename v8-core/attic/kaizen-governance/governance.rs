//! Alpha-Before-Sizing, Context Gating & Anti-Selection-Bias Governance Guardrails (Issue #222 / GOV-001).
//! Normative Traceability: D-025, D-043, D-044, D-046, D-123; arXiv:2402.05272, arXiv:2608.01494.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CertificationStatus {
    CertifiedWithMultiplicity,
    UncertifiedExploratory,
    Falsified,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContextRoutingMode {
    NoContext,
    SoftContext,
    HardContext,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KellySizingAssessment {
    pub sensor_id: String,
    pub status: CertificationStatus,
    pub empirical_win_rate: f64,
    pub empirical_win_loss_ratio: f64,
    pub raw_kelly_fraction: f64,
    pub allowable_fractional_kelly: f64, // <= 0.25 if certified, exactly 0.0 if uncertified
    pub is_leverage_scaled: bool,
    pub multiplicity_proof_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AntiPruningCompliance {
    pub total_registered_sensors: usize,
    pub evaluated_sensors_count: usize,
    pub silent_deletions_detected: usize,
    pub is_compliant: bool,
}

pub struct GovernanceGuardrailEngine;

impl GovernanceGuardrailEngine {
    /// Calculate Fractional Kelly Sizing strictly adhering to Alpha-Before-Sizing invariant.
    pub fn evaluate_kelly_sizing(
        sensor_id: &str,
        status: CertificationStatus,
        win_rate: f64,
        win_loss_ratio: f64,
        multiplicity_proof_hash: Option<&str>,
    ) -> KellySizingAssessment {
        if win_loss_ratio <= 0.0 || win_rate <= 0.0 || win_rate >= 1.0 {
            return KellySizingAssessment {
                sensor_id: sensor_id.to_string(),
                status,
                empirical_win_rate: win_rate,
                empirical_win_loss_ratio: win_loss_ratio,
                raw_kelly_fraction: 0.0,
                allowable_fractional_kelly: 0.0,
                is_leverage_scaled: false,
                multiplicity_proof_hash: None,
            };
        }

        // Full Kelly: f* = (p * b - q) / b
        let p = win_rate;
        let q = 1.0 - p;
        let b = win_loss_ratio;
        let full_kelly = ((p * b) - q) / b;

        // Rule 1: Uncertified signals NEVER receive leverage or Kelly expansion (Fractional Kelly = 0.0)
        let allowable_kelly = if status == CertificationStatus::CertifiedWithMultiplicity && multiplicity_proof_hash.is_some() {
            (full_kelly * 0.25).clamp(0.0, 0.25)
        } else {
            0.0
        };

        KellySizingAssessment {
            sensor_id: sensor_id.to_string(),
            status,
            empirical_win_rate: win_rate,
            empirical_win_loss_ratio: win_loss_ratio,
            raw_kelly_fraction: full_kelly.max(0.0),
            allowable_fractional_kelly: allowable_kelly,
            is_leverage_scaled: allowable_kelly > 0.0,
            multiplicity_proof_hash: multiplicity_proof_hash.map(|s| s.to_string()),
        }
    }

    /// Audit sensor evaluation roster to prevent silent developer pruning / selection bias.
    pub fn verify_anti_pruning(
        registered_sensor_ids: &[&str],
        evaluated_sensor_ids: &[&str],
    ) -> AntiPruningCompliance {
        let total = registered_sensor_ids.len();
        let evaluated = evaluated_sensor_ids.len();

        let mut silent_deletions = 0;
        for &reg in registered_sensor_ids {
            if !evaluated_sensor_ids.contains(&reg) {
                silent_deletions += 1;
            }
        }

        AntiPruningCompliance {
            total_registered_sensors: total,
            evaluated_sensors_count: evaluated,
            silent_deletions_detected: silent_deletions,
            is_compliant: silent_deletions == 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_alpha_before_sizing_blocks_uncertified_signal() {
        // High win rate (65%), 2.0 reward/risk, but Uncertified
        let res = GovernanceGuardrailEngine::evaluate_kelly_sizing(
            "sensor_experimental",
            CertificationStatus::UncertifiedExploratory,
            0.65,
            2.0,
            None,
        );

        assert_eq!(res.allowable_fractional_kelly, 0.0);
        assert!(!res.is_leverage_scaled);
    }

    #[test]
    fn test_alpha_before_sizing_allows_quarter_kelly_when_certified() {
        let res = GovernanceGuardrailEngine::evaluate_kelly_sizing(
            "sensor_certified",
            CertificationStatus::CertifiedWithMultiplicity,
            0.60,
            2.0,
            Some("sha256_multiplicity_proof_valid"),
        );

        assert!(res.allowable_fractional_kelly > 0.0);
        assert!(res.allowable_fractional_kelly <= 0.25);
        assert!(res.is_leverage_scaled);
    }
}
