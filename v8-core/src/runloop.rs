//! S4 full per-bar loop (issue #105): ExpertPlane -> candidates -> reduce.
//!
//! The `evaluate` subcommand is the composition point: per bar x per symbol,
//! for each expert in the DECLARED dispatch order (`dispatch_order`): build
//! the D-053-projected FeatMap (`features::group_closure` +
//! `project_features`; `history` is withheld unless the closure includes it),
//! evaluate, and feed CANDIDATE drafts into the candidate machinery in
//! candidate.rs.
//!
//! The dispatch order is the declared exposure-slot selection rule (issue
//! #68): ascending `sha1(expert_id)` (Canon-encoded). It replaces the implicit
//! alphabetical ranker (`lab.run` PHASE 3's `sorted_experts`), which let the
//! ExposureBook admit whichever expert fires first in alphabetical expert_id
//! order — an adverse-selection artefact that gave `bollinger_breakout` ~38%
//! of executions. The rule is deterministic, ledger-stable and economically
//! neutral (uncorrelated with alphabetical layout AND with signal merit); it
//! is NOT a merit ranker (V8_CONSTITUTION rules 6/14 keep the ranker ABSENT) —
//! it makes the previously implicit selection explicit. Slot conflicts for an
//! (instrument, direction) resolve to the candidate whose expert evaluates
//! first in this order.
//!
//! Per CANDIDATE decision the loop mirrors `lab.run`'s Phase 3 admission
//! ordering:
//! 1. D-026 episode-key dedup (`CandidateRegistry::is_duplicate`; a duplicate
//!    logs a `suppressed_duplicate` record and is NOT admitted);
//! 2. the DETECTED transition with its immutable birth snapshot
//!    (CANDIDATE_LIFECYCLE_SPEC §1);
//! 3. the D-024 tradability-mask veto (data-plane integrity);
//! 4. RiskGate admission (ExposureBook one-exposure-per-(instrument,
//!    direction) + heat caps) — a rejected draft logs the DETECTED->REJECTED
//!    transition and stays out of the registry's pending population;
//! 5. the DETECTED->PENDING transition — the admitted candidate.
//!
//! Admitted candidates then run the S2 ReplayKernel (backend::scalar) and feed
//! the S3 CubeReducer (regret.rs) per candidate, mirroring lab.run Phases
//! 1a/1b/2/3 — the entry is the next bar's close (`entry_bar = i + 1`), the
//! window is the tape tail, and the reduced cells are persisted to a
//! `cube-reduced.v82` artifact.
//!
//! The value-level population parity gate is issue #102 (a separate harness);
//! the module-level tests are the structural smoke tests (candidate count vs
//! the direct evaluate() dispatch, D-026 dedup, portfolio rejection).

use std::collections::HashMap;
use std::io::Write;
use std::path::PathBuf;

use serde_json::Value;

use crate::backend::scalar::ScalarKernel;
use crate::backend::ReplayCell;
use crate::candidate::{
    episode_key, geometry_version, tradability_mask_veto, CandidateRegistry, RiskGate,
    DEFAULT_CLUSTERS,
};
use crate::data;
use crate::evidence;
use crate::experts;
use crate::features;
use crate::hash;
use crate::regret;
use crate::scheduler;
use crate::simulator::{self, SimulatorParams};
use crate::state::{self, FeatureStore};

/// The bounded prior window for the pre-entry invalidation fallback
/// (D-034 / D-059, issue #66): the extreme over the `PRIOR_WINDOW_BARS` bars
/// before the birth bar, never the all-bars prefix extreme — the prefix
/// extreme is pinned by an old spike and made the gate dead code for the six
/// experts that freeze no `prior_*_ref`.
const PRIOR_WINDOW_BARS: usize = state::HISTORY_DEPTH_DEFAULT;

// ---------------------------------------------------------------------------
// Request
// ---------------------------------------------------------------------------

/// One evaluation request for the S4 evaluate loop (the control plane's
/// request.json). `out_dir` and `history_depth` are optional so a bare
/// `{tape_path, universe}` request runs; `max_heat` / `max_cluster_heat`
/// override the oracle's RiskGate defaults and `experts` narrows the dispatch
/// table to a subset (canonical TABLE order is preserved; empty = all 28).
#[derive(Debug, serde::Deserialize)]
struct EvaluateRequest {
    tape_path: PathBuf,
    #[serde(default)]
    universe: Vec<String>,
    #[serde(default = "default_out_dir")]
    out_dir: PathBuf,
    #[serde(default = "default_history_depth")]
    history_depth: usize,
    #[serde(default)]
    experts: Vec<String>,
    #[serde(default = "default_max_heat")]
    max_heat: f64,
    #[serde(default = "default_max_cluster_heat")]
    max_cluster_heat: f64,
    #[serde(default = "default_base_interval")]
    base_interval: String,
    /// Task-parallel worker count for the S2 replay batch (scheduler.rs,
    /// D-096 Backend-1); a scheduling detail that appears in no hash (D-084)
    /// and leaves every artifact byte-identical across thread counts (G5).
    #[serde(default = "default_threads")]
    threads: usize,
    #[serde(default)]
    manifest: Value,
}

fn default_threads() -> usize {
    1
}

fn default_out_dir() -> PathBuf {
    PathBuf::from("out")
}
fn default_history_depth() -> usize {
    state::HISTORY_DEPTH_DEFAULT
}
fn default_max_heat() -> f64 {
    3.0
}
fn default_max_cluster_heat() -> f64 {
    2.0
}
fn default_base_interval() -> String {
    "1h".to_string()
}

// ---------------------------------------------------------------------------
// Subcommand entry
// ---------------------------------------------------------------------------

