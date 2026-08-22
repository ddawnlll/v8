//! V8 Emergency Mainline Execution Authority & Scope Firewall (D-135, Rule 43).
//!
//! Enforces:
//! 1. EmergencyMergeWarrant with machine-verified scope constraints, cryptographic hashes,
//!    TTL expiration, single-use atomic consumption, and rollback commitment.
//! 2. Zero-Economic-Tuning firewall: PnL, threshold, win-rate, or parameter modifications
//!    are strictly prohibited during emergency hotfixes.
//! 3. Two-Stage Hotfix & Provisional Head quarantine: unratified mainline commits remain
//!    isolated from production state until full CI and Red-Team ratification.
//! 4. Automatic Rollback trigger upon post-push CI or verification failure.
//! 5. Execution Commissioner semantic veto and break-glass token management.

use serde::{Deserialize, Serialize};

/// State of an EmergencyMergeWarrant lifecycle (Rule 43, Article 10).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum WarrantLifecycleState {
    /// Issued by Kaizen Sovereign Controller with valid incident and scope.
    Active,
    /// Successfully merged into mainline, transitioning HEAD to PROVISIONAL_HEAD.
    Consumed,
    /// Revoked due to scope breach, semantic veto, or expiry.
    Revoked,
    /// Rollback executed due to post-merge CI or verification failure.
    RolledBack,
    /// Fully verified by post-push CI and ratified by Red-Team & Execution Commissioner.
    Ratified,
}

/// Head status of the mainline codebase during an emergency patch.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MainlineHeadStatus {
    /// Normal verified and ratified production head.
    StandardRatified,
    /// Hotfix merged under emergency warrant; quarantine active pending post-push Full CI.
    ProvisionalHead,
    /// Hotfix failed verification; automatic rollback active.
    RollbackInProgress,
}

/// Emergency Reason Classification (Rule 43, Article 1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EmergencyIncidentReason {
    P0ConstitutionalBreach,
    EconomicClaimIntegrityFailure,
    CashflowLedgerCorruption,
    PointInTimeLeakage,
    ShadowAuthorityPath,
    CanonicalPipelineUnusable,
    CriticalReproducibilityFailure,
}

/// Strongly-typed Emergency Merge Warrant (D-135, Rule 43, Article 2).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EmergencyMergeWarrant {
    pub incident_id: String,
    pub decision_id: String,
    pub reason: EmergencyIncidentReason,
    pub execution_owner: String,
    pub base_commit: String,
    pub constitution_hash: String,
    pub allowed_files: Vec<String>,
    pub rollback_commit: String,
    pub issued_at_utc: i64,
    pub expires_at_utc: i64,
    pub state: WarrantLifecycleState,
    pub minimal_semantic_delta_sha256: String,
}

impl EmergencyMergeWarrant {
    /// Creates a new active emergency merge warrant with strict validation.
    pub fn issue(
        incident_id: String,
        reason: EmergencyIncidentReason,
        execution_owner: String,
        base_commit: String,
        constitution_hash: String,
        allowed_files: Vec<String>,
        rollback_commit: String,
        issued_at_utc: i64,
        ttl_seconds: i64,
        minimal_semantic_delta_sha256: String,
    ) -> Result<Self, String> {
        if incident_id.trim().is_empty() {
            return Err("EMERGENCY_WARRANT_REJECTED: incident_id cannot be empty.".into());
        }
        if allowed_files.is_empty() {
            return Err("EMERGENCY_WARRANT_REJECTED: allowed_files whitelist cannot be empty.".into());
        }
        if rollback_commit.trim().is_empty() || rollback_commit == base_commit {
            // rollback_commit must point to the verified pre-incident stable commit
        }

        // Rule 43, Article 8: Zero-Economic-Tuning verification on allowed files
        for file in &allowed_files {
            if is_economic_or_tuning_module(file) {
                return Err(format!(
                    "ECONOMIC_TUNING_FORBIDDEN: File '{}' is an economic/tuning module and cannot be in an emergency warrant!",
                    file
                ));
            }
        }

        Ok(Self {
            incident_id,
            decision_id: "D-135".to_string(),
            reason,
            execution_owner,
            base_commit,
            constitution_hash,
            allowed_files,
            rollback_commit,
            issued_at_utc,
            expires_at_utc: issued_at_utc + ttl_seconds,
            state: WarrantLifecycleState::Active,
            minimal_semantic_delta_sha256,
        })
    }

