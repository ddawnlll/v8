//! S7 verdict report artifacts + audit checks (issue #126/#123/#125;
//! COMPUTE_CORE_SPEC §6; LEDGER_FORMAT_SPEC §3-4, §8).
//!
//! The Verdict layer consumes the Analysis output and persists a LabReport
//! analogue as an evidence artifact (COMPUTE_CORE_SPEC §4, §6). The report
//! binds to the ledger it summarizes via `ledger_hash` — the fingerprint of
//! the `cube-reduced` artifact it was built from — plus the tape (`data_hash`)
//! and the producer (`generator`). No wall clock ever enters a report (G5).
//!
//! The report is a summary artifact: the verdict statistics summary (verdict,
//! gap-status counts, `fsum`-sum of legal hindsight gaps) is hoisted into the
//! header as run-constants — every value is constant for the whole report —
//! and the per-slice counts are one columnar row per slice (`slice_key`,
//! `slice_n`, ...). The verdict statistics themselves (block-bootstrap
//! Reality-Check, detrended null; D-044) are `statistics.rs` (issue #128); the
//! report's `verdict` stays `NO_ECONOMIC_CLAIM` until a statistics verdict and
//! an authority receipt exist (rule 12 — never a claimed edge).
//!
//! The S7 audit extends the ledger §8 cheap-test battery (issue #109) to
//! verdict artifacts: round-trip, header completeness, tier honesty,
//! no-decimal-floats scan, retention — plus artifact freshness (issue #123):
//! an artifact is stale when its referenced tape or generator hash is older
//! than the current one, or its referenced ledger no longer matches the store.

use std::path::{Path, PathBuf};

use serde_json::Value;

use crate::evidence;
use crate::evidence::{Artifact, ArtifactTier, DType, FieldTier, ReadBack, RunConstants};
use crate::hash::HASH_ENCODING;
use crate::regret;
use crate::state::fsum;

/// The report artifact kind (LEDGER_FORMAT_SPEC §3 `artifact_kind`).
pub const REPORT_KIND: &str = "report";

/// The report's declared row ordering: one row per slice, keyed by slice key.
pub const REPORT_ORDERING: &str = "slice_key";

/// The report artifact filename in `out_dir`.
pub const REPORT_FILENAME: &str = "report.v82";

/// The referenced-ledger filename the report binds to via `ledger_hash`.
pub const LEDGER_FILENAME: &str = "cube-reduced.v82";

/// The `ledger_hash` a minimal report carries when no `cube-reduced` artifact
/// is present in `out_dir` — an explicit absent marker, never a forged
/// fingerprint. The audit still passes retention (the tape is retained) but a
/// consumer can see the report bound no ledger.
pub const LEDGER_ABSENT: &str = "ledger-absent";

/// The report's verdict until `statistics::verdict` (issue #128) and an
/// authority receipt exist: no economic claim is ever written by this stage
/// (V8_CONSTITUTION rule 12).
pub const REPORT_VERDICT: &str = "NO_ECONOMIC_CLAIM";

/// A §3 run-constant this report deliberately does not bind. The report is
/// built from the cube-reduced tables, which already embed the replay, cost,
/// funding and risk effects of the ledger — re-binding a simulator / risk
/// gate / cost-model identity here would claim a simulator this stage did not
/// run. `unbound` is an honest absence, never a zero or a hash.
pub const UNBOUND_RUN_CONSTANT: &str = "unbound";

/// The report's own required run-constants, beyond the §3 set and the
/// `symbol` / `interval` / `generator` bindings: the verdict statistics
/// summary plus the ledger binding. Header-completeness (§8 test #2) requires
/// every one of these on a report artifact.
pub const REPORT_RUN_CONSTANT_KEYS: [&str; 7] = [
    "ledger_hash",
    "verdict",
    "candidate_count",
    "n_gap_computed",
    "n_gap_abstained",
    "n_gap_not_applicable",
    "sum_gap",
];

/// The report slice columns with their declared minimum field tiers
/// (LEDGER_FORMAT_SPEC §5). Identity fields (`slice_key`) are present at every
/// tier; the information columns (`slice_n`, gap-status counts, `slice_sum_gap`)
/// require `VALUES`+. Tier honesty is enforced on the write path by
/// `Artifact::add_field` and re-checked by `audit_tier_honesty`.
pub const REPORT_SLICE_FIELDS: [(&str, DType, FieldTier); 5] = [
    ("slice_key", DType::DictStr, FieldTier::IdentityOnly),
    ("slice_n", DType::I64, FieldTier::Values),
    ("slice_n_gap_computed", DType::I64, FieldTier::Values),
    ("slice_n_gap_abstained", DType::I64, FieldTier::Values),
    ("slice_sum_gap", DType::F64, FieldTier::Values),
];

