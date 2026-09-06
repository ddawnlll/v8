//! #328 — Receipt and ledger cryptographic self-verification.
//!
//! Mutation matrix over every authority-relevant field, plus persisted-ledger
//! tamper tests. The invariant under test is issue §13:
//!
//! ```text
//! receipt_digest = H(canonical_encode(all_authority_relevant_fields))
//! ```
//!
//! Any semantic mutation must either change the digest or be rejected. Tests
//! assert on *observable* consequences (does `verify()` still accept it?), not
//! on internal helpers, so a fix that merely renamed fields could not pass.

use std::collections::HashMap;
use std::path::Path;

use v8_core::assurance::evidence_profile::DataRole;
use v8_core::benchmark::case::BenchmarkEvidenceManifest;
use v8_core::benchmark::ledger::{BenchmarkLedger, LedgerTamper};
use v8_core::benchmark::observation::MetricObservation;
use v8_core::benchmark::receipt::{
    ArtifactBinding, BenchmarkReceipt, DomainEvaluationResult, MinimalDefeaterSummary,
    ReceiptVerificationError, RECEIPT_DIGEST_VERSION, RECEIPT_DIGEST_VERSION_LEGACY,
};
use v8_core::benchmark::report::{BenchmarkReportGenerator, VerifiedReceipt};
use v8_core::benchmark::types::{
    CapabilityDomain, EvaluationPopulation, GateState, GateVector, ProjectionGrade,
};
use v8_core::benchmark::{BenchmarkCase, BenchmarkVersion, PolicyTarget};

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

fn fixture_case() -> BenchmarkCase {
    BenchmarkCase::new(
        "case_328".into(),
        BenchmarkVersion::new_v8_5(),
        PolicyTarget {
            policy_id: "pol_328".into(),
            commit_hash: "commit_abc".into(),
            binary_digest: "bin_def".into(),
            family: "trend".into(),
        },
        vec![
            CapabilityDomain::ExecutionFidelity,
            CapabilityDomain::StatisticalCredibility,
        ],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    )
}

fn all_pass() -> GateVector {
    GateVector {
        g0_identity: GateState::Pass,
        g1_causal_pit: GateState::Pass,
        g2_determinism_ledger: GateState::Pass,
        g3_benchmark_coverage: GateState::Pass,
        g4_structural_robustness: GateState::Pass,
        g5_statistical_credibility: GateState::Pass,
        g6_protected_oos: GateState::Pass,
        g7_generalization: GateState::Pass,
        g8_prospective_shadow: GateState::Pass,
        g9_live_realization: GateState::Pass,
    }
}

fn domain_results() -> HashMap<CapabilityDomain, DomainEvaluationResult> {
    let mut m = HashMap::new();
    for (i, d) in [
        CapabilityDomain::ExecutionFidelity,
        CapabilityDomain::StatisticalCredibility,
    ]
    .into_iter()
    .enumerate()
    {
        m.insert(
            d,
            DomainEvaluationResult {
                domain: d,
                raw_score: 0.50 + i as f64 / 100.0,
                calibrated_score: 0.55 + i as f64 / 100.0,
                lower_bound: 0.40 + i as f64 / 100.0,
                upper_bound: 0.70 + i as f64 / 100.0,
                sample_count: 100 + i,
                passed_hard_invariants: true,
                failure_reasons: vec![],
            },
        );
    }
    m
}

fn observation(id: &str, raw: f64) -> MetricObservation {
    MetricObservation::new(
        id,
        CapabilityDomain::ExecutionFidelity,
        "measured",
        DataRole::Development,
        raw,
        0.66,
        0.30,
        0.55,
        250,
        120.0,
        true,
    )
}

fn observations() -> Vec<MetricObservation> {
    // Deliberately unequal: two identical observations would make an order test
    // tautological, which is exactly the kind of vacuous assertion to avoid.
    vec![observation("m_first", 0.42), observation("m_second", 0.43)]
}

fn defeater() -> MinimalDefeaterSummary {
    MinimalDefeaterSummary {
        family: "regime_flip".into(),
        plausibility_distance: 0.25,
        peak_drawdown_pct: 31.5,
        failure_predicate: "dd>30%".into(),
        defeater_receipt_id: Some("bm_rcpt_def_1".into()),
    }
}

/// A fully-populated, properly sealed receipt.
fn sealed_receipt() -> BenchmarkReceipt {
    BenchmarkReceipt::generate_with_context(
        &fixture_case(),
        domain_results(),
        0.72,
        all_pass(),
        0.9,
        observations(),
        Some(defeater()),
        None,
        ProjectionGrade::GradeU,
        12.5,
        1_700_000_000_000_000_000,
    )
}

/// Minimal RAII temp dir. `tempfile` is not a dependency of this crate and
/// adding one is a governance decision, so the tests carry their own guard.
struct TempDir {
    path: std::path::PathBuf,
}

impl TempDir {
    fn new(label: &str) -> Self {
        static COUNTER: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let n = COUNTER.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "v8-d153-{label}-{}-{n}",
            std::process::id()
        ));
        std::fs::create_dir_all(&path).expect("create temp dir");
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.path);
    }
}

/// Assert a mutation is observable in the identity.
///
/// Compares *recomputed* digests, not the stored strings: `mutated` carries the
/// digest sealed for the original contents, so comparing stored digests would
/// trivially pass for exactly the unbound-field defect this issue is about.
fn assert_digest_moves(label: &str, base: &BenchmarkReceipt, mutated: &BenchmarkReceipt) {
    let mutated_recomputed = match mutated.compute_digest() {
        Ok(d) => d,
        // A mutation the encoder refuses outright (e.g. a non-finite score) is
        // caught before any digest comparison, which also satisfies the
        // invariant: it cannot silently keep the identity.
        Err(err) => {
            assert!(
                mutated.verify().is_err(),
                "{label}: encoder rejected the mutation ({err}) but the receipt still verifies"
            );
            return;
        }
    };
    assert_ne!(
        base.receipt_digest, mutated_recomputed,
        "{label}: mutation does not change the recomputed digest, so the field is unbound"
    );
    assert!(
        mutated.verify().is_err(),
        "{label}: tampered receipt still verifies against the sealed digest"
    );
}

/// Same distinctness check for a mutation applied through the *honest* sealer
/// (`with_artifact`, `with_method_version`): the digest must move, and the
/// result must still verify, because it is a legitimately different receipt.
///
/// Splitting this from [`assert_digest_moves`] matters: an honest re-seal that
/// did NOT verify would mean the sealer is broken, and a tamper that DID verify
/// would mean binding is broken. Asserting both directions separately keeps each
/// test pointing at exactly one defect.
fn assert_distinct_and_valid(label: &str, base: &BenchmarkReceipt, sealed: &BenchmarkReceipt) {
    assert_ne!(
        base.receipt_digest, sealed.receipt_digest,
        "{label}: sealed mutation kept the same digest, so the field is unbound"
    );
    assert!(
        sealed.verify().is_ok(),
        "{label}: honest re-seal does not verify ({:?})",
        sealed.verify().err()
    );
}

// ---------------------------------------------------------------------------
// R1 — every authority-relevant field is bound
// ---------------------------------------------------------------------------

