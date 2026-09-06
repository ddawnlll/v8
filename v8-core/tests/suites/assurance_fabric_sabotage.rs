//! Constitutional Sabotage Suite — Part 1: AF-T01 through AF-T06 (D-147, D-149, Rule 44).

use v8_core::assurance::*;
use v8_core::authority::{Authority, DecisionAuthority, EvidenceAuthority, RealizationStatus};
use v8_core::claims::StatutoryClaimClass;
use serde_json::json;

#[test]
fn test_af_t01_synthetic_evidence_cannot_satisfy_economic_claims() {
    let source_auth = Authority::new(
        EvidenceAuthority::ModelDerived,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Hypothetical,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    // 1. Synthetic attestation targeting EconomicReplication must be rejected
    let synthetic_economic_attestation = EvidenceAttestation {
        attestation_id: "att-synth-econ-1".to_string(),
        provider_id: "world-generator-jump".to_string(),
        provider_lineage: "synthetic-market-lineage".to_string(),
        target_claim: AssuranceClaim::EconomicReplication,
        authority: proj,
        artifact_hash: "abcdef0123456789abcdef0123456789".to_string(),
        is_synthetic: true,
        status: AttestationStatus::Verified,
        confidence_score: 0.99,
        metric_payload: json!({ "gross_pnl": 500.0, "net_pnl": 450.0 }),
    };

    let verdict = synthetic_economic_attestation.check_admissibility();
    assert_eq!(
        verdict,
        AdmissibilityVerdict::Inadmissible(
            "SYNTHETIC_EVIDENCE_FORBIDDEN_FOR_ECONOMIC_OR_SETTLEMENT_CLAIMS"
        )
    );

    // 2. Synthetic attestation targeting StructuralRobustness is admissible
    let synthetic_robustness_attestation = EvidenceAttestation {
        attestation_id: "att-synth-rob-1".to_string(),
        provider_id: "world-generator-jump".to_string(),
        provider_lineage: "synthetic-market-lineage".to_string(),
        target_claim: AssuranceClaim::StructuralRobustness,
        authority: proj,
        artifact_hash: "abcdef0123456789abcdef0123456789".to_string(),
        is_synthetic: true,
        status: AttestationStatus::Verified,
        confidence_score: 0.99,
        metric_payload: json!({ "tail_capture": 0.85 }),
    };

    assert_eq!(
        synthetic_robustness_attestation.check_admissibility(),
        AdmissibilityVerdict::Admissible
    );
}

#[test]
fn test_af_t02_pit_defeater_deterministically_blocks_shadow_ready() {
    let source_auth = Authority::new(
        EvidenceAuthority::Observed,
        DecisionAuthority::PortfolioAuthorized,
        RealizationStatus::Simulated,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-super-profitable".to_string(),
        "hash-super-profitable-code-12345".to_string(),
        "universe-btcusdt-1h".to_string(),
        vec![
            AssuranceClaim::EconomicReplication,
            AssuranceClaim::ProspectiveEfficacy,
        ],
        proj,
        EvaluationEpoch(1),
        1700000000000000000,
    );

    // Evidence claiming massive profit
    let profitable_attestation = EvidenceAttestation {
        attestation_id: "att-profit-1".to_string(),
        provider_id: "usdm-simulator".to_string(),
        provider_lineage: "real-tape-usdm".to_string(),
        target_claim: AssuranceClaim::EconomicReplication,
        authority: proj,
        artifact_hash: "0123456789abcdef0123456789abcdef".to_string(),
        is_synthetic: false,
        status: AttestationStatus::Verified,
        confidence_score: 1.0,
        metric_payload: json!({ "net_pnl": 5000.0 }),
    };

    // Hard PIT / Lookahead Defeater
    let pit_defeater = DefeaterReceipt::new(
        AssuranceClaim::ProspectiveEfficacy,
        DefeaterSeverity::ConstitutionalVeto,
        "LOOKAHEAD_FUTURE_SHOCK_DETECTED: Signal referenced bar N+1 at bar N".to_string(),
        "causal_future_shock_gate".to_string(),
        vec!["feature_store".to_string(), "expert_scan".to_string()],
        1700000000000000000,
    );

    let receipt = AssuranceCaseAdjudicator::adjudicate(
        &manifest,
        &[],
        &[profitable_attestation],
        &[pit_defeater],
        1700000000000000000,
    );

    // Even with massive profit, ConstitutionalVeto forces entire case to VETOED
    assert_eq!(receipt.overall_verdict, "ASSURANCE_CASE_VETOED");
    assert_eq!(
        receipt.claim_statuses.get(&AssuranceClaim::ProspectiveEfficacy),
        Some(&ClaimStatus::Blocked)
    );
    assert_eq!(
        receipt.claim_statuses.get(&AssuranceClaim::EconomicReplication),
        Some(&ClaimStatus::Blocked)
    );
}

#[test]
fn test_af_t03_authority_projection_never_increases_tensor_dimensions() {
    let source_auth = Authority::new(
        EvidenceAuthority::ModelDerived,
        DecisionAuthority::Reconciled,
        RealizationStatus::Hypothetical,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    // 1. Initial projection is non-escalating
    assert!(proj.is_non_escalating_wrt(&source_auth));

    // 2. An illegal escalated projection must be detected
    let mut escalated_proj = proj;
    escalated_proj.realization = RealizationStatus::CashflowSettled;
    assert!(!escalated_proj.is_non_escalating_wrt(&source_auth));

    let mut escalated_evidence = proj;
    escalated_evidence.evidence = EvidenceAuthority::Observed;
    assert!(!escalated_evidence.is_non_escalating_wrt(&source_auth));

    // 3. Counterfactual authority cannot validate RealizedCashflow claim
    assert!(proj.validate_claim_admissibility(StatutoryClaimClass::RealizedCashflow).is_err());
}

#[test]
fn test_af_t04_hash_divergent_artifacts_are_inadmissible_to_sealed_case() {
    let source_auth = Authority::new(
        EvidenceAuthority::Observed,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Hypothetical,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-v1".to_string(),
        "hash-policy-code-v1".to_string(),
        "universe-btcusdt-1h".to_string(),
        vec![AssuranceClaim::EngineeringIntegrity],
        proj,
        EvaluationEpoch(1),
        1700000000000000000,
    );

    // Sealed manifest verification passes initially
    assert!(manifest.verify_integrity());

    // Tampered manifest fails integrity verification
    let mut tampered = manifest.clone();
    tampered.policy_code_hash = "hash-malicious-tampered-code".to_string();
    assert!(!tampered.verify_integrity());
}

#[test]
fn test_af_t05_same_provider_lineage_cannot_satisfy_independence_twice() {
    let mut graph = CommonModeGraph::new();

    // Two providers sharing the same underlying data pipeline / lineage
    graph.register_provider("expert-a".to_string(), "shared-binance-pipeline-v1".to_string());
    graph.register_provider("expert-b".to_string(), "shared-binance-pipeline-v1".to_string());

    // Independent third provider
    graph.register_provider("expert-c".to_string(), "disjoint-kraken-pipeline-v1".to_string());

    // expert-a and expert-b are NOT independent
    assert!(!graph.are_independent(&["expert-a".to_string(), "expert-b".to_string()]));

    // expert-a and expert-c ARE independent
    assert!(graph.are_independent(&["expert-a".to_string(), "expert-c".to_string()]));
}

#[test]
fn test_af_t06_claim_rule_bound_aware_composition_fails_closed() {
    let bound_rule = ClaimRule {
        rule_id: "rule-drawdown-bound".to_string(),
        target_claim: AssuranceClaim::StructuralRobustness,
        composition: CompositionRule::BoundAware { lower: 0.0, upper: 0.10 }, // Max DD <= 10%
        required_providers: vec!["usdm_sim".to_string()],
    };

    let source_auth = Authority::new(
        EvidenceAuthority::Observed,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Hypothetical,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    // Attestation within bounds (8% DD) -> passes
    let passing_attestation = EvidenceAttestation {
        attestation_id: "att-1".to_string(),
        provider_id: "usdm_sim".to_string(),
        provider_lineage: "sim-lineage".to_string(),
        target_claim: AssuranceClaim::StructuralRobustness,
        authority: proj,
        artifact_hash: "0123456789abcdef0123456789abcdef".to_string(),
        is_synthetic: false,
        status: AttestationStatus::Verified,
        confidence_score: 1.0,
        metric_payload: json!({ "value": 0.08 }),
    };

    assert!(bound_rule.evaluate(&[passing_attestation]));

    // Attestation breaching bounds (15% DD) -> fails
    let breaching_attestation = EvidenceAttestation {
        attestation_id: "att-2".to_string(),
        provider_id: "usdm_sim".to_string(),
        provider_lineage: "sim-lineage".to_string(),
        target_claim: AssuranceClaim::StructuralRobustness,
        authority: proj,
        artifact_hash: "0123456789abcdef0123456789abcdef".to_string(),
        is_synthetic: false,
        status: AttestationStatus::Verified,
        confidence_score: 1.0,
        metric_payload: json!({ "value": 0.15 }),
    };

    assert!(!bound_rule.evaluate(&[breaching_attestation]));
}

#[test]
fn test_af_t09_defeater_cannot_be_outvoted_by_majority() {
    let source_auth = Authority::new(
        EvidenceAuthority::Observed,
        DecisionAuthority::ExecutionAuthorized,
        RealizationStatus::Simulated,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    let manifest = EvaluationCaseManifest::new_sealed(
        "policy-majority-vote".to_string(),
        "hash-majority-vote-code".to_string(),
        "universe-btcusdt-1h".to_string(),
        vec![
            AssuranceClaim::EngineeringIntegrity,
            AssuranceClaim::EconomicReplication,
            AssuranceClaim::StructuralRobustness,
        ],
        proj,
        EvaluationEpoch(1),
        1700000000000000000,
    );

    // 10 positive attestations
    let mut attestations = Vec::new();
    for i in 0..10 {
        attestations.push(EvidenceAttestation {
            attestation_id: format!("att-pos-{}", i),
            provider_id: "pos_provider".to_string(),
            provider_lineage: format!("pos_lineage_{}", i),
            target_claim: AssuranceClaim::EconomicReplication,
            authority: proj,
            artifact_hash: "0123456789abcdef0123456789abcdef".to_string(),
            is_synthetic: false,
            status: AttestationStatus::Verified,
            confidence_score: 0.99,
            metric_payload: json!({ "profit": 1000.0 }),
        });
    }

    // Single hard defeater on EconomicReplication
    let hard_defeater = DefeaterReceipt::new(
        AssuranceClaim::EconomicReplication,
        DefeaterSeverity::ClaimScoped,
        "UNACCOUNTED_TAKER_FEE_SURVIVORSHIP_BIAS".to_string(),
        "fee_auditor".to_string(),
        vec!["fee_model".to_string()],
        1700000000000000000,
    );

    let receipt = AssuranceCaseAdjudicator::adjudicate(
        &manifest,
        &[],
        &attestations,
        &[hard_defeater],
        1700000000000000000,
    );

    // Invariant (AF-T09): Defeater cannot be outvoted by the 10 positive attestations
    assert_eq!(
        receipt.claim_statuses.get(&AssuranceClaim::EconomicReplication),
        Some(&ClaimStatus::Blocked)
    );
    assert_eq!(receipt.overall_verdict, "ASSURANCE_CASE_FALSIFIED");
}

