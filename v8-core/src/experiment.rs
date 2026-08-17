//! Phase-4 frozen OOS experiment runner (`v8_slice_001`).
//!
//! This module is deliberately downstream of the S4 candidate collector.  S4
//! discovers immutable candidates; Phase-4 replays the actual action for every
//! candidate, admits at the entry clock, retains portfolio-rejected
//! counterfactuals, and only then computes the preregistered attribution and
//! family statistics.  A report without a valid authority receipt remains
//! `NO_ECONOMIC_CLAIM`.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use serde_json::{json, Map, Value};
use sha1::{Digest, Sha1};

use crate::backend::{self, ReplayCell};
use crate::candidate::{self, DEFAULT_CLUSTERS};
use crate::data::{Dataset, TapeRow};
use crate::hash;
use crate::runloop;
use crate::simulator::{Draft, Outcome, SimulatorParams};
use crate::state;
use crate::statistics::{detrended, reality_check, remaining};

const ID: &str = "v8_slice_001";
const INTERVAL: &str = "1h";
const SYMBOL: &str = "BTCUSDT";
const HOLDOUT_ANCHOR_NS: i64 = 1_782_864_000_000_000_000;
const ALPHA_FAMILY: f64 = 0.05;
const FAMILY_COUNT: u64 = 2;
const ALPHA_F: f64 = ALPHA_FAMILY / FAMILY_COUNT as f64;
const MIN_EPISODES: usize = 30;
const MIN_BARS: usize = 1_400;
const MIN_TAIL_ORDER_STATISTIC: usize = 100;
const BOOTSTRAP_FLOOR: usize = 2_000;
const EXECUTION_SHARE_FLOOR: f64 = 0.25;
const POPULATION_KS_MAX: f64 = 0.20;

#[derive(Debug, Clone, serde::Deserialize)]
struct DetectedCandidate {
    candidate_id: String,
    expert_id: String,
    instrument: String,
    direction: String,
    #[serde(default)]
    birth_time: i64,
    #[serde(default)]
    knowledge_time: i64,
    #[serde(default)]
    entry_bar: usize,
    #[serde(default)]
    state_quality: String,
    #[serde(default)]
    risk_geometry: Map<String, Value>,
    #[serde(default)]
    prior_low: Option<f64>,
    #[serde(default)]
    prior_high: Option<f64>,
    #[serde(default)]
    predicate_ir: Option<Value>,
    #[serde(default = "default_size")]
    size: f64,
    #[serde(default = "default_stop")]
    stop_r: f64,
}

fn default_size() -> f64 {
    1.0
}

fn default_stop() -> f64 {
    1.0
}

#[derive(Debug, Clone)]
struct Episode {
    candidate: DetectedCandidate,
    outcome: Outcome,
    admission: &'static str,
    rejection_reason: Option<String>,
}

#[derive(Debug, Clone)]
struct ActiveExposure {
    instrument: String,
    direction: String,
    cluster: String,
    close_time: i64,
    heat: f64,
}

pub fn run(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core experiment <frozen-manifest.json>");
        return 2;
    }
    match run_file(Path::new(&args[0])) {
        Ok(report) => {
            println!("{}", serde_json::to_string(&report).unwrap());
            0
        }
        Err(e) => {
            eprintln!("experiment: {e}");
            1
        }
    }
}

fn sha1_file(path: &Path) -> Result<String, String> {
    let bytes = fs::read(path).map_err(|e| format!("cannot read holdout tape: {e}"))?;
    Ok(format!("{:x}", Sha1::digest(bytes)))
}

fn canonical_row_value(row: &TapeRow) -> Value {
    json!({
        "source": row.source,
        "channel": row.channel,
        "instrument": row.instrument,
        "event_time": row.event_time,
        "available_time": row.available_time,
        "ingested_time": row.ingested_time,
        "venue_sequence": row.venue_sequence,
        "event_id": row.event_id,
        "payload": row.payload,
    })
}

fn canonical_tape_hash(rows: &[TapeRow]) -> String {
    // Python's frozen oracle uses sha1_hex: recursively sorted object keys
    // and compact JSON separators. This is intentionally separate from the
    // V8.2 IEEE identity hash used for internal artifacts.
    let value = Value::Array(rows.iter().map(canonical_row_value).collect());
    let mut encoded = String::new();
    append_python_canonical_json(&value, &mut encoded);
    format!("{:x}", Sha1::digest(encoded.as_bytes()))
}

fn append_python_canonical_json(value: &Value, out: &mut String) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(v) => out.push_str(if *v { "true" } else { "false" }),
        Value::Number(v) => out.push_str(&v.to_string()),
        Value::String(v) => {
            out.push_str(&serde_json::to_string(v).expect("string is serializable"));
        }
        Value::Array(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i != 0 {
                    out.push(',');
                }
                append_python_canonical_json(item, out);
            }
            out.push(']');
        }
        Value::Object(map) => {
            out.push('{');
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            for (i, key) in keys.into_iter().enumerate() {
                if i != 0 {
                    out.push(',');
                }
                out.push_str(&serde_json::to_string(key).expect("key is serializable"));
                out.push(':');
                append_python_canonical_json(&map[key], out);
            }
            out.push('}');
        }
    }
}

fn authority_present(v: &Value) -> bool {
    matches!(v, Value::String(s) if !s.trim().is_empty())
}

fn read_detected(path: &Path) -> Result<Vec<DetectedCandidate>, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("read candidates: {e}"))?;
    let mut out = Vec::new();
    let mut seen = HashSet::new();
    for (line_no, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let v: Value = serde_json::from_str(line)
            .map_err(|e| format!("candidates line {}: {e}", line_no + 1))?;
        if v.get("kind").and_then(Value::as_str) != Some("transition")
            || v.get("to_state").and_then(Value::as_str) != Some("DETECTED")
        {
            continue;
        }
        let c: DetectedCandidate = serde_json::from_value(v)
            .map_err(|e| format!("candidates line {}: {e}", line_no + 1))?;
        if seen.insert(c.candidate_id.clone()) {
            out.push(c);
        }
    }
    Ok(out)
}

fn family_for(expert_id: &str) -> Option<&'static str> {
    match expert_id {
        "trend_pullback" => Some("trend_continuation"),
        "failed_breakout" => Some("failed_breakout_reentry"),
        _ => None,
    }
}

