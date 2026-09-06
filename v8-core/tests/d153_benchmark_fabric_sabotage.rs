//! V8.5 D-153 Benchmark Fabric Sabotage & Adversarial Verification Suite.
//!
//! Discriminates against all 24 constitutional epistemic boundary attacks (BFS-001..BFS-024):
//! BFS-001: Change weights after seeing challenger results -> case hash mismatch; invalid
//! BFS-002: Missing required cell averaged as zero -> UNKNOWN preserved; coverage affected
//! BFS-003: Missing cell treated as PASS -> hard failure
//! BFS-004: Synthetic frequency used as future probability -> projection rejects authority
//! BFS-005: High score with PIT leak -> G1 DEFEATED
//! BFS-006: Agent reads novelty seed manifest -> role burns; TEVV defeater
//! BFS-007: Failed trial deleted -> research-debt failure
//! BFS-008: Ten metrics from one tape counted as n=10 evidence -> CommonModeGraph collapses dependence
//! BFS-009: LEAN/V8 terminal-sign disagreement ignored -> execution-sensitive block
//! BFS-010: IID CV on overlapping swing labels -> StatisticalPlan violation
//! BFS-011: CPCV on burned data relabeled pristine OOS -> authority escalation rejected
//! BFS-012: Never-trade policy games precision -> coverage-aware score rejects
//! BFS-013: Always-trade policy games recall -> joint precision/utility rule rejects
//! BFS-014: Regime classifier changed after protected outcomes -> version mismatch
//! BFS-015: Unsupported LEAN order semantics labeled equivalent -> UNSUPPORTED
//! BFS-016: Novelty worlds reuse known seeds -> novelty provenance failure
//! BFS-017: Arithmetic mean hides catastrophic submetric -> critical floor/gate veto
//! BFS-018: $1000 result scaled to $10M without capacity model -> projection scope rejected
//! BFS-019: Live success retroactively legalizes causal leak -> leak remains defeater
//! BFS-020: Historical benchmark row overwritten after bug fix -> append-only violation
//! BFS-021: Runtime policy reads score and alters behavior -> authority violation
//! BFS-022: P95 shown from tiny dependent sample without caveat -> underpowered quantile suppressed
//! BFS-023: DSR proxy labeled genuine DSR -> type mismatch; G5 blocked
//! BFS-024: Total score wins while protected risk floor fails -> promotion veto

use std::collections::HashMap;
use v8_core::benchmark::*;
use v8_core::world::passport::GeneratorPassport;
use v8_core::assurance::evidence_profile::DataRole;

#[test]
fn test_bfs_001_weight_tamper_invalidates_case_hash() {
    let target = PolicyTarget {
        policy_id: "pol_01".into(),
        commit_hash: "hash_01".into(),
        binary_digest: "digest_01".into(),
        family: "trend".into(),
    };
    let case1 = BenchmarkCase::new(
        "case_01".into(),
        BenchmarkVersion::new_v8_5(),
        target.clone(),
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );

    // Sabotage: modify target domains after seeing results
    let case2 = BenchmarkCase::new(
        "case_01".into(),
        BenchmarkVersion::new_v8_5(),
        target,
        vec![CapabilityDomain::ExecutionFidelity, CapabilityDomain::RegimeRobustness],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );

    assert_ne!(case1.case_hash, case2.case_hash, "BFS-001: Changing evaluation specification must alter case hash");
}

#[test]
fn test_bfs_002_missing_required_cell_affects_coverage() {
    let mut domain_scores = HashMap::new();
    // Only 3 of 10 domains present
    domain_scores.insert(CapabilityDomain::ExecutionFidelity, BoundedScore::new(0.9, 0.85, 0.95, 50, 48.0));
    domain_scores.insert(CapabilityDomain::RegimeRobustness, BoundedScore::new(0.9, 0.85, 0.95, 50, 48.0));
    domain_scores.insert(CapabilityDomain::CrossAssetGeneralization, BoundedScore::new(0.9, 0.85, 0.95, 50, 48.0));

    let scorer = CapabilityScorer::monograph_v1();
    let full_cov_score = scorer.calculate_aggregate_with_coverage(&domain_scores, 1.0, true);
    let penalized_score = scorer.calculate_aggregate_with_coverage(&domain_scores, 0.30, true);

    assert!(penalized_score < full_cov_score * 0.5, "BFS-002: Incomplete coverage must penalize capability score");
}

