//! donchian_breakout: N-bar price-channel breakout behavior family (E-10),
//! port of src/v8/experts/donchian_breakout.py variant a (N=20, long-only,
//! `channel` exit). The gate reference is the G-22 `window_high_20` /
//! `window_low_20` state features (the n bars before the current bar); the
//! D-026 anchor scans the windowed channel over `fm.history` exactly as the
//! Python `_channel_high`/`_channel_low` helpers. Ported at S4; draft parity
//! proven.

use crate::experts::base::*;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history", "participation"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

/// `channel_n` = 20 (variant a; base class parameter).
const CHANNEL_N: usize = 20;

pub fn donchian_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let window_high = match fm.value("window_high_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let window_low = match fm.value("window_low_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    if version == "v1" {
        if !(close > window_high) {
            return no_setup(expert_id, version, fm.as_of);
        }
        let pred = |i: usize, b: &crate::state::HistBar| -> bool {
            let start = i.saturating_sub(CHANNEL_N);
            if i <= start {
                return false;
            }
            b.close
                > fm.history[start..i]
                    .iter()
                    .map(|h| h.high)
                    .fold(f64::NEG_INFINITY, f64::max)
        };
        let anchor = find_setup_anchor(&fm.history, &pred);
        let stop_r = (close - window_low) / atr;
        let draft = Draft {
            direction: "LONG".into(),
            birth_time: fm.as_of,
            risk_geometry: geom(vec![
                ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
                ("target_r", serde_json::json!(TARGET_R)),
                ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
                ("atr_ref", serde_json::json!(atr)),
                ("prior_high_ref", serde_json::json!(window_high)),
                ("prior_low_ref", serde_json::json!(window_low)),
                ("channel_n", serde_json::json!(CHANNEL_N)),
                ("variant", serde_json::json!("a")),
                ("stop_ref", serde_json::json!(window_low)),
                ("stop_r", serde_json::json!(stop_r)),
            ]),
        };
        let fingerprint = format!("{sym}:LONG:{close:.6}:{window_high:.6}:{window_low:.6}");
        return candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint);
    }

    let direction = if close > window_high {
        "LONG"
    } else if close < window_low {
        "SHORT"
    } else {
        return no_setup(expert_id, version, fm.as_of);
    };

    // Single-bar setup freshness: prior bar must not have already closed beyond breakout level
    let n = fm.history.len();
    if n >= 2 {
        let prev_close = fm.history[n - 2].close;
        if (direction == "LONG" && prev_close > window_high)
            || (direction == "SHORT" && prev_close < window_low)
        {
            return no_setup(expert_id, version, fm.as_of);
        }
    }

    // Volume expansion filter: suppress low-volume false breakouts
    let vol_z = fm.value("vol_zscore").unwrap_or(0.0);
    if vol_z < 0.20 {
        return no_setup(expert_id, version, fm.as_of);
    }

    // D-026 anchor: newest false bar + 1 over the windowed predicate
    let pred = |i: usize, b: &crate::state::HistBar| -> bool {
        let start = i.saturating_sub(CHANNEL_N);
        if i <= start {
            return false;
        }
        if direction == "LONG" {
            b.close
                > fm.history[start..i]
                    .iter()
                    .map(|h| h.high)
                    .fold(f64::NEG_INFINITY, f64::max)
        } else {
            b.close
                < fm.history[start..i]
                    .iter()
                    .map(|h| h.low)
                    .fold(f64::INFINITY, f64::min)
        }
    };
    let anchor = find_setup_anchor(&fm.history, &pred);
    let raw_stop_dist = if direction == "LONG" {
        close - window_low
    } else {
        window_high - close
    };
    let stop_r = (raw_stop_dist / atr).clamp(0.8, 2.0);
    let stop_ref = if direction == "LONG" { window_low } else { window_high };

    let draft = Draft {
        direction: direction.into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("prior_high_ref", serde_json::json!(window_high)),
            ("prior_low_ref", serde_json::json!(window_low)),
            ("channel_n", serde_json::json!(CHANNEL_N)),
            ("variant", serde_json::json!("v2")),
            ("stop_ref", serde_json::json!(stop_ref)),
            ("stop_r", serde_json::json!(stop_r)),
        ]),
    };
    let fingerprint = format!("{sym}:{direction}:{close:.6}:{window_high:.6}:{window_low:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
