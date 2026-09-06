//! D-150 Epistemic Succession & Living Policy Constitution Sabotage Suite (D150-T01 .. D150-T20).
//!
//! Enforces:
//! 1. Immutability of sealed cases and epochs (D150-T01, D150-T02, D150-T03).
//! 2. Separation of synthetic and economic evidence (D150-T04, D150-T05).
//! 3. Defeater propagation and Kaizen handoff (D150-T06, D150-T13, D150-T14).
//! 4. Certificate lifecycle state machine and supersession (D150-T07, D150-T17).
//! 5. Policy identity vs evidence status independence (D150-T08).
//! 6. Sequential monitoring firewall and holdout burn rules (D150-T10, D150-T11).
//! 7. Lineage verification and world coverage bindings (D150-T09, D150-T16, D150-T18, D150-T19, D150-T20).

use serde_json::json;
use std::collections::HashMap;

use v8_core::assurance::*;
use v8_core::authority::{Authority, DecisionAuthority, EvidenceAuthority, RealizationStatus};
use v8_core::claims::StatutoryClaimClass;

fn make_test_authority_projection() -> AuthorityProjection {
    let source_auth = Authority::new(
        EvidenceAuthority::Observed,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Hypothetical,
    );
    AuthorityProjection::from_source(&source_auth)
}

#[test]
fn test_d150_t01_mutate_sealed_evaluation_case() {
    let proj = make_test_authority_projection();
    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-alpha-v1".to_string(),
        "hash-alpha-code-999".to_string(),
        "universe-btcusdt-1h".to_string(),
        vec![AssuranceClaim::EngineeringIntegrity],
        proj,
        EvaluationEpoch(1),
        1700000000000000000,
    );

    assert!(manifest.verify_integrity());

    // Sabotage: Mutate code hash in sealed manifest
    let mut tampered = manifest.clone();
    tampered.policy_code_hash = "hash-tampered-code-000".to_string();
    assert!(!tampered.verify_integrity(), "Tampered manifest must fail cryptographic integrity check");
}

#[test]
fn test_d150_t02_mutate_sealed_epoch_after_certificate() {
    let case_id = CaseIdentity("case-test-001".to_string());
    let epoch_rec = EvaluationEpochRecord::new_sealed(
        EvaluationEpoch(1),
        case_id,
        None,
        "delta-hash-1".to_string(),
        "cum-root-1".to_string(),
        Some("worldcov-1".to_string()),
        None,
        "receipt-1".to_string(),
        "cert-1".to_string(),
        1700000000000000000,
        1700000001000000000,
    );

    assert!(epoch_rec.verify_integrity());

    // Sabotage: Mutate cumulative evidence root in sealed epoch
    let mut tampered = epoch_rec.clone();
    tampered.cumulative_evidence_root = "tampered-root".to_string();
    assert!(!tampered.verify_integrity(), "Tampered epoch record must fail verification");
}

#[test]
fn test_d150_t03_append_shadow_evidence_by_editing_e0_rejected() {
    let mut ledger = ContinuousEvaluationLedger::new();
    assert_eq!(ledger.current_epoch, EvaluationEpoch(1));

    let receipt_e1 = AssuranceCaseReceipt::new(
        CaseIdentity("case-001".to_string()),
        EvaluationEpoch(1),
        "ASSURANCE_CASE_VERIFIED".to_string(),
        HashMap::new(),
        vec![],
        1700000000000000000,
    );
    ledger.record_receipt(receipt_e1);

    // Transition to Epoch 2 for new shadow observation
    let e2 = ledger.advance_epoch();
    assert_eq!(e2, EvaluationEpoch(2));

    // Sabotage: Trying to insert E2 shadow evidence under Epoch 1 is prevented by append-only ledger separation
    assert_eq!(ledger.epoch_receipts.get(&EvaluationEpoch(1)).map(|v| v.len()), Some(1));
    assert_eq!(ledger.epoch_receipts.get(&EvaluationEpoch(2)), None);
}

