//! pattern_measuring_objective: evaluate() port — mirror src/v8/experts/pattern_measuring_objective.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! The Python family is 3 variants (head_shoulders default, double_top,
//! triangle) selected by constructor `variant_id` — separate instances. The
//! Rust dispatch surface (mod.rs `PortFn`) carries no variant parameter, so
//! this port evaluates the DEFAULT instance, which is the instance the parity
//! harness instantiates (`PatternMeasuringObjectiveExpert()`). The double_top
//! and triangle detectors are mirrored below for completeness but are not
//! reachable through the dispatch until a variant parameter exists.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const EXPIRY_BARS: i64 = 8;

/// The variant this port evaluates: the Python default instance
/// (PatternMeasuringObjectiveExpert() -> variant_id = "head_shoulders").
const VARIANT_ID: &str = "head_shoulders";

/// Declared, LOCKED constants (D-036; "declared, never fitted").
const PT_FLANK: usize = 3;          // structure-pivot flank on the 32-bar history
const TRIANGLE_WINDOW: usize = 20;  // convergence scan window (bars)
const TRIANGLE_WIDTH_MAX: f64 = 0.03; // max consolidation width (G-26 verbatim)

/// Python `max(items, key=x[1])`: FIRST maximum on ties (Python's max returns
/// the first maximal element; Rust's max_by_key returns the last).
fn max_high(items: &[(usize, f64)]) -> (usize, f64) {
    let mut best = items[0];
    for &x in &items[1..] {
        if x.1 > best.1 {
            best = x;
        }
    }
    best
}

/// Python `min(items, key=x[1])`: FIRST minimum on ties.
fn min_low(items: &[(usize, f64)]) -> (usize, f64) {
    let mut best = items[0];
    for &x in &items[1..] {
        if x.1 < best.1 {
            best = x;
        }
    }
    best
}

/// `_pivot_highs`: bar i whose high exceeds the flank highs on both sides.
fn pivot_highs(hist: &[HistBar]) -> Vec<(usize, f64)> {
    let mut out = Vec::new();
    for i in PT_FLANK..hist.len() - PT_FLANK {
        let hi = hist[i].high;
        let left = (i - PT_FLANK..i).map(|j| hist[j].high).fold(f64::NEG_INFINITY, f64::max);
        let right = (i + 1..i + 1 + PT_FLANK).map(|j| hist[j].high).fold(f64::NEG_INFINITY, f64::max);
        if hi > left && hi > right {
            out.push((i, hi));
        }
    }
    out
}

/// `_pivot_lows`: bar i whose low is below the flank lows on both sides.
fn pivot_lows(hist: &[HistBar]) -> Vec<(usize, f64)> {
    let mut out = Vec::new();
    for i in PT_FLANK..hist.len() - PT_FLANK {
        let lo = hist[i].low;
        let left = (i - PT_FLANK..i).map(|j| hist[j].low).fold(f64::INFINITY, f64::min);
        let right = (i + 1..i + 1 + PT_FLANK).map(|j| hist[j].low).fold(f64::INFINITY, f64::min);
        if lo < left && lo < right {
            out.push((i, lo));
        }
    }
    out
}

/// `_hs_top`: (head, neckline, right_shoulder_idx) or None.
fn hs_top(hist: &[HistBar]) -> Option<(f64, f64, usize)> {
    let ph = pivot_highs(hist);
    let pl = pivot_lows(hist);
    if ph.len() < 3 || pl.len() < 2 {
        return None;
    }
    let (head_i, head) = max_high(&ph);
    let lefts: Vec<(usize, f64)> = ph.iter().copied().filter(|&(i, _)| i < head_i).collect();
    let rights: Vec<(usize, f64)> = ph.iter().copied().filter(|&(i, _)| i > head_i).collect();
    if lefts.is_empty() || rights.is_empty() {
        return None;
    }
    let (li, left) = max_high(&lefts);
    let (ri, right) = max_high(&rights);
    if !(left < head && right < head) {
        return None;
    }
    let lt: Vec<f64> = pl.iter().copied().filter(|&(i, _)| li < i && i < head_i).map(|(_, v)| v).collect();
    let rt: Vec<f64> = pl.iter().copied().filter(|&(i, _)| head_i < i && i < ri).map(|(_, v)| v).collect();
    if lt.is_empty() || rt.is_empty() {
        return None;
    }
    let neckline = lt.iter().copied().fold(f64::NEG_INFINITY, f64::max)
        .max(rt.iter().copied().fold(f64::NEG_INFINITY, f64::max));
    if neckline >= head {
        return None;
    }
    Some((head, neckline, ri))
}

