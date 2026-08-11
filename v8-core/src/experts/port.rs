//! ExpertPlane: the 28 registered `evaluate()` ports (EXPERT_PROTOCOL;
//! COMPUTE_CORE_SPEC §4). Each mirrors the Python Expert's setup predicate,
//! risk_geometry construction, and D-026 anchor, producing a `Draft` the
//! candidate machinery admits. Values are the parity target; identities are
//! V8.2-encoded (D-079).

use std::collections::HashMap;

use crate::simulator::Draft;
use crate::state::{Feature, HistBar};

/// One per-bar evaluation, mirroring `ExpertEvaluation`.
#[derive(Debug, Clone)]
pub struct ExpertEval {
    pub applicability: String, // APPLICABLE | NOT_APPLICABLE
    pub decision: String,      // CANDIDATE | NO_SETUP | NO_HABITAT
    pub draft: Option<Draft>,
    /// D-026 setup anchor (event id) — part of the candidate identity.
    pub setup_anchor_event_id: Option<String>,
    /// The Python setup_fingerprint string (value parity target).
    pub setup_fingerprint: Option<String>,
}

/// The per-bar feature view the experts read (the state's feature dict).
pub struct FeatMap<'a> {
    pub features: &'a HashMap<String, Feature>,
    pub history: Vec<HistBar>,
    pub as_of: i64,
}

impl<'a> FeatMap<'a> {
    /// The numeric value of a bare feature name (e.g. "close", "atr").
    /// The map is keyed by the bare name, matching state_features' emission.
    pub fn value(&self, name: &str) -> Option<f64> {
        self.features.get(name).and_then(|f| f.value.as_f64())
    }
}

/// D-026 anchor: event_id of the first closed bar of the current consecutive
/// run in which `pred` holds (newest false bar + 1, bounded to the window's
/// oldest; newest-bar fallback).
pub fn find_setup_anchor(hist: &[HistBar], pred: &dyn Fn(usize, &HistBar) -> bool) -> String {
    if hist.is_empty() {
        panic!("setup anchor requires non-empty history");
    }
    let mut newest_false = -1i64;
    for i in (0..hist.len()).rev() {
        if !pred(i, &hist[i]) {
            newest_false = i as i64;
            break;
        }
    }
    let mut start = newest_false + 1;
    if start == hist.len() as i64 {
        start = hist.len() as i64 - 1;
    }
    hist[start as usize].event_id.clone()
}

/// Python-style `f"{v:.6f}"` — the setup_fingerprint's fixed-6 formatting.
#[allow(dead_code)]
fn f6(v: f64) -> String {
    // Python's `:.6f` rounds half-even; Rust `{:.6}` also rounds half-even on
    // the correctly-rounded decimal expansion, so the digits agree.
    format!("{v:.6}")
}

fn geom(entries: Vec<(&str, serde_json::Value)>) -> serde_json::Map<String, serde_json::Value> {
    let mut m = serde_json::Map::new();
    for (k, v) in entries {
        m.insert(k.to_string(), v);
    }
    m
}

fn no_habitat(_expert_id: &str, _version: &str, _as_of: i64) -> ExpertEval {
    ExpertEval { applicability: "NOT_APPLICABLE".into(), decision: "NO_HABITAT".into(),
                 draft: None, setup_anchor_event_id: None, setup_fingerprint: None }
}
fn no_setup(_expert_id: &str, _version: &str, _as_of: i64) -> ExpertEval {
    ExpertEval { applicability: "NOT_APPLICABLE".into(), decision: "NO_SETUP".into(),
                 draft: None, setup_anchor_event_id: None, setup_fingerprint: None }
}
fn candidate(_expert_id: &str, _version: &str, _as_of: i64, draft: Draft,
              anchor: String, fingerprint: String) -> ExpertEval {
    ExpertEval { applicability: "APPLICABLE".into(), decision: "CANDIDATE".into(),
                 draft: Some(draft), setup_anchor_event_id: Some(anchor),
                 setup_fingerprint: Some(fingerprint) }
}

