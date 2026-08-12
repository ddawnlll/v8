//! rsi_stoch_reversion: evaluate() port — mirror src/v8/experts/rsi_stoch_reversion.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! The parity harness instantiates the Python expert with its default
//! variant_id ('a', RSI-only; D-044), so this port mirrors that evaluate()
//! path: a local Wilder-RSI recompute over the history window (per-bar RSI is
//! not carried in the history tuples), the run-start signal-bar anchor
//! (D-026 — the first bar of the newest consecutive run on the recovered side,
//! NOT `find_setup_anchor`), and the close-beyond-signal-extreme trigger.
//! NO_HABITAT whenever any required feature is missing or the window is too
//! short (< 21 bars), exactly as Python.

use crate::experts::base::*;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["oscillator", "volatility", "history"];

const RSI_OS: f64 = 30.0;
const RSI_OB: f64 = 70.0;

/// `_rsi_value` — mirrored arithmetic (plain IEEE ops, no libm pow).
fn rsi_value(avg_gain: f64, avg_loss: f64) -> f64 {
    if avg_loss == 0.0 {
        return if avg_gain > 0.0 { 100.0 } else { 50.0 };
    }
    if avg_gain == 0.0 {
        return 0.0;
    }
    100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
}

/// `_rsi_per_bar` over the window close series; the first `period` entries are
/// None (a bar needs `period` prior deltas). The seed sums are sequential f64
/// addition (fold from 0.0), matching CPython's builtin `sum`.
fn rsi_per_bar(closes: &[f64], period: usize) -> Vec<Option<f64>> {
    if closes.len() < period + 1 {
        return vec![None; closes.len()];
    }
    let deltas: Vec<f64> = closes.windows(2).map(|w| w[1] - w[0]).collect();
    let gains: Vec<f64> = deltas.iter().map(|d| d.max(0.0)).collect();
    let losses: Vec<f64> = deltas.iter().map(|d| (-d).max(0.0)).collect();
    let mut avg_gain = gains[..period].iter().sum::<f64>() / period as f64;
    let mut avg_loss = losses[..period].iter().sum::<f64>() / period as f64;
    let mut out: Vec<Option<f64>> = vec![None; period];
    out.push(Some(rsi_value(avg_gain, avg_loss)));
    for i in period..deltas.len() {
        avg_gain = (avg_gain * (period as f64 - 1.0) + gains[i]) / period as f64;
        avg_loss = (avg_loss * (period as f64 - 1.0) + losses[i]) / period as f64;
        out.push(Some(rsi_value(avg_gain, avg_loss)));
    }
    out
}

/// `_run_start`: first index of the newest consecutive run where `cond` holds;
/// -1 when the newest bar fails `cond`.
fn run_start(n: usize, cond: impl Fn(usize) -> bool) -> isize {
    if n == 0 {
        return -1;
    }
    let mut i = n - 1;
    if !cond(i) {
        return -1;
    }
    while i > 0 && cond(i - 1) {
        i -= 1;
    }
    i as isize
}

pub fn rsi_stoch_reversion(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // `_need` + habitat: close, atr, history, rsi14 (variant a).
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let rsi_now = match fm.value("rsi14") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // A too-short window rejects outright (len(hist) < 21).
    if fm.history.len() < 21 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let closes: Vec<f64> = fm.history.iter().map(|b| b.close).collect();
    let rsi = rsi_per_bar(&closes, 14);
    let n = rsi.len();

    let mut hit: Option<(&str, usize, f64)> = None;
    // LONG: rsi14 dipped below oversold then rose back above; the signal bar
    // is the run start of the recovered side; trigger = close above its high.
    if rsi_now > RSI_OS && rsi[n - 1].is_some() && rsi[n - 1].unwrap() > RSI_OS {
        let s = run_start(n, |i| rsi[i].is_some() && rsi[i].unwrap() > RSI_OS);
        if s >= 1 && rsi[(s - 1) as usize].is_some() && rsi[(s - 1) as usize].unwrap() <= RSI_OS {
            let signal_high = fm.history[s as usize].high;
            if close > signal_high {
                hit = Some(("LONG", s as usize, signal_high));
            }
        }
    }
    // SHORT: mirror at the overbought level; trigger = close below its low.
    if hit.is_none() && rsi_now < RSI_OB && rsi[n - 1].is_some() && rsi[n - 1].unwrap() < RSI_OB {
        let s = run_start(n, |i| rsi[i].is_some() && rsi[i].unwrap() < RSI_OB);
        if s >= 1 && rsi[(s - 1) as usize].is_some() && rsi[(s - 1) as usize].unwrap() >= RSI_OB {
            let signal_low = fm.history[s as usize].low;
            if close < signal_low {
                hit = Some(("SHORT", s as usize, signal_low));
            }
        }
    }
    let (direction, s, ref_v) = match hit {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let anchor = fm.history[s].event_id.clone();
    // f'{sym}:{variant_id}:{direction}:{ref:.6f}:{close:.6f}'
    let fingerprint = format!("{sym}:a:{direction}:{ref_v:.6}:{close:.6}");
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(1.0)),
            ("stop_r", serde_json::json!(1.0)),
            ("expiry_bars", serde_json::json!(8)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!("a")),
        ]),
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
