//! gap_exhaustion: evaluate() port (issue #89) — mirror src/v8/experts/gap_exhaustion.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Gap-sequence reaction expert (exhaustion / breakaway / runaway). The
//! ExpertPlane dispatch passes no variant, so this port serves the Python
//! default `GapExhaustionExpert()` — variant 'a' (third-gap exhaustion
//! reversal); the 'b' (breakaway) and 'c' (runaway) branches mirror the source
//! for completeness. Gap zone and direction are frozen at detection; the
//! anchor is the D-026 run start of the variant's own predicate.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["candle_shape", "location", "volatility", "history"];

/// D-036 locked: the same-direction gap-count window.
const GAP_COUNT_WINDOW: usize = 20;

/// Direction of history bar i's type-3 gap (-1, 0, +1) — `_gap_of`.
fn gap_of(hist: &[HistBar], i: usize) -> i32 {
    if i == 0 {
        return 0;
    }
    let o = hist[i].open;
    let ph = hist[i - 1].high;
    let pl = hist[i - 1].low;
    if o > ph {
        1
    } else if o < pl {
        -1
    } else {
        0
    }
}

/// Same-direction gaps within the trailing GAP_COUNT_WINDOW ending at bar i —
/// `_count_dir` (`start = max(1, i - GAP_COUNT_WINDOW + 1)`).
fn count_dir(hist: &[HistBar], i: usize, direction: i32) -> usize {
    let start = 1usize.max(i.saturating_sub(GAP_COUNT_WINDOW - 1));
    (start..=i).filter(|&j| gap_of(hist, j) == direction).count()
}

/// (top, bottom) of bar i's gap zone — `_zone` (marketstate G-27 semantics).
fn zone(hist: &[HistBar], i: usize, direction: i32) -> (f64, f64) {
    let o = hist[i].open;
    if direction == 1 {
        (o, hist[i - 1].high)
    } else {
        (hist[i - 1].low, o)
    }
}

/// `_exhaustion_pred`: third same-direction gap whose bar fails to hold the
/// gap direction (reversal thesis).
fn exhaustion_pred(hist: &[HistBar], i: usize, b: &HistBar, direction: i32) -> bool {
    if i == 0 || gap_of(hist, i) != direction {
        return false;
    }
    if count_dir(hist, i, direction) < 3 {
        return false;
    }
    let (o, c) = (b.open, b.close);
    if direction == 1 {
        c < o
    } else {
        c > o
    }
}

/// `_breakaway_pred`: first gap in the direction that opens beyond the 20-bar
/// range (continuation thesis).
fn breakaway_pred(hist: &[HistBar], i: usize, b: &HistBar, direction: i32) -> bool {
    if i == 0 || gap_of(hist, i) != direction {
        return false;
    }
    if count_dir(hist, i, direction) != 1 {
        return false;
    }
    let o = b.open;
    let lo = i.saturating_sub(20);
    if direction == 1 {
        o > (lo..i).map(|j| hist[j].high).fold(f64::NEG_INFINITY, f64::max)
    } else {
        o < (lo..i).map(|j| hist[j].low).fold(f64::INFINITY, f64::min)
    }
}

/// `_runaway_pred`: second same-direction gap whose close holds the gap
/// (continuation thesis).
fn runaway_pred(hist: &[HistBar], i: usize, b: &HistBar, direction: i32) -> bool {
    if i == 0 || gap_of(hist, i) != direction {
        return false;
    }
    if count_dir(hist, i, direction) != 2 {
        return false;
    }
    let (o, c) = (b.open, b.close);
    if direction == 1 {
        c > o
    } else {
        c < o
    }
}

