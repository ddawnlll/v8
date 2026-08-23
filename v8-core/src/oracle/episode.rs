//! Oracle Benchmark Hardening & 3-Tier Episode Formulation (Issue #279, D-138).
//!
//! Owning Authority: V8 Constitution Rules 1, 4, 5, 6, 18; TARGET_ORACLE_SPEC §§1-11.
//!
//! Taxonomy & Hierarchy:
//!   - O0: Raw Horizon Indicator (diagnostic forward excursion per event)
//!   - O1: Episode Oracle (causal, non-overlapping directional swings; canonical denominator for recall)
//!   - O2: Feasible Portfolio Oracle (capital, concurrency, margin, and venue fees)

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use crate::hash::Canon;

/// 3-Tier Oracle Classification Level (D-138).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum OracleTier {
    O0RawHorizon,
    O1Episode,
    O2FeasiblePortfolio,
}

/// Canonical parameters defining the Oracle measurement frame (D-138).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OracleDefinition {
    pub definition_id: String,
    pub symbol: String,
    pub horizon_bars: usize,
    pub min_mfe_pct: f64,
    pub max_mae_pct: f64,
    pub min_rr_ratio: f64,
    pub roundtrip_friction_bps: f64,
    pub non_overlapping_policy: bool,
}

impl OracleDefinition {
    pub fn new(
        symbol: &str,
        horizon_bars: usize,
        min_mfe_pct: f64,
        max_mae_pct: f64,
        min_rr_ratio: f64,
        roundtrip_friction_bps: f64,
        non_overlapping_policy: bool,
    ) -> Self {
        let mut c = Canon::new();
        c.push_str("OracleDefinition-v1");
        c.push_str(symbol);
        c.push_u64(horizon_bars as u64);
        c.push_f64(min_mfe_pct);
        c.push_f64(max_mae_pct);
        c.push_f64(min_rr_ratio);
        c.push_f64(roundtrip_friction_bps);
        c.push_str(if non_overlapping_policy { "true" } else { "false" });
        let definition_id = c.finish_blake3_hex();

        Self {
            definition_id,
            symbol: symbol.to_string(),
            horizon_bars,
            min_mfe_pct,
            max_mae_pct,
            min_rr_ratio,
            roundtrip_friction_bps,
            non_overlapping_policy,
        }
    }
}

/// A structured non-overlapping Oracle Opportunity Episode (O1).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OracleEpisode {
    pub episode_id: String,
    pub definition_id: String,
    pub symbol: String,
    pub direction: String, // "LONG" or "SHORT"
    pub entry_bar: usize,
    pub exit_bar: usize,
    pub duration_bars: usize,
    pub entry_price: f64,
    pub optimal_exit_price: f64,
    pub gross_mfe_pct: f64,
    pub gross_mae_pct: f64,
    pub gross_r: f64,
    pub habitat_type: String,
}

impl OracleEpisode {
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("OracleEpisode-v1");
        c.push_str(&self.definition_id);
        c.push_str(&self.symbol);
        c.push_str(&self.direction);
        c.push_u64(self.entry_bar as u64);
        c.push_u64(self.exit_bar as u64);
        c.push_f64(self.entry_price);
        c.push_f64(self.optimal_exit_price);
        c.finish_blake3_hex()
    }
}

/// Engine to extract canonical O1 episodes from historical price bars.
pub struct OracleEpisodeExtractor;

