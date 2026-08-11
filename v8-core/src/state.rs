//! FeatureStore + StateView (COMPUTE_CORE_SPEC §4; MARKET_STATE_CONTRACT).
//!
//! `FeatureStore` precomputes every per-symbol series once (the Rust mirror of
//! `marketstate.build_bar_series`), and `StateView::at(t)` reads the features
//! at bar count `t` from those arrays — the mirror of the cached path in
//! `build_state`, which `tests/test_state_cache_identity.py` pins byte-identical
//! to the uncached reference. Porting the cached path is therefore porting the
//! oracle's emitted values.
//!
//! Determinism rules (COMPUTE_SCHEDULING_SPEC §5):
//! - every reduction is a fixed left-to-right fold, in the exact order CPython
//!   evaluates it (no `Iterator::sum`, no pairwise summation);
//! - `f64` throughout, no FMA contraction (crate-wide `--fp-contract=off`);
//! - identities use the V8.2 bit encoding (`hash::Canon`), never decimal text
//!   (PARITY_AND_IDENTITY_SPEC §4).
//!
//! Parity (the S1 gate) compares VALUES, not hashes; `input_lineage_hash` and
//! the V8.2 `lineage_hash`/`state_id` are excluded from the comparison by
//! PARITY_AND_IDENTITY_SPEC §3 but computed here for identity semantics.

use crate::data::{Dataset, SymbolBars};
use crate::hash::Canon;

pub const HOUR_NS: i64 = 3_600_000_000_000;
pub const DAY_NS: i64 = 86_400_000_000_000;

// Declared-never-fitted constants (D-036), mirroring marketstate.py.
pub const HISTORY_DEPTH_DEFAULT: usize = 32;
pub const ATR_FILTER_BAND_N: usize = 20;
pub const STARC_K: f64 = 2.0;
pub const ATR_SLOPE_N: usize = 10;
pub const ATR_BAND_STOP_K: f64 = 2.0;
pub const SWING_NS: [usize; 3] = [5, 10, 20];
pub const WINDOW_NS: [usize; 3] = [10, 20, 50];
pub const SWING_SIGNIFICANCE_K: f64 = 1.0;
pub const FIB_RETRACEMENTS: [f64; 5] = [0.236, 0.382, 0.5, 0.618, 0.786];
pub const FIB_EXTENSIONS: [f64; 10] =
    [1.0, 1.272, 1.618, 2.0, 2.618, 3.0, 3.618, 4.0, 4.236, 4.618];
pub const BARS_PER_DAY: usize = 24;
pub const CONSOLIDATION_BARS: usize = 20;
pub const CONSOLIDATION_WIDTH_MAX: f64 = 0.03;
pub const GAP_ZONE_BARS: usize = 50;
#[allow(dead_code)] // declared constant mirror (marketstate.py MOM_N)
pub const MOM_N: usize = 14;
pub const OBOS_QUANTILE_WINDOW: usize = 100;
pub const VOLUME_STAT_N: usize = 100;
pub const VOLUME_SMA_N: usize = 20;
pub const CMF_N: usize = 20;
pub const BAR_CLASS_N: usize = 100;
pub const IMPULSIVE_START_HOUR: i64 = 8;
pub const IMPULSIVE_END_HOUR: i64 = 17;

/// The fixed, declared feature-name vocabulary (FEATURE_GROUPS in schema.py),
/// in deterministic sorted order. Positioning features are absent (not emitted)
/// when the tape lacks the channel; warmup-gated features are ABSENT until
/// their window is satisfied — absence is never zero (MARKET_STATE_CONTRACT §4).
pub const FEATURE_NAMES: [&str; 77] = [
    "adl", "adx14", "atr", "atr_2sigma_active", "atr_band_stop",
    "atr_filtered_2sigma", "atr_locational", "atr_trend_phase", "bar_class",
    "bar_of_session", "bb_bandwidth", "bb_lower", "bb_mid", "bb_pct_b",
    "bb_upper", "body_range_ratio", "cci20", "close", "close_position",
    "cmf_20", "consolidation_range", "day_index", "ema_fast", "ema_slow",
    "fib_levels", "funding_rate", "gap_dir", "gap_levels", "gap_size",
    "history", "hour_of_day_utc", "impulsive_window", "inside_bar",
    "keltner_l", "keltner_u", "long_short_skew", "lower_shadow", "macd",
    "macd_hist", "macd_signal", "mom_14", "obv", "open_interest",
    "osc_obos_quantile", "outside_bar", "pivot_points_day", "prior_high",
    "prior_low", "range_height_10", "range_height_20", "range_height_50",
    "real_body", "roc_14", "rsi14", "starc_l", "starc_u", "stoch_d", "stoch_k",
    "stochrsi", "swing_high_10", "swing_high_20", "swing_high_5",
    "swing_low_10", "swing_low_20", "swing_low_5", "upper_shadow",
    "vol_min_proximity", "vol_smooth_ma", "vol_zscore", "volume", "vwap",
    "window_high_10", "window_high_20", "window_high_50", "window_low_10",
    "window_low_20", "window_low_50",
];

/// Group tags per feature (FEATURE_TO_GROUP in schema.py).
pub fn feature_group(name: &str) -> &'static str {
    match name {
        "close" => "raw",
        "ema_fast" | "ema_slow" => "trend",
        "atr" | "bb_mid" | "bb_upper" | "bb_lower" | "bb_pct_b"
        | "bb_bandwidth" | "atr_locational" | "atr_filtered_2sigma"
        | "atr_2sigma_active" | "keltner_u" | "keltner_l" | "starc_u"
        | "starc_l" | "atr_trend_phase" => "volatility",
        "prior_high" | "prior_low" | "swing_high_5" | "swing_high_10"
        | "swing_high_20" | "swing_low_5" | "swing_low_10" | "swing_low_20"
        | "window_high_10" | "window_low_10" | "window_high_20"
        | "window_low_20" | "window_high_50" | "window_low_50"
        | "range_height_10" | "range_height_20" | "range_height_50"
        | "fib_levels" | "pivot_points_day" | "consolidation_range"
        | "gap_levels" | "atr_band_stop" => "location",
        "real_body" | "body_range_ratio" | "upper_shadow" | "lower_shadow"
        | "close_position" | "inside_bar" | "outside_bar" | "gap_size"
        | "gap_dir" => "candle_shape",
        "rsi14" | "stoch_k" | "stoch_d" | "stochrsi" | "cci20" | "macd"
        | "macd_signal" | "macd_hist" | "mom_14" | "roc_14" | "adx14"
        | "osc_obos_quantile" => "oscillator",
        "volume" | "vol_zscore" | "vol_min_proximity" | "vol_smooth_ma"
        | "obv" | "adl" | "cmf_20" | "vwap" | "bar_class" => "participation",
        "hour_of_day_utc" | "impulsive_window" | "bar_of_session"
        | "day_index" => "session",
        "funding_rate" | "open_interest" | "long_short_skew" => "positioning",
        "history" => "history",
        _ => "raw",
    }
}

/// Features whose value is structured (tuple), not a scalar float.
pub fn feature_dtype(name: &str) -> &'static str {
    match name {
        "history" => "history",
        "fib_levels" => "fib_levels",
        "pivot_points_day" => "pivot_points",
        "consolidation_range" => "consolidation",
        "gap_levels" => "gap_levels",
        _ => "float",
    }
}

fn sma(values: &[f64], period: usize) -> f64 {
    mean(&values[values.len() - period..])
}

