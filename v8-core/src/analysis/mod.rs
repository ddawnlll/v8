//! S6 analysis plane (D-091; COMPUTE_CORE_SPEC §6): reconciliation + regret
//! phases 1-3. One module per concern so the stages port in parallel.
//!
//! The `analysis` subcommand (issue #116) is the composition point: over the
//! loop/cube output it runs reconciliation (issue #122) then the regret
//! phases 1-3 in sequence and writes `analysis.jsonl` with the slice verdicts.
//!
//! Request shape (same as `reconcile` plus optional precomputed loop output):
//!
//! ```json
//! {
//!   "tape_path": "...", "universe": [...], "out_dir": "...", "manifest": {...},
//!   "candidates": [...], "evaluations": [...], "outcomes": [...], "states": [...],
//!   "evaluations_path": "...", "cube_reduced_path": "..."
//! }
//! ```
//!
//! `{tape_path, universe, out_dir?}` is the minimum. The ledger arrays are the
//! reconcile projection; when empty they are sourced from the S4 loop output
//! (candidates.jsonl + evaluations.jsonl), with the outcomes and states
//! ledgers re-derived from the store (the compute plane persists neither,
//! D-081). When `evaluations_path` is absent the full evaluate loop runs to
//! produce that output in `out_dir`.

pub mod outcome;
pub mod phase1;
pub mod phase2;
pub mod phase3;
pub mod reconcile;

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use crate::analysis::phase1::{
    CandidateIdentity, CubeAccumulators, GapRecord, JoinedCandidateRow, Phase0Output,
};
use crate::backend::scalar::ScalarKernel;
use crate::data::{Dataset, TapeRow};
use crate::evidence;
use crate::simulator::{Draft, SimulatorParams};
use crate::state::{self, FeatureStore};

pub fn reconcile(args: &[String]) -> i32 {
    reconcile::run(args)
}

// ---------------------------------------------------------------------------
// Request
// ---------------------------------------------------------------------------

/// The S6 analysis request (issue #116): the reconcile ledger projection plus
/// optional precomputed loop-output paths. `{tape_path, universe, out_dir?}`
/// is the minimum; the ledger arrays and loop paths are all optional so a
/// bare `{tape_path, universe, out_dir}` request runs the full S4 loop and
/// re-derives the ledgers it does not carry.
#[derive(Debug, serde::Deserialize)]
pub struct AnalysisRequest {
    pub tape_path: PathBuf,
    #[serde(default)]
    pub universe: Vec<String>,
    #[serde(default = "default_out_dir")]
    pub out_dir: PathBuf,
    #[serde(default)]
    pub manifest: Value,
    // The reconcile ledger projection (the same request shape `reconcile`
    // accepts; empty arrays fall back to the loop output / store derivation).
    #[serde(default)]
    pub candidates: Vec<Value>,
    #[serde(default)]
    pub evaluations: Vec<Value>,
    #[serde(default)]
    pub outcomes: Vec<Value>,
    #[serde(default)]
    pub states: Vec<Value>,
    /// Precomputed loop output (evaluations.jsonl; `cube_reduced_path`
    /// defaulting to `{out_dir}/cube-reduced.v82`). When absent — and no
    /// inline `evaluations` — the S4 evaluate loop runs.
    #[serde(default)]
    pub evaluations_path: Option<PathBuf>,
    #[serde(default)]
    pub cube_reduced_path: Option<PathBuf>,
    #[serde(default = "default_threads")]
    pub threads: usize,
}

fn default_out_dir() -> PathBuf {
    PathBuf::from("out")
}

fn default_threads() -> usize {
    4
}

/// Entry point dispatched from main (S6 composition, issue #116). Returns 0 on
/// a completed analysis, 1 on error (halt: reconciliation failure or PIT
/// lineage violation — the same fail-closed gate `reconcile` applies), 2 on
/// usage error.
pub fn analysis(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core analysis <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error: cannot read request: {e}");
            return 1;
        }
    };
    let req: AnalysisRequest = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    match run_analysis(&req) {
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
// Ledger + store helpers
// ---------------------------------------------------------------------------

/// Read a JSONL tape into parsed `TapeRow`s using the Python-json-compatible
/// parser (the tape is written by CPython `json.dumps`, which may emit
/// `NaN`/`Infinity` literals that strict JSON rejects).
fn read_tape(path: &Path) -> Result<Vec<TapeRow>, String> {
    let text =
        std::fs::read_to_string(path).map_err(|e| format!("cannot read tape {path:?}: {e}"))?;
    let mut rows = Vec::new();
    for (i, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed =
            crate::jsonx::parse_line(line).map_err(|e| format!("tape line {}: {e}", i + 1))?;
        let row = TapeRow::from_parts(&parsed.value, parsed.nonfinite)
            .map_err(|e| format!("tape line {}: {e}", i + 1))?;
        rows.push(row);
    }
    Ok(rows)
}

/// Read a JSONL ledger (one JSON value per line, blank lines skipped).
fn read_jsonl(path: &Path) -> Result<Vec<Value>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("cannot read {path:?}: {e}"))?;
    let mut out = Vec::new();
    for (i, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let v: Value =
            serde_json::from_str(line).map_err(|e| format!("{path:?} line {}: {e}", i + 1))?;
        out.push(v);
    }
    Ok(out)
}

/// Fast reader for evaluations.jsonl that filters for draft-bearing records before JSON deserialization.
fn read_evaluations_jsonl(path: &Path) -> Result<Vec<Value>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("cannot read {path:?}: {e}"))?;
    let mut out = Vec::new();
    for (i, line) in text.lines().enumerate() {
        if line.trim().is_empty() || line.contains("\"draft\":null") || !line.contains("\"draft\"") {
            continue;
        }
        let v: Value =
            serde_json::from_str(line).map_err(|e| format!("{path:?} line {}: {e}", i + 1))?;
        out.push(v);
    }
    Ok(out)
}

