//! Immutable EvaluationCase & Epoch Manifests (D-147, D-149, M0_CLOSED, M1).
//!
//! Sealed cases are permanently immutable. Any policy, candidate, schema, or rule mutation
//! creates a new EvaluationCase identity or advances the immutable EvaluationEpoch.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::assurance::authority::AuthorityProjection;
use crate::assurance::claim::AssuranceClaim;

/// Unique cryptographic identity of an evaluation case.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct CaseIdentity(pub String);

/// Chronological, append-only evaluation epoch.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default, Serialize, Deserialize)]
pub struct EvaluationEpoch(pub u64);

/// Immutable Manifest defining the exact scope, rules, and policy under evaluation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvaluationCaseManifest {
    pub case_id: CaseIdentity,
    pub epoch: EvaluationEpoch,
    pub policy_id: String,
    pub policy_code_hash: String,
    pub universe_id: String,
    pub target_claims: Vec<AssuranceClaim>,
    pub base_authority: AuthorityProjection,
    pub sealed_at_timestamp_ns: u64,
    pub manifest_digest: String,
}

impl EvaluationCaseManifest {
    /// Creates and seals a new EvaluationCaseManifest, computing its immutable SHA-256 digest.
    pub fn new_sealed(
        policy_id: String,
        policy_code_hash: String,
        universe_id: String,
        target_claims: Vec<AssuranceClaim>,
        base_authority: AuthorityProjection,
        epoch: EvaluationEpoch,
        timestamp_ns: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(policy_id.as_bytes());
        hasher.update(policy_code_hash.as_bytes());
        hasher.update(universe_id.as_bytes());
        hasher.update(&epoch.0.to_le_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        for c in &target_claims {
            hasher.update(c.as_str().as_bytes());
        }
        let digest = format!("{:x}", hasher.finalize());
        let case_id = CaseIdentity(format!("case-{}", &digest[..16]));

        Self {
            case_id,
            epoch,
            policy_id,
            policy_code_hash,
            universe_id,
            target_claims,
            base_authority,
            sealed_at_timestamp_ns: timestamp_ns,
            manifest_digest: digest,
        }
    }

    /// Verifies the cryptographic integrity of the sealed manifest.
    pub fn verify_integrity(&self) -> bool {
        let mut hasher = Sha256::new();
        hasher.update(self.policy_id.as_bytes());
        hasher.update(self.policy_code_hash.as_bytes());
        hasher.update(self.universe_id.as_bytes());
        hasher.update(&self.epoch.0.to_le_bytes());
        hasher.update(&self.sealed_at_timestamp_ns.to_le_bytes());
        for c in &self.target_claims {
            hasher.update(c.as_str().as_bytes());
        }
        let computed = format!("{:x}", hasher.finalize());
        computed == self.manifest_digest
    }
}