pub fn run(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core evaluate <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error: cannot read request: {e}");
            return 1;
        }
    };
    let req: EvaluateRequest = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    match evaluate(&req) {
        Ok(summary) => {
            println!("{}", serde_json::to_string(&summary).unwrap());
            0
        }
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

// ---------------------------------------------------------------------------
// The loop
// ---------------------------------------------------------------------------

/// S6 analysis composition entry (issue #116): run the full S4 evaluate loop
/// over the tape with the analysis request's fields — full 28-expert table,
/// default history depth and risk caps, 1h interval — writing evaluations.jsonl,
/// candidates.jsonl and cube-reduced.v82 into `out_dir`. Returns the loop's
/// summary (the caller reads the ledger files it names).
pub fn run_for_analysis(
    tape_path: &PathBuf,
    universe: &[String],
    out_dir: &PathBuf,
    manifest: &Value,
) -> Result<Value, String> {
    let req = EvaluateRequest {
        tape_path: tape_path.clone(),
        universe: universe.to_vec(),
        out_dir: out_dir.clone(),
        history_depth: default_history_depth(),
        experts: Vec::new(),
        max_heat: default_max_heat(),
        max_cluster_heat: default_max_cluster_heat(),
        base_interval: default_base_interval(),
        threads: default_threads(),
        manifest: manifest.clone(),
    };
    evaluate(&req)
}

/// One admitted (PENDING) candidate, held for the S2/S3 reduce pass.
struct PendingCandidate {
    candidate_id: String,
    direction: String,
    birth_time: i64,
    entry_bar: usize,
    risk_geometry: serde_json::Map<String, Value>,
    symbol: String,
    /// Pre-entry invalidation levels (issue #66 / D-059): the frozen
    /// `prior_low_ref` / `prior_high_ref` when the draft declares one, else
    /// the bounded windowed extreme over the bars before birth (D-034).
    prior_low: f64,
    prior_high: f64,
}

/// The bounded windowed prior extreme over the `PRIOR_WINDOW_BARS` bars before
/// `birth`: `(prior_low, prior_high)` = `(min(lows), max(highs))` over
/// `[birth - W, birth)`. Both `None` when the window is empty — the caller
/// fails closed rather than defaulting to 0.0/inf (issue #66 / D-059).
fn windowed_prior_extremes(highs: &[f64], lows: &[f64], birth: usize)
    -> (Option<f64>, Option<f64>) {
    let lo = birth.saturating_sub(PRIOR_WINDOW_BARS);
    if lo >= birth {
        return (None, None);
    }
    let low = lows[lo..birth].iter().cloned().fold(f64::INFINITY, f64::min);
    let high = highs[lo..birth].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    (Some(low), Some(high))
}

/// The declared exposure-slot selection rule (issue #68): the dispatch order
/// is ascending `sha1(expert_id)` (Canon-encoded — the same digest family as
/// episode identity). The implicit alphabetical ranker is gone; this order is
/// the deterministic, economically-neutral tie-break for ExposureBook
/// (instrument, direction) slot conflicts. Stable across runs and uncorrelated
/// with both alphabetical layout and signal merit.
fn dispatch_order() -> Vec<(&'static str, &'static str)> {
    let mut ids: Vec<&'static str> = experts::TABLE.iter().map(|(id, _, _, _)| *id).collect();
    ids.sort_by_key(|id| {
        let mut c = crate::hash::Canon::new();
        c.push_str(id);
        c.finish_sha1_hex()
    });
    ids.into_iter()
        .map(|id| {
            let (_, _, ver, _) = experts::TABLE.iter()
                .find(|(e, _, _, _)| *e == id)
                .expect("dispatch order only contains registered expert_ids");
            (id, *ver)
        })
        .collect()
}

fn evaluate(req: &EvaluateRequest) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = data::Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;

    let universe: Vec<String> = if req.universe.is_empty() {
        stores.iter().map(|s| s.symbol.clone()).collect()
    } else {
        req.universe.clone()
    };

    let sim = SimulatorParams::from_json(&req.manifest);
    let mut funding_schedule: Vec<(i64, f64)> = ds.rows.iter()
        .filter(|r| r.channel == "funding")
        .map(|r| (r.event_time, r.payload["funding_rate"].as_f64().unwrap_or(0.0)))
        .collect();
    funding_schedule.sort_by_key(|(t, _)| *t);
    let interval_ns = interval_ns_for(&req.base_interval);

    // Dispatch table in the declared exposure-slot selection order (issue
    // #68): ascending sha1(expert_id) — deterministic, non-alphabetical,
    // economically neutral. The evaluation/DETECTED record order (part of the
    // ledger hash) AND the ExposureBook slot-conflict tie-break both follow
    // this order; the requested subset keeps it.
    let table: Vec<(&str, &str)> = if req.experts.is_empty() {
        dispatch_order()
    } else {
        dispatch_order().into_iter()
            .filter(|(id, _)| req.experts.iter().any(|e| e == id))
            .collect()
    };

    let eval_path = req.out_dir.join("evaluations.jsonl");
    let cand_path = req.out_dir.join("candidates.jsonl");
    let mut eval_out = writer(&eval_path)?;
    let mut cand_out = writer(&cand_path)?;

    let mut registry = CandidateRegistry::new();
    let mut gate = RiskGate::new(req.max_heat, req.max_cluster_heat,
        DEFAULT_CLUSTERS.iter().map(|(s, c)| (s.to_string(), c.to_string())).collect());

    let max_bar_range_frac = req.manifest.get("max_bar_range_frac")
        .and_then(|v| v.as_f64()).unwrap_or(0.05);
    let funding_window_bars = req.manifest.get("funding_window_bars")
        .and_then(|v| v.as_i64()).unwrap_or(1);

    let mut n_candidates = 0usize;
    let mut n_suppressed = 0usize;
    let mut n_rejected = 0usize;
    let mut n_evaluations = 0usize;
    let mut pending: Vec<PendingCandidate> = Vec::new();

    for store in &stores {
        let sym = &store.symbol;
        if !universe.iter().any(|u| u == sym) {
            continue;
        }
        let n_bars = store.closes.len();
        for i in 0..n_bars {
            let t = i + 1;
            let as_of = store.avail[i];
            let feats = state::state_features(store, t, as_of, req.history_depth);
            let mut map: HashMap<String, state::Feature> = HashMap::new();
            for f in &feats {
                map.insert(f.name.clone(), f.clone());
            }
            let state_quality = if feats.iter().any(|f| f.quality == "DEGRADED") {
                "DEGRADED"
            } else {
                "COMPLETE"
            };
            let bar_map = bar_payload(store, i);

            for (eid, ver) in &table {
                // D-053 projection: each expert sees only its requires-closure;
                // a feature outside it is withheld (features.rs — the same
                // withholding the Python view applies).
                let closure = features::group_closure(experts::requires_for(eid));
                let projected = features::project_features(&map, &closure);
                let hist = if features::history_allowed(&closure) {
                    state::history_bars(store, t, req.history_depth)
                } else {
                    Vec::new()
                };
                let fm = experts::base::FeatMap {
                    features: &projected,
                    history: hist,
                    as_of,
                    symbol: sym,
                };
                let ev = experts::evaluate(eid, &fm);
                n_evaluations += 1;
                write_evaluation(&mut eval_out, eid, ver, sym, as_of, &ev)?;
                if ev.decision != "CANDIDATE" {
                    continue;
                }
                let draft = match &ev.draft {
                    Some(d) => d,
                    None => continue,
                };
                let anchor = match &ev.setup_anchor_event_id {
                    Some(a) => a,
                    None => continue,
                };
                // D-026 episode identity anchored to the setup EVIDENCE event.
                let gv = geometry_version(&draft.risk_geometry);
                let cid = episode_key(eid, ver, sym, &draft.direction, anchor, &gv);
                if registry.is_duplicate(&cid) {
                    write_line(&mut cand_out, &serde_json::json!({
                        "kind": "suppressed_duplicate",
                        "candidate_id": cid,
                        "birth_time": as_of,
                        "expert_id": eid,
                        "source": "expert",
                        "event_id": format!("{cid}:suppressed:{as_of}"),
                    }))?;
                    n_suppressed += 1;
                    continue;
                }
                // Immutable birth snapshot on the DETECTED transition
                // (CANDIDATE_LIFECYCLE_SPEC §1): expert identity, setup
                // evidence and the geometry version.
                let (event_hash, seq, event_id) =
                    registry.apply(&cid, None, "DETECTED", "setup_detected", as_of)?;
                write_line(&mut cand_out, &serde_json::json!({
                    "kind": "transition",
                    "candidate_id": cid,
                    "sequence": seq,
                    "from_state": Value::Null,
                    "to_state": "DETECTED",
                    "reason_code": "setup_detected",
                    "knowledge_time": as_of,
                    "event_hash": event_hash,
                    "event_id": event_id,
                    "source": "lifecycle",
                    "expert_id": eid,
                    "expert_version": ver,
                    "instrument": sym,
                    "direction": draft.direction,
                    "setup_anchor_event_id": anchor,
                    "geometry_version": gv,
                }))?;
                // D-024 mechanical tradability mask (data-plane integrity
                // veto; src/v8/risk.py `tradability_mask_veto`).
                let (vetoed, reason) = tradability_mask_veto(
                    &bar_map, state_quality, as_of,
                    max_bar_range_frac, funding_window_bars,
                    sim.funding_hours, interval_ns);
                if vetoed {
                    reject(&mut registry, &mut cand_out, &cid, as_of,
                           reason.as_deref().unwrap_or("TRADABILITY_MASK_VETO"))?;
                    n_rejected += 1;
                    continue;
                }
                // Risk admission: ExposureBook (rule 16: one active exposure
                // per (instrument, direction)) then heat caps.
                let size = draft.risk_geometry.get("size").and_then(|v| v.as_f64()).unwrap_or(1.0);
                let stop_r = draft.risk_geometry.get("stop_r").and_then(|v| v.as_f64()).unwrap_or(1.0);
                let verdict = gate.admit(sym, &draft.direction, size, stop_r);
                if !verdict.ok {
                    reject(&mut registry, &mut cand_out, &cid, as_of,
                           verdict.reason_code.as_deref().unwrap_or("risk_rejected"))?;
                    n_rejected += 1;
                    continue;
                }
                let (event_hash, seq, event_id) = registry.apply(
                    &cid, Some("DETECTED"), "PENDING", "hypothesis_completed", as_of)?;
                write_line(&mut cand_out, &serde_json::json!({
                    "kind": "transition",
                    "candidate_id": cid,
                    "sequence": seq,
                    "from_state": "DETECTED",
                    "to_state": "PENDING",
                    "reason_code": "hypothesis_completed",
                    "knowledge_time": as_of,
                    "event_hash": event_hash,
                    "event_id": event_id,
                    "source": "lifecycle",
                }))?;
                // Entry is the next bar's close (lab.run PHASE 2: a candidate
                // born at bar i enters at i + 1).
                // Pre-entry invalidation levels (issue #66 / D-059): the
                // frozen `prior_*_ref` when the draft declares one, else the
                // bounded windowed extreme over the bars before birth
                // (D-034). The all-bars prefix-extreme state feature is NEVER
                // used here — an old spike outside the window pins it and
                // makes the gate dead code for experts that freeze no ref.
                let frozen_low = draft.risk_geometry.get("prior_low_ref").and_then(|v| v.as_f64());
                let frozen_high = draft.risk_geometry.get("prior_high_ref").and_then(|v| v.as_f64());
                let (win_low, win_high) = windowed_prior_extremes(&store.highs, &store.lows, i);
                let prior_low = frozen_low.or(win_low).ok_or_else(|| format!(
                    "{sym} no prior bars at birth {as_of} to derive a windowed invalidation level for {eid} — refuse, never default to 0/inf"))?;
                let prior_high = frozen_high.or(win_high).ok_or_else(|| format!(
                    "{sym} no prior bars at birth {as_of} to derive a windowed invalidation level for {eid} — refuse, never default to 0/inf"))?;
                pending.push(PendingCandidate {
                    candidate_id: cid,
                    direction: draft.direction.clone(),
                    birth_time: draft.birth_time,
                    entry_bar: i + 1,
                    risk_geometry: draft.risk_geometry.clone(),
                    symbol: sym.clone(),
                    prior_low,
                    prior_high,
                });
                n_candidates += 1;
            }
        }
    }
    eval_out.flush().map_err(|e| e.to_string())?;
    cand_out.flush().map_err(|e| e.to_string())?;

    // S2 + S3: replay each admitted candidate and reduce the outcome cube.
    // The replay batch runs on `req.threads` worker threads (scheduler.rs);
    // threads=1 vs N must produce byte-identical artifacts (G5).
    let reduced_path = req.out_dir.join("cube-reduced.v82");
    let n_reduced = write_cube_reduced(
        &reduced_path, &pending, &stores, &ds, &sim, &funding_schedule, req.threads)?;

    Ok(serde_json::json!({
        "subcommand": "evaluate",
        "n_candidates": n_candidates,
        "n_suppressed": n_suppressed,
        "n_rejected": n_rejected,
        "n_evaluations": n_evaluations,
        "n_reduced": n_reduced,
        "evaluations": eval_path.to_string_lossy(),
        "candidates": cand_path.to_string_lossy(),
        "cube_reduced": reduced_path.to_string_lossy(),
    }))
}