/// The tape-driven funding schedule (D-041): (boundary_time_ns, rate) pairs
/// from the tape's funding channel, sorted by boundary time.
fn funding_schedule(ds: &Dataset) -> Vec<(i64, f64)> {
    let mut sched: Vec<(i64, f64)> = ds
        .rows
        .iter()
        .filter(|r| r.channel == "funding")
        .map(|r| {
            (
                r.event_time,
                r.payload["funding_rate"].as_f64().unwrap_or(0.0),
            )
        })
        .collect();
    sched.sort_by_key(|(t, _)| *t);
    sched
}

/// Replay one BOUND snapshot's ACTUAL action and project it onto the ten-field
/// reconciliation surface. `None` when the snapshot has no entry bar, no
/// draft, its instrument has no bars/store, or the replay raises (mirror of
/// `reconcile::reconcile_actual_actions`' skip paths).
fn replay_actual_surface(
    snap: &reconcile::CandidateSnapshot,
    ds: &Dataset,
    stores: &[FeatureStore],
    sim: &SimulatorParams,
    funding: &[(i64, f64)],
) -> Option<crate::simulator::Outcome> {
    let entry_time = snap.entry_bar_available_time?;
    let store = stores.iter().find(|s| s.symbol == snap.instrument)?;
    let bars = ds.bars.iter().find(|b| b.symbol == snap.instrument)?;
    let i = bars.available_times.binary_search(&entry_time).ok()?;
    let raw = snap.raw_draft.as_ref()?;
    let draft = Draft {
        direction: raw
            .get("direction")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        birth_time: raw.get("birth_time").and_then(|v| v.as_i64()).unwrap_or(0),
        risk_geometry: raw
            .get("risk_geometry")
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default(),
    };
    let kernel = ScalarKernel {
        round_trip_cost_r: sim.round_trip_cost_r,
        funding_rate_r: sim.funding_rate_r,
        funding_hours: sim.funding_hours,
        fill_policy: sim.fill_policy,
        funding_schedule: funding,
        round_trip_cost_bps: sim.round_trip_cost_bps,
        bars,
        store,
    };
    kernel
        .run(&draft, i, bars.closes.len(), snap.predicate_ir.as_ref())
        .ok()
}

/// Re-derive the observed-outcome ledger when the request omits it (D-081: the
/// compute plane persists no outcomes ledger; the observed outcome IS the
/// replayed ACTUAL action, so reconciliation passes by construction — exactly
/// the identity the oracle's lifecycle recorded).
fn derive_outcomes(
    snapshots: &[reconcile::CandidateSnapshot],
    ds: &Dataset,
    stores: &[FeatureStore],
    sim: &SimulatorParams,
    funding: &[(i64, f64)],
    threads: usize,
) -> Vec<Value> {
    let n = snapshots.len();
    if n == 0 {
        return Vec::new();
    }
    let workers = threads.max(1).min(n);
    if workers <= 1 {
        let mut out = Vec::new();
        for snap in snapshots {
            let Some(s) = replay_actual_surface(snap, ds, stores, sim, funding) else {
                continue;
            };
            let surf = s.reconcile_surface(&snap.candidate_id, "ACTUAL");
            out.push(json!({
                "candidate_id": surf.candidate_id,
                "endpoint": surf.endpoint,
                "label_status": surf.label_status,
                "horizon_bars": surf.horizon_bars,
                "ambiguous_bars": surf.ambiguous_bars,
                "net_r": surf.net_r,
                "entry_price": surf.entry_price,
                "risk_unit_price": surf.risk_unit_price,
                "mae_r": surf.mae_r,
                "mfe_r": surf.mfe_r,
                "market_move_r": surf.market_move_r,
            }));
        }
        out
    } else {
        let bounds = crate::scheduler::chunk_bounds(n, workers);
        let mut results = Vec::with_capacity(n);
        std::thread::scope(|s| {
            let mut handles = Vec::with_capacity(workers);
            for w in 0..workers {
                let (lo, hi) = (bounds[w], bounds[w + 1]);
                let chunk_snaps = &snapshots[lo..hi];
                handles.push(s.spawn(move || {
                    let mut chunk_out = Vec::with_capacity(hi - lo);
                    for snap in chunk_snaps {
                        if let Some(s) = replay_actual_surface(snap, ds, stores, sim, funding) {
                            let surf = s.reconcile_surface(&snap.candidate_id, "ACTUAL");
                            chunk_out.push(json!({
                                "candidate_id": surf.candidate_id,
                                "endpoint": surf.endpoint,
                                "label_status": surf.label_status,
                                "horizon_bars": surf.horizon_bars,
                                "ambiguous_bars": surf.ambiguous_bars,
                                "net_r": surf.net_r,
                                "entry_price": surf.entry_price,
                                "risk_unit_price": surf.risk_unit_price,
                                "mae_r": surf.mae_r,
                                "mfe_r": surf.mfe_r,
                                "market_move_r": surf.market_move_r,
                            }));
                        }
                    }
                    chunk_out
                }));
            }
            for h in handles {
                if let Ok(chunk) = h.join() {
                    results.extend(chunk);
                }
            }
        });
        results
    }
}