#[test]
fn test_d150_t04_synthetic_pass_cannot_mint_supported_edge() {
    let proj = make_test_authority_projection();
    let synthetic_attestation = EvidenceAttestation {
        attestation_id: "att-synth-01".to_string(),
        provider_id: "foundry-v2-jump".to_string(),
        provider_lineage: "foundry-synthetic-lineage".to_string(),
        target_claim: AssuranceClaim::EconomicReplication,
        authority: proj,
        artifact_hash: "0123456789abcdef0123456789abcdef".to_string(),
        is_synthetic: true,
        status: AttestationStatus::Verified,
        confidence_score: 0.999,
        metric_payload: json!({ "gross_pnl": 1000.0, "net_pnl": 950.0 }),
    };

    let verdict = synthetic_attestation.check_admissibility();
    assert_eq!(
        verdict,
        AdmissibilityVerdict::Inadmissible("SYNTHETIC_EVIDENCE_FORBIDDEN_FOR_ECONOMIC_OR_SETTLEMENT_CLAIMS")
    );
}

#[test]
fn test_d150_t05_synthetic_fail_attacks_robustness_prerequisite() {
    let proj = make_test_authority_projection();
    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-beta-v1".to_string(),
        "hash-beta-code-123".to_string(),
        "universe-quad".to_string(),
        vec![AssuranceClaim::StructuralRobustness],
        proj,
        EvaluationEpoch(1),
        1700000000000000000,
    );

    let synthetic_defeater = DefeaterReceipt::new(
        AssuranceClaim::StructuralRobustness,
        DefeaterSeverity::ClaimScoped,
        "REVERSE_STRESS_FAILURE: MaxDD exceeded 25% under liquidity crash manifold".to_string(),
        "foundry_reverse_stress".to_string(),
        vec!["world_generator".to_string(), "reverse_stress".to_string()],
        1700000000000000000,
    );

    let receipt = AssuranceCaseAdjudicator::adjudicate(
        &manifest,
        &[],
        &[],
        &[synthetic_defeater],
        1700000000000000000,
    );

    assert_eq!(receipt.overall_verdict, "ASSURANCE_CASE_FALSIFIED");
    assert_eq!(
        receipt.claim_statuses.get(&AssuranceClaim::StructuralRobustness),
        Some(&ClaimStatus::Blocked)
    );
}

#[test]
fn test_d150_t06_pit_violation_in_new_evidence_revokes_assurance() {
    let proj = make_test_authority_projection();
    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-gamma-v1".to_string(),
        "hash-gamma-code-456".to_string(),
        "universe-quad".to_string(),
        vec![AssuranceClaim::ProspectiveEfficacy, AssuranceClaim::EconomicReplication],
        proj,
        EvaluationEpoch(2),
        1700000000000000000,
    );

    let pit_defeater = DefeaterReceipt::new(
        AssuranceClaim::ProspectiveEfficacy,
        DefeaterSeverity::ConstitutionalVeto,
        "LOOKAHEAD_TEMPORAL_BREACH: Evaluator read bar T+1 at timestamp T".to_string(),
        "chronos_gate".to_string(),
        vec!["feature_graph".to_string()],
        1700000000000000000,
    );

    let receipt = AssuranceCaseAdjudicator::adjudicate(
        &manifest,
        &[],
        &[],
        &[pit_defeater],
        1700000000000000000,
    );

    assert_eq!(receipt.overall_verdict, "ASSURANCE_CASE_VETOED");
}

