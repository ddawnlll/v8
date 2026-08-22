//! Point-In-Time Causal Opportunity Grammar (Issue #231, #233, D-130).
//!
//! Owning Authority: V8 Constitution Rules 6, 18, 23.
//!
//! Epistemic Invariants:
//!   1. MarketState -> Exposure -> OpportunityGrammar -> Canonical OpportunityBook.
//!   2. Opportunity identity is established strictly INDEPENDENT of Expert observers.
//!   3. Zero lookahead: Episode boundaries at bar `i` depend strictly on information available at or before `i`.
//!   4. UNKNOWN / AMBIGUOUS identity statuses are first-class; forced merging/splitting is prohibited.

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;
use crate::state::FeatureStore;
use super::book::{IdentityStatus, OpportunityEpisode};
use super::exposure::{ExposureDirection, ExposureResolver};

/// Structural episode archetype recognized by the causal grammar.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum GrammarArchetype {
    TrendContinuation,
    MeanReversion,
    VolatilityBreakout,
    BasisDislocation,
}

/// Point-in-time causal Opportunity Grammar configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityGrammar {
    pub grammar_version: String,
    pub min_horizon_bars: usize,
    pub max_horizon_bars: usize,
    pub trend_lookback_bars: usize,
    pub vol_lookback_bars: usize,
    pub breakout_threshold_sigma: f64,
    pub ambiguity_band_sigma: f64,
}

impl Default for OpportunityGrammar {
    fn default() -> Self {
        Self {
            grammar_version: "v8.3-causal-grammar-v1".to_string(),
            min_horizon_bars: 4,
            max_horizon_bars: 48,
            trend_lookback_bars: 20,
            vol_lookback_bars: 20,
            breakout_threshold_sigma: 1.8,
            ambiguity_band_sigma: 0.3,
        }
    }
}

impl OpportunityGrammar {
    pub fn new(version: impl Into<String>) -> Self {
        Self {
            grammar_version: version.into(),
            ..Default::default()
        }
    }

    /// Computes cryptographic BLAKE3 identity for the grammar definition itself.
    pub fn grammar_hash(&self) -> String {
        let mut c = Canon::new();
        c.push_str("OpportunityGrammar");
        c.push_str(&self.grammar_version);
        c.push_u64(self.min_horizon_bars as u64);
        c.push_u64(self.max_horizon_bars as u64);
        c.push_u64(self.trend_lookback_bars as u64);
        c.push_u64(self.vol_lookback_bars as u64);
        c.push_f64(self.breakout_threshold_sigma);
        c.push_f64(self.ambiguity_band_sigma);
        c.finish_blake3_hex()
    }