/// Re-derive the states ledger (and the DETECTED transitions' `state_id`) when
/// the request omits it. Each DETECTED transition whose record lacks a
/// `state_id` gets the decision-time state id re-derived the same way the S1
/// features path does (`state::v82_state_id` over the birth-bar features), and
/// a symbol-prefixed state record is emitted per candidate — the store
/// projection `assert_pit_lineage` and Phase 3 (`load_birth_features`) read.
/// Records that already carry a `state_id` pass through untouched.
fn derive_state_ledger(
    candidates: &[Value],
    stores: &[FeatureStore],
    universe: &[String],
    history_depth: usize,
) -> (Vec<Value>, Vec<Value>) {
    let mut states: Vec<Value> = Vec::new();
    let mut out: Vec<Value> = Vec::with_capacity(candidates.len());
    let mut state_cache: HashMap<(String, i64), (String, Value)> = HashMap::new();
    for rec in candidates {
        let mut r = rec.clone();
        if rec.get("to_state").and_then(|v| v.as_str()) != Some("DETECTED")
            || rec.get("state_id").is_some()
        {
            out.push(r);
            continue;
        }
        let sym = rec.get("instrument").and_then(|v| v.as_str()).unwrap_or("");
        let as_of = rec
            .get("knowledge_time")
            .and_then(|v| v.as_i64())
            .unwrap_or(0);
        if let Some((sid, state_val)) = state_cache.get(&(sym.to_string(), as_of)) {
            states.push(state_val.clone());
            r.as_object_mut()
                .expect("record is an object")
                .insert("state_id".to_string(), json!(sid));
            out.push(r);
            continue;
        }
        if let Some(store) = stores.iter().find(|s| s.symbol == sym) {
            if let Ok(i) = store.avail.binary_search(&as_of) {
                let feats = state::state_features(store, i + 1, as_of, history_depth);
                let lineage = state::v82_lineage_hash(&feats, sym);
                let sid = state::v82_state_id(as_of, universe, &lineage);
                let mut features = serde_json::Map::new();
                for f in &feats {
                    features.insert(
                        format!("{sym}.{}", f.name),
                        json!({
                            "name": f.name,
                            "value": f.value,
                            "dtype": f.dtype,
                            "feature_version": f.feature_version,
                            "max_input_available_time": f.max_input_available_time,
                            "quality": f.quality,
                        }),
                    );
                }
                let quality = if feats.iter().any(|f| f.quality == "DEGRADED") {
                    "DEGRADED"
                } else {
                    "COMPLETE"
                };
                let state_val = json!({
                    "state_id": sid,
                    "as_of": as_of,
                    "universe": universe,
                    "features": features,
                    "lineage_hash": lineage,
                    "quality": quality,
                });
                states.push(state_val.clone());
                state_cache.insert((sym.to_string(), as_of), (sid.clone(), state_val));
                r.as_object_mut()
                    .expect("record is an object")
                    .insert("state_id".to_string(), json!(sid));
            }
        }
        out.push(r);
    }
    (out, states)
}

// ---------------------------------------------------------------------------
// Phase 1: the cube-reduced table + reconciled snapshots -> joined rows
// ---------------------------------------------------------------------------

/// The ACTUAL action's cube-reduced accumulators for one snapshot, re-derived
/// by replay (the compute plane reduces the cube in flight, D-081; the eight
/// OutcomeCubeRow value fields come from the replayed surface — `cost_r` /
/// `funding_r` are not carried by the compute-plane Outcome and read `None`,
/// exactly a `cube_by_key` miss in the oracle).
fn replay_actual_accumulators(
    snap: &reconcile::CandidateSnapshot,
    ds: &Dataset,
    stores: &[FeatureStore],
    sim: &SimulatorParams,
    funding: &[(i64, f64)],
) -> Option<CubeAccumulators> {
    let s = replay_actual_surface(snap, ds, stores, sim, funding)?;
    let surf = s.reconcile_surface(&snap.candidate_id, "ACTUAL");
    Some(CubeAccumulators {
        endpoint: Some(surf.endpoint),
        label_status: Some(surf.label_status),
        horizon_bars: Some(surf.horizon_bars),
        // The compute Outcome now carries the round-trip cost and funding the
        // oracle's cube rows record (the phase-1 join compares them).
        cost_r: Some(s.cost_r),
        funding_r: Some(s.funding_r),
        mae_r: Some(surf.mae_r),
        mfe_r: Some(surf.mfe_r),
        ambiguous_bars: Some(surf.ambiguous_bars),
    })
}

/// Build the Phase-1 per-symbol input (issue #118): the reconciled snapshot
/// projection (identities), the cube-reduced gap rows (gaps), and the ACTUAL
/// action's cube accumulators re-derived per BOUND snapshot.
fn build_phase0(
    snapshots: &[reconcile::CandidateSnapshot],
    ds: &Dataset,
    stores: &[FeatureStore],
    sim: &SimulatorParams,
    funding: &[(i64, f64)],
    cube: &evidence::ReadBack,
) -> Vec<(String, Phase0Output)> {
    let mut by_symbol: HashMap<String, Phase0Output> = HashMap::new();
    let mut cid_symbol: HashMap<&str, &str> = HashMap::new();
    let mut cid_snap: HashMap<&str, &reconcile::CandidateSnapshot> = HashMap::new();
    for s in snapshots {
        cid_symbol.insert(s.candidate_id.as_str(), s.instrument.as_str());
        cid_snap.insert(s.candidate_id.as_str(), s);
        let entry = by_symbol.entry(s.instrument.clone()).or_default();
        entry.identities.insert(
            s.candidate_id.clone(),
            CandidateIdentity {
                expert_id: s.expert_id.clone(),
                direction: s.direction.clone(),
                birth_time: s.birth_time,
            },
        );
    }

    let mut accum_cache: HashMap<&str, Option<CubeAccumulators>> = HashMap::new();

    let col_str = |name: &str, i: usize| -> Option<String> {
        cube.column(name)?
            .get(i)
            .cloned()
            .flatten()
            .and_then(|v| v.as_str().map(|s| s.to_string()))
    };
    let col_f64 = |name: &str, i: usize| -> Option<f64> {
        cube.column(name)?
            .get(i)
            .cloned()
            .flatten()
            .and_then(|v| v.as_f64())
    };
    let col_i64 = |name: &str, i: usize| -> i64 {
        cube.column(name)
            .and_then(|c| c.get(i))
            .cloned()
            .flatten()
            .and_then(|v| v.as_i64())
            .unwrap_or(0)
    };

    let n = cube.row_count();
    for i in 0..n {
        let Some(cid) = col_str("candidate_id", i) else {
            continue;
        };
        let Some(symbol) = cid_symbol.get(cid.as_str()).map(|s| s.to_string()) else {
            continue;
        };
        let snap = cid_snap.get(cid.as_str()).copied();
        let aid = col_str("actual_action_id", i);
        let gap = GapRecord {
            candidate_id: cid.clone(),
            actual_action_id: aid.clone(),
            actual_utility: col_f64("actual_utility", i),
            best_utility: col_f64("best_utility", i),
            tie_cardinality: col_i64("tie_cardinality", i) as usize,
            legal_hindsight_gap: col_f64("legal_hindsight_gap", i),
            gap_status: col_str("gap_status", i).unwrap_or_default(),
        };
        by_symbol.entry(symbol.clone()).or_default().gaps.push(gap);
        if let (Some(aid), Some(snap)) = (aid, snap) {
            let acc_opt = accum_cache
                .entry(snap.candidate_id.as_str())
                .or_insert_with(|| replay_actual_accumulators(snap, ds, stores, sim, funding));
            if let Some(acc) = acc_opt.clone() {
                by_symbol
                    .entry(symbol.clone())
                    .or_default()
                    .cubes
                    .insert((cid, aid), acc);
            }
        }
    }

    let mut per_symbol: Vec<(String, Phase0Output)> = by_symbol.into_iter().collect();
    per_symbol.sort_by(|a, b| a.0.cmp(&b.0));
    per_symbol
}

