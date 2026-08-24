//! breakout_retest: role-reversal retest on a breached significant level
//! (variant a), plus the double-top/bottom (b) and head-and-shoulders (c)
//! structure scans. Mirror src/v8/experts/breakout_retest.py bit-for-bit
//! (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4). The dispatch
//! carries no variant, so the entry point runs the default variant 'a' — the
//! instantiation the Python oracle is evaluated under (`BreakoutRetestExpert()`).

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

/// D-036 locked pattern-pivot flank for the double/H&S structure scans (the
/// global 32-bar history pin, O-020, keeps it small).
const PT_FLANK: usize = 3;

/// (direction, level, stop_price, height) — the `_variant_*` hit tuple;
/// `height` is None for variant a (no underlying pattern, family default
/// target applies).
type Hit = (String, f64, f64, Option<f64>);

// --- pivot lattice over the history window -------------------------------

fn pivot_highs(hist: &[HistBar]) -> Vec<(usize, f64)> {
    let mut out = Vec::new();
    for i in PT_FLANK..(hist.len() - PT_FLANK) {
        let hi = hist[i].high;
        let left = (i - PT_FLANK..i)
            .map(|j| hist[j].high)
            .fold(f64::NEG_INFINITY, f64::max);
        let right = (i + 1..i + 1 + PT_FLANK)
            .map(|j| hist[j].high)
            .fold(f64::NEG_INFINITY, f64::max);
        if hi > left && hi > right {
            out.push((i, hi));
        }
    }
    out
}

fn pivot_lows(hist: &[HistBar]) -> Vec<(usize, f64)> {
    let mut out = Vec::new();
    for i in PT_FLANK..(hist.len() - PT_FLANK) {
        let lo = hist[i].low;
        let left = (i - PT_FLANK..i)
            .map(|j| hist[j].low)
            .fold(f64::INFINITY, f64::min);
        let right = (i + 1..i + 1 + PT_FLANK)
            .map(|j| hist[j].low)
            .fold(f64::INFINITY, f64::min);
        if lo < left && lo < right {
            out.push((i, lo));
        }
    }
    out
}

/// max over `pivs` by price, first occurrence wins on ties (Python `max(key=)`).
fn max_by_price(pivs: &[(usize, f64)]) -> (usize, f64) {
    let mut best = pivs[0];
    for &p in &pivs[1..] {
        if p.1 > best.1 {
            best = p;
        }
    }
    best
}

/// min over `pivs` by price, first occurrence wins on ties (Python `min(key=)`).
fn min_by_price(pivs: &[(usize, f64)]) -> (usize, f64) {
    let mut best = pivs[0];
    for &p in &pivs[1..] {
        if p.1 < best.1 {
            best = p;
        }
    }
    best
}

// --- retest-hold predicates (frozen level; D-026 anchor scan) -------------

fn retest_long<'a>(hist: &'a [HistBar], level: f64) -> Box<dyn Fn(usize, &HistBar) -> bool + 'a> {
    Box::new(move |i, bar| {
        if i == 0 {
            return false;
        }
        if !(bar.low <= level && bar.close > level) {
            return false;
        }
        // The retest must follow a valid fresh breakout (<= 6 bars prior)
        let start = i.saturating_sub(6);
        (start..i).any(|j| hist[j].close > level)
    })
}

fn retest_short<'a>(hist: &'a [HistBar], level: f64) -> Box<dyn Fn(usize, &HistBar) -> bool + 'a> {
    Box::new(move |i, bar| {
        if i == 0 {
            return false;
        }
        if !(bar.high >= level && bar.close < level) {
            return false;
        }
        // The retest must follow a valid fresh breakout (<= 6 bars prior)
        let start = i.saturating_sub(6);
        (start..i).any(|j| hist[j].close < level)
    })
}

// --- variant detection ------------------------------------------------------

/// Role-reversal retest on the significant swing level (`swing_high_10` /
/// `swing_low_10`); no pattern, so height is None and the family default
/// target applies.
fn variant_a(hist: &[HistBar], fm: &FeatMap, atr: f64) -> Option<Hit> {
    let n = hist.len();
    let newest = &hist[n - 1];
    if let Some(hi) = fm.value("swing_high_10") {
        if hi > 0.0 && retest_long(hist, hi)(n - 1, newest) {
            let stop_price = newest.low.min(hi - 1.0 * atr);
            return Some(("LONG".to_string(), hi, stop_price, None));
        }
    }
    if let Some(lo) = fm.value("swing_low_10") {
        if lo > 0.0 && retest_short(hist, lo)(n - 1, newest) {
            let stop_price = newest.high.max(lo + 1.0 * atr);
            return Some(("SHORT".to_string(), lo, stop_price, None));
        }
    }
    None
}

