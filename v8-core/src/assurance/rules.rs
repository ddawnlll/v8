//! Claim Composition Rules & Adjudication Logic (D-147, D-149, M0_CLOSED, M1).
//!
//! Defines rigorous Boolean and threshold composition semantics: ALL_OF, ANY_OF, THRESHOLD, BOUND_AWARE.
//! Hard conjunctions prevent minority voting over critical invariant defeaters.

use serde::{Deserialize, Serialize};
use crate::assurance::attestation::{AttestationStatus, EvidenceAttestation};
use crate::assurance::claim::AssuranceClaim;

/// Composition mode for aggregating subclaims / attestations.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum CompositionRule {
    /// All dependent attestations must be VERIFIED.
    AllOf,
    /// At least one dependent attestation must be VERIFIED.
    AnyOf,
    /// At least K out of N dependent attestations must be VERIFIED.
    Threshold { required: usize, total: usize },
    /// Value must strictly fall within [lower_bound, upper_bound].
    BoundAware { lower: f64, upper: f64 },
}

/// A formal Claim Rule governing how an AssuranceClaim is adjudicated.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ClaimRule {
    pub rule_id: String,
    pub target_claim: AssuranceClaim,
    pub composition: CompositionRule,
    pub required_providers: Vec<String>,
}

impl ClaimRule {
    /// Evaluates the claim rule against a slice of verified attestations.
    pub fn evaluate(&self, attestations: &[EvidenceAttestation]) -> bool {
        let matching: Vec<&EvidenceAttestation> = attestations
            .iter()
            .filter(|a| a.target_claim == self.target_claim)
            .collect();

        if matching.is_empty() {
            return false;
        }

        match &self.composition {
            CompositionRule::AllOf => {
                matching.iter().all(|a| a.status == AttestationStatus::Verified)
            }
            CompositionRule::AnyOf => {
                matching.iter().any(|a| a.status == AttestationStatus::Verified)
            }
            CompositionRule::Threshold { required, total: _ } => {
                let verified_count = matching
                    .iter()
                    .filter(|a| a.status == AttestationStatus::Verified)
                    .count();
                verified_count >= *required
            }
            CompositionRule::BoundAware { lower, upper } => {
                matching.iter().all(|a| {
                    if a.status != AttestationStatus::Verified {
                        return false;
                    }
                    if let Some(val) = a.metric_payload.get("value").and_then(|v| v.as_f64()) {
                        val >= *lower && val <= *upper
                    } else {
                        false
                    }
                })
            }
        }
    }
}
