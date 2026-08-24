//! fib_retracement_continuation: evaluate() port target (issue #85) — mirror src/v8/experts/fib_retracement_continuation.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Variant 'a' (ratio 0.382): a pullback that reaches the retracement level
//! (low <= level) and is reclaimed by the close (close > level) on an up-
//! impulse, mirrored for down-impulses. The deepest retracement (0.786) is the
//! invalidation reference, frozen into the draft geometry as prior_low_ref /
//! prior_high_ref (D-042, `prior_*_ref` pattern). Anchor is the standard
//! D-026 base find_setup_anchor over the pullback-reclaim predicate.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const _STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

/// The frozen variant 'a' retracement ratio (self._RATIO['a']).
const _RATIO: f64 = 0.382;
/// The deepest retracement: the invalidation / stop reference level.
const DEEP_RETRACEMENT: f64 = 0.786;

/// Python `_retracement_level(fibs, ratio)`: the level for `ratio` from the
/// self-describing fib array [extreme, direction, retr, ext]; None when the
/// shape is wrong or no pair matches within 1e-9.
fn retracement_level(fibs: &serde_json::Value, ratio: f64) -> Option<f64> {
    let arr = fibs.as_array()?;
    if arr.len() != 4 {
        return None;
    }
    for pair in arr[2].as_array()? {
        let p = match pair.as_array() {
            Some(p) if p.len() == 2 => p,
            _ => return None,
        };
        let r = p[0].as_f64()?;
        if (r - ratio).abs() < 1e-9 {
            return p[1].as_f64();
        }
    }
    None
}

/// Python `_long_pred`: bar i reached the retracement level and reclaimed it
/// by the close (pullback-reclaim of an up-impulse).
fn long_pred(i: usize, b: &HistBar, level: f64) -> bool {
    i > 0 && b.close > level && b.low <= level
}

/// Python `_short_pred`: mirror (price rose to the level, closed back below).
fn short_pred(i: usize, b: &HistBar, level: f64) -> bool {
    i > 0 && b.close < level && b.high >= level
}

pub fn fib_retracement_continuation(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // `_need` over {sym}.close/.atr/.history/.fib_levels; then the None guards.
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let fibs = match fm.features.get("fib_levels") {
        Some(f) => f.value.clone(),
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // hist must be a non-empty (tuple|list) — empty window is NO_HABITAT.
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let fibs_arr = match fibs.as_array() {
        Some(a) if a.len() == 4 => a,
        _ => return no_habitat(expert_id, version, fm.as_of),
    };
    let anchor_price = match fibs_arr[0].as_f64() {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let direction = match fibs_arr[1].as_f64() {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // The fib anchor's own consistency is the guard (degenerate pair => None).
    if !(direction == 1.0 || direction == -1.0) || anchor_price <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }

    if version == "v1" {
        let level = match retracement_level(&fibs, 0.382) {
            Some(v) => v,
            None => return no_habitat(expert_id, version, fm.as_of),
        };
        let deep = match retracement_level(&fibs, DEEP_RETRACEMENT) {
            Some(v) => v,
            None => return no_habitat(expert_id, version, fm.as_of),
        };
        let (direction_sig, pred): (&str, fn(usize, &HistBar, f64) -> bool) = if direction == 1.0 {
            ("LONG", long_pred)
        } else {
            ("SHORT", short_pred)
        };
        let n = fm.history.len();
        if !pred(n - 1, &fm.history[n - 1], level) {
            return no_setup(expert_id, version, fm.as_of);
        }
        let anchor = find_setup_anchor(&fm.history, &|i, b| pred(i, b, level));
        let draft = Draft {
            direction: direction_sig.to_string(),
            birth_time: fm.as_of,
            risk_geometry: geom(vec![
                ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
                ("target_r", serde_json::json!(TARGET_R)),
                ("stop_r", serde_json::json!(1.0)),
                ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
                ("atr_ref", serde_json::json!(atr)),
                (
                    if direction_sig == "LONG" {
                        "prior_low_ref"
                    } else {
                        "prior_high_ref"
                    },
                    serde_json::json!(deep),
                ),
            ]),
        };
        let fingerprint = format!("{sym}:{:.3}:{:.6}:{direction_sig}", 0.382, level);
        return candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint);
    }

    let ratios = [0.382, 0.500, 0.618];
    let mut hit_level: Option<(f64, f64)> = None; // (ratio, level_price)

    let n = fm.history.len();
    let newest = &fm.history[n - 1];

    for &r in &ratios {
        if let Some(lvl) = retracement_level(&fibs, r) {
            let reached_and_reclaimed = if direction == 1.0 {
                newest.low <= lvl && newest.close > lvl
            } else {
                newest.high >= lvl && newest.close < lvl
            };
            if reached_and_reclaimed {
                hit_level = Some((r, lvl));
                break;
            }
        }
    }

    let (active_ratio, level) = match hit_level {
        Some(hl) => hl,
        None => return no_setup(expert_id, version, fm.as_of),
    };

    let deep = match retracement_level(&fibs, DEEP_RETRACEMENT) {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let (direction_sig, pred): (&str, fn(usize, &HistBar, f64) -> bool) = if direction == 1.0 {
        ("LONG", long_pred)
    } else {
        ("SHORT", short_pred)
    };

    let anchor = find_setup_anchor(&fm.history, &|i, b| pred(i, b, level));
    let raw_stop_r = (close - deep).abs() / atr;
    let stop_r = raw_stop_r.clamp(0.8, 2.0);

    let draft = Draft {
        direction: direction_sig.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(stop_r)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            // The invalidation reference is FROZEN at detection (prior_*_ref,
            // D-042): prior_low_ref for LONG, prior_high_ref for SHORT.
            (
                if direction_sig == "LONG" {
                    "prior_low_ref"
                } else {
                    "prior_high_ref"
                },
                serde_json::json!(deep),
            ),
            ("ratio", serde_json::json!(active_ratio)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.3}:{:.6}:{direction_sig}", active_ratio, level);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