/// Read a JSONL tape into parsed `TapeRow`s using the Python-json-compatible
/// parser (the tape is written by CPython `json.dumps`, which may emit
/// `NaN`/`Infinity` literals that strict JSON rejects).
fn read_tape(path: &PathBuf) -> Result<Vec<data::TapeRow>, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("cannot read tape {path:?}: {e}"))?;
    let mut rows = Vec::new();
    for (i, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed = crate::jsonx::parse_line(line)
            .map_err(|e| format!("tape line {}: {e}", i + 1))?;
        let row = data::TapeRow::from_parts(&parsed.value, parsed.nonfinite)
            .map_err(|e| format!("tape line {}: {e}", i + 1))?;
        rows.push(row);
    }
    Ok(rows)
}

fn interval_ns_for(base: &str) -> i64 {
    let m = 60_000_000_000i64; // one minute in ns
    match base {
        "1m" => m,
        "5m" => 5 * m,
        "15m" => 15 * m,
        "30m" => 30 * m,
        "1h" => state::HOUR_NS,
        "4h" => 4 * state::HOUR_NS,
        "1d" => state::DAY_NS,
        _ => state::HOUR_NS,
    }
}

/// The current bar's payload map for the D-024 mask.
fn bar_payload(store: &FeatureStore, i: usize) -> serde_json::Map<String, Value> {
    let mut m = serde_json::Map::new();
    m.insert("open".to_string(), serde_json::json!(store.opens[i]));
    m.insert("high".to_string(), serde_json::json!(store.highs[i]));
    m.insert("low".to_string(), serde_json::json!(store.lows[i]));
    m.insert("close".to_string(), serde_json::json!(store.closes[i]));
    m.insert("volume".to_string(), serde_json::json!(store.volumes[i]));
    m.insert("closed".to_string(), serde_json::json!(true));
    m
}

// ---------------------------------------------------------------------------
// Ledger writers
// ---------------------------------------------------------------------------

fn writer(path: &PathBuf) -> Result<std::io::BufWriter<std::fs::File>, String> {
    let f = std::fs::File::create(path).map_err(|e| format!("create {path:?}: {e}"))?;
    Ok(std::io::BufWriter::new(f))
}

fn write_line(out: &mut impl Write, v: &Value) -> Result<(), String> {
    let mut line = serde_json::to_string(v).map_err(|e| e.to_string())?;
    line.push('\n');
    out.write_all(line.as_bytes()).map_err(|e| e.to_string())
}

/// One evaluation record, mirroring lab's evaluations.jsonl ExpertEvaluation
/// (`knowledge_time` = the decision clock; the draft mirrors CandidateDraft).
fn write_evaluation(out: &mut impl Write, eid: &str, ver: &str, sym: &str, as_of: i64,
                    ev: &experts::base::ExpertEval) -> Result<(), String> {
    let draft = ev.draft.as_ref().map(|d| serde_json::json!({
        "expert_id": eid,
        "expert_version": ver,
        "instrument": sym,
        "direction": d.direction,
        "setup_fingerprint": ev.setup_fingerprint,
        "risk_geometry": d.risk_geometry,
        "birth_time": d.birth_time,
        "setup_anchor_event_id": ev.setup_anchor_event_id,
        "size": 1.0,
    }));
    write_line(out, &serde_json::json!({
        "knowledge_time": as_of,
        "expert_id": eid,
        "version": ver,
        "applicability": ev.applicability,
        "decision": ev.decision,
        "draft": draft,
    }))
}

/// DETECTED -> REJECTED with the reason, and the ledger record.
fn reject(registry: &mut CandidateRegistry, out: &mut impl Write, cid: &str,
          as_of: i64, reason: &str) -> Result<(), String> {
    let (event_hash, seq, event_id) =
        registry.apply(cid, Some("DETECTED"), "REJECTED", reason, as_of)?;
    write_line(out, &serde_json::json!({
        "kind": "transition",
        "candidate_id": cid,
        "sequence": seq,
        "from_state": "DETECTED",
        "to_state": "REJECTED",
        "reason_code": reason,
        "knowledge_time": as_of,
        "event_hash": event_hash,
        "event_id": event_id,
        "source": "lifecycle",
    }))
}

// ---------------------------------------------------------------------------
// S2 ReplayKernel (backend::scalar) + S3 CubeReducer per admitted candidate
// ---------------------------------------------------------------------------

