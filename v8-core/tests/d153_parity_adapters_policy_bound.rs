//! #329 — Policy-bound external parity adapters replace fixed vectors.
//!
//! The pre-#329 adapters could not fail: they compared two hardcoded arrays that
//! the same function wrote, under a tolerance chosen to contain them. A test that
//! only asserts "the new adapter agrees with itself" would be no stronger, so the
//! load-bearing tests here are the negative ones:
//!
//! - production evaluation has **no** fixed-vector path to call at all;
//! - an absent or unverifiable artifact yields `DataBlocked`, never a zero
//!   difference and never a pass (issue §13);
//! - changing policy, artifact, mapping or engine moves the identity, so a result
//!   cannot be re-labelled onto another subject (issue §13);
//! - no receipt outcome can raise economic authority (#329 R3, D-153 §2.1).
//!
//! Every fixture ledger is a physical file that the adapter re-hashes, so the
//! "data-backed" claim is exercised rather than described.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use v8_core::benchmark::case::BenchmarkEvidenceManifest;
use v8_core::benchmark::external::DisagreementDetector;
use v8_core::benchmark::parity::{
    check_method_version, EngineVersion, SemanticMapping, MAPPING_VERSION,
    NON_SOVEREIGN_INSTRUMENT_STATUS, PARITY_IDENTITY_VERSION, ParityAdapter, ParityOutcome,
    ParityReceipt, ParityRequest, ParitySubject, ReferenceEngine,
};
use v8_core::benchmark::receipt::{ArtifactBinding, BenchmarkReceipt};
use v8_core::benchmark::runner::BenchmarkRunner;
use v8_core::benchmark::types::{
    CapabilityDomain, EvaluationPopulation, GateState, GateVector, ProjectionGrade,
};
use v8_core::benchmark::{BenchmarkCase, BenchmarkVersion, PolicyTarget};

// ---------------------------------------------------------------------------
// temp dir guard (mirrors the #328 suite; tempfile is not a dependency)
// ---------------------------------------------------------------------------

struct TempDir {
    path: PathBuf,
}

impl TempDir {
    fn new(label: &str) -> Self {
        static COUNTER: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let n = COUNTER.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "v8-d153-329-{label}-{}-{n}",
            std::process::id()
        ));
        std::fs::create_dir_all(&path).expect("create temp dir");
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }

    fn write(&self, name: &str, contents: &str) -> PathBuf {
        let path = self.path.join(name);
        std::fs::write(&path, contents).expect("write fixture");
        path
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.path);
    }
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

/// A ledger as one JSON object per line, so the mapping's field names are the
/// only thing tying the file to the comparison.
fn ledger(records: &[(&str, f64)]) -> String {
    ledger_unsequenced(records)
}

