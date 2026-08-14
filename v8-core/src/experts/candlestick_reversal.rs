//! candlestick_reversal: evaluate() port — mirror src/v8/experts/candlestick_reversal.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4). One
//! bar-shape reversal pattern per variant (8 declared, D-044); direction is
//! fixed by the pattern. The parity harness instantiates the Python expert
//! with no variant override, so the default 'hammer' is the evaluated variant;
//! every predicate and stop/trigger rule is still ported for completeness.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["candle_shape", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

// Declared, LOCKED constants (book Ch14.2 p558/566/570; D-036 pattern:
// "declared, never fitted").
const BODY_RATIO_MAX: f64 = 1.0 / 3.0; // real body <= 1/3 of the range
const SHADOW_MIN_MULT: f64 = 2.0;      // long shadow >= 2x the body

/// The configured variant (D-044 default: 'hammer').
const VARIANT: &str = "hammer";

fn body(o: f64, c: f64) -> f64 {
    (c - o).abs()
}

fn upper_shadow(o: f64, h: f64, c: f64) -> f64 {
    h - o.max(c)
}

fn lower_shadow(o: f64, l: f64, c: f64) -> f64 {
    o.min(c) - l
}

fn body_ratio(o: f64, h: f64, l: f64, c: f64) -> f64 {
    let rng = h - l;
    if rng > 0.0 {
        body(o, c) / rng
    } else {
        0.0
    }
}

// --- per-bar pattern predicates (D-026 anchor scan) ----------------------

fn hammer(hist: &[HistBar], i: usize, bar: &HistBar) -> bool {
    if i < 1 {
        return false;
    }
    let (o, h, l, c) = (bar.open, bar.high, bar.low, bar.close);
    let prev = &hist[i - 1];
    let (po, pc) = (prev.open, prev.close);
    let b = body(o, c);
    if b <= 0.0 || !(c > o) {
        return false;
    }
    if body_ratio(o, h, l, c) > BODY_RATIO_MAX {
        return false;
    }
    if lower_shadow(o, l, c) < SHADOW_MIN_MULT * b {
        return false;
    }
    if upper_shadow(o, h, c) > b {
        return false;
    }
    pc < po // after a down bar (decline context)
}

fn shooting_star(hist: &[HistBar], i: usize, bar: &HistBar) -> bool {
    if i < 1 {
        return false;
    }
    let (o, h, l, c) = (bar.open, bar.high, bar.low, bar.close);
    let prev = &hist[i - 1];
    let (po, pc) = (prev.open, prev.close);
    let b = body(o, c);
    if b <= 0.0 || !(c < o) {
        return false;
    }
    if body_ratio(o, h, l, c) > BODY_RATIO_MAX {
        return false;
    }
    if upper_shadow(o, h, c) < SHADOW_MIN_MULT * b {
        return false;
    }
    if lower_shadow(o, l, c) > b {
        return false;
    }
    pc > po // after an up bar (rally context)
}

fn bullish_engulfing(hist: &[HistBar], i: usize, bar: &HistBar) -> bool {
    if i < 1 {
        return false;
    }
    let (o, c) = (bar.open, bar.close);
    let prev = &hist[i - 1];
    let (po, pc) = (prev.open, prev.close);
    pc < po && c > o && o <= pc && c >= po
}

fn bearish_engulfing(hist: &[HistBar], i: usize, bar: &HistBar) -> bool {
    if i < 1 {
        return false;
    }
    let (o, c) = (bar.open, bar.close);
    let prev = &hist[i - 1];
    let (po, pc) = (prev.open, prev.close);
    pc > po && c < o && o >= pc && c <= po
}

/// Shared harami predicate; the variant decides the directional tail.
fn harami(hist: &[HistBar], i: usize, bar: &HistBar, bullish: bool) -> bool {
    if i < 1 {
        return false;
    }
    let (o, c) = (bar.open, bar.close);
    let prev = &hist[i - 1];
    let (po, ph, pl, pc) = (prev.open, prev.high, prev.low, prev.close);
    let b = body(o, c);
    let rng_prev = ph - pl;
    if b <= 0.0 || rng_prev <= 0.0 {
        return false;
    }
    // Second body no larger than 1/4-1/3 of the first bar's range
    // (Ch14.2 p570) and fully nested inside the first body.
    if b > BODY_RATIO_MAX * rng_prev {
        return false;
    }
    let (lo_prev, hi_prev) = (po.min(pc), po.max(pc));
    if !(lo_prev < o && c < hi_prev) {
        return false;
    }
    if bullish {
        return pc < po && c > o;
    }
    pc > po && c < o
}