/// `_hs_bottom`: (head, neckline, right_shoulder_idx) or None.
fn hs_bottom(hist: &[HistBar]) -> Option<(f64, f64, usize)> {
    let ph = pivot_highs(hist);
    let pl = pivot_lows(hist);
    if ph.len() < 2 || pl.len() < 3 {
        return None;
    }
    let (head_i, head) = min_low(&pl);
    let lefts: Vec<(usize, f64)> = pl.iter().copied().filter(|&(i, _)| i < head_i).collect();
    let rights: Vec<(usize, f64)> = pl.iter().copied().filter(|&(i, _)| i > head_i).collect();
    if lefts.is_empty() || rights.is_empty() {
        return None;
    }
    let (li, left) = min_low(&lefts);
    let (ri, right) = min_low(&rights);
    if !(left > head && right > head) {
        return None;
    }
    let lp: Vec<f64> = ph.iter().copied().filter(|&(i, _)| li < i && i < head_i).map(|(_, v)| v).collect();
    let rp: Vec<f64> = ph.iter().copied().filter(|&(i, _)| head_i < i && i < ri).map(|(_, v)| v).collect();
    if lp.is_empty() || rp.is_empty() {
        return None;
    }
    let neckline = lp.iter().copied().fold(f64::INFINITY, f64::min)
        .min(rp.iter().copied().fold(f64::INFINITY, f64::min));
    if neckline <= head {
        return None;
    }
    Some((head, neckline, ri))
}

/// `_head_shoulders`: neckline break on the current close (no retest — entry
/// on the breakout), target = head-to-neckline height. Returns
/// (direction, level, stop_price, height, anchor).
fn head_shoulders(hist: &[HistBar]) -> Option<(String, f64, f64, f64, String)> {
    let close = hist[hist.len() - 1].close;
    if let Some((head, neckline, ri)) = hs_top(hist) {
        if close < neckline {
            let pred = |j: usize, bar: &HistBar| j >= ri && bar.close < neckline;
            let anchor = find_setup_anchor(hist, &pred);
            return Some(("SHORT".to_string(), neckline, head, head - neckline, anchor));
        }
    }
    if let Some((head, neckline, ri)) = hs_bottom(hist) {
        if close > neckline {
            let pred = |j: usize, bar: &HistBar| j >= ri && bar.close > neckline;
            let anchor = find_setup_anchor(hist, &pred);
            return Some(("LONG".to_string(), neckline, head, neckline - head, anchor));
        }
    }
    None
}

/// `_double`: validation-level break on the current close; target = the 1:1
/// validation-to-extreme projection. SHORT on the trough between the two most
/// recent pivot highs, LONG on the peak between the two most recent pivot lows.
#[allow(dead_code)] // mirrored; not reachable until a variant dispatch exists
fn double_detector(hist: &[HistBar]) -> Option<(String, f64, f64, f64, String)> {
    let close = hist[hist.len() - 1].close;
    let ph = pivot_highs(hist);
    if ph.len() >= 2 {
        let (i2, h2) = ph[ph.len() - 2];
        let (i1, h1) = ph[ph.len() - 1];
        let level = (i2 + 1..i1).map(|j| hist[j].low).fold(f64::INFINITY, f64::min);
        if h1 > level && h2 > level && close < level {
            let stop = h1.max(h2);
            let pred = |j: usize, bar: &HistBar| j >= i1 && bar.close < level;
            let anchor = find_setup_anchor(hist, &pred);
            return Some(("SHORT".to_string(), level, stop, stop - level, anchor));
        }
    }
    let pl = pivot_lows(hist);
    if pl.len() >= 2 {
        let (i2, v2) = pl[pl.len() - 2];
        let (i1, v1) = pl[pl.len() - 1];
        let level = (i2 + 1..i1).map(|j| hist[j].high).fold(f64::NEG_INFINITY, f64::max);
        if v1 < level && v2 < level && close > level {
            let stop = v1.min(v2);
            let pred = |j: usize, bar: &HistBar| j >= i1 && bar.close > level;
            let anchor = find_setup_anchor(hist, &pred);
            return Some(("LONG".to_string(), level, stop, level - stop, anchor));
        }
    }
    None
}