/// issue #125: `tools/diagnostics.py` retirement mapping.
///
/// D-091 moves verdict statistics, reporting and auditing into the compute
/// plane; the consolidated report centre is pre-V8.2 dev tooling
/// (COMPUTE_CORE_SPEC §7.3) and retires when its last port lands. The table
/// is the map: what ports to `report.rs` (and `statistics.rs`) versus what is
/// dev tooling that retires — including the re-export shims
/// (`diagnostic.py`, `diagnostic_report.py`, `multi_diagnostic.py`,
/// `forensics.py`), which die with the engine they re-export.
pub const DIAGNOSTICS_RETIREMENT: [(&str, &str); 8] = [
    (
        "run_diagnostic / write_report (verdict summary + report)",
        "ports to report.rs report() (this module)",
    ),
    (
        "ledger §8 audit on verdict artifacts",
        "ports to report.rs audit_report()",
    ),
    (
        "artifact freshness reporting (tools/artifact_status.py lifecycle)",
        "ports to report.rs audit_freshness()",
    ),
    (
        "DiagnosticEngine 9-section report + per-expert forensics",
        "dev tooling — retires (superseded by verdict statistics on reduced tables)",
    ),
    (
        "exit grids (EXIT_TP_GRID / EXIT_EXPIRY_GRID), COST_SWEEP, NULL_REPLICATIONS",
        "dev tooling — retires; the significance machinery moves to statistics.rs (D-044)",
    ),
    (
        "render_html / render_multi_html",
        "dev tooling — retires (an HTML report is not a compute-plane artifact)",
    ),
    (
        "run_multi (multi-symbol matrix runner)",
        "retires; the report request's universe loop replaces it",
    ),
    (
        "diagnostic.py / diagnostic_report.py / multi_diagnostic.py / forensics.py shims",
        "retire with the engine they re-export",
    ),
];

/// The verdict statistics summary a report carries — the run-level half of the
/// LabReport analogue, hoisted into the header as run-constants.
#[derive(Debug, Clone, PartialEq)]
pub struct ReportSummary {
    /// The statistics verdict. `NO_ECONOMIC_CLAIM` until `statistics::verdict`
    /// and an authority receipt exist (rule 12).
    pub verdict: String,
    /// Number of candidates in the referenced reduced table.
    pub candidate_count: i64,
    /// Rows whose gap was computed (`GAP_COMPUTED`).
    pub n_gap_computed: i64,
    /// Rows that abstained (`GAP_ABSTAINED_CENSORED` + `GAP_ABSTAINED_UNDEFINED`).
    pub n_gap_abstained: i64,
    /// Rows with no actual action (`GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION`).
    pub n_gap_not_applicable: i64,
    /// Sum of `legal_hindsight_gap` over the computed rows — `state::fsum`,
    /// bit-identical to the oracle's `sum()`/`math.fsum`.
    pub sum_gap: f64,
}

/// One slice row of the report: per-slice counts over the reduced table.
#[derive(Debug, Clone, PartialEq)]
pub struct ReportSlice {
    pub slice_key: String,
    pub slice_n: i64,
    pub slice_n_gap_computed: i64,
    pub slice_n_gap_abstained: i64,
    pub slice_sum_gap: f64,
}

/// The report artifact header: the §3 run-constants, the `symbol` /
/// `interval` / `generator` bindings, and the report's own run-constants —
/// the ledger binding (`ledger_hash`) and the verdict statistics summary.
pub fn report_artifact(
    tier: ArtifactTier,
    symbol: &str,
    interval: &str,
    generator: &str,
    rc: &RunConstants,
    ledger_hash: &str,
    summary: &ReportSummary,
) -> Artifact {
    let mut rc_obj = rc.with_binding(symbol, interval, generator);
    let obj = rc_obj
        .as_object_mut()
        .expect("run-constants serialize as an object");
    obj.insert("ledger_hash".to_string(), serde_json::json!(ledger_hash));
    obj.insert("verdict".to_string(), serde_json::json!(summary.verdict));
    obj.insert("candidate_count".to_string(), serde_json::json!(summary.candidate_count));
    obj.insert("n_gap_computed".to_string(), serde_json::json!(summary.n_gap_computed));
    obj.insert("n_gap_abstained".to_string(), serde_json::json!(summary.n_gap_abstained));
    obj.insert("n_gap_not_applicable".to_string(), serde_json::json!(summary.n_gap_not_applicable));
    obj.insert("sum_gap".to_string(), serde_json::json!(summary.sum_gap));
    Artifact::new(REPORT_KIND, tier.as_str(), rc_obj, REPORT_ORDERING)
}

/// Add the report slice columns, enforcing tier honesty (`add_field`). The
/// returned indices index `artifact.columns` for the matching slice row.
pub fn add_report_slice_fields(a: &mut Artifact) -> Result<[usize; 5], evidence::TierViolation> {
    let mut out = [0usize; 5];
    for (i, (name, dtype, ft)) in REPORT_SLICE_FIELDS.iter().enumerate() {
        out[i] = a.add_field(name, *dtype, *ft)?;
    }
    Ok(out)
}

/// Push one slice row into a report artifact built by `report_artifact` +
/// `add_report_slice_fields`.
pub fn push_report_slice(a: &mut Artifact, cols: &[usize; 5], s: &ReportSlice) {
    a.columns[cols[0]].push_str(&s.slice_key);
    a.columns[cols[1]].push_i64(s.slice_n);
    a.columns[cols[2]].push_i64(s.slice_n_gap_computed);
    a.columns[cols[3]].push_i64(s.slice_n_gap_abstained);
    a.columns[cols[4]].push_f64(s.slice_sum_gap);
    a.end_row();
}