fn default_predicate_ir(expert_id: &str) -> Option<Value> {
    match expert_id {
        // tools/predicate_ir.py RULES, frozen for the two Phase-4 pilots.
        "trend_pullback" => Some(json!({
            "type": "compare",
            "lhs": {"type": "live", "name": "ema_fast"},
            "op": "GT",
            "rhs": {"type": "live", "name": "ema_slow"},
            "orient": "AS_WRITTEN"
        })),
        "failed_breakout" => Some(json!({
            "type": "dispatch",
            "cases": [{
                "key": "prior_high_ref",
                "rule": {
                    "type": "compare",
                    "lhs": {"type": "live", "name": "close"},
                    "op": "LT",
                    "rhs": {"type": "ref", "key": "prior_high_ref"},
                    "orient": "AS_WRITTEN"
                }
            }],
            "default": {
                "type": "compare",
                "lhs": {"type": "live", "name": "close"},
                "op": "LT",
                "rhs": {"type": "live", "name": "prior_high"},
                "orient": "AS_WRITTEN"
            }
        })),
        _ => None,
    }
}

fn interval_ns(interval: &str) -> i64 {
    match interval {
        "1h" => state::HOUR_NS,
        "4h" => 4 * state::HOUR_NS,
        "1d" => state::DAY_NS,
        _ => state::HOUR_NS,
    }
}

fn funding_schedule(ds: &Dataset) -> Vec<(i64, f64)> {
    let mut out: Vec<(i64, f64)> = ds
        .rows
        .iter()
        .filter(|r| r.channel == "funding")
        .map(|r| {
            (
                r.event_time,
                r.payload
                    .get("funding_rate")
                    .and_then(Value::as_f64)
                    .unwrap_or(0.0),
            )
        })
        .collect();
    out.sort_by_key(|(t, _)| *t);
    out
}

fn bar_payload(store: &state::FeatureStore, i: usize) -> Map<String, Value> {
    let mut m = Map::new();
    m.insert("open".into(), json!(store.opens[i]));
    m.insert("high".into(), json!(store.highs[i]));
    m.insert("low".into(), json!(store.lows[i]));
    m.insert("close".into(), json!(store.closes[i]));
    m.insert("volume".into(), json!(store.volumes[i]));
    m.insert("closed".into(), json!(true));
    m
}

fn cluster_for(instrument: &str) -> String {
    DEFAULT_CLUSTERS
        .iter()
        .find(|(symbol, _)| *symbol == instrument)
        .map(|(_, cluster)| (*cluster).to_string())
        .unwrap_or_else(|| "other".to_string())
}

fn two_sample_ks(xs: &[f64], ys: &[f64]) -> f64 {
    if xs.is_empty() || ys.is_empty() {
        return 1.0;
    }
    let mut x = xs.to_vec();
    let mut y = ys.to_vec();
    x.sort_by(f64::total_cmp);
    y.sort_by(f64::total_cmp);
    let mut values = x.clone();
    values.extend_from_slice(&y);
    values.sort_by(f64::total_cmp);
    values.dedup_by(|a, b| a.to_bits() == b.to_bits());
    let mut i = 0usize;
    let mut j = 0usize;
    let mut d = 0.0f64;
    for v in values {
        while i < x.len() && x[i] <= v {
            i += 1;
        }
        while j < y.len() && y[j] <= v {
            j += 1;
        }
        d = d.max(((i as f64 / x.len() as f64) - (j as f64 / y.len() as f64)).abs());
    }
    d
}

fn resamples_for_alpha(alpha: f64) -> usize {
    BOOTSTRAP_FLOOR.max((MIN_TAIL_ORDER_STATISTIC as f64 / alpha).ceil() as usize)
}

fn bootstrap_lower_bound(
    series: &[f64],
    alpha: f64,
    seed: u64,
) -> Result<(f64, usize, usize), String> {
    if series.is_empty() {
        return Ok((0.0, 1, 0));
    }
    let block = reality_check::select_block_size(series, 0.10);
    let n = resamples_for_alpha(alpha);
    let mut means = reality_check::block_bootstrap_means(series, block, n as i64, seed)?;
    means.sort_by(f64::total_cmp);
    let idx = ((n as f64 * alpha) as usize).min(means.len() - 1);
    Ok((means[idx], block as usize, n))
}

fn family_search(manifest: &Value, family: &str) -> Result<(u64, u64), String> {
    // Frozen pilot registry (docs/EXPERTS_REGISTRY.yaml): both pilots have
    // one evaluated variant and a one-element declared search universe. A
    // manifest may repeat these values explicitly, but omission is resolved
    // from this versioned source rather than an accidental runtime default.
    let frozen = match family {
        "trend_continuation" | "failed_breakout_reentry" => (1, 1),
        _ => return Err(format!("unknown frozen family {family}")),
    };
    let Some(entry) = manifest.get("families").and_then(|v| v.get(family)) else {
        return Ok(frozen);
    };
    let variants = entry
        .get("variants_evaluated")
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("family {family} lacks variants_evaluated"))?;
    let search = entry
        .get("search_universe_size")
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("family {family} lacks search_universe_size"))?;
    if variants == 0 || search == 0 {
        return Err(format!(
            "family {family} multiplicity sizes must be positive"
        ));
    }
    if (variants, search) != frozen {
        return Err(format!(
            "family {family} multiplicity ({variants}, {search}) does not match frozen registry ({}, {})",
            frozen.0, frozen.1
        ));
    }
    Ok((variants, search.max(variants)))
}

fn write_json(path: &Path, value: &Value) -> Result<(), String> {
    let bytes = serde_json::to_vec_pretty(value).map_err(|e| e.to_string())?;
    let mut file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .map_err(|e| format!("create immutable artifact {}: {e}", path.display()))?;
    file.write_all(&bytes).map_err(|e| e.to_string())?;
    file.write_all(b"\n").map_err(|e| e.to_string())?;
    file.sync_all().map_err(|e| e.to_string())
}

fn write_or_verify(path: &Path, value: &Value) -> Result<String, String> {
    let fingerprint = hash::hash_value(value);
    if path.exists() {
        let existing: Value = serde_json::from_slice(
            &fs::read(path).map_err(|e| format!("read immutable artifact: {e}"))?,
        )
        .map_err(|e| format!("parse immutable artifact: {e}"))?;
        if hash::hash_value(&existing) != fingerprint {
            return Err(format!(
                "immutable artifact {} already exists with a different identity",
                path.display()
            ));
        }
        return Ok(fingerprint);
    }
    write_json(path, value)?;
    Ok(fingerprint)
}

