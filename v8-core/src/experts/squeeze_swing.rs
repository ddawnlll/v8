//! SqueezeReleaseSwingExpert: Macro structural swing trading on multi-day compression breakout (D-140 / H-MACRO-01).
//!
//! Replaces intraday 1H micro-noise churn with patient, multi-day regime swing execution:
//! 1. Identifies 50-bar rolling Bollinger Bandwidth compression (bw_rank <= 0.35 / 0.25).
//! 2. Triggers on 48-hour to 72-hour macro range breakout (prior_h / prior_l).
//! 3. Predeclares 2.0 ATR structural stop distance for wide swing breathing room.

#![allow(dead_code)]

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::fsum;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["volatility", "trend", "participation", "history"];

pub const TARGET_R: f64 = 4.0;
pub const STOP_R: f64 = 2.0;
pub const EXPIRY_BARS: i64 = 336; // Up to 14 days max hold for macro swings

pub fn squeeze_swing(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let variant = fm.variant(expert_id, "default");
    let (max_bw_rank, lookback_bars, min_vol_ratio) = match variant {
        "m1" | "deep_squeeze" => (0.25, 48, 1.40),
        "m2" | "macro_72h" => (0.30, 72, 1.35),
        "m3" | "ultra_macro" => (0.25, 72, 1.40),
        _ => (0.35, 48, 1.30),
    };
    squeeze_swing_custom(fm, expert_id, version, max_bw_rank, lookback_bars, min_vol_ratio)
}

