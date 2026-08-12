//! market_profile_value_area: prior-session TPO profile / value-area reversion
//! (variants a-d; the parity dispatch instantiates the default `a` variant).
//! Ported at S4; draft parity proven.
//!
//! The profile is computed inside the expert from the state's `history` OHLC
//! window (D-026 32-bar pin): each bar contributes one TPO to every bucket its
//! [low, high] range touches; the POC is the bucket with the most TPOs (ties
//! resolve nearest the session mid, lower index wins); the 68% value area
//! expands from the POC one bucket at a time, adding the larger side.

use std::collections::HashMap;

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["session", "volatility", "history"];

// Declared, LOCKED constants (D-036 pattern: "declared, never fitted").
const PROFILE_BUCKET_ATR_FRAC: f64 = 1.0; // price bucket = 1.0 * ATR at detection
const VALUE_AREA_FRAC: f64 = 0.68;        // book: value area = 68% of TPOs (Ch17.1)
const SESSION_BARS: usize = 24;           // 1h bars per UTC session (00:00 UTC anchor)
const MIN_PRIOR_BARS: usize = 12;         // minimum prior-session bars for a profile
const PRESSURE_THRESHOLD: f64 = 0.55;     // TPO-pressure share for variant c
const VA_EXIT_DISTANCE_ATR: f64 = 0.5;    // variant d: outside VA by >= 0.5 * ATR

/// CPython float floor division (`x // y`): `floor(x / y)` on the correctly
/// rounded IEEE division (CPython `float_floor_div`), NOT the exact-floor
/// fmod method — the rounded quotient can land on the next integer when the
/// exact quotient is just below a boundary (measured on the fixture).
fn py_floordiv(x: f64, y: f64) -> f64 {
    (x / y).floor()
}

/// TPO profile of the prior session (`_tpo_profile`). Each bar contributes one
/// TPO to every bucket its [low, high] range touches. Returns
/// (poc_price, va_low, va_high, total, above_share, below_share); None when no
/// bar contributes. The POC is the bucket with the most TPOs; ties resolve to
/// the bucket nearest the session mid, lower line wins. The value area expands
/// from the POC one bucket at a time, adding the larger side until the target
/// TPO share is reached.
fn tpo_profile(prior_bars: &[HistBar], bucket: f64, value_area_frac: f64)
    -> Option<(f64, f64, f64, i64, f64, f64)> {
    let mut counts: HashMap<i64, i64> = HashMap::new();
    for b in prior_bars {
        let lo = py_floordiv(b.low, bucket) as i64;
        let hi = py_floordiv(b.high, bucket) as i64;
        for idx in lo..=hi {
            *counts.entry(idx).or_insert(0) += 1;
        }
    }
    let total: i64 = counts.values().sum();
    if total == 0 {
        return None;
    }
    let max_high = prior_bars.iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
    let min_low = prior_bars.iter().map(|b| b.low).fold(f64::INFINITY, f64::min);
    let mid_idx = py_floordiv((max_high + min_low) / 2.0, bucket) as i64;
    // max by (count desc, |dist to mid| asc, lower index wins).
    let poc_idx = *counts.iter()
        .max_by(|(k1, v1), (k2, v2)| {
            let (k1, v1) = (**k1, **v1);
            let (k2, v2) = (**k2, **v2);
            (v1, -(k1 - mid_idx).abs(), -k1).cmp(&(v2, -(k2 - mid_idx).abs(), -k2))
        })
        .map(|(k, _)| k)
        .expect("counts non-empty since total > 0");
    let target = (value_area_frac * total as f64).ceil() as i64;
    let mut cum = *counts.get(&poc_idx).expect("poc present");
    let mut lo_i = poc_idx;
    let mut hi_i = poc_idx;
    while cum < target {
        let left = counts.get(&(lo_i - 1)).copied().unwrap_or(0);
        let right = counts.get(&(hi_i + 1)).copied().unwrap_or(0);
        if left == 0 && right == 0 {
            break;
        }
        if right > left {
            hi_i += 1;
            cum += counts.get(&hi_i).copied().unwrap_or(0);
        } else {
            lo_i -= 1;
            cum += counts.get(&lo_i).copied().unwrap_or(0);
        }
    }
    let above: i64 = counts.iter().filter(|(k, _)| **k > poc_idx).map(|(_, v)| *v).sum();
    let below: i64 = counts.iter().filter(|(k, _)| **k < poc_idx).map(|(_, v)| *v).sum();
    Some((poc_idx as f64 * bucket, lo_i as f64 * bucket, hi_i as f64 * bucket,
          total, above as f64 / total as f64, below as f64 / total as f64))
}

