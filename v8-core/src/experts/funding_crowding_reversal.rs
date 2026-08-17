//! funding_crowding_reversal: evaluate() port target (issue #88) — mirror src/v8/experts/funding_crowding_reversal.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! Ported variant 'a' — crowded-long reversal: funding >= +0.001 with price
//! confirmation (close below the prior 5-bar low) -> SHORT. The dispatch
//! table carries no variant parameter; the Python oracle the parity harness
//! runs is `FundingCrowdingReversalExpert()` (variant_id defaults to 'a').
//! On a tape without the funding channel the expert self-gates to NO_HABITAT
//! exactly as Python (the funding channel is a Phase 3 backlog; this is the
//! fail-loud data-absence contract, never a fabricated sentiment read).

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["positioning", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

// Declared, LOCKED thresholds (CRIT-9: numeric literals, never a fitted
// quantile). One pip of the funding rate on perp notional is the crowd line.
// Variant 'a' gates on the POSITIVE extreme only (crowded-long reversal); the
// Python module's NEG extreme (-0.001) feeds the LONG variants (b/c/d), which
// the port does not implement.
const FUNDING_EXTREME_POS: f64 = 0.001;
// Price-confirmation lookbacks (declared): the barrier broken (a/c) and the
// extension window (d).
const CONFIRM_N: usize = 5;
const EXTEND_N: usize = 10;

pub fn funding_crowding_reversal(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let variant = fm.variant(expert_id, "a");

    // _need(state, need): close, atr, history, funding_rate (open_interest is
    // appended only for variant 'c'). Any missing feature -> NO_HABITAT.
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if !fm.features.contains_key("history") {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let funding = match fm.value("funding_rate") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // atr <= 0 / empty history / funding None -> NO_HABITAT.
    if atr <= 0.0 || fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // oi_present is read but inert for variant 'a' (need_oi is False).
    let _oi_present = fm
        .features
        .get("open_interest")
        .map(|f| f.value.is_number())
        .unwrap_or(false);

    let n = fm.history.len();
    // _leg(close, closes, highs, lows, need_oi=False, oi_present, funding):
    // n < EXTEND_N + 1 -> None (no setup); variant 'a' SHORT fires only on
    // funding >= +0.001 with close < min(lows[-1-CONFIRM_N:-1]).
    let direction: Option<&str> = if n < EXTEND_N + 1 {
        None
    } else if funding >= FUNDING_EXTREME_POS
        && n > CONFIRM_N
        && close
            < fm.history[n - 1 - CONFIRM_N..n - 1]
                .iter()
                .map(|b| b.low)
                .fold(f64::INFINITY, f64::min)
    {
        Some("SHORT")
    } else {
        None
    };
    let direction = match direction {
        Some(d) => d,
        None => return no_setup(expert_id, version, fm.as_of),
    };

    // Stop beyond the confirmation barrier (countertrend stop doctrine,
    // Ch9.9.3.2): the frozen recent extreme for a/b/c; variant 'd' adds one
    // ATR. SHORT -> max(highs[-1-CONFIRM_N:-1]), LONG -> min(lows[...]).
    let (stop_r, barrier, ref_key) = if direction == "SHORT" {
        let barrier = fm.history[n - 1 - CONFIRM_N..n - 1]
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max);
        ((barrier - close) / atr, barrier, "prior_high_ref")
    } else {
        let barrier = fm.history[n - 1 - CONFIRM_N..n - 1]
            .iter()
            .map(|b| b.low)
            .fold(f64::INFINITY, f64::min);
        ((close - barrier) / atr, barrier, "prior_low_ref")
    };
    if stop_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }

    // _anchor_pred(direction, highs, lows): the price-confirmation run of the
    // setup (the funding leg is a state reading, not in the history tuples,
    // so the anchor captures the price-confirmation run — D-026).
    let hist = &fm.history;
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = if direction == "SHORT" {
        Box::new(move |i, _b| {
            i >= CONFIRM_N
                && hist[i].low
                    < hist[i - CONFIRM_N..i]
                        .iter()
                        .map(|b| b.low)
                        .fold(f64::INFINITY, f64::min)
        })
    } else {
        Box::new(move |i, _b| {
            i >= CONFIRM_N
                && hist[i].high
                    > hist[i - CONFIRM_N..i]
                        .iter()
                        .map(|b| b.high)
                        .fold(f64::NEG_INFINITY, f64::max)
        })
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);

    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(stop_r)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!(variant)),
            (ref_key, serde_json::json!(barrier)),
        ]),
    };
    let fingerprint = format!("{sym}:{variant}:{direction}:{close:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