fn make_outcome_cell<'a>(
    candidate: &'a DetectedCandidate,
    stores: &'a [state::FeatureStore],
) -> Result<Option<ReplayCell<'a>>, String> {
    let store = stores
        .iter()
        .find(|s| s.symbol == candidate.instrument)
        .ok_or_else(|| {
            format!(
                "candidate references unknown symbol {}",
                candidate.instrument
            )
        })?;
    let start = candidate.entry_bar;
    if start >= store.closes.len() {
        return Ok(None);
    }
    let mut risk_geometry = candidate.risk_geometry.clone();
    if let Some(value) = candidate.prior_low {
        risk_geometry
            .entry("prior_low_ref")
            .or_insert_with(|| json!(value));
    }
    if let Some(value) = candidate.prior_high {
        risk_geometry
            .entry("prior_high_ref")
            .or_insert_with(|| json!(value));
    }
    let draft = Draft {
        direction: candidate.direction.clone(),
        birth_time: candidate.birth_time,
        risk_geometry,
    };
    let thesis = candidate
        .predicate_ir
        .clone()
        .or_else(|| default_predicate_ir(&candidate.expert_id));
    Ok(Some(ReplayCell {
        symbol: &candidate.instrument,
        draft,
        start,
        end: store.closes.len(),
        thesis,
    }))
}

fn replay_candidates(
    candidates: &[DetectedCandidate],
    ds: &Dataset,
    stores: &[state::FeatureStore],
    sim: &SimulatorParams,
) -> Result<Vec<Outcome>, String> {
    let funding = funding_schedule(ds);
    let mut cells = Vec::new();
    let mut destinations = Vec::new();
    let mut outcomes = vec![Outcome::default(); candidates.len()];
    for (i, candidate) in candidates.iter().enumerate() {
        if let Some(invalidated_at) = invalidation_time(candidate, stores, sim)? {
            outcomes[i] = Outcome {
                endpoint: "INVALIDATED_BEFORE_TRIGGER".into(),
                label_status: "NOT_EXECUTED".into(),
                label_available_time: invalidated_at,
                ..Outcome::default()
            };
            continue;
        }
        if let Some(cell) = make_outcome_cell(candidate, stores)? {
            destinations.push(i);
            cells.push(cell);
        } else {
            outcomes[i] = Outcome {
                endpoint: "EXPIRY".into(),
                label_status: "NOT_EXECUTED".into(),
                ..Outcome::default()
            };
        }
    }
    if cells.is_empty() {
        return Ok(outcomes);
    }
    let mut replayed = vec![Outcome::default(); cells.len()];
    backend::evaluate_engine("cpu", 1, sim, &funding, stores, ds, &cells, &mut replayed)?;
    for (j, outcome) in replayed.into_iter().enumerate() {
        outcomes[destinations[j]] = outcome;
    }
    Ok(outcomes)
}

fn invalidation_time(
    candidate: &DetectedCandidate,
    stores: &[state::FeatureStore],
    sim: &SimulatorParams,
) -> Result<Option<i64>, String> {
    let store = stores
        .iter()
        .find(|s| s.symbol == candidate.instrument)
        .ok_or_else(|| {
            format!(
                "candidate references unknown symbol {}",
                candidate.instrument
            )
        })?;
    let start = candidate.entry_bar;
    if start >= store.closes.len() {
        return Ok(None);
    }
    let prior_low = candidate.prior_low;
    let prior_high = candidate.prior_high;
    let breached = |i: usize| {
        (candidate.direction == "LONG" && prior_low.is_some_and(|v| store.lows[i] < v))
            || (candidate.direction != "LONG" && prior_high.is_some_and(|v| store.highs[i] > v))
    };
    match sim.fill_policy {
        crate::simulator::FillPolicy::Limit => {
            let expiry = candidate
                .risk_geometry
                .get("expiry_bars")
                .and_then(Value::as_u64)
                .unwrap_or(0) as usize;
            let end = store.closes.len().min(start.saturating_add(expiry + 1));
            Ok((start..end)
                .find(|&i| breached(i))
                .and_then(|i| store.avail.get(i).copied()))
        }
        crate::simulator::FillPolicy::BarClose => {
            if candidate.risk_geometry.contains_key("trigger_ref") {
                for j in start..store.closes.len() {
                    if breached(j) {
                        return Ok(store.avail.get(j).copied());
                    }
                    if trigger_confirmed_for_admission(candidate, store.closes[j])? {
                        let entry = j + 1;
                        if entry >= store.closes.len() {
                            return Ok(None);
                        }
                        return Ok(if breached(entry) {
                            store.avail.get(entry).copied()
                        } else {
                            None
                        });
                    }
                }
                Ok(None)
            } else if breached(start) {
                Ok(store.avail.get(start).copied())
            } else {
                Ok(None)
            }
        }
    }
}

fn trigger_confirmed_for_admission(
    candidate: &DetectedCandidate,
    close: f64,
) -> Result<bool, String> {
    let reference = match candidate
        .risk_geometry
        .get("trigger_ref")
        .and_then(Value::as_f64)
    {
        Some(v) => v,
        None => return Ok(true),
    };
    let above = match candidate
        .risk_geometry
        .get("trigger_side")
        .and_then(Value::as_str)
    {
        None => candidate.direction != "SHORT",
        Some("CLOSE_ABOVE") => true,
        Some("CLOSE_BELOW") => false,
        Some(other) => return Err(format!("unsupported trigger_side {other:?}")),
    };
    Ok(if above {
        close > reference
    } else {
        close < reference
    })
}

