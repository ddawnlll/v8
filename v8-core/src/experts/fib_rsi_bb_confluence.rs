//! fib_rsi_bb_confluence: evaluate() port — mirror src/v8/experts/fib_rsi_bb_confluence.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//! Three-leg confluence: BB fade zone (close in 2-SD..3-SD), Wilder-RSI dip
//! recovery (state feature + local series), fib 0.786 reclaim of the prior
//! impulse. Variant a (STRICT: all three legs agree) — the harness instantiates
//! `FibRsiBbConfluenceExpert()` with the default variant_id 'a'. The D-026
//! anchor is the consecutive run of bars where the SAME confluence predicate
//! holds, via base::find_setup_anchor.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["oscillator", "location", "volatility", "history"];

// Declared, frozen constants, inherited verbatim from the registered families
// (D-036/D-046 pattern; never fitted on the dev window).
const BB_BASE_N: usize = 20;  // bollinger_reversion.py:43
const RSI_OS: f64 = 30.0;     // rsi_stoch_reversion.py:45
const RSI_OB: f64 = 70.0;     // rsi_stoch_reversion.py:46
// The confluence fib leg uses the DEEPEST retracement (structural co-occurrence
// argument in the module docstring); it doubles as the post-entry
// deep-correction reference, as in fib_retracement_continuation.
const FIB_RATIO: f64 = 0.786;
// The harness runs FibRsiBbConfluenceExpert() with no variant argument, so the
// instance variant_id is the class default 'a' (STRICT).
const VARIANT: &str = "a";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Dir {
    Long,
    Short,
}

impl Dir {
    fn label(self) -> &'static str {
        match self {
            Dir::Long => "LONG",
            Dir::Short => "SHORT",
        }
    }
}

/// Python `_mean`: `sum(values) / len(values)`. Builtin `sum()` is plain
/// left-to-right double accumulation (CPython float fast path), so Rust's
/// `Iterator::sum` agrees bit-for-bit.
fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

/// Python `_std_pop`: `(sum((v - m) ** 2 for v in values) / len(values)) ** 0.5`.
/// `** 2` / `** 0.5` are libm pow — use `.powf`, not `x * x` / `.sqrt()`.
fn std_pop(values: &[f64]) -> f64 {
    let m = mean(values);
    (values.iter().map(|v| (*v - m).powf(2.0)).sum::<f64>() / values.len() as f64).powf(0.5)
}

/// Python `_bb_series`: per-bar (mid, sd) of the trailing 20 closes; None in
/// warmup. A degenerate window still yields a pair; `sd <= 0` is rejected by
/// the vote (mirrors Python, which also computes the pair and rejects there).
fn bb_series(hist: &[HistBar]) -> Vec<Option<(f64, f64)>> {
    let closes: Vec<f64> = hist.iter().map(|b| b.close).collect();
    let mut out = Vec::with_capacity(closes.len());
    for i in 0..closes.len() {
        if i >= BB_BASE_N - 1 {
            let win = &closes[i - BB_BASE_N + 1..i + 1];
            out.push(Some((mean(win), std_pop(win))));
        } else {
            out.push(None);
        }
    }
    out
}

/// Python `_rsi_value`.
fn rsi_value(avg_gain: f64, avg_loss: f64) -> f64 {
    if avg_loss == 0.0 {
        return if avg_gain > 0.0 { 100.0 } else { 50.0 };
    }
    if avg_gain == 0.0 {
        return 0.0;
    }
    100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
}

/// Python `_rsi_per_bar` (Wilder RSI over the local window; None before the
/// seed). Identical formula to marketstate's rsi14 over the local window.
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

