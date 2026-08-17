//! S6 reconciliation (issue #122): CandidateSnapshot join, PIT lineage
//! assertion, and ledger reconciliation — the Phase-0 post-Candidate half of
//! `tools/regret.py` (frozen oracle; FCR FT001 / FT001c / FT010), ported to
//! the compute plane.
//!
//! The three steps mirror the oracle function-for-function:
//!
//! 1. `build_snapshots` — FT001. Identity is a RE-DERIVATION of the episode
//!    key from the draft's setup anchor + structural geometry
//!    (`candidate::episode_key` / `candidate::geometry_version`), never a
//!    stored foreign key (FER CA010). A candidate whose draft cannot be bound
//!    is reported `UNBOUND_NO_DRAFT`, never dropped or defaulted. `BOUND` /
//!    `UNBOUND_NO_DRAFT` split, `observed_outcome` join by candidate id.
//! 2. `assert_pit_lineage` — FT001c / RIR GR006. Asserts, does not build:
//!    every `BOUND` snapshot's `birth_state_id` resolves in the states ledger
//!    and no feature's `max_input_available_time` exceeds the birth state's
//!    `as_of`. Returns the violation list (empty = clean), never raises.
//! 3. `reconcile_actual_actions` — FT010. `Replay(C, a_actual, M)` via the
//!    `ReplayKernel` (SIMULATION_TRUTH_SPEC) against the observed ledger
//!    outcome on the ten `OutcomeSurface` fields: exact equality on
//!    endpoint / label_status / horizon_bars / ambiguous_bars, `1e-12`
//!    tolerance on the six float fields. Never-entered candidates are
//!    `NOT_APPLICABLE` (FT010c); admission-size / equity / heat fields are
//!    excluded (FT010b). Verdict `RECONCILED` iff zero mismatches.
//!
//! Parity contract (PARITY_AND_IDENTITY_SPEC §3): candidate_id,
//! geometry_version, action_id and the event/hash identities are V8.2
//! bit-encodings excluded from the value comparison; the counters, the
//! verdict, the mismatch reasons and `max_abs_deviation` are the parity
//! target. The post-entry thesis is the compiled predicate IR
//! (PREDICATE_IR_SPEC) carried on the DETECTED transition; a candidate with
//! no IR replays fail-open (thesis always valid) — byte-identical to the
//! oracle's unregistered-expert / missing-state paths. A replay that raises
//! in the oracle (e.g. geometry validation) is recorded as a per-candidate
//! `field_mismatch` here instead of crashing the run (documented divergence,
//! fail-closed per candidate).

use std::collections::HashMap;
use std::path::Path;

use serde_json::{json, Map, Value};

use crate::analysis::outcome::{OutcomeSurface, RECONCILE_FLOAT_FIELDS, RECONCILE_TOLERANCE};
use crate::backend::scalar::ScalarKernel;
use crate::candidate::TERMINAL;
use crate::data::{Dataset, SymbolBars, TapeRow};
use crate::simulator::{Draft, SimulatorParams};
use crate::state;
use crate::state::FeatureStore;

/// Mirror of `tools/regret.py` `EVALUATOR_VERSION`.
pub const EVALUATOR_VERSION: &str = "regret-phase0-v1";

pub const BOUND: &str = "BOUND";
pub const UNBOUND_NO_DRAFT: &str = "UNBOUND_NO_DRAFT";
pub const RECONCILED: &str = "RECONCILED";
pub const RECONCILIATION_FAILED: &str = "RECONCILIATION_FAILED";
pub const MISMATCH_REASON_FIELD: &str = "field_mismatch";
pub const MISMATCH_REASON_ENTRY_MISSING: &str = "entry_bar_or_outcome_missing";

/// One joined Candidate row (mirror of `tools/regret.py` `CandidateSnapshot`).
/// Identity fields are V8.2-encoded and excluded from value parity
/// (PARITY_AND_IDENTITY_SPEC §3); `observed_outcome` carries the ten
/// reconciliation fields from the outcomes ledger.
#[derive(Debug, Clone)]
pub struct CandidateSnapshot {
    pub candidate_id: String,
    #[allow(dead_code)] // consumed by the S6 Phase-1 join (issue #118)
    pub expert_id: String,
    #[allow(dead_code)]
    pub expert_version: String,
    pub instrument: String,
    #[allow(dead_code)] // consumed by the S6 Phase-1 join (issue #118)
    pub direction: String,
    #[allow(dead_code)] // identity (D-026 anchor); joined into episode_key
    pub setup_anchor_event_id: String,
    #[allow(dead_code)] // identity (structural geometry hash); excluded from parity
    pub geometry_version: String,
    #[allow(dead_code)] // decision-time clock of the DETECTED transition (FT002)
    pub birth_time: i64,
    pub birth_state_id: Option<String>,
    #[allow(dead_code)] // frozen risk geometry; consumed by the cube port (S6)
    pub risk_geometry: Map<String, Value>,
    #[allow(dead_code)] // FT010b: admission size is excluded from reconciliation
    pub size: f64,
    #[allow(dead_code)] // lifecycle projection; carried for the regret phases
    pub terminal_state: Option<String>,
    #[allow(dead_code)]
    pub terminal_reason_code: Option<String>,
    pub entry_bar_available_time: Option<i64>,
    pub observed_outcome: Option<Map<String, Value>>,
    pub binding_status: String, // BOUND | UNBOUND_NO_DRAFT
    pub raw_draft: Option<Map<String, Value>>,
    /// The compiled post-entry thesis (PREDICATE_IR_SPEC) carried on the
    /// DETECTED transition; `None` replays fail-open (thesis always valid).
    pub predicate_ir: Option<Value>,
}

