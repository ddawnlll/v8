//! Comprehensive tests for Judicial Review & Execution Oversight plane (D-134).

use crate::judiciary::mandate::{ExecutionMandate, MobilizationTier, SemanticChangeClass, TaskLease};
use crate::judiciary::veto::{VetoEvidenceType, VetoProof, JudicialVetoGate, VetoDecision, ExpeditedAppealEngine, AppealVerdict};
use crate::judiciary::oversight::{BlindAuditBundle, ProceduralCommissioner, TechnicalCommissioner, GovernanceReceipt};
use crate::judiciary::kaizen_boundary::{KaizenConstitutionalAuditor, KaizenOrchestrationRecord};

fn sample_mandate() -> ExecutionMandate {
    ExecutionMandate {
        mandate_id: "MANDATE-TEST-001".into(),
        decision_id: "D-134".into(),
        tier: MobilizationTier::Tier1Material,
        execution_owner: "worker_agent_01".into(),
        permitted_modules: vec!["v8-core/src/judiciary/".into(), "v8-core/src/audit/".into()],
        permitted_changes: vec![SemanticChangeClass::AuthorityHardening, SemanticChangeClass::BugFix],
        forbidden_changes: vec![SemanticChangeClass::EconomicThresholdTuning],
        constitution_tree_hash: "const_hash_abc123".into(),
        baseline_commit: "git_commit_789xyz".into(),
        lease: TaskLease {
            lease_id: "LEASE-001".into(),
            task_id: "TASK-100".into(),
            issued_at_utc: 1000,
            expires_at_utc: 2000,
            token_budget_ceiling: 50_000,
        },
    }
}

#[test]
fn test_mandate_scope_and_lease() {
    let mandate = sample_mandate();
    assert!(mandate.assert_module_permitted("v8-core/src/judiciary/mod.rs").is_ok());
    assert!(mandate.assert_module_permitted("v8-core/src/trading/tuning.rs").is_err());

    assert!(mandate.assert_change_permitted(&SemanticChangeClass::AuthorityHardening).is_ok());
    assert!(mandate.assert_change_permitted(&SemanticChangeClass::EconomicThresholdTuning).is_err());

    assert!(mandate.lease.is_valid(1500));
    assert!(!mandate.lease.is_valid(2500)); // Expired

    // ProceduralCommissioner audit
    assert!(ProceduralCommissioner::audit(&mandate, 1500, &["v8-core/src/judiciary/mod.rs".into()]).is_ok());
    assert!(ProceduralCommissioner::audit(&mandate, 2500, &["v8-core/src/judiciary/mod.rs".into()]).is_err());
    assert!(ProceduralCommissioner::audit(&mandate, 1500, &["v8-core/src/forbidden/tune.rs".into()]).is_err());
}

#[test]
fn test_constitution_tree_hash_pinning() {
    let mandate = sample_mandate();
    assert!(mandate.assert_constitution_unmodified("const_hash_abc123").is_ok());
    assert!(mandate.assert_constitution_unmodified("const_hash_drifted").is_err());
}

#[test]
fn test_no_naked_veto_enforcement() {
    // 1. Naked veto without proof must be rejected
    let decision = JudicialVetoGate::process_veto(true, None);
    assert!(matches!(decision, VetoDecision::VetoRejectedNakedVeto { .. }));

    // 2. Veto with empty panic message must be rejected
    let bad_proof = VetoProof {
        veto_id: "VETO-001".into(),
        issuing_commissioner: "tech_commissioner".into(),
        evidence: VetoEvidenceType::PanicUnitTestFailure {
            test_name: "test_failure".into(),
            panic_message: "".into(), // Empty!
        },
        failure_reproduction_cmd: "cargo test".into(),
        timestamp_utc: 1500,
    };
    let decision = JudicialVetoGate::process_veto(true, Some(&bad_proof));
    assert!(matches!(decision, VetoDecision::VetoRejectedNakedVeto { .. }));

    // 3. Legitimate veto with valid panic proof is affirmed
    let good_proof = VetoProof {
        veto_id: "VETO-002".into(),
        issuing_commissioner: "tech_commissioner".into(),
        evidence: VetoEvidenceType::PanicUnitTestFailure {
            test_name: "test_sabotage".into(),
            panic_message: "assertion failed: hash mismatch".into(),
        },
        failure_reproduction_cmd: "cargo test --test sabotage".into(),
        timestamp_utc: 1500,
    };
    let decision = JudicialVetoGate::process_veto(true, Some(&good_proof));
    assert!(matches!(decision, VetoDecision::VetoAffirmed { .. }));

    // 4. Overreaching auditor with write rights is rejected
    let decision = JudicialVetoGate::process_veto(false, Some(&good_proof));
    assert!(matches!(decision, VetoDecision::VetoRejectedAuditorOverreach { .. }));
}

