//! ichimoku_cloud: Tenkan-Kijun crossover aligned with the trend line (variant
//! c, E-18). The Tenkan/Kijun midranges are computed INSIDE the expert from the
//! history OHLC (G-44); the state does not emit a cloud group. The setup anchor
//! is the CROSSING BAR — the first bar of the current run where the crossing
//! predicate holds (D-026 run-start semantics, via find_setup_anchor). Ported
//! at S4; draft parity proven.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

const TENKAN_N: usize = 9;
const KIJUN_N: usize = 26;

/// (max(high, n) + min(low, n)) / 2 over bars [max(0, i-n+1), i] — mirrors the
/// expert's `_midrange(i, n)` over the full history window.
fn midrange(hist: &[HistBar], i: usize, n: usize) -> f64 {
    let start = i.saturating_sub(n - 1);
    let mut hi = f64::NEG_INFINITY;
    let mut lo = f64::INFINITY;
    for b in &hist[start..=i] {
        if b.high > hi {
            hi = b.high;
        }
        if b.low < lo {
            lo = b.low;
        }
    }
    (hi + lo) / 2.0
}

pub fn ichimoku_cloud(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // _need(['SOLUSDT.close', 'SOLUSDT.atr', 'SOLUSDT.history']): any missing
    // required feature is NO_HABITAT, exactly as the Python `_need`.
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if !fm.features.contains_key("history") {
        return no_habitat(expert_id, version, fm.as_of);
    }
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // Kijun (26) plus the previous bar's values must be inside the window for a
    // crossover to be confirmable (warmup is absence, never a value).
    let n = fm.history.len();
    if n < KIJUN_N + 1 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let tk_now = midrange(&fm.history, n - 1, TENKAN_N);
    let kj_now = midrange(&fm.history, n - 1, KIJUN_N);
    let tk_prev = midrange(&fm.history, n - 2, TENKAN_N);
    let kj_prev = midrange(&fm.history, n - 2, KIJUN_N);
    let direction: &str = if tk_now > kj_now && tk_prev <= kj_prev && close > kj_now {
        "LONG"
    } else if tk_now < kj_now && tk_prev >= kj_prev && close < kj_now {
        "SHORT"
    } else {
        return no_setup(expert_id, version, fm.as_of);
    };
    // The crossing predicate reads the per-bar close (bar[4] in the tuple) and
    // the Tenkan/Kijun midranges at the bar's own index — the anchor is the run
    // start of the current consecutive crossing run (D-026).
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = if direction == "LONG" {
        Box::new(move |i, b| {
            i >= 1
                && midrange(&fm.history, i, TENKAN_N) > midrange(&fm.history, i, KIJUN_N)
                && b.close > midrange(&fm.history, i, KIJUN_N)
        })
    } else {
        Box::new(move |i, b| {
            i >= 1
                && midrange(&fm.history, i, TENKAN_N) < midrange(&fm.history, i, KIJUN_N)
                && b.close < midrange(&fm.history, i, KIJUN_N)
        })
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
            ("variant", serde_json::json!("c")),
        ]),
    };
    let fingerprint = format!("{sym}:{direction}:{close:.6}:{tk_now:.6}:{kj_now:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