fn push_opt_f64(col: &mut evidence::Column, v: Option<f64>) {
    match v {
        Some(x) => col.push_f64(x),
        None => {
            col.push_f64(0.0);
            col.push_absent();
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn write_cube_reduced(path: &PathBuf, pending: &[PendingCandidate],
                      stores: &[FeatureStore], ds: &data::Dataset,
                      sim: &SimulatorParams, funding_schedule: &[(i64, f64)],
                      threads: usize)
    -> Result<usize, String> {
    let mut art = evidence::Artifact::new(
        "cube-reduced",
        "VALUES",
        serde_json::json!({
            "hash_encoding": hash::HASH_ENCODING,
            "generator_version": regret::GENERATOR_VERSION,
        }),
        "candidate_id",
    );
    let c_cid = art.add_column("candidate_id", evidence::DType::DictStr);
    let c_mid = art.add_column("manifest_id", evidence::DType::DictStr);
    let c_aid = art.add_column("actual_action_id", evidence::DType::DictStr);
    let c_au = art.add_column("actual_utility", evidence::DType::F64);
    let c_bu = art.add_column("best_utility", evidence::DType::F64);
    let c_tie = art.add_column("tie_cardinality", evidence::DType::I64);
    let c_gap = art.add_column("legal_hindsight_gap", evidence::DType::F64);
    let c_gs = art.add_column("gap_status", evidence::DType::DictStr);
    let c_reason = art.add_column("abstention_reason", evidence::DType::DictStr);
    let c_nt = art.add_column("no_trade_value", evidence::DType::F64);
    let c_ok = art.add_column("n_ok", evidence::DType::I64);
    let c_ce = art.add_column("n_censored", evidence::DType::I64);
    let c_uf = art.add_column("n_undefined_future", evidence::DType::I64);
    let c_ne = art.add_column("n_not_evaluable_action", evidence::DType::I64);
    let c_no_entry = art.add_column("n_no_entry", evidence::DType::I64);
    let cols = [c_cid, c_mid, c_aid, c_au, c_bu, c_tie, c_gap, c_gs, c_reason,
                c_nt, c_ok, c_ce, c_uf, c_ne, c_no_entry];

    // Phase 1 — plan every (candidate, action) cell. Cells that need a kernel
    // run go into a replay batch (evaluated through the task scheduler on
    // `threads` worker threads); the rest are decided directly. The plan keeps
    // per-candidate manifest + cell slots so the reduce pass below stays in
    // candidate order (the single-writer ledger discipline).
    let mut batch: Vec<ReplayCell> = Vec::new();
    let mut dests: Vec<(usize, usize)> = Vec::new();
    let mut manifests: Vec<regret::Manifest> = Vec::with_capacity(pending.len());
    let mut planned: Vec<Vec<Option<regret::Cell>>> = Vec::with_capacity(pending.len());

    for (ci, cand) in pending.iter().enumerate() {
        let store = stores.iter().find(|s| s.symbol == cand.symbol)
            .ok_or_else(|| format!("no bars for symbol {}", cand.symbol))?;
        let bars = ds.bars.iter().find(|b| b.symbol == cand.symbol)
            .ok_or_else(|| format!("no bars for symbol {}", cand.symbol))?;
        let manifest = regret::generate_legal_actions(&cand.risk_geometry);
        let window_end = store.closes.len();
        let entry_idx = cand.entry_bar;

        // Pre-entry invalidation re-checked on the entry bar itself
        // (CANDIDATE_LIFECYCLE_SPEC: a PENDING/TRIGGERED candidate ends on
        // invalidation_observed). The level is the frozen ref or the bounded
        // windowed extreme before birth (D-059) — never the unbounded all-bars
        // prefix state feature, which an old spike pins and which made the
        // gate dead code for the six ref-less experts (issue #66). A breached
        // candidate never enters: every legal action is a NO_ENTRY cell
        // (mirroring the oracle's `candidate has no actual entry bar`).
        let invalidated = entry_idx < window_end
            && ((cand.direction == "LONG" && bars.lows[entry_idx] < cand.prior_low)
                || (cand.direction == "SHORT" && bars.highs[entry_idx] > cand.prior_high));

        let mut plan: Vec<Option<regret::Cell>> = Vec::with_capacity(manifest.actions.len());
        for (ai, a) in manifest.actions.iter().enumerate() {
            if invalidated {
                plan.push(Some(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_NO_ENTRY,
                    reason: "candidate invalidated before entry (prior level breached)".into(),
                    net_utility: None,
                }));
                continue;
            }
            if a.kind == "NO_TRADE" {
                plan.push(Some(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_OK,
                    reason: String::new(),
                    net_utility: Some(0.0),
                }));
                continue;
            }
            if window_end.saturating_sub(entry_idx) <= regret::MIN_FUTURE_BARS {
                plan.push(Some(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_UNDEFINED_FUTURE,
                    reason: format!("fewer than {} bars of future after the entry bar — the simulator would return a manufactured EXPIRY value", regret::MIN_FUTURE_BARS + 1),
                    net_utility: None,
                }));
                continue;
            }
            let mut geom = cand.risk_geometry.clone();
            for (k, v) in &a.override_geom {
                geom.insert(k.clone(), v.clone());
            }
            let draft = simulator::Draft {
                direction: cand.direction.clone(),
                birth_time: cand.birth_time,
                risk_geometry: geom,
            };
            dests.push((ci, ai));
            batch.push(ReplayCell {
                symbol: &cand.symbol,
                draft,
                start: entry_idx,
                end: window_end,
                thesis: None,
            });
            plan.push(None); // filled from the batch outcome below
        }
        planned.push(plan);
        manifests.push(manifest);
    }

    // Phase 2 — one kernel per candidate (built once, never per cell —
    // COMPUTE_CORE_SPEC §5), then evaluate the replay batch on `threads`
    // worker threads. A per-cell Err is a task RESULT (the cube's
    // NOT_EVALUABLE_ACTION downgrade below); only a worker fault fails the
    // whole request (COMPUTE_SCHEDULING_SPEC §7).
    let mut kernels: Vec<ScalarKernel> = Vec::with_capacity(pending.len());
    for cand in pending {
        let store = stores.iter().find(|s| s.symbol == cand.symbol)
            .ok_or_else(|| format!("no bars for symbol {}", cand.symbol))?;
        let bars = ds.bars.iter().find(|b| b.symbol == cand.symbol)
            .ok_or_else(|| format!("no bars for symbol {}", cand.symbol))?;
        kernels.push(ScalarKernel {
            round_trip_cost_r: sim.round_trip_cost_r,
            funding_rate_r: sim.funding_rate_r,
            funding_hours: sim.funding_hours,
            fill_policy: sim.fill_policy,
            funding_schedule,
            round_trip_cost_bps: sim.round_trip_cost_bps,
            bars,
            store,
        });
    }
    let results = scheduler::parallel_map(threads, batch.len(), &|i| {
        let (ci, _ai) = dests[i];
        let cell = &batch[i];
        // S2 ReplayKernel via the SIMD path (Backend-1, #133): value-safe
        // `f64x2` lane math for barrier comparisons/extremes, bit-identical to
        // the scalar reference; drafts outside the SIMD value-safety guard
        // (trail/breakeven/scale-out/limit-fill) fall back to the exact
        // scalar kernel. An optimization may not change a value (D-088).
        kernels[ci].run_simd(&cell.draft, cell.start, cell.end, cell.thesis.as_ref())
    })?;

    // Phase 3 — classify every batch outcome into its planned cell slot, with
    // the exact sequential semantics: a per-cell replay error stays a
    // NOT_EVALUABLE_ACTION cell; NOT_EXECUTED resolves by trigger_ref
    // presence (D-057); MATURE is OK, everything else CENSORED.
    for (k, res) in results.iter().enumerate() {
        let (ci, ai) = dests[k];
        let cand = &pending[ci];
        let action = &manifests[ci].actions[ai];
        let cell = match res {
            Ok(out) => {
                if out.label_status == "NOT_EXECUTED" {
                    // D-057 (issue #67): a candidate whose declared entry
                    // trigger never confirmed (or was invalidated while
                    // waiting) never entered — every legal action is a NO_ENTRY
                    // cell, mirroring the oracle's `candidate has no actual
                    // entry bar` treatment (the same convention as invalidation
                    // before entry). A FILL_AT_LIMIT order that never traded
                    // through is a different case: the ACTION is not evaluable.
                    let (status, reason) = if cand.risk_geometry.contains_key("trigger_ref") {
                        (regret::CELL_NO_ENTRY,
                         "entry trigger never confirmed (close did not clear trigger_ref before expiry/invalidation)".into())
                    } else {
                        (regret::CELL_NOT_EVALUABLE_ACTION,
                         "action never filled on this tape (e.g. FILL_AT_LIMIT never traded through)".into())
                    };
                    regret::Cell {
                        action_id: action.action_id.clone(),
                        status,
                        reason,
                        net_utility: None,
                    }
                } else {
                    let status = if out.label_status == "MATURE" { regret::CELL_OK } else { regret::CELL_CENSORED };
                    regret::Cell {
                        action_id: action.action_id.clone(),
                        status,
                        reason: if status == regret::CELL_OK { String::new() } else {
                            "replay reached tape end before a terminal endpoint".into()
                        },
                        net_utility: Some(out.net_r),
                    }
                }
            }
            Err(e) => regret::Cell {
                action_id: action.action_id.clone(),
                status: regret::CELL_NOT_EVALUABLE_ACTION,
                reason: format!("replay raised: {e}"),
                net_utility: None,
            },
        };
        planned[ci][ai] = Some(cell);
    }

    // Phase 4 — reduce and write in candidate order (single-writer ledger).
    for (ci, cand) in pending.iter().enumerate() {
        let cells: Vec<regret::Cell> = planned[ci]
            .iter_mut()
            .map(|slot| slot.take().expect("every replay slot filled by the scheduler"))
            .collect();
        let row = regret::compute_gap(&cand.candidate_id, &manifests[ci], &cells);
        art.columns[cols[0]].push_str(&row.candidate_id);
        art.columns[cols[1]].push_str(&row.manifest_id);
        match &row.actual_action_id {
            Some(a) => art.columns[cols[2]].push_str(a),
            None => {
                art.columns[cols[2]].push_str("");
                art.columns[cols[2]].push_absent();
            }
        }
        push_opt_f64(&mut art.columns[cols[3]], row.actual_utility);
        push_opt_f64(&mut art.columns[cols[4]], row.best_utility);
        art.columns[cols[5]].push_i64(row.tie_cardinality as i64);
        push_opt_f64(&mut art.columns[cols[6]], row.legal_hindsight_gap);
        art.columns[cols[7]].push_str(row.gap_status);
        art.columns[cols[8]].push_str(&row.abstention_reason);
        push_opt_f64(&mut art.columns[cols[9]], row.no_trade_value);
        let n = |s: &str| *row.counts.get(s).unwrap_or(&0) as i64;
        art.columns[cols[10]].push_i64(n(regret::CELL_OK));
        art.columns[cols[11]].push_i64(n(regret::CELL_CENSORED));
        art.columns[cols[12]].push_i64(n(regret::CELL_UNDEFINED_FUTURE));
        art.columns[cols[13]].push_i64(n(regret::CELL_NOT_EVALUABLE_ACTION));
        art.columns[cols[14]].push_i64(n(regret::CELL_NO_ENTRY));
        art.end_row();
    }

    art.write(path).map_err(|e| format!("write cube artifact: {e}"))?;
    Ok(pending.len())
}