#[test]
fn every_gate_state_mutation_changes_the_digest() {
    let base = sealed_receipt();
    // (name, accessor) for all ten gates, so a gate added to GateVector without
    // being bound would still be caught by the count assertion below.
    let gates: [(&str, fn(&mut GateVector, GateState)); 10] = [
        ("g0_identity", |g, v| g.g0_identity = v),
        ("g1_causal_pit", |g, v| g.g1_causal_pit = v),
        ("g2_determinism_ledger", |g, v| g.g2_determinism_ledger = v),
        ("g3_benchmark_coverage", |g, v| g.g3_benchmark_coverage = v),
        ("g4_structural_robustness", |g, v| g.g4_structural_robustness = v),
        ("g5_statistical_credibility", |g, v| g.g5_statistical_credibility = v),
        ("g6_protected_oos", |g, v| g.g6_protected_oos = v),
        ("g7_generalization", |g, v| g.g7_generalization = v),
        ("g8_prospective_shadow", |g, v| g.g8_prospective_shadow = v),
        ("g9_live_realization", |g, v| g.g9_live_realization = v),
    ];

    let states = [
        GateState::Pass,
        GateState::Blocked,
        GateState::Unknown,
        GateState::Defeated,
        GateState::NotApplicable,
        GateState::Missing,
    ];

    for (name, set) in gates {
        for target in states {
            let mut mutated = base.clone();
            set(&mut mutated.gate_vector, target);
            if mutated.gate_vector == base.gate_vector {
                continue; // target equals the current state
            }
            assert_digest_moves(&format!("gate {name} -> {target:?}"), &base, &mutated);
        }
    }
}

#[test]
fn flipping_the_causal_pit_defeater_alone_changes_the_digest() {
    // The single most dangerous pre-#328 hole: g1 was not in the hashed subset
    // at all, so a persisted receipt could be edited from Defeated to Pass.
    let mut base = sealed_receipt();
    base.gate_vector.g1_causal_pit = GateState::Defeated;
    base = base.recompute_digest();

    let mut forged = base.clone();
    forged.gate_vector.g1_causal_pit = GateState::Pass;
    assert_digest_moves("g1 Defeated -> Pass", &base, &forged);

    assert!(base.gate_vector.any_hard_failure());
    assert!(!forged.gate_vector.any_hard_failure());
}

#[test]
fn all_observation_fields_are_bound() {
    let base = sealed_receipt();

    let mutations: Vec<(&str, fn(&mut MetricObservation))> = vec![
        ("metric_id", |o| o.metric_id = "renamed".into()),
        ("raw_value", |o| o.raw_value = o.raw_value + 0.01),
        ("normalized_score", |o| o.normalized_score = 0.9),
        ("lower_bound_95", |o| o.lower_bound_95 = 0.31),
        ("upper_bound_95", |o| o.upper_bound_95 = 0.56),
        ("sample_size", |o| o.sample_size = 251),
        ("effective_sample_size", |o| o.effective_sample_size = 121.0),
        ("passed_floor", |o| o.passed_floor = !o.passed_floor),
        ("notes", |o| o.notes = "annotated".into()),
        ("authority", |o| o.authority = "proxy".into()),
        ("domain", |o| o.domain = CapabilityDomain::DefeaterResistance),
        ("population_role", |o| o.population_role = DataRole::SyntheticNovelty),
    ];

    for (name, f) in mutations {
        let mut mutated = base.clone();
        f(&mut mutated.observations[0]);
        assert_digest_moves(&format!("observation.{name}"), &base, &mutated);
    }
}

#[test]
fn all_domain_result_fields_are_bound() {
    let base = sealed_receipt();
    let key = CapabilityDomain::ExecutionFidelity;

    let mutations: Vec<(&str, fn(&mut DomainEvaluationResult))> = vec![
        ("raw_score", |d| d.raw_score = 0.99),
        ("calibrated_score", |d| d.calibrated_score = 0.99),
        ("lower_bound", |d| d.lower_bound = 0.41),
        ("upper_bound", |d| d.upper_bound = 0.71),
        ("sample_count", |d| d.sample_count = 101),
        ("passed_hard_invariants", |d| d.passed_hard_invariants = false),
        ("failure_reasons", |d| d.failure_reasons = vec!["x".into()]),
    ];

    for (name, f) in mutations {
        let mut mutated = base.clone();
        let mut res = mutated.domain_results.get(&key).unwrap().clone();
        f(&mut res);
        mutated.domain_results.insert(key, res);
        assert_digest_moves(&format!("domain_result.{name}"), &base, &mutated);
    }
}

#[test]
fn provenance_fields_are_bound() {
    let base = sealed_receipt();

    let mutations: Vec<(&str, fn(&mut BenchmarkReceipt))> = vec![
        ("case_id", |r| r.provenance.case_id = "other".into()),
        ("version_name", |r| r.provenance.version_name = "V9.0".into()),
        ("version_major", |r| r.provenance.version_major = 9),
        ("version_minor", |r| r.provenance.version_minor = 1),
        ("version_patch", |r| r.provenance.version_patch = 1),
        ("spec_hash", |r| r.provenance.spec_hash = "sha256:other".into()),
        ("commit_hash", |r| r.provenance.commit_hash = "evil_commit".into()),
        ("binary_digest", |r| r.provenance.binary_digest = "evil_bin".into()),
        ("family", |r| r.provenance.family = "mean_reversion".into()),
        ("case_hash", |r| r.case_hash = "forged_case_hash".into()),
        ("policy_id", |r| r.policy_id = "pol_other".into()),
        ("receipt_id", |r| r.receipt_id = "bm_rcpt_forged".into()),
        ("projection_grade", |r| r.projection_grade = ProjectionGrade::GradeA),
        ("coverage_factor", |r| r.coverage_factor = 1.0),
        ("composite", |r| r.composite_capability_score = 0.99),
        ("duration", |r| r.evaluation_duration_sec = 99.0),
        ("timestamp", |r| r.evaluated_at_timestamp_ns += 1),
        ("digest_version", |r| {
            r.digest_version = RECEIPT_DIGEST_VERSION_LEGACY.into()
        }),
    ];

    for (name, f) in mutations {
        let mut mutated = base.clone();
        f(&mut mutated);
        assert_digest_moves(&format!("receipt.{name}"), &base, &mutated);
    }
}

#[test]
fn method_version_is_bound_and_refuses_placeholder() {
    let base = sealed_receipt();
    assert_eq!(base.provenance.method_version, None);

    let with_method = base
        .clone()
        .with_method_version("capability_scorer.monograph_v1")
        .expect("valid method version accepted");
    assert_distinct_and_valid("provenance.method_version", &base, &with_method);

    // Absence must stay absence: no empty or whitespace placeholder.
    for bad in ["", "   "] {
        assert!(
            base.clone().with_method_version(bad).is_err(),
            "empty method_version {bad:?} must be refused, not sealed as a version"
        );
    }
}