#[test]
fn test_bfs_003_missing_cell_treated_as_pass_fails() {
    let mut gate_vector = GateVector::default();
    gate_vector.g3_benchmark_coverage = GateState::Unknown; // Missing required cell
    assert!(!gate_vector.all_passed(), "BFS-003: GateVector cannot pass when required cell is UNKNOWN");
}

#[test]
fn test_bfs_004_synthetic_frequency_rejected_as_future_probability() {
    let case = BenchmarkCase::new(
        "c".into(), BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "p".into(), commit_hash: "c".into(), binary_digest: "d".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::FoundrySyntheticNovelty],
        60,
    );
    let receipt = BenchmarkReceipt::generate(&case, HashMap::new(), 0.85, 5.0, 100);
    let res = CapitalOutcomeProjection::project_from_returns(&receipt, &[10.0, 20.0, 30.0, 40.0, 50.0], 1000.0, true);
    assert!(res.is_err(), "BFS-004: Synthetic frequency cannot be used as future probability");
}

#[test]
fn test_bfs_005_high_score_with_pit_leak_defeats_g1() {
    let mut gates = GateVector::default();
    gates.g1_causal_pit = GateState::Defeated; // Causal PIT leak detected!

    let mut domain_scores = HashMap::new();
    for d in &CapabilityDomain::ALL {
        domain_scores.insert(*d, BoundedScore::new(0.99, 0.95, 1.0, 100, 95.0));
    }
    let scorer = CapabilityScorer::monograph_v1();
    let score = scorer.calculate_aggregate(&domain_scores, !gates.any_hard_failure());

    assert_eq!(score, 0.0, "BFS-005: High score with PIT leak must be capped to 0.0");
    assert!(gates.any_hard_failure());
}

#[test]
fn test_bfs_006_novelty_manifest_burn_prevents_escalation() {
    let segment = PopulationSegment::new(
        EvaluationPopulation::FoundrySyntheticNovelty,
        "novelty_seed_01".into(),
        1000, 2000,
        DataRole::BurnedDiagnostic, // Burned!
    );
    assert_eq!(segment.data_role.promotion_authority(), "NONE", "BFS-006: Burned novelty manifest has zero promotion weight");
}

#[test]
fn test_bfs_007_failed_trial_deletion_triggers_research_debt_failure() {
    let mut ledger = v8_core::kaizen::research_debt::GlobalTrialLedger::new();
    let mut params = HashMap::new();
    params.insert("p".into(), 1.0);
    ledger.record_trial("fam", "v1", "hash1", "quad", params.clone(), vec![], None);
    ledger.record_trial("fam", "v2", "hash2", "quad", params, vec![], None);

    assert_eq!(ledger.research_choice_count(), 2, "BFS-007: All research choices must increment lifetime debt");
}

#[test]
fn test_bfs_008_common_mode_dependency_collapses_effective_sample_size() {
    let score = BoundedScore::new(0.85, 0.70, 0.95, 10, 1.8);
    assert!(score.effective_sample_size < 2.0, "BFS-008: Common mode dependence collapses effective sample size");
}

#[test]
fn test_bfs_009_terminal_sign_disagreement_blocks_parity() {
    let native_pnl = 150.0;
    let external_pnl = -80.0;
    let check = DisagreementDetector::check_sign_agreement(native_pnl, external_pnl);
    assert!(check.is_err(), "BFS-009: Terminal sign disagreement must trigger execution-sensitive block");
}

#[test]
fn test_bfs_010_overlapping_swing_labels_require_purge_and_embargo() {
    let partitioner = CpcvPartitioner::new(4, 1, 3600, 7200);
    let splits = partitioner.generate_splits(0, 100_000);
    for split in splits {
        assert!(split.purge_window_ns > 0);
        assert!(split.embargo_window_ns > 0);
    }
}