fn three_soldiers(hist: &[HistBar], i: usize) -> bool {
    if i < 3 {
        return false;
    }
    for j in (i - 2)..=(i) {
        let (o, h, c) = (hist[j].open, hist[j].high, hist[j].close);
        if !(c > o) {
            return false;
        }
        let b = body(o, c);
        if b <= 0.0 || upper_shadow(o, h, c) > b {
            return false;
        }
    }
    let (c2, c1, c0) = (hist[i - 2].close, hist[i - 1].close, hist[i].close);
    if !(c2 < c1 && c1 < c0) {
        return false;
    }
    // Trigger: the third candle must close above the SECOND candle's high
    // (Ch14.2 p556).
    if !(c0 > hist[i - 1].high) {
        return false;
    }
    let (po, pc) = (hist[i - 3].open, hist[i - 3].close);
    pc < po // after a decline
}

fn three_crows(hist: &[HistBar], i: usize) -> bool {
    if i < 3 {
        return false;
    }
    for j in (i - 2)..=(i) {
        let (o, l, c) = (hist[j].open, hist[j].low, hist[j].close);
        if !(c < o) {
            return false;
        }
        let b = body(o, c);
        if b <= 0.0 || lower_shadow(o, l, c) > b {
            return false;
        }
    }
    let (c2, c1, c0) = (hist[i - 2].close, hist[i - 1].close, hist[i].close);
    if !(c2 > c1 && c1 > c0) {
        return false;
    }
    if !(c0 < hist[i - 1].low) {
        return false;
    }
    let (po, pc) = (hist[i - 3].open, hist[i - 3].close);
    pc > po // after a rally
}

/// The configured variant's per-bar predicate (anchor scan). The caller always
/// passes `bar == &hist[i]`, so the history indices used below are in-window.
fn pred(hist: &[HistBar], variant: &str, i: usize, bar: &HistBar) -> bool {
    match variant {
        "hammer" => hammer(hist, i, bar),
        "shooting_star" => shooting_star(hist, i, bar),
        "bullish_engulfing" => bullish_engulfing(hist, i, bar),
        "bearish_engulfing" => bearish_engulfing(hist, i, bar),
        "bullish_harami" => harami(hist, i, bar, true),
        "bearish_harami" => harami(hist, i, bar, false),
        "three_white_soldiers" => three_soldiers(hist, i),
        "three_black_crows" => three_crows(hist, i),
        _ => false,
    }
}

/// (stop_price, trigger_price) for the pattern completing on bar i (Ch14.2
/// p556 close-confirmation trigger; the stop is the book's pattern extreme).
fn stop_trigger(hist: &[HistBar], variant: &str, i: usize) -> (f64, f64) {
    match variant {
        "hammer" => (hist[i].low, hist[i].high),
        "shooting_star" => (hist[i].high, hist[i - 1].low),
        "bullish_engulfing" => (hist[i].low, hist[i].high),
        "bearish_engulfing" => (hist[i].high, hist[i].low),
        "bullish_harami" => (hist[i - 1].low, hist[i - 1].high),
        "bearish_harami" => (hist[i - 1].high, hist[i - 1].low),
        "three_white_soldiers" => (hist[i - 2].low, hist[i - 1].high),
        "three_black_crows" => (hist[i - 2].high, hist[i - 1].low),
        _ => (0.0, 0.0),
    }
}

fn direction_of(variant: &str) -> &'static str {
    match variant {
        "hammer" | "bullish_engulfing" | "bullish_harami" | "three_white_soldiers" => "LONG",
        _ => "SHORT",
    }
}

pub fn candlestick_reversal(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let variant = VARIANT;
    // _need: {sym}.close, {sym}.atr, {sym}.history, {sym}.real_body,
    //        {sym}.body_range_ratio, {sym}.upper_shadow, {sym}.lower_shadow,
    //        {sym}.close_position
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    for k in ["real_body", "body_range_ratio", "upper_shadow", "lower_shadow",
              "close_position"] {
        if fm.value(k).is_none() {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    // `not isinstance(hist_value, (tuple, list)) or not hist_value or atr is None`
    // — the Rust history carrier is always a Vec; empty window -> NO_HABITAT.
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let n = fm.history.len();
    if !pred(&fm.history, variant, n - 1, &fm.history[n - 1]) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let (stop_price, trigger_price) = stop_trigger(&fm.history, variant, n - 1);
    let direction = direction_of(variant);
    let stop_r = if direction == "LONG" {
        (close - stop_price) / atr
    } else {
        (stop_price - close) / atr
    };
    if stop_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let anchor_pred = |i: usize, b: &HistBar| pred(&fm.history, variant, i, b);
    let anchor = find_setup_anchor(&fm.history, &anchor_pred);
    let trigger_side = if direction == "LONG" { "CLOSE_ABOVE" } else { "CLOSE_BELOW" };
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(TARGET_R)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant)),
        ("stop_ref", serde_json::json!(stop_price)),
        ("trigger_ref", serde_json::json!(trigger_price)),
        ("trigger_side", serde_json::json!(trigger_side)),
    ]);
    if direction == "LONG" {
        geometry.insert("prior_low_ref".to_string(), serde_json::json!(stop_price));
    } else {
        geometry.insert("prior_high_ref".to_string(), serde_json::json!(stop_price));
    }
    let fingerprint = format!("{sym}:{variant}:{close:.6}:{stop_price:.6}:{trigger_price:.6}");
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