// ---------------------------------------------------------------------------
// Phase 2: 72-slice systematicity discovery over the joined dataset
// ---------------------------------------------------------------------------

/// FCR-V8RR-007 CONTRACT 6: the discovery/confirmation split is chronological
/// at the dev window's midpoint. The compute plane approximates it
/// deterministically — rows sorted by birth_time (tie-broken by candidate_id),
/// the earlier half is the DISCOVERY half, the remainder the untouched
/// CONFIRMATION half. The ceiling midpoint keeps the chronologically-earlier
/// rows (the first `ceil(n/2)`) in discovery when the count is odd.
fn split_half(rows: &[JoinedCandidateRow]) -> (Vec<JoinedCandidateRow>, Vec<JoinedCandidateRow>) {
    let mut sorted: Vec<JoinedCandidateRow> = rows.to_vec();
    sorted.sort_by(|a, b| {
        a.birth_time
            .cmp(&b.birth_time)
            .then_with(|| a.candidate_id.cmp(&b.candidate_id))
    });
    let mid = sorted.len().div_ceil(2);
    let disc = sorted[..mid].to_vec();
    let conf = sorted[mid..].to_vec();
    (disc, conf)
}

/// The Phase-2 slice-row projection of a Phase-1 joined row (`regret_phase2.py`
/// indexes exactly these fields).
fn slice_row(r: &JoinedCandidateRow) -> phase2::SliceRow {
    phase2::SliceRow {
        expert_id: r.expert_id.clone(),
        symbol: r.symbol.clone(),
        direction: r.direction.clone(),
        gap_status: r.gap_status.clone(),
        legal_hindsight_gap: r.legal_hindsight_gap,
        actual_utility: r.actual_utility,
        horizon_bars: r.horizon_bars,
    }
}

// ---------------------------------------------------------------------------
// Artifact writers
// ---------------------------------------------------------------------------

fn joined_row_to_value(r: &JoinedCandidateRow) -> Value {
    json!({
        "symbol": r.symbol,
        "candidate_id": r.candidate_id,
        "expert_id": r.expert_id,
        "direction": r.direction,
        "birth_time": r.birth_time,
        "gap_status": r.gap_status,
        "legal_hindsight_gap": r.legal_hindsight_gap,
        "actual_utility": r.actual_utility,
        "best_utility": r.best_utility,
        "tie_cardinality": r.tie_cardinality,
        "endpoint": r.endpoint,
        "label_status": r.label_status,
        "horizon_bars": r.horizon_bars,
        "cost_r": r.cost_r,
        "funding_r": r.funding_r,
        "mae_r": r.mae_r,
        "mfe_r": r.mfe_r,
        "ambiguous_bars": r.ambiguous_bars,
        "epistemic_class": r.epistemic_class,
    })
}

fn slice_result_to_value(r: &phase2::SliceResult) -> Value {
    json!({
        "slice_key": r.slice_key,
        "expert_id": r.expert_id,
        "symbol": r.symbol,
        "direction": r.direction,
        "estimand": r.estimand,
        "n_total_in_slice": r.n_total_in_slice,
        "n_computed": r.n_computed,
        "effective_independent_episodes": r.effective_independent_episodes,
        "mean": r.mean,
        "ci_lower": r.ci_lower,
        "ci_upper": r.ci_upper,
        "block_size": r.block_size,
        "alpha_slate": r.alpha_slate,
        "practically_significant": r.practically_significant,
        "materiality_note": r.materiality_note,
        "discovery_verdict": r.discovery_verdict,
        "confirmation_verdict": r.confirmation_verdict,
    })
}

fn confirmation_to_value(c: &phase2::ConfirmationResult) -> Value {
    json!({
        "slice_key": c.slice_key,
        "confirmation_verdict": c.confirmation_verdict,
        "confirmation_mean": c.confirmation_mean,
        "confirmation_ci_lower": c.confirmation_ci_lower,
        "confirmation_ci_upper": c.confirmation_ci_upper,
        "confirmation_n_computed": c.confirmation_n_computed,
    })
}

/// Materialize the ledger projection into the per-symbol store dirs Phase 3
/// reads (`store_dir/candidates.jsonl` DETECTED edges + `states.jsonl`). The
/// states ledger must carry symbol-prefixed feature keys (`{SYMBOL}.{feature}`
/// values), the projection `load_birth_features` reads (FT001).
fn write_phase3_store_dirs(
    out_dir: &Path,
    symbols: &[String],
    candidates: &[Value],
    states: &[Value],
) -> Result<HashMap<String, String>, String> {
    let mut dirs = HashMap::new();
    let detected: Vec<&Value> = candidates
        .iter()
        .filter(|c| c.get("to_state").and_then(|v| v.as_str()) == Some("DETECTED"))
        .collect();
    let mut stext = String::new();
    for s in states {
        stext.push_str(&serde_json::to_string(s).map_err(|e| e.to_string())?);
        stext.push('\n');
    }
    for sym in symbols {
        let dir = out_dir.join(sym);
        std::fs::create_dir_all(&dir).map_err(|e| format!("create {dir:?}: {e}"))?;
        let mut ctext = String::new();
        for rec in &detected {
            ctext.push_str(&serde_json::to_string(rec).map_err(|e| e.to_string())?);
            ctext.push('\n');
        }
        std::fs::write(dir.join("candidates.jsonl"), ctext)
            .map_err(|e| format!("write {}/candidates.jsonl: {e}", dir.display()))?;
        std::fs::write(dir.join("states.jsonl"), &stext)
            .map_err(|e| format!("write {}/states.jsonl: {e}", dir.display()))?;
        dirs.insert(sym.clone(), dir.to_string_lossy().to_string());
    }
    Ok(dirs)
}