#[test]
fn test_expedited_appeal_engine() {
    let proof = VetoProof {
        veto_id: "VETO-003".into(),
        issuing_commissioner: "tech_commissioner".into(),
        evidence: VetoEvidenceType::PanicUnitTestFailure {
            test_name: "test_reproduce".into(),
            panic_message: "failed".into(),
        },
        failure_reproduction_cmd: "cargo test".into(),
        timestamp_utc: 1500,
    };

    // Upheld appeal with green counter-test
    let appeal = ExpeditedAppealEngine::adjudicate_appeal(&proof, true, "falsification_digest_456");
    assert!(matches!(appeal, AppealVerdict::VetoOverturned { .. }));

    // Denied appeal with failing test
    let appeal = ExpeditedAppealEngine::adjudicate_appeal(&proof, false, "");
    assert!(matches!(appeal, AppealVerdict::VetoSustained { .. }));
}

#[test]
fn test_blind_audit_protocol() {
    let bundle = BlindAuditBundle::new(
        "TASK-100".into(),
        "input_hash_111".into(),
        "+ fn new_feature() {}".into(),
        vec!["receipt_test_001".into()],
        "const_hash_abc123".into(),
    );

    assert!(TechnicalCommissioner::audit_bundle(&bundle).is_ok());

    let empty_bundle = BlindAuditBundle::new(
        "TASK-100".into(),
        "input_hash_111".into(),
        "".into(),
        vec![],
        "const_hash_abc123".into(),
    );
    assert!(TechnicalCommissioner::audit_bundle(&empty_bundle).is_err());
}

#[test]
fn test_kaizen_external_constitutional_audit() {
    // Valid distinct roles
    let record = KaizenOrchestrationRecord {
        run_id: "RUN-001".into(),
        implementer_agent_id: "agent_implementer".into(),
        auditor_agent_id: "agent_auditor".into(),
        verdict_authority_id: "kaizen_verdict_engine".into(),
        constitution_tree_hash: "const_hash_999".into(),
    };
    assert!(KaizenConstitutionalAuditor::audit_orchestration(&record, "const_hash_999").is_ok());

    // Self-audit attempt (Dual-Key violation)
    let self_audit_record = KaizenOrchestrationRecord {
        run_id: "RUN-002".into(),
        implementer_agent_id: "agent_alpha".into(),
        auditor_agent_id: "agent_alpha".into(), // Self-audit!
        verdict_authority_id: "kaizen_verdict_engine".into(),
        constitution_tree_hash: "const_hash_999".into(),
    };
    assert!(KaizenConstitutionalAuditor::audit_orchestration(&self_audit_record, "const_hash_999").is_err());
}

#[test]
fn test_governance_receipt_efficiency() {
    let receipt = GovernanceReceipt {
        receipt_id: "GOV-001".into(),
        task_id: "TASK-100".into(),
        tokens_implementation: 10_000,
        tokens_committee: 5_000,
        tokens_audit: 3_000,
        tokens_execution_oversight: 2_000,
        total_tokens: 20_000,
        material_errors_prevented: 2,
    };

    assert!(!receipt.compute_id().is_empty());
    // Oversight cost = (5000 + 3000 + 2000) / 1000 = 10.0 kTokens
    // Score = 2 / 10.0 = 0.2
    let score = receipt.compute_efficiency_score();
    assert!((score - 0.2).abs() < 1e-6);
}
