//! Evidence Attestation & Cryptographic Witness Binding (D-147, D-149, M1).
//!
//! Formally captures an empirical or formal evidence observation submitted to the Assurance Fabric.

use serde::{Deserialize, Serialize};
use crate::assurance::authority::AuthorityProjection;
use crate::assurance::claim::AssuranceClaim;

/// Admissibility verdict of an individual evidence item.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AdmissibilityVerdict {
    Admissible,
    Inadmissible(&'static str),
    Contaminated(&'static str),
}

/// Verification status of an evidence attestation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AttestationStatus {
    Verified,
    Falsified,
    Inconclusive,
}

/// A certified Evidence Attestation bound to an EvaluationCase.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceAttestation {
    pub attestation_id: String,
    pub provider_id: String,
    pub provider_lineage: String,
    pub target_claim: AssuranceClaim,
    pub authority: AuthorityProjection,
    pub artifact_hash: String,
    pub is_synthetic: bool,
    pub status: AttestationStatus,
    pub confidence_score: f64,
    pub metric_payload: serde_json::Value,
}

impl EvidenceAttestation {
    /// Validates admissibility of this attestation against the target claim.
    pub fn check_admissibility(&self) -> AdmissibilityVerdict {
        if self.is_synthetic && !self.target_claim.accepts_synthetic_evidence() {
            return AdmissibilityVerdict::Inadmissible(
                "SYNTHETIC_EVIDENCE_FORBIDDEN_FOR_ECONOMIC_OR_SETTLEMENT_CLAIMS",
            );
        }
        if self.artifact_hash.is_empty() || self.artifact_hash.len() < 16 {
            return AdmissibilityVerdict::Inadmissible("INVALID_OR_MISSING_ARTIFACT_HASH");
        }
        AdmissibilityVerdict::Admissible
    }
}