/// Ledger where the declared sequence is given per record.
fn ledger_seqmap(records: &[(&str, f64, i64)]) -> String {
    records
        .iter()
        .map(|(id, pnl, seq)| {
            format!(r#"{{"trade_id":"{id}","pnl":{pnl},"seq":{seq}}}"#)
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Physical order equals the declared order (no sequence field at all).
fn ledger_unsequenced(records: &[(&str, f64)]) -> String {
    records
        .iter()
        .map(|(id, pnl)| format!(r#"{{"trade_id":"{id}","pnl":{pnl}}}"#))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Mapping that declares a sequence field, so ordering is explicit.
fn sequenced_mapping() -> SemanticMapping {
    SemanticMapping {
        sequence_field: Some("seq".to_string()),
        ..SemanticMapping::default()
    }
}

fn ledger_with_times(records: &[(&str, f64, i64)]) -> String {
    records
        .iter()
        .map(|(id, pnl, t)| {
            format!(r#"{{"trade_id":"{id}","pnl":{pnl},"fill_time_ns":{t}}}"#)
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn ledger_with_orders(records: &[(&str, f64, &str)]) -> String {
    records
        .iter()
        .map(|(id, pnl, ot)| format!(r#"{{"trade_id":"{id}","pnl":{pnl},"order_type":"{ot}"}}"#))
        .collect::<Vec<_>>()
        .join("\n")
}

fn case_for(policy_id: &str) -> BenchmarkCase {
    BenchmarkCase::new(
        "BC-329-PARITY-01".into(),
        BenchmarkVersion::new_v8_5(),
        PolicyTarget {
            policy_id: policy_id.into(),
            commit_hash: "commit_329".into(),
            binary_digest: "binary_329".into(),
            family: "trend".into(),
        },
        vec![CapabilityDomain::ExecutionFidelity],
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    )
}

fn case_with_evidence(policy_id: &str, paths: &[&Path]) -> BenchmarkCase {
    let mut case = case_for(policy_id);
    case.evidence = Some(BenchmarkEvidenceManifest {
        artifact_paths: paths
            .iter()
            .map(|p| p.to_string_lossy().into_owned())
            .collect(),
    });
    case
}

/// Bind a role. The hash is what the *caller declares*; when the file is absent
/// the binding is still constructible (zeroed hash) so that the missing-artifact
/// path can be exercised: `ArtifactBinding::from_file` refuses to invent an empty
/// binding, which is why this fixture builds the struct directly.
fn binding(role: &str, path: &Path) -> ArtifactBinding {
    match ArtifactBinding::from_file(role, path) {
        Ok(b) => b,
        Err(_) => ArtifactBinding {
            role: role.into(),
            path: path.to_string_lossy().into_owned(),
            sha256_hex: "0".repeat(64),
            bytes: 0,
        },
    }
}

fn engine() -> EngineVersion {
    EngineVersion::new(ReferenceEngine::Lean, "2.5.0").expect("fixture engine version")
}

fn request(
    subject: ParitySubject,
    native: &Path,
    reference: &Path,
) -> ParityRequest {
    ParityRequest {
        subject,
        mapping: SemanticMapping::default(),
        engine: engine(),
        method_version: "parity-adapter-1.0.0".into(),
        native_artifact: binding("native", native),
        reference_artifact: binding("reference", reference),
        computed_at_timestamp_ns: 1_700_000_000_000_000_000,
    }
}

fn request_with(
    subject: ParitySubject,
    native: &Path,
    reference: &Path,
    mapping: SemanticMapping,
) -> ParityRequest {
    ParityRequest {
        subject,
        mapping,
        engine: engine(),
        method_version: "parity-adapter-1.0.0".into(),
        native_artifact: binding("native", native),
        reference_artifact: binding("reference", reference),
        computed_at_timestamp_ns: 1_700_000_000_000_000_000,
    }
}

fn run_against(dir: &TempDir, native: &str, reference: &str) -> ParityReceipt {
    run_against_with(dir, native, reference, SemanticMapping::default())
}

fn run_against_with(
    dir: &TempDir,
    native: &str,
    reference: &str,
    mapping: SemanticMapping,
) -> ParityReceipt {
    let n = dir.write("native.jsonl", native);
    let r = dir.write("reference.jsonl", reference);
    let subject = ParitySubject::from_case(&case_for("pol_329"));
    ParityAdapter::lean().run(&request_with(subject, &n, &r, mapping))
}

fn sample_receipt() -> BenchmarkReceipt {
    let gates = GateVector {
        g1_causal_pit: GateState::Pass,
        ..GateVector::default()
    };
    BenchmarkReceipt::generate_with_context(
        &case_for("pol_329"),
        HashMap::new(),
        42.0,
        gates,
        0.5,
        Vec::new(),
        None,
        None,
        ProjectionGrade::GradeU,
        1.0,
        1_700_000_000_000_000_000,
    )
}

// ---------------------------------------------------------------------------
// R0: production evaluation has no fixed-vector path (#329 required end state)
// ---------------------------------------------------------------------------

#[test]
fn fixed_vectors_are_absent_from_parity_sources() {
    // Textual guard, deliberately. The old defect was a pair of literals inside
    // evaluate_parity; no behavioural test can catch a future re-introduction
    // that happens to avoid the compared-arrays pattern, so the source itself is
    // the thing under test.
    let sources = [
        concat!(env!("CARGO_MANIFEST_DIR"), "/src/benchmark/external.rs"),
        concat!(env!("CARGO_MANIFEST_DIR"), "/src/benchmark/parity.rs"),
    ];
    for src in sources {
        let text = std::fs::read_to_string(src).expect("read parity source");
        // Strip comments: this module documents the deleted literals, and the
        // guard is about *code*, not prose about it.
        let code: String = text
            .lines()
            .filter(|l| !l.trim_start().starts_with("//"))
            .collect::<Vec<_>>()
            .join("\n");
        for literal in [
            "0.012", "0.0121", "-0.0049", "0.0081", "0.0149", "0.0101", "0.0061", "0.0152",
            "0.0079",
        ] {
            assert!(
                !code.contains(literal),
                "fixed parity vector {literal} reappeared in {src}"
            );
        }
        assert!(
            !code.contains("_policy_id"),
            "a discarded policy_id argument reappeared in {src}: a parity result \
             must be bound to the policy it names"
        );
        assert!(
            !code.contains("evaluate_parity"),
            "the unbound evaluate_parity API reappeared in {src}"
        );
        assert!(
            !code.contains("evaluate_series_parity"),
            "the in-process array comparison API reappeared in {src}"
        );
    }
}

#[test]
fn tolerance_field_parity_passed_is_gone() {
    // PARITY_AND_IDENTITY_SPEC §3 forbids tolerance-based parity. A
    // `parity_passed` bool computed against a bps tolerance is exactly that, so
    // its name must not survive either.
    let dir = concat!(env!("CARGO_MANIFEST_DIR"), "/src/benchmark");
    for name in ["external.rs", "parity.rs"] {
        let text = std::fs::read_to_string(Path::new(dir).join(name)).expect("read source");
        let code: String = text
            .lines()
            .filter(|l| !l.trim_start().starts_with("//"))
            .collect::<Vec<_>>()
            .join("\n");
        assert!(
            !code.contains("parity_passed"),
            "{name} reintroduced a tolerance-gated parity_passed flag"
        );
    }
}

#[test]
fn fabricated_drawdown_multiplier_is_gone() {
    // The old code reported `pnl_discrepancy_bps * 1.5` as a drawdown
    // discrepancy. Any multiplication of a PnL divergence into a "drawdown"
    // field is a fabrication, so the shape is checked, not just the constant.
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/src/benchmark/parity.rs");
    let text = std::fs::read_to_string(path).expect("read source");
    let code: String = text
        .lines()
        .filter(|l| !l.trim_start().starts_with("//"))
        .collect::<Vec<_>>()
        .join("\n");
    for multiplier in ["* 1.5", "* 1.2", "* 1.1"] {
        assert!(
            !code.contains(multiplier),
            "a hardcoded drawdown multiplier {multiplier} reappeared in parity.rs"
        );
    }
    assert!(
        !code.contains("fill_timing_mae_ms: 0.0"),
        "unmeasured fill timing was hardcoded to a perfect 0.0 again"
    );
}

// ---------------------------------------------------------------------------
// R1: comparisons bind to case and policy identity
// ---------------------------------------------------------------------------

#[test]
fn subject_is_taken_from_the_case_not_from_a_string() {
    let case = case_for("pol_bound");
    let subject = ParitySubject::from_case(&case);
    assert_eq!(subject.policy_id, "pol_bound");
    assert_eq!(subject.case_id, case.case_id);
    assert_eq!(subject.case_hash, case.case_hash);
    assert_eq!(subject.commit_hash, case.target.commit_hash);
    assert_eq!(subject.binary_digest, case.target.binary_digest);
    assert!(
        subject.missing_fields().is_empty(),
        "fixture subject should be complete"
    );
}

#[test]
fn policy_id_change_changes_parity_identity() {
    let dir = TempDir::new("policy");
    let native = ledger(&[("t1", 0.01), ("t2", -0.005)]);
    let reference = native.clone();

    let a = run_against(&dir, &native, &reference);
    let n = dir.write("native.jsonl", &native);
    let r = dir.write("reference2.jsonl", &reference);
    let b = ParityAdapter::lean().run(&request(
        ParitySubject::from_case(&case_for("pol_other")),
        &n,
        &r,
    ));

    assert_ne!(
        a.parity_identity, b.parity_identity,
        "issue §13: policy id must be part of parity identity, otherwise one \
         policy's parity can be cited as another's"
    );
}

#[test]
fn blank_subject_is_blocked_not_compared() {
    let dir = TempDir::new("blank-subject");
    let n = dir.write("native.jsonl", &ledger(&[("t1", 0.01)]));
    let r = dir.write("reference.jsonl", &ledger(&[("t1", 0.01)]));
    let subject = ParitySubject {
        case_id: String::new(),
        case_hash: "h".into(),
        policy_id: "   ".into(),
        commit_hash: "c".into(),
        binary_digest: "b".into(),
        family: "trend".into(),
    };
    let receipt = ParityAdapter::lean()
        .run(&request(subject, &n, &r));
    match &receipt.outcome {
        ParityOutcome::DataBlocked { reason } => {
            assert!(reason.contains("BLOCKED_PARITY_SUBJECT_INCOMPLETE"), "{reason}");
            assert!(reason.contains("case_id"), "{reason}");
            assert!(reason.contains("policy_id"), "{reason}");
        }
        other => panic!("blank subject must block, got {other:?}"),
    }
    assert!(!receipt.outcome.is_agreement());
}

#[test]
fn receipt_cannot_be_grafted_onto_another_policy() {
    let dir = TempDir::new("graft");
    let parity = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    let foreign = receipt_for_policy("pol_victim");
    let err = foreign
        .with_parity(&parity)
        .expect_err("parity computed for pol_329 must not attach to pol_victim");
    assert!(err.contains("BLOCKED_PARITY_POLICY_MISMATCH"), "{err}");
}

fn receipt_for_policy(policy_id: &str) -> BenchmarkReceipt {
    let gates = GateVector {
        g1_causal_pit: GateState::Pass,
        ..GateVector::default()
    };
    BenchmarkReceipt::generate_with_context(
        &case_for(policy_id),
        HashMap::new(),
        42.0,
        gates,
        0.5,
        Vec::new(),
        None,
        None,
        ProjectionGrade::GradeU,
        1.0,
        1_700_000_000_000_000_000,
    )
}

// ---------------------------------------------------------------------------
// R2: parity requires physical verified artifacts
// ---------------------------------------------------------------------------

#[test]
fn identical_verified_ledgers_reach_exact_match() {
    let dir = TempDir::new("exact");
    let body = ledger(&[("t1", 0.0125), ("t2", -0.004), ("t3", 0.0)]);
    let receipt = run_against(&dir, &body, &body);
    assert_eq!(receipt.outcome, ParityOutcome::ExactMatch);
    assert!(receipt.outcome.is_agreement());
    assert_eq!(receipt.diagnostics.paired_records, 3);
    assert_eq!(receipt.diagnostics.mismatched_records, 0);
    assert!(receipt.native.is_some() && receipt.reference.is_some());
    assert!(receipt.verify_identity());
}

#[test]
fn parity_reads_real_bytes_not_the_caller_description() {
    // If the adapter trusted `rows` or the binding it was handed, this would
    // report a match. The file contents decide.
    let dir = TempDir::new("real-bytes");
    let a = dir.write("native.jsonl", &ledger(&[("t1", 0.01), ("t2", 0.02)]));
    let b = dir.write("reference.jsonl", &ledger(&[("t1", 0.01), ("t2", 0.03)]));
    let mut req = request(
        ParitySubject::from_case(&case_for("pol_329")),
        &a,
        &b,
    );
    // Lie about the reference artifact in every way the type allows.
    req.reference_artifact.bytes = 999_999;
    req.reference_artifact.sha256_hex = "0".repeat(64);
    let receipt = ParityAdapter::lean().run(&req);
    match &receipt.outcome {
        ParityOutcome::DataBlocked { reason } => {
            assert!(reason.contains("DATA_BLOCKED_PARITY_ARTIFACT_MISMATCH"), "{reason}")
        }
        other => panic!("a lying artifact binding must block, got {other:?}"),
    }
    assert_eq!(
        receipt.diagnostics.paired_records, 0,
        "no comparison may run against an artifact that fails its own hash"
    );
}

#[test]
fn tampered_artifact_after_binding_is_caught() {
    let dir = TempDir::new("tamper");
    let n = dir.write("native.jsonl", &ledger(&[("t1", 0.01)]));
    let r = dir.write("reference.jsonl", &ledger(&[("t1", 0.01)]));
    let req = request(ParitySubject::from_case(&case_for("pol_329")), &n, &r);
    assert!(ParityAdapter::lean()
        .run(&req)
        .outcome
        .is_agreement());

    std::fs::write(&r, ledger(&[("t1", 9.99)])).expect("tamper reference ledger");
    let receipt = ParityAdapter::lean().run(&req);
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("ARTIFACT_MISMATCH")),
        "tamper-at-rest on a parity ledger must block: {:?}",
        receipt.outcome
    );
}

#[test]
fn missing_artifact_is_data_blocked_never_zero_difference() {
    let dir = TempDir::new("missing");
    let n = dir.write("native.jsonl", &ledger(&[("t1", 0.01)]));
    let missing = dir.path().join("gone.jsonl");
    let req = request(
        ParitySubject::from_case(&case_for("pol_329")),
        &n,
        &missing,
    );
    let receipt = ParityAdapter::lean().run(&req);
    match &receipt.outcome {
        ParityOutcome::DataBlocked { reason } => {
            assert!(reason.contains("DATA_BLOCKED"), "{reason}");
            assert!(reason.contains("PARITY_ARTIFACT_UNREADABLE"), "{reason}");
        }
        other => panic!("missing artifact must block, got {other:?}"),
    }
    // The three ways absence could masquerade as a result, all checked.
    assert!(!receipt.outcome.is_agreement());
    assert_eq!(receipt.diagnostics.paired_records, 0);
    assert_eq!(receipt.diagnostics.terminal_divergence_bps, None);
    assert_eq!(receipt.diagnostics.mean_abs_divergence_bps, None);
    assert_eq!(receipt.diagnostics.max_drawdown_divergence_bps, None);
    assert_eq!(receipt.diagnostics.fill_timing_mae_ms, None);
    assert!(
        receipt.native.is_none() && receipt.reference.is_none(),
        "a blocked run must not claim artifact coverage it does not have"
    );
}

#[test]
fn empty_ledger_is_blocked_not_vacuously_equal() {
    // Two empty ledgers are bit-for-bit "identical", which is precisely why an
    // empty file must not read as perfect parity.
    let dir = TempDir::new("empty");
    let receipt = run_against(&dir, "", "");
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("PARITY_LEDGER_EMPTY")),
        "{:?}",
        receipt.outcome
    );
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), "");
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("reference")),
        "empty reference must name the role that is empty: {:?}",
        receipt.outcome
    );
}

#[test]
fn runner_requires_parity_artifacts_to_be_declared() {
    let dir = TempDir::new("declared");
    let n = dir.write("native.jsonl", &ledger(&[("t1", 0.01)]));
    let r = dir.write("reference.jsonl", &ledger(&[("t1", 0.01)]));

    // No manifest at all: nothing is declared, so nothing may be parity-tested.
    let no_manifest = case_for("pol_329");
    let err = BenchmarkRunner::default()
        .parity_request(
            &no_manifest,
            SemanticMapping::default(),
            engine(),
            &n,
            &r,
            "parity-adapter-1.0.0",
            1,
        )
        .expect_err("a case without an evidence manifest must not produce a request");
    assert!(err.contains("DATA_BLOCKED_NO_VERIFIED_BENCHMARK_EVIDENCE"), "{err}");

    // Manifest declares a *different* file: the ledgers exist and hash cleanly,
    // but the case never named them.
    let unrelated = dir.write("unrelated.jsonl", "bar\n");
    let undeclared = case_with_evidence("pol_329", &[Path::new(&unrelated)]);
    let err = BenchmarkRunner::default()
        .parity_request(
            &undeclared,
            SemanticMapping::default(),
            engine(),
            &n,
            &r,
            "parity-adapter-1.0.0",
            1,
        )
        .expect_err("undeclared artifacts must not produce a request");
    assert!(
        err.contains("DATA_BLOCKED_UNDECLARED_PARITY_ARTIFACT[native]"),
        "{err}"
    );

    let no_evidence = case_with_evidence("pol_329", &[]);
    let err = BenchmarkRunner::default()
        .parity_request(
            &no_evidence,
            SemanticMapping::default(),
            engine(),
            &n,
            &r,
            "parity-adapter-1.0.0",
            1,
        )
        .expect_err("empty manifest must block");
    assert!(err.contains("DATA_BLOCKED"), "{err}");

    // Declared: request is built and the run proceeds.
    let declared = case_with_evidence("pol_329", &[&n, &r]);
    let req = BenchmarkRunner::default()
        .parity_request(
            &declared,
            SemanticMapping::default(),
            engine(),
            &n,
            &r,
            "parity-adapter-1.0.0",
            1_700_000_000_000_000_000,
        )
        .expect("declared artifacts yield a request");
    assert_eq!(req.subject.policy_id, "pol_329");
    let receipt = ParityAdapter::lean().run(&req);
    assert!(receipt.outcome.is_agreement());
    assert_eq!(
        receipt.native.as_ref().expect("native bound").rows,
        1,
        "row count is read from the physical file"
    );

    // Declared for one case, used for another: the subject comes from the case,
    // so the identity moves with it.
    let other_case = case_with_evidence("pol_impostor", &[&n, &r]);
    let req2 = BenchmarkRunner::default()
        .parity_request(
            &other_case,
            SemanticMapping::default(),
            engine(),
            &n,
            &r,
            "parity-adapter-1.0.0",
            1,
        )
        .expect("same artifacts, different policy");
    assert_eq!(req2.subject.policy_id, "pol_impostor");
    let a = ParityAdapter::lean().run(&req);
    let b = ParityAdapter::lean().run(&req2);
    assert!(a.outcome.is_agreement() && b.outcome.is_agreement());
    assert_ne!(
        a.parity_identity, b.parity_identity,
        "identical ledgers must not yield identical parity identity across policies"
    );
}

#[test]
fn declared_but_missing_file_blocks_before_comparison() {
    let dir = TempDir::new("declared-missing");
    let n = dir.write("native.jsonl", &ledger(&[("t1", 0.01)]));
    let r = dir.write("reference.jsonl", &ledger(&[("t1", 0.01)]));
    let mut case = case_with_evidence("pol_329", &[&n, &r]);
    // Manifest names a file that is not on disk.
    case.evidence.as_mut().unwrap().artifact_paths.push(
        dir.path()
            .join("ghost.jsonl")
            .to_string_lossy()
            .into_owned(),
    );
    let err = BenchmarkRunner::default()
        .parity_request(
            &case,
            SemanticMapping::default(),
            engine(),
            &n,
            &r,
            "parity-adapter-1.0.0",
            1,
        )
        .expect_err("a declared artifact missing from disk must block");
    assert!(err.contains("DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT"), "{err}");
}

// ---------------------------------------------------------------------------
// §13: identity covers policy, artifact, mapping and engine hashes
// ---------------------------------------------------------------------------

fn exact_pair(dir: &TempDir) -> (PathBuf, PathBuf) {
    let body = ledger(&[("t1", 0.0125), ("t2", -0.004)]);
    (
        dir.write("native.jsonl", &body),
        dir.write("reference.jsonl", &body),
    )
}

#[test]
fn artifact_hash_change_invalidates_identity() {
    let dir = TempDir::new("id-artifact");
    let (n, r) = exact_pair(&dir);
    let a = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &n, &r));

    std::fs::write(&r, ledger(&[("t1", 0.0125), ("t2", -0.0041)])).expect("rewrite");
    let b = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &n, &r));

    assert_ne!(a.parity_identity, b.parity_identity);
    assert_eq!(b.outcome, ParityOutcome::Diverged);
}

#[test]
fn mapping_change_invalidates_identity() {
    let dir = TempDir::new("id-mapping");
    let (n, r) = exact_pair(&dir);

    let default_mapping = SemanticMapping::default();
    let a = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &n, &r));

    let narrower = SemanticMapping {
        supported_order_types: vec!["MARKET".into()],
        ..default_mapping.clone()
    };
    let b = ParityAdapter::lean()
        .run(&request_with(ParitySubject::from_case(&case_for("pol_329")), &n, &r, narrower));
    assert_ne!(
        a.mapping_hash, b.mapping_hash,
        "dropping supported order semantics changes what 'the same fill' means"
    );
    assert_ne!(a.parity_identity, b.parity_identity);

    let renamed_key = SemanticMapping {
        pairing_key: "execution_id".into(),
        ..default_mapping.clone()
    };
    let c = ParityAdapter::lean()
        .run(&request_with(
            ParitySubject::from_case(&case_for("pol_329")),
            &n,
            &r,
            renamed_key,
        ));
    assert_ne!(a.parity_identity, c.parity_identity);
    // The renamed key is not in the fixtures: blocked, not silently empty.
    assert!(matches!(&c.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("PARITY_RECORD_INVALID")), "{:?}", c.outcome);
}

