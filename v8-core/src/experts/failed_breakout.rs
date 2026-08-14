//! failed_breakout (pilot): SHORT after a close-breakout above the prior high
//! and a close back below it; the level is frozen at detection. Ported at S4;
//! draft parity proven.

use crate::experts::base::*;
use crate::state::HistBar;
use crate::simulator::Draft;

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

pub fn failed_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // _last_breakout: newest bar j whose close exceeded the max high before it.
    let mut breakout: Option<(usize, f64)> = None;
    for j in (1..fm.history.len()).rev() {
        let prior = fm.history[..j].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
        if fm.history[j].close > prior {
            breakout = Some((j, prior));
            break;
        }
    }
    let (breakout_idx, ref_prior_high) = match breakout {
        Some(x) => x,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    if !(close < ref_prior_high) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let level = ref_prior_high;
    let pred = |_i: usize, b: &HistBar| _i > breakout_idx && b.close < level;
    let anchor = find_setup_anchor(&fm.history, &pred);
    // Issue #63: the structural stop IS the frozen breakout level — beyond
    // the prior high the SHORT failed under, not an ATR multiple from entry.
    // stop_r is the frozen distance in R (D-028): (prior_high - close)/atr.
    let stop_r = (ref_prior_high - close) / atr;
    let draft = Draft {
        direction: "SHORT".into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("prior_high_ref", serde_json::json!(ref_prior_high)),
            ("stop_ref", serde_json::json!(ref_prior_high)),
            ("stop_r", serde_json::json!(stop_r)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_prior_high);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