fn resolved_entry_bar(
    candidate: &DetectedCandidate,
    outcome: &Outcome,
    store: &state::FeatureStore,
    sim: &SimulatorParams,
) -> Result<Option<usize>, String> {
    if outcome.label_status == "NOT_EXECUTED" {
        return Ok(None);
    }
    let start = candidate.entry_bar;
    if start >= store.closes.len() {
        return Ok(None);
    }
    let expiry = candidate
        .risk_geometry
        .get("expiry_bars")
        .and_then(Value::as_u64)
        .unwrap_or(0) as usize;
    match sim.fill_policy {
        crate::simulator::FillPolicy::Limit => {
            let limit = candidate
                .risk_geometry
                .get("limit_price")
                .and_then(Value::as_f64)
                .ok_or("FILL_AT_LIMIT requires limit_price")?;
            let end = store.closes.len().min(start.saturating_add(expiry + 1));
            for i in start..end {
                let hit = if candidate.direction == "LONG" {
                    store.lows[i] <= limit
                } else {
                    store.highs[i] >= limit
                };
                if hit {
                    return Ok(Some(i));
                }
            }
            Ok(None)
        }
        crate::simulator::FillPolicy::BarClose => {
            if candidate.risk_geometry.contains_key("trigger_ref") {
                let prior_low = candidate.prior_low.or_else(|| {
                    candidate
                        .risk_geometry
                        .get("prior_low_ref")
                        .and_then(Value::as_f64)
                });
                let prior_high = candidate.prior_high.or_else(|| {
                    candidate
                        .risk_geometry
                        .get("prior_high_ref")
                        .and_then(Value::as_f64)
                });
                for j in start..store.closes.len() {
                    let breached = (candidate.direction == "LONG"
                        && prior_low.is_some_and(|v| store.lows[j] < v))
                        || (candidate.direction != "LONG"
                            && prior_high.is_some_and(|v| store.highs[j] > v));
                    if breached {
                        return Ok(None);
                    }
                    if trigger_confirmed_for_admission(candidate, store.closes[j])? {
                        let entry = j + 1;
                        if entry >= store.closes.len() {
                            return Ok(None);
                        }
                        let entry_breached = (candidate.direction == "LONG"
                            && prior_low.is_some_and(|v| store.lows[entry] < v))
                            || (candidate.direction != "LONG"
                                && prior_high.is_some_and(|v| store.highs[entry] > v));
                        return Ok((!entry_breached).then_some(entry));
                    }
                }
                Ok(None)
            } else {
                let breached = (candidate.direction == "LONG"
                    && candidate.prior_low.is_some_and(|v| store.lows[start] < v))
                    || (candidate.direction != "LONG"
                        && candidate.prior_high.is_some_and(|v| store.highs[start] > v));
                Ok((!breached).then_some(start))
            }
        }
    }
}

fn admit_population(
    candidates: Vec<DetectedCandidate>,
    outcomes: Vec<Outcome>,
    stores: &[state::FeatureStore],
    manifest: &Value,
    sim: &SimulatorParams,
) -> Result<Vec<Episode>, String> {
    let max_heat = manifest
        .get("max_heat")
        .and_then(Value::as_f64)
        .unwrap_or(3.0);
    let max_cluster_heat = manifest
        .get("max_cluster_heat")
        .and_then(Value::as_f64)
        .unwrap_or(2.0);
    let max_range = manifest
        .get("max_bar_range_frac")
        .and_then(Value::as_f64)
        .unwrap_or(0.05);
    let funding_window = manifest
        .get("funding_window_bars")
        .and_then(Value::as_i64)
        .unwrap_or(1);
    let mut order: Vec<usize> = (0..candidates.len()).collect();
    order.sort_by(|a, b| {
        let ta = stores
            .iter()
            .find(|s| s.symbol == candidates[*a].instrument)
            .and_then(|s| {
                resolved_entry_bar(&candidates[*a], &outcomes[*a], s, sim)
                    .ok()
                    .flatten()
            })
            .and_then(|i| {
                stores
                    .iter()
                    .find(|s| s.symbol == candidates[*a].instrument)
                    .and_then(|s| s.avail.get(i))
            })
            .copied()
            .unwrap_or(candidates[*a].knowledge_time);
        let tb = stores
            .iter()
            .find(|s| s.symbol == candidates[*b].instrument)
            .and_then(|s| {
                resolved_entry_bar(&candidates[*b], &outcomes[*b], s, sim)
                    .ok()
                    .flatten()
            })
            .and_then(|i| {
                stores
                    .iter()
                    .find(|s| s.symbol == candidates[*b].instrument)
                    .and_then(|s| s.avail.get(i))
            })
            .copied()
            .unwrap_or(candidates[*b].knowledge_time);
        (ta, &candidates[*a].candidate_id).cmp(&(tb, &candidates[*b].candidate_id))
    });
    let mut active: Vec<ActiveExposure> = Vec::new();
    let mut heat: HashMap<String, f64> = HashMap::new();
    let mut episodes = Vec::with_capacity(candidates.len());
    for i in order {
        let c = candidates[i].clone();
        let outcome = outcomes[i].clone();
        let store = stores
            .iter()
            .find(|s| s.symbol == c.instrument)
            .ok_or_else(|| format!("candidate references unknown symbol {}", c.instrument))?;
        let resolved = resolved_entry_bar(&c, &outcome, store, sim)?;
        let entry_idx = resolved
            .unwrap_or(c.entry_bar)
            .min(store.closes.len().saturating_sub(1));
        let entry_time = store
            .avail
            .get(entry_idx)
            .copied()
            .unwrap_or(c.knowledge_time);
        let mut still_active = Vec::with_capacity(active.len());
        for old in active.drain(..) {
            if old.close_time <= entry_time {
                if let Some(v) = heat.get_mut(&old.cluster) {
                    *v -= old.heat;
                }
            } else {
                still_active.push(old);
            }
        }
        active = still_active;

        let mut admission = "NOT_EXECUTED";
        let mut reason = None;
        if outcome.label_status != "NOT_EXECUTED" && resolved.is_some() {
            let mask = candidate::tradability_mask_veto(
                &bar_payload(store, entry_idx),
                &c.state_quality,
                entry_time,
                max_range,
                funding_window,
                sim.funding_hours,
                interval_ns(INTERVAL),
            );
            if mask.0 {
                admission = "TRADABILITY_REJECTED";
                reason = Some(mask.1.unwrap_or_else(|| "TRADABILITY_MASK_VETO".into()));
            } else if active
                .iter()
                .any(|old| old.instrument == c.instrument && old.direction == c.direction)
            {
                admission = "PORTFOLIO_REJECTED";
                reason = Some("EXISTING_EXPOSURE_CONFLICT".into());
            } else {
                let cluster = cluster_for(&c.instrument);
                let candidate_heat = c.size * c.stop_r;
                let cluster_total = heat.get(&cluster).copied().unwrap_or(0.0);
                let total_heat: f64 = heat.values().sum();
                if total_heat + candidate_heat > max_heat
                    || cluster_total + candidate_heat > max_cluster_heat
                {
                    admission = "PORTFOLIO_REJECTED";
                    reason = Some("PORTFOLIO_HEAT_EXCEEDED".into());
                } else {
                    admission = "EXECUTED";
                    let close_time = outcome.label_available_time.max(entry_time);
                    if close_time > entry_time {
                        *heat.entry(cluster.clone()).or_insert(0.0) += candidate_heat;
                        active.push(ActiveExposure {
                            instrument: c.instrument.clone(),
                            direction: c.direction.clone(),
                            cluster,
                            close_time,
                            heat: candidate_heat,
                        });
                    }
                }
            }
        } else if outcome.label_status != "NOT_EXECUTED" {
            admission = "NOT_EXECUTED";
            reason = Some("ENTRY_NOT_RESOLVED".into());
        }
        episodes.push(Episode {
            candidate: c,
            outcome,
            admission,
            rejection_reason: reason,
        });
    }
    Ok(episodes)
}