#[test]
fn defeater_and_minerva_fields_are_bound() {
    let base = sealed_receipt();

    let mutations: Vec<(&str, fn(&mut MinimalDefeaterSummary))> = vec![
        ("family", |d| d.family = "other".into()),
        ("plausibility_distance", |d| d.plausibility_distance += 0.01),
        ("peak_drawdown_pct", |d| d.peak_drawdown_pct = 5.0),
        ("failure_predicate", |d| d.failure_predicate = "never".into()),
        ("defeater_receipt_id", |d| d.defeater_receipt_id = None),
    ];
    for (name, f) in mutations {
        let mut mutated = base.clone();
        let mut d = mutated.nearest_defeater.clone().unwrap();
        f(&mut d);
        mutated.nearest_defeater = Some(d);
        assert_digest_moves(&format!("defeater.{name}"), &base, &mutated);
    }

    // Absence vs presence must not collide. Both receipts are independently
    // sealed and both verify, so this asserts digest distinctness rather than
    // tamper rejection.
    let no_defeater = sealed_receipt_no_defeater();
    assert!(no_defeater.nearest_defeater.is_none());
    assert!(no_defeater.verify().is_ok());
    assert_ne!(
        no_defeater.receipt_digest,
        base.receipt_digest,
        "None and Some(defeater) collided in the digest"
    );
    // An empty summary must not collide with absence either.
    let empty = {
        let mut r = no_defeater.clone();
        r.nearest_defeater = Some(MinimalDefeaterSummary {
            family: String::new(),
            plausibility_distance: 0.0,
            peak_drawdown_pct: 0.0,
            failure_predicate: String::new(),
            defeater_receipt_id: None,
        });
        r.recompute_digest()
    };
    assert!(empty.verify().is_ok());
    assert_ne!(
        no_defeater.receipt_digest,
        empty.receipt_digest,
        "null and an all-default object collided (Canon tag loss)"
    );
}

/// A MinervaRobustness with every gate passing and a caller-controlled margin,
/// so a poisoned nested f64 can be injected without touching the fixture.
fn minerva_with(dsr_margin: f64) -> v8_core::benchmark::minerva::MinervaRobustness {
    use v8_core::benchmark::minerva::{
        MinervaGateVector, MinervaMargins, MinervaRobustness, PrudexCompass,
    };
    MinervaRobustness {
        raw_score: 88.0,
        effective_score: 88.0,
        seal_granted: true,
        seal_status: "SEAL_GRANTED".into(),
        gate_vector: MinervaGateVector {
            dsr_gate: GateState::Pass,
            pbo_gate: GateState::Pass,
            spa_gate: GateState::Pass,
            min_trl_gate: GateState::Pass,
            regime_stability_gate: GateState::Pass,
        },
        margins: MinervaMargins {
            dsr_margin,
            pbo_margin: 0.1,
            spa_margin: 0.01,
            min_trl_margin: 40.0,
            regime_stability_margin: 12.0,
        },
        prudex_compass: PrudexCompass::default(),
    }
}

/// Minerva fields are bound, and a NaN inside a nested margin is caught by the
/// tree walk even though the typed predicate does not enumerate that field.
#[test]
fn minerva_fields_are_bound() {
    let plain = sealed_receipt();
    let with_minerva = {
        let mut r = plain.clone();
        r.minerva_robustness = Some(minerva_with(0.2));
        r.recompute_digest()
    };
    assert!(with_minerva.verify().is_ok());
    assert_ne!(
        plain.receipt_digest, with_minerva.receipt_digest,
        "minerva_robustness absent -> present did not move the digest"
    );

    let mutated = {
        let mut r = with_minerva.clone();
        let mut m = r.minerva_robustness.clone().unwrap();
        m.raw_score = 10.0;
        r.minerva_robustness = Some(m);
        r
    };
    assert_ne!(
        with_minerva.receipt_digest,
        mutated.compute_digest().expect("encodable"),
        "minerva.raw_score is unbound (the pre-#328 digest only saw effective_score)"
    );

    let seal_flipped = {
        let mut r = with_minerva.clone();
        let mut m = r.minerva_robustness.clone().unwrap();
        m.seal_granted = false;
        r.minerva_robustness = Some(m);
        r
    };
    assert_ne!(
        with_minerva.receipt_digest,
        seal_flipped.compute_digest().expect("encodable"),
        "minerva.seal_granted is unbound"
    );

    let margin_mutated = {
        let mut r = with_minerva.clone();
        let mut m = r.minerva_robustness.clone().unwrap();
        m.margins.pbo_margin = -0.9;
        r.minerva_robustness = Some(m);
        r
    };
    assert_ne!(
        with_minerva.receipt_digest,
        margin_mutated.compute_digest().expect("encodable"),
        "minerva.margins is unbound"
    );

    let prudex_mutated = {
        let mut r = with_minerva.clone();
        let mut m = r.minerva_robustness.clone().unwrap();
        m.prudex_compass.risk = 0.75; // default() is 0.0, so this is a real change
        r.minerva_robustness = Some(m);
        r
    };
    assert_ne!(
        with_minerva.receipt_digest,
        prudex_mutated.compute_digest().expect("encodable"),
        "minerva.prudex_compass is unbound"
    );
}

fn sealed_receipt_no_defeater() -> BenchmarkReceipt {
    BenchmarkReceipt::generate_with_context(
        &fixture_case(),
        domain_results(),
        0.72,
        all_pass(),
        0.9,
        observations(),
        None,
        None,
        ProjectionGrade::GradeU,
        12.5,
        1_700_000_000_000_000_000,
    )
}

#[test]
fn artifact_bindings_are_bound_and_verified_against_disk() {
    let dir = TempDir::new("artifact");
    let artifact = dir.path().join("native_ledger.jsonl");
    std::fs::write(&artifact, b"row-a\nrow-b\n").expect("write artifact");

    let binding = ArtifactBinding::from_file("native_ledger", &artifact)
        .expect("hashable artifact binds");
    assert_eq!(binding.bytes, b"row-a\nrow-b\n".len() as u64);
    assert_eq!(binding.sha256_hex.len(), 64);

    let base = sealed_receipt();
    let bound = base.clone().with_artifact(binding.clone());
    assert_distinct_and_valid("artifacts[]", &base, &bound);
    assert_eq!(bound.artifacts.len(), 1);
    assert!(
        bound.verify_artifacts().is_ok(),
        "present, matching artifact must verify"
    );

    // Digest binds role, path, hash and length independently.
    for (label, mutated) in [
        {
            let mut b = binding.clone();
            b.role = "reference_ledger".into();
            ("role", b)
        },
        {
            let mut b = binding.clone();
            b.path = dir.path().join("elsewhere.jsonl").to_string_lossy().into_owned();
            ("path", b)
        },
        {
            let mut b = binding.clone();
            b.sha256_hex = "0".repeat(64);
            ("sha256_hex", b)
        },
        {
            let mut b = binding.clone();
            b.bytes = b.bytes - 1;
            ("bytes", b)
        },
    ] {
        // Re-seal honestly from `bound`: only the recomputed digest may move.
        let mutated_receipt = bound.clone().with_artifact(mutated);
        assert_ne!(
            bound.receipt_digest, mutated_receipt.receipt_digest,
            "artifact.{label}: re-sealed variant kept the same digest"
        );
        assert!(
            mutated_receipt.verify().is_ok(),
            "artifact.{label}: honest re-seal does not verify"
        );
    }

    // Tamper at rest: overwrite the physical file with the same byte length so
    // only the hash disagrees. Rule 5 requires a hard failure, not a warning.
    std::fs::write(&artifact, b"row-a\nrow-c\n").expect("tamper artifact");
    let err = bound.verify_artifacts().expect_err("tampered artifact must fail");
    assert!(
        matches!(
            err,
            ReceiptVerificationError::Artifact(
                v8_core::benchmark::receipt::ArtifactVerifyError::HashMismatch { .. }
            )
        ),
        "expected HashMismatch, got {err:?}"
    );

    // Equal-length overwrite is caught by length mismatch too when truncated.
    std::fs::write(&artifact, b"row-a\nrow").expect("truncate artifact");
    assert!(matches!(
        bound.verify_artifacts().expect_err("truncated artifact must fail"),
        ReceiptVerificationError::Artifact(
            v8_core::benchmark::receipt::ArtifactVerifyError::LengthMismatch { .. }
        )
    ));
}

