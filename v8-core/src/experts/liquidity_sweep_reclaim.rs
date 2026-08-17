//! liquidity_sweep_reclaim (pilot): LONG on a sweep+reclaim of the windowed
//! prior low, SHORT on the prior high; one frozen reference for gate+anchor.
//! Ported at S4; draft parity proven.

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
pub const EXPIRY_BARS: i64 = 8;

pub fn liquidity_sweep_reclaim(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let prior_low = |i: usize| -> f64 {
        fm.history[..i]
            .iter()
            .map(|b| b.low)
            .fold(f64::INFINITY, f64::min)
    };
    let prior_high = |i: usize| -> f64 {
        fm.history[..i]
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max)
    };
    let newest = &fm.history[fm.history.len() - 1];
    let (direction, ref_val, ref_key) = if newest.low < prior_low(fm.history.len() - 1)
        && close > prior_low(fm.history.len() - 1)
    {
        ("LONG", prior_low(fm.history.len() - 1), "prior_low_ref")
    } else if newest.high > prior_high(fm.history.len() - 1)
        && close < prior_high(fm.history.len() - 1)
    {
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
    // Issue #63: the structural stop is the swept level itself (prior_low for
    // a LONG reclaim, prior_high for a SHORT) — beyond the sweep, not an ATR
    // multiple from entry. stop_r is the frozen distance in R (D-028).
    let stop_r = if direction == "LONG" {
        (close - ref_val) / atr
    } else {
        (ref_val - close) / atr
    };
    let entries = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(TARGET_R)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        (ref_key, serde_json::json!(ref_val)),
        ("stop_ref", serde_json::json!(ref_val)),
        ("stop_r", serde_json::json!(stop_r)),
    ];
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(entries),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_val);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