// ---------------------------------------------------------------------------
// trend_pullback (pilot): LONG when fast > slow and close < slow, anchored on
// the consecutive pullback run.
// ---------------------------------------------------------------------------
pub fn trend_pullback(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = "SOLUSDT";
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let fast = match fm.value("ema_fast") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let slow = match fm.value("ema_slow") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    if !(fast > slow && close < slow) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let pred = |_i: usize, b: &HistBar| b.ema_fast > b.ema_slow && b.close < b.ema_slow;
    let anchor = find_setup_anchor(&fm.history, &pred);
    let draft = Draft {
        direction: "LONG".into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(1.0)),
            ("stop_r", serde_json::json!(1.0)),
            ("expiry_bars", serde_json::json!(8)),
            ("atr_ref", serde_json::json!(atr)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, slow);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}

// ---------------------------------------------------------------------------
// failed_breakout (pilot): SHORT after a close-breakout above the prior high
// and a close back below it; the level is frozen at detection.
// ---------------------------------------------------------------------------
pub fn failed_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = "SOLUSDT";
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // _last_breakout: newest bar j whose close exceeded the max high before it.
    let mut breakout: Option<(usize, f64)> = None;
    for j in (1..fm.history.len()).rev() {
        let prior = fm.history[..j].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
        if fm.history[j].close > prior {
            breakout = Some((j, prior));
            break;
        }
    }
    let (breakout_idx, ref_prior_high) = match breakout {
        Some(x) => x,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    if !(close < ref_prior_high) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let level = ref_prior_high;
    let pred = |_i: usize, b: &HistBar| _i > breakout_idx && b.close < level;
    let anchor = find_setup_anchor(&fm.history, &pred);
    let draft = Draft {
        direction: "SHORT".into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(1.0)),
            ("stop_r", serde_json::json!(1.0)),
            ("expiry_bars", serde_json::json!(8)),
            ("atr_ref", serde_json::json!(atr)),
            ("prior_high_ref", serde_json::json!(ref_prior_high)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_prior_high);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}

// ---------------------------------------------------------------------------
// liquidity_sweep_reclaim (pilot): LONG on a sweep+reclaim of the windowed
// prior low, SHORT on the prior high; one frozen reference for gate+anchor.
// ---------------------------------------------------------------------------
pub fn liquidity_sweep_reclaim(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = "SOLUSDT";
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let prior_low = |i: usize| -> f64 {
        fm.history[..i].iter().map(|b| b.low).fold(f64::INFINITY, f64::min)
    };
    let prior_high = |i: usize| -> f64 {
        fm.history[..i].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max)
    };
    let newest = &fm.history[fm.history.len() - 1];
    let (direction, ref_val, ref_key) = if newest.low < prior_low(fm.history.len() - 1)
        && close > prior_low(fm.history.len() - 1) {
        ("LONG", prior_low(fm.history.len() - 1), "prior_low_ref")
    } else if newest.high > prior_high(fm.history.len() - 1)
        && close < prior_high(fm.history.len() - 1) {
        ("SHORT", prior_high(fm.history.len() - 1), "prior_high_ref")
    } else {
        return no_setup(expert_id, version, fm.as_of);
    };
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = if direction == "LONG" {
        Box::new(move |i, b| i > 0 && b.low < prior_low(i) && b.close > prior_low(i))
    } else {
        Box::new(move |i, b| i > 0 && b.high > prior_high(i) && b.close < prior_high(i))
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);
    let entries = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(1.0)),
        ("stop_r", serde_json::json!(1.0)),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        (ref_key, serde_json::json!(ref_val)),
    ];
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(entries),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_val);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}

