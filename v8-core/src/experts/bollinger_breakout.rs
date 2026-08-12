//! bollinger_breakout: evaluate() port — mirror src/v8/experts/bollinger_breakout.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Variant `a` (Setup 1: close beyond the SMA, enter toward the 1-SD band,
//! target the 2-SD band) is the evaluated variant — the parity harness runs
//! `BollingerBreakoutExpert()` with the class-default variant_id 'a'. The full
//! a/b/c machinery mirrors the Python source; the geometry carries the variant
//! key. The band stack is FROZEN at the setup anchor (D-026), not at the
//! detection bar; a degenerate band (sd_ref <= 0 or atr_ref <= 0) or an
//! anchor whose 20-bar context leaves the history window is NO_HABITAT.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::{fsum, HistBar};

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["volatility", "history"];

// Declared, frozen constants (D-036 pattern): the marketstate bb_* features
// are SMA20 +/- 2*sigma; the book's 1-SD/3-SD levels derive from them.
const BB_BASE_N: usize = 20;
// E-08 variant c: squeeze lookback for "bandwidth at an extended low" before
// the closing band violation (book Ch12 bandwidth/squeeze doctrine, H04).
const SQUEEZE_LOOKBACK: usize = 10;

/// The frozen band stack + ATR14 at the setup anchor (Python `_anchor_refs`).
/// Only the refs the geometry/fingerprint read are carried (the Python 3-SD
/// refs are computed but never emitted into the risk_geometry).
struct AnchorRefs {
    mid_ref: f64,
    sd_ref: f64,
    atr_ref: f64,
    upper_1sd_ref: f64,
    upper_2sd_ref: f64,
    lower_1sd_ref: f64,
    lower_2sd_ref: f64,
}

/// CPython `_mean` = `sum(values) / len(values)` — sum() is compensated
/// (state::fsum, bit-identical to CPython 3.12+).
fn mean(values: &[f64]) -> f64 {
    fsum(values) / values.len() as f64
}

/// CPython `_std_pop`: `(sum((v - m) ** 2 for v in values) / len) ** 0.5`.
/// `(v - m) ** 2` and `** 0.5` are libm pow; black_box keeps the exponents
/// opaque so LLVM cannot fold pow(x, 2.0) -> x*x or pow(x, 0.5) -> sqrt
/// (COMPUTE_SCHEDULING_SPEC §5).
fn std_pop(values: &[f64]) -> f64 {
    let m = mean(values);
    let mut acc = Vec::with_capacity(values.len());
    for v in values {
        acc.push((v - m).powf(std::hint::black_box(2.0)));
    }
    (fsum(&acc) / values.len() as f64).powf(std::hint::black_box(0.5))
}

/// Per-bar (mid, sd) of the trailing 20 closes; None in warmup (Python
/// `_bb_series`).
fn bb_series(hist: &[HistBar]) -> Vec<Option<(f64, f64)>> {
    let closes: Vec<f64> = hist.iter().map(|b| b.close).collect();
    let mut out = Vec::with_capacity(closes.len());
    for i in 0..closes.len() {
        if i >= BB_BASE_N - 1 {
            let win = &closes[i - BB_BASE_N + 1..=i];
            out.push(Some((mean(win), std_pop(win))));
        } else {
            out.push(None);
        }
    }
    out
}

/// Per-bar bandwidth (upper-lower)/mid = 4*sd/mid (Python `_bw_series`; None
/// where the bb pair is not computable).
fn bw_series(bb: &[Option<(f64, f64)>]) -> Vec<Option<f64>> {
    bb.iter()
        .map(|ms| match ms {
            None => None,
            Some((mid, sd)) => Some(if *mid != 0.0 { 4.0 * sd / mid } else { 0.0 }),
        })
        .collect()
}