/// Validation-level retest for a double-top / double-bottom. The validation
/// level is read from the structure itself (the trough/peak strictly between
/// the two most recent pivots), never from the state swing feature.
fn variant_b(hist: &[HistBar]) -> Option<Hit> {
    let n = hist.len();
    let newest = &hist[n - 1];
    let ph = pivot_highs(hist);
    if ph.len() >= 2 {
        let (i2, h2) = ph[ph.len() - 2];
        let (i1, h1) = ph[ph.len() - 1];
        // validation level = the trough strictly between the two peaks
        let mut level = f64::INFINITY;
        for j in (i2 + 1)..i1 {
            level = level.min(hist[j].low);
        }
        if h1 > level && h2 > level {
            // double top
            if (i1..(n - 1)).any(|j| hist[j].close < level)
                && retest_short(hist, level)(n - 1, newest)
            {
                let mx = h1.max(h2);
                return Some(("SHORT".to_string(), level, mx, Some(mx - level)));
            }
        }
    }
    let pl = pivot_lows(hist);
    if pl.len() >= 2 {
        let (i2, v2) = pl[pl.len() - 2];
        let (i1, v1) = pl[pl.len() - 1];
        // validation level = the peak strictly between the two troughs
        let mut level = f64::NEG_INFINITY;
        for j in (i2 + 1)..i1 {
            level = level.max(hist[j].high);
        }
        if v1 < level && v2 < level {
            // double bottom
            if (i1..(n - 1)).any(|j| hist[j].close > level)
                && retest_long(hist, level)(n - 1, newest)
            {
                let mn = v1.min(v2);
                return Some(("LONG".to_string(), level, mn, Some(level - mn)));
            }
        }
    }
    None
}

/// `(head, right_shoulder_price, neckline, right_shoulder_idx)` for an H&S
/// top on the history; None when no structure exists. Flat neckline = the
/// higher of the two flank troughs.
fn hs_top(hist: &[HistBar]) -> Option<(f64, f64, f64, usize)> {
    let ph = pivot_highs(hist);
    let pl = pivot_lows(hist);
    if ph.len() < 3 || pl.len() < 2 {
        return None;
    }
    let (head_i, head) = max_by_price(&ph);
    let lefts: Vec<(usize, f64)> = ph.iter().filter(|(i, _)| *i < head_i).copied().collect();
    let rights: Vec<(usize, f64)> = ph.iter().filter(|(i, _)| *i > head_i).copied().collect();
    if lefts.is_empty() || rights.is_empty() {
        return None;
    }
    let (li, left) = max_by_price(&lefts);
    let (ri, right) = max_by_price(&rights);
    if !(left < head && right < head) {
        return None;
    }
    let lt: Vec<f64> = pl
        .iter()
        .filter(|(i, _)| *i > li && *i < head_i)
        .map(|(_, v)| *v)
        .collect();
    let rt: Vec<f64> = pl
        .iter()
        .filter(|(i, _)| *i > head_i && *i < ri)
        .map(|(_, v)| *v)
        .collect();
    if lt.is_empty() || rt.is_empty() {
        return None;
    }
    let lmax = lt.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let rmax = rt.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let neckline = lmax.max(rmax);
    if neckline >= head {
        return None;
    }
    Some((head, right, neckline, ri))
}

