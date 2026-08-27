//! Sealed Assurance Case Receipts (D-147, D-149, M1).
//!
//! Captures the final, cryptographically bound receipt emitted after case adjudication.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use crate::assurance::case::{CaseIdentity, EvaluationEpoch};
use crate::assurance::claim::AssuranceClaim;
use crate::assurance::defeater::DefeaterReceipt;

/// Final status of an evaluated claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClaimStatus {
    Verified,
    Falsified,
    Blocked,
    Unresolved,
}

/// The final cryptographic receipt of an evaluated Assurance Case.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AssuranceCaseReceipt {
    pub receipt_id: String,
    pub case_id: CaseIdentity,
    pub epoch: EvaluationEpoch,
    pub overall_verdict: String,
    pub claim_statuses: HashMap<AssuranceClaim, ClaimStatus>,
    pub active_defeaters: Vec<DefeaterReceipt>,
    pub evaluated_at_timestamp_ns: u64,
    pub receipt_digest: String,
}

impl AssuranceCaseReceipt {
    pub fn new(
        case_id: CaseIdentity,
        epoch: EvaluationEpoch,
        overall_verdict: String,
        claim_statuses: HashMap<AssuranceClaim, ClaimStatus>,
        active_defeaters: Vec<DefeaterReceipt>,
        timestamp_ns: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(case_id.0.as_bytes());
        hasher.update(&epoch.0.to_le_bytes());
        hasher.update(overall_verdict.as_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        for (c, s) in &claim_statuses {
            hasher.update(c.as_str().as_bytes());
            hasher.update(format!("{:?}", s).as_bytes());
        }
        for d in &active_defeaters {
            hasher.update(d.receipt_hash.as_bytes());
        }
        let digest = format!("{:x}", hasher.finalize());
        let receipt_id = format!("receipt-case-{}", &digest[..16]);

        Self {
            receipt_id,
            case_id,
            epoch,
            overall_verdict,
            claim_statuses,
            active_defeaters,
            evaluated_at_timestamp_ns: timestamp_ns,
            receipt_digest: digest,
        }
    }
}
