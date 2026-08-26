//! divergence_12_setups: evaluate() port target (issue #81) — mirror src/v8/experts/divergence_12_setups.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//! Variant 'a' (bearish standard divergence, SHORT) is the evaluated default —
//! the Python lab instantiates the expert with no variant argument and the
//! Rust dispatch carries no variant parameter. Variant 'b' is unported.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::{fsum, HistBar};

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["oscillator", "location", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const _STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

// Declared, LOCKED constants (D-036). SWING_N is 5, NOT 10 — the frozen
// 32-bar history window makes a strength-10 divergence pair structurally
// unobservable (module docstring); the local lattice cross-checks against the
// state's swing_high_5/swing_low_5 features.
const SWING_N: usize = 5;
const SWING_SIGNIFICANCE_K: f64 = 1.0; // CRIT-1 / Ch27.2 p858-859 range filter
const RSI_PERIOD: usize = 14; // G-08 rsi14 lookback

/// Python `_rsi_value` — 100 - 100/(1 + gain/loss) with the degenerate cases.
fn rsi_value(avg_gain: f64, avg_loss: f64) -> f64 {
    if avg_loss == 0.0 {
        return if avg_gain > 0.0 { 100.0 } else { 50.0 };
    }
    if avg_gain == 0.0 {
        return 0.0;
    }
    100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
}

/// Python `_rsi_per_bar` — Wilder RSI per bar, None before the seed (a bar
/// needs `period` prior deltas). The seed averages are Python `sum()` over
/// floats, i.e. compensated summation (fsum).
fn rsi_per_bar(closes: &[f64]) -> Vec<Option<f64>> {
    if closes.len() < RSI_PERIOD + 1 {
        return vec![None; closes.len()];
    }
    let period = RSI_PERIOD as f64;
    let mut gains = Vec::with_capacity(closes.len() - 1);
    let mut losses = Vec::with_capacity(closes.len() - 1);
    for w in closes.windows(2) {
        let d = w[1] - w[0];
        gains.push(d.max(0.0));
        losses.push((-d).max(0.0));
    }
    let mut avg_gain = fsum(&gains[..RSI_PERIOD]) / period;
    let mut avg_loss = fsum(&losses[..RSI_PERIOD]) / period;
    let mut out: Vec<Option<f64>> = vec![None; RSI_PERIOD];
    out.push(Some(rsi_value(avg_gain, avg_loss)));
    for i in RSI_PERIOD..gains.len() {
        avg_gain = (avg_gain * (period - 1.0) + gains[i]) / period;
        avg_loss = (avg_loss * (period - 1.0) + losses[i]) / period;
        out.push(Some(rsi_value(avg_gain, avg_loss)));
    }
    out
}

/// Python `_lattice` — confirmed significant pivot highs/lows (G-21 + CRIT-1,
/// Ch27.2 p858-859): index p is a pivot when both n-bar flanks are closed and
/// its range passes the significance filter (>= k*ATR).
fn lattice(
    highs: &[f64],
    lows: &[f64],
    n: usize,
    atr: f64,
) -> (Vec<(usize, f64)>, Vec<(usize, f64)>) {
    let mut peaks = Vec::new();
    let mut troughs = Vec::new();
    let mut i = n;
    while i + n < highs.len() {
        let hi = highs[i];
        let flank_max = highs[i - n..i]
            .iter()
            .chain(highs[i + 1..i + 1 + n].iter())
            .copied()
            .fold(f64::NEG_INFINITY, f64::max);
        if hi > flank_max && hi - lows[i] >= SWING_SIGNIFICANCE_K * atr {
            peaks.push((i, hi));
        }
        let lo = lows[i];
        let flank_min = lows[i - n..i]
            .iter()
            .chain(lows[i + 1..i + 1 + n].iter())
            .copied()
            .fold(f64::INFINITY, f64::min);
        if lo < flank_min && highs[i] - lo >= SWING_SIGNIFICANCE_K * atr {
            troughs.push((i, lo));
        }
        i += 1;
    }
    (peaks, troughs)
}

/// Python `_setup_at` variant 'a' — the FULL observable setup at bar i:
/// bearish standard divergence (price higher high at peak2 vs peak1 while rsi
/// makes a lower high) AND close-through confirmation (close below the
/// intervening swing low). Uses only pivots confirmed by bar i (p + SWING_N
/// <= i). Returns (barrier, extremum) or None.
fn setup_at(
    closes: &[f64],
    highs: &[f64],
    lows: &[f64],
    rsi: &[Option<f64>],
    peaks: &[(usize, f64)],
    troughs: &[(usize, f64)],
    i: usize,
) -> Option<(&'static str, f64, f64)> {
    // 1. Bearish Divergence (SHORT): Price HH, RSI LH, close breaks below intervening swing low
    let conf_peaks: Vec<&(usize, f64)> = peaks.iter().filter(|(p, _)| p + SWING_N <= i).collect();
    if conf_peaks.len() >= 2 {
        let (i1, p1) = *conf_peaks[conf_peaks.len() - 2];
        let (i2, p2) = *conf_peaks[conf_peaks.len() - 1];
        if p2 > p1 {
            if let (Some(r1), Some(r2)) = (rsi[i1], rsi[i2]) {
                if r2 < r1 && i2 > i1 + 1 {
                    let barrier = lows[i1 + 1..i2]
                        .iter()
                        .copied()
                        .fold(f64::INFINITY, f64::min);
                    if closes[i] < barrier {
                        return Some(("SHORT", barrier, p2));
                    }
                }
            }
        }
    }

    // 2. Bullish Divergence (LONG): Price LL, RSI HL, close reclaims above intervening swing high
    let conf_troughs: Vec<&(usize, f64)> = troughs.iter().filter(|(p, _)| p + SWING_N <= i).collect();
    if conf_troughs.len() >= 2 {
        let (i1, t1) = *conf_troughs[conf_troughs.len() - 2];
        let (i2, t2) = *conf_troughs[conf_troughs.len() - 1];
        if t2 < t1 {
            if let (Some(r1), Some(r2)) = (rsi[i1], rsi[i2]) {
                if r2 > r1 && i2 > i1 + 1 {
                    let barrier = highs[i1 + 1..i2]
                        .iter()
                        .copied()
                        .fold(f64::NEG_INFINITY, f64::max);
                    if closes[i] > barrier {
                        return Some(("LONG", barrier, t2));
                    }
                }
            }
        }
    }

    None
}

fn setup_at_v1(
    closes: &[f64],
    lows: &[f64],
    rsi: &[Option<f64>],
    peaks: &[(usize, f64)],
    i: usize,
) -> Option<(f64, f64)> {
    let conf: Vec<&(usize, f64)> = peaks.iter().filter(|(p, _)| p + SWING_N <= i).collect();
    if conf.len() < 2 {
        return None;
    }
    let (i1, p1) = *conf[conf.len() - 2];
    let (i2, p2) = *conf[conf.len() - 1];
    if !(p2 > p1) {
        return None;
    }
    let r1 = rsi[i1]?;
    let r2 = rsi[i2]?;
    if !(r2 < r1) {
        return None;
    }
    if i2 <= i1 + 1 {
        return None;
    }
    let barrier = lows[i1 + 1..i2]
        .iter()
        .copied()
        .fold(f64::INFINITY, f64::min);
    if closes[i] >= barrier {
        return None;
    }
    Some((barrier, p2))
}

pub fn divergence_12_setups(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // Python `_need` over the six bare feature names (S1 parity emission).
    if fm.value("close").is_none()
        || fm.value("atr").is_none()
        || fm.value("rsi14").is_none()
        || fm.value("swing_high_5").is_none()
        || fm.value("swing_low_5").is_none()
        || fm.features.get("history").is_none()
    {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let atr = fm.value("atr").unwrap();
    if atr <= 0.0 || fm.history.len() < 2 * SWING_N + 1 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let closes: Vec<f64> = fm.history.iter().map(|b| b.close).collect();
    let highs: Vec<f64> = fm.history.iter().map(|b| b.high).collect();
    let lows: Vec<f64> = fm.history.iter().map(|b| b.low).collect();
    let rsi = rsi_per_bar(&closes);

    if version == "v1" {
        let (peaks, _troughs) = lattice(&highs, &lows, SWING_N, atr);
        let n = closes.len();
        let (barrier, extremum) = match setup_at_v1(&closes, &lows, &rsi, &peaks, n - 1) {
            Some(hit) => hit,
            None => return no_setup(expert_id, version, fm.as_of),
        };
        let sw = match fm.value("swing_high_5") {
            Some(v) => v,
            None => return no_habitat(expert_id, version, fm.as_of),
        };
        if sw != 0.0 && (extremum - sw).abs() > 1e-9 {
            return no_setup(expert_id, version, fm.as_of);
        }
        let pred = |i: usize, _bar: &HistBar| setup_at_v1(&closes, &lows, &rsi, &peaks, i).is_some();
        let anchor = find_setup_anchor(&fm.history, &pred);
        let mut geo = geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(1.0)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!("a")),
            ("barrier_ref", serde_json::json!(barrier)),
            ("extremum_ref", serde_json::json!(extremum)),
        ]);
        geo.insert("prior_high_ref".into(), serde_json::json!(extremum));
        let draft = Draft {
            direction: "SHORT".into(),
            birth_time: fm.as_of,
            risk_geometry: geo,
        };
        let fingerprint = format!("{sym}:a:SHORT:{barrier:.6}:{extremum:.6}");
        return candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint);
    }
    let (peaks, troughs) = lattice(&highs, &lows, SWING_N, atr);
    let n = closes.len();
    let (direction, barrier, extremum) = match setup_at(&closes, &highs, &lows, &rsi, &peaks, &troughs, n - 1) {
        Some(hit) => hit,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let pred = |i: usize, _bar: &HistBar| {
        setup_at(&closes, &highs, &lows, &rsi, &peaks, &troughs, i)
            .map(|(d, _, _)| d == direction)
            .unwrap_or(false)
    };
    let anchor = find_setup_anchor(&fm.history, &pred);
    let close = closes[n - 1];
    let raw_stop_r = (close - extremum).abs() / atr;
    let stop_r = raw_stop_r.clamp(0.8, 2.0);

    let mut geo = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(TARGET_R)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!("v2")),
        ("barrier_ref", serde_json::json!(barrier)),
        ("extremum_ref", serde_json::json!(extremum)),
    ]);
    if direction == "SHORT" {
        geo.insert("prior_high_ref".into(), serde_json::json!(extremum));
    } else {
        geo.insert("prior_low_ref".into(), serde_json::json!(extremum));
    }
    let draft = Draft {
        direction: direction.into(),
        birth_time: fm.as_of,
        risk_geometry: geo,
    };
    let fingerprint = format!("{sym}:v2:{direction}:{barrier:.6}:{extremum:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