/// Frozen band stack + ATR14 at the setup anchor, or None when the anchor's
/// 20-bar context is not fully inside the history window (Python
/// `_anchor_refs`; the pos < 13 bound is subsumed by pos < BB_BASE_N - 1).
fn anchor_refs(hist: &[HistBar], anchor_event_id: &str) -> Option<AnchorRefs> {
    let pos = hist.iter().position(|b| b.event_id == anchor_event_id)?;
    if pos < BB_BASE_N - 1 || pos < 13 {
        return None;
    }
    let closes: Vec<f64> = hist.iter().map(|b| b.close).collect();
    let win = &closes[pos - BB_BASE_N + 1..=pos];
    let mid = mean(win);
    let sd = std_pop(win);
    let mut atr_acc = Vec::with_capacity(14);
    for k in pos - 13..=pos {
        atr_acc.push(hist[k].high - hist[k].low);
    }
    let atr = mean(&atr_acc);
    Some(AnchorRefs {
        mid_ref: mid,
        sd_ref: sd,
        atr_ref: atr,
        upper_1sd_ref: mid + sd,
        upper_2sd_ref: mid + 2.0 * sd,
        lower_1sd_ref: mid - sd,
        lower_2sd_ref: mid - 2.0 * sd,
    })
}

/// Per-variant per-bar predicates (Python `_pred_a|b|c_{long,short}`) — the
/// D-026 anchor scan predicate for the selected direction.
fn pred_for<'a>(
    variant: &str,
    direction: &str,
    bb: &'a [Option<(f64, f64)>],
    bw: &'a [Option<f64>],
) -> Box<dyn Fn(usize, &HistBar) -> bool + 'a> {
    if variant == "a" {
        if direction == "LONG" {
            Box::new(move |i, b| {
                if i < BB_BASE_N - 1 {
                    return false;
                }
                b.close > bb[i].unwrap().0
            })
        } else {
            Box::new(move |i, b| {
                if i < BB_BASE_N - 1 {
                    return false;
                }
                b.close < bb[i].unwrap().0
            })
        }
    } else if variant == "b" {
        if direction == "LONG" {
            Box::new(move |i, b| {
                if i < BB_BASE_N - 1 {
                    return false;
                }
                let (mid, sd) = bb[i].unwrap();
                b.close > mid + 2.0 * sd
            })
        } else {
            Box::new(move |i, b| {
                if i < BB_BASE_N - 1 {
                    return false;
                }
                let (mid, sd) = bb[i].unwrap();
                b.close < mid - 2.0 * sd
            })
        }
    } else if direction == "LONG" {
        Box::new(move |i, b| {
            if i < BB_BASE_N - 1 + SQUEEZE_LOOKBACK + 1 {
                return false;
            }
            let (mid, sd) = bb[i].unwrap();
            if !(b.close > mid + 2.0 * sd) {
                return false;
            }
            // The PRIOR bar was at a fresh bandwidth low (the squeeze).
            bw[i - 1].unwrap() < bw[i - 1 - SQUEEZE_LOOKBACK..i - 1]
                .iter()
                .map(|x| x.unwrap())
                .fold(f64::INFINITY, f64::min)
        })
    } else {
        Box::new(move |i, b| {
            if i < BB_BASE_N - 1 + SQUEEZE_LOOKBACK + 1 {
                return false;
            }
            let (mid, sd) = bb[i].unwrap();
            if !(b.close < mid - 2.0 * sd) {
                return false;
            }
            bw[i - 1].unwrap() < bw[i - 1 - SQUEEZE_LOOKBACK..i - 1]
                .iter()
                .map(|x| x.unwrap())
                .fold(f64::INFINITY, f64::min)
        })
    }
}