pub fn market_profile_value_area(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let bof = match fm.value("bar_of_session") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    if atr <= 0.0 || fm.history.is_empty() || bof <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // `_profile`: prior-session TPO profile + range; None when not computable.
    if fm.history.len() as i64 <= bof as i64 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let bucket = atr * PROFILE_BUCKET_ATR_FRAC;
    if bucket <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let n = fm.history.len() as i64 - bof as i64;
    let prior_sess = &fm.history[..n as usize];
    let prior_day = &prior_sess[prior_sess.len().saturating_sub(SESSION_BARS)..];
    if prior_day.len() < MIN_PRIOR_BARS {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let prof = match tpo_profile(prior_day, bucket, VALUE_AREA_FRAC) {
        Some(p) => p,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let (poc, va_low, va_high, _total, above, below) = prof;
    let day_high = prior_day.iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max);
    let day_low = prior_day.iter().map(|b| b.low).fold(f64::INFINITY, f64::min);
    // The dispatch carries no variant; the parity harness instantiates the
    // default `variant_id = 'a'`. Variants b/c/d are mirrored below.
    let variant = "a";
    // Setup gate per variant (Ch17.2 responsive/initiative doctrine).
    let mut direction = None;
    if variant == "a" {
        if close < poc && close > day_low {
            direction = Some("LONG");
        } else if close > poc && close < day_high {
            direction = Some("SHORT");
        }
    } else if variant == "b" {
        if close < va_low && close > day_low {
            direction = Some("LONG");
        } else if close > va_high && close < day_high {
            direction = Some("SHORT");
        }
    } else if variant == "c" {
        // TPO-pressure gauge: the larger tail (above vs below the POC)
        // dominates at >= 55%; initiative is a close BEYOND the value area but
        // inside the prior-day range.
        let tails = above + below;
        if tails != 0.0 {
            if above / tails >= PRESSURE_THRESHOLD && close > va_high && close < day_high {
                direction = Some("LONG");
            } else if below / tails >= PRESSURE_THRESHOLD && close < va_low && close > day_low {
                direction = Some("SHORT");
            }
        }
    } else {
        // 'd' — deep deviation below the value center (POC) by the declared
        // distance gate; the VA is the profile context.
        let dist = VA_EXIT_DISTANCE_ATR * atr;
        if close < poc - dist && close > day_low {
            direction = Some("LONG");
        } else if close > poc + dist && close < day_high {
            direction = Some("SHORT");
        }
    }
    let direction = match direction {
        Some(d) => d,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let long = direction == "LONG";
    // Frozen references (Ch17.2 p669 action-point doctrine): the prior-day
    // range extreme is the stop reference for the reversion variants; the
    // value center (POC) is the hold level for the initiative variant c.
    let (stop_ref, low_ref, high_ref) = if variant == "c" {
        (if long { va_low } else { va_high },
         if long { Some(poc) } else { None },
         if long { None } else { Some(poc) })
    } else {
        (if long { day_low } else { day_high },
         if long { Some(day_low) } else { None },
         if long { None } else { Some(day_high) })
    };
    // Target: reversion variants revert to the value center (POC); the
    // initiative variant c continues to the prior-day range extreme.
    let target_ref = if variant != "c" { poc } else if long { day_high } else { day_low };
    let (target_r, stop_r) = if long {
        ((target_ref - close) / atr, (close - stop_ref) / atr)
    } else {
        ((close - target_ref) / atr, (stop_ref - close) / atr)
    };
    if target_r <= 0.0 || stop_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    // Per-history-bar predicate for the setup anchor: the price leg of the
    // setup (the run of closes beyond the reference); D-026.
    let pred = |_i: usize, b: &HistBar| -> bool {
        if variant == "a" || variant == "d" {
            if long { b.close < poc } else { b.close > poc }
        } else if variant == "c" {
            if long { b.close > va_high } else { b.close < va_low }
        } else {
            if long { b.close < va_low } else { b.close > va_high }
        }
    };
    let anchor = find_setup_anchor(&fm.history, &pred);
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(target_r)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant)),
        ("poc_ref", serde_json::json!(poc)),
        ("va_low_ref", serde_json::json!(va_low)),
        ("va_high_ref", serde_json::json!(va_high)),
    ]);
    if let Some(lo) = low_ref {
        geometry.insert("prior_low_ref".into(), serde_json::json!(lo));
    }
    if let Some(hi) = high_ref {
        geometry.insert("prior_high_ref".into(), serde_json::json!(hi));
    }
    let fingerprint = format!("{sym}:{variant}:{direction}:{close:.6}:{poc:.6}");
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
