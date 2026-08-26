//! trend_pullback_depth: LONG when the close pulls back inside a declared
//! depth band of the impulse swing while the trend fan stays aligned. Ported
//! variant a (depth <= 38.2% of the swing_high_10/swing_low_10 impulse range)
//! — the registered expert_id "trend_pullback_depth" is Python class
//! TrendPullbackDepthExpert (variant_id 'a', depth_gate DEPTH_382); variants
//! b..g are separate registry entries, not ported here. Mirrors
//! src/v8/experts/trend_pullback_depth.py bit-for-bit (§3 PARITY_AND_IDENTITY_SPEC).

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["trend", "location", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const _STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

/// DEPTH_382 — book verbatim 38.2% retracement gate (variant a).
const _DEPTH_382: f64 = 0.382;

pub fn trend_pullback_depth(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // Python `_need`: close/atr/history/ema_fast/ema_slow always, plus
    // swing_high_10/swing_low_10 for the depth variants (a). Presence = the
    // feature is emitted with a numeric value (fm.value None covers both an
    // absent feature and a null value — Python's `_need` + `_impulse` value
    // checks land on the same NO_HABITAT).
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let fast = match fm.value("ema_fast") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let slow = match fm.value("ema_slow") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let sh = match fm.value("swing_high_10") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let sl = match fm.value("swing_low_10") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // Python history check (`not hist_value`); the state's "history" feature
    // and fm.history share the same 32-bar window ending at t-1.
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    if !(sh > sl && sl > 0.0) {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let rng = sh - sl;

    if version == "v1" {
        if !(fast > slow) {
            return no_setup(expert_id, version, fm.as_of);
        }
        let depth = (sh - close) / rng;
        if !(0.0..=0.382).contains(&depth) || !(close < sh) {
            return no_setup(expert_id, version, fm.as_of);
        }
        let lower = sh - 0.382 * rng;
        let pred = |_i: usize, b: &HistBar| b.ema_fast > b.ema_slow && lower <= b.close && b.close < sh;
        let anchor = find_setup_anchor(&fm.history, &pred);
        let draft = Draft {
            direction: "LONG".into(),
            birth_time: fm.as_of,
            risk_geometry: geom(vec![
                ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
                ("target_r", serde_json::json!(TARGET_R)),
                ("stop_r", serde_json::json!(1.0)),
                ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
                ("atr_ref", serde_json::json!(atr)),
                ("prior_low_ref", serde_json::json!(sl)),
                ("variant", serde_json::json!("a")),
            ]),
        };
        let fingerprint = format!("{sym}:a:LONG:{close:.6}:{sl:.6}");
        return candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint);
    }

    // LONG in uptrend: Pullback into 0.0..0.50 retracement
    let is_long = fast > slow && close < sh && {
        let depth = (sh - close) / rng;
        (0.0..=0.50).contains(&depth)
    };

    // SHORT in downtrend: Rally into 0.0..0.50 upward retracement
    let is_short = fast < slow && close > sl && {
        let depth = (close - sl) / rng;
        (0.0..=0.50).contains(&depth)
    };

    let direction = if is_long {
        "LONG"
    } else if is_short {
        "SHORT"
    } else {
        return no_setup(expert_id, version, fm.as_of);
    };

    let pred = move |_i: usize, b: &HistBar| {
        if direction == "LONG" {
            b.ema_fast > b.ema_slow && b.close < sh && ((sh - b.close) / rng) <= 0.50
        } else {
            b.ema_fast < b.ema_slow && b.close > sl && ((b.close - sl) / rng) <= 0.50
        }
    };
    let anchor = find_setup_anchor(&fm.history, &pred);
    let _stop_price = if direction == "LONG" { sl } else { sh };
    let raw_stop_r = if direction == "LONG" {
        (close - sl) / atr
    } else {
        (sh - close) / atr
    };
    let stop_r = raw_stop_r.clamp(0.8, 2.0);

    let draft = Draft {
        direction: direction.into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(stop_r)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("prior_low_ref", serde_json::json!(sl)),
            ("prior_high_ref", serde_json::json!(sh)),
            ("variant", serde_json::json!("v2")),
        ]),
    };
    let fingerprint = format!("{sym}:{direction}:{close:.6}:{sl:.6}:{sh:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