pub fn gap_exhaustion(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // D-044: the dispatch serves the Python default variant 'a'.
    let variant_id = "a";
    let common = ["close", "atr", "history", "gap_dir", "gap_size", "gap_levels"];
    // `_need` — key presence in the feature dict (values may be None).
    if variant_id == "b" {
        for k in ["window_high_20", "window_low_20"] {
            if !fm.features.contains_key(k) {
                return no_habitat(expert_id, version, fm.as_of);
            }
        }
    }
    for k in common {
        if !fm.features.contains_key(k) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let hist: &[HistBar] = &fm.history;
    if hist.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let n = hist.len();
    if n < 2 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let direction = match fm.value("gap_dir") {
        Some(v) => v.round() as i32,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if direction == 0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let o = hist[n - 1].open;
    let c = hist[n - 1].close;
    let (top, bottom) = zone(hist, n - 1, direction);
    // The current gap zone must be present in gap_levels (still unfilled);
    // `gl is None or gl.value is None or not gl.value` -> NO_HABITAT.
    let last_zone = match fm.features.get("gap_levels") {
        Some(f) => match &f.value {
            serde_json::Value::Array(arr) if !arr.is_empty() => arr.last().unwrap(),
            _ => return no_habitat(expert_id, version, fm.as_of),
        },
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let ztop = last_zone[0].as_f64().unwrap_or(f64::NAN);
    let zbottom = last_zone[1].as_f64().unwrap_or(f64::NAN);
    let zd = last_zone[2].as_f64().unwrap_or(f64::NAN);
    if !(zd.round() as i32 == direction
        && (ztop - top).abs() < 1e-9
        && (zbottom - bottom).abs() < 1e-9) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let count = count_dir(hist, n - 1, direction);
    let trade_dir: &str;
    let pred: Box<dyn Fn(usize, &HistBar) -> bool>;
    if variant_id == "a" {
        if count < 3 {
            return no_setup(expert_id, version, fm.as_of);
        }
        if direction == 1 && !(c < o) {
            return no_setup(expert_id, version, fm.as_of);
        }
        if direction == -1 && !(c > o) {
            return no_setup(expert_id, version, fm.as_of);
        }
        trade_dir = if direction == 1 { "SHORT" } else { "LONG" };
        pred = Box::new(move |i, b| exhaustion_pred(hist, i, b, direction));
    } else if variant_id == "b" {
        let wh = fm.value("window_high_20");
        let wl = fm.value("window_low_20");
        if direction == 1 && !wh.map_or(false, |v| o > v) {
            return no_setup(expert_id, version, fm.as_of);
        }
        if direction == -1 && !wl.map_or(false, |v| o < v) {
            return no_setup(expert_id, version, fm.as_of);
        }
        if count != 1
            || (direction == 1 && !(c > top))
            || (direction == -1 && !(c < bottom)) {
            return no_setup(expert_id, version, fm.as_of);
        }
        trade_dir = if direction == 1 { "LONG" } else { "SHORT" };
        pred = Box::new(move |i, b| breakaway_pred(hist, i, b, direction));
    } else {
        // 'c' — runaway/midway continuation.
        if count != 2
            || (direction == 1 && !(c > top))
            || (direction == -1 && !(c < bottom)) {
            return no_setup(expert_id, version, fm.as_of);
        }
        trade_dir = if direction == 1 { "LONG" } else { "SHORT" };
        pred = Box::new(move |i, b| runaway_pred(hist, i, b, direction));
    }
    // Gap-zone S/R reference, FROZEN at detection: the far side of the zone.
    let (ref_level, stop_r) = if trade_dir == "LONG" {
        (bottom, (close - bottom) / atr)
    } else {
        (top, (top - close) / atr)
    };
    if stop_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let anchor = find_setup_anchor(hist, &*pred);
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(1.0)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant_id)),
        ("level_ref", serde_json::json!(ref_level)),
        ("stop_ref", serde_json::json!(ref_level)),
        ("gap_top_ref", serde_json::json!(top)),
        ("gap_bottom_ref", serde_json::json!(bottom)),
    ]);
    if trade_dir == "LONG" {
        geometry.insert("prior_low_ref".into(), serde_json::json!(bottom));
    } else {
        geometry.insert("prior_high_ref".into(), serde_json::json!(top));
    }
    let fingerprint =
        format!("{sym}:{variant_id}:{trade_dir}:{close:.6}:{top:.6}:{bottom:.6}");
    let draft = Draft {
        direction: trade_dir.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