impl OracleEpisodeExtractor {
    pub fn extract_episodes(
        def: &OracleDefinition,
        highs: &[f64],
        lows: &[f64],
        closes: &[f64],
        volumes: &[f64],
        atrs: &[f64],
    ) -> Vec<OracleEpisode> {
        let n_bars = closes.len();
        let mut episodes = Vec::new();
        let mut i = 0;

        while i + def.horizon_bars < n_bars {
            let entry_price = closes[i];
            let atr = atrs.get(i).copied().unwrap_or(1.0).max(1e-6);

            let fwd_end = (i + def.horizon_bars + 1).min(n_bars);
            let fwd_highs = &highs[i + 1..fwd_end];
            let fwd_lows = &lows[i + 1..fwd_end];

            if fwd_highs.is_empty() || fwd_lows.is_empty() {
                i += 1;
                continue;
            }

            let mut max_h = fwd_highs[0];
            let mut max_h_rel_idx = 0;
            for (idx, &h) in fwd_highs.iter().enumerate() {
                if h > max_h {
                    max_h = h;
                    max_h_rel_idx = idx;
                }
            }

            let mut min_l = fwd_lows[0];
            let mut min_l_rel_idx = 0;
            for (idx, &l) in fwd_lows.iter().enumerate() {
                if l < min_l {
                    min_l = l;
                    min_l_rel_idx = idx;
                }
            }

            let max_h_bar = i + 1 + max_h_rel_idx;
            let min_l_bar = i + 1 + min_l_rel_idx;

            // Long metrics
            let long_mae_price = lows[i + 1..=max_h_bar].iter().copied().fold(f64::INFINITY, f64::min);
            let long_mfe_pct = (max_h - entry_price) / entry_price;
            let long_mae_pct = (entry_price - long_mae_price).max(0.0) / entry_price;

            // Short metrics
            let short_mae_price = highs[i + 1..=min_l_bar].iter().copied().fold(f64::NEG_INFINITY, f64::max);
            let short_mfe_pct = (entry_price - min_l) / entry_price;
            let short_mae_pct = (short_mae_price - entry_price).max(0.0) / entry_price;

            let mut admitted_ep = None;

            if long_mfe_pct >= def.min_mfe_pct
                && long_mae_pct <= def.max_mae_pct
                && (long_mfe_pct / long_mae_pct.max(0.001)) >= def.min_rr_ratio
            {
                let dur = max_h_bar.saturating_sub(i).max(1);
                let gross_r = (max_h - entry_price) / atr;
                let hab = if volumes.get(i).copied().unwrap_or(1.0) > 1.2 {
                    "TrendExpansionBreakout"
                } else {
                    "TrendPullbackContinuation"
                };

                let mut ep = OracleEpisode {
                    episode_id: String::new(),
                    definition_id: def.definition_id.clone(),
                    symbol: def.symbol.clone(),
                    direction: "LONG".to_string(),
                    entry_bar: i,
                    exit_bar: max_h_bar,
                    duration_bars: dur,
                    entry_price,
                    optimal_exit_price: max_h,
                    gross_mfe_pct: long_mfe_pct * 100.0,
                    gross_mae_pct: long_mae_pct * 100.0,
                    gross_r,
                    habitat_type: hab.to_string(),
                };
                ep.episode_id = ep.compute_id();
                admitted_ep = Some(ep);
            } else if short_mfe_pct >= def.min_mfe_pct
                && short_mae_pct <= def.max_mae_pct
                && (short_mfe_pct / short_mae_pct.max(0.001)) >= def.min_rr_ratio
            {
                let dur = min_l_bar.saturating_sub(i).max(1);
                let gross_r = (entry_price - min_l) / atr;
                let hab = if volumes.get(i).copied().unwrap_or(1.0) > 1.2 {
                    "TrendExpansionBreakout"
                } else {
                    "TrendPullbackContinuation"
                };

                let mut ep = OracleEpisode {
                    episode_id: String::new(),
                    definition_id: def.definition_id.clone(),
                    symbol: def.symbol.clone(),
                    direction: "SHORT".to_string(),
                    entry_bar: i,
                    exit_bar: min_l_bar,
                    duration_bars: dur,
                    entry_price,
                    optimal_exit_price: min_l,
                    gross_mfe_pct: short_mfe_pct * 100.0,
                    gross_mae_pct: short_mae_pct * 100.0,
                    gross_r,
                    habitat_type: hab.to_string(),
                };
                ep.episode_id = ep.compute_id();
                admitted_ep = Some(ep);
            }

            if let Some(ep) = admitted_ep {
                let next_step = if def.non_overlapping_policy { ep.exit_bar } else { i + 1 };
                episodes.push(ep);
                i = next_step;
            } else {
                i += 1;
            }
        }

        episodes
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_oracle_definition_deterministic_hashing() {
        let def1 = OracleDefinition::new("BTCUSDT", 24, 0.02, 0.01, 2.0, 10.0, true);
        let def2 = OracleDefinition::new("BTCUSDT", 24, 0.02, 0.01, 2.0, 10.0, true);
        let def3 = OracleDefinition::new("ETHUSDT", 24, 0.02, 0.01, 2.0, 10.0, true);

        assert_eq!(def1.definition_id, def2.definition_id);
        assert_ne!(def1.definition_id, def3.definition_id);
    }

    #[test]
    fn test_oracle_episode_extraction_and_non_overlap() {
        let def = OracleDefinition::new("BTCUSDT", 4, 0.02, 0.01, 2.0, 10.0, true);
        let highs = vec![100.0, 101.0, 103.0, 101.0, 100.0, 105.0, 102.0, 101.0];
        let lows = vec![99.0, 99.5, 99.5, 99.0, 98.0, 100.0, 100.0, 99.0];
        let closes = vec![100.0, 100.5, 102.5, 100.0, 99.0, 104.0, 101.0, 100.0];
        let volumes = vec![1.0; 8];
        let atrs = vec![1.0; 8];

        let eps = OracleEpisodeExtractor::extract_episodes(&def, &highs, &lows, &closes, &volumes, &atrs);
        assert!(!eps.is_empty());
        assert_eq!(eps[0].direction, "LONG");
        assert_eq!(eps[0].entry_bar, 0);
        assert_eq!(eps[0].exit_bar, 2);
        assert!(eps[0].compute_id().len() == 64);
    }
}
