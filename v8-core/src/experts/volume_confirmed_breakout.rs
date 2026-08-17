//! volume_confirmed_breakout: close beyond the 20-bar window extreme with a
//! volume gate (variants d/c/b/a in priority order); the frozen prior extreme
//! is the reference for gate + anchor. Ported at S4; draft parity proven.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "participation", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

pub fn volume_confirmed_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let volume = match fm.value("volume") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let sma = match fm.value("vol_smooth_ma") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let long_level = match fm.value("window_high_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let short_level = match fm.value("window_low_20") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
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
        fm.history[lo..i]
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max)
    };
    let prior_low = |i: usize| -> f64 {
        let lo = i.saturating_sub(20);
        fm.history[lo..i]
            .iter()
            .map(|b| b.low)
            .fold(f64::INFINITY, f64::min)
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
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(STOP_R)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!(variant)),
            (ref_key, serde_json::json!(level)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}:{}", close, level, variant);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