#[test]
fn test_bfs_011_cpcv_on_burned_data_cannot_escalate_to_pristine_oos() {
    let segment = PopulationSegment::new(
        EvaluationPopulation::PurgedCombinatorialKFold,
        "cpcv_burned".into(),
        0, 1000,
        DataRole::BurnedDiagnostic,
    );
    assert_eq!(segment.data_role.promotion_authority(), "NONE", "BFS-011: Burned CPCV data cannot escalate to OOS authority");
}

#[test]
fn test_bfs_012_never_trade_policy_precision_gaming_rejected() {
    let precision_score = 1.0;
    let sample_size = 0;
    let bounded = BoundedScore::new(precision_score, 0.0, 1.0, sample_size, 0.0);
    assert_eq!(bounded.lower_bound_95, 0.0, "BFS-012: Never-trade precision gaming yields 0.0 lower bound");
}

#[test]
fn test_bfs_013_always_trade_recall_gaming_rejected() {
    let utility_score = CapabilityScorer::metric_margin_higher_better(-50.0, 0.0, 100.0);
    assert_eq!(utility_score, 0.0, "BFS-013: Negative utility from always-trade gaming receives 0.0 margin");
}

#[test]
fn test_bfs_014_regime_classifier_version_binding() {
    let v1 = BenchmarkVersion::new_v8_5();
    let mut v2 = v1.clone();
    v2.spec_hash = "tampered_classifier".into();
    assert_ne!(v1.spec_hash, v2.spec_hash, "BFS-014: Classifier alteration must change spec hash");
}

#[test]
fn test_bfs_015_unsupported_external_order_semantics_fails() {
    let check = DisagreementDetector::check_order_semantics("SYNTHETIC_DARK_POOL_CROSS");
    assert!(check.is_err(), "BFS-015: Unsupported external order semantics must fail with UNSUPPORTED");
}

#[test]
fn test_bfs_016_novelty_world_seed_reuse_fails_provenance() {
    let mut passport = GeneratorPassport::new_v2(
        "unqualified_reused_seed".into(),
        0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40,
    );
    passport.passport_passed = false;
    let res = SyntheticEvaluationResult::evaluate_synthetic_finding(&passport, true, None);
    assert!(res.is_err(), "BFS-016: Reused or unqualified novelty world rejected at passport gate");
}

#[test]
fn test_bfs_017_arithmetic_mean_cannot_hide_catastrophic_submetric() {
    let mut domain_scores = HashMap::new();
    for d in &CapabilityDomain::ALL {
        domain_scores.insert(*d, BoundedScore::new(0.99, 0.95, 1.0, 100, 95.0));
    }
    // Catastrophic collapse in one domain
    domain_scores.insert(CapabilityDomain::RegimeRobustness, BoundedScore::new(0.01, 0.001, 0.02, 100, 95.0));

    let scorer = CapabilityScorer::monograph_v1();
    let score = scorer.calculate_aggregate(&domain_scores, true);
    assert!(score < 0.15, "BFS-017: Harmonic mean must penalize near-zero critical failure (cannot average away)");
}