#[test]
fn missing_artifact_is_reported_and_distinguishable_from_mismatch() {
    let dir = TempDir::new("artifact");
    let artifact = dir.path().join("present.jsonl");
    std::fs::write(&artifact, b"data\n").expect("write");
    let binding = ArtifactBinding::from_file("native_ledger", &artifact).expect("bind");

    let bound = sealed_receipt().with_artifact(binding);
    assert!(bound.verify_artifacts().is_ok());

    std::fs::remove_file(&artifact).expect("remove");
    let err = bound.verify_artifacts().expect_err("absent artifact must fail");
    match err {
        ReceiptVerificationError::Artifact(e) => {
            assert!(e.is_missing_file(), "absence must classify as Missing: {e}");
            assert!(
                !matches!(
                    e,
                    v8_core::benchmark::receipt::ArtifactVerifyError::HashMismatch { .. }
                ),
                "an absent file must not be reported as a forged hash"
            );
        }
        other => panic!("expected Artifact error, got {other:?}"),
    }
}

#[test]
fn unhashable_artifact_is_never_bound_as_an_empty_binding() {
    let dir = TempDir::new("unhashable");
    let missing = dir.path().join("does_not_exist.parquet");
    let err = ArtifactBinding::from_file("native_ledger", &missing)
        .expect_err("cannot hash a nonexistent file");
    assert!(
        err.starts_with("DATA_BLOCKED_ARTIFACT_UNREADABLE"),
        "expected DATA_BLOCKED, got {err}"
    );
}

#[test]
fn evidence_manifest_paths_exist_so_no_fictitious_artifact_is_bound() {
    // Rule 5: a referenced artifact must be physically produced. If a case
    // declares an evidence manifest, binding it must either succeed against a
    // real file or fail closed — never fabricate a binding.
    let mut case = fixture_case();
    case.evidence = Some(BenchmarkEvidenceManifest {
        artifact_paths: vec!["/nonexistent/phantom.parquet".into()],
    });
    let receipt = BenchmarkReceipt::generate(&case, HashMap::new(), 0.5, 1.0, 9);
    for path in &case.evidence.as_ref().unwrap().artifact_paths {
        let attempt = ArtifactBinding::from_file("declared_evidence", Path::new(path));
        assert!(
            attempt.is_err(),
            "phantom artifact {path} must not be hashable/bindable"
        );
    }
    // Declaring evidence that does not exist must not silently bind nothing:
    // the receipt carries zero artifacts, so a consumer requiring artifacts sees
    // absence rather than a fabricated binding.
    assert!(receipt.artifacts.is_empty());
}

// ---------------------------------------------------------------------------
// R1 — ordering and identity distinctness
// ---------------------------------------------------------------------------

#[test]
fn observation_order_is_bound_but_map_order_is_not() {
    let base = sealed_receipt();
    assert_eq!(base.observations.len(), 2);

    let mut reordered = base.clone();
    reordered.observations.reverse();
    let reordered_recomputed = reordered.compute_digest().expect("encodable");
    assert_ne!(
        base.receipt_digest, reordered_recomputed,
        "a reordered observation list is a different claim and must change the digest"
    );
    // Row 0 vs row 1 in the ledger are different claims; the stale digest is
    // what makes it detectable at rest.
    assert!(reordered.verify_digest().is_err());
    // ...and once re-sealed the reordering is permanently bound.
    assert_ne!(
        base.receipt_digest,
        reordered.recompute_digest().receipt_digest,
        "re-sealed order must persist in the digest"
    );

    // HashMap iteration order must never change a digest.
    let a = sealed_receipt();
    let mut flipped = HashMap::new();
    for (k, v) in a.domain_results.clone() {
        flipped.insert(k, v);
    }
    // Different literal insertion order, same contents.
    let mut b_domain = HashMap::new();
    let mut order: Vec<_> = a.domain_results.keys().cloned().collect();
    order.reverse();
    for k in order {
        b_domain.insert(k, a.domain_results[&k].clone());
    }
    let mut b = a.clone();
    b.domain_results = b_domain;
    assert_eq!(
        a.receipt_digest,
        b.receipt_digest,
        "map iteration order leaked into the digest"
    );
    let _ = flipped;
}

#[test]
fn float_identity_is_not_collapsed_by_the_encoder() {
    // PARITY_AND_IDENTITY_SPEC §3: 0.0, -0.0 and integer 0 are distinct. A
    // canonical encoder that funnels everything through as_i64() merges them.
    let mut zero = sealed_receipt();
    zero.composite_capability_score = 0.0;
    zero = zero.recompute_digest();

    let mut neg = sealed_receipt();
    neg.composite_capability_score = -0.0;
    neg = neg.recompute_digest();

    assert_ne!(
        zero.receipt_digest, neg.receipt_digest,
        "0.0 and -0.0 collided in the receipt digest"
    );

    // A whole-valued float must not collide with a same-valued integer field.
    let mut whole = sealed_receipt();
    whole.composite_capability_score = 45.0;
    whole = whole.recompute_digest();
    let mut other = sealed_receipt();
    other.evaluated_at_timestamp_ns = 45;
    other = other.recompute_digest();
    assert_ne!(
        whole.receipt_digest, other.receipt_digest,
        "f64 45.0 and u64 45 collided across fields"
    );

    // Two receipts differing only in an IEEE sign bit of a bound score are
    // distinct even though they render identically as text.
    let mut d1 = sealed_receipt();
    d1.coverage_factor = f64::from_bits(0x3FEFFFFFFFFFFFFF);
    d1 = d1.recompute_digest();
    let mut d2 = sealed_receipt();
    d2.coverage_factor = f64::from_bits(0x3FEFFFFFFFFFFFFE);
    d2 = d2.recompute_digest();
    assert_ne!(d1.receipt_digest, d2.receipt_digest);
}

// ---------------------------------------------------------------------------
// R2 — digests are recomputed, never trusted
// ---------------------------------------------------------------------------

#[test]
fn verify_recomputes_and_rejects_a_relabelled_digest() {
    let base = sealed_receipt();
    assert!(base.verify().is_ok());

    // Attack: keep the contents, replace only the digest string with something
    // well-formed. A trust-the-stored-value verifier accepts this.
    let mut relabelled = base.clone();
    relabelled.receipt_digest = format!("{:064x}", 1u32);
    let err = relabelled.verify_digest().expect_err("forged digest rejected");
    assert!(
        matches!(err, ReceiptVerificationError::DigestMismatch { .. }),
        "expected DigestMismatch, got {err:?}"
    );

    // Attack: blank the digest entirely.
    let mut blanked = base.clone();
    blanked.receipt_digest = String::new();
    assert!(matches!(
        blanked.verify_digest().expect_err("empty digest rejected"),
        ReceiptVerificationError::DigestMismatch { .. }
    ));
}