#[test]
fn engine_version_and_build_hash_are_part_of_identity() {
    let dir = TempDir::new("id-engine");
    let (n, r) = exact_pair(&dir);
    let subject = || ParitySubject::from_case(&case_for("pol_329"));

    let mut req_a = request(subject(), &n, &r);
    let a = ParityAdapter::lean().run(&req_a);

    req_a.engine = EngineVersion::new(ReferenceEngine::Lean, "2.5.1").expect("2.5.1");
    let b = ParityAdapter::lean().run(&req_a);
    assert_ne!(a.parity_identity, b.parity_identity, "different engine version");

    req_a.engine = EngineVersion::new(ReferenceEngine::Skfolio, "2.5.0").expect("skfolio");
    let c = ParityAdapter::lean().run(&req_a);
    assert_ne!(b.parity_identity, c.parity_identity, "different engine");

    req_a.engine = EngineVersion::new(ReferenceEngine::Lean, "2.5.0")
        .expect("2.5.0")
        .with_build_hash("deadbeef")
        .expect("build hash");
    let d = ParityAdapter::lean().run(&req_a);
    assert_ne!(a.parity_identity, d.parity_identity, "build hash must bind");
    assert_eq!(
        a.engine.engine, d.engine.engine,
        "adding a build hash must not change which engine ran"
    );
    assert!(!d.provenance_gaps.iter().any(|g| g.contains("engine_build_hash")));
}

