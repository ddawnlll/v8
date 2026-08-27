//! Hard Defeater Propagation & Minimal Blocking Paths (D-147, D-149, M0_CLOSED, M1).
//!
//! Enforces non-negotiable hard defeaters. When an invariant fails (e.g. lookahead, holdout leak),
//! a DefeaterReceipt is generated and deterministically blocks top-level claims regardless of profit.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::assurance::claim::AssuranceClaim;

/// Defeater severity level.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DefeaterSeverity {
    /// Informational warning / non-blocking divergence.
    Advisory,
    /// Blocks specific subclaims but allows independent branches.
    ClaimScoped,
    /// Absolute veto — immediately forces SHADOW_READY and DEPLOYMENT_QUALIFIED to BLOCKED.
    ConstitutionalVeto,
}

/// An immutable, cryptographically sealed Defeater Receipt.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DefeaterReceipt {
    pub defeater_id: String,
    pub blocked_claim: AssuranceClaim,
    pub severity: DefeaterSeverity,
    pub reason: String,
    pub source_module: String,
    pub minimal_path: Vec<String>,
    pub timestamp_ns: u64,
    pub receipt_hash: String,
}

impl DefeaterReceipt {
    /// Creates and seals a new DefeaterReceipt.
    pub fn new(
        blocked_claim: AssuranceClaim,
        severity: DefeaterSeverity,
        reason: String,
        source_module: String,
        minimal_path: Vec<String>,
        timestamp_ns: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(blocked_claim.as_str().as_bytes());
        hasher.update(reason.as_bytes());
        hasher.update(source_module.as_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        for p in &minimal_path {
            hasher.update(p.as_bytes());
        }
        let digest = format!("{:x}", hasher.finalize());
        let defeater_id = format!("defeater-{}", &digest[..16]);

        Self {
            defeater_id,
            blocked_claim,
            severity,
            reason,
            source_module,
            minimal_path,
            timestamp_ns,
            receipt_hash: digest,
        }
    }
}
