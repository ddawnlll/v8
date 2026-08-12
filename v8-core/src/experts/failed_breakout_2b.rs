//! failed_breakout_2b: evaluate() port — mirror src/v8/experts/failed_breakout_2b.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Variant b — 2B non-failure swing (Sperandeo, Ch7.3 p228): LONG on a
//! close-based reclaim of the significant swing low (swing_low_10, 0.0 = no
//! significant swing) after a failed breakdown. Setup anchor (D-026):
//! `find_setup_anchor` on the consecutive run of reclaim bars (the run-start
//! semantics resolve to the completion bar itself). Risk geometry: the family's
//! 1R:1R:8bar fallback with atr_ref (D-028), the frozen swing low bound as
//! `prior_low_ref` (D-042). The subclass variants c..g are separate
//! registrations; this module is the variant-b class (D-044), so only `b` is
//! reachable from the dispatch table — the full variant dispatch is mirrored
//! anyway so the family's guards stay in one faithful copy.

use crate::experts::base::*;
use crate::state::HistBar;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history", "candle_shape"];

/// Variant id of this class (FailedBreakout2BExpert.variant_id = 'b').
const VARIANT: &str = "b";
/// Hikkake reclaim window (book verbatim, Ch7.4 p230: "within 3 bars").
const HIKKAKE_WINDOW_BARS: usize = 3;
/// Ichimoku Kijun-style cloud-proxy lookback (book: Kijun = midrange(26)).
const CLOUD_N: usize = 26;
/// Minimum history length per variant (D-034/O-020 bound): the false move +
/// reference bar + reclaim must all fit inside the 32-bar history window.
const MIN_HISTORY_B: usize = 2;
const MIN_HISTORY_C: usize = 4;
const MIN_HISTORY_D: usize = 4;
const MIN_HISTORY_E: usize = 2;
const MIN_HISTORY_F: usize = CLOUD_N + 2;
const MIN_HISTORY_G: usize = 22;

// --- per-history-bar helpers ------------------------------------------------
//
// Python history bars are tuples [event_id, open, high, low, close, ema_fast,
// ema_slow]; HistBar { event_id, open, high, low, close, ema_fast, ema_slow }
// mirrors them (v8-core/src/state.rs:1319).

/// Bar i is an inside bar of bar i-1 (marketstate G-06 formula).
fn inside_at(hist: &[HistBar], i: usize) -> bool {
    hist[i].high <= hist[i - 1].high && hist[i].low >= hist[i - 1].low
}

/// Kijun-style cloud-proxy top at bar i: midrange of the CLOUD_N bars before
/// it (G-44 proxy; None when the window is not computable).
fn cloud_top(hist: &[HistBar], i: usize) -> Option<f64> {
    if i < CLOUD_N {
        return None;
    }
    let win = &hist[i - CLOUD_N..i];
    if win.is_empty() {
        return None;
    }
    let hi = win.iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
    let lo = win.iter().map(|b| b.low).fold(f64::INFINITY, f64::min);
    Some((hi + lo) / 2.0)
}

/// Cross-check the newest bar's inside/outside status against the state
/// candle_shape features (feature and local computation must agree; a drift
/// fails the setup conservatively rather than emitting an anchor the features
/// cannot reproduce).
fn candle_features_agree(fm: &FeatMap, hist: &[HistBar]) -> bool {
    if hist.len() < 2 {
        return false;
    }
    let (Some(in_feat), Some(out_feat)) = (fm.value("inside_bar"), fm.value("outside_bar")) else {
        return false;
    };
    let n = hist.len();
    let in_loc = if inside_at(hist, n - 1) { 1.0 } else { 0.0 };
    let out_loc = if hist[n - 1].high >= hist[n - 2].high && hist[n - 1].low <= hist[n - 2].low {
        1.0
    } else {
        0.0
    };
    (in_loc == in_feat) && (out_loc == out_feat)
}

// --- per-variant detection predicates ---------------------------------------

/// 2B non-failure swing: LONG reclaim of the significant swing low.
fn detect_b(fm: &FeatMap, hist: &[HistBar], close: f64) -> Option<(String, String, f64)> {
    // `sw_low is None or sw_low.value is None or float(sw_low.value) <= 0`.
    let ref_ = match fm.value("swing_low_10") {
        Some(v) if v > 0.0 => v,
        _ => return None,
    };
    if hist.len() < 2 {
        return None;
    }
    let n = hist.len();
    if !(hist[n - 2].close < ref_ && close > ref_) {
        return None;
    }
    let pred = |i: usize, bar: &HistBar| i >= 1 && hist[i - 1].close < ref_ && bar.close > ref_;
    let anchor = find_setup_anchor(hist, &pred);
    Some(("LONG".to_string(), anchor, ref_))
}