#[test]
fn engine_without_declared_version_is_refused_at_construction() {
    for label in ["", "   ", "\t"] {
        let err = EngineVersion::new(ReferenceEngine::Lean, label)
            .expect_err("blank engine version must be refused");
        assert!(err.contains("BLOCKED_ENGINE_VERSION_UNKNOWN"), "{err}");
    }
    let err = EngineVersion::new(ReferenceEngine::Lean, "2.5.0")
        .expect("ok")
        .with_build_hash("  ")
        .expect_err("blank build hash must be refused");
    assert!(err.contains("BLOCKED_ENGINE_BUILD_HASH_EMPTY"), "{err}");
}

#[test]
fn method_version_is_part_of_identity_and_placeholders_rejected() {
    let dir = TempDir::new("id-method");
    let (n, r) = exact_pair(&dir);
    let subject = || ParitySubject::from_case(&case_for("pol_329"));

    let mut req = request(subject(), &n, &r);
    let a = ParityAdapter::lean().run(&req);
    assert_eq!(a.outcome, ParityOutcome::ExactMatch);

    req.method_version = "parity-adapter-1.0.1".into();
    let b = ParityAdapter::lean().run(&req);
    assert_ne!(a.parity_identity, b.parity_identity, "method refactor invalidates");

    for placeholder in ["", " ", "N/A "] {
        req.method_version = placeholder.into();
        let blocked = ParityAdapter::lean().run(&req);
        assert!(
            matches!(&blocked.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("BLOCKED_EMPTY_METHOD_VERSION")),
            "placeholder {placeholder:?} must block, got {:?}",
            blocked.outcome
        );
    }
    assert!(check_method_version("v1").is_ok());
    assert!(check_method_version("  ").is_err());
}

#[test]
fn edited_receipt_fails_identity_verification() {
    let dir = TempDir::new("id-edit");
    let mut receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    assert!(receipt.verify_identity());
    // Flip the outcome to agreement without touching the inputs: the identity
    // does not cover the outcome, so this is caught only because the detector
    // re-verifies identity and the report path re-checks artifacts. Both must
    // reject a receipt whose *inputs* were edited.
    receipt.engine = EngineVersion::new(ReferenceEngine::Lean, "9.9.9").expect("edited");
    assert!(
        !receipt.verify_identity(),
        "editing a bound input must break the stamped identity"
    );
    let err = DisagreementDetector::assert_parity(&receipt)
        .expect_err("an identity-broken receipt must not assert parity");
    assert!(err.contains("identity does not match"), "{err}");
}

#[test]
fn identity_version_is_stamped_and_required() {
    let dir = TempDir::new("id-version");
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    assert_eq!(receipt.identity_version, PARITY_IDENTITY_VERSION);
    assert_eq!(receipt.mapping_hash, SemanticMapping::default().mapping_hash());
}

// ---------------------------------------------------------------------------
// divergence is observable
// ---------------------------------------------------------------------------