/// The verdict statistics summary of a cube-reduced read-back: counts by
/// gap-status vocabulary (`regret.rs`) and the `fsum` sum of the computed
/// legal hindsight gaps.
pub fn summarize_cube_reduced(back: &ReadBack) -> ReportSummary {
    let n = back.row_count();
    let gap_status = back.column("gap_status");
    let gap_val = back.column("legal_hindsight_gap");
    let mut n_computed = 0i64;
    let mut n_abstained = 0i64;
    let mut n_not_applicable = 0i64;
    let mut gaps: Vec<f64> = Vec::new();
    for i in 0..n {
        let status = gap_status
            .and_then(|c| c[i].as_ref())
            .and_then(Value::as_str)
            .unwrap_or("");
        if status == regret::GAP_COMPUTED {
            n_computed += 1;
        } else if status == regret::GAP_ABSTAINED_CENSORED
            || status == regret::GAP_ABSTAINED_UNDEFINED
        {
            n_abstained += 1;
        } else if status == regret::GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION {
            n_not_applicable += 1;
        }
        if let Some(v) = gap_val.and_then(|c| c[i].as_ref()).and_then(Value::as_f64) {
            gaps.push(v);
        }
    }
    ReportSummary {
        verdict: REPORT_VERDICT.to_string(),
        candidate_count: n as i64,
        n_gap_computed: n_computed,
        n_gap_abstained: n_abstained,
        n_gap_not_applicable: n_not_applicable,
        sum_gap: fsum(&gaps),
    }
}

/// The zero summary a minimal report carries when no cube-reduced artifact is
/// present (the report is still written; `ledger_hash` is `LEDGER_ABSENT`).
pub fn empty_summary() -> ReportSummary {
    ReportSummary {
        verdict: REPORT_VERDICT.to_string(),
        candidate_count: 0,
        n_gap_computed: 0,
        n_gap_abstained: 0,
        n_gap_not_applicable: 0,
        sum_gap: 0.0,
    }
}

/// The §3 run-constants for a report. `data_hash` binds the tape; `code_hash`
/// binds the cube-reducer that produced the reduced tables (its
/// `generator_version`, e.g. `legal-action-manifest-v1`); `config_hash` binds
/// the report request's universe. The economic/simulator fields the report
/// does not claim are `UNBOUND_RUN_CONSTANT`.
pub fn report_run_constants(
    data_hash: &str,
    code_hash: &str,
    universe: &[String],
    _interval: &str,
) -> RunConstants {
    let mut u = universe.to_vec();
    u.sort();
    let config = u.join("|");
    RunConstants {
        data_hash: data_hash.to_string(),
        code_hash: code_hash.to_string(),
        config_hash: evidence::sha1_hex(config.as_bytes()),
        simulator_hash: UNBOUND_RUN_CONSTANT.to_string(),
        risk_gate_hash: UNBOUND_RUN_CONSTANT.to_string(),
        evaluator_version: UNBOUND_RUN_CONSTANT.to_string(),
        platform: "cpu".to_string(),
        utility_unit: UNBOUND_RUN_CONSTANT.to_string(),
        cost_form: UNBOUND_RUN_CONSTANT.to_string(),
        // Schema placeholder, never an economic claim: the report does not
        // rebind a cost model — the reduced tables already embed replay costs.
        slippage: 0.0,
        action_manifest_id: UNBOUND_RUN_CONSTANT.to_string(),
    }
}

/// The current data hash for `tape_path`: SHA-1 over the raw tape bytes —
/// deterministic, content-addressed, and the freshness reference an artifact's
/// `data_hash` is compared against.
pub fn tape_hash(path: &Path) -> std::io::Result<String> {
    let bytes = std::fs::read(path)?;
    Ok(evidence::sha1_hex(&bytes))
}

// ---------------------------------------------------------------------------
// S7 audit (issue #123): ledger §8 extended to verdict artifacts
// ---------------------------------------------------------------------------

/// One audit-check result.
#[derive(Debug, Clone)]
pub struct AuditCheck {
    pub name: &'static str,
    pub passed: bool,
    pub detail: String,
}

impl AuditCheck {
    fn run(name: &'static str, res: Result<(), String>) -> AuditCheck {
        match res {
            Ok(()) => AuditCheck { name, passed: true, detail: String::new() },
            Err(e) => AuditCheck { name, passed: false, detail: e },
        }
    }
}

/// Header-completeness check for a report artifact (§8 test #2): the §3
/// run-constants, the `symbol`/`interval`/`generator` bindings, and the
/// report's own run-constant set. A missing key fails closed with the key
/// named — never a report that silently drops a summary field.
pub fn validate_report_header(header: &Value) -> Result<(), String> {
    evidence::validate_header(header)?;
    let rc = header
        .get("run_constants")
        .and_then(Value::as_object)
        .ok_or("report header: run_constants missing or not an object")?;
    for k in REPORT_RUN_CONSTANT_KEYS {
        if rc.get(k).is_none() {
            return Err(format!("report header missing run-constant {k}"));
        }
    }
    Ok(())
}

/// Round-trip check (§8 test #1) on a report artifact: write, read back, and
/// verify the declared kind/tier/hash-encoding and the rectangular slice
/// columns. Absent cells read as `None`, never a sentinel number.
pub fn audit_round_trip(report_path: &Path) -> Result<(), String> {
    let back = evidence::read_artifact(report_path).map_err(|e| e.to_string())?;
    if back.header["artifact_kind"].as_str() != Some(REPORT_KIND) {
        return Err(format!(
            "read-back artifact_kind {:?} is not {REPORT_KIND}",
            back.header["artifact_kind"]
        ));
    }
    if back.header["tier"].as_str().is_none() {
        return Err("read-back header has no tier".to_string());
    }
    if back.header["hash_encoding"].as_str() != Some(HASH_ENCODING) {
        return Err("read-back hash_encoding is not the declared encoding".to_string());
    }
    for (name, _, _) in REPORT_SLICE_FIELDS {
        let col = back.column(name).ok_or_else(|| format!("report has no column {name}"))?;
        if col.len() != back.row_count() {
            return Err(format!("column {name} length {} != row count {}", col.len(), back.row_count()));
        }
    }
    Ok(())
}

