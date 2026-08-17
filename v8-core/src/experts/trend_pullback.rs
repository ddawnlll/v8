//! trend_pullback (pilot): LONG when fast > slow and close < slow, anchored on
//! the consecutive pullback run. Ported at S4; draft parity proven.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["trend", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

pub fn trend_pullback(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
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
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    if !(fast > slow && close < slow) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let pred = |_i: usize, b: &HistBar| b.ema_fast > b.ema_slow && b.close < b.ema_slow;
    let anchor = find_setup_anchor(&fm.history, &pred);
    let draft = Draft {
        direction: "LONG".into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(STOP_R)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, slow);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
