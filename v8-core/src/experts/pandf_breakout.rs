//! pandf_breakout: evaluate() port target (issue #95) — mirror src/v8/experts/pandf_breakout.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Point-and-figure boxed-price breakout (variants a/b/c/d). The P&F transform
//! is computed inside the expert from the history close window: columns of X
//! rising / O falling, box = 1.0 * ATR at detection (LOCKED orchestrator
//! directive), reversal = 3 boxes. The setup anchor is the column-START index
//! of the current (breakout) column (`hist[anchor_idx][0]`), NOT the D-026
//! find_setup_anchor run-start — the Python source anchors on the column.
//!
//! The parity harness constructs `PandfBreakoutExpert()` with its default
//! variant_id 'a', and the port fn signature carries no variant parameter, so
//! the declared default variant 'a' is used here; the full `_signal` machinery
//! (all four variants) is mirrored below for fidelity.

use crate::experts::base::*;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const EXPIRY_BARS: i64 = 8;

// Declared, LOCKED box filter (orchestrator directive): box = 1.0 * ATR at
// detection, reversal = 3 boxes.
const BOX_ATR_K: f64 = 1.0;
const REVERSAL_BOXES: i64 = 3;
// Minimum history for a meaningful column structure.
const MIN_HISTORY_BARS: usize = 20;

/// One P&F column: direction (+1 = X rising, -1 = O falling), index of the
/// first close that contributed, and box prices ordered from the column's
/// origin to its extreme (rising for X, falling for O).
struct Column {
    d: i64,
    start: usize,
    levels: Vec<f64>,
}

/// A matched breakout signal (mirror of the Python `_signal` return tuple
/// (direction, anchor_idx, col_bottom, col_top, col_boxes)).
struct Signal {
    direction: &'static str,
    anchor_idx: usize,
    col_bottom: f64,
    col_top: f64,
    col_boxes: usize,
}

/// Deterministic close-based P&F columns (mirror of `_columns`).
fn columns(closes: &[f64], box_: f64, reversal: i64) -> Vec<Column> {
    let mut cols: Vec<Column> = Vec::new();
    let mut cur: Option<Column> = None;
    for (i, &c) in closes.iter().enumerate() {
        if cur.is_none() {
            cur = Some(Column { d: 1, start: i, levels: vec![c] });
            continue;
        }
        let col = cur.as_mut().unwrap();
        if col.d > 0 {
            let top = *col.levels.last().unwrap();
            if c >= top + box_ {
                let add = ((c - top) / box_) as i64;
                for k in 1..=add {
                    col.levels.push(top + box_ * (k as f64));
                }
                continue;
            }
            if c <= top - (reversal as f64) * box_ {
                let mut new_levels = vec![top - box_];
                let add = ((top - box_ - c) / box_) as i64;
                for k in 1..=add {
                    new_levels.push(top - box_ - box_ * (k as f64));
                }
                cols.push(std::mem::replace(
                    col,
                    Column { d: 0, start: 0, levels: Vec::new() },
                ));
                cur = Some(Column { d: -1, start: i, levels: new_levels });
                continue;
            }
        } else {
            let bottom = *col.levels.last().unwrap();
            if c <= bottom - box_ {
                let add = ((bottom - c) / box_) as i64;
                for k in 1..=add {
                    col.levels.push(bottom - box_ * (k as f64));
                }
                continue;
            }
            if c >= bottom + (reversal as f64) * box_ {
                let mut new_levels = vec![bottom + box_];
                let add = ((c - bottom - box_) / box_) as i64;
                for k in 1..=add {
                    new_levels.push(bottom + box_ + box_ * (k as f64));
                }
                cols.push(std::mem::replace(
                    col,
                    Column { d: 0, start: 0, levels: Vec::new() },
                ));
                cur = Some(Column { d: 1, start: i, levels: new_levels });
                continue;
            }
        }
    }
    if let Some(c) = cur {
        cols.push(c);
    }
    cols
}