// ---------------------------------------------------------------------------
// The composition
// ---------------------------------------------------------------------------

/// S6 composition: reconciliation -> phases 1-3 over the loop/cube output,
/// writing `analysis.jsonl` (the phase-1 join rows, the 72 slice verdicts, the
/// confirmation results and the phase-3 recoverability results) plus the
/// phase-3 artifacts. Returns the summary object; errors halt (reconciliation
/// failure or PIT lineage violation fail closed, mirroring `reconcile`).
pub fn run_analysis(req: &AnalysisRequest) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;
    let universe: Vec<String> = if req.universe.is_empty() {
        stores.iter().map(|s| s.symbol.clone()).collect()
    } else {
        req.universe.clone()
    };

    // The loop output: run the S4 evaluate loop unless the request names an
    // existing evaluations.jsonl (the cube-reduced artifact defaults to
    // {out_dir}/cube-reduced.v82, which the loop also writes).
    let evaluations: Vec<Value> = if !req.evaluations.is_empty() {
        req.evaluations.clone()
    } else {
        let eval_path = match &req.evaluations_path {
            Some(p) => p.clone(),
            None => {
                let p = req.out_dir.join("evaluations.jsonl");
                if !p.exists() {
                    crate::runloop::run_for_analysis(
                        &req.tape_path,
                        &universe,
                        &req.out_dir,
                        &req.manifest,
                    )?;
                }
                p
            }
        };
        read_evaluations_jsonl(&eval_path)?
    };
    let candidates: Vec<Value> = if !req.candidates.is_empty() {
        req.candidates.clone()
    } else {
        read_jsonl(&req.out_dir.join("candidates.jsonl"))?
    };
    let cube_path = req
        .cube_reduced_path
        .clone()
        .unwrap_or_else(|| req.out_dir.join("cube-reduced.v82"));

    // The store derivation for the ledgers the request does not carry (D-081).
    let sim = SimulatorParams::from_json(&req.manifest);
    let funding = funding_schedule(&ds);
    let pre_snaps = reconcile::build_snapshots(&candidates, &evaluations, &req.outcomes);
    let outcomes: Vec<Value> = if req.outcomes.is_empty() {
        derive_outcomes(&pre_snaps, &ds, &stores, &sim, &funding, req.threads)
    } else {
        req.outcomes.clone()
    };
    let (candidates, states) = if req.states.is_empty() {
        derive_state_ledger(
            &candidates,
            &stores,
            &universe,
            state::HISTORY_DEPTH_DEFAULT,
        )
    } else {
        (candidates, req.states.clone())
    };

    // Phase 0 — reconciliation (issue #122). Halt on lineage leakage or a
    // non-RECONCILED ledger, exactly like `reconcile`'s fail-closed gate.
    let snapshots = reconcile::build_snapshots(&candidates, &evaluations, &outcomes);
    let problems = reconcile::assert_pit_lineage(&states, &snapshots);
    if !problems.is_empty() {
        return Err(format!(
            "PIT lineage violation — future leakage, refusing to proceed: {}",
            problems.join("; ")
        ));
    }
    let recon = reconcile::reconcile_actual_actions(&snapshots, &ds.bars, &stores, &sim, &funding);
    if recon.verdict != reconcile::RECONCILED {
        let detail = recon
            .mismatches
            .iter()
            .map(|(cid, reason)| format!("{cid}:{reason}"))
            .collect::<Vec<_>>()
            .join(" | ");
        let clipped: String = detail.chars().take(1200).collect();
        return Err(format!(
            "reconciliation failed ({} executed, {} reconciled, {} mismatched, {} not applicable) \
             — refusing to compose the regret phases. mismatches: {}",
            recon.n_executed,
            recon.n_reconciled,
            recon.n_mismatched,
            recon.n_not_applicable,
            clipped
        ));
    }

    // Phase 1 — opportunity accounting over the cube-reduced table.
    let cube = evidence::read_artifact(&cube_path)
        .map_err(|e| format!("read cube artifact {cube_path:?}: {e}"))?;
    let per_symbol = build_phase0(&snapshots, &ds, &stores, &sim, &funding, &cube);
    let joined = phase1::join_dataset(per_symbol);

    // Phase 2 — systematicity discovery over the chronological halves.
    let (disc, conf) = split_half(&joined);
    let disc_slices: Vec<phase2::SliceRow> = disc.iter().map(slice_row).collect();
    let conf_slices: Vec<phase2::SliceRow> = conf.iter().map(slice_row).collect();
    let declared = phase2::declare_slices();
    let workers = req.threads.max(1);
    let slice_results: Vec<phase2::SliceResult> = if workers <= 1 {
        let mut out = Vec::with_capacity(declared.len());
        for s in &declared {
            out.push(phase2::score_slice(
                &s[0],
                &s[1],
                &s[2],
                &s[3],
                &s[4],
                &disc_slices,
            ));
        }
        out
    } else {
        let n = declared.len();
        let workers = workers.min(n);
        let bounds = crate::scheduler::chunk_bounds(n, workers);
        let mut results = Vec::with_capacity(n);
        std::thread::scope(|s| -> Result<Vec<phase2::SliceResult>, String> {
            let mut handles = Vec::with_capacity(workers);
            for w in 0..workers {
                let (lo, hi) = (bounds[w], bounds[w + 1]);
                let dec = &declared;
                let slices = &disc_slices;
                handles.push(s.spawn(move || {
                    let mut chunk = Vec::with_capacity(hi - lo);
                    for i in lo..hi {
                        let item = &dec[i];
                        chunk.push(phase2::score_slice(
                            &item[0],
                            &item[1],
                            &item[2],
                            &item[3],
                            &item[4],
                            slices,
                        ));
                    }
                    chunk
                }));
            }
            for h in handles {
                let chunk = h
                    .join()
                    .map_err(|_| "worker fault in phase2 slice evaluation".to_string())?;
                results.extend(chunk);
            }
            Ok(results)
        })?
    };
    let discovery = phase2::discovery_summary(&slice_results);
    let mut confirmation_ledger = phase2::ConfirmationLedger::new();
    let mut confirmations: Vec<phase2::ConfirmationResult> = Vec::new();
    for r in &slice_results {
        if r.discovery_verdict == "CANDIDATE_SYSTEMATIC" {
            confirmations.push(
                confirmation_ledger
                    .query(r, &conf_slices)
                    .map_err(|e| e.to_string())?,
            );
        }
    }
    let confirmed_keys: Vec<String> = confirmations
        .iter()
        .filter(|c| c.confirmation_verdict == "SYSTEMATIC_FINDING")
        .map(|c| c.slice_key.clone())
        .collect();

    // Phase 3 — recoverability over the confirmed slices.
    let mut symbols: Vec<String> = joined.iter().map(|r| r.symbol.clone()).collect();
    symbols.sort();
    symbols.dedup();
    let disc_json: Vec<Value> = disc.iter().map(joined_row_to_value).collect();
    let conf_json: Vec<Value> = conf.iter().map(joined_row_to_value).collect();
    let store_dirs = write_phase3_store_dirs(&req.out_dir, &symbols, &candidates, &states)?;
    let phase3_summary = phase3::run_phase3(
        &confirmed_keys,
        &disc_json,
        &conf_json,
        &store_dirs,
        &req.out_dir,
    )?;

    // The `analysis.jsonl` artifact: one tagged record per phase row.
    let mut lines: Vec<Value> = Vec::new();
    for r in &joined {
        let mut v = joined_row_to_value(r);
        v.as_object_mut()
            .expect("row is an object")
            .insert("stage".to_string(), json!("phase1_join"));
        lines.push(v);
    }
    for r in &slice_results {
        let mut v = slice_result_to_value(r);
        v.as_object_mut()
            .expect("row is an object")
            .insert("stage".to_string(), json!("phase2_slice"));
        lines.push(v);
    }
    for c in &confirmations {
        let mut v = confirmation_to_value(c);
        v.as_object_mut()
            .expect("row is an object")
            .insert("stage".to_string(), json!("phase2_confirmation"));
        lines.push(v);
    }
    if let Some(results) = phase3_summary.get("results").and_then(|v| v.as_array()) {
        for r in results {
            let mut v = r.clone();
            v.as_object_mut()
                .expect("row is an object")
                .insert("stage".to_string(), json!("phase3_recoverability"));
            lines.push(v);
        }
    }
    let analysis_path = req.out_dir.join("analysis.jsonl");
    let mut text = String::new();
    for l in &lines {
        text.push_str(&serde_json::to_string(l).map_err(|e| e.to_string())?);
        text.push('\n');
    }
    std::fs::write(&analysis_path, text).map_err(|e| format!("write analysis.jsonl: {e}"))?;

    Ok(json!({
        "subcommand": "analysis",
        "n_candidates": snapshots.len(),
        "reconciliation": {
            "n_executed": recon.n_executed,
            "n_reconciled": recon.n_reconciled,
            "n_mismatched": recon.n_mismatched,
            "n_not_applicable": recon.n_not_applicable,
            "verdict": recon.verdict,
            "pit_lineage_problems": problems.len(),
        },
        "phase1": { "n_joined_rows": joined.len() },
        "phase2": {
            "discovery": {
                "n_slices_declared": discovery.n_slices_declared,
                "discovery_verdict_distribution": discovery.discovery_verdict_distribution,
                "n_candidate_systematic": discovery.n_candidate_systematic,
                "expected_false_positives_at_family_alpha":
                    discovery.expected_false_positives_at_family_alpha,
                "alpha_slate_bonferroni": discovery.alpha_slate_bonferroni,
                "candidate_systematic_slices": discovery.candidate_systematic_slices,
            },
            "n_candidate_systematic_tested": confirmations.len(),
            "n_systematic_finding": confirmed_keys.len(),
        },
        "phase3": phase3_summary,
        "analysis_artifact": analysis_path.to_string_lossy().to_string(),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::candidate::{episode_key, geometry_version};
    use crate::regret;

    const SYMBOL: &str = "SOLUSDT";
    const DETECTED_AT: i64 = 3000;
    const ENTRY_TIME: i64 = 5000; // EXECUTED knowledge_time -> bar index 4

    fn geometry_map() -> serde_json::Map<String, Value> {
        // Same structural geometry as the reconcile fixture (target_r is
        // off-grid, expiry_bars on-grid -> an 11-action manifest).
        let mut m = serde_json::Map::new();
        m.insert("target_r".to_string(), json!(1.5));
        m.insert("stop_r".to_string(), json!(1.0));
        m.insert("expiry_bars".to_string(), json!(8));
        m.insert("risk_frac".to_string(), json!(0.01));
        m
    }

    fn geometry_version_hex() -> String {
        geometry_version(&geometry_map())
    }

    fn rust_cid(expert: &str, anchor: &str) -> String {
        episode_key(
            expert,
            "1.0",
            SYMBOL,
            "LONG",
            anchor,
            &geometry_version_hex(),
        )
    }

    fn kline_row(id: &str, t: i64, o: f64, h: f64, l: f64, c: f64, v: f64) -> Value {
        json!({
            "source": "binance-um", "channel": "kline", "instrument": SYMBOL,
            "event_time": t, "available_time": t, "ingested_time": t,
            "venue_sequence": 1, "event_id": id,
            "payload": {"open": o, "high": h, "low": l, "close": c,
                        "volume": v, "closed": true},
        })
    }

    /// The 10-bar tape (identical OHLC to the reconcile oracle fixture).
    fn tape_values() -> Vec<Value> {
        let bars: [(f64, f64, f64, f64, f64); 10] = [
            (100.0, 102.0, 99.5, 101.0, 1000.0),
            (101.0, 103.0, 100.5, 102.5, 1100.0),
            (102.5, 106.0, 102.0, 105.0, 1200.0),
            (105.0, 107.0, 104.0, 106.0, 1300.0),
            (106.0, 108.0, 105.0, 107.0, 1400.0),
            (107.0, 109.0, 106.0, 108.0, 1500.0),
            (108.0, 110.0, 107.0, 109.0, 1600.0),
            (109.0, 111.0, 108.0, 110.0, 1700.0),
            (110.0, 112.0, 109.0, 111.0, 1800.0),
            (111.0, 113.0, 110.0, 112.0, 1900.0),
        ];
        bars.iter()
            .enumerate()
            .map(|(i, (o, h, l, c, v))| {
                kline_row(
                    &format!("sol-{i}"),
                    (i as i64 + 1) * 1000,
                    *o,
                    *h,
                    *l,
                    *c,
                    *v,
                )
            })
            .collect()
    }

    fn write_tape(path: &Path) {
        let text: String = tape_values().iter().map(|r| r.to_string() + "\n").collect();
        std::fs::write(path, text).unwrap();
    }

    fn draft_value(expert: &str, anchor: &str) -> Value {
        json!({
            "expert_id": expert, "expert_version": "1.0",
            "instrument": SYMBOL, "direction": "LONG",
            "setup_fingerprint": "synthetic",
            "risk_geometry": geometry_map(),
            "birth_time": DETECTED_AT,
            "setup_anchor_event_id": anchor,
            "size": 1.0,
        })
    }

    fn eval_record(expert: &str, anchor: &str) -> Value {
        json!({
            "expert_id": expert, "version": "1.0", "state_id": "st-sol-x",
            "applicability": "APPLICABLE", "decision": "CANDIDATE",
            "knowledge_time": DETECTED_AT,
            "draft": draft_value(expert, anchor),
            "source": "expert", "event_id": "eval",
        })
    }

    fn transition(cid: &str, seq: i64, from: Option<&str>, to: &str, kt: i64) -> Value {
        let mut v = serde_json::Map::new();
        v.insert("candidate_id".to_string(), json!(cid));
        v.insert("sequence".to_string(), json!(seq));
        v.insert("from_state".to_string(), json!(from));
        v.insert("to_state".to_string(), json!(to));
        v.insert("reason_code".to_string(), json!("test"));
        v.insert("knowledge_time".to_string(), json!(kt));
        v.insert("source".to_string(), json!("lifecycle"));
        v.insert("event_id".to_string(), json!(format!("{cid}:{seq}")));
        Value::Object(v)
    }

    /// Full DETECTED -> ... -> EXECUTED chain entering at bar 4, carrying the
    /// birth state id (mirror of the reconcile fixture).
    fn entered_transitions(cid: &str, expert: &str, anchor: &str, sid: &str) -> Vec<Value> {
        let mut detected = match transition(cid, 1, None, "DETECTED", DETECTED_AT) {
            Value::Object(m) => m,
            _ => unreachable!(),
        };
        detected.insert("expert_id".to_string(), json!(expert));
        detected.insert("expert_version".to_string(), json!("1.0"));
        detected.insert("instrument".to_string(), json!(SYMBOL));
        detected.insert("direction".to_string(), json!("LONG"));
        detected.insert("setup_anchor_event_id".to_string(), json!(anchor));
        detected.insert(
            "geometry_version".to_string(),
            json!(geometry_version_hex()),
        );
        detected.insert("state_id".to_string(), json!(sid));
        let mut chain = vec![Value::Object(detected)];
        chain.push(transition(cid, 2, Some("DETECTED"), "PENDING", 3100));
        chain.push(transition(cid, 3, Some("PENDING"), "TRIGGERED", 3200));
        chain.push(transition(cid, 4, Some("TRIGGERED"), "ACCEPTED", 3300));
        chain.push(transition(
            cid,
            5,
            Some("ACCEPTED"),
            "ORDER_SUBMITTED",
            3400,
        ));
        chain.push(transition(
            cid,
            6,
            Some("ORDER_SUBMITTED"),
            "EXECUTED",
            ENTRY_TIME,
        ));
        chain
    }

    fn detected_only_transition(cid: &str, expert: &str, anchor: &str, sid: &str) -> Value {
        let mut m = match transition(cid, 1, None, "DETECTED", DETECTED_AT) {
            Value::Object(m) => m,
            _ => unreachable!(),
        };
        m.insert("expert_id".to_string(), json!(expert));
        m.insert("expert_version".to_string(), json!("1.0"));
        m.insert("instrument".to_string(), json!(SYMBOL));
        m.insert("direction".to_string(), json!("LONG"));
        m.insert("setup_anchor_event_id".to_string(), json!(anchor));
        m.insert(
            "geometry_version".to_string(),
            json!(geometry_version_hex()),
        );
        m.insert("state_id".to_string(), json!(sid));
        Value::Object(m)
    }

    /// A state record with symbol-prefixed phase-3 features (FT001) and a
    /// lineage-legal max_input_available_time.
    fn state_record(sid: &str, mia: i64) -> Value {
        json!({
            "state_id": sid, "as_of": DETECTED_AT, "universe": [SYMBOL],
            "features": {
                "SOLUSDT.rsi14": {"name": "rsi14", "value": 55.0, "dtype": "float64",
                                  "feature_version": "v1",
                                  "max_input_available_time": mia, "quality": "COMPLETE"},
                "SOLUSDT.bb_pct_b": {"name": "bb_pct_b", "value": 0.6, "dtype": "float64",
                                     "feature_version": "v1",
                                     "max_input_available_time": mia, "quality": "COMPLETE"},
                "SOLUSDT.adx14": {"name": "adx14", "value": 22.0, "dtype": "float64",
                                  "feature_version": "v1",
                                  "max_input_available_time": mia, "quality": "COMPLETE"},
            },
            "lineage_hash": "0000000000000000000000000000000000000000",
            "quality": "COMPLETE",
        })
    }

    fn manifest() -> Value {
        json!({
            "round_trip_cost_r": 0.0, "funding_rate_r": 0.0,
            "funding_hours": 0, "fill_policy": "FILL_AT_BAR_CLOSE",
        })
    }

    fn push_opt_f64(col: &mut evidence::Column, v: Option<f64>) {
        match v {
            Some(x) => col.push_f64(x),
            None => {
                col.push_f64(0.0);
                col.push_absent();
            }
        }
    }

    /// Write one cube-reduced row per value in `rows` (the same 15-column
    /// schema runloop's `write_cube_reduced` emits).
    fn write_cube_reduced(path: &Path, rows: &[Value]) {
        let mut art = evidence::Artifact::new(
            "cube-reduced",
            "VALUES",
            serde_json::json!({
                "hash_encoding": crate::hash::HASH_ENCODING,
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
        for row in rows {
            art.columns[c_cid].push_str(row["candidate_id"].as_str().unwrap());
            art.columns[c_mid].push_str(row["manifest_id"].as_str().unwrap_or(""));
            match row.get("actual_action_id").and_then(|v| v.as_str()) {
                Some(a) => art.columns[c_aid].push_str(a),
                None => {
                    art.columns[c_aid].push_str("");
                    art.columns[c_aid].push_absent();
                }
            }
            push_opt_f64(
                &mut art.columns[c_au],
                row.get("actual_utility").and_then(|v| v.as_f64()),
            );
            push_opt_f64(
                &mut art.columns[c_bu],
                row.get("best_utility").and_then(|v| v.as_f64()),
            );
            art.columns[c_tie].push_i64(
                row.get("tie_cardinality")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(0),
            );
            push_opt_f64(
                &mut art.columns[c_gap],
                row.get("legal_hindsight_gap").and_then(|v| v.as_f64()),
            );
            art.columns[c_gs]
                .push_str(row.get("gap_status").and_then(|v| v.as_str()).unwrap_or(""));
            art.columns[c_reason].push_str(
                row.get("abstention_reason")
                    .and_then(|v| v.as_str())
                    .unwrap_or(""),
            );
            push_opt_f64(
                &mut art.columns[c_nt],
                row.get("no_trade_value").and_then(|v| v.as_f64()),
            );
            for (name, col) in [
                ("n_ok", c_ok),
                ("n_censored", c_ce),
                ("n_undefined_future", c_uf),
                ("n_not_evaluable_action", c_ne),
                ("n_no_entry", c_no_entry),
            ] {
                art.columns[col].push_i64(row.get(name).and_then(|v| v.as_i64()).unwrap_or(0));
            }
            art.end_row();
        }
        art.write(path).unwrap();
    }

    /// A tiny synthetic store: C1 (entered, reconciles) + C2 (never entered)
    /// with a one-row cube-reduced table for C1. The request carries the
    /// ledger inline (outcomes omitted -> re-derived by the composition) and
    /// names the cube-reduced artifact; `analysis` must run reconcile ->
    /// phase1 -> phase2 -> phase3 without error and write `analysis.jsonl`.
    #[test]
    fn analysis_smoke_reconcile_through_phase3_without_error() {
        let tmp = std::env::temp_dir().join(format!("v8-analysis-smoke-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        write_tape(&tape);
        let out = tmp.join("out");

        let c1 = rust_cid("trend_pullback", "sol-setup-1");
        let c2 = rust_cid("ghost_expert", "sol-setup-2");
        let mut candidates = entered_transitions(&c1, "trend_pullback", "sol-setup-1", "st-sol-1");
        candidates.push(detected_only_transition(
            &c2,
            "ghost_expert",
            "sol-setup-2",
            "st-sol-2",
        ));
        let evaluations = vec![
            eval_record("trend_pullback", "sol-setup-1"),
            eval_record("ghost_expert", "sol-setup-2"),
        ];
        let states = vec![
            state_record("st-sol-1", DETECTED_AT - 1),
            state_record("st-sol-2", DETECTED_AT - 1),
        ];

        let geom = geometry_map();
        let aid = regret::action_id(&geom);
        let manifest_id = regret::generate_legal_actions(&geom).manifest_id;
        let cube_path = tmp.join("cube-reduced.v82");
        write_cube_reduced(
            &cube_path,
            &[json!({
                "candidate_id": c1,
                "manifest_id": manifest_id,
                "actual_action_id": aid,
                "actual_utility": 1.5000000000000036,
                "best_utility": 1.6,
                "tie_cardinality": 1,
                "legal_hindsight_gap": 0.09999999999999636,
                "gap_status": "COMPUTED",
                "abstention_reason": "",
                "no_trade_value": 0.0,
                "n_ok": 11, "n_censored": 0, "n_undefined_future": 0,
                "n_not_evaluable_action": 0, "n_no_entry": 0,
            })],
        );

        let req_path = tmp.join("request.json");
        let req = json!({
            "tape_path": tape,
            "out_dir": out,
            "universe": [SYMBOL],
            "manifest": manifest(),
            "candidates": candidates,
            "evaluations": evaluations,
            "states": states,
            "cube_reduced_path": cube_path,
        });
        std::fs::write(&req_path, serde_json::to_string_pretty(&req).unwrap()).unwrap();

        let code = analysis(&[req_path.to_str().unwrap().to_string()]);
        assert_eq!(code, 0, "tiny synthetic store must compose cleanly");

        // The analysis artifact carries every stage: 1 phase1 join row, all
        // 72 slice verdicts, and the (empty) confirmation + phase3 stages.
        let text = std::fs::read_to_string(out.join("analysis.jsonl")).unwrap();
        let lines: Vec<Value> = text
            .lines()
            .filter(|l| !l.trim().is_empty())
            .map(|l| serde_json::from_str(l).unwrap())
            .collect();
        assert_eq!(
            lines.len(),
            1 + 72,
            "1 phase-1 join row + 72 slice verdicts"
        );
        let stages: Vec<&str> = lines.iter().map(|l| l["stage"].as_str().unwrap()).collect();
        assert_eq!(stages[0], "phase1_join");
        assert!(stages[1..].iter().all(|s| *s == "phase2_slice"));
        assert_eq!(
            lines[1]["slice_key"],
            "trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap"
        );
        // The C1 slice has a single COMPUTED row -> INSUFFICIENT_SUPPORT.
        let c1_slice = lines
            .iter()
            .find(|l| l["slice_key"] == "trend_pullback|SOLUSDT|LONG|mean_legal_hindsight_gap")
            .unwrap();
        assert_eq!(c1_slice["n_computed"], 1);
        assert_eq!(c1_slice["discovery_verdict"], "INSUFFICIENT_SUPPORT");

        // Phase 3 ran (no confirmed slice -> empty summary, still written).
        let p3: Value = serde_json::from_str(
            &std::fs::read_to_string(out.join("phase3_summary.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(p3["n_slices_tested"], 0);
        assert!(out.join("recoverability_attempts.jsonl").exists());
    }
}