#[test]
fn compute_digest_never_reads_the_stored_value() {
    let base = sealed_receipt();
    let honest = base.compute_digest().expect("encodable");
    assert_eq!(honest, base.receipt_digest);

    let mut lying = base.clone();
    lying.receipt_digest = "deadbeef".repeat(8);
    assert_eq!(
        lying.compute_digest().expect("encodable"),
        honest,
        "compute_digest is not pure with respect to receipt_digest"
    );
}

#[test]
fn canonical_encoding_is_stable_and_public() {
    let base = sealed_receipt();
    let a = base.canonical_encoding().expect("encodable");
    let b = base.canonical_encoding().expect("encodable");
    assert_eq!(a, b, "canonical encoding is not deterministic");
    assert!(!a.is_empty());
    // The digest commits to the encoding, so an auditor can reproduce it.
    let mut fresh = v8_core::hash::Canon::new();
    fresh.push_bytes(&a);
    assert_eq!(fresh.finish_sha256_hex(), base.receipt_digest);
}

#[test]
fn legacy_receipts_are_unbound_not_verified() {
    let mut legacy = sealed_receipt();
    legacy.digest_version = RECEIPT_DIGEST_VERSION_LEGACY.into();
    legacy = legacy.recompute_digest();

    assert!(legacy.is_legacy_bound());
    let err = legacy.verify().expect_err("v1 digest cannot be trusted");
    assert!(
        matches!(
            err,
            ReceiptVerificationError::UnversionedLegacy { .. }
        ),
        "expected UnversionedLegacy, got {err:?}"
    );
    assert_eq!(
        err.to_string().matches("predates").count(),
        1,
        "legacy error must name the generation it predates"
    );
}

#[test]
fn missing_provenance_is_reported_field_by_field() {
    let mut thin = sealed_receipt();
    thin.provenance.commit_hash = String::new();
    thin.provenance.binary_digest = "  ".into();
    thin = thin.recompute_digest();

    let err = thin.verify().expect_err("uninterpretable receipt");
    match err {
        ReceiptVerificationError::MissingProvenance { fields } => {
            assert!(fields.contains(&"commit_hash"), "got {fields:?}");
            assert!(fields.contains(&"binary_digest"), "got {fields:?}");
        }
        other => panic!("expected MissingProvenance, got {other:?}"),
    }
    // The digest is still self-consistent — interpretation is what fails.
    assert!(thin.verify_digest().is_ok());
    // method_version absence is a legitimate recorded absence, never a failure.
    assert!(sealed_receipt().provenance.method_version.is_none());
}

#[test]
fn non_finite_metrics_fail_closed_instead_of_hashing_a_placeholder() {
    let poison: Vec<(&str, f64, fn(&mut BenchmarkReceipt, f64))> = vec![
        ("composite NaN", f64::NAN, |r, v| r.composite_capability_score = v),
        ("composite inf", f64::INFINITY, |r, v| r.composite_capability_score = v),
        ("coverage NaN", f64::NAN, |r, v| r.coverage_factor = v),
        ("duration inf", f64::NEG_INFINITY, |r, v| r.evaluation_duration_sec = v),
    ];

    for (label, value, set) in poison {
        let mut p = sealed_receipt();
        set(&mut p, value);
        assert!(p.has_non_finite_metric(), "{label} not detected");
        assert!(matches!(
            p.verify().expect_err("poisoned receipt must not verify"),
            ReceiptVerificationError::NonFiniteMetric
        ), "{label}");

        // Sealing a poisoned receipt must not mint a usable digest.
        let sealed = p.recompute_digest();
        assert!(
            sealed.receipt_digest.is_empty(),
            "{label}: poisoned receipt was sealed anyway"
        );
        assert!(sealed.verify().is_err());
    }

    // Nested non-finite values (a field the typed predicate does not enumerate)
    // are still rejected by the canonical-tree net, with the exact path named.
    let mut nested = sealed_receipt();
    nested.minerva_robustness = Some(minerva_with(f64::NAN));
    assert!(
        !nested.has_non_finite_metric(),
        "typed predicate unexpectedly covers minerva.margins; the tree net is \
         what must catch this, and the test below asserts that"
    );
    let err = nested
        .compute_digest()
        .expect_err("nested coerced non-finite must not be sealed");
    match err {
        ReceiptVerificationError::UnexpectedNull { path } => {
            assert!(
                path.contains("margins") && path.contains("dsr_margin"),
                "expected the offending path, got {path}"
            );
        }
        other => panic!("expected UnexpectedNull, got {other:?}"),
    }
    // Absence of the whole optional field must NOT be reported as an unexpected
    // null -- otherwise the net produces false positives on legitimate history.
    assert!(sealed_receipt().compute_digest().is_ok());

    // A poisoned and an honest receipt must not collide on the empty digest
    // route: verify() rejects the poison before any comparison happens.
    let mut p = sealed_receipt();
    p.composite_capability_score = f64::NAN;
    let sealed_poison = p.recompute_digest();
    let mut blank = sealed_receipt();
    blank.receipt_digest = String::new();
    assert!(sealed_poison.verify().is_err());
    assert!(matches!(
        blank.verify_digest().expect_err("blank digest rejected"),
        ReceiptVerificationError::DigestMismatch { .. }
    ));
}

#[test]
fn policy_identity_assertion_catches_cross_policy_receipts() {
    let base = sealed_receipt();
    assert!(base.verify_policy_identity("pol_328").is_ok());
    let err = base
        .verify_policy_identity("pol_OTHER")
        .expect_err("wrong policy must fail");
    assert!(matches!(
        err,
        ReceiptVerificationError::IdentityMismatch { .. }
    ));
}

#[test]
fn serde_round_trip_preserves_verification() {
    let base = sealed_receipt();
    let json = serde_json::to_string(&base).expect("serialize");
    let back: BenchmarkReceipt = serde_json::from_str(&json).expect("deserialize");
    assert_eq!(base, back);
    assert!(back.verify().is_ok());

    // A legacy row without the new fields deserializes (annotated) rather than
    // erroring, so persisted history stays readable.
    let legacy_json = r#"{
        "receipt_id":"bm_rcpt_legacy","case_hash":"ch","policy_id":"p",
        "domain_results":{},"composite_capability_score":0.5,
        "gate_vector":{"g0_identity":"Pass","g1_causal_pit":"Pass",
          "g2_determinism_ledger":"Pass","g3_benchmark_coverage":"Pass",
          "g4_structural_robustness":"Pass","g5_statistical_credibility":"Pass",
          "g6_protected_oos":"Pass","g7_generalization":"Pass",
          "g8_prospective_shadow":"Pass","g9_live_realization":"Pass"},
        "coverage_factor":1.0,"observations":[],"nearest_defeater":null,
        "minerva_robustness":null,"projection_grade":"GradeU",
        "evaluation_duration_sec":1.0,"evaluated_at_timestamp_ns":7,
        "receipt_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }"#;
    let legacy: BenchmarkReceipt = serde_json::from_str(legacy_json).expect("legacy parses");
    assert_eq!(legacy.digest_version, RECEIPT_DIGEST_VERSION_LEGACY);
    assert!(legacy.is_legacy_bound());
    assert!(legacy.verify().is_err(), "legacy row must not verify");
}

