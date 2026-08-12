//! S4 full per-bar loop (issue #105): ExpertPlane -> candidates -> reduce.
//!
//! The `evaluate` subcommand is the composition point: per bar x per symbol,
//! for each expert in `experts::TABLE` (canonical expert_id order, matching
//! `lab.run` PHASE 3's `sorted_experts`): build the D-053-projected FeatMap
//! (`features::group_closure` + `project_features`; `history` is withheld
//! unless the closure includes it), evaluate, and feed CANDIDATE drafts into
//! the candidate machinery in candidate.rs.
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
//! Admitted candidates then run the S2 ReplayKernel (simulator.rs) and feed
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
use crate::simulator::{self, ReplayKernel, SimulatorParams};
use crate::state::{self, FeatureStore};

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
    #[serde(default)]
    manifest: Value,
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

/// One admitted (PENDING) candidate, held for the S2/S3 reduce pass.
struct PendingCandidate {
    candidate_id: String,
    direction: String,
    birth_time: i64,
    entry_bar: usize,
    risk_geometry: serde_json::Map<String, Value>,
    symbol: String,
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

    // Dispatch table: the full TABLE in canonical expert_id order, or the
    // requested subset (order preserved — the evaluation/DETECTED record order
    // is part of the ledger hash).
    let table: Vec<(&str, &str)> = if req.experts.is_empty() {
        experts::TABLE.iter().map(|(id, _, ver, _)| (*id, *ver)).collect()
    } else {
        experts::TABLE.iter()
            .filter(|(id, _, _, _)| req.experts.iter().any(|e| e == id))
            .map(|(id, _, ver, _)| (*id, *ver))
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
                pending.push(PendingCandidate {
                    candidate_id: cid,
                    direction: draft.direction.clone(),
                    birth_time: draft.birth_time,
                    entry_bar: i + 1,
                    risk_geometry: draft.risk_geometry.clone(),
                    symbol: sym.clone(),
                });
                n_candidates += 1;
            }
        }
    }
    eval_out.flush().map_err(|e| e.to_string())?;
    cand_out.flush().map_err(|e| e.to_string())?;

    // S2 + S3: replay each admitted candidate and reduce the outcome cube.
    let reduced_path = req.out_dir.join("cube-reduced.v82");
    let n_reduced = write_cube_reduced(&reduced_path, &pending, &stores, &ds, &sim, &funding_schedule)?;

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
// S2 ReplayKernel + S3 CubeReducer per admitted candidate
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
                      sim: &SimulatorParams, funding_schedule: &[(i64, f64)])
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

    for cand in pending {
        let store = stores.iter().find(|s| s.symbol == cand.symbol)
            .ok_or_else(|| format!("no bars for symbol {}", cand.symbol))?;
        let bars = ds.bars.iter().find(|b| b.symbol == cand.symbol)
            .ok_or_else(|| format!("no bars for symbol {}", cand.symbol))?;
        let kernel = ReplayKernel {
            round_trip_cost_r: sim.round_trip_cost_r,
            funding_rate_r: sim.funding_rate_r,
            funding_hours: sim.funding_hours,
            fill_policy: sim.fill_policy,
            funding_schedule,
            round_trip_cost_bps: sim.round_trip_cost_bps,
            bars,
            store,
        };
        let manifest = regret::generate_legal_actions(&cand.risk_geometry);
        let window_end = store.closes.len();
        let entry_idx = cand.entry_bar;

        let mut cells = Vec::with_capacity(manifest.actions.len());
        for a in &manifest.actions {
            if a.kind == "NO_TRADE" {
                cells.push(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_OK,
                    reason: String::new(),
                    net_utility: Some(0.0),
                });
                continue;
            }
            if window_end.saturating_sub(entry_idx) <= regret::MIN_FUTURE_BARS {
                cells.push(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_UNDEFINED_FUTURE,
                    reason: format!("fewer than {} bars of future after the entry bar — the simulator would return a manufactured EXPIRY value", regret::MIN_FUTURE_BARS + 1),
                    net_utility: None,
                });
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
            let out = match kernel.run(&draft, entry_idx, window_end, None) {
                Ok(o) => o,
                Err(e) => {
                    cells.push(regret::Cell {
                        action_id: a.action_id.clone(),
                        status: regret::CELL_NOT_EVALUABLE_ACTION,
                        reason: format!("replay raised: {e}"),
                        net_utility: None,
                    });
                    continue;
                }
            };
            if out.label_status == "NOT_EXECUTED" {
                cells.push(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_NOT_EVALUABLE_ACTION,
                    reason: "action never filled on this tape (e.g. FILL_AT_LIMIT never traded through)".into(),
                    net_utility: None,
                });
                continue;
            }
            let status = if out.label_status == "MATURE" { regret::CELL_OK } else { regret::CELL_CENSORED };
            cells.push(regret::Cell {
                action_id: a.action_id.clone(),
                status,
                reason: if status == regret::CELL_OK { String::new() } else {
                    "replay reached tape end before a terminal endpoint".into()
                },
                net_utility: Some(out.net_r),
            });
        }

        let row = regret::compute_gap(&cand.candidate_id, &manifest, &cells);
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
        let table: Vec<(&str, &str)> = if experts.is_empty() {
            experts::TABLE.iter().map(|(id, _, ver, _)| (*id, *ver)).collect()
        } else {
            experts::TABLE.iter()
                .filter(|(id, _, _, _)| experts.iter().any(|e| e == id))
                .map(|(id, _, ver, _)| (*id, *ver))
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

}
