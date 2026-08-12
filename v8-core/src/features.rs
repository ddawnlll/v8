//! D-053 feature-group projection (MARKET_STATE_CONTRACT; EXPERT_PROTOCOL §2).
//!
//! Mirrors `schema.py FEATURE_GROUPS` + `marketstate.py group_closure` and
//! `project_state`: an Expert's view contains only the features in its
//! declared `requires`-closure; a feature outside it is WITHHELD — never
//! "missing data". This is what makes `obv_adl_regime` (requires
//! participation+trend, reads atr/history) emit NO_HABITAT in the lab: atr
//! and history are outside its closure and are withheld, so its `_need` fails.
//! The Rust FeatMap must reproduce the same withholding or the parity gate
//! breaks on exactly such experts.

use std::collections::HashMap;

use crate::state::Feature;

/// group -> the groups it transitively requires (schema.py FEATURE_GROUPS).
pub const GROUP_REQUIRES: &[(&str, &[&str])] = &[
    ("raw", &[]),
    ("trend", &["raw"]),
    ("volatility", &["raw"]),
    ("location", &["raw"]),
    ("candle_shape", &["raw"]),
    ("oscillator", &["raw"]),
    ("participation", &["raw"]),
    ("session", &["raw"]),
    ("positioning", &["raw"]),
    ("response", &["trend", "volatility", "location", "participation"]),
    ("history", &["trend", "volatility"]),
];

/// group -> its feature names (schema.py FEATURE_GROUPS `features`).
pub const GROUP_FEATURES: &[(&str, &[&str])] = &[
    ("raw", &["close"]),
    ("trend", &["ema_fast", "ema_slow"]),
    ("volatility", &[
        "atr", "bb_mid", "bb_upper", "bb_lower", "bb_pct_b", "bb_bandwidth",
        "atr_locational", "atr_filtered_2sigma", "atr_2sigma_active",
        "keltner_u", "keltner_l", "starc_u", "starc_l", "atr_trend_phase",
    ]),
    ("location", &[
        "prior_high", "prior_low", "swing_high_5", "swing_high_10", "swing_high_20",
        "swing_low_5", "swing_low_10", "swing_low_20",
        "window_high_10", "window_low_10", "window_high_20", "window_low_20",
        "window_high_50", "window_low_50",
        "range_height_10", "range_height_20", "range_height_50",
        "fib_levels", "pivot_points_day", "consolidation_range", "gap_levels",
        "atr_band_stop",
    ]),
    ("candle_shape", &[
        "real_body", "body_range_ratio", "upper_shadow", "lower_shadow",
        "close_position", "inside_bar", "outside_bar", "gap_size", "gap_dir",
    ]),
    ("oscillator", &[
        "rsi14", "stoch_k", "stoch_d", "stochrsi", "cci20", "macd",
        "macd_signal", "macd_hist", "mom_14", "roc_14", "adx14", "osc_obos_quantile",
    ]),
    ("participation", &[
        "volume", "vol_zscore", "vol_min_proximity", "vol_smooth_ma", "obv",
        "adl", "cmf_20", "vwap", "bar_class",
    ]),
    ("session", &["hour_of_day_utc", "impulsive_window", "bar_of_session", "day_index"]),
    ("positioning", &["funding_rate", "open_interest", "long_short_skew"]),
    ("response", &[]),
    ("history", &["history"]),
];

/// The declared group set plus everything it transitively requires
/// (marketstate.py `group_closure`). Owned strings — the set is tiny and this
/// avoids threading input lifetimes into the projection helpers.
pub fn group_closure(groups: &[&str]) -> std::collections::HashSet<String> {
    let mut out = std::collections::HashSet::new();
    let mut stack: Vec<String> = groups.iter().map(|g| g.to_string()).collect();
    while let Some(g) = stack.pop() {
        if out.contains(&g) {
            continue;
        }
        if let Some((_, reqs)) = GROUP_REQUIRES.iter().find(|(n, _)| *n == g) {
            out.insert(g);
            stack.extend(reqs.iter().map(|r| r.to_string()));
        }
    }
    out
}

/// Is this bare feature name inside the closure? (FEATURE_TO_GROUP lookup.)
/// An unknown name is withheld (the Python view would raise KeyError at the
/// access site; a port that reads it must NO_HABITAT via its _need).
pub fn feature_in_closure(name: &str, closure: &std::collections::HashSet<String>) -> bool {
    let group = GROUP_FEATURES
        .iter()
        .find(|(_, feats)| feats.contains(&name))
        .map(|(g, _)| *g);
    match group {
        Some(g) => closure.contains(g),
        None => false,
    }
}

/// Project a full bare-keyed feature map down to the closure (project_state).
pub fn project_features<'a>(
    features: &'a HashMap<String, Feature>,
    closure: &std::collections::HashSet<String>,
) -> HashMap<String, Feature> {
    features
        .iter()
        .filter(|(name, _)| feature_in_closure(name, closure))
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect()
}

/// Whether the `history` feature is in the closure (withheld otherwise).
pub fn history_allowed(closure: &std::collections::HashSet<String>) -> bool {
    closure.contains("history")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn closure_is_transitive() {
        let c = group_closure(&["history"]);
        assert!(c.contains("history"));
        assert!(c.contains("trend"));
        assert!(c.contains("volatility"));
        assert!(c.contains("raw"));
        assert!(!c.contains("oscillator"));
    }

    #[test]
    fn obv_closure_withholds_atr_and_history() {
        // obv_adl_regime declares requires = (participation, trend) — atr
        // (volatility) and history are outside the closure (the D-053 gap
        // that makes the oracle emit NO_HABITAT on every bar).
        let c = group_closure(&["participation", "trend"]);
        assert!(feature_in_closure("cmf_20", &c));
        assert!(feature_in_closure("ema_fast", &c));
        assert!(feature_in_closure("close", &c));
        assert!(!feature_in_closure("atr", &c));
        assert!(!history_allowed(&c));
    }

    #[test]
    fn typical_closure_keeps_its_reads() {
        let c = group_closure(&["volatility", "history"]);
        assert!(feature_in_closure("atr", &c));
        assert!(feature_in_closure("close", &c));
        assert!(history_allowed(&c));
        assert!(!feature_in_closure("open_interest", &c));
    }
}