/// Python `_bb_vote_at` (bollinger_reversion Setup 2): close between 2-SD and
/// 3-SD of the 20-bar SMA. Degenerate band (sd <= 0) is no level; a close
/// beyond 3-SD is a trend, not a reversion.
fn bb_vote_at(bb: &[Option<(f64, f64)>], i: usize, bar: &HistBar) -> Option<Dir> {
    if i < BB_BASE_N - 1 {
        return None;
    }
    let (mid, sd) = match bb[i] {
        Some(p) => p,
        None => return None,
    };
    if sd <= 0.0 {
        return None;
    }
    let close = bar.close;
    if mid - 3.0 * sd < close && close <= mid - 2.0 * sd {
        return Some(Dir::Long);
    }
    if mid + 2.0 * sd <= close && close < mid + 3.0 * sd {
        return Some(Dir::Short);
    }
    None
}

/// Python `_rsi_vote_at` (rsi_stoch_reversion variant a): the newest run sits
/// on the reverted side of its extreme AND the run start's predecessor is on
/// the extreme side. LONG checked first, mirroring the source's return-early
/// order.
fn rsi_vote_at(rsi: &[Option<f64>], i: usize) -> Option<Dir> {
    if i >= rsi.len() {
        return None;
    }
    let cur = match rsi[i] {
        Some(v) => v,
        None => return None,
    };
    if cur > RSI_OS {
        let mut s = i;
        while s > 0 && rsi[s - 1].map(|v| v > RSI_OS).unwrap_or(false) {
            s -= 1;
        }
        if s > 0 && rsi[s - 1].map(|v| v <= RSI_OS).unwrap_or(false) {
            return Some(Dir::Long);
        }
    }
    if cur < RSI_OB {
        let mut s = i;
        while s > 0 && rsi[s - 1].map(|v| v < RSI_OB).unwrap_or(false) {
            s -= 1;
        }
        if s > 0 && rsi[s - 1].map(|v| v >= RSI_OB).unwrap_or(false) {
            return Some(Dir::Short);
        }
    }
    None
}

/// Python `_fib_vote_at`: a close that reclaimed the deepest retracement of
/// the intact impulse. `fib_direction`/`fib_level` are frozen from the state's
/// fib_levels at detection, so the anchor scan uses the same level.
fn fib_vote_at(fib_direction: f64, fib_level: f64, bar: &HistBar) -> Option<Dir> {
    if fib_direction == 1.0 {
        if bar.close > fib_level && bar.low <= fib_level {
            return Some(Dir::Long);
        }
        None
    } else {
        if bar.close < fib_level && bar.high >= fib_level {
            return Some(Dir::Short);
        }
        None
    }
}

/// Python `_confluence_vote`. Variant a (STRICT): all three legs vote the same
/// direction. Variant b (MAJORITY): at least two of the three agree.
fn confluence_vote(variant: &str, votes: &[Option<Dir>; 3]) -> Option<Dir> {
    if variant == "a" {
        if let (Some(a), Some(b), Some(c)) = (votes[0], votes[1], votes[2]) {
            if a == b && b == c {
                return Some(a);
            }
        }
        return None;
    }
    let longs = votes.iter().filter(|v| **v == Some(Dir::Long)).count();
    let shorts = votes.iter().filter(|v| **v == Some(Dir::Short)).count();
    if longs >= 2 {
        return Some(Dir::Long);
    }
    if shorts >= 2 {
        return Some(Dir::Short);
    }
    None
}

/// Python `_retracement_level`: the level for `ratio` from the self-describing
/// fib tuple `(anchor, direction, retr, ext)`; None when absent.
fn retracement_level(fibs: &[serde_json::Value], ratio: f64) -> Option<f64> {
    let retr = match fibs.get(2).and_then(|v| v.as_array()) {
        Some(r) => r,
        None => return None,
    };
    for pair in retr {
        let r = match pair.get(0).and_then(|v| v.as_f64()) {
            Some(v) => v,
            None => continue,
        };
        if (r - ratio).abs() < 1e-9 {
            return pair.get(1).and_then(|v| v.as_f64());
        }
    }
    None
}

