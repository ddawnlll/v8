//! V8 Kaizen Continuous Improvement Engine — Adaptive Sweep Authority & Stopped e-BH Gate.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §6 (Adaptive Sweep Gate)
//! - `OPEN_DECISIONS.md` O-032 (*Anytime-valid sequential error control for candidate sweeps*)
//! - arXiv:2502.08539 (*On Local and Global Filtration Dependencies in Sequential Multiple Testing with Stopped e-Processes*)
//! - arXiv:2009.02824 (*e-BH procedure for FDR control under arbitrary dependence*)
//! - arXiv:2210.01948 (*Safe Anytime-Valid Inference via Test Martingales*)

use serde::{Deserialize, Serialize};

use crate::kaizen::challenger::{ChallengerFamilySpec, ChallengerVariant};
use crate::kaizen::diagnosis::VariantId;
use crate::kaizen::research_debt::GlobalTrialLedger;

/// Multi-variant candidate sweep execution mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SweepMode {
    /// Pre-declared, finite sample size with full trial debt accounting and post-hoc FWER/DSR control (ENABLED).
    FixedSample,
    /// Sequential early-stopping under stopped e-BH (BLOCKED under Open Decision O-032).
    AdaptiveSequential,
}

/// Canonical sweep execution errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SweepError {
    /// Adaptive sequential search requested without certified O-032 authority.
    SequentialEvidenceAuthorityMissing {
        open_decision: String,
        details: String,
    },
    /// Invalid sweep configuration or empty parameter lattice.
    InvalidSweepConfiguration(String),
    /// Failure during candidate variant evaluation.
    ExecutionFailure(String),
}

impl std::fmt::Display for SweepError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::SequentialEvidenceAuthorityMissing {
                open_decision,
                details,
            } => {
                write!(
                    f,
                    "BLOCKED_BY_{open_decision}: Sequential evidence authority missing. {details}"
                )
            }
            Self::InvalidSweepConfiguration(msg) => {
                write!(f, "INVALID_SWEEP_CONFIGURATION: {msg}")
            }
            Self::ExecutionFailure(msg) => write!(f, "EXECUTION_FAILURE: {msg}"),
        }
    }
}

impl std::error::Error for SweepError {}

/// Formal unblocking criteria for Open Decision O-032.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct O032UnblockingCriteria {
    pub supermartingale_valid_under_null: bool,
    pub global_filtration_contract_specified: bool,
    pub empirical_fdr_monte_carlo_verified: bool,
    pub reference_oracle_parity_in_rust: bool,
    pub trial_accounting_contract_pinned: bool,
    pub authority_receipt_registered: bool,
}

impl O032UnblockingCriteria {
    /// Verifies whether all governance gates required to unlock adaptive sequential sweeping are met.
    pub fn is_fully_certified(&self) -> bool {
        self.supermartingale_valid_under_null
            && self.global_filtration_contract_specified
            && self.empirical_fdr_monte_carlo_verified
            && self.reference_oracle_parity_in_rust
            && self.trial_accounting_contract_pinned
            && self.authority_receipt_registered
    }
}

/// Configuration for parameter sweep execution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SweepConfig {
    pub sweep_id: String,
    pub mode: SweepMode,
    pub challenger_family_spec: ChallengerFamilySpec,
    pub dataset_lineage: String,
    pub target_metric: String,
}

/// Evaluation receipt for a completed sweep execution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SweepReceipt {
    pub sweep_id: String,
    pub mode: SweepMode,
    pub variants_evaluated: usize,
    pub initial_research_choices: u64,
    pub final_research_choices: u64,
    pub total_trials_registered: u64,
    pub best_variant_id: Option<VariantId>,
    pub best_variant_score: Option<f64>,
}

/// Sweep execution engine.
pub struct SweepEngine;

