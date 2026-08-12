//! liquidity_sweep_reclaim (pilot): LONG on a sweep+reclaim of the windowed
//! prior low, SHORT on the prior high; one frozen reference for gate+anchor.
//! Ported at S4; draft parity proven.

use crate::experts::base::*;
use crate::state::HistBar;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history"];

pub fn liquidity_sweep_reclaim(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let prior_low = |i: usize| -> f64 {
        fm.history[..i].iter().map(|b| b.low).fold(f64::INFINITY, f64::min)
    };
    let prior_high = |i: usize| -> f64 {
        fm.history[..i].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max)
    };
    let newest = &fm.history[fm.history.len() - 1];
    let (direction, ref_val, ref_key) = if newest.low < prior_low(fm.history.len() - 1)
        && close > prior_low(fm.history.len() - 1) {
        ("LONG", prior_low(fm.history.len() - 1), "prior_low_ref")
    } else if newest.high > prior_high(fm.history.len() - 1)
        && close < prior_high(fm.history.len() - 1) {
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
    let entries = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(1.0)),
        ("stop_r", serde_json::json!(1.0)),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        (ref_key, serde_json::json!(ref_val)),
    ];
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(entries),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_val);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