pub fn fib_rsi_bb_confluence(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // Python `_need`: every required feature key present, else NO_HABITAT.
    let need = ["close", "atr", "history", "bb_mid", "bb_upper", "bb_lower",
                "rsi14", "fib_levels"];
    for k in need {
        if !fm.features.contains_key(k) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // `atr is None` -> NO_HABITAT (Python checks the value, not just the key).
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // `not hist_value` -> NO_HABITAT (fm.history mirrors Python's self._hist).
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // `not isinstance(fibs, tuple) or len(fibs) != 4` -> NO_HABITAT.
    let fibs = match fm.features.get("fib_levels") {
        Some(f) => &f.value,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let fib_arr = match fibs.as_array() {
        Some(a) if a.len() == 4 => a,
        _ => return no_habitat(expert_id, version, fm.as_of),
    };
    // Fib warmup needs a confirmed swing pair (n_close >= 21 in marketstate);
    // a shorter window cannot host the confluence (habitat-unavailable).
    if fm.history.len() < 21 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let anchor_price = match fib_arr[0].as_f64() {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let direction = match fib_arr[1].as_f64() {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if !(direction == 1.0 || direction == -1.0) || anchor_price <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let fib_level = match retracement_level(fib_arr, FIB_RATIO) {
        Some(l) => l,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let fib_direction = direction;

    let bb = bb_series(&fm.history);
    let closes: Vec<f64> = fm.history.iter().map(|b| b.close).collect();
    let rsi = rsi_per_bar(&closes, 14);

    // Current-bar votes. The RSI leg additionally requires the STATE feature
    // to clear the threshold (the full-series Wilder value can disagree with
    // the local window near the boundary; the conservative gate from
    // rsi_stoch_reversion).
    let last = fm.history.len() - 1;
    let bb_v = bb_vote_at(&bb, last, &fm.history[last]);
    let mut rsi_v = rsi_vote_at(&rsi, last);
    let rsi_feat = match fm.value("rsi14") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if rsi_v == Some(Dir::Long) && !(rsi_feat > RSI_OS) {
        rsi_v = None;
    }
    if rsi_v == Some(Dir::Short) && !(rsi_feat < RSI_OB) {
        rsi_v = None;
    }
    let fib_v = fib_vote_at(fib_direction, fib_level, &fm.history[last]);
    let direction_sig = match confluence_vote(VARIANT, &[bb_v, rsi_v, fib_v]) {
        Some(d) => d,
        None => return no_setup(expert_id, version, fm.as_of),
    };

    // D-026 anchor: the consecutive run of bars where the same confluence
    // predicate holds (base.py find_setup_anchor, newest-false + 1).
    let confluence_at = |i: usize, b: &HistBar| {
        let votes = [
            bb_vote_at(&bb, i, b),
            rsi_vote_at(&rsi, i),
            fib_vote_at(fib_direction, fib_level, b),
        ];
        confluence_vote(VARIANT, &votes).is_some()
    };
    let anchor = find_setup_anchor(&fm.history, &confluence_at);

    // Geometry, frozen at detection (D-042 prior_*_ref pattern). The 78.6%
    // level doubles as the pre-entry invalidation and the post-entry
    // deep-correction reference; the frozen 3-SD band is the reversion-premise
    // reference. `variant` separates the episode keys.
    let mid = match fm.value("bb_mid") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let upper = match fm.value("bb_upper") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let lower = match fm.value("bb_lower") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(1.0)),
        ("stop_r", serde_json::json!(1.0)),
        ("expiry_bars", serde_json::json!(8)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(VARIANT)),
    ]);
    match direction_sig {
        Dir::Long => {
            geometry.insert("prior_low_ref".to_string(), serde_json::json!(fib_level));
            geometry.insert("lower_3sd_ref".to_string(),
                            serde_json::json!(mid - 1.5 * (mid - lower)));
        }
        Dir::Short => {
            geometry.insert("prior_high_ref".to_string(), serde_json::json!(fib_level));
            geometry.insert("upper_3sd_ref".to_string(),
                            serde_json::json!(mid + 1.5 * (upper - mid)));
        }
    }
    let fingerprint = format!("{sym}:{}:{}:{:.6}:{:.6}",
                              VARIANT, direction_sig.label(), fib_level, close);
    let draft = Draft {
        direction: direction_sig.label().to_string(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