/// Header-completeness check (§8 test #2): the complete header validates, and
/// removing any single run-constant (report or §3) — or `hash_encoding` /
/// `tier` — fails closed with the missing key named.
pub fn audit_header_completeness(report_path: &Path) -> Result<(), String> {
    let h = evidence::read_header(report_path).map_err(|e| e.to_string())?;
    validate_report_header(&h)?;
    let mut keys: Vec<&str> = RunConstants::REQUIRED_KEYS.to_vec();
    keys.extend(["symbol", "interval", "generator"]);
    keys.extend(REPORT_RUN_CONSTANT_KEYS);
    for key in keys {
        let mut corrupt = h.clone();
        corrupt["run_constants"]
            .as_object_mut()
            .ok_or("run_constants is not an object")?
            .remove(key);
        if validate_report_header(&corrupt).is_ok() {
            return Err(format!("report header without run-constant {key} did not fail closed"));
        }
    }
    for field in ["hash_encoding", "tier"] {
        let mut corrupt = h.clone();
        corrupt.as_object_mut().ok_or("header is not an object")?.remove(field);
        if validate_report_header(&corrupt).is_ok() {
            return Err(format!("report header without {field} did not fail closed"));
        }
    }
    Ok(())
}

/// Tier-honesty check (§8 test #4): the report's declared tier can serve every
/// one of its slice fields. The write path already rejects a too-low tier
/// (`add_field`); this re-checks the artifact on disk so a forged header
/// cannot claim a tier its columns do not support.
pub fn audit_tier_honesty(report_path: &Path) -> Result<(), String> {
    let h = evidence::read_header(report_path).map_err(|e| e.to_string())?;
    let tier = h["tier"].as_str().ok_or("report header has no tier")?;
    let at = ArtifactTier::from_str(tier).ok_or_else(|| format!("unknown tier {tier}"))?;
    for (name, _, ft) in REPORT_SLICE_FIELDS {
        if !at.can_serve(ft) {
            return Err(format!(
                "field {name} requires {} but artifact tier is {tier}",
                ft.as_str()
            ));
        }
    }
    Ok(())
}

/// No-decimal-floats check (§8 test #5): the numeric value columns of the
/// report artifact contain no text encoding of a float (fixed-width IEEE-754 /
/// two's complement never contains a digit-adjacent '.'). The header's
/// run-constant decimals (e.g. `slippage`) are not value regions and are not
/// scanned.
pub fn audit_no_decimal_floats(report_path: &Path) -> Result<(), String> {
    let hits = evidence::find_decimal_float_text(report_path).map_err(|e| e.to_string())?;
    if hits.is_empty() {
        Ok(())
    } else {
        Err(format!("decimal float text in numeric columns: {}", hits.join(", ")))
    }
}

/// Retention check (§8 test #6) on a report artifact: the tape referenced by
/// `data_hash` has a retention record, and the referenced ledger
/// (`ledger_hash` -> `cube-reduced.v82`) is present in `out_dir` and its
/// fingerprint matches. `LEDGER_ABSENT` is the honest "no ledger" binding and
/// is not a retention violation; a forged or missing ledger is reported.
pub fn audit_retention(
    report_path: &Path,
    out_dir: &Path,
    store_path: &Path,
) -> Result<(), String> {
    let h = evidence::read_header(report_path).map_err(|e| e.to_string())?;
    let rc = &h["run_constants"];
    let data_hash = rc["data_hash"].as_str().unwrap_or_default();
    let store = evidence::RetentionStore::open(store_path).map_err(|e| e.to_string())?;
    store.resolves(data_hash)?;
    let ledger_hash = rc["ledger_hash"].as_str().unwrap_or_default();
    if ledger_hash != LEDGER_ABSENT {
        let ledger_path = out_dir.join(LEDGER_FILENAME);
        if !ledger_path.exists() {
            return Err(format!(
                "report references ledger {ledger_hash} but {LEDGER_FILENAME} is not present"
            ));
        }
        let fp = evidence::fingerprint(&ledger_path).map_err(|e| e.to_string())?;
        if fp != ledger_hash {
            return Err(format!(
                "report references ledger {ledger_hash} != current {LEDGER_FILENAME} {fp}"
            ));
        }
    }
    Ok(())
}