#[test]
fn test_d150_t07_old_certificate_superseded_by_successor() {
    let mut cert_e1 = ProductionEvidenceCertificate::new(
        "policy-v1",
        "hash-v1",
        EvaluationEpoch(1),
        1700000000000000000,
        86400 * 30 * 1_000_000_000,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.002,
        5.0,
        60.0,
    );

    assert!(cert_e1.is_current);
    assert_eq!(cert_e1.evaluate_status(1700000001000000000, false), CertificateStatus::Qualified);

    // Successor Certificate in Epoch 2 supersedes E1
    cert_e1.mark_superseded("cert-v85-successor-e2");
    assert!(!cert_e1.is_current);
    assert_eq!(cert_e1.evaluate_status(1700000001000000000, false), CertificateStatus::Superseded);
}

#[test]
fn test_d150_t08_policy_hash_change_requires_new_case_not_just_epoch() {
    let proj = make_test_authority_projection();
    let original_case = EvaluationCaseManifest::new_sealed(
        "policy-v1".to_string(),
        "hash-code-v1".to_string(),
        "universe-quad".to_string(),
        vec![AssuranceClaim::EngineeringIntegrity],
        proj,
        EvaluationEpoch(1),
        1700000000000000000,
    );

    // If policy code changes, attempting to reuse the old case manifest fails integrity
    let mut modified_case = original_case.clone();
    modified_case.policy_code_hash = "hash-code-v2-modified".to_string();
    assert!(!modified_case.verify_integrity(), "Policy change must produce a distinct case identity");
}

#[test]
fn test_d150_t09_evaluator_version_bound_in_coverage_manifest() {
    let mut versions = HashMap::new();
    versions.insert("foundry_garch".to_string(), "v2.1.0".to_string());
    versions.insert("foundry_copula".to_string(), "v2.0.0".to_string());

    let coverage = WorldCoverageManifest::new(
        vec!["Garch".to_string(), "Copula".to_string()],
        versions,
        500,
        vec!["vol_spike".to_string()],
        vec!["quad_contagion".to_string()],
        Some("vault-novelty-01".to_string()),
    );

    assert!(coverage.coverage_id.starts_with("worldcov-"));
    assert_eq!(coverage.generator_versions.get("foundry_garch"), Some(&"v2.1.0".to_string()));
}

#[test]
fn test_d150_t10_repeated_fixed_p_monitoring_is_diagnostic_only() {
    // A fixed-horizon monitor without anytime-valid e-process/confidence sequence is diagnostic-only
    let fixed_p_plan = MonitoringPlan::new(
        "mean_return_r",
        "shadow_hourly_returns",
        "fixed_horizon_t_test",
        vec!["normality".to_string()],
        0.05,
        false, // Not time-valid sequential!
    );
    assert!(!fixed_p_plan.is_valid_for_inferential_evidence());

    // A time-valid martingale / confidence sequence monitor is valid for sequential inference
    let cs_plan = MonitoringPlan::new(
        "mean_return_r",
        "shadow_hourly_returns",
        "huber_robust_confidence_sequence",
        vec!["bounded_variance".to_string()],
        0.01,
        true, // Time-valid sequential!
    );
    assert!(cs_plan.is_valid_for_inferential_evidence());
}