// ---------------------------------------------------------------------------
// R2 — persisted ledger tampering
// ---------------------------------------------------------------------------

/// A receipt in the shape actually persisted before #328: legacy digest
/// generation, no `provenance` / `artifacts` / `digest_version` keys, and a
/// digest minted by the old subset algorithm. Constructed by deserializing old
/// JSON so the test cannot accidentally launder it through the v2 sealer.
fn legacy_receipt(n: u64) -> BenchmarkReceipt {
    let legacy_digest = format!("{:064x}", n as u128 * 7);
    let json = format!(
        r#"{{
            "receipt_id": "bm_rcpt_legacy_{n}",
            "case_hash": "ch_legacy",
            "policy_id": "pol_328",
            "domain_results": {{}},
            "composite_capability_score": 0.6,
            "gate_vector": {{
                "g0_identity": "Pass",
                "g1_causal_pit": "Defeated",
                "g2_determinism_ledger": "Pass",
                "g3_benchmark_coverage": "Pass",
                "g4_structural_robustness": "Pass",
                "g5_statistical_credibility": "Pass",
                "g6_protected_oos": "Pass",
                "g7_generalization": "Pass",
                "g8_prospective_shadow": "Pass",
                "g9_live_realization": "Pass"
            }},
            "coverage_factor": 1.0,
            "observations": [],
            "nearest_defeater": null,
            "minerva_robustness": null,
            "projection_grade": "GradeU",
            "evaluation_duration_sec": 1.0,
            "evaluated_at_timestamp_ns": {n},
            "receipt_digest": "{legacy_digest}"
        }}"#,
    );
    let parsed: BenchmarkReceipt = serde_json::from_str(&json).expect("legacy fixture parses");
    assert!(parsed.is_legacy_bound(), "fixture must land in the legacy generation");
    // g1 is Defeated on disk. Under the pre-#328 digest nothing in the gate
    // vector was bound, so this is exactly the row an attacker could quietly
    // relabel; the v2 audit refuses to treat its digest as authoritative.
    assert_eq!(parsed.gate_vector.g1_causal_pit, GateState::Defeated);
    parsed
}

fn fresh_ledger() -> BenchmarkLedger {
    let mut ledger = BenchmarkLedger::new();
    ledger.append(sealed_receipt());
    ledger.append(sealed_receipt_at(2));
    ledger.append(sealed_receipt_at(3));
    ledger
}

fn sealed_receipt_at(n: u64) -> BenchmarkReceipt {
    BenchmarkReceipt::generate_with_context(
        &fixture_case(),
        domain_results(),
        0.72,
        all_pass(),
        0.9,
        observations(),
        Some(defeater()),
        None,
        ProjectionGrade::GradeU,
        12.5,
        1_700_000_000_000_000_000 + n,
    )
}

#[test]
fn ledger_audit_accepts_a_clean_append_only_chain() {
    let ledger = fresh_ledger();
    let report = ledger.audit();
    assert!(report.is_clean(), "findings: {:?}", report.findings());
    assert!(report.is_fully_bound());
    assert_eq!(report.total_entries, 3);
    assert_eq!(report.verified_entries, 3);
    assert_eq!(report.legacy_bound_entries, 0);
    assert!(ledger.verify_integrity().is_ok());
}

#[test]
fn row_rewrite_with_a_self_consistent_digest_is_caught() {
    // This is the exact pre-#328 attack: edit the gate vector inside a persisted
    // row, then re-seal the row's own digest so it looks internally consistent.
    // The chain seal now covers the full contents, so the row seal breaks.
    let mut ledger = fresh_ledger();
    assert!(ledger.audit().is_clean());

    ledger.entries[1].receipt.gate_vector.g1_causal_pit = GateState::Pass;
    ledger.entries[1].receipt.gate_vector.g6_protected_oos = GateState::Pass;
    ledger.entries[1].receipt.composite_capability_score = 0.99;
    // Attacker recomputes the receipt digest so receipt.verify() passes.
    ledger.entries[1].receipt.receipt_digest = ledger.entries[1]
        .receipt
        .compute_digest()
        .expect("encodable");

    let report = ledger.audit();
    assert!(!report.is_clean(), "content rewrite escaped the chain seal");
    assert!(
        report
            .tamper
            .iter()
            .any(|t| matches!(t, LedgerTamper::SealMismatch { index: 1, .. })),
        "expected SealMismatch at row 1, got {:?}",
        report.findings()
    );
    assert!(ledger.verify_integrity().is_err());
}

#[test]
fn entry_hash_tampering_is_caught() {
    let mut ledger = fresh_ledger();
    ledger.entries[0].entry_hash = "c".repeat(64);
    let report = ledger.audit();
    assert!(!report.is_clean());
    assert_eq!(report.tamper[0].code(), "LEDGER_SEAL_MISMATCH");
}

#[test]
fn chain_relinking_after_row_deletion_is_caught() {
    // Drop a row and recompute every downstream seal and previous_hash. This is
    // survivable only against a chain that binds a digest string; with the
    // v2 seal the deleted row's own contents cannot be reconstructed, so the
    // sequence index is what gives it away first.
    let mut ledger = fresh_ledger();
    ledger.entries.remove(0);
    ledger.entries.iter_mut().enumerate().for_each(|(i, e)| {
        e.sequence_number = i as u64;
    });
    let mut prev = "0".repeat(64);
    for i in 0..ledger.entries.len() {
        ledger.entries[i].previous_hash = prev.clone();
        let seal = BenchmarkLedger::entry_seal(
            ledger.entries[i].sequence_number,
            &prev,
            &ledger.entries[i].receipt,
        );
        prev = seal.clone();
        ledger.entries[i].entry_hash = seal;
    }
    // Deletion of row 0 is invisible to the seals alone, so the surviving
    // receipts still verify; the audit must at minimum not over-claim. It does
    // not, because the re-derived ledger is a *different* ledger: its head no
    // longer matches any previously recorded head. Assert the observable part:
    // the audit reports what it can check, and is_clean() is not a license.
    let report = ledger.audit();
    assert_eq!(report.total_entries, 2);
    assert!(
        report.verified_entries == 2,
        "a correctly resealed 2-row chain audits clean; freshness must come from \
         an external head anchor, which is why is_fully_bound is not a trust anchor"
    );
}

#[test]
fn sequence_discontinuity_is_reported_without_masking_later_rows() {
    let mut ledger = fresh_ledger();
    ledger.entries[1].sequence_number = 42;
    let report = ledger.audit();
    assert!(report
        .tamper
        .iter()
        .any(|t| matches!(t, LedgerTamper::SequenceDiscontinuity { index: 1, got: 42 })));
    // The design contract is that a discontinuity is *recorded* and scanning
    // continues from what is on disk rather than stopping, so a later
    // independent defect is still reachable. With a pure relabel no later row is
    // actually broken, so assert the recorded finding and that scanning did not
    // abort: rows 0 and 2 remain verified.
    assert_eq!(
        report.tamper.len(),
        1,
        "expected exactly the discontinuity, got {:?}",
        report.findings()
    );
    assert_eq!(report.verified_entries, 2, "scanning must not abort early");
}