impl SweepEngine {
    /// Executes a parameter sweep across candidate variants with fail-closed governance enforcement.
    ///
    /// - In `FixedSample` mode: evaluates all variants on the preregistered lattice and records trial debt.
    /// - In `AdaptiveSequential` mode: fails closed with `SequentialEvidenceAuthorityMissing` (BLOCKED_BY_O032).
    pub fn execute_sweep<F>(
        config: &SweepConfig,
        ledger: &mut GlobalTrialLedger,
        mut evaluate_variant: F,
    ) -> Result<SweepReceipt, SweepError>
    where
        F: FnMut(&ChallengerVariant) -> Result<f64, String>,
    {
        match config.mode {
            SweepMode::AdaptiveSequential => {
                // Governance Invariant (I2): Fails closed unconditionally under O-032
                Err(SweepError::SequentialEvidenceAuthorityMissing {
                    open_decision: "O-032".to_string(),
                    details: "Adaptive sequential early-stopping is BLOCKED_BY_O032 until anytime-valid stopped e-BH local/global filtration contracts under cross-variant stopping are mathematically proven and certified.".to_string(),
                })
            }
            SweepMode::FixedSample => {
                let variants = config
                    .challenger_family_spec
                    .generate_variants()
                    .map_err(|e| SweepError::InvalidSweepConfiguration(e.to_string()))?;

                let initial_debt = ledger.research_choice_count();
                let mut best_variant = None;
                let mut best_score = f64::NEG_INFINITY;

                for v in &variants {
                    // Register candidate in global research debt ledger
                    ledger.record_trial(
                        &v.family_id,
                        &v.variant_id,
                        &v.variant_hash,
                        &config.dataset_lineage,
                        v.parameter_values.clone(),
                        vec![format!("sweep_{}", config.sweep_id)],
                        None,
                    );

                    let score = evaluate_variant(v).map_err(SweepError::ExecutionFailure)?;
                    if score > best_score {
                        best_score = score;
                        best_variant = Some(v.variant_id.clone());
                    }
                }

                let final_debt = ledger.research_choice_count();

                Ok(SweepReceipt {
                    sweep_id: config.sweep_id.clone(),
                    mode: SweepMode::FixedSample,
                    variants_evaluated: variants.len(),
                    initial_research_choices: initial_debt,
                    final_research_choices: final_debt,
                    total_trials_registered: variants.len() as u64,
                    best_variant_id: best_variant,
                    best_variant_score: if best_score.is_finite() {
                        Some(best_score)
                    } else {
                        None
                    },
                })
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kaizen::challenger::DiscreteParameterRange;

    fn sample_spec() -> ChallengerFamilySpec {
        let p1 = DiscreteParameterRange::new("lookback", vec![14.0, 21.0]).unwrap();
        let p2 = DiscreteParameterRange::new("multiplier", vec![1.5, 2.0, 2.5]).unwrap();
        ChallengerFamilySpec::new(
            "sweep_family_001",
            "bollinger_breakout",
            "v1",
            "Sweep testing family",
            vec![p1, p2],
        )
        .unwrap()
    }

    #[test]
    fn test_fixed_sample_sweep_evaluates_and_accounts_trial_debt() {
        let mut ledger = GlobalTrialLedger::new();
        let spec = sample_spec();

        let config = SweepConfig {
            sweep_id: "sweep_fixed_01".to_string(),
            mode: SweepMode::FixedSample,
            challenger_family_spec: spec,
            dataset_lineage: "dataset_btc_2024".to_string(),
            target_metric: "net_expectancy_r".to_string(),
        };

        let receipt = SweepEngine::execute_sweep(&config, &mut ledger, |variant| {
            // Mock deterministic score computation
            let score = variant.parameter_values.get("multiplier").copied().unwrap_or(0.0) * 0.1;
            Ok(score)
        })
        .expect("FixedSample sweep must succeed");

        assert_eq!(receipt.mode, SweepMode::FixedSample);
        assert_eq!(receipt.variants_evaluated, 6); // 2 * 3 = 6 points
        assert_eq!(receipt.initial_research_choices, 0);
        assert_eq!(receipt.final_research_choices, 6);
        assert_eq!(receipt.total_trials_registered, 6);
        assert!(receipt.best_variant_id.is_some());
        assert_eq!(receipt.best_variant_score, Some(0.25));

        assert_eq!(ledger.research_choice_count(), 6);
    }

    #[test]
    fn test_adaptive_sequential_mode_fails_closed_blocked_by_o032() {
        let mut ledger = GlobalTrialLedger::new();
        let spec = sample_spec();

        let config = SweepConfig {
            sweep_id: "sweep_adaptive_01".to_string(),
            mode: SweepMode::AdaptiveSequential,
            challenger_family_spec: spec,
            dataset_lineage: "dataset_btc_2024".to_string(),
            target_metric: "net_expectancy_r".to_string(),
        };

        let err = SweepEngine::execute_sweep(&config, &mut ledger, |_| Ok(1.0))
            .expect_err("AdaptiveSequential must fail closed pending O-032");

        match err {
            SweepError::SequentialEvidenceAuthorityMissing {
                open_decision,
                details,
            } => {
                assert_eq!(open_decision, "O-032");
                assert!(details.contains("BLOCKED_BY_O032"));
            }
            other => panic!("Expected SequentialEvidenceAuthorityMissing error, got {:?}", other),
        }

        // Ledger must NOT have registered any uncertified trials
        assert_eq!(ledger.research_choice_count(), 0);
    }

    #[test]
    fn test_o032_unblocking_criteria_certification_check() {
        let uncertified = O032UnblockingCriteria {
            supermartingale_valid_under_null: false,
            global_filtration_contract_specified: false,
            empirical_fdr_monte_carlo_verified: false,
            reference_oracle_parity_in_rust: false,
            trial_accounting_contract_pinned: false,
            authority_receipt_registered: false,
        };
        assert!(!uncertified.is_fully_certified());

        let certified = O032UnblockingCriteria {
            supermartingale_valid_under_null: true,
            global_filtration_contract_specified: true,
            empirical_fdr_monte_carlo_verified: true,
            reference_oracle_parity_in_rust: true,
            trial_accounting_contract_pinned: true,
            authority_receipt_registered: true,
        };
        assert!(certified.is_fully_certified());
    }
}