#[test]
fn bit_level_divergence_is_detected() {
    let dir = TempDir::new("diverged");
    let receipt = run_against(
        &dir,
        &ledger(&[("t1", 0.0125), ("t2", -0.004)]),
        &ledger(&[("t1", 0.0125), ("t2", -0.00400001)]),
    );
    assert_eq!(receipt.outcome, ParityOutcome::Diverged);
    assert_eq!(receipt.diagnostics.paired_records, 2);
    assert_eq!(receipt.diagnostics.mismatched_records, 1);
    let mean = receipt.diagnostics.mean_abs_divergence_bps.expect("mean");
    assert!(mean > 0.0 && mean < 1.0, "sub-bps drift: {mean}");
    assert!(receipt.diagnostics.max_abs_divergence_bps.expect("max") > 0.0);
    assert!(DisagreementDetector::assert_parity(&receipt).is_err());
}

#[test]
fn negative_zero_is_not_equal_to_zero() {
    // The spec's equality is the IEEE-754 bit pattern, so -0.0 vs 0.0 is a
    // divergence. The old `==` comparison reported agreement.
    let dir = TempDir::new("negzero");
    let receipt = run_against(&dir, &ledger(&[("t1", -0.0)]), &ledger(&[("t1", 0.0)]));
    assert_eq!(
        receipt.outcome,
        ParityOutcome::Diverged,
        "-0.0 and 0.0 must not compare equal in the parity path"
    );
}

#[test]
fn terminal_sign_reversal_is_divergence_not_rounding() {
    let dir = TempDir::new("sign");
    let receipt = run_against(&dir, &ledger(&[("t1", 150.0)]), &ledger(&[("t1", -80.0)]));
    assert!(receipt.diagnostics.terminal_sign_disagreement);
    assert_eq!(receipt.outcome, ParityOutcome::Diverged);
    assert!(DisagreementDetector::check_sign_agreement(150.0, -80.0).is_err());
}

#[test]
fn unpaired_records_never_become_partial_agreement() {
    let dir = TempDir::new("unpaired");
    let receipt = run_against(
        &dir,
        &ledger(&[("t1", 0.01), ("t2", 0.02)]),
        &ledger(&[("t1", 0.01), ("t9", 0.02)]),
    );
    assert_eq!(
        receipt.outcome,
        ParityOutcome::UnpairedRecords {
            native_only: 1,
            reference_only: 1
        }
    );
    assert!(!receipt.outcome.is_agreement());
    // The matching pair is not allowed to launder the missing ones.
    assert_eq!(receipt.diagnostics.paired_records, 1);
    assert_eq!(receipt.diagnostics.mismatched_records, 0);
    assert!(DisagreementDetector::assert_parity(&receipt).is_err());
}

#[test]
fn unsupported_order_semantics_veto_the_comparison() {
    // BFS-015: an unmappable fill has no defined parity. It must not be skipped
    // and must not be scored as agreement.
    let dir = TempDir::new("semantics");
    let native = ledger_with_orders(&[("t1", 0.01, "MARKET")]);
    let reference = ledger_with_orders(&[("t1", 0.01, "SYNTHETIC_DARK_POOL_CROSS")]);
    let receipt = run_against(&dir, &native, &reference);
    assert_eq!(
        receipt.outcome,
        ParityOutcome::UnsupportedSemantics {
            order_type: "SYNTHETIC_DARK_POOL_CROSS".into()
        }
    );
    assert!(!receipt.outcome.is_agreement());
    assert_eq!(receipt.diagnostics.paired_records, 0);
    let err = DisagreementDetector::assert_parity(&receipt)
        .expect_err("unsupported semantics must not assert parity");
    assert!(err.contains("BFS-015") || err.contains("PARITY_UNSUPPORTED_SEMANTICS"), "{err}");
}

#[test]
fn mapping_order_set_is_the_single_source_of_supported_semantics() {
    let narrow = SemanticMapping {
        supported_order_types: vec!["MARKET".into()],
        ..SemanticMapping::default()
    };
    assert!(!narrow.supports_order_type("LIMIT"));
    // The detector consults the registered default mapping, so its list and the
    // adapter's cannot drift apart silently.
    assert!(DisagreementDetector::check_order_semantics("LIMIT").is_ok());
    assert!(DisagreementDetector::check_order_semantics("MARKET").is_ok());
    assert!(DisagreementDetector::check_order_semantics("STOP_MARKET").is_ok());
    assert!(DisagreementDetector::check_order_semantics("ICEBERG").is_err());
    let dir = TempDir::new("mapping-orders");
    let receipt = run_against(
        &dir,
        &ledger_with_orders(&[("t1", 0.01, "LIMIT")]),
        &ledger_with_orders(&[("t1", 0.01, "LIMIT")]),
    );
    assert!(receipt.outcome.is_agreement(), "LIMIT is in the default mapping");
}

#[test]
fn blank_mapping_is_unusable_and_blocks() {
    let dir = TempDir::new("mapping-blank");
    let (n, r) = exact_pair(&dir);
    let subject = || ParitySubject::from_case(&case_for("pol_329"));

    let mapping = SemanticMapping {
        mapping_version: "  ".into(),
        ..SemanticMapping::default()
    };
    let receipt = ParityAdapter::lean()
        .run(&request_with(subject(), &n, &r, mapping));
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("MAPPING_UNUSABLE")),
        "{:?}",
        receipt.outcome
    );

    let mapping = SemanticMapping {
        pairing_key: String::new(),
        ..SemanticMapping::default()
    };
    let receipt = ParityAdapter::lean()
        .run(&request_with(subject(), &n, &r, mapping));
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("pairing_key")),
        "{:?}",
        receipt.outcome
    );

    let mapping = SemanticMapping {
        supported_order_types: Vec::new(),
        ..SemanticMapping::default()
    };
    let receipt = ParityAdapter::lean()
        .run(&request_with(subject(), &n, &r, mapping));
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("order semantics")),
        "{:?}",
        receipt.outcome
    );
}

#[test]
fn a_narrower_mapping_rejects_semantics_the_default_allows() {
    // The mapping, not the adapter, decides what is expressible, so a MARKET-only
    // mapping must refuse LIMIT rather than compare it.
    let dir = TempDir::new("mapping-narrow");
    let mapping = SemanticMapping {
        supported_order_types: vec!["MARKET".into()],
        ..SemanticMapping::default()
    };
    let body = ledger_with_orders(&[("t1", 0.01, "LIMIT")]);
    let receipt = run_against_with(&dir, &body, &body, mapping);
    assert_eq!(
        receipt.outcome,
        ParityOutcome::UnsupportedSemantics { order_type: "LIMIT".into() }
    );
    assert!(!receipt.outcome.is_agreement());
}

#[test]
fn adapter_and_request_engine_must_agree() {
    // A skfolio adapter handed a LEAN-declared request must refuse rather than
    // silently attribute a result to the wrong engine.
    let dir = TempDir::new("engine-mismatch");
    let (n, r) = exact_pair(&dir);
    let receipt = ParityAdapter::skfolio()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &n, &r));
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("BLOCKED_PARITY_ENGINE_MISMATCH")),
        "{:?}",
        receipt.outcome
    );
    assert!(!receipt.outcome.is_agreement());
}

#[test]
fn default_mapping_version_is_the_registered_one() {
    assert_eq!(SemanticMapping::default().mapping_version, MAPPING_VERSION);
}