/// `(head, left_shoulder_price, neckline, right_shoulder_idx)` for an H&S
/// bottom; None when no structure exists. Flat neckline = the lower of the
/// two flank peaks.
fn hs_bottom(hist: &[HistBar]) -> Option<(f64, f64, f64, usize)> {
    let ph = pivot_highs(hist);
    let pl = pivot_lows(hist);
    if ph.len() < 2 || pl.len() < 3 {
        return None;
    }
    let (head_i, head) = min_by_price(&pl);
    let lefts: Vec<(usize, f64)> = pl.iter().filter(|(i, _)| *i < head_i).copied().collect();
    let rights: Vec<(usize, f64)> = pl.iter().filter(|(i, _)| *i > head_i).copied().collect();
    if lefts.is_empty() || rights.is_empty() {
        return None;
    }
    let (li, left) = min_by_price(&lefts);
    let (ri, right) = min_by_price(&rights);
    if !(left > head && right > head) {
        return None;
    }
    let lp: Vec<f64> = ph
        .iter()
        .filter(|(i, _)| *i > li && *i < head_i)
        .map(|(_, h)| *h)
        .collect();
    let rp: Vec<f64> = ph
        .iter()
        .filter(|(i, _)| *i > head_i && *i < ri)
        .map(|(_, h)| *h)
        .collect();
    if lp.is_empty() || rp.is_empty() {
        return None;
    }
    let lmin = lp.iter().copied().fold(f64::INFINITY, f64::min);
    let rmin = rp.iter().copied().fold(f64::INFINITY, f64::min);
    let neckline = lmin.min(rmin);
    if neckline <= head {
        return None;
    }
    Some((head, left, neckline, ri))
}

/// Neckline retest for a head-and-shoulders (top or bottom); target is the
/// 1:1 head-to-neckline objective.
fn variant_c(hist: &[HistBar]) -> Option<Hit> {
    let n = hist.len();
    let newest = &hist[n - 1];
    if let Some((head, right, neckline, ri)) = hs_top(hist) {
        if (ri..(n - 1)).any(|j| hist[j].close < neckline)
            && retest_short(hist, neckline)(n - 1, newest)
        {
            return Some(("SHORT".to_string(), neckline, right, Some(head - neckline)));
        }
    }
    if let Some((head, left, neckline, ri)) = hs_bottom(hist) {
        if (ri..(n - 1)).any(|j| hist[j].close > neckline)
            && retest_long(hist, neckline)(n - 1, newest)
        {
            return Some(("LONG".to_string(), neckline, left, Some(neckline - head)));
        }
    }
    None
}

// --- evaluate ---------------------------------------------------------------

pub fn breakout_retest(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // The dispatch carries no variant selector; the Python oracle runs the
    // default instantiation (`BreakoutRetestExpert()`, variant_id='a').
    let variant = fm.variant(expert_id, "a");
    // `_need`: all five declared feature keys must be present (a not-yet-
    // computable feature is ABSENT, never a null — the D-024 veto).
    for name in ["close", "atr", "history", "swing_high_10", "swing_low_10"] {
        if !fm.features.contains_key(name) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // history feature value must be a non-empty tuple/list (`self._hist`).
    let hist_feat = match fm.features.get("history") {
        Some(f) => f,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let hist_arr = match hist_feat.value.as_array() {
        Some(a) => a,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if hist_arr.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let hist = &fm.history;
    let n = hist.len();
    if n < 2 * PT_FLANK + 1 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let hit = match variant {
        "a" => variant_a(hist, fm, atr),
        "b" => variant_b(hist),
        _ => variant_c(hist),
    };
    let (direction, level, stop_price, height) = match hit {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let raw_stop_r = if direction == "LONG" {
        (close - stop_price) / atr
    } else {
        (stop_price - close) / atr
    };
    let stop_r = raw_stop_r.clamp(0.8, 2.0);
    // 1:1 measuring objective: variant a has no underlying pattern, so the
    // target is the family default (1R); b/c target the 1:1 projection of the
    // pattern height in R (D-028: R is a price distance).
    let target_r = if variant == "a" {
        1.0
    } else {
        height.unwrap() / atr
    };
    if target_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let pred = if direction == "LONG" {
        retest_long(hist, level)
    } else {
        retest_short(hist, level)
    };
    let anchor = find_setup_anchor(hist, &*pred);
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(target_r)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant)),
        ("level_ref", serde_json::json!(level)),
        ("stop_ref", serde_json::json!(stop_price)),
    ]);
    if direction == "LONG" {
        geometry.insert("prior_low_ref".to_string(), serde_json::json!(stop_price));
    } else {
        geometry.insert("prior_high_ref".to_string(), serde_json::json!(stop_price));
    }
    let draft = Draft {
        direction: direction.clone(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    let fingerprint = format!(
        "{sym}:{variant}:{direction}:{:.6}:{:.6}:{:.6}",
        close, level, stop_price
    );
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
