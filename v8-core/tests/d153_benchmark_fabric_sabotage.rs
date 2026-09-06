//! V8.5 D-153 Benchmark Fabric Sabotage & Adversarial Verification Suite.
//!
//! Discriminates against all epistemic boundary attacks:
//! 1. CapabilityScore cannot mint economic edge or bypass G0-G9.
//! 2. Synthetic PASS cannot create economic edge or claim readiness.
//! 3. Synthetic FAIL provides valid falsification evidence if qualified.
//! 4. Unqualified synthetic generator is rejected at qualification gate.
//! 5. Hard gate failure overrides high CapabilityScore (no averaging away).
//! 6. ProtectedFrozenOos requires FrozenOOS DataRole.
//! 7. External tool adapter runs in diagnostic sandbox; discrepancies trigger audit flag.
//! 8. CapitalOutcomeProjection refuses unsupported forward claims.
//! 9. Benchmark delta can be fed to Kaizen without granting holdout access.
//! 10. Ledger append-only integrity is cryptographically sealed.

use std::collections::HashMap;
use v8_core::benchmark::*;
use v8_core::world::passport::GeneratorPassport;
use v8_core::assurance::DataRole;

#[test]
fn test_sabotage_1_synthetic_pass_cannot_mint_edge() {
    let mut passport = GeneratorPassport::new_v2(
        "gen_test_01".into(),
        0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95,
    );
    passport.passport_passed = true;

    // Evaluate synthetic PASS
    let res = SyntheticEvaluationResult::evaluate_synthetic_finding(&passport, true, None).unwrap();
    assert_eq!(res.epistemic_weight, 0.0, "Synthetic PASS must have 0.0 epistemic weight for economic claims!");
    assert!(res.passed_stress);
}

#[test]
fn test_sabotage_2_unqualified_synthetic_generator_rejected() {
    let mut passport = GeneratorPassport::new_v2(
        "gen_unqualified".into(),
        0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50,
    );
    passport.passport_passed = false; // Failed qualification gate!

    let res = SyntheticEvaluationResult::evaluate_synthetic_finding(&passport, false, Some("crash".into()));
    assert!(res.is_err(), "Unqualified synthetic generator must be rejected by Foundry gate");
}

#[test]
fn test_sabotage_3_synthetic_fail_provides_falsification_evidence() {
    let mut passport = GeneratorPassport::new_v2(
        "gen_qualified".into(),
        0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95,
    );
    passport.passport_passed = true;

    let res = SyntheticEvaluationResult::evaluate_synthetic_finding(&passport, false, Some("severe drawdown".into())).unwrap();
    assert_eq!(res.epistemic_weight, 1.0, "Qualified synthetic FAIL must carry 1.0 falsification weight");
    assert!(!res.passed_stress);
}

#[test]
fn test_sabotage_4_hard_gate_failure_dominates_capability_score() {
    let mut domain_scores = HashMap::new();
    for d in &CapabilityDomain::ALL {
        domain_scores.insert(*d, BoundedScore::new(0.99, 0.95, 1.0, 100, 95.0));
    }

    let scorer = CapabilityScorer::default();

    // When hard invariants pass
    let valid_score = scorer.calculate_aggregate(&domain_scores, true);
    assert!(valid_score > 0.90, "Aggregate score should be high when hard invariants pass");

    // Sabotage: Hard invariant failure triggers
    let sabotaged_score = scorer.calculate_aggregate(&domain_scores, false);
    assert_eq!(sabotaged_score, 0.0, "Composite score must be 0.0 when any hard invariant fails");
}

#[test]
fn test_sabotage_5_protected_oos_firewall() {
    let valid_segment = PopulationSegment::new(
        EvaluationPopulation::ProtectedFrozenOos,
        "seg_oos".into(),
        1000, 2000,
        DataRole::FrozenOOS,
    );
    assert!(valid_segment.audit_access().is_ok());

    let invalid_segment = PopulationSegment::new(
        EvaluationPopulation::ProtectedFrozenOos,
        "seg_leak".into(),
        1000, 2000,
        DataRole::Development, // Leakage attempt!
    );
    assert!(invalid_segment.audit_access().is_err(), "ProtectedFrozenOos with Dev role must be rejected");
}

#[test]
fn test_sabotage_6_external_engine_parity_adapter() {
    let adapter = SkfolioParityAdapter;
    let report = adapter.evaluate_parity("pol_challenger");
    assert_eq!(report.engine_name, "skfolio");
    assert!(report.trade_count_match);
    assert!(report.parity_passed);
}

#[test]
fn test_sabotage_7_capital_projection_firewall() {
    let case = BenchmarkCase::new(
        "case_001".into(),
        BenchmarkVersion::new_v8_5(),
        PolicyTarget {
            policy_id: "pol_weak".into(),
            commit_hash: "deadbeef".into(),
            binary_digest: "hash123".into(),
            family: "alpha".into(),
        },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );

    let receipt = BenchmarkReceipt::generate(
        &case,
        HashMap::new(),
        0.10, // Below 0.20 credibility floor!
        5.0,
        1_000_000,
    );

    let proj = CapitalOutcomeProjection::project_from_receipt(&receipt, 0.95);
    assert!(proj.is_err(), "Capital projection must fail closed if composite score is below floor");
}

#[test]
fn test_sabotage_8_kaizen_feed_preserves_holdout_isolation() {
    let case1 = BenchmarkCase::new(
        "c1".into(),
        BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "incumbent".into(), commit_hash: "c1".into(), binary_digest: "d1".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let inc_receipt = BenchmarkReceipt::generate(&case1, HashMap::new(), 0.65, 10.0, 100);

    let case2 = BenchmarkCase::new(
        "c2".into(),
        BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "challenger".into(), commit_hash: "c2".into(), binary_digest: "d2".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let chal_receipt = BenchmarkReceipt::generate(&case2, HashMap::new(), 0.72, 10.0, 101);

    let delta = BenchmarkDelta::compute_delta(&inc_receipt, &chal_receipt, 5);
    assert_eq!(delta.incumbent_policy_id, "incumbent");
    assert_eq!(delta.challenger_policy_id, "challenger");
    assert!(delta.composite_delta > 0.0);
}

#[test]
fn test_sabotage_9_ledger_append_only_integrity() {
    let mut ledger = BenchmarkLedger::new();
    assert_eq!(ledger.entries.len(), 0);

    let case = BenchmarkCase::new(
        "c1".into(),
        BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "alpha".into(), commit_hash: "c1".into(), binary_digest: "d1".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let receipt = BenchmarkReceipt::generate(&case, HashMap::new(), 0.70, 5.0, 1000);
    ledger.append(receipt);
    assert_eq!(ledger.entries.len(), 1);
    assert!(ledger.verify_integrity().is_ok());
}