/// Shared Hikkake sequence (Ch7.4 p230). bullish=true -> variant c, false ->
/// variant d. Scans newest -> oldest for the most recent inside bar whose
/// range was falsely broken and then reclaimed at the newest bar within
/// HIKKAKE_WINDOW_BARS of the failed move.
fn hikkake(fm: &FeatMap, hist: &[HistBar], close: f64, bullish: bool) -> Option<(String, String, f64)> {
    if !candle_features_agree(fm, hist) {
        return None;
    }
    let n = hist.len();
    if n < 4 {
        return None;
    }
    // `range(n - 3, 0, -1)`: inside-bar index j, newest first.
    for j in (1..=(n - 3)).rev() {
        if !inside_at(hist, j) {
            continue;
        }
        let inside_high = hist[j].high;
        let inside_low = hist[j].low;
        if inside_high <= inside_low {
            continue;
        }
        let fb = j + 1; // the false-break bar
        if fb >= n - 1 {
            continue; // no reclaim bar yet
        }
        let (broke, reclaim) = if bullish {
            (hist[fb].close < inside_low, close > inside_high)
        } else {
            (hist[fb].close > inside_high, close < inside_low)
        };
        if !broke || !reclaim {
            continue;
        }
        if (n - 1) - fb > HIKKAKE_WINDOW_BARS {
            continue; // reclaim too late
        }
        let ref_ = if bullish { inside_low } else { inside_high };
        // Python's pred lambda takes (i, bar) but only uses i (the completion
        // helper reads hist[i]); the unused bar param is mirrored as `_bar`.
        let pred = |i: usize, _bar: &HistBar| {
            i >= 2 && hikkake_completes(hist, i, j, inside_low, inside_high, bullish)
        };
        let anchor = find_setup_anchor(hist, &pred);
        return Some((
            (if bullish { "LONG" } else { "SHORT" }).to_string(),
            anchor,
            ref_,
        ));
    }
    None
}

/// True when bar i completes the Hikkake that began at inside bar j (j and its
/// false-break bar fixed) — used by the anchor scan so the gate and the anchor
/// cannot drift.
fn hikkake_completes(
    hist: &[HistBar],
    i: usize,
    j: usize,
    inside_low: f64,
    inside_high: f64,
    bullish: bool,
) -> bool {
    if i < j + 2 {
        return false;
    }
    let fb = j + 1;
    if i - fb > HIKKAKE_WINDOW_BARS {
        return false;
    }
    if bullish {
        return hist[fb].close < inside_low && hist[i].close > inside_high;
    }
    hist[fb].close > inside_high && hist[i].close < inside_low
}

/// William's Oops (Ch7.4 p231): an open beyond the prior bar's range (type-3
/// gap) reclaimed by a close back through the prior extreme.
fn detect_e(fm: &FeatMap, hist: &[HistBar], close: f64) -> Option<(String, String, f64)> {
    // `gap_dir is None or gap_dir.value is None`.
    let gdir = match fm.value("gap_dir") {
        Some(v) => v,
        None => return None,
    };
    let n = hist.len();
    if n < 2 {
        return None;
    }
    let prior_high = hist[n - 2].high;
    let prior_low = hist[n - 2].low;
    if gdir < 0.0 && close > prior_low {
        let ref_ = prior_low;
        let pred = |i: usize, bar: &HistBar| {
            i >= 1 && bar.open < hist[i - 1].low && bar.close > hist[i - 1].low
        };
        let anchor = find_setup_anchor(hist, &pred);
        return Some(("LONG".to_string(), anchor, ref_));
    }
    if gdir > 0.0 && close < prior_high {
        let ref_ = prior_high;
        let pred = |i: usize, bar: &HistBar| {
            i >= 1 && bar.open > hist[i - 1].high && bar.close < hist[i - 1].high
        };
        let anchor = find_setup_anchor(hist, &pred);
        return Some(("SHORT".to_string(), anchor, ref_));
    }
    None
}

/// Ichimoku failed cloud breakout (Ch16.2 p642): SHORT on a close back below
/// the cloud-proxy top after a close above it.
fn detect_f(hist: &[HistBar], close: f64) -> Option<(String, String, f64)> {
    let n = hist.len();
    if n < CLOUD_N + 1 {
        return None;
    }
    let top = cloud_top(hist, n - 2)?; // cloud top at the prior bar
    if !(hist[n - 2].close > top && close < top) {
        return None;
    }
    let pred = |i: usize, bar: &HistBar| {
        if i < CLOUD_N + 1 {
            return false;
        }
        match cloud_top(hist, i - 1) {
            Some(t) => hist[i - 1].close > t && bar.close < t,
            None => false,
        }
    };
    let anchor = find_setup_anchor(hist, &pred);
    Some(("SHORT".to_string(), anchor, top))
}