/// The registered evaluate() dispatch. Experts not yet ported return
/// NO_HABITAT (never a wrong draft — a missing port must not fabricate a
/// candidate; the S4 gate fails loudly until the port is complete).
pub fn evaluate(expert_id: &str, fm: &FeatMap) -> ExpertEval {
    match expert_id {
        "trend_pullback" => trend_pullback(fm, expert_id, "v1"),
        "failed_breakout" => failed_breakout(fm, expert_id, "v1"),
        "liquidity_sweep_reclaim" => liquidity_sweep_reclaim(fm, expert_id, "v1"),
        "volume_confirmed_breakout" => volume_confirmed_breakout(fm, expert_id, "v1"),
        _ => no_habitat(expert_id, "v1", fm.as_of),
    }
}

/// The expert registry (mirrors v8.experts.__all__, the 28 admitted families).
#[allow(dead_code)] // S4 loop dispatch surface; used once the loop is wired
pub const REGISTRY: [&str; 28] = [
    "bollinger_breakout", "bollinger_reversion", "breakout_retest",
    "candlestick_reversal", "divergence_12_setups", "donchian_breakout",
    "failed_breakout", "failed_breakout_2b", "fib_projection_reversal",
    "fib_retracement_continuation", "fib_rsi_bb_confluence",
    "floor_trader_pivot", "funding_crowding_reversal", "gap_exhaustion",
    "ichimoku_cloud", "liquidity_sweep_reclaim", "macd_stoch_trend",
    "market_profile_value_area", "obv_adl_regime", "open_interest_divergence",
    "pandf_breakout", "pattern_measuring_objective", "range_breakout_1to1",
    "rsi_stoch_reversion", "trend_pullback", "trend_pullback_depth",
    "volume_climax_reversal", "volume_confirmed_breakout",
];

// ---------------------------------------------------------------------------
// volume_confirmed_breakout: close beyond the 20-bar window extreme with a
// volume gate (variants d/c/b/a in priority order); the frozen prior extreme
// is the reference for gate + anchor.
// ---------------------------------------------------------------------------
pub fn volume_confirmed_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = "SOLUSDT";
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let volume = match fm.value("volume") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let sma = match fm.value("vol_smooth_ma") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let long_level = match fm.value("window_high_20") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let short_level = match fm.value("window_low_20") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    if !(close > long_level || close < short_level) {
        return no_setup(expert_id, version, fm.as_of);
    }
    // _evaluate_variants: first variant whose volume gate fires, in declared
    // priority order d, c, b, a.
    let mut variant: Option<&str> = None;
    if sma > 0.0 && volume >= 2.0 * sma {
        if let Some(z) = fm.value("vol_zscore") {
            if z < 2.0 {
                variant = Some("d");
            }
        }
    }
    if variant.is_none() && sma > 0.0 && volume >= 1.2 * sma {
        variant = Some("c");
    }
    if variant.is_none() {
        if let Some(prox) = fm.value("vol_min_proximity") {
            if prox < 0.4 && sma > 0.0 && volume > sma {
                variant = Some("b");
            }
        }
    }
    if variant.is_none() && sma > 0.0 && volume > sma {
        variant = Some("a");
    }
    let variant = match variant {
        Some(v) => v,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let (direction, level, ref_key) = if close > long_level {
        ("LONG", long_level, "prior_low_ref")
    } else {
        ("SHORT", short_level, "prior_high_ref")
    };
    let prior_high = |i: usize| -> f64 {
        let lo = i.saturating_sub(20);
        fm.history[lo..i].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max)
    };
    let prior_low = |i: usize| -> f64 {
        let lo = i.saturating_sub(20);
        fm.history[lo..i].iter().map(|b| b.low).fold(f64::INFINITY, f64::min)
    };
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = if direction == "LONG" {
        Box::new(move |i, b| i > 0 && b.close > prior_high(i))
    } else {
        Box::new(move |i, b| i > 0 && b.close < prior_low(i))
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(1.0)),
            ("stop_r", serde_json::json!(1.0)),
            ("expiry_bars", serde_json::json!(8)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!(variant)),
            (ref_key, serde_json::json!(level)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}:{}", close, level, variant);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
