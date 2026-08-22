//! Adversarial Separation & Dual-Key Independence Auditor (D-132, Rule 32).

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DualKeyVerificationResult {
    pub authorized: bool,
    pub implementer_receipt_id: String,
    pub auditor_receipt_id: String,
    pub verdict_hash: String,
}

pub struct IndependenceAuditor;

impl IndependenceAuditor {
    /// Validates dual-key separation of powers: IMPLEMENTER != AUDITOR != VERDICT.
    pub fn audit_dual_key(
        worker_agent_id: &str,
        auditor_agent_id: &str,
        impl_digest: &str,
        audit_replay_digest: &str,
        zero_synthetic_verified: bool,
    ) -> Result<DualKeyVerificationResult, String> {
        // Rule: Worker cannot grade/audit itself
        if worker_agent_id == auditor_agent_id {
            return Err(format!(
                "SELF_GRADING_PROHIBITED: Worker '{worker_agent_id}' cannot act as independent auditor"
            ));
        }

        // Rule: Replay digest must bit-exact match
        if impl_digest != audit_replay_digest {
            return Err(format!(
                "REPLAY_DIGEST_MISMATCH: Impl='{impl_digest}', Audit='{audit_replay_digest}'"
            ));
        }

        // Rule: Zero-synthetic verification must be certified by auditor
        if !zero_synthetic_verified {
            return Err("SYNTHETIC_DATA_LEAKAGE_DETECTED: Auditor failed zero-synthetic check".to_string());
        }

        let mut c = crate::hash::Canon::new();
        c.push_str("DualKeyVerdict");
        c.push_str(worker_agent_id);
        c.push_str(auditor_agent_id);
        c.push_str(impl_digest);
        let verdict_hash = c.finish_blake3_hex();

        Ok(DualKeyVerificationResult {
            authorized: true,
            implementer_receipt_id: format!("impl_{impl_digest}"),
            auditor_receipt_id: format!("audit_{audit_replay_digest}"),
            verdict_hash,
        })
    }
}