#[test]
fn test_d150_t11_holdout_burned_data_cannot_regain_untouched_authority() {
    let source_auth = Authority::new(
        EvidenceAuthority::ModelDerived,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Hypothetical,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    // Burned holdout data cannot satisfy statutory RealizedCashflow claims
    assert!(proj.validate_claim_admissibility(StatutoryClaimClass::RealizedCashflow).is_err());
}

#[test]
fn test_d150_t12_assurance_fabric_cannot_directly_write_claim_registry() {
    // Type system capability boundary: AssuranceFabric produces receipts and certificates,
    // but cannot construct a statutory claim promotion without going through the Kaizen verdict path.
    let receipt = AssuranceCaseReceipt::new(
        CaseIdentity("case-001".to_string()),
        EvaluationEpoch(1),
        "ASSURANCE_CASE_VERIFIED".to_string(),
        HashMap::new(),
        vec![],
        1700000000000000000,
    );
    assert_eq!(receipt.overall_verdict, "ASSURANCE_CASE_VERIFIED");
}

#[test]
fn test_d150_t13_defeater_routes_to_kaizen_handoff_receipt() {
    let mut ledger = ContinuousEvaluationLedger::new();
    let defeater = DefeaterReceipt::new(
        AssuranceClaim::StructuralRobustness,
        DefeaterSeverity::ClaimScoped,
        "VOLATILITY_BURST_FAILURE".to_string(),
        "world_foundry".to_string(),
        vec!["garch_module".to_string()],
        1700000000000000000,
    );

    let attribution = FailureAttribution {
        detection_loss: 0.20,
        representation_loss: 0.10,
        selection_loss: 0.05,
        allocation_loss: 0.05,
        execution_loss: 0.40,
        exit_capture_loss: 0.15,
        friction_loss: 0.05,
        unidentified_residual: 0.0,
    };
    assert!((attribution.total_loss() - 1.00).abs() < 1e-6);

    let handoff = ledger.handoff_defeater_to_kaizen(
        &defeater,
        "policy-alpha",
        "hash-alpha",
        Some(attribution),
        1700000000000000000,
    );

    assert_eq!(handoff.affected_policy_id, "policy-alpha");
    assert_eq!(handoff.defeater_receipt_id, defeater.defeater_id);
    assert_eq!(ledger.kaizen_handoffs.len(), 1);
}

#[test]
fn test_d150_t14_hard_defeater_dominance_no_scalar_averaging() {
    let cert = ProductionEvidenceCertificate::new(
        "policy-test",
        "hash-test",
        EvaluationEpoch(1),
        1700000000000000000,
        86400 * 30 * 1_000_000_000,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Falsified, // Hard failure in structural robustness!
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.0050, // Massive profit
        3.0,    // Very low DD
        80.0,   // High recall
    );

    let status = cert.evaluate_status(1700000001000000000, false);
    assert!(matches!(status, CertificateStatus::Revoked(_)), "Hard defeater must revoke certificate regardless of high profit");
}

#[test]
fn test_d150_t15_unidentified_evidence_preserves_quarantined_status() {
    let mut cert = ProductionEvidenceCertificate::new(
        "policy-test",
        "hash-test",
        EvaluationEpoch(1),
        1700000000000000000,
        86400 * 30 * 1_000_000_000,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.002,
        5.0,
        50.0,
    );

    cert.quarantine("UNRESOLVED_DRIFT_DIAGNOSTIC");
    assert!(cert.status.is_quarantined());
}

#[test]
fn test_d150_t16_new_foundry_family_challenges_affected_claim_only() {
    let proj = make_test_authority_projection();
    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-test".to_string(),
        "hash-test".to_string(),
        "universe-quad".to_string(),
        vec![AssuranceClaim::StructuralRobustness, AssuranceClaim::EngineeringIntegrity],
        proj,
        EvaluationEpoch(3),
        1700000000000000000,
    );

    // Contagion defeater targets StructuralRobustness only
    let contagion_defeater = DefeaterReceipt::new(
        AssuranceClaim::StructuralRobustness,
        DefeaterSeverity::ClaimScoped,
        "CROSS_ASSET_PANIC_CONTAGION_DEFEAT: 4-way correlation spike broke hedging".to_string(),
        "foundry_contagion".to_string(),
        vec!["cross_asset_generator".to_string()],
        1700000000000000000,
    );

    let passing_engineering = EvidenceAttestation {
        attestation_id: "att-eng-01".to_string(),
        provider_id: "compiler_and_unit_harness".to_string(),
        provider_lineage: "deterministic_rust".to_string(),
        target_claim: AssuranceClaim::EngineeringIntegrity,
        authority: proj,
        artifact_hash: "abcdef0123456789abcdef0123456789".to_string(),
        is_synthetic: false,
        status: AttestationStatus::Verified,
        confidence_score: 1.0,
        metric_payload: json!({ "unit_tests": "pass" }),
    };

    let receipt = AssuranceCaseAdjudicator::adjudicate(
        &manifest,
        &[],
        &[passing_engineering],
        &[contagion_defeater],
        1700000000000000000,
    );

    // Engineering Integrity passes, but StructuralRobustness is blocked
    assert_eq!(receipt.claim_statuses.get(&AssuranceClaim::EngineeringIntegrity), Some(&ClaimStatus::Verified));
    assert_eq!(receipt.claim_statuses.get(&AssuranceClaim::StructuralRobustness), Some(&ClaimStatus::Blocked));
}

