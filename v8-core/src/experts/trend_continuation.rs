//! trend_continuation: Dual-direction dynamic pullback continuation expert (D-138, Issue #282).
//!
//! Economic Thesis:
//!   1. Established Macro Trend: Fast EMA > Slow EMA (Long) or Fast EMA < Slow EMA (Short).
//!   2. Controlled Pullback: Price tests the dynamic value zone between Fast and Slow EMA.
//!   3. Structural Preservation: Price maintains higher low (Long) or lower high (Short) without breaking Slow EMA.
//!   4. Renewal Expansion: Rejection candle closes back in the direction of the dominant macro trend.

#![allow(dead_code)]

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["trend", "volatility", "history"];

pub const TARGET_R: f64 = 2.0;
pub const STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 16;

pub fn trend_continuation(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let fast = match fm.value("ema_fast") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let slow = match fm.value("ema_slow") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };

    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }

    let last_bar = &fm.history[fm.history.len() - 1];
    let open = last_bar.open;
    let high = last_bar.high;
    let low = last_bar.low;

    let is_long_trend = fast > slow;
    let is_short_trend = fast < slow;

    let (dir, is_setup) = if is_long_trend {
        let touched_fast = low <= fast * 1.002;
        let preserved_slow = close >= slow * 0.998;
        let bullish_rejection = close >= open;
        ("LONG", touched_fast && preserved_slow && bullish_rejection)
    } else if is_short_trend {
        let touched_fast = high >= fast * 0.998;
        let preserved_slow = close <= slow * 1.002;
        let bearish_rejection = close <= open;
        ("SHORT", touched_fast && preserved_slow && bearish_rejection)
    } else {
        ("NONE", false)
    };

    if !is_setup {
        if !is_long_trend && !is_short_trend {
            return no_habitat(expert_id, version, fm.as_of);
        }
        return no_setup(expert_id, version, fm.as_of);
    }

    let pred = |_i: usize, b: &HistBar| {
        (b.ema_fast > b.ema_slow && b.low <= b.ema_fast && b.close >= b.ema_slow)
            || (b.ema_fast < b.ema_slow && b.high >= b.ema_fast && b.close <= b.ema_slow)
    };
    let anchor = find_setup_anchor(&fm.history, &pred);

    let draft = Draft {
        direction: dir.into(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(STOP_R)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
        ]),
    };

    let fingerprint = format!("{sym}:{dir}:{:.6}:{:.6}:{:.6}", close, fast, slow);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