fn score_population(
    episodes: &[Episode],
    ds: &Dataset,
    manifest: &Value,
    authority: &Value,
) -> Result<Value, String> {
    let executed: Vec<&Episode> = episodes
        .iter()
        .filter(|e| e.admission == "EXECUTED")
        .collect();
    let portfolio_rejected: Vec<&Episode> = episodes
        .iter()
        .filter(|e| e.admission == "PORTFOLIO_REJECTED")
        .collect();
    let executed_net: Vec<f64> = executed.iter().map(|e| e.outcome.net_r).collect();
    let rejected_net: Vec<f64> = portfolio_rejected.iter().map(|e| e.outcome.net_r).collect();
    let mut rejection_distribution: BTreeMap<String, usize> = BTreeMap::new();
    for episode in episodes {
        if let Some(reason) = &episode.rejection_reason {
            *rejection_distribution.entry(reason.clone()).or_default() += 1;
        }
    }
    let denom = executed.len() + portfolio_rejected.len();
    let execution_share = if denom == 0 {
        None
    } else {
        Some(executed.len() as f64 / denom as f64)
    };
    let divergence_ks = if denom == 0 {
        None
    } else if rejected_net.is_empty() {
        Some(0.0)
    } else {
        Some(two_sample_ks(&executed_net, &rejected_net))
    };
    let d027_status = if !authority_present(authority) {
        "NO_ECONOMIC_CLAIM"
    } else if execution_share.is_some_and(|x| x < EXECUTION_SHARE_FLOOR) {
        "ATTRIBUTION_UNSAFE_LOW_COVERAGE"
    } else if divergence_ks.is_some_and(|x| x > POPULATION_KS_MAX) {
        "ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE"
    } else {
        "CERTIFIED_AVAILABLE"
    };

    let bars = ds.rows.iter().filter(|r| r.channel == "kline").count();
    let population = json!({
        "total": episodes.len(),
        "executed": executed.len(),
        "portfolio_rejected": portfolio_rejected.len(),
        "other_not_executed": episodes.len().saturating_sub(executed.len() + portfolio_rejected.len()),
        "rejection_distribution": rejection_distribution,
    });
    // D-027 is an attribution-validity gate. Once the measured execution
    // population is unsafe, family-level effect sizes are diagnostic only and
    // must not be presented as scored claims (Python oracle behavior).
    if d027_status.starts_with("ATTRIBUTION_UNSAFE_") {
        return Ok(json!({
            "d027": {
                "n_executed": executed.len(),
                "n_portfolio_rejected": portfolio_rejected.len(),
                "execution_share": execution_share,
                "divergence_ks": divergence_ks,
                "status": d027_status,
            },
            "sufficiency": {
                "bars": bars,
                "min_bars": MIN_BARS,
                "episodes_ok": false,
                "min_episodes": MIN_EPISODES,
            },
            "families": {
                "trend_continuation": {"scored": false},
                "failed_breakout_reentry": {"scored": false},
            },
            "population": population,
        }));
    }

    let closes: Vec<f64> = ds
        .rows
        .iter()
        .filter(|r| r.channel == "kline")
        .filter_map(|r| r.payload.get("close").and_then(Value::as_f64))
        .collect();
    let drift = detrended::mean_log_drift_per_bar(&closes)?;
    let mut family_out = Map::new();
    for family in ["trend_continuation", "failed_breakout_reentry"] {
        let family_executed: Vec<&Episode> = executed
            .iter()
            .copied()
            .filter(|e| family_for(&e.candidate.expert_id) == Some(family))
            .collect();
        let exposures: Vec<detrended::EpisodeExposure> = family_executed
            .iter()
            .map(|e| detrended::EpisodeExposure {
                net_r: e.outcome.net_r,
                direction: if e.candidate.direction == "SHORT" {
                    "SHORT"
                } else {
                    "LONG"
                },
                entry_price: e.outcome.entry_price,
                risk_unit_price: e.outcome.risk_unit_price,
                horizon_bars: e.outcome.horizon_bars,
            })
            .collect();
        let detrended_series = detrended::detrend_net_r(&exposures, drift)?;
        let (lower, block, n_resamples) = bootstrap_lower_bound(&detrended_series, ALPHA_F, 7)?;
        let (variants, search_size) = family_search(manifest, family)?;
        let effective = remaining::effective_search_size(variants, search_size)?;
        let expected_false = remaining::expected_false_positives(effective, ALPHA_F)?;
        family_out.insert(
            family.to_string(),
            json!({
                "n": family_executed.len(),
                "mu_hat_raw": if exposures.is_empty() { 0.0 } else { state::fsum(&exposures.iter().map(|e| e.net_r).collect::<Vec<_>>()) / exposures.len() as f64 },
                "mu_hat": if detrended_series.is_empty() { 0.0 } else { state::fsum(&detrended_series) / detrended_series.len() as f64 },
                "position_bias_component": if exposures.is_empty() || detrended_series.is_empty() { 0.0 } else {
                    state::fsum(&exposures.iter().map(|e| e.net_r).collect::<Vec<_>>()) / exposures.len() as f64
                        - state::fsum(&detrended_series) / detrended_series.len() as f64
                },
                "ci_lower": lower,
                "ci_lower_2p5": lower,
                "block_size": block,
                "bootstrap_resamples": n_resamples,
                "h0_rejected": lower > 0.0 && family_executed.len() >= MIN_EPISODES,
                "variants_evaluated": variants,
                "search_universe_size": search_size,
                "multiplicity_undercounted": search_size > variants,
                "multiplicity_source": "docs/EXPERTS_REGISTRY.yaml:frozen-pilot-v1",
                "effective_search_size": effective,
                "expected_false_positives": expected_false,
            }),
        );
    }
    let bars = closes.len();
    let expected_false_positives: f64 = family_out
        .values()
        .filter_map(|v| v.get("expected_false_positives").and_then(Value::as_f64))
        .sum();
    let episodes_ok = bars >= MIN_BARS
        && ["trend_continuation", "failed_breakout_reentry"]
            .iter()
            .all(|f| {
                family_out[*f].get("n").and_then(Value::as_u64).unwrap_or(0) >= MIN_EPISODES as u64
            });
    Ok(json!({
        "d027": {
            "n_executed": executed.len(),
            "n_portfolio_rejected": portfolio_rejected.len(),
            "execution_share": execution_share,
            "divergence_ks": divergence_ks,
            "status": d027_status,
        },
        "sufficiency": {
            "bars": bars,
            "min_bars": MIN_BARS,
            "episodes_ok": episodes_ok,
            "min_episodes": MIN_EPISODES,
        },
        "detrending": {
            "method": "aronson-appendix-a-same-exposure-benchmark",
            "mean_log_drift_per_bar": drift,
            "estimated_on": "frozen-oos-window",
        },
        "families": family_out,
        "expected_false_positives": {
            "method": "program-level sum of family effective_search_size x alpha_f",
            "total": expected_false_positives,
        },
        "population": population,
    }))
}