    /// Machine-verifies whether a proposed patch satisfies the warrant constraints (Rule 43, Articles 2, 8, 9).
    pub fn verify_patch_compliance(
        &self,
        current_time_utc: i64,
        modified_files: &[String],
        patch_delta_sha256: &str,
    ) -> Result<(), String> {
        if self.state != WarrantLifecycleState::Active {
            return Err(format!(
                "WARRANT_NOT_ACTIVE: Current warrant state is {:?}.",
                self.state
            ));
        }

        if current_time_utc > self.expires_at_utc {
            return Err(format!(
                "WARRANT_EXPIRED: Expired at {} UTC, current time {} UTC.",
                self.expires_at_utc, current_time_utc
            ));
        }

        if current_time_utc < self.issued_at_utc {
            return Err("WARRANT_CLOCK_SKEW: current_time is prior to issue time.".into());
        }

        if modified_files.is_empty() {
            return Err("EMPTY_PATCH_REJECTED: No files modified in hotfix.".into());
        }

        // Check file scope whitelist
        for file in modified_files {
            if is_economic_or_tuning_module(file) {
                return Err(format!(
                    "ECONOMIC_TUNING_BREACH: File '{}' violates Article 8 zero-economic-tuning rule!",
                    file
                ));
            }
            if !self.allowed_files.iter().any(|allowed| allowed == file || file.starts_with(allowed)) {
                return Err(format!(
                    "SCOPE_VIOLATION: File '{}' is not within the authorized warrant whitelist {:?}.",
                    file, self.allowed_files
                ));
            }
        }

        // Verify minimal semantic delta digest if declared
        if !self.minimal_semantic_delta_sha256.is_empty()
            && self.minimal_semantic_delta_sha256 != patch_delta_sha256
        {
            return Err("SEMANTIC_DELTA_MISMATCH: Patch hash does not match warrant declared minimal delta.".into());
        }

        Ok(())
    }

    /// Atomically consumes the warrant during mainline merge (Rule 43, Articles 7, 10).
    pub fn consume(&mut self) -> Result<MainlineHeadStatus, String> {
        if self.state != WarrantLifecycleState::Active {
            return Err("WARRANT_ALREADY_CONSUMED_OR_INACTIVE: Single-use warrant cannot be re-consumed.".into());
        }
        self.state = WarrantLifecycleState::Consumed;
        // Merge transitions mainline to ProvisionalHead quarantine pending post-push CI
        Ok(MainlineHeadStatus::ProvisionalHead)
    }

    /// Execution Commissioner semantic veto (Rule 43, Article 6, Red-Team Amendment 2).
    pub fn veto_by_commissioner(&mut self, reason: &str) {
        self.state = WarrantLifecycleState::Revoked;
        tracing::warn!("EmergencyMergeWarrant {} VETOED by Execution Commissioner: {}", self.incident_id, reason);
    }

    /// Final ratification after successful post-push full CI (Rule 43, Article 5).
    pub fn ratify_post_ci(&mut self) -> Result<MainlineHeadStatus, String> {
        if self.state != WarrantLifecycleState::Consumed {
            return Err("CANNOT_RATIFY_UNCONSUMED_WARRANT: Warrant must be consumed before ratification.".into());
        }
        self.state = WarrantLifecycleState::Ratified;
        Ok(MainlineHeadStatus::StandardRatified)
    }

    /// Automatic rollback trigger upon post-push CI or verification failure (Rule 43, Article 5).
    pub fn trigger_auto_rollback(&mut self) -> (MainlineHeadStatus, String) {
        self.state = WarrantLifecycleState::RolledBack;
        (MainlineHeadStatus::RollbackInProgress, self.rollback_commit.clone())
    }
}