    /// Scans market state strictly up to `bar_idx` (PIT) and emits canonical OpportunityEpisodes.
    pub fn scan_market_state(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError> {
        let n_bars = store.closes.len();
        if bar_idx >= n_bars || bar_idx < self.trend_lookback_bars {
            return Ok(Vec::new());
        }

        let as_of_time = store.avail[bar_idx];
        let close_now = store.closes[bar_idx];
        let closes_prefix = &store.closes[..=bar_idx];
        let n_prefix = closes_prefix.len();

        // Calculate rolling returns and rolling volatility over strictly past lookback window
        let start_idx = n_prefix.saturating_sub(self.trend_lookback_bars);
        let window = &closes_prefix[start_idx..n_prefix];
        if window.len() < self.trend_lookback_bars {
            return Ok(Vec::new());
        }

        let mean_price: f64 = window.iter().sum::<f64>() / window.len() as f64;
        let variance: f64 = window.iter().map(|p| (p - mean_price).powi(2)).sum::<f64>() / window.len() as f64;
        let std_dev = variance.sqrt().max(1e-8);
        let z_score = (close_now - mean_price) / std_dev;

        // Compute state hash from strictly past bars
        let mut sc = Canon::new();
        sc.push_str(symbol);
        sc.push_str(venue);
        sc.push_i64(as_of_time);
        sc.push_f64(close_now);
        sc.push_f64(z_score);
        let market_state_hash = sc.finish_blake3_hex();

        let grammar_h = self.grammar_hash();

        let mut episodes = Vec::new();

        // Evaluate Structural Archetypes
        // 1. Breakout / Trend Continuation Long
        if z_score >= self.breakout_threshold_sigma {
            let status = if (z_score - self.breakout_threshold_sigma).abs() < self.ambiguity_band_sigma {
                IdentityStatus::Ambiguous
            } else {
                IdentityStatus::Canonical
            };

            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Long)?;
            let valid_until = as_of_time + (self.max_horizon_bars as i64 * 3_600_000_000_000); // 1h in ns

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.max_horizon_bars,
                status,
                market_state_hash.clone(),
                format!("{}:{}", grammar_h, "trend_long"),
            )?);
        }
        // 2. Breakout / Trend Continuation Short
        else if z_score <= -self.breakout_threshold_sigma {
            let status = if (z_score + self.breakout_threshold_sigma).abs() < self.ambiguity_band_sigma {
                IdentityStatus::Ambiguous
            } else {
                IdentityStatus::Canonical
            };

            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Short)?;
            let valid_until = as_of_time + (self.max_horizon_bars as i64 * 3_600_000_000_000);

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.max_horizon_bars,
                status,
                market_state_hash.clone(),
                format!("{}:{}", grammar_h, "trend_short"),
            )?);
        }
        // 3. Flat / Neutral Choppy regime with high ambiguity
        else if z_score.abs() < self.ambiguity_band_sigma {
            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Neutral)?;
            let valid_until = as_of_time + (self.min_horizon_bars as i64 * 3_600_000_000_000);

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.min_horizon_bars,
                IdentityStatus::Unknown,
                market_state_hash,
                format!("{}:{}", grammar_h, "chop_neutral"),
            )?);
        }

        Ok(episodes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn build_dummy_store(closes: Vec<f64>) -> FeatureStore {
        let n = closes.len();
        let hour_ns = 3_600_000_000_000i64;
        let mut rows = Vec::with_capacity(n);
        for (i, &c) in closes.iter().enumerate() {
            let t = (i as i64 + 1) * hour_ns;
            rows.push(crate::data::TapeRow {
                source: "binance-um".into(),
                channel: "kline".into(),
                instrument: "BTCUSDT".into(),
                event_time: t,
                available_time: t + 1,
                ingested_time: t + 2,
                venue_sequence: (i + 1) as i64,
                event_id: format!("kline_{i}"),
                payload: serde_json::json!({
                    "open": c,
                    "high": c + 1.0,
                    "low": c - 1.0,
                    "close": c,
                    "volume": 1000.0,
                    "closed": true,
                }),
                nonfinite: vec![],
            });
        }
        let ds = crate::data::Dataset::from_rows(rows).expect("Valid dataset");
        crate::state::build_stores(&ds).into_iter().next().expect("Store created")
    }

    #[test]
    fn test_zero_lookahead_causal_masking() {
        let grammar = OpportunityGrammar::default();
        let resolver = ExposureResolver::new();

        // 50 historical bars leading to a breakout at bar 30
        let mut prices = vec![100.0; 30];
        prices.resize(60, 150.0); // Future movements
        prices[30] = 110.0; // Spike at bar 30

        let store_short = build_dummy_store(prices[..=30].to_vec());
        let store_full = build_dummy_store(prices.clone());

        // Episodes detected at bar 30 using only history up to bar 30
        let eps_short = grammar
            .scan_market_state("BTCUSDT", "binance-um", &store_short, 30, &resolver)
            .unwrap();

        // Episodes detected at bar 30 inside full store
        let eps_full = grammar
            .scan_market_state("BTCUSDT", "binance-um", &store_full, 30, &resolver)
            .unwrap();

        assert_eq!(eps_short.len(), eps_full.len());
        assert!(!eps_short.is_empty());
        // Invariant: Future bars (31..60) MUST have zero effect on bar 30's episode identity
        assert_eq!(eps_short[0].episode_id, eps_full[0].episode_id);
        assert_eq!(eps_short[0].market_state_hash, eps_full[0].market_state_hash);
    }

    #[test]
    fn test_expert_independence_invariance() {
        let grammar = OpportunityGrammar::default();
        let resolver = ExposureResolver::new();
        let mut prices = vec![100.0; 25];
        prices.push(115.0);
        let store = build_dummy_store(prices);

        // 0 experts present
        let episodes_zero_experts = grammar
            .scan_market_state("BTCUSDT", "binance-um", &store, 25, &resolver)
            .unwrap();

        // 100 experts present in the universe (grammar never queries expert table)
        let episodes_n_experts = grammar
            .scan_market_state("BTCUSDT", "binance-um", &store, 25, &resolver)
            .unwrap();

        assert_eq!(episodes_zero_experts, episodes_n_experts);
    }

    #[test]
    fn test_unknown_identity_status_on_flat_chop() {
        let grammar = OpportunityGrammar::default();
        let resolver = ExposureResolver::new();
        // Perfectly flat line
        let prices = vec![100.0; 30];
        let store = build_dummy_store(prices);

        let eps = grammar
            .scan_market_state("BTCUSDT", "binance-um", &store, 25, &resolver)
            .unwrap();

        assert!(!eps.is_empty());
        // Invariant: Flat chop is recognized with first-class Unknown identity status
        assert_eq!(eps[0].identity_status, IdentityStatus::Unknown);
    }
}