fn population_artifact(episodes: &[Episode]) -> Value {
    let rows: Vec<Value> = episodes
        .iter()
        .map(|episode| {
            let c = &episode.candidate;
            let o = &episode.outcome;
            json!({
                "candidate_id": c.candidate_id,
                "expert_id": c.expert_id,
                "family": family_for(&c.expert_id),
                "instrument": c.instrument,
                "direction": c.direction,
                "birth_time": c.birth_time,
                "knowledge_time": c.knowledge_time,
                "entry_bar": c.entry_bar,
                "state_quality": c.state_quality,
                "admission": episode.admission,
                "rejection_reason": episode.rejection_reason,
                "outcome": {
                    "endpoint": o.endpoint,
                    "net_r": o.net_r,
                    "label_status": o.label_status,
                    "horizon_bars": o.horizon_bars,
                    "label_available_time": o.label_available_time,
                    "mae_r": o.mae_r,
                    "mfe_r": o.mfe_r,
                    "ambiguous_bars": o.ambiguous_bars,
                    "entry_price": o.entry_price,
                    "risk_unit_price": o.risk_unit_price,
                    "market_move_r": o.market_move_r,
                    "cost_r": o.cost_r,
                    "funding_r": o.funding_r,
                },
            })
        })
        .collect();
    json!({
        "schema_version": "v1",
        "experiment_id": ID,
        "population": rows,
    })
}