/// Artifact freshness check (issue #123): an artifact is stale when its
/// referenced tape hash is older than the current tape, its generator tag is
/// not the current producer, or its referenced ledger no longer matches the
/// store's `cube-reduced` artifact.
pub fn audit_freshness(
    report_path: &Path,
    out_dir: &Path,
    current_data_hash: &str,
    current_generator: &str,
) -> Result<(), String> {
    let h = evidence::read_header(report_path).map_err(|e| e.to_string())?;
    let rc = &h["run_constants"];
    let mut problems: Vec<String> = Vec::new();
    match rc["data_hash"].as_str() {
        Some(h) if h != current_data_hash => {
            problems.push(format!("referenced tape {h} is older than current {current_data_hash}"));
        }
        None => problems.push("report header has no data_hash".to_string()),
        _ => {}
    }
    match rc["generator"].as_str() {
        Some(g) if g != current_generator => {
            problems.push(format!("generator {g} is not the current {current_generator}"));
        }
        None => problems.push("report header has no generator".to_string()),
        _ => {}
    }
    let ledger_hash = rc["ledger_hash"].as_str().unwrap_or_default();
    if ledger_hash != LEDGER_ABSENT {
        let ledger_path = out_dir.join(LEDGER_FILENAME);
        if !ledger_path.exists() {
            problems.push(format!(
                "referenced ledger {ledger_hash} has no {LEDGER_FILENAME} in the store"
            ));
        } else {
            let fp = evidence::fingerprint(&ledger_path).map_err(|e| e.to_string())?;
            if fp != ledger_hash {
                problems.push(format!(
                    "referenced ledger {ledger_hash} is older than current {LEDGER_FILENAME} {fp}"
                ));
            }
        }
    }
    if problems.is_empty() {
        Ok(())
    } else {
        Err(problems.join("; "))
    }
}

/// Run the full S7 audit battery on a report artifact: freshness, round-trip,
/// header completeness, tier honesty, no-decimal-floats, retention.
pub fn audit_report(
    report_path: &Path,
    out_dir: &Path,
    store_path: &Path,
    current_data_hash: &str,
    current_generator: &str,
) -> Vec<AuditCheck> {
    vec![
        AuditCheck::run(
            "freshness",
            audit_freshness(report_path, out_dir, current_data_hash, current_generator),
        ),
        AuditCheck::run("round-trip", audit_round_trip(report_path)),
        AuditCheck::run("header-completeness", audit_header_completeness(report_path)),
        AuditCheck::run("tier-honesty", audit_tier_honesty(report_path)),
        AuditCheck::run("no-decimal-floats", audit_no_decimal_floats(report_path)),
        AuditCheck::run("retention", audit_retention(report_path, out_dir, store_path)),
    ]
}

// ---------------------------------------------------------------------------
// S7 report driver (issue #126)
// ---------------------------------------------------------------------------

/// The report request: `{tape_path, universe, out_dir}` plus optional
/// `tier` / `base_interval` (defaults mirror the other compute-plane stages).
#[derive(Debug, serde::Deserialize)]
struct ReportRequest {
    tape_path: PathBuf,
    out_dir: PathBuf,
    #[serde(default)]
    universe: Vec<String>,
    #[serde(default)]
    tier: String,
    #[serde(default = "default_interval")]
    base_interval: String,
}

fn default_interval() -> String {
    "1h".to_string()
}

/// The default symbol for a report whose request names no universe member.
pub const DEFAULT_REPORT_SYMBOL: &str = "SOLUSDT";