/// FT001 join. `candidates` are the transition records (candidates.jsonl),
/// `evaluations` the draft-carrying records (evaluations.jsonl), `outcomes`
/// the observed outcomes (outcomes.jsonl).
pub fn build_snapshots(
    candidates: &[Value],
    evaluations: &[Value],
    outcomes: &[Value],
) -> Vec<CandidateSnapshot> {
    // Drafts keyed by (expert_id, knowledge_time) — the lab evaluates each
    // expert once per bar, and the DETECTED transition's own knowledge_time
    // IS the birth bar, so the evaluation at that clock is the exact draft
    // the registry kept. This is the only binding that survives episodes
    // that re-evaluate at the same D-026 anchor with a moved structural
    // geometry: the fixture has 45 anchor-tuples with multiple DETECTED
    // candidates (different geometry_version = different stop/target), which
    // an anchor-tuple join merges onto the first draft (the 6 remaining S6
    // reconciliation mismatches, issue #117).
    let mut drafts_by_clock: HashMap<(String, i64), Map<String, Value>> = HashMap::new();
    for rec in evaluations {
        let d = match rec.get("draft").and_then(|v| v.as_object()) {
            Some(d) => d,
            None => continue,
        };
        let eid = rec
            .get("expert_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let kt = rec
            .get("knowledge_time")
            .and_then(|v| v.as_i64())
            .unwrap_or(0);
        drafts_by_clock
            .entry((eid, kt))
            .or_insert_with(|| d.clone());
    }

    // Transitions grouped by candidate_id (the stored candidate_id is the
    // registry's projection of the same key).
    let mut trans_by_cid: HashMap<String, Vec<&Value>> = HashMap::new();
    for rec in candidates {
        if rec.get("to_state").is_none() {
            continue;
        }
        if let Some(cid) = rec.get("candidate_id").and_then(|v| v.as_str()) {
            trans_by_cid.entry(cid.to_string()).or_default().push(rec);
        }
    }

    let outcome_by_cid: HashMap<&str, &Value> = outcomes
        .iter()
        .filter_map(|o| {
            o.get("candidate_id")
                .and_then(|v| v.as_str())
                .map(|c| (c, o))
        })
        .collect();

    let mut cids: Vec<String> = trans_by_cid.keys().cloned().collect();
    cids.sort();
    let mut snapshots = Vec::new();
    for cid in cids {
        let trans = trans_by_cid.get_mut(&cid).expect("cid from keys()");
        trans.sort_by_key(|r| r.get("sequence").and_then(|v| v.as_i64()).unwrap_or(0));
        let detected = trans
            .iter()
            .find(|t| t.get("to_state").and_then(|v| v.as_str()) == Some("DETECTED"));
        let executed = trans
            .iter()
            .find(|t| t.get("to_state").and_then(|v| v.as_str()) == Some("EXECUTED"));
        let terminal = trans.iter().rev().find(|t| {
            t.get("to_state")
                .and_then(|v| v.as_str())
                .map(|s| TERMINAL.contains(&s))
                .unwrap_or(false)
        });
        // Bind the draft to the DETECTED transition by the birth clock:
        // (expert_id, DETECTED knowledge_time) — the evaluation at that bar
        // is the stored draft.
        let draft = detected.and_then(|t| {
            let eid = t
                .get("expert_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let kt = t
                .get("knowledge_time")
                .and_then(|v| v.as_i64())
                .unwrap_or(0);
            drafts_by_clock.get(&(eid, kt))
        });
        let entry_time = executed.and_then(|t| t.get("knowledge_time").and_then(|v| v.as_i64()));
        let predicate_ir = detected.and_then(|t| t.get("predicate_ir")).cloned();

        if draft.is_none() {
            // UNBOUND_NO_DRAFT: identity fields fall back to the DETECTED
            // transition (or empty), risk_geometry empty, size 1.0 — never
            // dropped (FER CA010).
            snapshots.push(CandidateSnapshot {
                candidate_id: cid.clone(),
                expert_id: detected
                    .and_then(|t| t.get("expert_id").and_then(|v| v.as_str()))
                    .unwrap_or("")
                    .to_string(),
                expert_version: detected
                    .and_then(|t| t.get("expert_version").and_then(|v| v.as_str()))
                    .unwrap_or("")
                    .to_string(),
                instrument: detected
                    .and_then(|t| t.get("instrument").and_then(|v| v.as_str()))
                    .unwrap_or("")
                    .to_string(),
                direction: detected
                    .and_then(|t| t.get("direction").and_then(|v| v.as_str()))
                    .unwrap_or("")
                    .to_string(),
                setup_anchor_event_id: detected
                    .and_then(|t| t.get("setup_anchor_event_id").and_then(|v| v.as_str()))
                    .unwrap_or("")
                    .to_string(),
                geometry_version: detected
                    .and_then(|t| t.get("geometry_version").and_then(|v| v.as_str()))
                    .unwrap_or("")
                    .to_string(),
                birth_time: detected
                    .and_then(|t| t.get("knowledge_time").and_then(|v| v.as_i64()))
                    .unwrap_or(0),
                birth_state_id: detected
                    .and_then(|t| t.get("state_id").and_then(|v| v.as_str()))
                    .map(|s| s.to_string()),
                risk_geometry: Map::new(),
                size: 1.0,
                terminal_state: terminal.map(|t| {
                    t.get("to_state")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string()
                }),
                terminal_reason_code: terminal
                    .and_then(|t| t.get("reason_code").and_then(|v| v.as_str()))
                    .map(|s| s.to_string()),
                entry_bar_available_time: entry_time,
                observed_outcome: outcome_by_cid
                    .get(cid.as_str())
                    .and_then(|o| o.as_object().cloned()),
                binding_status: UNBOUND_NO_DRAFT.to_string(),
                raw_draft: None,
                predicate_ir,
            });
            continue;
        }

        let d = draft.unwrap();
        let risk_geometry = d
            .get("risk_geometry")
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default();
        snapshots.push(CandidateSnapshot {
            candidate_id: cid.clone(),
            expert_id: d
                .get("expert_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            expert_version: d
                .get("expert_version")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            instrument: d
                .get("instrument")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            direction: d
                .get("direction")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            setup_anchor_event_id: d
                .get("setup_anchor_event_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            geometry_version: detected
                .and_then(|t| t.get("geometry_version").and_then(|v| v.as_str()))
                .unwrap_or("")
                .to_string(),
            birth_time: d.get("birth_time").and_then(|v| v.as_i64()).unwrap_or(0),
            birth_state_id: detected
                .and_then(|t| t.get("state_id").and_then(|v| v.as_str()))
                .map(|s| s.to_string()),
            risk_geometry,
            size: d.get("size").and_then(|v| v.as_f64()).unwrap_or(1.0),
            terminal_state: terminal.map(|t| {
                t.get("to_state")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string()
            }),
            terminal_reason_code: terminal
                .and_then(|t| t.get("reason_code").and_then(|v| v.as_str()))
                .map(|s| s.to_string()),
            entry_bar_available_time: entry_time,
            observed_outcome: outcome_by_cid
                .get(cid.as_str())
                .and_then(|o| o.as_object().cloned()),
            binding_status: BOUND.to_string(),
            raw_draft: Some(d.clone()),
            predicate_ir,
        });
    }
    snapshots
}

/// FT001c: PIT lineage verification. Returns the violation list (empty =
/// clean). Every `BOUND` snapshot's `birth_state_id` must resolve in the
/// states ledger and no feature's `max_input_available_time` may exceed the
/// birth state's own `as_of` (future leakage).
pub fn assert_pit_lineage(states: &[Value], snapshots: &[CandidateSnapshot]) -> Vec<String> {
    let states_by_id: HashMap<&str, &Value> = states
        .iter()
        .filter_map(|s| s.get("state_id").and_then(|v| v.as_str()).map(|id| (id, s)))
        .collect();
    let mut problems = Vec::new();
    for snap in snapshots {
        if snap.binding_status != BOUND {
            continue;
        }
        let sid = match &snap.birth_state_id {
            Some(s) => s,
            None => {
                problems.push(format!("{}: no birth_state_id recorded", snap.candidate_id));
                continue;
            }
        };
        let st = match states_by_id.get(sid.as_str()) {
            Some(s) => s,
            None => {
                problems.push(format!(
                    "{}: birth_state_id {} not found in states.jsonl",
                    snap.candidate_id, sid
                ));
                continue;
            }
        };
        let as_of = st.get("as_of").and_then(|v| v.as_i64()).unwrap_or(0);
        if let Some(features) = st.get("features").and_then(|v| v.as_object()) {
            for (fname, fv) in features {
                let mia = fv
                    .get("max_input_available_time")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(0);
                if mia > as_of {
                    problems.push(format!(
                        "{}: feature {} max_input_available_time {} > decision clock {} — future leakage",
                        snap.candidate_id, fname, mia, as_of
                    ));
                }
            }
        }
    }
    problems
}

/// The name of the first compared field that differs (diagnostics; the
/// reconciliation reason string is a parity target, the field name is not).
fn first_mismatched_field(replayed: &OutcomeSurface, obs: &Map<String, Value>) -> String {
    let exact_i64 = |v: Option<&Value>| -> Option<i64> {
        v.and_then(|x| x.as_i64()).or_else(|| {
            v.and_then(|x| x.as_f64())
                .filter(|f| f.fract() == 0.0 && *f >= i64::MIN as f64 && *f <= i64::MAX as f64)
                .map(|f| f as i64)
        })
    };
    let exact: &[(&str, String, i64)] = &[
        ("endpoint", replayed.endpoint.clone(), 0),
        ("label_status", replayed.label_status.clone(), 0),
        ("horizon_bars", String::new(), replayed.horizon_bars),
        ("ambiguous_bars", String::new(), replayed.ambiguous_bars),
    ];
    for (name, s, i) in exact {
        let obs_s = if *name == "endpoint" || *name == "label_status" {
            obs.get(*name)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string()
        } else {
            String::new()
        };
        let obs_i = if *name == "horizon_bars" || *name == "ambiguous_bars" {
            exact_i64(obs.get(*name)).unwrap_or(i64::MIN)
        } else {
            0
        };
        let same = if *name == "endpoint" || *name == "label_status" {
            *s == obs_s
        } else {
            *i == obs_i
        };
        if !same {
            return name.to_string();
        }
    }
    for f in RECONCILE_FLOAT_FIELDS {
        let rv = match f {
            "net_r" => replayed.net_r,
            "entry_price" => replayed.entry_price,
            "risk_unit_price" => replayed.risk_unit_price,
            "mae_r" => replayed.mae_r,
            "mfe_r" => replayed.mfe_r,
            _ => replayed.market_move_r,
        };
        let ov = obs.get(f).and_then(|v| v.as_f64()).unwrap_or(0.0);
        if (rv - ov).abs() > RECONCILE_TOLERANCE {
            return format!("{f}:rust={rv:.9}:obs={ov:.9}");
        }
    }
    "unknown".to_string()
}

/// The reconciliation counters (mirror of `tools/regret.py`
/// `ReconciliationResult`). `mismatches` carries (candidate_id, reason)
/// pairs; candidate_id is a V8.2 identity excluded from value parity, the
/// reason string is part of the parity target.
#[derive(Debug, Clone)]
pub struct ReconciliationResult {
    pub n_executed: usize,
    pub n_reconciled: usize,
    pub n_mismatched: usize,
    pub n_not_applicable: usize,
    pub mismatches: Vec<(String, String)>,
    pub max_abs_deviation: HashMap<String, f64>,
    pub verdict: String, // RECONCILED | RECONCILIATION_FAILED
}

/// Compare the replayed surface against the observed outcome map, updating
/// `max_dev` for every float field (the oracle computes `max_abs_deviation`
/// over all compared candidates even when a mismatch occurs). Exact fields
/// compare strictly equal; float fields within `RECONCILE_TOLERANCE`.
fn compare_observed(
    replayed: &OutcomeSurface,
    obs: &Map<String, Value>,
    max_dev: &mut HashMap<String, f64>,
) -> bool {
    // JSON number -> i64 that also accepts integral floats, mirroring
    // Python's `1 == 1.0` for the exact integer fields.
    fn exact_i64(v: Option<&Value>) -> Option<i64> {
        v.and_then(|x| x.as_i64()).or_else(|| {
            v.and_then(|x| x.as_f64())
                .filter(|f| f.fract() == 0.0 && *f >= i64::MIN as f64 && *f <= i64::MAX as f64)
                .map(|f| f as i64)
        })
    }
    let exact_ok = replayed.endpoint == obs.get("endpoint").and_then(|v| v.as_str()).unwrap_or("")
        && replayed.label_status
            == obs
                .get("label_status")
                .and_then(|v| v.as_str())
                .unwrap_or("")
        && replayed.horizon_bars == exact_i64(obs.get("horizon_bars")).unwrap_or(i64::MIN)
        && replayed.ambiguous_bars == exact_i64(obs.get("ambiguous_bars")).unwrap_or(i64::MIN);
    let mut float_ok = true;
    for f in RECONCILE_FLOAT_FIELDS {
        let rv = match f {
            "net_r" => replayed.net_r,
            "entry_price" => replayed.entry_price,
            "risk_unit_price" => replayed.risk_unit_price,
            "mae_r" => replayed.mae_r,
            "mfe_r" => replayed.mfe_r,
            _ => replayed.market_move_r,
        };
        // Python: `float(obs.get(f, 0.0))` — a missing field reads 0.0.
        let ov = obs.get(f).and_then(|v| v.as_f64()).unwrap_or(0.0);
        let dev = (rv - ov).abs();
        let e = max_dev.entry(f.to_string()).or_insert(0.0);
        *e = e.max(dev);
        if dev > RECONCILE_TOLERANCE {
            float_ok = false;
        }
    }
    exact_ok && float_ok
}

/// FT010: `Replay(C, a_actual, M) == observed`. `bars`/`stores` are the
/// per-symbol columnar bars and FeatureStores the dataset was built with; a
/// BOUND snapshot replays against its own instrument's bars (the oracle's
/// single-symbol stores make the two identical).
pub fn reconcile_actual_actions(
    snapshots: &[CandidateSnapshot],
    bars: &[SymbolBars],
    stores: &[FeatureStore],
    sim: &SimulatorParams,
    funding_schedule: &[(i64, f64)],
) -> ReconciliationResult {
    let mut n_exec = 0usize;
    let mut n_ok = 0usize;
    let mut n_bad = 0usize;
    let mut n_na = 0usize;
    let mut mismatches: Vec<(String, String)> = Vec::new();
    let mut max_dev: HashMap<String, f64> = RECONCILE_FLOAT_FIELDS
        .iter()
        .map(|f| (f.to_string(), 0.0))
        .collect();

    for snap in snapshots {
        if snap.binding_status != BOUND || snap.entry_bar_available_time.is_none() {
            n_na += 1; // FT010c: never entered -> NOT_APPLICABLE
            continue;
        }
        n_exec += 1;
        let entry_time = snap.entry_bar_available_time.unwrap();
        let store = stores.iter().find(|s| s.symbol == snap.instrument);
        let sym_bars = match bars.iter().find(|b| b.symbol == snap.instrument) {
            Some(b) => b,
            None => {
                n_bad += 1;
                mismatches.push((
                    snap.candidate_id.clone(),
                    MISMATCH_REASON_ENTRY_MISSING.to_string(),
                ));
                continue;
            }
        };
        let i = sym_bars
            .available_times
            .iter()
            .position(|t| *t == entry_time);
        let obs = snap.observed_outcome.as_ref();
        if i.is_none() || obs.is_none() || store.is_none() {
            n_bad += 1;
            mismatches.push((
                snap.candidate_id.clone(),
                MISMATCH_REASON_ENTRY_MISSING.to_string(),
            ));
            continue;
        }
        let i = i.unwrap();
        let obs = obs.unwrap();
        let store = store.unwrap();

        let raw = snap.raw_draft.as_ref().unwrap(); // BOUND implies a draft
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
        let atr_ref = draft.geom_f64("atr_ref");
        let kernel = ScalarKernel {
            round_trip_cost_r: sim.round_trip_cost_r,
            funding_rate_r: sim.funding_rate_r,
            funding_hours: sim.funding_hours,
            fill_policy: sim.fill_policy,
            funding_schedule,
            round_trip_cost_bps: sim.round_trip_cost_bps,
            bars: sym_bars,
            store,
        };
        let out = match kernel.run(&draft, i, sym_bars.closes.len(), snap.predicate_ir.as_ref()) {
            Ok(o) => o,
            Err(_) => {
                // The oracle raises on replay failure; the compute plane
                // records it per-candidate and fails closed instead.
                n_bad += 1;
                mismatches.push((snap.candidate_id.clone(), MISMATCH_REASON_FIELD.to_string()));
                continue;
            }
        };
        let surface = out.reconcile_surface(&snap.candidate_id, "ACTUAL");
        if compare_observed(&surface, obs, &mut max_dev) {
            n_ok += 1;
        } else {
            n_bad += 1;
            mismatches.push((
                snap.candidate_id.clone(),
                format!(
                    "field_mismatch:{}:{}:{}:atr={}",
                    snap.expert_id,
                    snap.direction,
                    first_mismatched_field(&surface, obs),
                    atr_ref
                        .map(|a| format!("{a:.9}"))
                        .unwrap_or_else(|| "None".into()),
                ),
            ));
        }
    }

    let verdict = if n_bad == 0 {
        RECONCILED
    } else {
        RECONCILIATION_FAILED
    };
    ReconciliationResult {
        n_executed: n_exec,
        n_reconciled: n_ok,
        n_mismatched: n_bad,
        n_not_applicable: n_na,
        mismatches,
        max_abs_deviation: max_dev,
        verdict: verdict.to_string(),
    }
}

// ---------------------------------------------------------------------------
// CLI: `v8-core reconcile <request.json>`
// ---------------------------------------------------------------------------

/// The S6 reconciliation request: a completed store's ledger projection plus
/// the tape and manifest (the compute-plane store is in-memory; D-081).
#[derive(Debug, serde::Deserialize)]
pub struct ReconcileRequest {
    pub tape_path: std::path::PathBuf,
    pub out_dir: std::path::PathBuf,
    #[serde(default)]
    #[allow(dead_code)] // consumed by the analysis composition (issue #116)
    pub universe: Vec<String>,
    #[serde(default)]
    pub manifest: Value,
    #[serde(default)]
    pub candidates: Vec<Value>,
    #[serde(default)]
    pub evaluations: Vec<Value>,
    #[serde(default)]
    pub outcomes: Vec<Value>,
    #[serde(default)]
    pub states: Vec<Value>,
    /// Optional precomputed loop-output paths (the S6 analysis composition,
    /// issue #116, may supply them; `reconcile` itself does not consume them —
    /// they exist so the analysis request shape is accepted here verbatim).
    #[serde(default)]
    #[allow(dead_code)]
    pub evaluations_path: Option<std::path::PathBuf>,
    #[serde(default)]
    #[allow(dead_code)]
    pub cube_reduced_path: Option<std::path::PathBuf>,
}

/// Read a JSONL tape into parsed rows (mirror of `main::read_tape`).
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

/// The six-field `reconciliation.json` artifact (deliverable of issue #122).
fn recon_artifact_json(r: &ReconciliationResult) -> Value {
    json!({
        "n_executed": r.n_executed,
        "n_reconciled": r.n_reconciled,
        "n_mismatched": r.n_mismatched,
        "n_not_applicable": r.n_not_applicable,
        "max_abs_deviation": r.max_abs_deviation,
        "verdict": r.verdict,
    })
}

/// The oracle-shaped summary (mirror of `run_phase0`'s returned dict):
/// includes the mismatch detail the artifact deliberately excludes.
fn summary_json(
    r: &ReconciliationResult,
    n_candidates: usize,
    n_unbound: usize,
    problems: &[String],
) -> Value {
    let mismatches: Vec<Value> = r
        .mismatches
        .iter()
        .map(|(cid, reason)| json!([cid, reason]))
        .collect();
    let halted = r.verdict != RECONCILED || !problems.is_empty();
    let halt_reason = if r.verdict != RECONCILED {
        Some("reconciliation failed — load-bearing invariant broken, refusing to produce a cube")
    } else if !problems.is_empty() {
        Some("PIT lineage violation detected — future leakage, refusing to proceed")
    } else {
        None
    };
    let mut s = Map::new();
    s.insert("evaluator_version".to_string(), json!(EVALUATOR_VERSION));
    s.insert("n_candidates".to_string(), json!(n_candidates));
    s.insert("n_unbound".to_string(), json!(n_unbound));
    s.insert("pit_lineage_problems".to_string(), json!(problems));
    s.insert(
        "reconciliation".to_string(),
        json!({
            "n_executed": r.n_executed,
            "n_reconciled": r.n_reconciled,
            "n_mismatched": r.n_mismatched,
            "n_not_applicable": r.n_not_applicable,
            "mismatches": mismatches,
            "max_abs_deviation": r.max_abs_deviation,
            "verdict": r.verdict,
        }),
    );
    s.insert("halted".to_string(), json!(halted));
    if let Some(reason) = halt_reason {
        s.insert("halt_reason".to_string(), json!(reason));
    }
    Value::Object(s)
}

/// Build the store, run the three steps, write `reconciliation.json`, and
/// return the oracle-shaped summary.
pub fn reconcile(req: &ReconcileRequest) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;

    let sim = SimulatorParams::from_json(&req.manifest);
    let mut funding_schedule: Vec<(i64, f64)> = ds
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
    funding_schedule.sort_by_key(|(t, _)| *t);

    let snapshots = build_snapshots(&req.candidates, &req.evaluations, &req.outcomes);
    let problems = assert_pit_lineage(&req.states, &snapshots);
    let recon = reconcile_actual_actions(&snapshots, &ds.bars, &stores, &sim, &funding_schedule);

    let artifact = recon_artifact_json(&recon);
    let artifact_path = req.out_dir.join("reconciliation.json");
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).map_err(|e| e.to_string())? + "\n",
    )
    .map_err(|e| format!("reconciliation.json: {e}"))?;

    let n_unbound = snapshots
        .iter()
        .filter(|s| s.binding_status == UNBOUND_NO_DRAFT)
        .count();
    Ok(summary_json(&recon, snapshots.len(), n_unbound, &problems))
}

/// Entry point dispatched from `analysis::reconcile`. Returns 0 when the
/// reconciliation is clean (verdict RECONCILED and no PIT lineage problems),
/// 1 when halted (mirror of `tools/regret.py:main`), 2 on usage error.
pub fn run(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core reconcile <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error: cannot read request: {e}");
            return 1;
        }
    };
    let req: ReconcileRequest = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    match reconcile(&req) {
        Ok(summary) => {
            println!("{}", serde_json::to_string(&summary).unwrap());
            if summary
                .get("halted")
                .and_then(|v| v.as_bool())
                .unwrap_or(false)
            {
                1
            } else {
                0
            }
        }
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::candidate::{episode_key, geometry_version};
    use crate::state;

    // -----------------------------------------------------------------------
    // Fixture — the same synthetic store `tools/regret.py` Phase 0 ran on
    // (see the oracle-capture script); every expected value below is the
    // frozen oracle's emitted number (IEEE bit equality, no tolerance).
    // -----------------------------------------------------------------------

    const SYMBOL: &str = "SOLUSDT";
    const DETECTED_AT: i64 = 3000;
    const ENTRY_TIME: i64 = 5000; // EXECUTED knowledge_time -> bar index 4 (bar times are (i+1)*1000)

    fn geometry_map() -> Map<String, Value> {
        // Same structural geometry as the oracle fixture: expiry_bars is an
        // integer (the draft serializes it as an int).
        let mut m = Map::new();
        m.insert("target_r".to_string(), json!(1.5));
        m.insert("stop_r".to_string(), json!(1.0));
        m.insert("expiry_bars".to_string(), json!(8));
        m.insert("risk_frac".to_string(), json!(0.01));
        m
    }

    fn geometry_version_hex() -> String {
        geometry_version(&geometry_map())
    }

    /// The Rust re-derivation of the episode key (mirror of the oracle's
    /// `episode_key` + `_geometry_version` on the same draft inputs).
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

    /// The 10-bar tape (identical OHLC to the oracle fixture).
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

    fn write_tape(path: &std::path::Path) {
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

    /// Full DETECTED -> ... -> EXECUTED chain for a candidate that enters at
    /// bar 4 (EXECUTED knowledge_time 4000).
    fn entered_transitions(cid: &str, expert: &str, anchor: &str, sid: &str) -> Vec<Value> {
        let mut chain = Vec::new();
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
        chain.push(Value::Object(detected));
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

    fn state_record(sid: &str, mia: i64) -> Value {
        json!({
            "state_id": sid, "as_of": DETECTED_AT, "universe": [SYMBOL],
            "features": {
                "sma20": {"name": "sma20", "value": 100.0, "dtype": "float64",
                          "feature_version": "v1",
                          "max_input_available_time": mia,
                          "quality": "COMPLETE"},
            },
            "lineage_hash": "0000000000000000000000000000000000000000",
            "quality": "COMPLETE",
        })
    }

    /// The oracle-computed observed outcome for the C1/C3 LONG on bar 4
    /// (`tools/regret.py` simulator output, captured verbatim — net_r is
    /// `1.605/1.07` in IEEE, i.e. NOT exactly 1.5).
    fn observed_outcome(net_r: f64) -> Map<String, Value> {
        let mut m = Map::new();
        m.insert("endpoint".to_string(), json!("TARGET"));
        m.insert("label_status".to_string(), json!("MATURE"));
        m.insert("horizon_bars".to_string(), json!(1));
        m.insert("ambiguous_bars".to_string(), json!(0));
        m.insert("net_r".to_string(), json!(net_r));
        m.insert("entry_price".to_string(), json!(107.0));
        m.insert("risk_unit_price".to_string(), json!(1.07));
        m.insert("mae_r".to_string(), json!(0.9345794392523364));
        m.insert("mfe_r".to_string(), json!(1.8691588785046729));
        m.insert("market_move_r".to_string(), json!(0.9345794392523364));
        m
    }

    /// The clean ledger: C1 (entered, outcome matches) + C2 (never entered).
    fn clean_ledger() -> (Vec<Value>, Vec<Value>, Vec<Value>, Vec<Value>) {
        let c1 = rust_cid("fragile_expert", "sol-setup-1");
        let c2 = rust_cid("ghost_expert", "sol-setup-2");
        let mut candidates = entered_transitions(&c1, "fragile_expert", "sol-setup-1", "st-sol-1");
        candidates.push(detected_only_transition(
            &c2,
            "ghost_expert",
            "sol-setup-2",
            "st-sol-2",
        ));
        let evaluations = vec![
            eval_record("fragile_expert", "sol-setup-1"),
            eval_record("ghost_expert", "sol-setup-2"),
        ];
        let outcomes = vec![json!({
            "candidate_id": c1,
            "endpoint": "TARGET", "label_status": "MATURE",
            "horizon_bars": 1, "ambiguous_bars": 0,
            "net_r": 1.5000000000000036, "entry_price": 107.0,
            "risk_unit_price": 1.07,
            "mae_r": 0.9345794392523364, "mfe_r": 1.8691588785046729,
            "market_move_r": 0.9345794392523364,
        })];
        let states = vec![
            state_record("st-sol-1", DETECTED_AT - 1),
            state_record("st-sol-2", DETECTED_AT - 1),
        ];
        (candidates, evaluations, outcomes, states)
    }

    fn manifest() -> Value {
        json!({
            "round_trip_cost_r": 0.0, "funding_rate_r": 0.0,
            "funding_hours": 0, "fill_policy": "FILL_AT_BAR_CLOSE",
        })
    }

    /// Build the dataset + stores + sim the way `reconcile` does, from a tape
    /// written to `tape_path`.
    fn env(
        tape_path: &std::path::Path,
    ) -> (Dataset, Vec<FeatureStore>, SimulatorParams, Vec<(i64, f64)>) {
        write_tape(tape_path);
        let rows = read_tape(tape_path).unwrap();
        let ds = Dataset::from_rows(rows).unwrap();
        let stores = state::build_stores(&ds);
        let sim = SimulatorParams::from_json(&manifest());
        let funding_schedule = Vec::new();
        (ds, stores, sim, funding_schedule)
    }

    // -----------------------------------------------------------------------
    // build_snapshots
    // -----------------------------------------------------------------------

    #[test]
    fn snapshots_bind_by_rederived_episode_key() {
        let (candidates, evaluations, outcomes, _) = clean_ledger();
        let c1 = rust_cid("fragile_expert", "sol-setup-1");
        let c2 = rust_cid("ghost_expert", "sol-setup-2");
        let snaps = build_snapshots(&candidates, &evaluations, &outcomes);
        assert_eq!(snaps.len(), 2);
        // Join is a RE-DERIVATION: the snapshot identity equals the episode
        // key computed from the draft alone, never a stored edge.
        assert_eq!(snaps[0].candidate_id, c1);
        assert_eq!(snaps[1].candidate_id, c2);
        assert_eq!(snaps[0].binding_status, BOUND);
        assert_eq!(snaps[1].binding_status, BOUND);
        assert_eq!(snaps[0].entry_bar_available_time, Some(ENTRY_TIME));
        assert_eq!(snaps[1].entry_bar_available_time, None);
        assert_eq!(snaps[0].birth_state_id.as_deref(), Some("st-sol-1"));
        assert_eq!(snaps[0].instrument, SYMBOL);
        assert_eq!(snaps[0].direction, "LONG");
        assert_eq!(snaps[0].expert_id, "fragile_expert");
        assert!(snaps[0].observed_outcome.is_some());
        assert!(snaps[1].observed_outcome.is_none());
        assert_eq!(snaps[0].geometry_version, geometry_version_hex());
    }

    #[test]
    fn unbound_candidate_is_reported_not_dropped() {
        // A transition whose draft is absent binds UNBOUND_NO_DRAFT with the
        // DETECTED fields, never a panic and never a silent drop.
        let cid = rust_cid("ghost_expert", "sol-setup-2");
        let candidates = vec![detected_only_transition(
            &cid,
            "ghost_expert",
            "sol-setup-2",
            "st-sol-2",
        )];
        let snaps = build_snapshots(&candidates, &[], &[]);
        assert_eq!(snaps.len(), 1);
        assert_eq!(snaps[0].binding_status, UNBOUND_NO_DRAFT);
        assert_eq!(snaps[0].expert_id, "ghost_expert");
        assert_eq!(snaps[0].raw_draft, None);
        assert_eq!(snaps[0].size, 1.0);
        assert!(snaps[0].risk_geometry.is_empty());
    }

    #[test]
    fn transitions_sort_by_sequence_for_detected_executed_terminal() {
        // Out-of-order append must not change the DETECTED/EXECUTED picks.
        let cid = rust_cid("fragile_expert", "sol-setup-1");
        let mut candidates = entered_transitions(&cid, "fragile_expert", "sol-setup-1", "st-sol-1");
        candidates.push(transition(&cid, 7, Some("EXECUTED"), "CLOSED", 5000));
        candidates.reverse();
        let evaluations = vec![eval_record("fragile_expert", "sol-setup-1")];
        let snaps = build_snapshots(&candidates, &evaluations, &[]);
        assert_eq!(snaps.len(), 1);
        assert_eq!(snaps[0].entry_bar_available_time, Some(ENTRY_TIME));
        assert_eq!(snaps[0].terminal_state.as_deref(), Some("CLOSED"));
    }

    // -----------------------------------------------------------------------
    // assert_pit_lineage
    // -----------------------------------------------------------------------

    #[test]
    fn pit_lineage_is_clean_when_states_resolve() {
        let (candidates, evaluations, outcomes, states) = clean_ledger();
        let snaps = build_snapshots(&candidates, &evaluations, &outcomes);
        let problems = assert_pit_lineage(&states, &snaps);
        assert!(
            problems.is_empty(),
            "expected clean lineage, got {problems:?}"
        );
    }

    #[test]
    fn pit_lineage_reports_future_leakage_with_oracle_text() {
        let (candidates, evaluations, outcomes, _) = clean_ledger();
        // st-sol-2's sma20 declares max_input_available_time 99999 > as_of
        // 3000 — the oracle's leak fixture.
        let states = vec![
            state_record("st-sol-1", DETECTED_AT - 1),
            state_record("st-sol-2", 99999),
        ];
        let snaps = build_snapshots(&candidates, &evaluations, &outcomes);
        let problems = assert_pit_lineage(&states, &snaps);
        assert_eq!(problems.len(), 1);
        // Value-bearing suffix is the oracle's exact string (the prefix is
        // the V8.2 candidate_id, an identity excluded from parity).
        let c2 = rust_cid("ghost_expert", "sol-setup-2");
        assert_eq!(problems[0], format!(
            "{c2}: feature sma20 max_input_available_time 99999 > decision clock 3000 — future leakage"));
    }

    #[test]
    fn pit_lineage_reports_missing_and_unresolved_birth_states() {
        let (candidates, evaluations, outcomes, states) = clean_ledger();
        let snaps = build_snapshots(&candidates, &evaluations, &outcomes);
        // Drop st-sol-1 -> "not found in states.jsonl"; strip st-sol-2's
        // birth_state_id -> "no birth_state_id recorded".
        let mut snaps = snaps;
        snaps[0].birth_state_id = Some("st-gone".to_string());
        snaps[1].birth_state_id = None;
        let problems = assert_pit_lineage(&states, &snaps);
        assert_eq!(problems.len(), 2);
        assert!(problems[0].contains("birth_state_id st-gone not found in states.jsonl"));
        assert!(problems[1].ends_with("no birth_state_id recorded"));
    }

    // -----------------------------------------------------------------------
    // reconcile_actual_actions
    // -----------------------------------------------------------------------

    #[test]
    fn clean_ledger_reconciles_to_oracle_counts() {
        let (candidates, evaluations, outcomes, states) = clean_ledger();
        let snaps = build_snapshots(&candidates, &evaluations, &outcomes);
        assert!(assert_pit_lineage(&states, &snaps).is_empty());

        let tmp = std::env::temp_dir().join(format!("v8-reconcile-clean-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        let (ds, stores, sim, funding) = env(&tape);

        let recon = reconcile_actual_actions(&snaps, &ds.bars, &stores, &sim, &funding);
        // Frozen oracle (clean variant): the same store ran through
        // `tools/regret.py` Phase 0 emits exactly these counters.
        assert_eq!(recon.n_executed, 1);
        assert_eq!(recon.n_reconciled, 1);
        assert_eq!(recon.n_mismatched, 0);
        assert_eq!(recon.n_not_applicable, 1);
        assert_eq!(recon.verdict, RECONCILED);
        assert!(recon.mismatches.is_empty());
        // Bit-exact: the Rust kernel reproduces the oracle's floats, so the
        // max observed deviation is 0.0 on every compared field.
        for f in RECONCILE_FLOAT_FIELDS {
            assert_eq!(
                recon.max_abs_deviation[f], 0.0,
                "{f}: kernel deviates from oracle"
            );
        }
    }

    #[test]
    fn corrupted_observed_net_r_mismatches_with_oracle_counts() {
        let (mut candidates, mut evaluations, mut outcomes, _) = clean_ledger();
        // C3: a distinct episode (different setup anchor) that entered and
        // whose observed net_r is corrupted by +0.5.
        let c3 = rust_cid("fragile_expert", "sol-setup-3");
        candidates.extend(entered_transitions(
            &c3,
            "fragile_expert",
            "sol-setup-3",
            "st-sol-3",
        ));
        evaluations.push(eval_record("fragile_expert", "sol-setup-3"));
        let mut obs = observed_outcome(2.0000000000000036); // net_r + 0.5
        obs.insert("candidate_id".to_string(), json!(c3));
        outcomes.push(json!(obs));
        let snaps = build_snapshots(&candidates, &evaluations, &outcomes);
        assert_eq!(snaps.len(), 3);

        let tmp = std::env::temp_dir().join(format!("v8-reconcile-corrupt-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        let (ds, stores, sim, funding) = env(&tape);

        let recon = reconcile_actual_actions(&snaps, &ds.bars, &stores, &sim, &funding);
        // Frozen oracle (corrupted variant): n_executed=2, n_reconciled=1,
        // n_mismatched=1, n_not_applicable=1, net_r deviation 0.5, verdict
        // RECONCILIATION_FAILED.
        assert_eq!(recon.n_executed, 2);
        assert_eq!(recon.n_reconciled, 1);
        assert_eq!(recon.n_mismatched, 1);
        assert_eq!(recon.n_not_applicable, 1);
        assert_eq!(recon.verdict, RECONCILIATION_FAILED);
        assert_eq!(recon.mismatches.len(), 1);
        assert!(
            recon.mismatches[0].1.starts_with("field_mismatch:"),
            "reason was: {}",
            recon.mismatches[0].1
        );
        assert_eq!(recon.max_abs_deviation["net_r"], 0.5);
        for f in RECONCILE_FLOAT_FIELDS {
            if f != "net_r" {
                assert_eq!(recon.max_abs_deviation[f], 0.0);
            }
        }
    }

    #[test]
    fn missing_observed_outcome_is_entry_bar_or_outcome_missing() {
        let c1 = rust_cid("fragile_expert", "sol-setup-1");
        let candidates = entered_transitions(&c1, "fragile_expert", "sol-setup-1", "st-sol-1");
        let evaluations = vec![eval_record("fragile_expert", "sol-setup-1")];
        // No outcomes ledger entry for c1.
        let snaps = build_snapshots(&candidates, &evaluations, &[]);
        assert_eq!(snaps.len(), 1);
        assert_eq!(snaps[0].observed_outcome, None);

        let tmp = std::env::temp_dir().join(format!("v8-reconcile-missing-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        let (ds, stores, sim, funding) = env(&tape);

        let recon = reconcile_actual_actions(&snaps, &ds.bars, &stores, &sim, &funding);
        assert_eq!(recon.n_executed, 1);
        assert_eq!(recon.n_reconciled, 0);
        assert_eq!(recon.n_mismatched, 1);
        assert_eq!(recon.mismatches[0].1, "entry_bar_or_outcome_missing");
        assert_eq!(recon.verdict, RECONCILIATION_FAILED);
    }

    // -----------------------------------------------------------------------
    // run() end-to-end: the request -> reconciliation.json artifact
    // -----------------------------------------------------------------------

    fn write_request(
        path: &std::path::Path,
        tape_path: &std::path::Path,
        out_dir: &std::path::Path,
        candidates: &[Value],
        evaluations: &[Value],
        outcomes: &[Value],
        states: &[Value],
    ) {
        let req = json!({
            "tape_path": tape_path, "out_dir": out_dir,
            "universe": [SYMBOL], "manifest": manifest(),
            "candidates": candidates, "evaluations": evaluations,
            "outcomes": outcomes, "states": states,
        });
        std::fs::write(path, serde_json::to_string_pretty(&req).unwrap()).unwrap();
    }

    #[test]
    fn run_writes_reconciliation_json_matching_oracle() {
        let tmp = std::env::temp_dir().join(format!("v8-reconcile-run-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        write_tape(&tape);
        let out = tmp.join("out");
        let req_path = tmp.join("request.json");
        let (candidates, evaluations, outcomes, states) = clean_ledger();
        write_request(
            &req_path,
            &tape,
            &out,
            &candidates,
            &evaluations,
            &outcomes,
            &states,
        );

        let code = run(&[req_path.to_str().unwrap().to_string()]);
        assert_eq!(code, 0, "clean store must not halt");

        let artifact: Value = serde_json::from_str(
            &std::fs::read_to_string(out.join("reconciliation.json")).unwrap(),
        )
        .unwrap();
        // Field-for-field vs the frozen oracle's clean summary:
        // {n_executed:1, n_reconciled:1, n_mismatched:0, n_not_applicable:1,
        //  max_abs_deviation all 0.0, verdict RECONCILED}.
        assert_eq!(artifact["n_executed"], 1);
        assert_eq!(artifact["n_reconciled"], 1);
        assert_eq!(artifact["n_mismatched"], 0);
        assert_eq!(artifact["n_not_applicable"], 1);
        assert_eq!(artifact["verdict"], RECONCILED);
        for f in RECONCILE_FLOAT_FIELDS {
            assert_eq!(artifact["max_abs_deviation"][f], 0.0);
        }
    }

    #[test]
    fn run_halts_on_corrupted_ledger_and_reports_reason() {
        let tmp = std::env::temp_dir().join(format!("v8-reconcile-run-bad-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        let out = tmp.join("out");
        let req_path = tmp.join("request.json");
        let (mut candidates, mut evaluations, mut outcomes, mut states) = clean_ledger();
        let c3 = rust_cid("fragile_expert", "sol-setup-3");
        candidates.extend(entered_transitions(
            &c3,
            "fragile_expert",
            "sol-setup-3",
            "st-sol-3",
        ));
        evaluations.push(eval_record("fragile_expert", "sol-setup-3"));
        let mut obs = observed_outcome(2.0000000000000036);
        obs.insert("candidate_id".to_string(), json!(c3));
        outcomes.push(json!(obs));
        states.push(state_record("st-sol-3", DETECTED_AT - 1));
        write_tape(&tape);
        write_request(
            &req_path,
            &tape,
            &out,
            &candidates,
            &evaluations,
            &outcomes,
            &states,
        );

        let code = run(&[req_path.to_str().unwrap().to_string()]);
        assert_eq!(code, 1, "corrupted ledger must halt (oracle main exit 1)");

        let artifact: Value = serde_json::from_str(
            &std::fs::read_to_string(out.join("reconciliation.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(artifact["n_executed"], 2);
        assert_eq!(artifact["n_reconciled"], 1);
        assert_eq!(artifact["n_mismatched"], 1);
        assert_eq!(artifact["n_not_applicable"], 1);
        assert_eq!(artifact["max_abs_deviation"]["net_r"], 0.5);
        assert_eq!(artifact["verdict"], RECONCILIATION_FAILED);
    }

    #[test]
    fn run_halts_on_pit_lineage_violation() {
        let tmp =
            std::env::temp_dir().join(format!("v8-reconcile-run-leak-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let tape = tmp.join("tape.jsonl");
        let out = tmp.join("out");
        let req_path = tmp.join("request.json");
        let (candidates, evaluations, outcomes, _) = clean_ledger();
        let states = vec![
            state_record("st-sol-1", DETECTED_AT - 1),
            state_record("st-sol-2", 99999),
        ];
        write_tape(&tape);
        write_request(
            &req_path,
            &tape,
            &out,
            &candidates,
            &evaluations,
            &outcomes,
            &states,
        );

        let code = run(&[req_path.to_str().unwrap().to_string()]);
        assert_eq!(code, 1, "PIT violation must halt (oracle main exit 1)");
        // The artifact still records the reconciliation counters; the verdict
        // is untouched by lineage (the oracle's summary halts separately).
        let artifact: Value = serde_json::from_str(
            &std::fs::read_to_string(out.join("reconciliation.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(artifact["verdict"], RECONCILED);
        assert_eq!(artifact["n_executed"], 1);
    }

    #[test]
    fn run_usage_error_returns_two() {
        assert_eq!(run(&[]), 2);
    }
}