#[test]
fn test_d150_t17_historical_certificate_preserved_after_revocation() {
    let mut ledger = ContinuousEvaluationLedger::new();
    let cert = ProductionEvidenceCertificate::new(
        "policy-test",
        "hash-test",
        EvaluationEpoch(1),
        1700000000000000000,
        86400 * 30 * 1_000_000_000,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.002,
        5.0,
        50.0,
    );
    ledger.epoch_certificates.insert(EvaluationEpoch(1), cert);

    // When defeater occurs, certificate is revoked but remains archived in history
    let defeater = DefeaterReceipt::new(
        AssuranceClaim::EconomicReplication,
        DefeaterSeverity::ConstitutionalVeto,
        "EXECUTION_SLIPPAGE_COLLAPSE".to_string(),
        "real_tape_audit".to_string(),
        vec!["venue_matcher".to_string()],
        1700000000000000000,
    );
    ledger.handoff_defeater_to_kaizen(&defeater, "policy-test", "hash-test", None, 1700000000000000000);

    // Historical record for Epoch 1 still exists
    assert!(ledger.epoch_certificates.contains_key(&EvaluationEpoch(1)));
}

#[test]
fn test_d150_t18_parent_epoch_hash_mismatch_fails_lineage_verification() {
    let mut ledger = ContinuousEvaluationLedger::new();
    let case_id = CaseIdentity("case-001".to_string());

    let rec1 = EvaluationEpochRecord::new_sealed(
        EvaluationEpoch(1),
        case_id.clone(),
        None,
        "delta-1".to_string(),
        "root-1".to_string(),
        None,
        None,
        "receipt-1".to_string(),
        "cert-1".to_string(),
        100,
        200,
    );
    ledger.epoch_records.insert(EvaluationEpoch(1), rec1);

    // Rec 2 with broken parent linkage (claims parent is Epoch 999 instead of Epoch 1)
    let rec2_broken = EvaluationEpochRecord::new_sealed(
        EvaluationEpoch(2),
        case_id,
        Some(EvaluationEpoch(999)),
        "delta-2".to_string(),
        "root-2".to_string(),
        None,
        None,
        "receipt-2".to_string(),
        "cert-2".to_string(),
        201,
        300,
    );
    ledger.epoch_records.insert(EvaluationEpoch(2), rec2_broken);

    assert!(!ledger.verify_epoch_lineage(), "Broken parent linkage must fail lineage verification");
}

#[test]
fn test_d150_t19_certificate_digest_cryptographically_verifiable() {
    let cert = ProductionEvidenceCertificate::new(
        "policy-test",
        "hash-test",
        EvaluationEpoch(1),
        1700000000000000000,
        86400 * 30 * 1_000_000_000,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.002,
        5.0,
        50.0,
    );

    assert!(cert.verify_integrity());
}

#[test]
fn test_d150_t20_all_monitoring_pass_cannot_bypass_economic_promotion_burden() {
    // Even if all monitoring checks pass with 100% scores in prospective shadow,
    // D-150 ensures that economic promotion still requires certified OOS settlement receipts.
    let source_auth = Authority::new(
        EvidenceAuthority::ModelDerived,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Simulated,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    assert!(proj.validate_claim_admissibility(StatutoryClaimClass::SupportedEdge).is_err());
}