/// `_triangle_structure`: >= 2 pivot highs declining and >= 2 pivot lows
/// rising inside the trailing consolidation window (excluding the current bar).
#[allow(dead_code)] // mirrored; not reachable until a variant dispatch exists
fn triangle_structure(hist: &[HistBar]) -> bool {
    let n = hist.len();
    let lo = n.saturating_sub(1 + TRIANGLE_WINDOW);
    let mut ph: Vec<(usize, f64)> =
        pivot_highs(hist).into_iter().filter(|&(i, _)| lo <= i && i < n - 1).collect();
    let mut pl: Vec<(usize, f64)> =
        pivot_lows(hist).into_iter().filter(|&(i, _)| lo <= i && i < n - 1).collect();
    // Python `sorted((i, h) for ...)`: tuple order is index order (indices are
    // distinct), so sorting by the pivot index alone is equivalent.
    ph.sort_by_key(|&(i, _)| i);
    pl.sort_by_key(|&(i, _)| i);
    if ph.len() < 2 || pl.len() < 2 {
        return false;
    }
    ph[0].1 > ph[ph.len() - 1].1 && pl[0].1 < pl[pl.len() - 1].1
}

/// `_triangle`: close beyond the narrow consolidation range (breakout from a
/// converging range); target = 1:1 of the 20-bar range height.
#[allow(dead_code)] // mirrored; not reachable until a variant dispatch exists
fn triangle_detector(fm: &FeatMap) -> Option<(String, f64, f64, f64, String)> {
    let hist = &fm.history;
    let n = hist.len();
    let cr = fm.features.get("consolidation_range").map(|f| f.value.clone());
    let rh = fm.value("range_height_20");
    let cr = match cr {
        Some(c) => c,
        None => return None,
    };
    let rh = match rh {
        Some(v) => v,
        None => return None,
    };
    let h_ref = cr[0].as_f64()?;
    let l_ref = cr[1].as_f64()?;
    let width_ratio = cr[2].as_f64()?;
    if width_ratio > TRIANGLE_WIDTH_MAX || !triangle_structure(hist) {
        return None;
    }
    if n < 2 {
        return None;
    }
    let prev_close = hist[n - 2].close;
    if !(l_ref <= prev_close && prev_close <= h_ref) {
        return None;
    }
    let close = fm.value("close")?;
    if close > h_ref {
        let pred = |_j: usize, bar: &HistBar| bar.close > h_ref;
        let anchor = find_setup_anchor(hist, &pred);
        return Some(("LONG".to_string(), h_ref, l_ref, rh, anchor));
    }
    if close < l_ref {
        let pred = |_j: usize, bar: &HistBar| bar.close < l_ref;
        let anchor = find_setup_anchor(hist, &pred);
        return Some(("SHORT".to_string(), l_ref, h_ref, rh, anchor));
    }
    None
}

/// evaluate() — mirrors the Python default instance (variant head_shoulders).
pub fn pattern_measuring_objective(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    // `_need`: the seven declared features must all be present
    // (consolidation_range is structured — presence, not value read).
    for k in ["history", "window_high_20", "window_low_20",
              "range_height_20", "consolidation_range"] {
        if !fm.features.contains_key(k) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let n = fm.history.len();
    if n < 2 * PT_FLANK + 1 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let hit = match VARIANT_ID {
        "head_shoulders" => head_shoulders(&fm.history),
        "double_top" => double_detector(&fm.history),
        _ => triangle_detector(fm),
    };
    let (direction, level, stop_price, height, anchor) = match hit {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let stop_r = if direction == "LONG" { (close - stop_price) / atr } else { (stop_price - close) / atr };
    let target_r = height / atr;
    if stop_r <= 0.0 || target_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let mut entries = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(target_r)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(VARIANT_ID)),
        ("level_ref", serde_json::json!(level)),
        ("stop_ref", serde_json::json!(stop_price)),
    ];
    if direction == "LONG" {
        entries.push(("prior_low_ref", serde_json::json!(stop_price)));
    } else {
        entries.push(("prior_high_ref", serde_json::json!(stop_price)));
    }
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(entries),
    };
    let fingerprint = format!("{sym}:{VARIANT_ID}:{direction}:{close:.6}:{level:.6}:{stop_price:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