// ---------------------------------------------------------------------------
// Structural smoke tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// One kline TapeRow mirroring synth.make_synthetic_tape's record shape
    /// (FIXED_EPOCH_NS + i*HOUR_NS, 1s configured feed latency).
    fn bar(o: f64, h: f64, l: f64, c: f64, symbol: &str, i: usize) -> Value {
        let open_time = 1_750_000_000_000_000_000i64 + (i as i64) * state::HOUR_NS;
        let close_time = open_time + state::HOUR_NS - 1_000_000;
        let available = close_time + 1_000_000_000;
        serde_json::json!({
            "source": "binance-um",
            "channel": "kline",
            "instrument": symbol,
            "event_time": close_time,
            "available_time": available,
            "ingested_time": available,
            "venue_sequence": i as i64 + 1,
            "event_id": format!("{symbol}:{}", i + 1),
            "payload": {
                "open": o, "high": h, "low": l, "close": c,
                "volume": 1.0, "closed": true,
            },
        })
    }

    fn write_tape(rows: &[Value], tag: &str) -> PathBuf {
        let dir = std::env::temp_dir()
            .join(format!("v8core-runloop-{tag}-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("tape.jsonl");
        let mut s = String::new();
        for r in rows {
            s.push_str(&serde_json::to_string(r).unwrap());
            s.push('\n');
        }
        std::fs::write(&path, s).unwrap();
        path
    }

    fn req(tape: PathBuf, out: &str, experts: Vec<&str>, manifest: Value) -> EvaluateRequest {
        EvaluateRequest {
            tape_path: tape,
            universe: vec!["SOLUSDT".to_string()],
            out_dir: std::env::temp_dir()
                .join(format!("v8core-runloop-{out}-{}", std::process::id())),
            history_depth: state::HISTORY_DEPTH_DEFAULT,
            experts: experts.iter().map(|s| s.to_string()).collect(),
            // Generous caps: the smoke tests exercise the exposure book and
            // dedup, not the heat ladder (RiskGate's heat caps are covered by
            // candidate.rs's own tests).
            max_heat: 1000.0,
            max_cluster_heat: 1000.0,
            base_interval: "1h".to_string(),
            threads: default_threads(),
            // funding_window_bars: 0 disables the D-024 funding-window veto,
            // which depends on the tape's wall-clock alignment and would make
            // the structural counts flaky.
            manifest,
        }
    }

    /// A linear ramp (close 10.0 + 0.5*i, bar range 0.2): the canonical
    /// breakout fixture — close[t-1] exceeds the trailing 20-bar high on every
    /// bar t >= 22. Used by the candidate-count test (donchian_breakout fires
    /// from bar 21 onward with a single admitted episode and 38 identical
    /// duplicates).
    fn ramp_bars(n: usize) -> Vec<Value> {
        let mut rows = Vec::with_capacity(n);
        for i in 0..n {
            let p = 10.0 + 0.5 * (i as f64);
            rows.push(bar(p, p + 0.1, p - 0.1, p, "SOLUSDT", i));
        }
        rows
    }

    /// A 20-bar up-ramp (closes 10.0..19.5) followed by the given tail — the
    /// trend_pullback fixture. The ramp establishes fast > slow; a sharp dip
    /// then puts close below the slow EMA while the 5-EMA still leads (the
    /// pullback condition), and each pullback run re-anchors on its first dip
    /// bar.
    fn pullback_tape(tail: &[f64]) -> Vec<Value> {
        let mut rows = Vec::with_capacity(20 + tail.len());
        for i in 0..20 {
            let c = 10.0 + 0.5 * (i as f64);
            rows.push(bar(c, c + 0.3, c - 0.3, c, "SOLUSDT", i));
        }
        for (k, c) in tail.iter().enumerate() {
            let i = 20 + k;
            rows.push(bar(*c, *c + 0.3, *c - 0.3, *c, "SOLUSDT", i));
        }
        rows
    }

    fn direct_candidate_count(tape: &PathBuf, history_depth: usize,
                              experts: &[String]) -> usize {
        // Independent pass over the same stores: count CANDIDATE decisions the
        // dispatch table returns, with no registry/gate state.
        let rows = read_tape(tape).unwrap();
        let ds = data::Dataset::from_rows(rows).unwrap();
        let stores = state::build_stores(&ds);
        // Same declared dispatch order the loop uses (issue #68) — the direct
        // pass must mirror the loop's evaluation order exactly.
        let table: Vec<(&str, &str)> = if experts.is_empty() {
            dispatch_order()
        } else {
            dispatch_order().into_iter()
                .filter(|(id, _)| experts.iter().any(|e| e == id))
                .collect()
        };
        let mut count = 0usize;
        for store in &stores {
            for i in 0..store.closes.len() {
                let t = i + 1;
                let as_of = store.avail[i];
                let feats = state::state_features(store, t, as_of, history_depth);
                let mut map = HashMap::new();
                for f in &feats {
                    map.insert(f.name.clone(), f.clone());
                }
                for (eid, _) in &table {
                    let closure = features::group_closure(experts::requires_for(eid));
                    let projected = features::project_features(&map, &closure);
                    let hist = if features::history_allowed(&closure) {
                        state::history_bars(store, t, history_depth)
                    } else {
                        Vec::new()
                    };
                    let fm = experts::base::FeatMap {
                        features: &projected,
                        history: hist,
                        as_of,
                        symbol: &store.symbol,
                    };
                    if experts::evaluate(eid, &fm).decision == "CANDIDATE" {
                        count += 1;
                    }
                }
            }
        }
        count
    }

    /// Run the loop over `rows` and return (n_candidates, n_suppressed,
    /// n_rejected, n_evaluations). The smoke contract (a) is asserted here:
    /// every CANDIDATE decision the dispatch returns is either admitted,
    /// suppressed, or rejected, so the three counters sum to the direct
    /// evaluate() CANDIDATE count.
    fn counts(rows: &[Value], out: &str, experts: Vec<&str>) -> (u64, u64, u64, u64) {
        let manifest = serde_json::json!({ "funding_window_bars": 0 });
        let tape = write_tape(rows, out);
        let r = req(tape.clone(), out, experts.clone(), manifest);
        let summary = evaluate(&r).unwrap();
        let a = summary["n_candidates"].as_u64().unwrap();
        let b = summary["n_suppressed"].as_u64().unwrap();
        let c = summary["n_rejected"].as_u64().unwrap();
        let n = summary["n_evaluations"].as_u64().unwrap();
        let direct = direct_candidate_count(&tape, state::HISTORY_DEPTH_DEFAULT, &r.experts) as u64;
        assert_eq!(a + b + c, direct,
                   "loop candidate outcomes must equal the direct evaluate() CANDIDATE count");
        (a, b, c, n)
    }

    /// Read the candidates.jsonl the loop wrote and return the expert_id of
    /// the admitted candidate in `direction` (the PENDING candidate in that
    /// direction). The regression probe for issue #68: which expert wins an
    /// (instrument, direction) slot conflict.
    fn admitted_expert(rows: &[Value], out: &str, experts: Vec<&str>,
                       direction: &str) -> String {
        let manifest = serde_json::json!({ "funding_window_bars": 0 });
        let tape = write_tape(rows, out);
        let r = req(tape, out, experts, manifest);
        let summary = evaluate(&r).unwrap();
        let cand_path = PathBuf::from(summary["candidates"].as_str().unwrap());
        let text = std::fs::read_to_string(&cand_path).unwrap();
        let mut admitted: Vec<String> = Vec::new();
        let mut dir_of: HashMap<String, String> = HashMap::new();
        let mut expert_of: HashMap<String, String> = HashMap::new();
        for line in text.lines() {
            let v: Value = serde_json::from_str(line).unwrap();
            if v["kind"] == "transition" {
                let cid = v["candidate_id"].as_str().unwrap().to_string();
                match v["to_state"].as_str().unwrap() {
                    "DETECTED" => {
                        expert_of.insert(cid.clone(), v["expert_id"].as_str().unwrap().to_string());
                        dir_of.insert(cid, v["direction"].as_str().unwrap().to_string());
                    }
                    "PENDING" => admitted.push(cid),
                    _ => {}
                }
            }
        }
        let mut winners: Vec<String> = admitted.iter()
            .filter(|cid| dir_of.get(*cid).map(|d| d == direction).unwrap_or(false))
            .map(|cid| expert_of.get(cid).cloned().unwrap())
            .collect();
        assert_eq!(winners.len(), 1, "exactly one admitted candidate in direction {direction}");
        winners.pop().unwrap()
    }

    #[test]
    fn candidate_count_matches_direct_evaluate() {
        // A tiny synthetic tape (fixed-array rows) run through the loop
        // produces exactly the CANDIDATE decisions the dispatch table returns.
        // The subset spans the table but deliberately excludes bollinger_breakout
        // and fib_rsi_bb_confluence: both panic in DEBUG builds on the `i - N + 1`
        // index at i == N - 1 (usize underflow; release wraps to the correct
        // index, which is why the release-mode parity harness is unaffected) —
        // a pre-existing defect in those modules, not in this loop.
        let (a, b, c, n) = counts(&ramp_bars(60), "count",
            vec!["donchian_breakout", "trend_pullback", "liquidity_sweep_reclaim"]);
        // donchian_breakout fires on every bar t >= 22; the first detection is
        // admitted (a == 1), and every later one is either a
        // suppressed_duplicate (when its episode key coincides — the ramp's
        // stop_r drifts only in the last ulp) or a portfolio rejection (when
        // it differs). The invariant a + b + c == direct is the contract and
        // is asserted inside counts(); the other two experts never fire on a
        // ramp, so no other candidate exists.
        assert_eq!(a, 1, "first ramp breakout admitted");
        assert!(b + c > 0, "later breakouts are suppressed or rejected");
        assert_eq!(n, 60 * 3, "every bar x every expert evaluated");
    }

    #[test]
    fn duplicate_setup_yields_one_candidate_one_suppressed() {
        // The bar-20 dip opens a pullback run; bar 21 is still inside it. The
        // D-026 anchor is the run's first bar (SOLUSDT:21) for both, and
        // trend_pullback's structural geometry is constant (stop_r/target_r are
        // declared constants; atr_ref is excluded from the geometry version) —
        // so the second bar's episode key is identical: one admitted candidate
        // + one suppressed_duplicate, nothing rejected.
        let (a, b, c, _) = counts(&pullback_tape(&[13.0, 13.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5]),
                                   "dedup", vec!["trend_pullback"]);
        assert_eq!(a, 1, "first detection admitted");
        assert_eq!(b, 1, "identical consecutive setup is a suppressed_duplicate");
        assert_eq!(c, 0);
    }

    #[test]
    fn second_same_direction_candidate_is_rejected() {
        // The bar-20 pullback holds the (SOLUSDT, LONG) exposure slot; the
        // recovery resets the setup predicate; the bar-27 dip opens a NEW
        // episode (new anchor) that passes dedup but is NOT admitted:
        // EXISTING_EXPOSURE_CONFLICT (rule 16 — one active exposure per
        // (instrument, direction)).
        let (a, b, c, _) = counts(&pullback_tape(&[13.0, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5,
                                                   14.0, 18.5, 19.5]),
                                   "exposure", vec!["trend_pullback"]);
        assert_eq!(a, 1, "first detection admitted");
        assert_eq!(b, 0, "no duplicate episode keys on this tape");
        assert_eq!(c, 1, "second same-direction candidate is portfolio-rejected");
    }

    #[test]
    fn dispatch_order_is_declared_non_alphabetical_and_deterministic() {
        // Issue #68: the exposure book's selection order must be a declared
        // deterministic rule that is NOT alphabetical expert_id order — the
        // alphabetical TABLE order was the implicit ranker that systematically
        // gave the slot to bollinger_breakout. The declared rule is ascending
        // sha1(expert_id).
        let a = dispatch_order();
        let b = dispatch_order();
        assert_eq!(a, b, "the dispatch order must be deterministic");
        assert_eq!(a.len(), experts::TABLE.len(),
                   "every registered expert is dispatched exactly once");
        // The canonical TABLE is alphabetical and leads with bollinger_breakout.
        assert_eq!(experts::TABLE[0].0, "bollinger_breakout",
                   "TABLE is expert_id-sorted — the old implicit alphabetical ranker");
        // The declared order differs from it at the top of the queue.
        assert_ne!(a[0].0, experts::TABLE[0].0,
                   "the declared order must not be alphabetical");
        // And it is exactly the declared rule: strictly ascending sha1(expert_id).
        let hashes: Vec<String> = a.iter().map(|(id, _)| {
            let mut c = crate::hash::Canon::new();
            c.push_str(id);
            c.finish_sha1_hex()
        }).collect();
        let mut sorted = hashes.clone();
        sorted.sort();
        assert_eq!(hashes, sorted,
                   "the dispatch order is the declared ascending sha1(expert_id)");
    }

    #[test]
    fn slot_conflict_resolves_by_declared_hash_order_not_alphabetical() {
        // Issue #68: when two experts fire the same (instrument, direction) at
        // the same bar, the ExposureBook slot used to go to the
        // alphabetically-first expert — an implicit ranker selecting by
        // expert_id spelling. The declared rule resolves the conflict by the
        // dispatch order (ascending sha1(expert_id)): pandf_breakout (sha1
        // rank 14) precedes bollinger_breakout (rank 18), so pandf must win
        // the (SOLUSDT, LONG) slot despite being alphabetically LAST.
        //
        // Fixture: a 20-bar down-ramp (closes 110.0 -> 100.0), then a jump to
        // 115.0. At the jump bar both experts fire their first LONG candidate
        // into the same free slot: bollinger (close > SMA20) and pandf
        // (point-and-figure box breakout). Alphabetically bollinger would take
        // the slot; the declared rule must admit pandf and reject bollinger.
        let mut rows: Vec<Value> = Vec::new();
        for i in 0..20usize {
            let c = 110.0 - 0.5 * (i as f64);
            rows.push(bar(c, c + 0.3, c - 0.3, c, "SOLUSDT", i));
        }
        rows.push(bar(115.0, 115.3, 114.7, 115.0, "SOLUSDT", 20));
        let winner = admitted_expert(&rows, "slot-conflict",
                                     vec!["bollinger_breakout", "pandf_breakout"], "LONG");
        assert_eq!(winner, "pandf_breakout",
                   "slot conflicts must resolve by the declared sha1(expert_id) order, \
                    not alphabetical expert_id (issue #68)");
    }

    #[test]
    fn windowed_prior_extremes_is_bounded_to_prior_32_bars() {
        // 40 bars: bars 0..3 spike down to low 1.0; bars 4..40 hold >= 5.0.
        // The window before birth = 40 is [8..40) — the old spike is excluded,
        // so the windowed prior low is the recent-window minimum, not the
        // all-bars prefix minimum (issue #66: the prefix extreme is pinned by
        // an old spike and makes the gate dead code).
        let mut highs = Vec::new();
        let mut lows = Vec::new();
        for i in 0..40usize {
            if i < 4 {
                highs.push(6.0);
                lows.push(1.0);
            } else {
                highs.push(30.0);
                lows.push(5.0 + i as f64);
            }
        }
        let (prior_low, prior_high) = windowed_prior_extremes(&highs, &lows, 40);
        assert!(prior_low.unwrap() > 1.0,
                "the old spike outside the window must not pin the windowed prior low");
        assert_eq!(prior_high.unwrap(), 30.0);
        // Empty window (birth 0) fails closed — never default to 0.0/inf.
        assert_eq!(windowed_prior_extremes(&highs, &lows, 0), (None, None));
    }

    #[test]
    fn pre_entry_invalidation_fires_on_windowed_prior_extreme() {
        // An old crash (bars 0..3, low 3.7) pins the UNBOUNDED prefix minimum
        // at 3.7. The trend_pullback LONG setup is born at bar 36, whose
        // 32-bar window [4..36) excludes the old crash — the windowed
        // prior_low is the ramp's bar-4 low (9.7). The entry bar 37 then
        // crashes to low 6.7: below the windowed level but above the old
        // spike, so the pre-entry gate fires — with the unbounded prefix it
        // would be dead code. The candidate must NOT execute: every cube cell
        // is NO_ENTRY.
        let mut rows: Vec<Value> = Vec::new();
        for i in 0..4usize {
            let c = 4.0;
            rows.push(bar(c, c + 0.3, c - 0.3, c, "SOLUSDT", i));
        }
        for i in 4..36usize {
            let c = 10.0 + 0.5 * ((i - 4) as f64); // ramp 10.0..25.5
            rows.push(bar(c, c + 0.3, c - 0.3, c, "SOLUSDT", i));
        }
        rows.push(bar(20.0, 20.3, 19.7, 20.0, "SOLUSDT", 36)); // dip: setup born
        rows.push(bar(7.0, 7.3, 6.7, 7.0, "SOLUSDT", 37));     // crash: gate fires
        for (k, c) in [9.0, 10.0, 11.0, 12.0].iter().enumerate() {
            rows.push(bar(*c, *c + 0.3, *c - 0.3, *c, "SOLUSDT", 38 + k));
        }

        let manifest = serde_json::json!({ "funding_window_bars": 0 });
        let tape = write_tape(&rows, "invalidation");
        let r = req(tape, "invalidation", vec!["trend_pullback"], manifest);
        let summary = evaluate(&r).unwrap();
        assert_eq!(summary["n_candidates"].as_u64().unwrap(), 1,
                   "the dip admits exactly one candidate");
        let cube_path = std::path::PathBuf::from(summary["cube_reduced"].as_str().unwrap());
        let cube = evidence::read_artifact(&cube_path).unwrap();
        let no_entry = cube.column("n_no_entry").expect("n_no_entry column");
        assert_eq!(no_entry.len(), 1, "one candidate row in the cube");
        let n_no_entry = no_entry[0].as_ref().expect("n_no_entry present").as_i64().unwrap();
        assert!(n_no_entry > 0, "the invalidated candidate never enters (n_no_entry={n_no_entry})");
        let n_ok = cube.column("n_ok").expect("n_ok column")[0]
            .as_ref().expect("n_ok present").as_i64().unwrap();
        assert_eq!(n_ok, 0, "no action executes for an invalidated candidate");
        let reason = cube.column("abstention_reason").expect("abstention_reason column")[0]
            .as_ref().expect("reason present").as_str().unwrap();
        assert!(reason.contains("invalidated before entry"),
                "the cube records the pre-entry invalidation, got: {reason}");
    }

    // -----------------------------------------------------------------------
    // D-057 entry-trigger gate (issue #67) + risk_geometry dead-field registry
    // -----------------------------------------------------------------------

    /// The risk_geometry keys the runner/simulator/predicate actually READ
    /// (behavioral consumption) — sourced from the read sites in simulator.rs,
    /// runloop.rs, regret.rs and the compiled predicate IR ref operands
    /// (tools/predicate_ir.py). Every key an expert DECLARES must land here or
    /// in `IDENTITY_ONLY_GEOMETRY_KEYS` (issue #67: trigger_ref was computed,
    /// written and hashed but read by no runner path — a field both inert and
    /// identity-carrying; the registry is the guard that dead fields cannot
    /// silently accumulate).
    const CONSUMED_GEOMETRY_KEYS: &[&str] = &[
        // ReplayKernel entry/exit path (backend::scalar)
        "atr_ref", "risk_frac", "target_r", "stop_r", "expiry_bars", "stop_ref",
        "time_exit_bars", "pyramid_add_rules", "breakeven_roll_at_mfe_r",
        "breakeven_margin_r", "trail_stop_atr", "scale_out_ratio",
        "scale_out_at_mfe_r", "limit_price", "trigger_ref", "trigger_side",
        // runloop admission + pre-entry invalidation
        "size", "prior_low_ref", "prior_high_ref",
        // compiled predicate IR ref operands (tools/predicate_ir.py)
        "level_ref", "breakout_ref", "gap_top_ref", "gap_bottom_ref",
        "barrier_ref", "extremum_ref", "mid_ref", "upper_1sd_ref",
        "lower_1sd_ref", "upper_2sd_ref", "lower_2sd_ref", "lower_3sd_ref",
        "upper_3sd_ref", "channel_n", "variant",
    ];

    /// Declared risk_geometry keys with NO behavioral reader in the compute
    /// plane, registered as identity/structural constants (they still hash
    /// into geometry_version — D-079 — so they carry candidate identity). Each
    /// entry names its declaring expert. Adding a key here requires a decision;
    /// the runner does not read it.
    const IDENTITY_ONLY_GEOMETRY_KEYS: &[(&str, &str)] = &[
        ("entry", "all experts: the declared entry mode (NEXT_BAR_CLOSE) — the bar-close entry model"),
        ("poc_ref", "market_profile_value_area: frozen profile POC"),
        ("va_low_ref", "market_profile_value_area: frozen value-area low"),
        ("va_high_ref", "market_profile_value_area: frozen value-area high"),
        ("target_2x_ref", "range_breakout_1to1: 2x-target projection"),
        ("reversal", "pandf_breakout: reversal-box count declaration"),
    ];

    fn tape_fixture(rows: &[Value], tag: &str) -> (data::Dataset, Vec<FeatureStore>) {
        let tape = write_tape(rows, tag);
        let parsed = read_tape(&tape).unwrap();
        let ds = data::Dataset::from_rows(parsed).unwrap();
        let stores = state::build_stores(&ds);
        (ds, stores)
    }

    fn trigger_draft(trigger_ref: Option<f64>, prior_low: f64) -> simulator::Draft {
        let mut g = serde_json::Map::new();
        g.insert("atr_ref".to_string(), serde_json::json!(2.0));
        g.insert("target_r".to_string(), serde_json::json!(1.0));
        g.insert("stop_r".to_string(), serde_json::json!(1.0));
        g.insert("expiry_bars".to_string(), serde_json::json!(8));
        g.insert("stop_ref".to_string(), serde_json::json!(98.0));
        g.insert("prior_low_ref".to_string(), serde_json::json!(prior_low));
        if let Some(t) = trigger_ref {
            g.insert("trigger_ref".to_string(), serde_json::json!(t));
            g.insert("trigger_side".to_string(), serde_json::json!("CLOSE_ABOVE"));
        }
        simulator::Draft { direction: "LONG".to_string(), birth_time: 0, risk_geometry: g }
    }

    #[test]
    fn entry_trigger_gate_consults_trigger_ref() {
        // Bars 0..7 flat at 100; bar 8 jumps to 110 (clears trigger_ref 105);
        // bars 9..13 drift down. A LONG/CLOSE_ABOVE draft with trigger_ref=105:
        // the wait starts at bar 8, whose close confirms — entry is the NEXT
        // bar's close (bar 9), never the confirming bar's.
        let rows: Vec<Value> = (0..14).map(|i| {
            let c = if i < 8 { 100.0 } else { 110.0 - 0.5 * ((i - 8) as f64) };
            bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i)
        }).collect();
        let (ds, stores) = tape_fixture(&rows, "trigger-confirm");
        let funding: &[(i64, f64)] = &[];
        let kernel = ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: simulator::FillPolicy::BarClose,
            funding_schedule: funding,
            round_trip_cost_bps: None,
            bars: &ds.bars[0],
            store: &stores[0],
        };
        let out = kernel.run(&trigger_draft(Some(105.0), 95.0), 8,
                             ds.bars[0].closes.len(), None).unwrap();
        assert_ne!(out.label_status, "NOT_EXECUTED", "a confirmed trigger must enter");
        assert_eq!(out.entry_price, ds.bars[0].closes[9],
                   "entry is the bar AFTER the confirming close (issue #67: the trigger is a close-confirmation, not the entry bar)");
    }

    #[test]
    fn entry_trigger_never_confirmed_is_not_executed() {
        // All closes stay at 100, below trigger_ref 105: the wait runs to the
        // end of the tape and the trigger never fires — the epilogue
        // convention (EXPIRY / NOT_EXECUTED): a non-trade, not a censored
        // position.
        let rows: Vec<Value> = (0..14).map(|i| {
            let c = 100.0;
            bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i)
        }).collect();
        let (ds, stores) = tape_fixture(&rows, "trigger-never");
        let funding: &[(i64, f64)] = &[];
        let kernel = ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: simulator::FillPolicy::BarClose,
            funding_schedule: funding,
            round_trip_cost_bps: None,
            bars: &ds.bars[0],
            store: &stores[0],
        };
        let out = kernel.run(&trigger_draft(Some(105.0), 95.0), 8,
                             ds.bars[0].closes.len(), None).unwrap();
        assert_eq!(out.label_status, "NOT_EXECUTED", "an unfired trigger never enters");
        assert_eq!(out.endpoint, "EXPIRY", "the tape-end epilogue expires a PENDING candidate");
        assert_eq!(out.net_r, 0.0);
    }

    #[test]
    fn entry_trigger_absent_fails_open_unconditional() {
        // No trigger_ref: the D-082 fail-open keeps the unconditional
        // next-bar-close entry (experts without a trigger — entry:
        // NEXT_BAR_CLOSE — must not change behavior).
        let rows: Vec<Value> = (0..14).map(|i| {
            let c = 100.0;
            bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i)
        }).collect();
        let (ds, stores) = tape_fixture(&rows, "trigger-absent");
        let funding: &[(i64, f64)] = &[];
        let kernel = ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: simulator::FillPolicy::BarClose,
            funding_schedule: funding,
            round_trip_cost_bps: None,
            bars: &ds.bars[0],
            store: &stores[0],
        };
        let out = kernel.run(&trigger_draft(None, 95.0), 8,
                             ds.bars[0].closes.len(), None).unwrap();
        assert_ne!(out.label_status, "NOT_EXECUTED",
                   "no trigger_ref means unconditional entry (fail-open, D-082)");
        assert_eq!(out.entry_price, ds.bars[0].closes[8],
                   "entry at the first wait bar's close");
    }

    #[test]
    fn entry_trigger_invalidated_during_wait_is_not_executed() {
        // Bar 8's close stays at 100 (trigger 105 unfired); bar 9's low dips to
        // 94, breaching the frozen prior_low_ref 95 while the candidate is
        // still PENDING — the wait ends invalidated (INVALIDATED_BEFORE_TRIGGER),
        // never as an executed position.
        let mut rows: Vec<Value> = (0..9).map(|i| {
            let c = 100.0;
            bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i)
        }).collect();
        rows.push(bar(99.0, 99.5, 94.0, 99.0, "SOLUSDT", 9)); // breach bar
        for i in 10..14 {
            let c = 100.0;
            rows.push(bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i));
        }
        let (ds, stores) = tape_fixture(&rows, "trigger-invalid");
        let funding: &[(i64, f64)] = &[];
        let kernel = ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: simulator::FillPolicy::BarClose,
            funding_schedule: funding,
            round_trip_cost_bps: None,
            bars: &ds.bars[0],
            store: &stores[0],
        };
        let out = kernel.run(&trigger_draft(Some(105.0), 95.0), 8,
                             ds.bars[0].closes.len(), None).unwrap();
        assert_eq!(out.label_status, "NOT_EXECUTED");
        assert_eq!(out.endpoint, "INVALIDATED_BEFORE_TRIGGER",
                   "a prior-level breach during the PENDING wait invalidates — the candidate never enters");
    }

    #[test]
    fn every_declared_risk_geometry_key_is_consumed_or_registered() {
        // The dead-field registry guard (issue #67): union the risk_geometry
        // keys every fired expert declares on a diverse tape and assert each
        // is either read by a runner path (simulator/runloop/regret/compiled
        // predicate) or registered as an identity/structural constant.
        // trigger_ref was the original violation — computed, written, hashed,
        // and read by no one; it is now a CONSUMED key, so the guard is live.
        // bollinger_breakout and fib_rsi_bb_confluence are excluded: both
        // underflow `i - BB_BASE_N + 1` on early bars in DEBUG builds (the
        // same pre-existing defect the candidate-count test documents).
        let mut rows: Vec<Value> = Vec::new();
        // Bars 0..18: a gentle decline (each a down bar: open above close) so
        // the ATR feature is emitted (it requires t >= 20, state.rs) and the
        // immediately-preceding bar is a down bar.
        for i in 0..19usize {
            let c = 25.0 - 0.5 * (i as f64);
            rows.push(bar(c + 0.3, c + 0.6, c - 0.3, c, "SOLUSDT", i));
        }
        // Bar 19: the down bar the hammer needs for its decline context.
        rows.push(bar(15.3, 15.6, 14.5, 15.0, "SOLUSDT", 19));
        // Bar 20: hammer (tiny real body near the top, long lower shadow) —
        // candlestick_reversal (the trigger-ref pilot) fires here.
        rows.push(bar(14.0, 14.2, 12.0, 14.15, "SOLUSDT", 20));
        // Bars 21..60: a ramp (donchian_breakout, trend_pullback, ...).
        for k in 0..40usize {
            let i = 21 + k;
            let c = 15.0 + 0.5 * (k as f64);
            rows.push(bar(c, c + 0.3, c - 0.3, c, "SOLUSDT", i));
        }
        let (ds, stores) = tape_fixture(&rows, "declared-keys");
        let mut declared: std::collections::HashSet<String> = std::collections::HashSet::new();
        for store in &stores {
            for i in 0..store.closes.len() {
                let t = i + 1;
                let as_of = store.avail[i];
                let feats = state::state_features(store, t, as_of, state::HISTORY_DEPTH_DEFAULT);
                let mut map: HashMap<String, state::Feature> = HashMap::new();
                for f in &feats {
                    map.insert(f.name.clone(), f.clone());
                }
                for (eid, _) in experts::TABLE.iter()
                    .filter(|(id, _, _, _)| *id != "bollinger_breakout"
                            && *id != "fib_rsi_bb_confluence")
                    .map(|(id, _, ver, _)| (*id, *ver))
                {
                    let closure = features::group_closure(experts::requires_for(eid));
                    let projected = features::project_features(&map, &closure);
                    let hist = if features::history_allowed(&closure) {
                        state::history_bars(store, t, state::HISTORY_DEPTH_DEFAULT)
                    } else {
                        Vec::new()
                    };
                    let fm = experts::base::FeatMap {
                        features: &projected,
                        history: hist,
                        as_of,
                        symbol: &store.symbol,
                    };
                    if let Some(d) = experts::evaluate(eid, &fm).draft {
                        for k in d.risk_geometry.keys() {
                            declared.insert(k.clone());
                        }
                    }
                }
            }
        }
        // The pilot must fire for the guard to protect its keys.
        assert!(declared.contains("trigger_ref"),
                "the dead-field tape must fire candlestick_reversal (the trigger-ref pilot)");
        assert!(declared.contains("trigger_side"));
        for key in &declared {
            let consumed = CONSUMED_GEOMETRY_KEYS.contains(&key.as_str());
            let identity = IDENTITY_ONLY_GEOMETRY_KEYS.iter().any(|(k, _)| *k == key.as_str());
            assert!(consumed || identity,
                    "risk_geometry key {key:?} is declared by a fired expert but read by NO runner path \
                     (issue #67: dead fields must not silently accumulate)");
        }
    }

    /// A LONG draft with explicit control over the invariant-bearing geometry
    /// keys (issue #70).
    fn geom_draft(target_r: f64, stop_r: f64, expiry_bars: i64) -> simulator::Draft {
        let mut g = serde_json::Map::new();
        g.insert("atr_ref".to_string(), serde_json::json!(2.0));
        g.insert("target_r".to_string(), serde_json::json!(target_r));
        g.insert("stop_r".to_string(), serde_json::json!(stop_r));
        g.insert("expiry_bars".to_string(), serde_json::json!(expiry_bars));
        simulator::Draft { direction: "LONG".to_string(), birth_time: 0, risk_geometry: g }
    }

    #[test]
    fn risk_geometry_invariants_fail_closed() {
        // Issue #70: validate_geometry must reject degenerate geometry at
        // admission. target_r <= 0 puts the target on the losing side and the
        // replay would book the loss as a TARGET endpoint (a win in any
        // downstream hit-rate / profit-factor statistic); stop_r <= 0 is not
        // a position; expiry_bars < 1 is not a horizon.
        let valid = geom_draft(1.0, 1.0, 8);
        assert!(simulator::validate_geometry(&valid).is_ok(),
                "a sane geometry must validate");
        for (label, g) in [
            ("target_r = 0", geom_draft(0.0, 1.0, 8)),
            ("target_r < 0", geom_draft(-1.0, 1.0, 8)),
            ("stop_r = 0", geom_draft(1.0, 0.0, 8)),
            ("stop_r < 0", geom_draft(1.0, -1.0, 8)),
            ("expiry_bars = 0", geom_draft(1.0, 1.0, 0)),
            ("expiry_bars < 1", geom_draft(1.0, 1.0, -2)),
        ] {
            assert!(simulator::validate_geometry(&g).is_err(),
                    "{label} must fail closed");
        }
        // A present-but-non-numeric key fails closed too: geom_f64 would
        // return None and the replay path would default target_r to 0.0 —
        // target = entry — booking the first bar as a TARGET exit. The
        // oracle's float()/int() raises for the same input.
        for key in ["target_r", "stop_r"] {
            let mut g = geom_draft(1.0, 1.0, 8);
            g.risk_geometry.insert(key.to_string(), serde_json::json!("not-a-number"));
            assert!(simulator::validate_geometry(&g).is_err(),
                    "non-numeric {key} must fail closed, never be silently skipped");
        }
        let mut g = geom_draft(1.0, 1.0, 8);
        g.risk_geometry.insert("expiry_bars".to_string(), serde_json::json!("many"));
        assert!(simulator::validate_geometry(&g).is_err(),
                "non-numeric expiry_bars must fail closed");
    }

    #[test]
    fn negative_target_r_is_rejected_never_recorded_as_target() {
        // Issue #70 end-to-end: a LONG draft with target_r = -1 places the
        // target BELOW entry. On the first stepped bar the low reaches the
        // wrong-side target while the stop is not hit — without the guard the
        // kernel would return endpoint=TARGET with net_r = (98-100)/2 - 0.07 =
        // -1.07 (the issue's exact scenario: a loss booked as a win by
        // downstream statistics). The kernel must reject the geometry at
        // admission instead of replaying it.
        let rows: Vec<Value> = vec![
            bar(100.0, 100.5, 99.5, 100.0, "SOLUSDT", 0),
            // low 97 reaches the wrong-side target (98) and misses the
            // stop (94): hit_target fires, hit_stop does not.
            bar(98.0, 98.5, 97.0, 97.5, "SOLUSDT", 1),
        ];
        let (ds, stores) = tape_fixture(&rows, "neg-target");
        let funding: &[(i64, f64)] = &[];
        let kernel = ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: simulator::FillPolicy::BarClose,
            funding_schedule: funding,
            round_trip_cost_bps: None,
            bars: &ds.bars[0],
            store: &stores[0],
        };
        // target = 100 + 1.0 * (-1.0) * 2.0 = 98; stop = 100 - 3.0 * 2.0 = 94.
        let draft = geom_draft(-1.0, 3.0, 8);
        let out = kernel.run(&draft, 0, ds.bars[0].closes.len(), None);
        match out {
            Ok(o) => panic!("a target_r<0 draft must be rejected, never recorded as endpoint={} net_r={}",
                            o.endpoint, o.net_r),
            Err(e) => assert!(e.contains("target_r must be > 0"),
                              "the rejection must name the offending key: {e}"),
        }
    }

    #[test]
    fn cube_reduced_is_byte_identical_across_thread_counts() {
        // G5 on the S4 path (COMPUTE_SCHEDULING_SPEC §8.1): the cube-reduced
        // artifact must be byte-identical at threads=1 and threads=8. The
        // scheduler (Backend-1, issue #132) now really splits the S2 replay
        // batch across worker threads, so this is a live thread-invariance
        // check — pre-scheduler the `threads` manifest field was nominal.
        let manifest = serde_json::json!({ "funding_window_bars": 0 });
        let tape1 = write_tape(&ramp_bars(60), "g5-one");
        let tape2 = write_tape(&ramp_bars(60), "g5-eight");
        let mut r1 = req(tape1, "g5-threads1", vec!["donchian_breakout"], manifest.clone());
        r1.threads = 1;
        let mut r8 = req(tape2, "g5-threads8", vec!["donchian_breakout"], manifest);
        r8.threads = 8;
        let s1 = evaluate(&r1).unwrap();
        let s8 = evaluate(&r8).unwrap();
        assert_eq!(
            s1["n_reduced"], s8["n_reduced"],
            "the same tape must admit the same candidate count at any thread count"
        );
        let cube1 = std::fs::read(s1["cube_reduced"].as_str().unwrap()).unwrap();
        let cube8 = std::fs::read(s8["cube_reduced"].as_str().unwrap()).unwrap();
        assert_eq!(
            cube1, cube8,
            "cube-reduced artifact must be byte-identical at threads=1 vs threads=8"
        );
    }

}
