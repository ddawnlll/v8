//! Holdout Burn Semantics & Burn Receipts (D-147, D-149, Rules 11, 17, 18, 34, 35, M4).
//!
//! Invariant (AF-T07): A used POLICY_FROZEN_OOS segment emits a HoldoutBurnReceipt and
//! cannot remain pristine for that lineage. Subsequent evaluations on burned segments are diagnostic only.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::research::data_role::{DataRoleLedger, DataSegmentRole};

/// An immutable, cryptographically sealed Holdout Burn Receipt.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HoldoutBurnReceipt {
    pub burn_receipt_id: String,
    pub segment_id: String,
    pub policy_lineage: String,
    pub prior_role: DataSegmentRole,
    pub new_role: DataSegmentRole,
    pub burned_at_timestamp_ns: u64,
    pub receipt_digest: String,
}

impl HoldoutBurnReceipt {
    /// Burns a pristine holdout segment for the given policy lineage, recording the irreversible transition.
    pub fn burn_segment(
        ledger: &mut DataRoleLedger,
        segment_id: &str,
        lineage: &str,
        timestamp_ns: u64,
    ) -> Result<Self, &'static str> {
        let current_role = ledger.get_role(segment_id, lineage);

        if current_role != DataSegmentRole::PolicyFrozenOos {
            return Err("CANNOT_BURN_NON_FROZEN_OOS_SEGMENT");
        }

        // Transition role in ledger to BURNED_DIAGNOSTIC
        ledger.assign_role(segment_id, lineage, DataSegmentRole::BurnedDiagnostic);

        let mut hasher = Sha256::new();
        hasher.update(segment_id.as_bytes());
        hasher.update(lineage.as_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        let digest = format!("{:x}", hasher.finalize());
        let burn_receipt_id = format!("burn-{}-{}", &digest[..12], segment_id);

        Ok(Self {
            burn_receipt_id,
            segment_id: segment_id.to_string(),
            policy_lineage: lineage.to_string(),
            prior_role: DataSegmentRole::PolicyFrozenOos,
            new_role: DataSegmentRole::BurnedDiagnostic,
            burned_at_timestamp_ns: timestamp_ns,
            receipt_digest: digest,
        })
    }
}