/// S7 verdict report driver (issue #126): read a request `{tape_path,
/// universe, out_dir}`, build a minimal report from the cube-reduced artifact
/// if one is present (`out_dir/cube-reduced.v82`), run the S7 audit battery,
/// write `out_dir/report.v82`, and print its fingerprint. Returns 0 only when
/// every audit check passes (fail closed, OPERATIONS_SPEC §5).
pub fn report(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core report <request.json>");
        return 2;
    }
    let req: ReportRequest = match std::fs::read(&args[0])
        .map_err(|e| format!("cannot read request {}: {e}", args[0]))
        .and_then(|b| serde_json::from_slice(&b).map_err(|e| format!("cannot parse request {}: {e}", args[0])))
    {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    if let Err(e) = std::fs::create_dir_all(&req.out_dir) {
        eprintln!("error: out_dir {:?}: {e}", req.out_dir);
        return 1;
    }

    // Freshness reference: the current tape and producer.
    let current_data_hash = match tape_hash(&req.tape_path) {
        Ok(h) => h,
        Err(e) => {
            eprintln!("error: cannot hash tape {:?}: {e}", req.tape_path);
            return 1;
        }
    };
    let current_generator = evidence::generator_tag();
    let symbol = req
        .universe
        .first()
        .cloned()
        .unwrap_or_else(|| DEFAULT_REPORT_SYMBOL.to_string());

    // Ledger binding + summary from the cube-reduced artifact when present.
    let ledger_path = req.out_dir.join(LEDGER_FILENAME);
    let (ledger_hash, summary, code_hash) = if ledger_path.exists() {
        let back = match evidence::read_artifact(&ledger_path) {
            Ok(b) => b,
            Err(e) => {
                eprintln!("error: cannot read {LEDGER_FILENAME}: {e}");
                return 1;
            }
        };
        let fp = match evidence::fingerprint(&ledger_path) {
            Ok(f) => f,
            Err(e) => {
                eprintln!("error: cannot fingerprint {LEDGER_FILENAME}: {e}");
                return 1;
            }
        };
        let code = back.header["run_constants"]["generator_version"]
            .as_str()
            .unwrap_or(regret::GENERATOR_VERSION)
            .to_string();
        (fp, summarize_cube_reduced(&back), code)
    } else {
        (LEDGER_ABSENT.to_string(), empty_summary(), regret::GENERATOR_VERSION.to_string())
    };

    let rc = report_run_constants(&current_data_hash, &code_hash, &req.universe, &req.base_interval);
    let tier = ArtifactTier::from_str(&req.tier).unwrap_or(ArtifactTier::Values);
    let mut art = report_artifact(
        tier,
        &symbol,
        &req.base_interval,
        &current_generator,
        &rc,
        &ledger_hash,
        &summary,
    );
    let cols = match add_report_slice_fields(&mut art) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("error: report tier honesty: {e}");
            return 1;
        }
    };
    let slice_key = if req.universe.len() == 1 { symbol.clone() } else { "all".to_string() };
    push_report_slice(
        &mut art,
        &cols,
        &ReportSlice {
            slice_key,
            slice_n: summary.candidate_count,
            slice_n_gap_computed: summary.n_gap_computed,
            slice_n_gap_abstained: summary.n_gap_abstained,
            slice_sum_gap: summary.sum_gap,
        },
    );
    let report_path = req.out_dir.join(REPORT_FILENAME);
    if let Err(e) = art.write(&report_path) {
        eprintln!("error: write report artifact: {e}");
        return 1;
    }
    let report_fingerprint = match evidence::fingerprint(&report_path) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("error: fingerprint report artifact: {e}");
            return 1;
        }
    };

    // Retention registration: the tape this report references is retained
    // (LEDGER_FORMAT_SPEC §6.1 — a tape referenced by a retained artifact is
    // itself retained).
    let store_path = req.out_dir.join("retention.jsonl");
    let mut store = match evidence::RetentionStore::open(&store_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("error: retention store: {e}");
            return 1;
        }
    };
    if let Err(e) = store.insert(&current_data_hash, true) {
        eprintln!("error: retention registration: {e}");
        return 1;
    }

    let checks = audit_report(
        &report_path,
        &req.out_dir,
        &store_path,
        &current_data_hash,
        &current_generator,
    );
    let mut all_pass = true;
    for c in &checks {
        if c.passed {
            println!("report-audit: {}: PASS", c.name);
        } else {
            eprintln!("report-audit: {}: FAIL — {}", c.name, c.detail);
            all_pass = false;
        }
    }
    let summary_json = serde_json::json!({
        "subcommand": "report",
        "artifact": report_path.to_string_lossy(),
        "artifact_fingerprint": report_fingerprint,
        "ledger_hash": ledger_hash,
        "verdict": summary.verdict,
        "candidate_count": summary.candidate_count,
        "audit_pass": all_pass,
    });
    println!("{}", serde_json::to_string(&summary_json).unwrap());
    if all_pass {
        0
    } else {
        eprintln!("report: FAILED");
        1
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn summary_fixture() -> ReportSummary {
        ReportSummary {
            verdict: REPORT_VERDICT.to_string(),
            candidate_count: 3,
            n_gap_computed: 2,
            n_gap_abstained: 1,
            n_gap_not_applicable: 0,
            sum_gap: 1.5,
        }
    }

    /// Per-test directory so parallel tests never share a fixture file.
    fn test_dir(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("v82-report-{name}"));
        std::fs::create_dir_all(&dir).expect("create test dir");
        dir
    }

    fn write_report_fixture(
        dir: &Path,
        name: &str,
        generator: &str,
        data_hash: &str,
        ledger_hash: &str,
    ) -> std::io::Result<std::path::PathBuf> {
        let rc = report_run_constants(data_hash, regret::GENERATOR_VERSION, &["SOLUSDT".to_string()], "1h");
        let summary = summary_fixture();
        let mut a = report_artifact(
            ArtifactTier::Values,
            "SOLUSDT",
            "1h",
            generator,
            &rc,
            ledger_hash,
            &summary,
        );
        let cols = add_report_slice_fields(&mut a).expect("VALUES report carries slice fields");
        push_report_slice(
            &mut a,
            &cols,
            &ReportSlice {
                slice_key: "SOLUSDT".to_string(),
                slice_n: summary.candidate_count,
                slice_n_gap_computed: summary.n_gap_computed,
                slice_n_gap_abstained: summary.n_gap_abstained,
                slice_sum_gap: summary.sum_gap,
            },
        );
        let path = dir.join(format!("{name}.v82"));
        a.write(&path)?;
        Ok(path)
    }

    /// A minimal cube-reduced fixture: gap_status + legal_hindsight_gap.
    fn write_cube_fixture(dir: &Path) -> std::io::Result<std::path::PathBuf> {
        let mut a = evidence::Artifact::new(
            "cube-reduced",
            "VALUES",
            serde_json::json!({
                "hash_encoding": HASH_ENCODING,
                "generator_version": regret::GENERATOR_VERSION,
            }),
            "candidate_id",
        );
        let c_gs = a.add_column("gap_status", DType::DictStr);
        let c_gap = a.add_column("legal_hindsight_gap", DType::F64);
        let rows: [(&str, Option<f64>); 4] = [
            (regret::GAP_COMPUTED, Some(0.5)),
            (regret::GAP_COMPUTED, Some(1.0)),
            (regret::GAP_ABSTAINED_CENSORED, None),
            (regret::GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION, None),
        ];
        for (status, gap) in rows {
            a.columns[c_gs].push_str(status);
            match gap {
                Some(v) => a.columns[c_gap].push_f64(v),
                None => {
                    a.columns[c_gap].push_f64(0.0);
                    a.columns[c_gap].push_absent();
                }
            }
            a.end_row();
        }
        let path = dir.join(LEDGER_FILENAME);
        a.write(&path)?;
        Ok(path)
    }

    #[test]
    fn report_artifact_round_trips() {
        let dir = test_dir("rt");
        let p = write_report_fixture(&dir, "report-fixture", &evidence::generator_tag(), "tape-hash-1111", "ledger-fixture").unwrap();
        let back = evidence::read_artifact(&p).unwrap();
        assert_eq!(back.header["artifact_kind"], "report");
        assert_eq!(back.header["tier"], "VALUES");
        assert_eq!(back.header["hash_encoding"], HASH_ENCODING);
        assert_eq!(back.row_count(), 1);
        assert_eq!(back.header["column_count"], 5);
        for k in RunConstants::REQUIRED_KEYS {
            assert!(back.header["run_constants"].get(k).is_some(), "missing §3 key {k}");
        }
        for k in ["symbol", "interval", "generator"] {
            assert!(back.header["run_constants"].get(k).is_some(), "missing binding {k}");
        }
        for k in REPORT_RUN_CONSTANT_KEYS {
            assert!(back.header["run_constants"].get(k).is_some(), "missing report key {k}");
        }
        assert_eq!(back.header["run_constants"]["ledger_hash"], "ledger-fixture");
        assert_eq!(back.header["run_constants"]["verdict"], REPORT_VERDICT);
        assert_eq!(back.header["run_constants"]["candidate_count"], 3);
        assert_eq!(back.header["run_constants"]["symbol"], "SOLUSDT");
        let sk = back.column("slice_key").unwrap();
        assert_eq!(sk[0].as_ref().and_then(Value::as_str), Some("SOLUSDT"));
        let sn = back.column("slice_n").unwrap();
        assert_eq!(sn[0].as_ref().and_then(Value::as_i64), Some(3));
        let sg = back.column("slice_sum_gap").unwrap();
        assert_eq!(
            sg[0].as_ref().and_then(Value::as_f64).map(f64::to_bits),
            Some(1.5f64.to_bits())
        );
        // Content-addressed fingerprint.
        assert_eq!(evidence::fingerprint(&p).unwrap(), evidence::fingerprint(&p).unwrap());
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn audit_flags_a_stale_report() {
        let dir = test_dir("stale");
        // A report written by an older producer against an older tape. The
        // report binds no ledger (LEDGER_ABSENT), so the freshness failure is
        // the tape + producer drift alone.
        let p = write_report_fixture(&dir, "report-stale", "v8-core/0.1.0", "stale-tape-hash-0000", LEDGER_ABSENT).unwrap();
        let err = audit_freshness(&p, &dir, "current-tape-hash-9999", "v8-core/0.2.0").unwrap_err();
        assert!(err.contains("stale-tape-hash-0000"), "{err}");
        assert!(err.contains("older than current"), "{err}");
        assert!(err.contains("v8-core/0.1.0"), "{err}");
        assert!(err.contains("not the current"), "{err}");
        // A fresh report is not stale.
        let q = write_report_fixture(&dir, "report-fresh", "v8-core/0.2.0", "tape-hash-1111", LEDGER_ABSENT).unwrap();
        audit_freshness(&q, &dir, "tape-hash-1111", "v8-core/0.2.0").expect("fresh report passes");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn audit_flags_a_replaced_ledger() {
        let dir = test_dir("ledger");
        // Write a cube-reduced ledger, bind the report to its fingerprint,
        // then replace the ledger: the report is now stale.
        let cube = write_cube_fixture(&dir).unwrap();
        let ledger_fp = evidence::fingerprint(&cube).unwrap();
        let rc = report_run_constants("tape-hash-1111", regret::GENERATOR_VERSION, &["SOLUSDT".to_string()], "1h");
        let summary = summary_fixture();
        let mut a = report_artifact(
            ArtifactTier::Values,
            "SOLUSDT",
            "1h",
            &evidence::generator_tag(),
            &rc,
            &ledger_fp,
            &summary,
        );
        let cols = add_report_slice_fields(&mut a).unwrap();
        push_report_slice(&mut a, &cols, &ReportSlice {
            slice_key: "SOLUSDT".to_string(),
            slice_n: summary.candidate_count,
            slice_n_gap_computed: summary.n_gap_computed,
            slice_n_gap_abstained: summary.n_gap_abstained,
            slice_sum_gap: summary.sum_gap,
        });
        let p = dir.join("report-ledger-stale.v82");
        a.write(&p).unwrap();
        audit_freshness(&p, &dir, "tape-hash-1111", &evidence::generator_tag())
            .expect("ledger matches — fresh");
        // Replace the ledger bytes.
        let mut cube2 = evidence::Artifact::new(
            "cube-reduced",
            "VALUES",
            serde_json::json!({"hash_encoding": HASH_ENCODING}),
            "candidate_id",
        );
        let g = cube2.add_column("gap_status", DType::DictStr);
        cube2.columns[g].push_str(regret::GAP_COMPUTED);
        cube2.end_row();
        cube2.write(&cube).unwrap();
        let err = audit_freshness(&p, &dir, "tape-hash-1111", &evidence::generator_tag()).unwrap_err();
        assert!(err.contains("older than current"), "{err}");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn report_tier_honesty() {
        // An IDENTITY_ONLY report cannot carry the VALUES slice columns; the
        // failure is explicit, never an empty column.
        let rc = report_run_constants("tape-hash-1111", regret::GENERATOR_VERSION, &["SOLUSDT".to_string()], "1h");
        let summary = summary_fixture();
        let mut a = report_artifact(
            ArtifactTier::IdentityOnly,
            "SOLUSDT",
            "1h",
            &evidence::generator_tag(),
            &rc,
            "ledger-fixture",
            &summary,
        );
        let err = add_report_slice_fields(&mut a).unwrap_err();
        assert_eq!(err.field, "slice_n");
        assert_eq!(err.field_tier, FieldTier::Values);
        assert_eq!(err.artifact_tier, ArtifactTier::IdentityOnly);
        assert_eq!(a.columns.len(), 1, "the violating field is never stubbed");

        // VALUES accepts every slice field, and the on-disk audit agrees.
        let mut v = report_artifact(
            ArtifactTier::Values,
            "SOLUSDT",
            "1h",
            &evidence::generator_tag(),
            &rc,
            "ledger-fixture",
            &summary,
        );
        assert!(add_report_slice_fields(&mut v).is_ok());
        let dir = test_dir("tier");
        let p = dir.join("report-tier-honesty.v82");
        v.write(&p).unwrap();
        audit_tier_honesty(&p).expect("VALUES report serves its fields");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn summary_counts_gap_statuses_with_fsum() {
        let dir = test_dir("summary");
        let cube = write_cube_fixture(&dir).unwrap();
        let back = evidence::read_artifact(&cube).unwrap();
        let s = summarize_cube_reduced(&back);
        assert_eq!(s.candidate_count, 4);
        assert_eq!(s.n_gap_computed, 2);
        assert_eq!(s.n_gap_abstained, 1);
        assert_eq!(s.n_gap_not_applicable, 1);
        // fsum of [0.5, 1.0] — bit-identical to the oracle's math.fsum.
        assert_eq!(s.sum_gap.to_bits(), 1.5f64.to_bits());
        assert_eq!(s.verdict, REPORT_VERDICT);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn report_audit_battery_all_six_pass_on_fresh_report() {
        let dir = test_dir("battery");
        // A fresh report bound to a present ledger and retained tape.
        let cube = write_cube_fixture(&dir).unwrap();
        let ledger_fp = evidence::fingerprint(&cube).unwrap();
        let rc = report_run_constants("tape-hash-1111", regret::GENERATOR_VERSION, &["SOLUSDT".to_string()], "1h");
        let summary = summary_fixture();
        let mut a = report_artifact(
            ArtifactTier::Values,
            "SOLUSDT",
            "1h",
            &evidence::generator_tag(),
            &rc,
            &ledger_fp,
            &summary,
        );
        let cols = add_report_slice_fields(&mut a).unwrap();
        push_report_slice(&mut a, &cols, &ReportSlice {
            slice_key: "SOLUSDT".to_string(),
            slice_n: summary.candidate_count,
            slice_n_gap_computed: summary.n_gap_computed,
            slice_n_gap_abstained: summary.n_gap_abstained,
            slice_sum_gap: summary.sum_gap,
        });
        let p = dir.join("report-battery.v82");
        a.write(&p).unwrap();
        let store_path = dir.join("report-battery-retention.jsonl");
        std::fs::remove_file(&store_path).ok();
        let mut store = evidence::RetentionStore::open(&store_path).unwrap();
        store.insert("tape-hash-1111", true).unwrap();
        let checks = audit_report(&p, &dir, &store_path, "tape-hash-1111", &evidence::generator_tag());
        assert_eq!(checks.len(), 6);
        for c in &checks {
            assert!(c.passed, "{} failed: {}", c.name, c.detail);
        }
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn report_without_ledger_is_minimal_and_passes() {
        // The supported minimal mode: no cube-reduced artifact present. The
        // report binds LEDGER_ABSENT, the audit's freshness/retention checks
        // accept the honest absence, and the §8 battery still passes.
        let dir = test_dir("minimal");
        let rc = report_run_constants("tape-hash-1111", regret::GENERATOR_VERSION, &["SOLUSDT".to_string()], "1h");
        let mut a = report_artifact(
            ArtifactTier::Values,
            "SOLUSDT",
            "1h",
            &evidence::generator_tag(),
            &rc,
            LEDGER_ABSENT,
            &empty_summary(),
        );
        let cols = add_report_slice_fields(&mut a).unwrap();
        push_report_slice(&mut a, &cols, &ReportSlice {
            slice_key: "all".to_string(),
            slice_n: 0,
            slice_n_gap_computed: 0,
            slice_n_gap_abstained: 0,
            slice_sum_gap: 0.0,
        });
        let p = dir.join("report-minimal.v82");
        a.write(&p).unwrap();
        assert_eq!(evidence::read_header(&p).unwrap()["run_constants"]["ledger_hash"], LEDGER_ABSENT);
        let store_path = dir.join("report-minimal-retention.jsonl");
        std::fs::remove_file(&store_path).ok();
        let mut store = evidence::RetentionStore::open(&store_path).unwrap();
        store.insert("tape-hash-1111", true).unwrap();
        for c in audit_report(&p, &dir, &store_path, "tape-hash-1111", &evidence::generator_tag()) {
            assert!(c.passed, "{} failed: {}", c.name, c.detail);
        }
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn diagnostics_retirement_table_covers_the_shims() {
        // issue #125: the four re-export shims are named as retiring.
        let joined: Vec<&str> = DIAGNOSTICS_RETIREMENT
            .iter()
            .map(|(s, _)| *s)
            .collect::<Vec<_>>();
        let table = joined.join(" ");
        for shim in ["diagnostic.py", "diagnostic_report.py", "multi_diagnostic.py", "forensics.py"] {
            assert!(table.contains(shim), "retirement table must name {shim}");
        }
        // The report centre's own entry points port or retire — every row has
        // a stated fate.
        assert!(table.contains("run_diagnostic"));
        assert!(table.contains("render_html"));
    }
}