#[test]
fn non_finite_and_duplicate_records_fail_closed() {
    let dir = TempDir::new("bad-records");
    // Non-finite pnl arrives as JSON null (serde coerces NaN/inf), which is not
    // a number: the adapter must reject it rather than read 0.0.
    let n = dir.write(
        "native.jsonl",
        "{\"trade_id\":\"t1\",\"pnl\":null}\n",
    );
    let r = dir.write("reference.jsonl", &ledger(&[("t1", 0.01)]));
    let receipt = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &n, &r));
    assert!(matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("PARITY_RECORD_INVALID")), "{:?}", receipt.outcome);

    // Duplicate keys: which record is "the" trade is undefined.
    let dup = dir.write(
        "dup.jsonl",
        &format!("{}\n{}", ledger(&[("t1", 0.01)]), ledger(&[("t1", 0.02)])),
    );
    let receipt = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &dup, &r));
    assert!(
        matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("BLOCKED_PARITY_AMBIGUOUS_KEYS")),
        "{:?}",
        receipt.outcome
    );

    // Malformed line.
    let junk = dir.write("junk.jsonl", "not json at all\n");
    let receipt = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &junk, &r));
    assert!(matches!(&receipt.outcome, ParityOutcome::DataBlocked { reason } if reason.contains("unparseable")), "{:?}", receipt.outcome);
}

#[test]
fn fill_timing_absence_is_none_not_zero() {
    let dir = TempDir::new("timing");
    // Neither side has fill_time_ns: an absence, not a perfect measurement.
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    assert_eq!(receipt.diagnostics.fill_timing_mae_ms, None);

    // Both sides present and equal -> exact, zero error is now meaningful.
    let same = ledger_with_times(&[("t1", 0.01, 1_000_000_000), ("t2", 0.02, 2_000_000_000)]);
    let receipt = run_against(&dir, &same, &same);
    assert_eq!(receipt.diagnostics.fill_timing_mae_ms, Some(0.0));

    // Drift of 5ms per record.
    let late = ledger_with_times(&[("t1", 0.01, 1_005_000_000), ("t2", 0.02, 2_005_000_000)]);
    let receipt = run_against(&dir, &same, &late);
    let mae = receipt.diagnostics.fill_timing_mae_ms.expect("measured");
    assert!((mae - 5.0).abs() < 1e-9, "expected 5ms MAE, got {mae}");
    // The old code reported 0.0 here and still passed on PnL agreement; now the
    // timing divergence is visible and the outcome is not an agreement.
    assert_ne!(receipt.outcome, ParityOutcome::ExactMatch);
}

#[test]
fn max_drawdown_divergence_is_measured_not_multiplied() {
    let dir = TempDir::new("drawdown");
    // native: +0.05, -0.02, -0.04, +0.01 -> equity 0.05/0.03/-0.01/0.0
    //   peak 0.05, trough 0.05 -> 600 bps
    // reference: +0.05, -0.01, -0.01, 0.0 -> equity 0.05/0.04/0.03/0.03
    //   peak 0.05, trough 0.05 -> 200 bps
    // divergence 400 bps, while the terminal (summed) PnL difference is 300 bps.
    // Under the deleted `pnl_discrepancy * 1.5` formula the reported value would
    // have been 450 bps, so the two are distinguishable.
    let native = ledger(&[("t1", 0.05), ("t2", -0.02), ("t3", -0.04), ("t4", 0.01)]);
    let reference = ledger(&[("t1", 0.05), ("t2", -0.01), ("t3", -0.01), ("t4", 0.0)]);
    let receipt = run_against(&dir, &native, &reference);
    let dd = receipt
        .diagnostics
        .max_drawdown_divergence_bps
        .expect("measured from both equity curves");
    assert!(
        (dd - 400.0).abs() < 1e-6,
        "drawdown divergence must come from the curves, got {dd}"
    );
    let term = receipt
        .diagnostics
        .terminal_divergence_bps
        .expect("terminal sums");
    assert!(
        (term - 300.0).abs() < 1e-6,
        "terminal PnL divergence is a different quantity: {term}"
    );
    assert_ne!(
        dd,
        term * 1.5,
        "the fabricated multiplier is still being applied"
    );
}

#[test]
fn drawdown_uses_declared_sequence_not_file_order() {
    // Same three trades in both files, so pairing is exact and the only thing
    // that can move the drawdown diagnostic is how each ledger says to order
    // itself. (+0.02, -0.01, -0.01) peaks at 200 bps; (-0.01, +0.02, -0.01)
    // peaks at 100 bps.
    let dir = TempDir::new("curve-seq");
    let native = ledger_seqmap(&[("t1", 0.02, 0), ("t2", -0.01, 1), ("t3", -0.01, 2)]);
    let reference = ledger_seqmap(&[("t1", 0.02, 1), ("t2", -0.01, 2), ("t3", -0.01, 0)]);
    let n = dir.write("native.jsonl", &native);
    let r = dir.write("reference.jsonl", &reference);
    let receipt = ParityAdapter::lean().run(&request_with(
        ParitySubject::from_case(&case_for("pol_329")),
        &n,
        &r,
        sequenced_mapping(),
    ));
    assert_eq!(
        receipt.outcome,
        ParityOutcome::ExactMatch,
        "identical trades must pair identically regardless of numbering"
    );
    assert!(
        receipt.diagnostics.fill_timing_mae_ms.is_none(),
        "no fill times recorded, so timing must stay unmeasured"
    );
    let dd = receipt
        .diagnostics
        .max_drawdown_divergence_bps
        .expect("both curves built");
    assert!(
        (dd - 100.0).abs() < 1e-6,
        "declared sequence must drive the curve: expected 100 bps, got {dd}"
    );
}

#[test]
fn partially_sequenced_ledger_yields_no_curve_diagnostic() {
    // A sequence field is declared, but one native row lacks it. Splicing
    // seq-ordered rows with position-ordered rows would invent a path between
    // them, so the drawdown diagnostic must be absent.
    let dir = TempDir::new("curve-absent");
    let n = dir.write(
        "native.jsonl",
        r#"{"trade_id":"t1","pnl":0.05,"seq":0}
{"trade_id":"t2","pnl":-0.09}"#,
    );
    let r = dir.write(
        "reference.jsonl",
        r#"{"trade_id":"t1","pnl":0.05,"seq":0}
{"trade_id":"t2","pnl":-0.09,"seq":1}"#,
    );
    let receipt = ParityAdapter::lean().run(&request_with(
        ParitySubject::from_case(&case_for("pol_329")),
        &n,
        &r,
        sequenced_mapping(),
    ));
    assert_eq!(
        receipt.diagnostics.max_drawdown_divergence_bps, None,
        "an unorderable ledger must report an absent curve, not a computed one"
    );
    // The rest of the run is unaffected: parity itself does not need ordering.
    assert_eq!(receipt.outcome, ParityOutcome::ExactMatch);
}

#[test]
fn no_sequence_field_at_all_still_yields_a_curve_from_file_order() {
    let dir = TempDir::new("no-seq-field");
    let mapping = SemanticMapping {
        sequence_field: None,
        ..SemanticMapping::default()
    };
    let body = r#"{"trade_id":"t1","pnl":0.05}
{"trade_id":"t2","pnl":-0.09}"#;
    let n = dir.write("native.jsonl", body);
    let r = dir.write("reference.jsonl", body);
    let req = ParityRequest {
        subject: ParitySubject::from_case(&case_for("pol_329")),
        mapping: mapping.clone(),
        engine: engine(),
        method_version: "parity-adapter-1.0.0".into(),
        native_artifact: binding("native", &n),
        reference_artifact: binding("reference", &r),
        computed_at_timestamp_ns: 1_700_000_000_000_000_000,
    };
    let receipt = ParityAdapter::lean().run(&req);
    assert_eq!(receipt.outcome, ParityOutcome::ExactMatch);
    assert!(receipt.diagnostics.max_drawdown_divergence_bps.is_some());
    // Dropping the sequence field changes the mapping hash, hence the identity:
    // results computed under a different ordering rule are not interchangeable.
    let with_seq = run_against_with(&dir, body, body, sequenced_mapping());
    assert_ne!(receipt.mapping_hash, with_seq.mapping_hash);
}

