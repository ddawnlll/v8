//! bollinger_reversion: fade the 2-SD band back toward the 1-SD band (Setup 2
//! / Setup 3) — mirror src/v8/experts/bollinger_reversion.py bit-for-bit
//! (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4). Default instance is
//! variant 'a' (the Python oracle's default constructor).

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::{fsum, HistBar};

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["trend", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const EXPIRY_BARS: i64 = 8;

/// Declared, frozen constant (D-036 pattern): the Bollinger base window of the
/// marketstate bb_* features (SMA20 +/- 2*sigma); the 1-SD/3-SD levels are
/// derived from it, not new features.
const BB_BASE_N: usize = 20;

/// Python `_mean`: `sum(values) / len(values)` — CPython's sum() over floats
/// is compensated (state::fsum is bit-identical, per state.rs).
fn mean(values: &[f64]) -> f64 {
    fsum(values) / values.len() as f64
}

/// Python `_std_pop`: `(sum((v - m) ** 2 for v in values) / len(values)) ** 0.5`
/// — both powers are libm pow (x**2 / x**0.5), not x*x / sqrt. black_box keeps
/// the exponents opaque so LLVM cannot fold pow -> x*x / sqrt in release
/// (same pattern as state.rs std_pop).
fn std_pop(values: &[f64]) -> f64 {
    let m = mean(values);
    let mut acc = Vec::with_capacity(values.len());
    for v in values {
        let d = v - m;
        acc.push(d.powf(std::hint::black_box(2.0)));
    }
    let sos = fsum(&acc);
    (sos / values.len() as f64).powf(std::hint::black_box(0.5))
}

/// Python `_bb_series`: per-bar (mid, sd) of the trailing 20 closes; None in
/// warmup (entry i<BB_BASE_N-1 is a placeholder, never read — every predicate
/// guards i >= BB_BASE_N-1 first).
fn bb_series(hist: &[HistBar]) -> Vec<(f64, f64)> {
    let n = hist.len();
    let closes: Vec<f64> = hist.iter().map(|b| b.close).collect();
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        if i >= BB_BASE_N - 1 {
            let win = &closes[i - (BB_BASE_N - 1)..=i];
            out.push((mean(win), std_pop(win)));
        } else {
            out.push((0.0, 0.0));
        }
    }
    out
}

/// Frozen band stack + ATR14 at the setup anchor (Python `_anchor_refs`):
/// None when the anchor's 20-bar context is not fully inside the window.
struct Refs {
    mid_ref: f64,
    sd_ref: f64,
    atr_ref: f64,
    upper_1sd_ref: f64,
    upper_2sd_ref: f64,
    upper_3sd_ref: f64,
    lower_1sd_ref: f64,
    lower_2sd_ref: f64,
    lower_3sd_ref: f64,
}

fn anchor_refs(hist: &[HistBar], anchor_event_id: &str) -> Option<Refs> {
    let pos = hist.iter().position(|b| b.event_id == *anchor_event_id)?;
    if pos < BB_BASE_N - 1 || pos < 13 {
        return None;
    }
    let closes: Vec<f64> = hist.iter().map(|b| b.close).collect();
    let win = &closes[pos - (BB_BASE_N - 1)..=pos];
    let mid = mean(win);
    let sd = std_pop(win);
    let mut trs = Vec::with_capacity(14);
    for k in pos - 13..=pos {
        trs.push(hist[k].high - hist[k].low);
    }
    let atr = mean(&trs);
    Some(Refs {
        mid_ref: mid,
        sd_ref: sd,
        atr_ref: atr,
        upper_1sd_ref: mid + sd,
        upper_2sd_ref: mid + 2.0 * sd,
        upper_3sd_ref: mid + 3.0 * sd,
        lower_1sd_ref: mid - sd,
        lower_2sd_ref: mid - 2.0 * sd,
        lower_3sd_ref: mid - 3.0 * sd,
    })
}

/// Python `_direction`: (direction, ref_key) from the state's bb/ema features.
/// Fade-zone boundaries are GTE/LTE asymmetric, NOT symmetric: a-LONG is
/// `mid-3sd < close <= mid-2sd`, a-SHORT is `mid+2sd <= close < mid+3sd`
/// (the 3-SD boundary is open in both — a close beyond 3-SD is a trend).
fn direction(
    version: &str,
    variant: &str,
    close: f64,
    bb_mid: f64,
    bb_upper: f64,
    bb_lower: f64,
    ema_fast: f64,
    ema_slow: f64,
) -> (Option<&'static str>, &'static str) {
    if variant == "a" {
        if version == "v1" {
            let mid = bb_mid;
            let upper_3sd = mid + 1.5 * (bb_upper - mid);
            let lower_3sd = mid - 1.5 * (mid - bb_lower);
            if bb_upper <= close && close < upper_3sd {
                return (Some("SHORT"), "upper_2sd_ref");
            }
            if lower_3sd < close && close <= bb_lower {
                return (Some("LONG"), "lower_2sd_ref");
            }
            return (None, "");
        }
        // Tag & Re-entry: close has closed back inside the 2SD band after touching extreme
        if close < bb_upper && close > bb_mid && (bb_upper - close) < (bb_upper - bb_mid) * 0.5 {
            return (Some("SHORT"), "upper_2sd_ref");
        }
        if close > bb_lower && close < bb_mid && (close - bb_lower) < (bb_mid - bb_lower) * 0.5 {
            return (Some("LONG"), "lower_2sd_ref");
        }
        return (None, "");
    }
    if close > bb_mid && ema_fast > ema_slow {
        return (Some("LONG"), "mid_ref");
    }
    if close < bb_mid && ema_fast < ema_slow {
        return (Some("SHORT"), "mid_ref");
    }
    (None, "")
}

