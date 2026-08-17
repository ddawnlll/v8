//! open_interest_divergence: evaluate() port target (issue #94) — mirror src/v8/experts/open_interest_divergence.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! The default-instantiated `OpenInterestDivergenceExpert()` uses variant 'a';
//! request-level overrides select the b/c/d legs, which are ported verbatim.
//!
//! DATA_BLOCKED self-gate: the derivatives tape is a Phase 3 backlog, so
//! `{sym}.open_interest` is ABSENT from the state on any tape without the OI
//! channel (absent, never zero — MARKET_STATE_CONTRACT §4). The Python `_need`
//! check fires on key presence and the expert returns NO_HABITAT; the port
//! reproduces that exactly (the state's `open_interest` value is never read —
//! only its key presence gates). On the synthetic fixture (kline-only) this
//! expert is NO_HABITAT on every bar, as the oracle is.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["positioning", "participation", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

// Declared, LOCKED constants (D-036 pattern). Price-direction lookback on the
// close series (declared; the book leaves the window unstated).
const LOOKBACK_N: usize = 5;
// Positioning proxy threshold: long_short_skew >= 1.0 = long-heavy.
const SKEW_LONG_HEAVY: f64 = 1.0;
// The variant the harness's oracle instantiates (default variant_id = 'a').

pub fn open_interest_divergence(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let variant = fm.variant(expert_id, "a");
    let sym = fm.symbol;

    // _need(state, need): key PRESENCE of close, atr, history, open_interest,
    // long_short_skew, vol_zscore. open_interest absent (no OI channel on the
    // tape) -> the DATA_BLOCKED self-gate fires: NO_HABITAT, never a
    // fabricated positioning read.
    for k in [
        "close",
        "atr",
        "history",
        "open_interest",
        "long_short_skew",
        "vol_zscore",
    ] {
        if !fm.features.contains_key(k) {
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
    let skew = match fm.value("long_short_skew") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let vol_zscore = match fm.value("vol_zscore") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // Python: atr is None or atr <= 0 or not isinstance(hist, (tuple, list))
    // or not hist or skew is None or vol_zscore is None -> NO_HABITAT.
    if atr <= 0.0 || fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }

    // closes = [float(b[4]) for b in hist] — bar-close column of the window.
    let closes: Vec<f64> = fm.history.iter().map(|b| b.close).collect();
    // _detect: len(closes) < LOOKBACK_N + 1 -> None -> NO_SETUP.
    if closes.len() < LOOKBACK_N + 1 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let price_up = close > closes[closes.len() - 1 - LOOKBACK_N];
    let vol_up = vol_zscore > 0.0;
    let vol_down = vol_zscore < 0.0;
    let long_heavy = skew >= SKEW_LONG_HEAVY;
    let short_heavy = skew < SKEW_LONG_HEAVY;
    let direction: Option<&str> = if variant == "a" && price_up && vol_up && long_heavy {
        Some("LONG")
    } else if (variant == "b" && price_up && vol_down && short_heavy)
        || (variant == "c" && !price_up && vol_up && long_heavy)
    {
        Some("SHORT")
    } else if variant == "d" && !price_up && vol_down && short_heavy {
        Some("LONG")
    } else {
        None
    };
    let direction = match direction {
        Some(d) => d,
        None => return no_setup(expert_id, version, fm.as_of),
    };

    // Stop behind the recent window extreme (the diverged barrier), frozen at
    // detection (Ch6.1). The window INCLUDES the current bar (the last
    // LOOKBACK_N history bars; history ends at t-1).
    let n = fm.history.len();
    let (stop_r, prior_low_ref, prior_high_ref) = if direction == "LONG" {
        // lows = [float(b[3]) for b in hist]; low_ref = min(lows[-LOOKBACK_N:])
        let low_ref = fm.history[n - LOOKBACK_N..]
            .iter()
            .map(|b| b.low)
            .fold(f64::INFINITY, f64::min);
        ((close - low_ref) / atr, Some(low_ref), None)
    } else {
        // highs = [float(b[2]) for b in hist]; high_ref = max(highs[-LOOKBACK_N:])
        let high_ref = fm.history[n - LOOKBACK_N..]
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max);
        ((high_ref - close) / atr, None, Some(high_ref))
    };
    if stop_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }

    // _anchor_pred(direction, closes): the price-direction leg (the run of
    // closes agreeing with the direction); the participation/positioning legs
    // are state readings (per-bar volume/OI are not in the history tuples), so
    // the anchor captures the price run (D-026).
    let pred: Box<dyn Fn(usize, &HistBar) -> bool> = if direction == "LONG" {
        Box::new(move |i, _b| i >= LOOKBACK_N && closes[i] > closes[i - LOOKBACK_N])
    } else {
        Box::new(move |i, _b| i >= LOOKBACK_N && closes[i] < closes[i - LOOKBACK_N])
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);

    let mut g = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(TARGET_R)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!(variant)),
    ];
    if let Some(low_ref) = prior_low_ref {
        g.push(("prior_low_ref", serde_json::json!(low_ref)));
    }
    if let Some(high_ref) = prior_high_ref {
        g.push(("prior_high_ref", serde_json::json!(high_ref)));
    }
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(g),
    };
    let fingerprint = format!("{sym}:{variant}:{direction}:{close:.6}");
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