/// (direction, anchor_idx, col_bottom, col_top, col_boxes) for the signal, or
/// None. A double/triple top requires the current column to be an X column
/// whose top exceeds the prior X column top(s); bottoms mirror on O columns.
fn signal(cols: &[Column], variant_id: &str) -> Option<Signal> {
    if cols.is_empty() {
        return None;
    }
    let last = cols.last().unwrap();
    let d_last = last.d;
    let start_last = last.start;
    let levels_last = &last.levels;
    let xs: Vec<&Column> = cols.iter().filter(|c| c.d > 0).collect();
    let os_: Vec<&Column> = cols.iter().filter(|c| c.d < 0).collect();
    match variant_id {
        "a" => {
            if d_last > 0
                && xs.len() >= 2
                && levels_last[levels_last.len() - 1]
                    > xs[xs.len() - 2].levels[xs[xs.len() - 2].levels.len() - 1]
            {
                return Some(Signal {
                    direction: "LONG",
                    anchor_idx: start_last,
                    col_bottom: levels_last[0],
                    col_top: levels_last[levels_last.len() - 1],
                    col_boxes: levels_last.len() - 1,
                });
            }
            None
        }
        "b" => {
            if d_last < 0
                && os_.len() >= 2
                && levels_last[levels_last.len() - 1]
                    < os_[os_.len() - 2].levels[os_[os_.len() - 2].levels.len() - 1]
            {
                return Some(Signal {
                    direction: "SHORT",
                    anchor_idx: start_last,
                    col_bottom: levels_last[levels_last.len() - 1],
                    col_top: levels_last[0],
                    col_boxes: levels_last.len() - 1,
                });
            }
            None
        }
        "c" => {
            if d_last > 0
                && xs.len() >= 3
                && levels_last[levels_last.len() - 1]
                    > xs[xs.len() - 2].levels[xs[xs.len() - 2].levels.len() - 1]
                        .max(xs[xs.len() - 3].levels[xs[xs.len() - 3].levels.len() - 1])
            {
                return Some(Signal {
                    direction: "LONG",
                    anchor_idx: start_last,
                    col_bottom: levels_last[0],
                    col_top: levels_last[levels_last.len() - 1],
                    col_boxes: levels_last.len() - 1,
                });
            }
            None
        }
        _ => {
            if d_last < 0
                && os_.len() >= 3
                && levels_last[levels_last.len() - 1]
                    < os_[os_.len() - 2].levels[os_[os_.len() - 2].levels.len() - 1]
                        .min(os_[os_.len() - 3].levels[os_[os_.len() - 3].levels.len() - 1])
            {
                return Some(Signal {
                    direction: "SHORT",
                    anchor_idx: start_last,
                    col_bottom: levels_last[levels_last.len() - 1],
                    col_top: levels_last[0],
                    col_boxes: levels_last.len() - 1,
                });
            }
            None
        }
    }
}

pub fn pandf_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    // The parity harness instantiates PandfBreakoutExpert() with its default
    // variant_id 'a'; the port fn signature carries no variant, so the default
    // is used (mirror of the Python __init__ default).
    let variant_id = "a";
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // Python: atr None or atr <= 0 or empty history / len < MIN_HISTORY_BARS.
    if atr <= 0.0 || fm.history.len() < MIN_HISTORY_BARS {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let box_ = atr * BOX_ATR_K;
    if box_ <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let closes: Vec<f64> = fm.history.iter().map(|b| b.close).collect();
    let hit = match signal(&columns(&closes, box_, REVERSAL_BOXES), variant_id) {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    // The setup anchor is the event id of the bar at the breakout column's
    // start index (hist[anchor_idx][0]) — NOT the D-026 find_setup_anchor.
    let anchor = fm.history[hit.anchor_idx].event_id.clone();
    let (stop_price, target_price, prior_low_ref, prior_high_ref) = if hit.direction == "LONG" {
        let stop_price = hit.col_bottom;
        let target_price =
            hit.col_bottom + (hit.col_boxes as f64) * box_ * (REVERSAL_BOXES as f64);
        (stop_price, target_price, Some(hit.col_bottom), None)
    } else {
        let stop_price = hit.col_top;
        let target_price = hit.col_top - (hit.col_boxes as f64) * box_ * (REVERSAL_BOXES as f64);
        (stop_price, target_price, None, Some(hit.col_top))
    };
    let stop_r = if hit.direction == "LONG" {
        (close - stop_price) / atr
    } else {
        (stop_price - close) / atr
    };
    let target_r = if hit.direction == "LONG" {
        (target_price - close) / atr
    } else {
        (close - target_price) / atr
    };
    if stop_r <= 0.0 || target_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let mut entries = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(target_r)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant_id)),
        ("reversal", serde_json::json!(REVERSAL_BOXES)),
    ];
    if let Some(v) = prior_low_ref {
        entries.push(("prior_low_ref", serde_json::json!(v)));
    }
    if let Some(v) = prior_high_ref {
        entries.push(("prior_high_ref", serde_json::json!(v)));
    }
    let draft = Draft {
        direction: hit.direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(entries),
    };
    let fingerprint = format!("{sym}:{variant_id}:{}:{:.6}", hit.direction, close);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