pub fn squeeze_swing_custom(
    fm: &FeatMap,
    expert_id: &str,
    version: &str,
    max_bw_rank: f64,
    lookback_bars: usize,
    min_vol_ratio: f64,
) -> ExpertEval {
    let sym = fm.symbol;
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };

    let n_hist = fm.history.len();
    if n_hist < lookback_bars.max(50) {
        return no_habitat(expert_id, version, fm.as_of);
    }

    // 1. Calculate rolling 20-bar Bollinger Bandwidth over the past 50 bars
    let mut bw_window = Vec::with_capacity(50);
    let start_idx = n_hist.saturating_sub(50);
    
    for k in start_idx..n_hist {
        let win_start = k.saturating_sub(19);
        let win_closes: Vec<f64> = fm.history[win_start..=k].iter().map(|b| b.close).collect();
        let len = win_closes.len() as f64;
        if len > 1.0 {
            let m = fsum(&win_closes) / len;
            let mut acc = 0.0;
            for c in &win_closes {
                acc += (c - m).powi(2);
            }
            let sd = (acc / len).sqrt();
            let bw = if m > 1e-6 { (4.0 * sd) / m } else { 0.0 };
            bw_window.push(bw);
        }
    }

    if bw_window.is_empty() {
        return no_setup(expert_id, version, fm.as_of);
    }

    let min_bw = bw_window.iter().cloned().fold(f64::INFINITY, f64::min);
    let max_bw = bw_window.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let cur_bw = bw_window[bw_window.len() - 1];
    let bw_rank = if (max_bw - min_bw) > 1e-6 {
        (cur_bw - min_bw) / (max_bw - min_bw)
    } else {
        0.5
    };

    // Squeeze condition: Bandwidth must be compressed in lower percentile
    if bw_rank > max_bw_rank {
        return no_setup(expert_id, version, fm.as_of);
    }

    // Volume expansion confirmation
    let cur_vol = fm.value("volume").unwrap_or(1.0);
    let vol_ma = fm.value("vol_smooth_ma").unwrap_or(1.0);
    let vol_ratio = if vol_ma > 1e-6 { cur_vol / vol_ma } else { 1.0 };
    if vol_ratio < min_vol_ratio {
        return no_setup(expert_id, version, fm.as_of);
    }

    // 2. Kaufman Trend Efficiency Ratio (ER over past 20 bars) - Rejects dead chop
    if n_hist >= 20 {
        let close_change = (close - fm.history[n_hist - 20].close).abs();
        let mut total_path = 0.0;
        for k in (n_hist - 19)..n_hist {
            total_path += (fm.history[k].close - fm.history[k - 1].close).abs();
        }
        let er = if total_path > 1e-6 { close_change / total_path } else { 0.0 };
        if er < 0.18 {
            return no_setup(expert_id, version, fm.as_of);
        }
    }

    // 3. Macro swing high and low strictly PIT
    let s_lookback = n_hist.saturating_sub(lookback_bars);
    let prior_high = fm.history[s_lookback..n_hist - 1]
        .iter()
        .map(|b| b.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let prior_low = fm.history[s_lookback..n_hist - 1]
        .iter()
        .map(|b| b.low)
        .fold(f64::INFINITY, f64::min);

    // 3. Macro Breakout Decision
    let mut decision_dir = None;
    if close > prior_high {
        decision_dir = Some("LONG");
    } else if close < prior_low {
        decision_dir = Some("SHORT");
    }

    if let Some(dir) = decision_dir {
        let draft = Draft {
            direction: dir.into(),
            birth_time: fm.as_of,
            risk_geometry: geom(vec![
                ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
                ("target_r", serde_json::json!(TARGET_R)),
                ("stop_r", serde_json::json!(STOP_R)),
                ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
                ("atr_ref", serde_json::json!(atr)),
                ("bw_rank", serde_json::json!(bw_rank)),
                ("lookback_bars", serde_json::json!(lookback_bars)),
            ]),
        };

        let anchor = if let Some(last) = fm.history.last() {
            last.event_id.clone()
        } else {
            format!("{sym}:{}:setup", fm.as_of)
        };
        let fingerprint = format!("{sym}:{dir}:{:.6}:{:.6}", close, bw_rank);
        candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
    } else {
        no_setup(expert_id, version, fm.as_of)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::{Feature, HistBar};

    #[test]
    fn test_squeeze_swing_triggers_on_compression_and_breakout() {
        let mut hist = Vec::new();
        for i in 0..30 {
            let c = if i % 2 == 0 { 110.0 } else { 90.0 };
            hist.push(HistBar {
                event_id: format!("ev-{i}"),
                open: c,
                high: c + 2.0,
                low: c - 2.0,
                close: c,
                ema_fast: 100.0,
                ema_slow: 100.0,
            });
        }

        for i in 30..60 {
            hist.push(HistBar {
                event_id: format!("ev-{i}"),
                open: 100.0,
                high: 100.2,
                low: 99.8,
                close: 100.0,
                ema_fast: 100.0,
                ema_slow: 100.0,
            });
        }

        // Add breakout bar
        hist.push(HistBar {
            event_id: "ev-60".to_string(),
            open: 100.0,
            high: 115.0,
            low: 100.0,
            close: 114.0,
            ema_fast: 101.0,
            ema_slow: 100.5,
        });

        let feats = vec![
            Feature {
                name: "close".to_string(),
                value: serde_json::json!(114.0),
                dtype: "float64".to_string(),
                feature_version: "v1".to_string(),
                max_input_available_time: 1000,
                quality: "GOOD".to_string(),
                null_reason: None,
                group: "raw".to_string(),
            },
            Feature {
                name: "atr".to_string(),
                value: serde_json::json!(2.0),
                dtype: "float64".to_string(),
                feature_version: "v1".to_string(),
                max_input_available_time: 1000,
                quality: "GOOD".to_string(),
                null_reason: None,
                group: "volatility".to_string(),
            },
            Feature {
                name: "volume".to_string(),
                value: serde_json::json!(2000.0),
                dtype: "float64".to_string(),
                feature_version: "v1".to_string(),
                max_input_available_time: 1000,
                quality: "GOOD".to_string(),
                null_reason: None,
                group: "volume".to_string(),
            },
            Feature {
                name: "vol_smooth_ma".to_string(),
                value: serde_json::json!(1000.0),
                dtype: "float64".to_string(),
                feature_version: "v1".to_string(),
                max_input_available_time: 1000,
                quality: "GOOD".to_string(),
                null_reason: None,
                group: "volume".to_string(),
            },
        ];
        let closure = crate::features::group_closure(&["volatility", "participation", "raw", "history"]);

        let fm = FeatMap {
            features: ProjectedFeatures::new(&feats, &closure),
            history: hist,
            as_of: 1000,
            symbol: "BTCUSDT",
            variant_overrides: &std::collections::HashMap::new(),
        };

        let ev = squeeze_swing(&fm, "squeeze_swing", "v1");
        assert_eq!(ev.decision, "CANDIDATE");
        assert_eq!(ev.draft.unwrap().direction, "LONG");
    }
}
