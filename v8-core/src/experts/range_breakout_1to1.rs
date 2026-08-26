//! range_breakout_1to1: close beyond the 20-bar consolidation range with the
//! book's 1:1 measuring objective (variant a — no completion filter). Ported
//! at S4; draft parity proven. The oracle for expert_id `range_breakout_1to1`
//! is the base class `RangeBreakout1To1Expert` (variant 'a'), so the port
//! hardcodes variant-a flags: filter_mult = 1.0, atr_filter = false, no
//! volume gates. Mirrors src/v8/experts/range_breakout_1to1.py evaluate().

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history", "participation"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const EXPIRY_BARS: i64 = 8;

const RANGE_N: usize = 20;
const WIDTH_MAX: f64 = 0.03;

/// G-22 20-bar window high before bar i (Python `_win_high`).
fn win_high(hist: &[HistBar], i: usize) -> Option<f64> {
    if i < RANGE_N {
        return None;
    }
    Some(
        hist[i - RANGE_N..i]
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max),
    )
}

/// G-22 20-bar window low before bar i (Python `_win_low`).
fn win_low(hist: &[HistBar], i: usize) -> Option<f64> {
    if i < RANGE_N {
        return None;
    }
    Some(
        hist[i - RANGE_N..i]
            .iter()
            .map(|b| b.low)
            .fold(f64::INFINITY, f64::min),
    )
}

/// Variant-a breakout level at bar i (Python `_breakout_level` with
/// filter_mult=1.0 and atr_filter=False — the raw window extreme).
fn breakout_level(hist: &[HistBar], i: usize, direction: &str) -> Option<f64> {
    if direction == "LONG" {
        win_high(hist, i)
    } else {
        win_low(hist, i)
    }
}

/// Python `_long_pred`: bar i broke above the 20-bar window high and the prior
/// bar did not (single-bar setup guarantee).
fn long_pred(hist: &[HistBar], i: usize, bar: &HistBar) -> bool {
    if i < RANGE_N {
        return false;
    }
    let level = win_high(hist, i).expect("i >= RANGE_N");
    if !(bar.close > level) {
        return false;
    }
    let prev = if i > RANGE_N {
        win_high(hist, i - 1)
    } else {
        None
    };
    match prev {
        None => true,
        Some(p) => hist[i - 1].close <= p,
    }
}

/// Python `_short_pred`: bar i broke below the 20-bar window low and the prior
/// bar did not.
fn short_pred(hist: &[HistBar], i: usize, bar: &HistBar) -> bool {
    if i < RANGE_N {
        return false;
    }
    let level = win_low(hist, i).expect("i >= RANGE_N");
    if !(bar.close < level) {
        return false;
    }
    let prev = if i > RANGE_N {
        win_low(hist, i - 1)
    } else {
        None
    };
    match prev {
        None => true,
        Some(p) => hist[i - 1].close >= p,
    }
}

pub fn range_breakout_1to1(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let wh = match fm.value("window_high_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let wl = match fm.value("window_low_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let rng_h = match fm.value("range_height_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // consolidation_range is a 4-tuple (h_ref, l_ref, width_ratio, is_active)
    // in Python; the Rust state emits it as a JSON array.
    let cons = match fm.features.get("consolidation_range") {
        Some(f) => match f.value.as_array() {
            Some(a) => a,
            None => return no_habitat(expert_id, version, fm.as_of),
        },
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let cons_w = match cons.get(2).and_then(|v| v.as_f64()) {
        Some(w) => w,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // Narrow-consolidation precondition (declared width bound).
    if cons_w > WIDTH_MAX {
        return no_setup(expert_id, version, fm.as_of);
    }
    if !(wh > wl && rng_h > 0.0) {
        return no_setup(expert_id, version, fm.as_of);
    }
    // D-141 Volume Expansion Gate: Require positive volume z-score on range breakout
    let vol_z = fm.value("vol_zscore").unwrap_or(0.0);
    if vol_z < 0.20 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let direction = if close > wh {
        "LONG"
    } else if close < wl {
        "SHORT"
    } else {
        return no_setup(expert_id, version, fm.as_of);
    };
    // Single-bar setup guarantee: the prior bar (hist[-2]) must NOT have
    // broken out. Python `_breakout_level(n - 2, direction)` returns None for
    // n - 2 < RANGE_N (an underflow-safe negative index); saturating_sub
    // yields the same None branch.
    let n = fm.history.len();
    let prev = breakout_level(&fm.history, n.saturating_sub(2), direction);
    let prior_broke = match prev {
        Some(p) => {
            if direction == "LONG" {
                fm.history[n - 2].close > p
            } else {
                fm.history[n - 2].close < p
            }
        }
        None => false,
    };
    if prior_broke {
        return no_setup(expert_id, version, fm.as_of);
    }
    // D-026 anchor via the Python per-bar predicate (the anchor is the
    // breakout bar itself: the gate guarantees hist[-2] did not break out).
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = if direction == "LONG" {
        Box::new(move |i, b| long_pred(&fm.history, i, b))
    } else {
        Box::new(move |i, b| short_pred(&fm.history, i, b))
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);
    // 1:1 measuring objective in R: one range height is the target AND the
    // far-side stop distance (D-028).
    let rr = rng_h / atr;
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: if direction == "LONG" {
            geom(vec![
                ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
                ("target_r", serde_json::json!(rr)),
                ("stop_r", serde_json::json!(rr)),
                ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
                ("atr_ref", serde_json::json!(atr)),
                ("variant", serde_json::json!("a")),
                ("prior_low_ref", serde_json::json!(wl)),
                ("breakout_ref", serde_json::json!(wh)),
                ("target_2x_ref", serde_json::json!(wh + 2.0 * rng_h)),
            ])
        } else {
            geom(vec![
                ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
                ("target_r", serde_json::json!(rr)),
                ("stop_r", serde_json::json!(rr)),
                ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
                ("atr_ref", serde_json::json!(atr)),
                ("variant", serde_json::json!("a")),
                ("prior_high_ref", serde_json::json!(wh)),
                ("breakout_ref", serde_json::json!(wl)),
                ("target_2x_ref", serde_json::json!(wl - 2.0 * rng_h)),
            ])
        },
    };
    // Python: f'{sym}:{variant_id}:{direction}:{close:.6f}:{wh:.6f}:{wl:.6f}'.
    let fingerprint = format!("{sym}:a:{direction}:{close:.6}:{wh:.6}:{wl:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