pub fn bollinger_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    // _need: every required feature present, else NO_HABITAT.
    let need = ["close", "bb_mid", "bb_upper", "bb_lower", "bb_pct_b",
                "bb_bandwidth", "history"];
    for k in need {
        if !fm.features.contains_key(k) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // Empty history (or a non-tuple history value) is no habitat.
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let hist = &fm.history;
    let bb = bb_series(hist);
    let bw = bw_series(&bb);

    // The evaluated variant: the harness instantiates the class-default
    // variant_id 'a' (BollingerBreakoutExpert()); the full a/b/c machinery is
    // mirrored so the geometry carries the variant key.
    let variant = "a";

    // _direction: decided by the newest bar on the SAME condition the anchor
    // predicate evaluates per history bar (a gate that slides the reference
    // would make the anchor inconsistent with the gate).
    let (direction, ref_key): (&str, &str) = if variant == "a" {
        let mid = match fm.value("bb_mid") {
            Some(v) => v,
            None => return no_habitat(expert_id, version, fm.as_of),
        };
        if close > mid {
            ("LONG", "mid_ref")
        } else if close < mid {
            ("SHORT", "mid_ref")
        } else {
            return no_setup(expert_id, version, fm.as_of);
        }
    } else if variant == "b" {
        let pct = match fm.value("bb_pct_b") {
            Some(v) => v,
            None => return no_habitat(expert_id, version, fm.as_of),
        };
        if pct > 1.0 {
            ("LONG", "upper_2sd_ref")
        } else if pct < 0.0 {
            ("SHORT", "lower_2sd_ref")
        } else {
            return no_setup(expert_id, version, fm.as_of);
        }
    } else {
        // variant c: closing violation WITH the squeeze precondition.
        let pct = match fm.value("bb_pct_b") {
            Some(v) => v,
            None => return no_habitat(expert_id, version, fm.as_of),
        };
        let p = hist.len() - 1;
        let squeeze = p >= BB_BASE_N - 1 + SQUEEZE_LOOKBACK + 1
            && bw[p - 1].is_some()
            && bw[p - 1].unwrap()
                < bw[p - 1 - SQUEEZE_LOOKBACK..p - 1]
                    .iter()
                    .map(|x| x.unwrap())
                    .fold(f64::INFINITY, f64::min);
        if pct > 1.0 && squeeze {
            ("LONG", "upper_2sd_ref")
        } else if pct < 0.0 && squeeze {
            ("SHORT", "lower_2sd_ref")
        } else {
            return no_setup(expert_id, version, fm.as_of);
        }
    };

    let pred = pred_for(variant, direction, &bb, &bw);
    let anchor = find_setup_anchor(hist, &*pred);
    let refs = match anchor_refs(hist, &anchor) {
        Some(r) => r,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // A degenerate band (flat closes: sd == 0) or a non-positive risk unit is
    // no habitat: the geometry would be a zero-distance stop/target.
    if refs.sd_ref <= 0.0 || refs.atr_ref <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }

    let sd = refs.sd_ref;
    let atr = refs.atr_ref;
    let mut entries = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant)),
        ("mid_ref", serde_json::json!(refs.mid_ref)),
    ];
    if variant == "a" {
        // Setup 1: entry proxy at the 1-SD band; the SMA stop and the 2-SD
        // target are each one band-sigma away (Ch12 p480-481).
        let r = sd / atr;
        entries.push(("target_r", serde_json::json!(r)));
        entries.push(("stop_r", serde_json::json!(r)));
        if direction == "LONG" {
            entries.push(("upper_1sd_ref", serde_json::json!(refs.upper_1sd_ref)));
            entries.push(("upper_2sd_ref", serde_json::json!(refs.upper_2sd_ref)));
        } else {
            entries.push(("lower_1sd_ref", serde_json::json!(refs.lower_1sd_ref)));
            entries.push(("lower_2sd_ref", serde_json::json!(refs.lower_2sd_ref)));
        }
    } else {
        // Variants b/c: the 2-SD band is already violated at entry; the stop
        // is the central value (book caveat, two sigma away) and the target is
        // the family 1:1 default.
        let r = 2.0 * sd / atr;
        entries.push(("target_r", serde_json::json!(r)));
        entries.push(("stop_r", serde_json::json!(r)));
        if direction == "LONG" {
            entries.push(("upper_2sd_ref", serde_json::json!(refs.upper_2sd_ref)));
        } else {
            entries.push(("lower_2sd_ref", serde_json::json!(refs.lower_2sd_ref)));
        }
    }
    let geometry = geom(entries);
    let sym = fm.symbol;
    let ref_val = geometry.get(ref_key).and_then(|v| v.as_f64()).unwrap();
    let fingerprint = format!("{sym}:{:.6}:{:.6}", close, ref_val);
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
