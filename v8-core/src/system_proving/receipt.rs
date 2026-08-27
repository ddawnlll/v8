//! System Proving Ground Receipts (D-147, D-149, M3).
//!
//! Sealed receipts documenting end-to-end stress proving ground executions.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::system_proving::attribution::FailureAttributionBreakdown;
use crate::system_proving::metrics::SystemRobustnessVector;

/// Final receipt emitted by the System Proving Ground.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SystemProvingGroundReceipt {
    pub receipt_id: String,
    pub world_id: String,
    pub policy_id: String,
    pub total_trades: usize,
    pub total_campaigns: usize,
    pub metrics: SystemRobustnessVector,
    pub attribution: FailureAttributionBreakdown,
    pub exercises_full_pipeline: bool,
    pub evaluated_at_timestamp_ns: u64,
    pub receipt_digest: String,
}

impl SystemProvingGroundReceipt {
    pub fn new(
        world_id: String,
        policy_id: String,
        total_trades: usize,
        total_campaigns: usize,
        metrics: SystemRobustnessVector,
        attribution: FailureAttributionBreakdown,
        exercises_full_pipeline: bool,
        timestamp_ns: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(world_id.as_bytes());
        hasher.update(policy_id.as_bytes());
        hasher.update(&(total_trades as u64).to_le_bytes());
        hasher.update(&(total_campaigns as u64).to_le_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        let digest = format!("{:x}", hasher.finalize());
        let receipt_id = format!("spg-receipt-{}", &digest[..16]);

        Self {
            receipt_id,
            world_id,
            policy_id,
            total_trades,
            total_campaigns,
            metrics,
            attribution,
            exercises_full_pipeline,
            evaluated_at_timestamp_ns: timestamp_ns,
            receipt_digest: digest,
        }
    }
}