/// Compensated summation, bit-identical to CPython's `sum()`/`math.fsum`
/// (`_PyFloat_Fsum` partials algorithm). CPython 3.12+ uses this for floats,
/// NOT a left fold — a left fold drifts by ulps on ~20-element windows
/// (measured), so every reduction mirroring a Python `sum(...)` must go
/// through this. Reductions that mirror explicit `+=` loops (vwap, cmf,
/// obv, adl) stay plain folds.
pub fn fsum(values: &[f64]) -> f64 {
    let mut partials: Vec<f64> = Vec::with_capacity(32);
    for &x0 in values {
        let mut x = x0;
        let mut i = 0usize;
        let n = partials.len();
        for j in 0..n {
            let y = partials[j];
            let (a, b) = if x.abs() < y.abs() { (y, x) } else { (x, y) };
            let hi = a + b;
            let yr = hi - a;
            let lo = b - yr;
            if lo != 0.0 {
                partials[i] = lo;
                i += 1;
            }
            x = hi;
        }
        partials.truncate(i);
        if x != 0.0 {
            partials.push(x);
        }
    }
    // Final fold, exactly CPython's math_fsum: take the largest partial first,
    // walk down, STOP at the first inexact addition, then the half-even tie
    // fix (sum([1e-16, 1, 1e16]) must round the last digit UP to two).
    let mut hi = 0.0;
    let mut n = partials.len();
    let mut lo = 0.0;
    if n > 0 {
        n -= 1;
        hi = partials[n];
        while n > 0 {
            let x = hi;
            n -= 1;
            let y = partials[n];
            debug_assert!(y.abs() < x.abs());
            hi = x + y;
            let yr = hi - x;
            lo = y - yr;
            if lo != 0.0 {
                break;
            }
        }
        if n > 0 && ((lo < 0.0 && partials[n - 1] < 0.0)
            || (lo > 0.0 && partials[n - 1] > 0.0))
        {
            let y = lo * 2.0;
            let x = hi + y;
            let yr = x - hi;
            if y == yr {
                hi = x;
            }
        }
    }
    hi
}

fn mean(values: &[f64]) -> f64 {
    // CPython `_mean` = `sum(values) / len(values)` — sum() is compensated.
    fsum(values) / values.len() as f64
}

fn std_pop(values: &[f64]) -> f64 {
    let m = mean(values);
    let mut acc = Vec::with_capacity(values.len());
    for v in values {
        let d = v - m;
        // CPython `(v - m) ** 2` calls libm pow(x, 2.0), which is not always
        // bit-identical to x*x. f64::powf calls the same platform libm, but
        // LLVM folds pow(x, 2.0) -> x*x in release (which changes the last
        // ulp); black_box keeps the exponent opaque so the libm call survives
        // (COMPUTE_SCHEDULING_SPEC §5: an optimization may not change a value).
        acc.push(d.powf(std::hint::black_box(2.0)));
    }
    let sos = fsum(&acc);
    // CPython `_std_pop` finishes with `** 0.5`, which is libm pow(x, 0.5) —
    // measured to differ from sqrt(x) by 1 ulp on some values. black_box keeps
    // the exponent opaque so LLVM cannot fold pow(x, 0.5) -> sqrt.
    (sos / values.len() as f64).powf(std::hint::black_box(0.5))
}


fn typical(highs: &[f64], lows: &[f64], closes: &[f64]) -> Vec<f64> {
    highs.iter().zip(lows).zip(closes).map(|((h, l), c)| (h + l + c) / 3.0).collect()
}

fn percentile_rank(values: &[f64], current: f64) -> f64 {
    let mut n = 0.0;
    for v in values {
        if *v <= current {
            n += 1.0;
        }
    }
    n / values.len() as f64
}

fn ema(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    let k = 2.0 / (period as f64 + 1.0);
    let mut out = Vec::with_capacity(values.len());
    out.push(values[0]);
    for v in &values[1..] {
        let prev = out[out.len() - 1];
        out.push(v * k + prev * (1.0 - k));
    }
    out
}

fn rsi_value(avg_gain: f64, avg_loss: f64) -> f64 {
    if avg_loss == 0.0 {
        return if avg_gain > 0.0 { 100.0 } else { 50.0 };
    }
    if avg_gain == 0.0 {
        return 0.0;
    }
    100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
}

/// Wilder RSI over the full close series (G-08).
fn rsi_series(closes: &[f64], period: usize) -> Vec<f64> {
    if closes.len() < period + 1 {
        return Vec::new();
    }
    let mut gains = Vec::with_capacity(closes.len() - 1);
    let mut losses = Vec::with_capacity(closes.len() - 1);
    for i in 1..closes.len() {
        let d = closes[i] - closes[i - 1];
        gains.push(d.max(0.0));
        losses.push((-d).max(0.0));
    }
    let mut avg_gain = fsum(&gains[..period]) / period as f64;
    let mut avg_loss = fsum(&losses[..period]) / period as f64;
    let mut out = vec![rsi_value(avg_gain, avg_loss)];
    for i in period..gains.len() {
        avg_gain = (avg_gain * (period as f64 - 1.0) + gains[i]) / period as f64;
        avg_loss = (avg_loss * (period as f64 - 1.0) + losses[i]) / period as f64;
        out.push(rsi_value(avg_gain, avg_loss));
    }
    out
}