pub fn run_file(path: &Path) -> Result<Value, String> {
    let manifest: Value =
        serde_json::from_slice(&fs::read(path).map_err(|e| format!("read frozen manifest: {e}"))?)
            .map_err(|e| format!("invalid frozen manifest: {e}"))?;
    let obj = manifest
        .as_object()
        .ok_or("frozen manifest must be an object")?;
    let tape = PathBuf::from(
        obj.get("tape_path")
            .and_then(Value::as_str)
            .ok_or("frozen manifest lacks tape_path")?,
    );
    if obj.get("experiment_id").and_then(Value::as_str) != Some(ID) {
        return Err("manifest is not v8_slice_001".into());
    }
    if obj.get("interval").and_then(Value::as_str) != Some(INTERVAL) {
        return Err("v8_slice_001 requires interval=1h".into());
    }
    if obj
        .get("universe")
        .and_then(Value::as_array)
        .map(|u| u.iter().filter_map(Value::as_str).collect::<Vec<_>>())
        != Some(vec![SYMBOL])
    {
        return Err("v8_slice_001 requires universe=[BTCUSDT]".into());
    }
    let start = obj
        .get("start_ns")
        .and_then(Value::as_i64)
        .ok_or("manifest lacks start_ns")?;
    if start < HOLDOUT_ANCHOR_NS {
        return Err("frozen OOS starts before the 2026-07-01 anchor".into());
    }
    if !tape.exists() {
        let mut report = json!({
            "schema_version": "v1",
            "experiment_id": ID,
            "verdict": "NO_ECONOMIC_CLAIM",
            "holdout_unavailable": true,
            "authority_receipt": obj.get("authority_receipt").cloned().unwrap_or(Value::Null),
        });
        let out_dir = obj
            .get("out_dir")
            .and_then(Value::as_str)
            .map(PathBuf::from)
            .unwrap_or_else(|| {
                path.parent()
                    .unwrap_or(Path::new("."))
                    .join("experiment-v8_slice_001")
            });
        fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;
        let authority = report["authority_receipt"].clone();
        let receipt = json!({
            "schema_version": "v1",
            "experiment_id": ID,
            "manifest_hash": hash::hash_value(&manifest),
            "raw_tape_sha1": "",
            "canonical_data_hash": "",
            "report_core_hash": hash::hash_value(&report),
            "authority_receipt_hash": if authority_present(&authority) { hash::hash_value(&authority) } else { String::new() },
            "generator": crate::evidence::generator_tag(),
            "verdict": report["verdict"].clone(),
        });
        let receipt_hash = write_or_verify(&out_dir.join("experiment-receipt.json"), &receipt)?;
        report["receipt_hash"] = Value::String(receipt_hash);
        write_or_verify(&out_dir.join("experiment-report.json"), &report)?;
        return Ok(report);
    }

    let raw_hash = sha1_file(&tape)?;
    let declared_raw_hash = obj
        .get("tape_sha1")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("frozen manifest tape_sha1 is required when the holdout exists")?;
    if declared_raw_hash != raw_hash {
        return Err(format!(
            "holdout tape sha1 mismatch: {raw_hash} != {declared_raw_hash}"
        ));
    }
    let rows = runloop::read_tape(&tape)?;
    let ds = Dataset::from_rows(rows.clone()).map_err(|e| e.to_string())?;
    let canonical_hash = canonical_tape_hash(&rows);
    let declared_data_hash = obj
        .get("data_hash")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("frozen manifest data_hash is required when the holdout exists")?;
    if declared_data_hash != canonical_hash {
        return Err(format!(
            "holdout canonical data hash mismatch: {canonical_hash} != {declared_data_hash}"
        ));
    }
    let klines: Vec<&TapeRow> = rows.iter().filter(|r| r.channel == "kline").collect();
    if klines.is_empty() {
        return Err("holdout tape has no kline rows".into());
    }
    let instruments: HashSet<&str> = klines.iter().map(|r| r.instrument.as_str()).collect();
    if instruments.len() != 1 || !instruments.contains(SYMBOL) {
        return Err(format!(
            "v8_slice_001 holdout must contain only {SYMBOL} kline rows; found {instruments:?}"
        ));
    }
    let mut clocks = HashSet::with_capacity(klines.len());
    if klines.iter().any(|row| !clocks.insert(row.available_time)) {
        return Err("holdout has duplicate kline available_time decision clocks".into());
    }
    let min_event = klines.iter().map(|r| r.event_time).min().unwrap();
    let max_event = klines.iter().map(|r| r.event_time).max().unwrap();
    if min_event < start {
        return Err(format!(
            "holdout first kline {min_event} precedes start_ns {start}"
        ));
    }
    if let Some(end) = obj.get("end_ns").and_then(Value::as_i64) {
        if max_event > end {
            return Err(format!(
                "holdout last kline {max_event} exceeds end_ns {end}"
            ));
        }
    }
    if klines.len() < MIN_BARS {
        return Err(format!(
            "holdout has {} kline bars; minimum is {MIN_BARS}",
            klines.len()
        ));
    }

    let authority = obj.get("authority_receipt").cloned().unwrap_or(Value::Null);
    let universe = vec![SYMBOL.to_string()];
    let out_dir = obj
        .get("out_dir")
        .and_then(Value::as_str)
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            path.parent()
                .unwrap_or(Path::new("."))
                .join("experiment-v8_slice_001")
        });
    fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;
    let collect = runloop::collect_for_experiment(&tape, &universe, &out_dir, &manifest)?;
    let candidates_path = PathBuf::from(
        collect
            .get("candidates")
            .and_then(Value::as_str)
            .ok_or("candidate collector did not return candidates path")?,
    );
    let candidates = read_detected(&candidates_path)?;
    let stores = state::build_stores(&ds);
    let sim = SimulatorParams::from_json(&manifest);
    let outcomes = replay_candidates(&candidates, &ds, &stores, &sim)?;
    let episodes = admit_population(candidates, outcomes, &stores, &manifest, &sim)?;
    let scored = score_population(&episodes, &ds, &manifest, &authority)?;
    let population = population_artifact(&episodes);
    let population_path = out_dir.join("experiment-population.json");
    let population_hash = write_or_verify(&population_path, &population)?;
    let d027_status = scored["d027"]["status"]
        .as_str()
        .unwrap_or("NO_ECONOMIC_CLAIM");
    let verdict = if d027_status != "CERTIFIED_AVAILABLE" {
        d027_status.to_string()
    } else if !scored["sufficiency"]["episodes_ok"]
        .as_bool()
        .unwrap_or(false)
        || !authority_present(&authority)
    {
        "NO_ECONOMIC_CLAIM".to_string()
    } else {
        "CERTIFIED_AVAILABLE".to_string()
    };
    let mut report = json!({
        "schema_version": "v1",
        "experiment_id": ID,
        "verdict": verdict,
        "authority_receipt": authority,
        "holdout": {
            "path": tape,
            "raw_sha1": raw_hash,
            "canonical_data_hash": canonical_hash,
            "actual_first_event_ns": min_event,
            "actual_last_event_ns": max_event,
            "bar_count": klines.len(),
            "anchor_ns": HOLDOUT_ANCHOR_NS,
        },
        "collector": collect,
        "population_artifact": {
            "path": population_path,
            "hash": population_hash,
            "rows": episodes.len(),
        },
        "scoring": scored,
    });
    let core_hash = hash::hash_value(&report);
    let receipt = json!({
        "schema_version": "v1",
        "experiment_id": ID,
        "manifest_hash": hash::hash_value(&manifest),
        "raw_tape_sha1": raw_hash,
        "canonical_data_hash": canonical_hash,
        "population_hash": population_hash,
        "report_core_hash": core_hash,
        "authority_receipt_hash": if authority_present(&authority) { hash::hash_value(&authority) } else { String::new() },
        "generator": crate::evidence::generator_tag(),
        "verdict": report["verdict"].clone(),
    });
    let receipt_hash = write_or_verify(&out_dir.join("experiment-receipt.json"), &receipt)?;
    report["receipt_hash"] = Value::String(receipt_hash);
    write_or_verify(&out_dir.join("experiment-report.json"), &report)?;
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::TapeRow;

    fn fixture_rows(n: usize) -> Vec<TapeRow> {
        (0..n)
            .map(|i| {
                let event = 1_700_000_000_000_000_000i64 + i as i64 * state::HOUR_NS;
                let value = 100.0 + i as f64;
                let v = json!({
                    "source": "binance-um",
                    "channel": "kline",
                    "instrument": "BTCUSDT",
                    "event_time": event,
                    "available_time": event + 1_000_000_000,
                    "ingested_time": event + 1_000_000_000,
                    "venue_sequence": i as i64 + 1,
                    "event_id": format!("BTCUSDT:{i}"),
                    "payload": {
                        "open": value,
                        "high": value + 0.1,
                        "low": value - 0.1,
                        "close": value,
                        "volume": 1.0,
                        "closed": true
                    }
                });
                TapeRow::from_parts(&v, vec![]).unwrap()
            })
            .collect()
    }

    fn candidate(id: &str, entry_bar: usize) -> DetectedCandidate {
        DetectedCandidate {
            candidate_id: id.into(),
            expert_id: "trend_pullback".into(),
            instrument: "BTCUSDT".into(),
            direction: "LONG".into(),
            birth_time: 1,
            knowledge_time: 1,
            entry_bar,
            state_quality: "COMPLETE".into(),
            risk_geometry: {
                let mut m = Map::new();
                m.insert("atr_ref".into(), json!(1.0));
                m.insert("target_r".into(), json!(1.0));
                m.insert("stop_r".into(), json!(1.0));
                m.insert("expiry_bars".into(), json!(2));
                m
            },
            prior_low: Some(99.0),
            prior_high: Some(101.0),
            predicate_ir: None,
            size: 1.0,
            stop_r: 1.0,
        }
    }

    fn mature_outcome(close_time: i64) -> Outcome {
        Outcome {
            endpoint: "TARGET".into(),
            net_r: 0.5,
            label_status: "MATURE".into(),
            horizon_bars: 1,
            label_available_time: close_time,
            entry_price: 101.0,
            risk_unit_price: 1.0,
            ..Outcome::default()
        }
    }

    #[test]
    fn ks_empty_population_is_maximal() {
        assert_eq!(two_sample_ks(&[], &[1.0]), 1.0);
    }

    #[test]
    fn ks_matches_known_ecdf() {
        assert_eq!(two_sample_ks(&[0.0, 1.0], &[0.0, 0.0]), 0.5);
    }

    #[test]
    fn tape_hash_matches_python_sha1_hex_fixture() {
        // The expected digest is generated by
        // json.dumps([row], sort_keys=True, separators=(',', ':')).
        assert_eq!(
            canonical_tape_hash(&fixture_rows(1)),
            "f3d2ded7d9ed09b54bce7d94ce58c2bf2552b58b"
        );
    }

    #[test]
    fn receipt_is_immutable_and_idempotent() {
        let dir = std::env::temp_dir().join(format!("v8-phase4-receipt-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let p = dir.join("receipt.json");
        let v = json!({"x": 1, "y": "fixed"});
        let first = write_or_verify(&p, &v).unwrap();
        assert_eq!(first, write_or_verify(&p, &v).unwrap());
        assert!(write_or_verify(&p, &json!({"x": 2})).is_err());
        fs::remove_file(p).ok();
        fs::remove_dir(dir).ok();
    }

    #[test]
    fn lifecycle_admission_releases_closed_exposure() {
        let rows = fixture_rows(8);
        let ds = Dataset::from_rows(rows).unwrap();
        let stores = state::build_stores(&ds);
        let close_first = stores[0].avail[3];
        let close_second = stores[0].avail[5];
        let candidates = vec![candidate("a", 1), candidate("b", 2), candidate("c", 4)];
        let outcomes = vec![
            mature_outcome(close_first),
            mature_outcome(close_second),
            mature_outcome(stores[0].avail[5]),
        ];
        let episodes = admit_population(
            candidates,
            outcomes,
            &stores,
            &json!({"max_heat": 3.0, "max_cluster_heat": 2.0, "funding_window_bars": 0}),
            &SimulatorParams::from_json(&json!({})),
        )
        .unwrap();
        assert_eq!(episodes[0].admission, "EXECUTED");
        assert_eq!(episodes[1].admission, "PORTFOLIO_REJECTED");
        assert_eq!(
            episodes[1].rejection_reason.as_deref(),
            Some("EXISTING_EXPOSURE_CONFLICT")
        );
        assert_eq!(episodes[2].admission, "EXECUTED");
    }

    #[test]
    fn authority_blocks_economic_claim() {
        let ds = Dataset::from_rows(fixture_rows(8)).unwrap();
        let stores = state::build_stores(&ds);
        let episodes = vec![Episode {
            candidate: candidate("authority-block", 1),
            outcome: mature_outcome(stores[0].avail[3]),
            admission: "EXECUTED",
            rejection_reason: None,
        }];
        let manifest = json!({
            "families": {
                "trend_continuation": {"variants_evaluated": 1, "search_universe_size": 1},
                "failed_breakout_reentry": {"variants_evaluated": 1, "search_universe_size": 1}
            }
        });
        let scored = score_population(&episodes, &ds, &manifest, &Value::Null).unwrap();
        assert_eq!(scored["d027"]["status"], "NO_ECONOMIC_CLAIM");
    }

    #[test]
    fn authority_receipt_type_is_fail_closed() {
        assert!(!authority_present(&Value::Null));
        assert!(!authority_present(&json!(1)));
        assert!(!authority_present(&json!({"receipt": "x"})));
        assert!(authority_present(&json!("operator-receipt-v1")));
    }

    #[test]
    fn invalidation_is_resolved_before_counterfactual_replay() {
        let ds = Dataset::from_rows(fixture_rows(8)).unwrap();
        let stores = state::build_stores(&ds);
        let mut c = candidate("invalidated", 1);
        c.prior_low = Some(101.5);
        let at = invalidation_time(&c, &stores, &SimulatorParams::from_json(&json!({}))).unwrap();
        assert_eq!(at, Some(stores[0].avail[1]));
    }

    #[test]
    fn pilot_predicate_is_bound_to_replay_cell() {
        let ds = Dataset::from_rows(fixture_rows(8)).unwrap();
        let stores = state::build_stores(&ds);
        let c = candidate("predicate", 1);
        let cell = make_outcome_cell(&c, &stores).unwrap().unwrap();
        assert_eq!(
            cell.thesis
                .as_ref()
                .and_then(|v| v.get("type"))
                .and_then(Value::as_str),
            Some("compare")
        );
    }

    #[test]
    fn low_execution_share_blocks_attribution() {
        let ds = Dataset::from_rows(fixture_rows(8)).unwrap();
        let stores = state::build_stores(&ds);
        let mut episodes = vec![Episode {
            candidate: candidate("executed", 1),
            outcome: mature_outcome(stores[0].avail[3]),
            admission: "EXECUTED",
            rejection_reason: None,
        }];
        for i in 0..4 {
            episodes.push(Episode {
                candidate: candidate(&format!("rejected-{i}"), 1),
                outcome: mature_outcome(stores[0].avail[3]),
                admission: "PORTFOLIO_REJECTED",
                rejection_reason: Some("EXISTING_EXPOSURE_CONFLICT".into()),
            });
        }
        let manifest = json!({
            "families": {
                "trend_continuation": {"variants_evaluated": 1, "search_universe_size": 1},
                "failed_breakout_reentry": {"variants_evaluated": 1, "search_universe_size": 1}
            }
        });
        let scored = score_population(&episodes, &ds, &manifest, &json!("authority-ok")).unwrap();
        assert_eq!(scored["d027"]["status"], "ATTRIBUTION_UNSAFE_LOW_COVERAGE");
        assert_eq!(scored["families"]["trend_continuation"]["scored"], false);
    }

    #[test]
    fn missing_holdout_writes_receipt_and_report() {
        let root = std::env::temp_dir().join(format!("v8-phase4-missing-{}", std::process::id()));
        fs::create_dir_all(&root).unwrap();
        let manifest_path = root.join("manifest.json");
        let out_dir = root.join("out");
        let manifest = json!({
            "experiment_id": ID,
            "interval": INTERVAL,
            "universe": [SYMBOL],
            "start_ns": HOLDOUT_ANCHOR_NS,
            "tape_path": root.join("missing.jsonl"),
            "out_dir": out_dir,
        });
        fs::write(&manifest_path, serde_json::to_vec(&manifest).unwrap()).unwrap();
        let report = run_file(&manifest_path).unwrap();
        assert_eq!(report["verdict"], "NO_ECONOMIC_CLAIM");
        assert!(out_dir.join("experiment-receipt.json").exists());
        assert!(out_dir.join("experiment-report.json").exists());
        let second = run_file(&manifest_path).unwrap();
        assert_eq!(report["receipt_hash"], second["receipt_hash"]);
        fs::remove_dir_all(root).ok();
    }
}