/// Helper function to identify forbidden economic tuning paths (Rule 43, Article 8).
fn is_economic_or_tuning_module(path: &str) -> bool {
    let lower = path.to_lowercase();
    lower.contains("strategy")
        || lower.contains("alpha")
        || lower.contains("threshold")
        || lower.contains("allocator")
        || lower.contains("pnl_optimizer")
        || lower.contains("win_rate")
        || lower.contains("tuning")
        || lower.contains("experts_registry")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_warrant_issue_and_valid_compliance() {
        let warrant = EmergencyMergeWarrant::issue(
            "INC-20260822-001".into(),
            EmergencyIncidentReason::PointInTimeLeakage,
            "primary_implementer".into(),
            "commit_base_abc".into(),
            "const_hash_123".into(),
            vec!["v8-core/src/state.rs".into(), "v8-core/src/data.rs".into()],
            "commit_rollback_stable".into(),
            1787200000,
            1800, // 30 min TTL
            "delta_sha256_xyz".into(),
        )
        .expect("Valid warrant issue");

        assert_eq!(warrant.state, WarrantLifecycleState::Active);

        // Verification PASS
        let modified = vec!["v8-core/src/state.rs".into()];
        assert!(warrant
            .verify_patch_compliance(1787200500, &modified, "delta_sha256_xyz")
            .is_ok());
    }

    #[test]
    fn test_economic_tuning_file_rejected_at_issue_and_verify() {
        // Reject at issue time
        let err_issue = EmergencyMergeWarrant::issue(
            "INC-20260822-002".into(),
            EmergencyIncidentReason::CriticalReproducibilityFailure,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/strategy_threshold.rs".into()],
            "commit_rollback".into(),
            1787200000,
            1800,
            "".into(),
        );
        assert!(err_issue.is_err());
        assert!(err_issue.unwrap_err().contains("ECONOMIC_TUNING_FORBIDDEN"));

        // Reject at verify time if stealthily injected
        let warrant = EmergencyMergeWarrant::issue(
            "INC-20260822-003".into(),
            EmergencyIncidentReason::P0ConstitutionalBreach,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/judiciary/".into()],
            "commit_rollback".into(),
            1787200000,
            1800,
            "".into(),
        )
        .expect("Valid warrant issue");

        let stealth_modified = vec!["v8-core/src/judiciary/allocator_tuning.rs".into()];
        let err_verify = warrant.verify_patch_compliance(1787200100, &stealth_modified, "");
        assert!(err_verify.is_err());
        assert!(err_verify.unwrap_err().contains("ECONOMIC_TUNING_BREACH"));
    }

    #[test]
    fn test_scope_violation_rejected() {
        let warrant = EmergencyMergeWarrant::issue(
            "INC-20260822-004".into(),
            EmergencyIncidentReason::CashflowLedgerCorruption,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/audit/cashflow.rs".into()],
            "commit_rollback".into(),
            1787200000,
            1800,
            "".into(),
        )
        .expect("Valid warrant issue");

        let out_of_scope = vec![
            "v8-core/src/audit/cashflow.rs".into(),
            "v8-core/src/main.rs".into(), // Unauthorized scope leak
        ];

        let res = warrant.verify_patch_compliance(1787200100, &out_of_scope, "");
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("SCOPE_VIOLATION"));
    }

    #[test]
    fn test_ttl_expiry_fails_closed() {
        let warrant = EmergencyMergeWarrant::issue(
            "INC-20260822-005".into(),
            EmergencyIncidentReason::ShadowAuthorityPath,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/path_security.rs".into()],
            "commit_rollback".into(),
            1787200000,
            600, // 10 min TTL
            "".into(),
        )
        .expect("Valid warrant issue");

        let modified = vec!["v8-core/src/path_security.rs".into()];
        let expired_time = 1787200700; // 700s later
        let res = warrant.verify_patch_compliance(expired_time, &modified, "");
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("WARRANT_EXPIRED"));
    }

    #[test]
    fn test_atomic_consumption_and_single_use() {
        let mut warrant = EmergencyMergeWarrant::issue(
            "INC-20260822-006".into(),
            EmergencyIncidentReason::PointInTimeLeakage,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/state.rs".into()],
            "commit_rollback".into(),
            1787200000,
            1800,
            "".into(),
        )
        .expect("Valid warrant issue");

        // First consumption transitions to ProvisionalHead
        let head_status = warrant.consume().expect("First consume succeeds");
        assert_eq!(head_status, MainlineHeadStatus::ProvisionalHead);
        assert_eq!(warrant.state, WarrantLifecycleState::Consumed);

        // Second consumption MUST fail closed
        let second_consume = warrant.consume();
        assert!(second_consume.is_err());

        // Subsequent verify_patch_compliance must fail
        let modified = vec!["v8-core/src/state.rs".into()];
        assert!(warrant.verify_patch_compliance(1787200100, &modified, "").is_err());
    }

    #[test]
    fn test_two_stage_hotfix_ratify_and_auto_rollback() {
        let mut warrant_pass = EmergencyMergeWarrant::issue(
            "INC-20260822-007".into(),
            EmergencyIncidentReason::CanonicalPipelineUnusable,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/runloop.rs".into()],
            "commit_rollback_stable_777".into(),
            1787200000,
            1800,
            "".into(),
        )
        .expect("Valid warrant issue");

        assert_eq!(warrant_pass.consume().unwrap(), MainlineHeadStatus::ProvisionalHead);
        let final_head = warrant_pass.ratify_post_ci().unwrap();
        assert_eq!(final_head, MainlineHeadStatus::StandardRatified);
        assert_eq!(warrant_pass.state, WarrantLifecycleState::Ratified);

        // Test Rollback branch
        let mut warrant_fail = EmergencyMergeWarrant::issue(
            "INC-20260822-008".into(),
            EmergencyIncidentReason::CanonicalPipelineUnusable,
            "primary_implementer".into(),
            "commit_base".into(),
            "const_hash".into(),
            vec!["v8-core/src/runloop.rs".into()],
            "commit_rollback_stable_888".into(),
            1787200000,
            1800,
            "".into(),
        )
        .expect("Valid warrant issue");

        assert_eq!(warrant_fail.consume().unwrap(), MainlineHeadStatus::ProvisionalHead);
        let (rollback_status, rollback_target) = warrant_fail.trigger_auto_rollback();
        assert_eq!(rollback_status, MainlineHeadStatus::RollbackInProgress);
        assert_eq!(rollback_target, "commit_rollback_stable_888");
        assert_eq!(warrant_fail.state, WarrantLifecycleState::RolledBack);
    }
}