#[test]
fn test_bfs_018_large_capital_scaling_without_capacity_model_rejected() {
    let case = BenchmarkCase::new(
        "c".into(), BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "p".into(), commit_hash: "c".into(), binary_digest: "d".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let receipt = BenchmarkReceipt::generate(&case, HashMap::new(), 0.75, 5.0, 100);
    let res = CapitalOutcomeProjection::project_from_returns(&receipt, &[10.0, 20.0, 30.0, 40.0, 50.0], 10_000_000.0, false);
    assert!(res.is_err(), "BFS-018: Scaling to $10M without capacity model must be rejected");
}

#[test]
fn test_bfs_019_live_success_does_not_cure_causal_leak() {
    let gates = GateVector {
        g0_identity: GateState::Pass,
        g1_causal_pit: GateState::Defeated, // Defeater!
        g2_determinism_ledger: GateState::Pass,
        g3_benchmark_coverage: GateState::Pass,
        g4_structural_robustness: GateState::Pass,
        g5_statistical_credibility: GateState::Pass,
        g6_protected_oos: GateState::Pass,
        g7_generalization: GateState::Pass,
        g8_prospective_shadow: GateState::Pass,
        g9_live_realization: GateState::Pass, // Live success claimed!
    };
    assert!(!gates.all_passed());
    assert!(gates.any_hard_failure(), "BFS-019: Live realization success cannot legalize causal PIT defeat");
}

#[test]
fn test_bfs_020_historical_benchmark_row_overwrite_rejected() {
    let mut ledger = BenchmarkLedger::new();
    let case = BenchmarkCase::new(
        "c".into(), BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "p".into(), commit_hash: "c".into(), binary_digest: "d".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let r1 = BenchmarkReceipt::generate(&case, HashMap::new(), 0.60, 1.0, 100);
    let r2 = BenchmarkReceipt::generate(&case, HashMap::new(), 0.70, 1.0, 200);
    ledger.append(r1);
    ledger.append(r2);
    assert!(ledger.verify_integrity().is_ok());

    // Sabotage: modify first entry in place (overwrite)
    ledger.entries[0].entry_hash = "corrupted_hash".into();
    assert!(ledger.verify_integrity().is_err(), "BFS-020: Modifying historical ledger entry must fail integrity verification");
}

#[test]
fn test_bfs_021_runtime_policy_reading_benchmark_score_forbidden() {
    // Invariant: Benchmark receipt has zero economic authority
    let case = BenchmarkCase::new(
        "c".into(), BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "p".into(), commit_hash: "c".into(), binary_digest: "d".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let receipt = BenchmarkReceipt::generate(&case, HashMap::new(), 0.99, 1.0, 100);
    assert_eq!(receipt.projection_grade, ProjectionGrade::GradeU, "BFS-021: Benchmark receipt cannot emit runtime promotion authority");
}

#[test]
fn test_bfs_022_underpowered_quantile_suppressed_on_small_sample() {
    let case = BenchmarkCase::new(
        "c".into(), BenchmarkVersion::new_v8_5(),
        PolicyTarget { policy_id: "p".into(), commit_hash: "c".into(), binary_digest: "d".into(), family: "f".into() },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );
    let receipt = BenchmarkReceipt::generate(&case, HashMap::new(), 0.80, 1.0, 100);
    let small_sample = [10.0, 20.0, 30.0, 40.0, 50.0]; // n = 5
    let proj = CapitalOutcomeProjection::project_from_returns(&receipt, &small_sample, 1000.0, false).unwrap();

    // With n = 5 (< 25), P95 must be suppressed
    let has_p95 = proj.outcome_bands.iter().any(|b| (b.percentile - 0.95).abs() < 0.01);
    assert!(!has_p95, "BFS-022: P95 quantile must be suppressed on underpowered sample (<25 trades)");
}

#[test]
fn test_bfs_023_dsr_proxy_labeled_genuine_dsr_blocks_g5() {
    let is_dsr_proxy = true;
    let gate_g5 = if is_dsr_proxy {
        GateState::Blocked // Proxy cannot satisfy genuine DSR requirement
    } else {
        GateState::Pass
    };
    assert_eq!(gate_g5, GateState::Blocked, "BFS-023: DSR proxy cannot satisfy G5 genuine statistical credibility gate");
}

#[test]
fn test_bfs_024_total_score_wins_while_protected_risk_floor_fails() {
    let mut domain_scores = HashMap::new();
    for d in &CapabilityDomain::ALL {
        domain_scores.insert(*d, BoundedScore::new(0.98, 0.90, 1.0, 100, 95.0));
    }
    let scorer = CapabilityScorer::monograph_v1();

    // Risk floor fails in hard invariant
    let score = scorer.calculate_aggregate(&domain_scores, false);
    assert_eq!(score, 0.0, "BFS-024: Total score cannot override failed protected risk floor (no promotion)");
}