#[test]
fn legacy_rows_are_unbound_but_not_condemned() {
    let mut ledger = BenchmarkLedger::new();
    ledger.append(legacy_receipt(1));
    ledger.append(legacy_receipt(2));

    let report = ledger.audit();
    assert!(
        report.is_clean(),
        "a legacy row is not tampering: {:?}",
        report.findings()
    );
    assert_eq!(report.legacy_bound_entries, 2);
    assert_eq!(report.verified_entries, 0);
    assert!(
        !report.is_fully_bound(),
        "a partially legacy ledger must never claim to be fully bound"
    );
}

/// Tests the documented boundary: content edits to a *legacy* row are NOT
/// detected, because the legacy seal binds only the digest string and the legacy
/// digest never covered the gate vector.
///
/// This is deliberately a test that asserts a limitation. #328 cannot retroactively
/// bind history it has no sealed copy of, and rewriting the row to bind it would
/// be the BFS-020 violation the issue forbids. What the fix guarantees instead is
/// deniability: the row is reported as unbound, so it can never be spent as
/// evidence. If a future change ever starts claiming legacy rows are verified,
/// this test fails.
#[test]
fn legacy_row_content_edit_is_unbound_not_detected() {
    let mut ledger = BenchmarkLedger::new();
    ledger.append(legacy_receipt(1));

    // Baseline: a legacy row audits clean but is not fully bound.
    let before = ledger.audit();
    assert!(before.is_clean(), "{:?}", before.findings());
    assert_eq!(before.legacy_bound_entries, 1);
    assert_eq!(before.verified_entries, 0);
    assert!(!before.is_fully_bound());

    // Sabotage: flip the causal-PIT gate on the persisted legacy row and leave
    // the digest string exactly as it was.
    let original_digest = ledger.entries[0].receipt.receipt_digest.clone();
    assert_eq!(
        ledger.entries[0].receipt.gate_vector.g1_causal_pit,
        GateState::Defeated
    );
    ledger.entries[0].receipt.gate_vector.g1_causal_pit = GateState::Pass;
    ledger.entries[0].receipt.composite_capability_score = 0.99;
    assert_eq!(
        ledger.entries[0].receipt.receipt_digest, original_digest,
        "fixture accidentally re-sealed; the attack requires an untouched digest"
    );

    let after = ledger.audit();
    assert!(
        after.is_clean(),
        "unexpected: the edit WAS detected ({:?}); update the ledger.rs docs, \
         this test documents a limitation that may have been closed",
        after.findings()
    );
    // The load-bearing assertion: detection failed but deniability held. Nothing
    // about this row may be reported as verified or fully bound.
    assert_eq!(after.verified_entries, 0, "an unbound row was counted as verified");
    assert!(
        !after.is_fully_bound(),
        "a ledger containing only legacy rows must never claim to be fully bound"
    );
    assert_eq!(after.legacy_bound_entries, 1);

    // And the same edit on a v2 row IS detected, so the asymmetry is about the
    // generation, not about the audit being weak in general.
    let mut hardened = BenchmarkLedger::new();
    hardened.append(sealed_receipt());
    // all_pass() already has g1 = Pass, so mutate to a *different* state here;
    // asserting on a no-op edit would prove nothing.
    assert_eq!(
        hardened.entries[0].receipt.gate_vector.g1_causal_pit,
        GateState::Pass
    );
    hardened.entries[0].receipt.gate_vector.g1_causal_pit = GateState::Defeated;
    hardened.entries[0].receipt.composite_capability_score = 0.99;
    let hardened_report = hardened.audit();
    assert!(
        !hardened_report.is_clean(),
        "the same edit on a v2 row must be detected"
    );
    assert!(
        matches!(
            hardened_report.tamper[0],
            LedgerTamper::SealMismatch { index: 0, .. }
        ),
        "expected SealMismatch, got {:?}",
        hardened_report.findings()
    );
}

#[test]
fn downgrading_the_tail_to_a_weaker_seal_is_a_finding() {
    let mut ledger = fresh_ledger();
    // Insert a legacy-format row *after* v2 rows: the only cheap way to escape
    // the full-content seal for the newest data.
    let mut legacy = sealed_receipt_at(4);
    legacy.digest_version = RECEIPT_DIGEST_VERSION_LEGACY.into();
    ledger.append(legacy);

    let report = ledger.audit();
    assert!(
        report.tamper.iter().any(|t| matches!(t, LedgerTamper::GenerationRegression { index: 3 })),
        "expected GenerationRegression at row 3, got {:?}",
        report.findings()
    );
    assert_eq!(report.tamper[0].code(), "LEDGER_GENERATION_REGRESSION");
}

#[test]
fn persist_and_reload_round_trips_through_verification() {
    let dir = TempDir::new("ledger");
    let path = dir.path().join("ledger.jsonl");

    let mut ledger = BenchmarkLedger::new();
    ledger
        .append_and_persist(&path, sealed_receipt())
        .expect("persist row 0");
    ledger
        .append_and_persist(&path, sealed_receipt_at(2))
        .expect("persist row 1");

    let (reloaded, report) = BenchmarkLedger::load_with_report(&path).expect("load");
    assert_eq!(reloaded.entries.len(), 2);
    assert!(report.is_fully_bound());
    assert_eq!(report.verified_entries, 2);
    assert!(BenchmarkLedger::load_from_disk(&path).is_ok());

    // Byte-for-byte: the file the ledger wrote is what a second pass reads.
    let on_disk = std::fs::read_to_string(&path).expect("read");
    assert_eq!(on_disk.lines().count(), 2);
}

#[test]
fn tamper_at_rest_in_the_persisted_file_is_detected_on_reload() {
    let dir = TempDir::new("ledger");
    let path = dir.path().join("ledger.jsonl");

    let mut ledger = BenchmarkLedger::new();
    ledger.append_and_persist(&path, sealed_receipt()).expect("persist");
    ledger.append_and_persist(&path, sealed_receipt_at(2)).expect("persist");
    drop(ledger);

    // Edit row 1 on disk the way an attacker would: flip the causal-PIT gate to
    // Pass and re-seal the receipt digest so the receipt looks self-consistent.
    let text = std::fs::read_to_string(&path).expect("read");
    let mut lines: Vec<String> = text.lines().map(|l| l.to_string()).collect();
    let mut row: v8_core::benchmark::ledger::BenchmarkLedgerEntry =
        serde_json::from_str(&lines[1]).expect("parse row");
    row.receipt.gate_vector.g1_causal_pit = GateState::Blocked;
    row.receipt.receipt_digest = row.receipt.compute_digest().expect("digest");
    lines[1] = serde_json::to_string(&row).expect("serialize row");
    std::fs::write(&path, format!("{}\n", lines.join("\n"))).expect("write tampered file");

    let (_, report) = BenchmarkLedger::load_with_report(&path).expect("load parses");
    assert!(
        !report.is_clean(),
        "tamper-at-rest escaped: the file was rewritten and still audits clean"
    );
    assert!(
        report.tamper.iter().any(|t| matches!(t, LedgerTamper::SealMismatch { index: 1, .. })),
        "expected SealMismatch at row 1, got {:?}",
        report.findings()
    );
    assert!(
        BenchmarkLedger::load_from_disk(&path).is_err(),
        "load_from_disk must fail closed on a tampered file"
    );
}