#[test]
fn record_ordering_does_not_change_parity_verdict() {
    let dir = TempDir::new("order");
    let a = ledger(&[("t1", 0.01), ("t2", 0.02), ("t3", 0.03)]);
    let shuffled = ledger(&[("t3", 0.03), ("t1", 0.01), ("t2", 0.02)]);
    let receipt = run_against(&dir, &a, &shuffled);
    assert_eq!(
        receipt.outcome,
        ParityOutcome::ExactMatch,
        "pairing is by trade id, so file order is not a parity signal"
    );
    assert_eq!(receipt.diagnostics.paired_records, 3);
}

#[test]
fn curve_falls_back_to_file_order_without_a_sequence_field() {
    // Same trades, different physical order, no sequence declared anywhere:
    // parity is exact (pairing is by trade id) while the curve diagnostic, read
    // in file order, still moves. Keeping both behaviours under test prevents a
    // future refactor from "fixing" one by breaking the other.
    let dir = TempDir::new("curve-file-order");
    let mapping = SemanticMapping {
        sequence_field: None,
        ..SemanticMapping::default()
    };
    let in_order =
        ledger_unsequenced(&[("t1", 0.02), ("t2", -0.01), ("t3", -0.01)]);
    let reversed =
        ledger_unsequenced(&[("t3", -0.01), ("t1", 0.02), ("t2", -0.01)]);
    let n = dir.write("native.jsonl", &in_order);
    let r = dir.write("reference.jsonl", &reversed);
    let receipt = ParityAdapter::lean()
        .run(&request_with(ParitySubject::from_case(&case_for("pol_329")), &n, &r, mapping));
    assert_eq!(receipt.outcome, ParityOutcome::ExactMatch);
    let dd = receipt
        .diagnostics
        .max_drawdown_divergence_bps
        .expect("curves built from file order");
    assert!(
        (dd - 100.0).abs() < 1e-6,
        "expected the 100 bps file-order difference, got {dd}"
    );
}

// ---------------------------------------------------------------------------
// R3: instruments, not authorities
// ---------------------------------------------------------------------------

#[test]
fn every_outcome_carries_zero_authority() {
    let dir = TempDir::new("authority");
    let outcomes = [
        run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)])),
        run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.02)])),
        run_against(&dir, "", ""),
        run_against(
            &dir,
            &ledger_with_orders(&[("t1", 0.01, "SYNTHETIC")]),
            &ledger_with_orders(&[("t1", 0.01, "SYNTHETIC")]),
        ),
        run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t9", 0.01)])),
    ];
    assert_eq!(outcomes.len(), 5);
    for receipt in &outcomes {
        let authority = receipt.authority();
        assert_eq!(
            authority.decision,
            v8_core::authority::DecisionAuthority::DiagnosticOnly,
            "parity outcome {:?} escalated decision authority",
            receipt.outcome
        );
        assert_eq!(
            authority.realization,
            v8_core::authority::RealizationStatus::Hypothetical,
            "parity outcome {:?} claims realized cashflow",
            receipt.outcome
        );
        assert_eq!(receipt.authority_class(), NON_SOVEREIGN_INSTRUMENT_STATUS);
    }
}

#[test]
fn there_is_no_authority_field_to_forge() {
    // Stronger than "the typed accessor ignores the stored string": the
    // serialized receipt has no authority field at all, so a persisted parity
    // result cannot be re-labelled by editing JSON. The status string is a
    // method over a constant.
    let dir = TempDir::new("authority-field");
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    let json = serde_json::to_string(&receipt).expect("serialize");
    let value: serde_json::Value = serde_json::from_str(&json).expect("parse");
    assert!(
        value.get("authority").is_none(),
        "a settable authority field returned to ParityReceipt: {json}"
    );
    assert_eq!(receipt.authority_class(), NON_SOVEREIGN_INSTRUMENT_STATUS);

    // And even a hand-built Authority claiming portfolio authorization cannot
    // raise the ceiling: #327's firewall clamps rendering to input.
    let cap = v8_core::benchmark::gate_authority::cap_authority(
        v8_core::benchmark::parity::PARITY_INSTRUMENT_AUTHORITY,
        v8_core::authority::Authority {
            evidence: v8_core::authority::EvidenceAuthority::Observed,
            decision: v8_core::authority::DecisionAuthority::PortfolioAuthorized,
            realization: v8_core::authority::RealizationStatus::CashflowSettled,
        },
    );
    assert_eq!(
        cap,
        v8_core::benchmark::parity::PARITY_INSTRUMENT_AUTHORITY,
        "parity escalated through a rendering step"
    );
}

#[test]
fn parity_observation_is_marked_non_sovereign() {
    let dir = TempDir::new("observation");
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    let obs = receipt.to_observation();
    assert_eq!(obs.authority, NON_SOVEREIGN_INSTRUMENT_STATUS);
    assert_ne!(
        obs.authority, "measured",
        "a parity observation must not carry the authority string that real \
         statistical evidence uses"
    );
    assert!(obs.notes.contains(&receipt.parity_identity));
    assert_eq!(obs.metric_id, "external_parity::QuantConnect-LEAN");

    let blocked = run_against(&dir, "", &ledger(&[("t1", 0.01)]));
    let obs = blocked.to_observation();
    assert!(!obs.passed_floor, "a blocked parity run must not pass a floor");
    assert_eq!(obs.raw_value, 0.0);
    assert!(obs.notes.contains("DATA_BLOCKED"), "{}", obs.notes);
    assert_eq!(obs.sample_size, 0, "no samples may be claimed for absent data");
}

#[test]
fn exact_parity_cannot_make_a_certificate_production_ready() {
    // End-to-end #327 + #328 + #329: an *exact* external match on an otherwise
    // all-Pass diagnostic receipt must still render NO_ECONOMIC_CLAIM.
    let dir = TempDir::new("cert");
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));
    assert_eq!(receipt.outcome, ParityOutcome::ExactMatch);

    let gates = GateVector {
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
    };
    let base = BenchmarkReceipt::generate_with_context(
        &case_for("pol_329"),
        HashMap::new(),
        99.0,
        gates,
        1.0,
        Vec::new(),
        None,
        None,
        ProjectionGrade::GradeU,
        1.0,
        1_700_000_000_000_000_000,
    );
    let with_parity = base.with_parity(&receipt).expect("attest exact parity");
    let certificate = v8_core::benchmark::certificate::PolicyCertificate::generate(&with_parity, None);
    assert!(
        certificate.authority_verdict.contains("NO_ECONOMIC_CLAIM"),
        "exact external parity minted an economic claim: {}",
        certificate.authority_verdict
    );
    assert!(
        !certificate.status.contains("Production Ready"),
        "exact external parity minted deployment readiness: {}",
        certificate.status
    );
}

// ---------------------------------------------------------------------------
// composition with BenchmarkReceipt (#328)
// ---------------------------------------------------------------------------

