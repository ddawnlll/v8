//! macd_stoch_trend: evaluate() port target (issue #91) — mirror src/v8/experts/macd_stoch_trend.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Stoch crossover (stoch_k crosses stoch_d) filtered by the MACD zero line
//! (macd > 0 long / macd < 0 short). The setup anchor is the crossing bar —
//! the first bar of the current consecutive run where the crossing state holds
//! (D-026 run-start semantics via the local `_run_start` helper, NOT
//! `find_setup_anchor`). stoch_k/stoch_d are window-stationary so the local
//! series over the history window equals the state features at the newest bar.

use crate::experts::base::*;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["oscillator", "volatility", "history"];

/// Mirror of `_stoch_k_d`: per-bar fast %K and %D = SMA3(%K). Flat 14-bar
/// window -> %K = 50.0 (G-09; identical formula to marketstate's stoch).
fn stoch_k_d(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> (Vec<f64>, Vec<f64>) {
    let mut ks = Vec::with_capacity(closes.len());
    for i in 0..closes.len() {
        let lo = i.saturating_sub(period - 1);
        let mut h14 = f64::NEG_INFINITY;
        let mut l14 = f64::INFINITY;
        for &h in &highs[lo..=i] {
            h14 = h14.max(h);
        }
        for &l in &lows[lo..=i] {
            l14 = l14.min(l);
        }
        if h14 == l14 {
            ks.push(50.0);
        } else {
            ks.push((closes[i] - l14) / (h14 - l14) * 100.0);
        }
    }
    let mut ds = Vec::with_capacity(closes.len());
    for i in 0..closes.len() {
        let lo = i.saturating_sub(2);
        let win = &ks[lo..=i];
        // Python builtin sum (left-to-right, not fsum).
        let sum: f64 = win.iter().sum();
        ds.push(sum / win.len() as f64);
    }
    (ks, ds)
}

/// Mirror of `_run_start(cond, n)`: index of the first bar of the consecutive
/// run ending at the newest bar in which `above` (ks > ds, LONG) or `below`
/// (ks < ds, SHORT) holds; -1 when the newest bar does not hold the predicate.
fn run_start(ks: &[f64], ds: &[f64], n: usize, above: bool) -> i64 {
    let i = n as i64 - 1;
    let holds = |j: usize| if above { ks[j] > ds[j] } else { ks[j] < ds[j] };
    if i < 0 || !holds(i as usize) {
        return -1;
    }
    let mut s = i;
    while s > 0 && holds((s - 1) as usize) {
        s -= 1;
    }
    s
}

pub fn macd_stoch_trend(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // `_need`: all required feature keys present (prefixed in Python; the Rust
    // state keys are bare names).
    for name in ["close", "stoch_k", "stoch_d", "macd", "macd_signal", "macd_hist", "atr", "history"] {
        if !fm.features.contains_key(name) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = fm.value("atr");
    let macd = fm.value("macd");
    let k_now = fm.value("stoch_k");
    let d_now = fm.value("stoch_d");
    if atr.is_none() || macd.is_none() || k_now.is_none() || d_now.is_none() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let atr = atr.unwrap();
    let macd = macd.unwrap();
    let k_now = k_now.unwrap();
    let d_now = d_now.unwrap();
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let hist = &fm.history;
    if hist.len() < 17 {
        // The crossing needs %K/%D seeds inside the window (14+3 bars).
        return no_habitat(expert_id, version, fm.as_of);
    }
    let closes: Vec<f64> = hist.iter().map(|b| b.close).collect();
    let highs: Vec<f64> = hist.iter().map(|b| b.high).collect();
    let lows: Vec<f64> = hist.iter().map(|b| b.low).collect();
    let (ks, ds) = stoch_k_d(&highs, &lows, &closes, 14);
    let n = ks.len();
    let mut direction: Option<&str> = None;
    let mut s: i64 = -1;
    if macd > 0.0 && k_now > d_now && ks[n - 1] > ds[n - 1] {
        s = run_start(&ks, &ds, n, true);
        if s >= 1 && ks[(s - 1) as usize] <= ds[(s - 1) as usize] {
            direction = Some("LONG");
        }
    } else if macd < 0.0 && k_now < d_now && ks[n - 1] < ds[n - 1] {
        s = run_start(&ks, &ds, n, false);
        if s >= 1 && ks[(s - 1) as usize] >= ds[(s - 1) as usize] {
            direction = Some("SHORT");
        }
    }
    let direction = match direction {
        Some(d) => d,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let anchor = hist[s as usize].event_id.clone();
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
    let fingerprint = format!("{sym}:{direction}:{k_now:.6}:{d_now:.6}:{close:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