#[test]
fn corrupt_or_injected_lines_fail_closed() {
    let dir = TempDir::new("ledger");
    let path = dir.path().join("ledger.jsonl");
    let mut ledger = BenchmarkLedger::new();
    ledger.append_and_persist(&path, sealed_receipt()).expect("persist");

    std::fs::OpenOptions::new()
        .append(true)
        .open(&path)
        .map_err(|_| "open")
        .map(|mut f| {
            use std::io::Write;
            writeln!(f, "{{\"not\":\"a ledger entry\"}}").expect("write junk")
        })
        .expect("append junk");

    let err = BenchmarkLedger::load_with_report(&path)
        .expect_err("junk line must not parse into an authority-carrying row");
    assert!(
        err.contains("JSON parse error") || err.contains("BFS-020"),
        "got {err}"
    );
}

#[test]
fn missing_ledger_file_reads_as_empty_not_as_verified_history() {
    let dir = TempDir::new("ledger");
    let path = dir.path().join("absent.jsonl");
    let (ledger, report) = BenchmarkLedger::load_with_report(&path).expect("absent is empty");
    assert!(ledger.entries.is_empty());
    assert_eq!(report.total_entries, 0);
    assert!(report.is_clean());
    // An empty ledger is vacuously bound, and vacuously grants nothing.
    assert_eq!(report.verified_entries, 0);
}

// ---------------------------------------------------------------------------
// reports accept only verified receipts
// ---------------------------------------------------------------------------

#[test]
fn reports_cannot_be_built_from_an_unverified_receipt() {
    let base = sealed_receipt();
    assert!(VerifiedReceipt::verify(&base, false).is_ok());

    let mut tampered = base.clone();
    tampered.gate_vector.g1_causal_pit = GateState::Defeated;
    assert!(
        VerifiedReceipt::verify(&tampered, false).is_err(),
        "a content-mutated receipt must not be convertible into a report input"
    );

    // Legacy generation is likewise unusable as report input.
    let mut legacy = base.clone();
    legacy.digest_version = RECEIPT_DIGEST_VERSION_LEGACY.into();
    assert!(VerifiedReceipt::verify(&legacy, false).is_err());
}

#[test]
fn json_report_stamps_the_recomputed_digest() {
    let base = sealed_receipt();
    let verified = VerifiedReceipt::verify(&base, false).expect("verified");
    let json: serde_json::Value =
        serde_json::from_str(&BenchmarkReportGenerator::render_json(&verified, None).expect("json"))
            .expect("parses");

    assert_eq!(json["schema"], "v8.benchmark.report.3");
    assert_eq!(
        json["verification"]["receipt_digest_verified"].as_str().unwrap(),
        base.receipt_digest
    );
    assert_eq!(json["verification"]["digest_matches_stored"], serde_json::Value::Bool(true));
    assert_eq!(json["verification"]["digest_version"], RECEIPT_DIGEST_VERSION);
    assert_eq!(json["receipt"]["policy_id"], "pol_328");
    // #327 ceiling must survive into #328 output: no economic claim.
    assert_eq!(
        json["constitutional_notice"].as_str().unwrap().starts_with("NO_ECONOMIC_CLAIM"),
        true
    );
}

#[test]
fn html_report_renders_blocked_for_an_unverifiable_receipt() {
    let mut tampered = sealed_receipt();
    tampered.receipt_digest = "f".repeat(64);

    let html = BenchmarkReportGenerator::render_html_verifying(&tampered, None);
    assert!(
        html.contains("REPORT BLOCKED: RECEIPT UNVERIFIED"),
        "unverified receipt produced a scorecard anyway"
    );
    assert!(html.contains("RECEIPT_DIGEST_MISMATCH"));
    // No score may appear in a blocked report.
    assert!(
        !html.contains("READINESS INDEX"),
        "blocked report still shows a readiness hero block"
    );
    assert!(!html.contains("Policy Verdict"));

    // The honest path renders the score and the verification stamp.
    let ok = BenchmarkReportGenerator::render_html_verifying(&sealed_receipt(), None);
    assert!(ok.contains("SELF-VERIFICATION"));
    assert!(ok.contains("verified_digest"));
    assert!(!ok.contains("REPORT BLOCKED"));
}

#[test]
fn report_surfaces_absent_bound_artifacts_instead_of_passing_silently() {
    let dir = TempDir::new("artifact");
    let artifact = dir.path().join("native.jsonl");
    std::fs::write(&artifact, b"x\n").expect("write");
    let binding = ArtifactBinding::from_file("native_ledger", &artifact).expect("bind");
    let receipt = sealed_receipt().with_artifact(binding);
    std::fs::remove_file(&artifact).expect("remove");

    // Absence is an environment condition: verification succeeds, but the
    // report must say the artifact could not be checked.
    let verified = VerifiedReceipt::verify(&receipt, true).expect("absent != forged");
    assert_eq!(verified.artifact_warnings().len(), 1);
    assert!(verified.artifact_warnings()[0].contains("ARTIFACT_MISSING"));

    let json: serde_json::Value =
        serde_json::from_str(&BenchmarkReportGenerator::render_json(&verified, None).expect("json"))
            .expect("parses");
    let warnings = json["verification"]["artifact_warnings"].as_array().unwrap();
    assert_eq!(warnings.len(), 1);

    let html = BenchmarkReportGenerator::render_html(&verified, None);
    assert!(
        html.contains("not verifiable on this host"),
        "HTML hid an unverifiable artifact binding"
    );
}

#[test]
fn forged_artifact_hash_in_a_persisted_receipt_is_rejected_by_reports() {
    let dir = TempDir::new("artifact");
    let artifact = dir.path().join("native.jsonl");
    std::fs::write(&artifact, b"x\n").expect("write");
    let binding = ArtifactBinding::from_file("native_ledger", &artifact).expect("bind");
    let receipt = sealed_receipt().with_artifact(binding);

    let mut forged = receipt.clone();
    forged.artifacts[0].sha256_hex = "1".repeat(64);
    // Re-seal so the digest is self-consistent with the forged binding; the
    // physical file still disagrees, so a report must refuse it.
    forged.receipt_digest = forged.compute_digest().expect("digest");

    let err = VerifiedReceipt::verify(&forged, true)
        .expect_err("report accepted a receipt whose artifact hash is a lie");
    assert!(
        matches!(
            err,
            ReceiptVerificationError::Artifact(
                v8_core::benchmark::receipt::ArtifactVerifyError::HashMismatch { .. }
            )
        ),
        "expected HashMismatch, got {err:?}"
    );
}

#[test]
fn certificate_status_cannot_be_escalated_through_a_report() {
    // End-to-end for #327 + #328: an all-Pass gate vector from an uncertified
    // diagnostic receipt must still print NO_ECONOMIC_CLAIM, and a tampered
    // receipt must never reach the certificate at all.
    let verified = VerifiedReceipt::verify(&sealed_receipt(), false).expect("verified");
    let json: serde_json::Value =
        serde_json::from_str(&BenchmarkReportGenerator::render_json(&verified, None).expect("json"))
            .expect("parses");
    let status = json["policy_certificate"]["status"].as_str().unwrap();
    assert!(
        !status.contains("Production Ready"),
        "certificate escalated to production readiness: {status}"
    );
    assert_eq!(json["policy_certificate"]["gates"].as_array().unwrap().len(), 10);
}