fn evaluate_variant(fm: &FeatMap, expert_id: &str, version: &str, variant: &str) -> ExpertEval {
    let sym = fm.symbol;
    // `_need`: close, bb_mid, bb_upper, bb_lower, bb_pct_b, ema_fast, ema_slow,
    // history — any missing required feature is NO_HABITAT (Python `_need`).
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let bb_mid = match fm.value("bb_mid") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let bb_upper = match fm.value("bb_upper") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let bb_lower = match fm.value("bb_lower") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let _bb_pct_b = match fm.value("bb_pct_b") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let ema_fast = match fm.value("ema_fast") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let ema_slow = match fm.value("ema_slow") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let (dir, ref_key) = direction(
        version, variant, close, bb_mid, bb_upper, bb_lower, ema_fast, ema_slow,
    );
    let direction = match dir {
        Some(d) => d,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    // The D-026 anchor uses the per-bar recomputed band stack (Python
    // `self._bb` from `_bb_series`), NOT the state bb_* features.
    let bb = bb_series(&fm.history);
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = match (variant, direction) {
        ("a", "LONG") => Box::new(move |i, b| {
            if i < BB_BASE_N - 1 {
                return false;
            }
            let (mid, sd) = bb[i];
            sd > 0.0 && mid - 3.0 * sd < b.close && b.close <= mid - 2.0 * sd
        }),
        ("a", "SHORT") => Box::new(move |i, b| {
            if i < BB_BASE_N - 1 {
                return false;
            }
            let (mid, sd) = bb[i];
            sd > 0.0 && mid + 2.0 * sd <= b.close && b.close < mid + 3.0 * sd
        }),
        ("b", "LONG") => Box::new(move |i, b| {
            if i < BB_BASE_N - 1 {
                return false;
            }
            b.close > bb[i].0 && b.ema_fast > b.ema_slow
        }),
        ("b", "SHORT") => Box::new(move |i, b| {
            if i < BB_BASE_N - 1 {
                return false;
            }
            b.close < bb[i].0 && b.ema_fast < b.ema_slow
        }),
        _ => unreachable!(),
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);
    let refs = match anchor_refs(&fm.history, &anchor) {
        Some(r) => r,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if refs.sd_ref <= 0.0 || refs.atr_ref <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // Python `_geometry`: common keys first, then the variant-specific legs.
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(refs.atr_ref)),
        ("variant", serde_json::json!(variant)),
    ]);
    if variant == "b" {
        // Setup 3: entry proxy at the 2-SD band, stop under the SMA (two
        // sigma), profit exit at the 1-SD band (one sigma).
        let stop_r = (2.0 * refs.sd_ref / refs.atr_ref).clamp(0.8, 2.0);
        let target_r = (refs.sd_ref / refs.atr_ref).clamp(0.8, 2.0);
        geometry.insert(
            "stop_r".to_string(),
            serde_json::json!(stop_r),
        );
        geometry.insert(
            "target_r".to_string(),
            serde_json::json!(target_r),
        );
        geometry.insert("mid_ref".to_string(), serde_json::json!(refs.mid_ref));
        if direction == "LONG" {
            geometry.insert(
                "upper_1sd_ref".to_string(),
                serde_json::json!(refs.upper_1sd_ref),
            );
            geometry.insert(
                "upper_2sd_ref".to_string(),
                serde_json::json!(refs.upper_2sd_ref),
            );
        } else {
            geometry.insert(
                "lower_1sd_ref".to_string(),
                serde_json::json!(refs.lower_1sd_ref),
            );
            geometry.insert(
                "lower_2sd_ref".to_string(),
                serde_json::json!(refs.lower_2sd_ref),
            );
        }
    } else {
        // Setup 2: fade the 2-SD band; the 3-SD stop and the 1-SD target are
        // each one band-sigma away.
        let r = (refs.sd_ref / refs.atr_ref).clamp(0.8, 2.0);
        geometry.insert("stop_r".to_string(), serde_json::json!(r));
        geometry.insert("target_r".to_string(), serde_json::json!(r));
        if direction == "SHORT" {
            geometry.insert(
                "upper_1sd_ref".to_string(),
                serde_json::json!(refs.upper_1sd_ref),
            );
            geometry.insert(
                "upper_2sd_ref".to_string(),
                serde_json::json!(refs.upper_2sd_ref),
            );
            geometry.insert(
                "upper_3sd_ref".to_string(),
                serde_json::json!(refs.upper_3sd_ref),
            );
        } else {
            geometry.insert(
                "lower_1sd_ref".to_string(),
                serde_json::json!(refs.lower_1sd_ref),
            );
            geometry.insert(
                "lower_2sd_ref".to_string(),
                serde_json::json!(refs.lower_2sd_ref),
            );
            geometry.insert(
                "lower_3sd_ref".to_string(),
                serde_json::json!(refs.lower_3sd_ref),
            );
        }
    }
    let ref_val = geometry.get(ref_key).and_then(|v| v.as_f64()).unwrap();
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_val);
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}

pub fn bollinger_reversion(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    // Default variant instance mirrors the Python oracle's default constructor
    // (`BollingerReversionExpert()` -> variant 'a', Setup 2).
    evaluate_variant(fm, expert_id, version, "a")
}
