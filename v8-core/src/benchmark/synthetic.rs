//! Synthetic Authority and Foundry Qualification Gate (D-153 Section 41-48, Rule 57.3).
//!
//! Enforces:
//! - Asymmetric Synthetic Authority: Synthetic FAIL may falsify hypotheses;
//!   Synthetic PASS does NOT create economic edge or claim readiness.
//! - FoundryQualificationGate: All synthetic populations must be qualified via
//!   Market World Foundry GeneratorPassport before benchmark ingestion.

use serde::{Deserialize, Serialize};
use crate::world::passport::GeneratorPassport;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SyntheticEvaluationResult {
    pub generator_id: String,
    pub passed_stress: bool,
    pub failure_mode: Option<String>,
    pub epistemic_weight: f64,
}

impl SyntheticEvaluationResult {
    /// Validates qualification and determines falsification scope
    pub fn evaluate_synthetic_finding(
        passport: &GeneratorPassport,
        stress_passed: bool,
        failure_mode: Option<String>,
    ) -> Result<Self, String> {
        // Enforce qualification gate: passport must have passed
        if !passport.passport_passed {
            return Err(format!(
                "Synthetic world rejected: generator {} failed qualification gate",
                passport.generator_id
            ));
        }

        // Epistemic asymmetry: synthetic pass has zero economic claim weight
        let epistemic_weight = if stress_passed {
            0.0 // PASS does not prove economic edge!
        } else {
            1.0 // FAIL provides falsification evidence!
        };

        Ok(Self {
            generator_id: passport.generator_id.clone(),
            passed_stress: stress_passed,
            failure_mode,
            epistemic_weight,
        })
    }
}