#[test]
fn with_parity_binds_artifacts_and_reseals() {
    let dir = TempDir::new("attach");
    let native = ledger(&[("t1", 0.01), ("t2", 0.02)]);
    let receipt = run_against(&dir, &native, &native);
    let base = sample_receipt();
    let before = base.receipt_digest.clone();
    let attached = base.clone().with_parity(&receipt).expect("attach parity");

    assert_ne!(attached.receipt_digest, before, "attesting parity must move the digest");
    assert_eq!(attached.observations.len(), base.observations.len() + 1);
    assert_eq!(attached.artifacts.len(), 2);
    assert!(attached.verify_digest().is_ok());
    assert!(attached.verify().is_ok());

    // The bound artifacts are physically checkable, so a ledger edited after the
    // fact cannot keep attesting to itself.
    let reference_path = receipt.reference.as_ref().unwrap().binding.path.clone();
    std::fs::write(&reference_path, ledger(&[("t1", 7.7)])).expect("tamper");
    let err = attached
        .verify_artifacts()
        .expect_err("tampered parity ledger must be caught at verification");
    assert!(format!("{err}").contains("MISMATCH"), "{err}");
}

#[test]
fn with_parity_rejects_mismatched_case_and_broken_identity() {
    let dir = TempDir::new("attach-reject");
    let receipt = run_against(&dir, &ledger(&[("t1", 0.01)]), &ledger(&[("t1", 0.01)]));

    let foreign = BenchmarkCase {
        case_hash: "case_hash_of_another_case".into(),
        ..case_for("pol_329")
    };
    let base = BenchmarkReceipt {
        case_hash: foreign.case_hash.clone(),
        ..sample_receipt()
    };
    let err = base
        .with_parity(&receipt)
        .expect_err("case_hash mismatch must block attachment");
    assert!(err.contains("BLOCKED_PARITY_CASE_MISMATCH"), "{err}");

    let edited = ParityReceipt {
        method_version: "parity-adapter-9.9.9".into(),
        ..receipt.clone()
    };
    let err = sample_receipt()
        .with_parity(&edited)
        .expect_err("edited parity receipt must block attachment");
    assert!(err.contains("BLOCKED_PARITY_IDENTITY_MISMATCH"), "{err}");
}

#[test]
fn blocked_parity_is_still_attestable_as_a_negative() {
    // A blocked run is a finding, not a missing row: recording it keeps the gap
    // visible to coverage and to the report instead of leaving no trace.
    let dir = TempDir::new("negative");
    let receipt = run_against(&dir, "", "");
    let attached = sample_receipt()
        .with_parity(&receipt)
        .expect("blocked parity attaches as a failed floor");
    assert_eq!(attached.artifacts.len(), 0, "blocked run bound no artifacts");
    assert_eq!(attached.observations.len(), 1);
    assert!(!attached.observations[0].passed_floor);
    assert!(attached.observations[0].notes.contains("DATA_BLOCKED"));
    assert!(attached.verify().is_ok());
}

#[test]
fn same_artifact_bound_twice_with_different_hashes_conflicts() {
    // A receipt that already attests to `reference.jsonl` under one hash cannot
    // also attest to it under another: one of the two is a lie and we cannot tell
    // which, so the attach must fail rather than keep both.
    let dir = TempDir::new("conflict");
    let (n, r) = exact_pair(&dir);
    let parity = ParityAdapter::lean()
        .run(&request(ParitySubject::from_case(&case_for("pol_329")), &n, &r));
    assert!(parity.outcome.is_agreement());

    let mut base = sample_receipt();
    base.artifacts.push(ArtifactBinding {
        role: "reference".into(),
        path: r.to_string_lossy().into_owned(),
        sha256_hex: "f".repeat(64),
        bytes: 1,
    });
    base.receipt_digest = base.compute_digest().expect("reseal fixture");
    let err = base
        .with_parity(&parity)
        .expect_err("two hashes for one file cannot both be attested");
    assert!(err.contains("BLOCKED_PARITY_ARTIFACT_CONFLICT"), "{err}");

    // Same path and same hash is not a conflict, and must not duplicate the row.
    let mut deduped = sample_receipt().with_artifact(
        parity
            .reference
            .as_ref()
            .expect("reference binding present for an agreement run")
            .binding
            .clone(),
    );
    deduped = deduped.with_parity(&parity).expect("identical binding is idempotent");
    assert_eq!(
        deduped
            .artifacts
            .iter()
            .filter(|b| b.path == r.to_string_lossy().as_ref())
            .count(),
        1,
        "the same artifact must be bound once"
    );
    assert!(deduped.verify().is_ok());
}

#[test]
fn receipt_round_trips_through_json_and_still_verifies() {
    let dir = TempDir::new("serde");
    let native = ledger(&[("t1", 0.0125), ("t2", -0.004)]);
    let receipt = run_against(&dir, &native, &native);
    let json = serde_json::to_string(&receipt).expect("serialize parity receipt");
    let back: ParityReceipt = serde_json::from_str(&json).expect("deserialize");
    assert_eq!(back, receipt);
    assert!(back.verify_identity());
    assert!(back.outcome.is_agreement());
    // A serialized receipt that a caller re-labels must not silently keep its
    // identity: subject is part of the hash.
    let mut value: serde_json::Value = serde_json::from_str(&json).expect("parse");
    value["subject"]["policy_id"] = serde_json::Value::String("pol_stolen".into());
    let relabelled: ParityReceipt = serde_json::from_value(value).expect("parse relabelled");
    assert_eq!(relabelled.subject.policy_id, "pol_stolen");
    assert!(
        !relabelled.verify_identity(),
        "re-labelling a receipt's policy must break its identity"
    );
    assert!(DisagreementDetector::assert_parity(&relabelled).is_err());
}

#[test]
fn mapping_hash_is_order_independent_but_content_dependent() {
    let mut a = SemanticMapping::default();
    let mut b = SemanticMapping::default();
    a.supported_order_types = vec!["MARKET".into(), "LIMIT".into()];
    b.supported_order_types = vec!["LIMIT".into(), "MARKET".into()];
    assert_eq!(a.mapping_hash(), b.mapping_hash(), "declaration order is not semantics");
    b.supported_order_types.push("STOP_MARKET".into());
    assert_ne!(a.mapping_hash(), b.mapping_hash(), "the set is the contract");
    let c = SemanticMapping {
        sequence_field: None,
        ..SemanticMapping::default()
    };
    assert_ne!(
        a.mapping_hash(),
        c.mapping_hash(),
        "how a curve is ordered is part of the mapping"
    );
}

// ---------------------------------------------------------------------------
// honest scope: trade-path parity, not D-116 monetary parity
// ---------------------------------------------------------------------------

#[test]
fn reconciliation_gaps_are_reported_even_on_exact_agreement() {
    // An exact match must not read as D-116 monetary parity. The gap note is
    // therefore stamped on every receipt, agreement included.
    let dir = TempDir::new("scope");
    let body = ledger(&[("t1", 0.01), ("t2", -0.005)]);
    let agreement = run_against(&dir, &body, &body);
    assert_eq!(agreement.outcome, ParityOutcome::ExactMatch);
    assert!(
        !agreement.reconciliation_gaps.is_empty(),
        "a receipt that silently omits commission/funding/balance scope is the \
         next version of the fixed-vector lie"
    );
    let stamped: Vec<&str> = agreement.reconciliation_gaps.iter().map(String::as_str).collect();
    assert_eq!(
        stamped,
        v8_core::benchmark::parity::reconciliation_gaps().to_vec(),
        "the receipt must carry exactly the declared scope gaps"
    );
    for gap in stamped {
        assert!(gap.contains("D-116"), "gap note must cite its authority: {gap}");
    }

    let blocked = run_against(&dir, "", "");
    assert_eq!(
        blocked.reconciliation_gaps, agreement.reconciliation_gaps,
        "scope is a property of the adapter, not of the outcome"
    );
}