/// Fast stochastic %K/%D over the trailing window (G-09); flat window -> 50.0.
fn stoch(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> (f64, f64) {
    let n = closes.len();
    let mut ks = Vec::with_capacity(3);
    for i in (n - 3)..n {
        let h14 = highs[i + 1 - period..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let l14 = lows[i + 1 - period..=i].iter().cloned().fold(f64::INFINITY, f64::min);
        if h14 == l14 {
            ks.push(50.0);
        } else {
            ks.push((closes[i] - l14) / (h14 - l14) * 100.0);
        }
    }
    let d = fsum(&ks) / 3.0;
    (ks[2], d)
}

fn stochrsi_from(rsis: &[f64], period: usize) -> f64 {
    let window = &rsis[rsis.len() - period..];
    let lo = window.iter().cloned().fold(f64::INFINITY, f64::min);
    let hi = window.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    if hi == lo {
        return 0.5;
    }
    (rsis[rsis.len() - 1] - lo) / (hi - lo)
}

fn dx_value(atr: f64, pdi: f64, ndi: f64) -> f64 {
    if atr <= 0.0 {
        return 0.0;
    }
    let pdi_p = 100.0 * pdi / atr;
    let ndi_p = 100.0 * ndi / atr;
    if pdi_p + ndi_p == 0.0 {
        return 0.0;
    }
    100.0 * (pdi_p - ndi_p).abs() / (pdi_p + ndi_p)
}

/// Wilder DMI ADX value at every bar index (G-14), 0.0 until 2*period bars.
fn adx_series(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    let mut out = vec![0.0; n];
    if n < 2 * period {
        return out;
    }
    let mut trs = Vec::with_capacity(n - 1);
    let mut pdms = Vec::with_capacity(n - 1);
    let mut ndms = Vec::with_capacity(n - 1);
    for i in 1..n {
        let h = highs[i];
        let l = lows[i];
        let pc = closes[i - 1];
        trs.push((h - l).max((h - pc).abs()).max((l - pc).abs()));
        let up = highs[i] - highs[i - 1];
        let dn = lows[i - 1] - lows[i];
        pdms.push(if up > dn && up > 0.0 { up } else { 0.0 });
        ndms.push(if dn > up && dn > 0.0 { dn } else { 0.0 });
    }
    let mut atr_w = fsum(&trs[..period]);
    let mut pdi_w = fsum(&pdms[..period]);
    let mut ndi_w = fsum(&ndms[..period]);
    let mut dxs = vec![dx_value(atr_w, pdi_w, ndi_w)];
    for i in period..trs.len() {
        atr_w = atr_w - atr_w / period as f64 + trs[i];
        pdi_w = pdi_w - pdi_w / period as f64 + pdms[i];
        ndi_w = ndi_w - ndi_w / period as f64 + ndms[i];
        dxs.push(dx_value(atr_w, pdi_w, ndi_w));
    }
    let mut adx = fsum(&dxs[..period]) / period as f64;
    out[2 * period - 1] = adx;
    for j in period..dxs.len() {
        adx = (adx * (period as f64 - 1.0) + dxs[j]) / period as f64;
        out[period + j] = adx;
    }
    out
}

/// Simple-mean ATR over rolling `period`-bar windows; starts at bar period-1.
fn atr_series(highs: &[f64], lows: &[f64], period: usize) -> Vec<f64> {
    let mut out = Vec::with_capacity(highs.len().saturating_sub(period - 1));
    let mut window = Vec::with_capacity(period);
    for i in (period - 1)..highs.len() {
        window.clear();
        // (i + 1 - period) avoids usize underflow when i == period - 1
        // (i - period + 1 would evaluate i - period first and panic in debug).
        for j in (i + 1 - period)..=i {
            window.push(highs[j] - lows[j]);
        }
        out.push(fsum(&window) / period as f64);
    }
    out
}

fn obv_series(closes: &[f64], volumes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let mut out = vec![0.0; n];
    let mut acc = 0.0;
    for i in 1..n {
        if closes[i] > closes[i - 1] {
            acc += volumes[i];
        } else if closes[i] < closes[i - 1] {
            acc -= volumes[i];
        }
        out[i] = acc;
    }
    out
}

fn adl_series(highs: &[f64], lows: &[f64], closes: &[f64], volumes: &[f64]) -> Vec<f64> {
    let n = closes.len();
    let mut out = vec![0.0; n];
    let mut acc = 0.0;
    for i in 0..n {
        let rng = highs[i] - lows[i];
        if rng > 0.0 {
            acc += ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng * volumes[i];
        }
        out[i] = acc;
    }
    out
}

/// All confirmed strength-n pivot bars in the full series: (idx, value, range).
fn pivot_lists(highs: &[f64], lows: &[f64], n: usize) -> (Vec<(usize, f64, f64)>, Vec<(usize, f64, f64)>) {
    let mut hi = Vec::new();
    let mut lo = Vec::new();
    let mut i = n;
    while i + n < highs.len() {
        let h = highs[i];
        let l = lows[i];
        let mut hmax = f64::NEG_INFINITY;
        for j in (i - n)..i {
            if highs[j] > hmax {
                hmax = highs[j];
            }
        }
        for j in (i + 1)..(i + 1 + n) {
            if highs[j] > hmax {
                hmax = highs[j];
            }
        }
        if h > hmax {
            hi.push((i, h, h - l));
        }
        let mut lmin = f64::INFINITY;
        for j in (i - n)..i {
            if lows[j] < lmin {
                lmin = lows[j];
            }
        }
        for j in (i + 1)..(i + 1 + n) {
            if lows[j] < lmin {
                lmin = lows[j];
            }
        }
        if l < lmin {
            lo.push((i, l, highs[i] - l));
        }
        i += 1;
    }
    (hi, lo)
}

fn last_significant_pivot(pivs: &[(usize, f64, f64)], t: usize, n: usize,
                          atr_now: f64, k: f64) -> Option<(usize, f64)> {
    let limit = t as i64 - 1 - n as i64;
    for (idx, val, rng) in pivs.iter().rev() {
        if *idx as i64 > limit {
            continue;
        }
        if *rng >= k * atr_now {
            return Some((*idx, *val));
        }
    }
    None
}

fn last_confirmed_swing(pivs: &[(usize, f64, f64)], t: usize, n: usize) -> Option<(usize, f64)> {
    let limit = t as i64 - 1 - n as i64;
    for (idx, val, _) in pivs.iter().rev() {
        if *idx as i64 <= limit {
            return Some((*idx, *val));
        }
    }
    None
}

fn fib_levels(swing_high: Option<(usize, f64)>, swing_low: Option<(usize, f64)>) -> Option<(f64, f64, Vec<(f64, f64)>, Vec<(f64, f64)>)> {
    let (i_h, h) = swing_high?;
    let (i_l, l) = swing_low?;
    let (extreme, origin, rng, direction) = if i_h > i_l {
        (h, l, h - l, 1.0)
    } else {
        (l, h, h - l, -1.0)
    };
    if rng <= 0.0 {
        return None;
    }
    let retr: Vec<(f64, f64)> = FIB_RETRACEMENTS
        .iter()
        .map(|r| (*r, extreme - direction * r * rng))
        .collect();
    let ext: Vec<(f64, f64)> = FIB_EXTENSIONS
        .iter()
        .map(|r| (*r, origin + direction * r * rng))
        .collect();
    Some((extreme, direction, retr, ext))
}

fn consolidation_range(highs: &[f64], lows: &[f64], closes: &[f64],
                       m: usize, width_max: f64) -> (f64, f64, f64, f64) {
    let h_ref = highs[highs.len() - m - 1..highs.len() - 1].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let l_ref = lows[lows.len() - m - 1..lows.len() - 1].iter().cloned().fold(f64::INFINITY, f64::min);
    let width = h_ref - l_ref;
    let width_ratio = if closes[closes.len() - 1] != 0.0 { width / closes[closes.len() - 1] } else { 0.0 };
    let inside = if l_ref <= closes[closes.len() - 1] && closes[closes.len() - 1] <= h_ref { 1.0 } else { 0.0 };
    let is_active = if inside == 1.0 && width_ratio <= width_max { 1.0 } else { 0.0 };
    (h_ref, l_ref, width_ratio, is_active)
}

fn gap_levels(opens: &[f64], highs: &[f64], lows: &[f64], closes: &[f64], n: usize) -> Vec<(f64, f64, f64)> {
    let mut zones = Vec::new();
    let start = 1usize.max(opens.len().saturating_sub(n));
    for t in start..opens.len() {
        let o = opens[t];
        let ph = highs[t - 1];
        let pl = lows[t - 1];
        let (top, bottom, d) = if o > ph {
            (o, ph, 1.0)
        } else if o < pl {
            (pl, o, -1.0)
        } else {
            continue;
        };
        let mut filled = false;
        for j in (t + 1)..closes.len() {
            if closes[j] >= bottom && closes[j] <= top {
                filled = true;
                break;
            }
        }
        if !filled {
            zones.push((top, bottom, d));
        }
    }
    zones
}

fn cmf(highs: &[f64], lows: &[f64], closes: &[f64], volumes: &[f64], period: usize) -> f64 {
    let n = closes.len();
    let mut mf_sum = 0.0;
    let mut vol_sum = 0.0;
    for i in (n - period)..n {
        let rng = highs[i] - lows[i];
        if rng > 0.0 {
            mf_sum += ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng * volumes[i];
        }
        vol_sum += volumes[i];
    }
    if vol_sum == 0.0 {
        return 0.0;
    }
    mf_sum / vol_sum
}

fn hour_utc(event_time_ns: i64) -> i64 {
    (event_time_ns.div_euclid(HOUR_NS)) % 24
}

fn bar_of_session(event_time_ns: i64) -> i64 {
    (event_time_ns % DAY_NS).div_euclid(HOUR_NS) + 1
}

fn day_index(event_time_ns: i64) -> i64 {
    event_time_ns.div_euclid(DAY_NS)
}

fn bar_class(opens: &[f64], closes: &[f64], highs: &[f64], lows: &[f64],
             volumes: &[f64], lookback: usize) -> f64 {
    let n = closes.len();
    let mut ranges = Vec::with_capacity(n.min(BAR_CLASS_N));
    for i in (n - BAR_CLASS_N)..n {
        ranges.push(highs[i] - lows[i]);
    }
    let range_pct = percentile_rank(&ranges, highs[n - 1] - lows[n - 1]);
    let vol_pct = percentile_rank(&volumes[n - BAR_CLASS_N..], volumes[n - 1]);
    let up_trend = closes[n - 1] > closes[n - 1 - lookback];
    let reversal = (up_trend && closes[n - 1] < opens[n - 1])
        || (!up_trend && closes[n - 1] > opens[n - 1]);
    let high_vol = if vol_pct >= 0.8 || range_pct >= 0.8 { 1.0 } else { 0.0 };
    if high_vol == 1.0 {
        return if reversal == false { 3.0 } else { 1.0 };
    }
    if reversal == false { 0.0 } else { 2.0 }
}

/// Per-symbol precomputed series (mirror of `build_bar_series`).
pub struct FeatureStore {
    pub symbol: String,
    pub closes: Vec<f64>,
    pub highs: Vec<f64>,
    pub lows: Vec<f64>,
    pub opens: Vec<f64>,
    pub volumes: Vec<f64>,
    pub tp: Vec<f64>,
    pub ema_fast: Vec<f64>,
    pub ema_slow: Vec<f64>,
    pub atr: Vec<f64>,
    pub rsi: Vec<f64>,
    pub adx: Vec<f64>,
    pub cci: Vec<f64>,
    pub macd: Vec<f64>,
    pub macd_signal: Vec<f64>,
    pub macd_hist: Vec<f64>,
    pub obv: Vec<f64>,
    pub adl: Vec<f64>,
    /// Indexed by bar count t: prior_high[t] = max(highs[0..t-1]), None for t < 2.
    pub prior_high: Vec<Option<f64>>,
    pub prior_low: Vec<Option<f64>>,
    pub piv_hi: [Vec<(usize, f64, f64)>; 3], // per SWING_NS
    pub piv_lo: [Vec<(usize, f64, f64)>; 3],
    pub vwap: Vec<f64>,
    pub vwap_start: Vec<usize>,
    pub event_time_monotonic: bool,
    pub avail: Vec<i64>,
    pub bar_event_times: Vec<i64>,
    pub event_ids: Vec<String>,
    // funding / open-interest channels (latest admissible per clock).
    pub funding_avail: Vec<i64>,
    pub funding_rate: Vec<f64>,
    pub oi_avail: Vec<i64>,
    pub oi_value: Vec<f64>,
    pub oi_skew: Vec<Option<f64>>,
    #[allow(dead_code)] // S5 raw_manifest_hash
    pub kline_avail: Vec<i64>,
}

impl FeatureStore {
    /// Build from one symbol's columnar bars plus its funding/OI rows.
    pub fn build(bars: &SymbolBars, rows: &[crate::data::TapeRow]) -> FeatureStore {
        let closes = bars.closes.clone();
        let highs = bars.highs.clone();
        let lows = bars.lows.clone();
        let opens = bars.opens.clone();
        let volumes = bars.volumes.clone();
        let n = closes.len();
        let tp = typical(&highs, &lows, &closes);
        let ema_fast = ema(&closes, 5);
        let ema_slow = ema(&closes, 20);
        let atr = atr_series(&highs, &lows, 14);
        let rsi = rsi_series(&closes, 14);
        let adx = adx_series(&highs, &lows, &closes, 14);

        let mut cci = vec![0.0; n];
        let mut diffs = Vec::with_capacity(20);
        for j in 19..n {
            let sma = fsum(&tp[j - 19..=j]) / 20.0;
            diffs.clear();
            for x in &tp[j - 19..=j] {
                diffs.push((x - sma).abs());
            }
            let mad = fsum(&diffs) / 20.0;
            if mad != 0.0 {
                cci[j] = (tp[j] - sma) / (0.015 * mad);
            }
        }

        let e12 = ema(&closes, 12);
        let e26 = ema(&closes, 26);
        let macd: Vec<f64> = e12.iter().zip(&e26).map(|(f, s)| f - s).collect();
        let macd_signal = ema(&macd, 9);
        let macd_hist: Vec<f64> = macd.iter().zip(&macd_signal).map(|(m, s)| m - s).collect();

        let obv = obv_series(&closes, &volumes);
        let adl = adl_series(&highs, &lows, &closes, &volumes);

        let mut prior_high: Vec<Option<f64>> = vec![None, None];
        let mut prior_low: Vec<Option<f64>> = vec![None, None];
        let mut ph: Vec<f64> = vec![highs[0]];
        let mut pl: Vec<f64> = vec![lows[0]];
        for j in 1..n {
            let nh = if ph[ph.len() - 1] >= highs[j] { ph[ph.len() - 1] } else { highs[j] };
            let nl = if pl[pl.len() - 1] <= lows[j] { pl[pl.len() - 1] } else { lows[j] };
            ph.push(nh);
            pl.push(nl);
        }
        prior_high.extend(ph[..n.saturating_sub(1)].iter().map(|v| Some(*v)));
        prior_low.extend(pl[..n.saturating_sub(1)].iter().map(|v| Some(*v)));

        let mut piv_hi: [Vec<(usize, f64, f64)>; 3] = [Vec::new(), Vec::new(), Vec::new()];
        let mut piv_lo: [Vec<(usize, f64, f64)>; 3] = [Vec::new(), Vec::new(), Vec::new()];
        for (k, swn) in SWING_NS.iter().enumerate() {
            let (hi, lo) = pivot_lists(&highs, &lows, *swn);
            piv_hi[k] = hi;
            piv_lo[k] = lo;
        }

        let mut vwap = vec![0.0; n];
        let mut vwap_start = vec![0usize; n];
        let mut bar_event_times = Vec::with_capacity(n);
        for j in 0..n {
            let ev = bars.event_times[j];
            bar_event_times.push(ev);
            let anchor = ev - (ev % DAY_NS);
            let mut lo = j;
            while lo > 0 && bars.event_times[lo - 1] >= anchor {
                lo -= 1;
            }
            vwap_start[j] = lo;
            let mut tp_v = 0.0;
            let mut vol = 0.0;
            for k in lo..=j {
                tp_v += (bars.highs[k] + bars.lows[k] + bars.closes[k]) / 3.0 * bars.volumes[k];
                vol += bars.volumes[k];
            }
            vwap[j] = if vol != 0.0 { tp_v / vol } else { 0.0 };
        }

        let mut funding_avail = Vec::new();
        let mut funding_rate = Vec::new();
        let mut oi_avail = Vec::new();
        let mut oi_value = Vec::new();
        let mut oi_skew = Vec::new();
        let mut kline_avail = Vec::new();
        for r in rows {
            match r.channel.as_str() {
                "funding" if r.instrument == bars.symbol => {
                    funding_avail.push(r.available_time);
                    funding_rate.push(r.payload["funding_rate"].as_f64().unwrap_or(0.0));
                }
                "open_interest" if r.instrument == bars.symbol => {
                    oi_avail.push(r.available_time);
                    oi_value.push(r.payload["open_interest"].as_f64().unwrap_or(0.0));
                    oi_skew.push(r.payload.get("long_short_skew").and_then(|v| v.as_f64()));
                }
                "kline" if r.instrument == bars.symbol => {
                    kline_avail.push(r.available_time);
                }
                _ => {}
            }
        }

        let event_time_monotonic = bars.event_times.windows(2).all(|w| w[0] <= w[1]);

        FeatureStore {
            symbol: bars.symbol.clone(),
            closes, highs, lows, opens, volumes, tp, ema_fast, ema_slow,
            atr, rsi, adx, cci, macd, macd_signal, macd_hist, obv, adl,
            prior_high, prior_low, piv_hi, piv_lo, vwap, vwap_start,
            event_time_monotonic, avail: bars.available_times.clone(),
            bar_event_times, event_ids: bars.event_ids.clone(),
            funding_avail, funding_rate, oi_avail, oi_value, oi_skew, kline_avail,
        }
    }

    pub fn bisect_right_times(times: &[i64], as_of: i64) -> usize {
        times.partition_point(|a| *a <= as_of)
    }
}

// Build stores for every symbol in a dataset.
pub fn build_stores(ds: &Dataset) -> Vec<FeatureStore> {
    ds.bars.iter().map(|b| FeatureStore::build(b, &ds.rows)).collect()
}

// ---------------------------------------------------------------------------
// StateView: per-clock features (the cached branch of `build_state`).
// ---------------------------------------------------------------------------

/// One emitted feature value (parity compares these fields; hashes are
/// computed separately and excluded by PARITY_AND_IDENTITY_SPEC §3).
#[derive(Debug, Clone)]
pub struct Feature {
    pub name: String,
    /// Scalar features carry a number; structured features (history,
    /// fib_levels, pivot_points_day, consolidation_range, gap_levels) carry an
    /// array mirror of the Python tuple.
    pub value: serde_json::Value,
    pub dtype: String,
    pub feature_version: String,
    pub max_input_available_time: i64,
    pub quality: String,
    pub null_reason: Option<String>,
    pub group: String,
}

fn num(v: f64) -> serde_json::Value {
    // Validated tapes are finite; serde_json::Number holds finite f64 exactly.
    serde_json::Value::Number(serde_json::Number::from_f64(v).expect("finite feature value"))
}

/// `consumed` is the (lo, hi) index range into the closed-bar prefix
/// `s.closed[..t]` that produced the feature; `calc` is that slice's last
/// bar's available_time, or `explicit_calc` when the consumed rows are not
/// closed bars (funding/OI rows). Mirrors the cached `add()` fast route and
/// its slow-path fallback for non-closed rows.
#[allow(clippy::too_many_arguments)]
fn add(
    out: &mut Vec<Feature>,
    name: &str,
    value: Option<f64>,
    structured: Option<serde_json::Value>,
    dtype: &str,
    version: &str,
    consumed: (usize, usize),
    explicit_calc: Option<i64>,
    store: &FeatureStore,
    quality_in: &str,
    null_reason_in: Option<&str>,
) {
    let mut quality = quality_in.to_string();
    let mut null_reason = null_reason_in.map(|s| s.to_string());
    let value = match (value, structured) {
        (Some(v), None) => num(v),
        (None, Some(v)) => v,
        (None, None) => {
            if quality == "COMPLETE" {
                quality = "DEGRADED".to_string();
                null_reason.get_or_insert_with(|| "NOT_YET_AVAILABLE".to_string());
            }
            serde_json::Value::Null
        }
        _ => unreachable!("value and structured are mutually exclusive"),
    };
    let calc = match explicit_calc {
        Some(c) => c,
        None => {
            if consumed.1 > consumed.0 {
                store.avail[consumed.1 - 1]
            } else {
                0
            }
        }
    };
    out.push(Feature {
        name: name.to_string(),
        value,
        dtype: dtype.to_string(),
        feature_version: version.to_string(),
        max_input_available_time: calc,
        quality,
        null_reason,
        group: feature_group(name).to_string(),
    });
}

/// Build the feature list at bar count `t` (t closed bars, indices 0..t-1),
/// mirroring `build_state`'s cached branch byte-for-byte in value and clock.
pub fn state_features(
    store: &FeatureStore,
    t: usize,
    as_of: i64,
    history_depth: usize,
) -> Vec<Feature> {
    let mut out = Vec::with_capacity(FEATURE_NAMES.len());
    if t == 0 {
        return out;
    }
    let closes = &store.closes[..t];
    let highs = &store.highs[..t];
    let lows = &store.lows[..t];
    let opens = &store.opens[..t];
    let volumes = &store.volumes[..t];
    let tp = &store.tp[..t];
    let atrs = &store.atr[..t.saturating_sub(13)];
    let rsis = &store.rsi[..t.saturating_sub(14)];
    let v1 = "v1";

    // --- raw / location / trend / volatility baseline -----------------------
    add(&mut out, "close", Some(closes[t - 1]), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    if t >= 2 {
        add(&mut out, "prior_high", store.prior_high[t], None, "float", v1, (t - 2, t - 1), None, store, "COMPLETE", None);
        add(&mut out, "prior_low", store.prior_low[t], None, "float", v1, (t - 2, t - 1), None, store, "COMPLETE", None);
    } else {
        add(&mut out, "prior_high", None, None, "float", v1, (0, 0), None, store, "COMPLETE", None);
        add(&mut out, "prior_low", None, None, "float", v1, (0, 0), None, store, "COMPLETE", None);
    }
    if t >= 20 {
        add(&mut out, "ema_fast", Some(store.ema_fast[t - 1]), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
        add(&mut out, "ema_slow", Some(store.ema_slow[t - 1]), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
        add(&mut out, "atr", Some(store.atr[t - 14]), None, "float", v1, (t - 14, t), None, store, "COMPLETE", None);
    }

    // --- FG-1 candle_shape (G-01..G-07) -------------------------------------
    let (o, h, l, c) = (opens[t - 1], highs[t - 1], lows[t - 1], closes[t - 1]);
    let rng = h - l;
    let body = (c - o).abs();
    add(&mut out, "real_body", Some(body), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "body_range_ratio", Some(if rng > 0.0 { body / rng } else { 0.0 }), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "upper_shadow", Some(h - o.max(c)), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "lower_shadow", Some(o.min(c) - l), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "close_position", Some(if rng > 0.0 { (c - l) / rng } else { 0.5 }), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    if t >= 2 {
        let (_po, ph, pl) = (opens[t - 2], highs[t - 2], lows[t - 2]);
        add(&mut out, "inside_bar", Some(if h <= ph && l >= pl { 1.0 } else { 0.0 }), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
        add(&mut out, "outside_bar", Some(if h >= ph && l <= pl { 1.0 } else { 0.0 }), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
        if o > ph {
            add(&mut out, "gap_size", Some(o - ph), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
            add(&mut out, "gap_dir", Some(1.0), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
        } else if o < pl {
            add(&mut out, "gap_size", Some(o - pl), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
            add(&mut out, "gap_dir", Some(-1.0), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
        } else {
            add(&mut out, "gap_size", Some(0.0), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
            add(&mut out, "gap_dir", Some(0.0), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
        }
    } else {
        add(&mut out, "inside_bar", None, None, "float", v1, (0, 0), None, store, "COMPLETE", Some("NOT_YET_AVAILABLE"));
        add(&mut out, "outside_bar", None, None, "float", v1, (0, 0), None, store, "COMPLETE", Some("NOT_YET_AVAILABLE"));
        add(&mut out, "gap_size", None, None, "float", v1, (0, 0), None, store, "COMPLETE", Some("NOT_YET_AVAILABLE"));
        add(&mut out, "gap_dir", None, None, "float", v1, (0, 0), None, store, "COMPLETE", Some("NOT_YET_AVAILABLE"));
    }

    // --- FG-2 oscillator (G-08..G-15) ---------------------------------------
    if t >= 15 {
        add(&mut out, "rsi14", Some(rsis[t - 15]), None, "float", v1, (t - 15, t), None, store, "COMPLETE", None);
        add(&mut out, "mom_14", Some(closes[t - 1] - closes[t - 15]), None, "float", v1, (t - 15, t), None, store, "COMPLETE", None);
        add(&mut out, "roc_14", Some((closes[t - 1] - closes[t - 15]) / closes[t - 15] * 100.0), None, "float", v1, (t - 15, t), None, store, "COMPLETE", None);
    }
    if t >= 16 {
        let (k, d) = stoch(highs, lows, closes, 14);
        add(&mut out, "stoch_k", Some(k), None, "float", v1, (t - 16, t), None, store, "COMPLETE", None);
        add(&mut out, "stoch_d", Some(d), None, "float", v1, (t - 16, t), None, store, "COMPLETE", None);
    }
    if t >= 28 {
        add(&mut out, "stochrsi", Some(stochrsi_from(rsis, 14)), None, "float", v1, (t - 28, t), None, store, "COMPLETE", None);
    }
    if t >= 20 {
        add(&mut out, "cci20", Some(store.cci[t - 1]), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
    }
    if t >= 34 {
        add(&mut out, "macd", Some(store.macd[t - 1]), None, "float", v1, (t - 34, t), None, store, "COMPLETE", None);
        add(&mut out, "macd_signal", Some(store.macd_signal[t - 1]), None, "float", v1, (t - 34, t), None, store, "COMPLETE", None);
        add(&mut out, "macd_hist", Some(store.macd_hist[t - 1]), None, "float", v1, (t - 34, t), None, store, "COMPLETE", None);
    }
    if t >= 28 {
        add(&mut out, "adx14", Some(store.adx[t - 1]), None, "float", v1, (t - 28, t), None, store, "COMPLETE", None);
    }
    if t >= 14 + OBOS_QUANTILE_WINDOW {
        let win = &rsis[rsis.len() - OBOS_QUANTILE_WINDOW..];
        add(&mut out, "osc_obos_quantile", Some(percentile_rank(win, rsis[rsis.len() - 1])), None, "float", v1, (t - (14 + OBOS_QUANTILE_WINDOW), t), None, store, "COMPLETE", None);
    }

    // --- FG-3 volatility (G-16..G-20, G-28) ---------------------------------
    if t >= 20 {
        let mid = sma(closes, 20);
        let sd = std_pop(&closes[t - 20..]);
        let upper = mid + 2.0 * sd;
        let lower = mid - 2.0 * sd;
        add(&mut out, "bb_mid", Some(mid), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
        add(&mut out, "bb_upper", Some(upper), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
        add(&mut out, "bb_lower", Some(lower), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
        add(&mut out, "bb_pct_b", Some(if upper > lower { (closes[t - 1] - lower) / (upper - lower) } else { 0.5 }), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
        add(&mut out, "bb_bandwidth", Some(if mid != 0.0 { (upper - lower) / mid } else { 0.0 }), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
    }
    if t >= 5 {
        let mut win = Vec::with_capacity(5);
        for j in (t - 5)..t {
            win.push(highs[j] - lows[j]);
        }
        add(&mut out, "atr_locational", Some(fsum(&win) / 5.0), None, "float", v1, (t - 5, t), None, store, "COMPLETE", None);
    }
    if t >= 20 {
        add(&mut out, "atr_filtered_2sigma", Some(atrs[atrs.len() - 1]), None, "float", v1, (t - 14, t), None, store, "COMPLETE", None);
    }
    if atrs.len() >= ATR_FILTER_BAND_N {
        let band = sma(atrs, ATR_FILTER_BAND_N) + 2.0 * std_pop(&atrs[atrs.len() - ATR_FILTER_BAND_N..]);
        add(&mut out, "atr_2sigma_active", Some(if atrs[atrs.len() - 1] > band { 1.0 } else { 0.0 }), None, "float", v1, (t - (14 + ATR_FILTER_BAND_N - 1), t), None, store, "COMPLETE", None);
    }
    if atrs.len() >= ATR_SLOPE_N + 1 {
        let slope = atrs[atrs.len() - 1] - atrs[atrs.len() - 1 - ATR_SLOPE_N];
        let phase = if slope > 0.0 { 1.0 } else if slope < 0.0 { -1.0 } else { 0.0 };
        add(&mut out, "atr_trend_phase", Some(phase), None, "float", v1, (t - (14 + ATR_SLOPE_N), t), None, store, "COMPLETE", None);
    }
    if t >= 23 {
        let mid_k = sma(tp, 10);
        let k_atr = sma(atrs, 10);
        add(&mut out, "keltner_u", Some(mid_k + k_atr), None, "float", v1, (t - 23, t), None, store, "COMPLETE", None);
        add(&mut out, "keltner_l", Some(mid_k - k_atr), None, "float", v1, (t - 23, t), None, store, "COMPLETE", None);
    }
    if t >= 15 {
        let mid_s = sma(tp, 6);
        let mut win = Vec::with_capacity(15);
        for j in (t - 15)..t {
            win.push(highs[j] - lows[j]);
        }
        let a15 = fsum(&win) / 15.0;
        add(&mut out, "starc_u", Some(mid_s + STARC_K * a15), None, "float", v1, (t - 15, t), None, store, "COMPLETE", None);
        add(&mut out, "starc_l", Some(mid_s - STARC_K * a15), None, "float", v1, (t - 15, t), None, store, "COMPLETE", None);
    }
    if t >= 20 {
        add(&mut out, "atr_band_stop", Some(ATR_BAND_STOP_K * atrs[atrs.len() - 1]), None, "float", v1, (t - 20, t), None, store, "COMPLETE", None);
    }

    // --- FG-4 location (G-21..G-28) -----------------------------------------
    let atr_now = if !atrs.is_empty() { Some(atrs[atrs.len() - 1]) } else { None };
    for (k, n) in SWING_NS.iter().enumerate() {
        if t >= 2 * n + 1 && atr_now.is_some() {
            let p = last_significant_pivot(&store.piv_hi[k], t, *n, atr_now.unwrap(), SWING_SIGNIFICANCE_K);
            let q = last_significant_pivot(&store.piv_lo[k], t, *n, atr_now.unwrap(), SWING_SIGNIFICANCE_K);
            let swing_hi = p.map(|x| x.1).unwrap_or(0.0);
            let swing_lo = q.map(|x| x.1).unwrap_or(0.0);
            add(&mut out, &format!("swing_high_{n}"), Some(swing_hi), None, "float", v1, (t - (2 * n + 1), t), None, store, "COMPLETE", None);
            add(&mut out, &format!("swing_low_{n}"), Some(swing_lo), None, "float", v1, (t - (2 * n + 1), t), None, store, "COMPLETE", None);
        }
    }
    for n in WINDOW_NS {
        if t >= n + 1 {
            let mut hmax = f64::NEG_INFINITY;
            let mut lmin = f64::INFINITY;
            for j in (t - n - 1)..(t - 1) {
                if highs[j] > hmax {
                    hmax = highs[j];
                }
                if lows[j] < lmin {
                    lmin = lows[j];
                }
            }
            add(&mut out, &format!("window_high_{n}"), Some(hmax), None, "float", v1, (t - n - 1, t - 1), None, store, "COMPLETE", None);
            add(&mut out, &format!("window_low_{n}"), Some(lmin), None, "float", v1, (t - n - 1, t - 1), None, store, "COMPLETE", None);
            add(&mut out, &format!("range_height_{n}"), Some(hmax - lmin), None, "float", v1, (t - n - 1, t - 1), None, store, "COMPLETE", None);
        }
    }
    if t >= 21 {
        let hi10 = last_confirmed_swing(&store.piv_hi[1], t, 10);
        let lo10 = last_confirmed_swing(&store.piv_lo[1], t, 10);
        if let Some(fibs) = fib_levels(hi10, lo10) {
            let (extreme, direction, retr, ext) = fibs;
            // Python value: (extreme, direction, ((r, v), ...), ((r, v), ...))
            // — nested (r, v) pairs, mirrored exactly.
            let retr_arr: Vec<serde_json::Value> = retr
                .iter()
                .map(|(r, v)| serde_json::json!([num(*r), num(*v)]))
                .collect();
            let ext_arr: Vec<serde_json::Value> = ext
                .iter()
                .map(|(r, v)| serde_json::json!([num(*r), num(*v)]))
                .collect();
            let arr = serde_json::json!([num(extreme), num(direction), retr_arr, ext_arr]);
            add(&mut out, "fib_levels", None, Some(arr), "fib_levels", v1, (t - 21, t), None, store, "COMPLETE", None);
        }
    }
    if t >= BARS_PER_DAY + 1 {
        let mut ph_p = f64::NEG_INFINITY;
        let mut pl_p = f64::INFINITY;
        for j in (t - (BARS_PER_DAY + 1))..(t - 1) {
            if highs[j] > ph_p {
                ph_p = highs[j];
            }
            if lows[j] < pl_p {
                pl_p = lows[j];
            }
        }
        let pc_p = closes[t - BARS_PER_DAY - 1];
        let pp = (ph_p + pl_p + pc_p) / 3.0;
        let rng_p = ph_p - pl_p;
        let vals = [
            pp,
            pp + (pp - pl_p),
            pp + rng_p,
            pp + (pp - pl_p) + rng_p,
            pp + rng_p + rng_p,
            pp - (ph_p - pp),
            pp - rng_p,
            pp - (ph_p - pp) - rng_p,
            pp - rng_p - rng_p,
        ];
        let arr: Vec<serde_json::Value> = vals.iter().map(|v| num(*v)).collect();
        add(&mut out, "pivot_points_day", None, Some(serde_json::Value::Array(arr)), "pivot_points", v1, (t - (BARS_PER_DAY + 1), t - 1), None, store, "COMPLETE", None);
    }
    if t >= CONSOLIDATION_BARS + 1 {
        let (h_ref, l_ref, w, act) = consolidation_range(highs, lows, closes, CONSOLIDATION_BARS, CONSOLIDATION_WIDTH_MAX);
        let arr = serde_json::json!([h_ref, l_ref, w, act]);
        add(&mut out, "consolidation_range", None, Some(arr), "consolidation", v1, (t - (CONSOLIDATION_BARS + 1), t - 1), None, store, "COMPLETE", None);
    }
    {
        let zones = gap_levels(opens, highs, lows, closes, GAP_ZONE_BARS);
        let arr: Vec<serde_json::Value> = zones
            .iter()
            .map(|(top, bottom, d)| serde_json::json!([top, bottom, d]))
            .collect();
        add(&mut out, "gap_levels", None, Some(serde_json::Value::Array(arr)), "gap_levels", v1, (t.saturating_sub(GAP_ZONE_BARS), t), None, store, "COMPLETE", None);
    }

    // --- FG-5 participation (G-29..G-37) ------------------------------------
    add(&mut out, "volume", Some(volumes[t - 1]), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    if t >= VOLUME_STAT_N {
        let vol_win = &volumes[t - VOLUME_STAT_N..];
        let vmean = mean(vol_win);
        let vsd = std_pop(vol_win);
        let z = if vsd != 0.0 { (volumes[t - 1] - vmean) / vsd } else { 0.0 };
        add(&mut out, "vol_zscore", Some(z), None, "float", v1, (t - VOLUME_STAT_N, t), None, store, "COMPLETE", None);
        let mut vmin = f64::INFINITY;
        let mut vmax = f64::NEG_INFINITY;
        for v in vol_win {
            if *v < vmin {
                vmin = *v;
            }
            if *v > vmax {
                vmax = *v;
            }
        }
        let prox = if vmax > vmin { (volumes[t - 1] - vmin) / (vmax - vmin) } else { 0.5 };
        add(&mut out, "vol_min_proximity", Some(prox), None, "float", v1, (t - VOLUME_STAT_N, t), None, store, "COMPLETE", None);
    }
    if t >= VOLUME_SMA_N {
        add(&mut out, "vol_smooth_ma", Some(sma(volumes, VOLUME_SMA_N)), None, "float", v1, (t - VOLUME_SMA_N, t), None, store, "COMPLETE", None);
    }
    if t >= 2 {
        add(&mut out, "obv", Some(store.obv[t - 1]), None, "float", v1, (t - 2, t), None, store, "COMPLETE", None);
    }
    add(&mut out, "adl", Some(store.adl[t - 1]), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    if t >= CMF_N {
        add(&mut out, "cmf_20", Some(cmf(highs, lows, closes, volumes, CMF_N)), None, "float", v1, (t - CMF_N, t), None, store, "COMPLETE", None);
    }
    if store.event_time_monotonic {
        let lo = store.vwap_start[t - 1];
        add(&mut out, "vwap", Some(store.vwap[t - 1]), None, "float", v1, (lo, t), None, store, "COMPLETE", None);
    } else {
        // Non-monotonic event_time: the exact full-filter `_vwap` over the
        // prefix (the uncached reference).
        let (val, lo) = vwap_fallback(store, t);
        add(&mut out, "vwap", Some(val), None, "float", v1, (lo, t), None, store, "COMPLETE", None);
    }
    if t >= BAR_CLASS_N && t >= 6 {
        add(&mut out, "bar_class", Some(bar_class(opens, closes, highs, lows, volumes, 5)), None, "float", v1, (t - BAR_CLASS_N, t), None, store, "COMPLETE", None);
    }

    // --- FG-6 session (G-38..G-40) ------------------------------------------
    let ev = store.bar_event_times[t - 1];
    let hour = hour_utc(ev);
    add(&mut out, "hour_of_day_utc", Some(hour as f64), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "impulsive_window", Some(if hour >= IMPULSIVE_START_HOUR && hour <= IMPULSIVE_END_HOUR { 1.0 } else { 0.0 }), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "bar_of_session", Some(bar_of_session(ev) as f64), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);
    add(&mut out, "day_index", Some(day_index(ev) as f64), None, "float", v1, (t - 1, t), None, store, "COMPLETE", None);

    // --- FG-7 positioning (G-41..G-43) --------------------------------------
    let m = FeatureStore::bisect_right_times(&store.funding_avail, as_of);
    if m > 0 {
        add(&mut out, "funding_rate", Some(store.funding_rate[m - 1]), None, "float", v1, (0, 0), Some(store.funding_avail[m - 1]), store, "COMPLETE", None);
    }
    let m = FeatureStore::bisect_right_times(&store.oi_avail, as_of);
    if m > 0 {
        add(&mut out, "open_interest", Some(store.oi_value[m - 1]), None, "float", v1, (0, 0), Some(store.oi_avail[m - 1]), store, "COMPLETE", None);
        if let Some(skew) = store.oi_skew[m - 1] {
            add(&mut out, "long_short_skew", Some(skew), None, "float", v1, (0, 0), Some(store.oi_avail[m - 1]), store, "COMPLETE", None);
        }
    }

    // --- D-026 history ------------------------------------------------------
    if t > 0 {
        let depth = history_depth.min(t);
        let win_lo = t - depth;
        let mut hist = Vec::with_capacity(depth);
        for (i, j) in (win_lo..t).enumerate() {
            let pos = t - depth + i; // full-series index of window element i
            let bar = &store.event_ids[j];
            let arr = serde_json::json!([
                bar,
                opens[j], highs[j], lows[j], closes[j],
                store.ema_fast[pos],
                store.ema_slow[pos],
            ]);
            hist.push(arr);
        }
        add(&mut out, "history", None, Some(serde_json::Value::Array(hist)), "history", "v2", (win_lo, t), None, store, "COMPLETE", None);
    }

    out
}

/// The exact full-filter `_vwap` (marketstate.py) over the prefix: session
/// anchored at the last 00:00 UTC boundary of the newest bar's event_time.
fn vwap_fallback(store: &FeatureStore, t: usize) -> (f64, usize) {
    let ev = store.bar_event_times[t - 1];
    let anchor = ev - (ev % DAY_NS);
    let mut lo = t;
    while lo > 0 && store.bar_event_times[lo - 1] >= anchor {
        lo -= 1;
    }
    let mut tp_v = 0.0;
    let mut vol = 0.0;
    for j in lo..t {
        tp_v += (store.highs[j] + store.lows[j] + store.closes[j]) / 3.0 * store.volumes[j];
        vol += store.volumes[j];
    }
    if vol == 0.0 {
        (0.0, lo)
    } else {
        (tp_v / vol, lo)
    }
}

/// V8.2 identity (excluded from the parity comparison by §3, but load-bearing
/// for the mutation semantics: a changed input must change exactly the states
/// that consumed it).
pub fn v82_lineage_hash(features: &[Feature], symbol: &str) -> String {
    let mut c = Canon::new();
    c.push_map();
    c.push_count(features.len());
    let mut idx: Vec<usize> = (0..features.len()).collect();
    idx.sort_by(|a, b| format!("{symbol}.{}", features[*a].name).cmp(&format!("{symbol}.{}", features[*b].name)));
    for i in idx {
        let f = &features[i];
        c.push_str(&format!("{symbol}.{}", f.name));
        c.push_list();
        c.push_count(4);
        c.push_value(&f.value);
        c.push_i64(f.max_input_available_time);
        c.push_str(&f.group);
        c.push_str(&f.feature_version);
    }
    c.finish_sha1_hex()
}

pub fn v82_state_id(as_of: i64, universe: &[String], lineage_hash: &str) -> String {
    let mut c = Canon::new();
    c.push_list();
    c.push_count(3);
    c.push_i64(as_of);
    c.push_list();
    c.push_count(universe.len());
    for u in universe {
        c.push_str(u);
    }
    c.push_str(lineage_hash);
    c.finish_sha1_hex()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn f64_from_hex(hex: &str) -> f64 {
        let mut bytes = [0u8; 8];
        for (i, ch) in hex.as_bytes().chunks(2).enumerate() {
            bytes[i] = u8::from_str_radix(std::str::from_utf8(ch).unwrap(), 16).unwrap();
        }
        f64::from_be_bytes(bytes)
    }

    /// fsum must be bit-identical to CPython's sum()/math.fsum on a battery of
    /// arrays (expected values captured from CPython 3.14).
    #[test]
    fn fsum_matches_cpython() {
        let battery: Vec<(Vec<f64>, &str)> = vec![
            (vec![75.52262466728358, 76.00946797757125, 76.57378417171833, 76.12761096477955, 75.55392863144242, 77.149300302392, 76.39792362109318, 75.62424105469441, 74.39680135569978, 75.34879861632106, 73.49560260116411, 74.0916476205677, 74.7476811870851, 75.38436978025692, 76.2531887906469, 75.0185839794253, 74.63878647287305, 74.59817011285026, 74.62120009454075, 73.18940594096142], "409782f8f3e8ff54"),
            (vec![1e100, 1.0, -1e100, 1.0], "4000000000000000"),
            (vec![1e16, 1.0, 1.0, -1e16, 1.0], "4008000000000000"),
            (vec![1.0, 2.0, 3.0, 4.0, 5.0], "402e000000000000"),
            (vec![0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "4016000000000000"),
            (vec![-118.53480164929465, -985.0170598828256, 821.9519248982483, 878.537994727528, 164.45514611789827, 343.1269629759702, -832.1235463258321, 532.9618655835925, -526.3804492737645, -938.3719565467801, 577.545434472567, -307.8220688057538, 246.56295007833705, 231.63139020723042, -702.8907225834248, -633.8187051801367, -771.1740606226247, -970.7624390261817, -26.496918790483278, 929.8031218324313, -870.8754380456278, 82.17637110226042, -68.20288198338085, 202.9268991221029, -822.1423400186753, 158.00537237473304, -460.8289923611035], "c0ae33838ea2df41"),
            (vec![-873.8446288610364, -395.1418924177235, 700.3567271715274, -467.09151194763024, 310.96349557512235, -599.9355546625256, 753.109448107499, 330.82309394031086, 882.9511032715727, -858.8233291241492, -332.9798408781228, 420.0266372088629, 314.7089984617746, -665.7750896487355, -847.5320400665925, -6.836665213060087, -849.356598297801, -569.8112078868492, -945.7426676555414, -307.5382892641429], "c0af4ef08b3916ec"),
            (vec![-589.8393315816795, 779.3497845890442, -157.65273310706164, 905.0902811365097, -593.480299386724, -879.3783960811587, -295.02844014256095, -693.8790455522046, 812.9210587341367, 901.7698697601356, -55.128003153830605, -722.5422392646543, -903.8549717589322, -669.8404114641814, -710.142942632156, 92.12929114326494, 427.59751268156174, -657.9525917514211, 336.47991232122763, -878.3507102984174, -824.7590101076847, 584.2075220983313, 831.0605468904032, -920.1773638610189, -217.11771582477013, -351.1779873502405, 943.4132251566189, 349.42049356104553, 872.7767299754287, 830.4426813129285], "c096b692b907a7a3"),
            (vec![74975.44038065267, 842134.7186645006, -155926.26752028638, 370540.1804707835, 693817.6922711257, 677535.5716443022, -814262.3489447867, -479368.47391694284, -179483.95907779213, 715648.719145997, -446514.9413674994, -772522.1708169791, -249303.09840700042, -572228.3527635646, 432473.2696582796, 175019.03173831757, -895002.0916830625, 754860.7563154402, -118889.82009146991, 553774.0810290182, -669358.5905351988, -384165.6744115298, -853347.4135368038, -210018.55584351637, -142179.2679747271, 365592.5814457368, -40824.29132492654, -198976.26894102152, -44076.03804483288, -437479.1891648966, -260949.12506302272, 200987.49319436983, -587864.038810408, 37728.652301505674, 859345.370054608, -85165.0863322335, 336621.0233334757, 319686.3834305762, 602690.3360429173, 451100.75872976007, 321414.0653514853, -792578.3540768693, -266732.49946508836, 588120.7805248376, -869614.5278799017, -719964.684721224, 810720.3378580115, 176034.93231206317, 960337.5248445068, 507160.5258129735, 991355.9003122542, -402761.00216016045, 372113.0279163737, -338826.5138439501, 891940.2055675965, -412437.34117552487, -610867.343706467], "41305baa075c254c"),
            (vec![-441930.6803869525, 68067.32257583528, 204407.4267745174, -320731.5130491324, -331530.2742426953, -357877.6350910895, -464992.40271812247, 519344.6953188032, 178459.47418411146, 96490.11670971732, 648277.0330496577, -485698.78381678875, -725833.3881113927, -943241.8585636964, -925292.0945787679, 981352.4491202082, 947629.3803559185, 333199.518245596, 981320.8477647395, 31305.005482253735, -130889.20848461892, 30568.464212609222, -862006.3089718606, 519161.5813593534, -389676.9544269898, 396160.8929271924, 819005.3936811425, -560801.8137850291, 8752.555889971205, 306283.6067451106, 621916.6519963352, 365502.84303798503, -337817.253730317, 128359.66392764589, -674931.4147534766, -1167.942807888845, 880096.1475933851, 900365.3972106797, -720122.6371847112, 64627.56727086031, 239723.62381568854, -708936.1916274335, 897981.9244043839, -513428.5287758813, -671499.7900422366, 12863.259828657494, 10007.21292716579, 546896.7466526313, 706354.6305719556, -346993.66794642806, 416454.61320614885, 123444.83384744497, 70162.45439900667, 198398.3195460341, -107324.4804011815, -256592.54090953374, 859446.3671610528, 525798.1097777286, 351739.04014221113, 772622.198531423, 208084.50299437204, -858195.8813345742, -544153.979074135, 606040.5701129194, -307627.35098930926, 879239.6861502521, 378104.5938897012, -240426.50178397796, -14428.153973663459, -895104.8697555213, -103848.71354716062, -839644.166404801, -413671.90440897713, 858583.0232546455, -704212.0026625387, 353834.69991528126, 301577.82498044684, 386135.4587115501, 588940.1589304414, 728512.2832304242, -286782.6135242814, -257176.88478527928, -651901.1396964735, 278848.9761622043, -575458.5597614592, -607100.9660525662, 980184.6236758516], "414c783f5c2bfc1a"),
            (vec![1e-16, 1.0, 1e16], "4341c37937e08001"),
            (vec![1e100, 1.0, -1e100, 1.0], "4000000000000000"),
            (vec![
                f64::from_be_bytes([0x40,0x15,0x7e,0x35,0xce,0x74,0xd0,0xf4]),
                f64::from_be_bytes([0x3f,0xf4,0x5a,0xe3,0x71,0xe8,0xce,0x75]),
                f64::from_be_bytes([0x40,0x11,0xc4,0xe6,0xce,0x10,0x81,0x0c]),
            ], "40262ceabc7fc2cf"),
        ];
        for (i, (arr, expected)) in battery.iter().enumerate() {
            let got = fsum(arr);
            let exp = f64_from_hex(expected);
            assert_eq!(got.to_bits(), exp.to_bits(), "battery case {i}");
        }
    }
}

// ---------------------------------------------------------------------------
// Live-feature resolution for the compiled thesis IR (PREDICATE_IR_SPEC).
// ---------------------------------------------------------------------------

/// Resolve one scalar live feature at bar count `t` (0-indexed bars 0..t-1),
/// with the same warmup gating the feature block applies — absent until the
/// window is satisfied (fail-open operand). Vocabulary: close, ema_fast,
/// ema_slow, rsi14, stoch_k, cci20, macd, prior_high.
pub fn live_feature(store: &FeatureStore, t: usize, name: &str) -> Option<f64> {
    if t == 0 {
        return None;
    }
    match name {
        "close" => Some(store.closes[t - 1]),
        "ema_fast" => (t >= 20).then(|| store.ema_fast[t - 1]),
        "ema_slow" => (t >= 20).then(|| store.ema_slow[t - 1]),
        "rsi14" => (t >= 15).then(|| store.rsi[t - 15]),
        "stoch_k" => {
            if t < 16 {
                return None;
            }
            let closes = &store.closes[..t];
            let highs = &store.highs[..t];
            let lows = &store.lows[..t];
            Some(stoch(highs, lows, closes, 14).0)
        }
        "cci20" => (t >= 20).then(|| store.cci[t - 1]),
        "macd" => (t >= 34).then(|| store.macd[t - 1]),
        "prior_high" => store.prior_high[t],
        _ => None,
    }
}

/// `window_high_{n}` / `window_low_{n}` live channel features (donchian): the
/// max high / min low over the n bars BEFORE the current bar.
pub fn live_window_feature(store: &FeatureStore, t: usize, name: &str, n: usize) -> Option<f64> {
    if t < n + 1 {
        return None;
    }
    let lo = t - n - 1;
    let hi = t - 1; // excludes the newest bar
    match name {
        "window_high" => Some(store.highs[lo..hi].iter().cloned().fold(f64::NEG_INFINITY, f64::max)),
        "window_low" => Some(store.lows[lo..hi].iter().cloned().fold(f64::INFINITY, f64::min)),
        _ => None,
    }
}

/// The history window ending at bar t-1, oldest first, each bar as
/// [open, high, low, close, ema_fast, ema_slow] with the full-series EMAs —
/// the carrier the predicate IR's `WindowAgg` slices.
pub fn history_window(store: &FeatureStore, t: usize, depth: usize) -> Vec<[f64; 6]> {
    let d = depth.min(t);
    let win_lo = t - d;
    let mut out = Vec::with_capacity(d);
    for (k, j) in (win_lo..t).enumerate() {
        let pos = win_lo + k; // full-series index
        out.push([
            store.opens[j],
            store.highs[j],
            store.lows[j],
            store.closes[j],
            store.ema_fast[pos],
            store.ema_slow[pos],
        ]);
    }
    out
}