/// Failed S/R close-through (role reversal, Ch5.5 p150): the prior bar closed
/// THROUGH the 20-bar window S/R level (as of the PRIOR bar), and the current
/// bar closes back through it. LONG at the window low, SHORT at the window
/// high.
fn detect_g(hist: &[HistBar], close: f64) -> Option<(String, String, f64)> {
    let n = hist.len();
    if n < 22 {
        return None;
    }
    // The S/R level as of the PRIOR bar (G-22 window of the 20 bars before
    // it): the false-move bar's own low/high cannot set the level it broke.
    let w_high = hist[n - 22..n - 2].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
    let w_low = hist[n - 22..n - 2].iter().map(|b| b.low).fold(f64::INFINITY, f64::min);
    if !(w_high > w_low) {
        return None;
    }
    if hist[n - 2].close < w_low && close > w_low {
        let pred = |i: usize, bar: &HistBar| {
            if i < 21 {
                return false;
            }
            let lv = hist[i - 21..i - 1].iter().map(|b| b.low).fold(f64::INFINITY, f64::min);
            hist[i - 1].close < lv && bar.close > lv
        };
        let anchor = find_setup_anchor(hist, &pred);
        return Some(("LONG".to_string(), anchor, w_low));
    }
    if hist[n - 2].close > w_high && close < w_high {
        let pred = |i: usize, bar: &HistBar| {
            if i < 21 {
                return false;
            }
            let hv = hist[i - 21..i - 1].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
            hist[i - 1].close > hv && bar.close < hv
        };
        let anchor = find_setup_anchor(hist, &pred);
        return Some(("SHORT".to_string(), anchor, w_high));
    }
    None
}

// --- evaluation -------------------------------------------------------------

pub fn failed_breakout_2b(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let variant = VARIANT;
    // `_need(state, [close, atr, history])` — key presence (Python `in
    // state.features`), never a value check.
    if !fm.features.contains_key("close")
        || !fm.features.contains_key("atr")
        || !fm.features.contains_key("history")
    {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // `atr is None or not isinstance(hist_value, (tuple, list)) or not
    // hist_value` — an empty history is NO_HABITAT.
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // Per-variant habitat: each setup needs a minimum history length (the
    // false move, its reference bar, and the reclaim bar must all fit) — a
    // too-short window is NO_HABITAT, never a zero signal.
    let min_hist = match variant {
        "b" => MIN_HISTORY_B,
        "c" => MIN_HISTORY_C,
        "d" => MIN_HISTORY_D,
        "e" => MIN_HISTORY_E,
        "f" => MIN_HISTORY_F,
        _ => MIN_HISTORY_G,
    };
    if fm.history.len() < min_hist {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // Per-variant habitat: candle_shape features are warmup-gated and ABSENT
    // until their window fills (inside/outside need 2 bars, gaps need 2 bars)
    // — absent features are NO_HABITAT, never a zero signal.
    if variant == "c" || variant == "d" {
        if !fm.features.contains_key("inside_bar") || !fm.features.contains_key("outside_bar") {
            return no_habitat(expert_id, version, fm.as_of);
        }
    } else if variant == "e" {
        if !fm.features.contains_key("gap_dir") || !fm.features.contains_key("gap_size") {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    let hist = &fm.history;
    let hit = match variant {
        "b" => detect_b(fm, hist, close),
        "c" => hikkake(fm, hist, close, true),
        "d" => hikkake(fm, hist, close, false),
        "e" => detect_e(fm, hist, close),
        "f" => detect_f(hist, close),
        _ => detect_g(hist, close),
    };
    let (direction, anchor, ref_) = match hit {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    // 1R:1R:8bar fallback geometry with the atr_ref unit (D-028); the frozen
    // level is bound as prior_low_ref (longs) / prior_high_ref (shorts).
    let mut g = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(1.0)),
        ("stop_r", serde_json::json!(1.0)),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant)),
    ]);
    if direction == "LONG" {
        g.insert("prior_low_ref".to_string(), serde_json::json!(ref_));
    } else {
        g.insert("prior_high_ref".to_string(), serde_json::json!(ref_));
    }
    let draft = Draft {
        direction: direction.clone(),
        birth_time: fm.as_of,
        risk_geometry: g,
    };
    // `f'{sym}:{variant_id}:{direction}:{ref:.6f}:{close:.6f}'` — fixed-6,
    // half-even, exactly the Python f-string (PARITY_AND_IDENTITY_SPEC §3).
    let fingerprint = format!("{sym}:{variant}:{direction}:{ref_:.6}:{close:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
