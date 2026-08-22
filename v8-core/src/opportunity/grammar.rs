//! Point-In-Time Causal Modular Opportunity Grammar (Issue #231, #233, #252, PH2-002, D-130).
//!
//! Owning Authority: V8 Constitution Rules 6, 18, 20, 23.
//!
//! Epistemic Invariants:
//!   1. MarketState -> Exposure -> OpportunityGrammar -> Canonical OpportunityBook.
//!   2. Opportunity identity is established strictly INDEPENDENT of Expert observers.
//!   3. Zero lookahead: Episode boundaries at bar `i` depend strictly on information available at or before `i`.
//!   4. Modular Archetypes: Detectors express distinct market physics (Volatility Extreme, Trend Continuation, Mean Reversion, Compression Expansion).
//!   5. Overlap Deduplication: Deduplicates identical (exposure, direction, anchor_time) episodes across detectors while preserving archetype lineage.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use crate::error::V8CoreError;
use crate::hash::Canon;
use crate::state::FeatureStore;
use super::book::{IdentityStatus, OpportunityEpisode};
use super::exposure::{ExposureDirection, ExposureResolver};

/// Structural episode archetype recognized by the causal grammar.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum GrammarArchetype {
    VolatilityExtreme,
    TrendContinuation,
    MeanReversion,
    CompressionExpansion,
    BasisDislocation,
}

/// Core trait implemented by independent point-in-time opportunity detectors.
pub trait OpportunityDetector: Send + Sync {
    fn detector_id(&self) -> &str;
    fn archetype(&self) -> GrammarArchetype;
    fn detect(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError>;
}

// -------------------------------------------------------------------------------------------------
// G0: Baseline Volatility Extreme Detector
// -------------------------------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct VolatilityExtremeDetector {
    pub lookback_bars: usize,
    pub breakout_threshold_sigma: f64,
    pub ambiguity_band_sigma: f64,
    pub horizon_bars: usize,
}

impl Default for VolatilityExtremeDetector {
    fn default() -> Self {
        Self {
            lookback_bars: 20,
            breakout_threshold_sigma: 1.8,
            ambiguity_band_sigma: 0.3,
            horizon_bars: 48,
        }
    }
}

impl OpportunityDetector for VolatilityExtremeDetector {
    fn detector_id(&self) -> &str {
        "G0_VOLATILITY_EXTREME"
    }

    fn archetype(&self) -> GrammarArchetype {
        GrammarArchetype::VolatilityExtreme
    }

    fn detect(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError> {
        let n_bars = store.closes.len();
        if bar_idx >= n_bars || bar_idx < self.lookback_bars {
            return Ok(Vec::new());
        }

        let as_of_time = store.avail[bar_idx];
        let close_now = store.closes[bar_idx];
        let closes_prefix = &store.closes[..=bar_idx];
        let n_prefix = closes_prefix.len();

        let start_idx = n_prefix.saturating_sub(self.lookback_bars);
        let window = &closes_prefix[start_idx..n_prefix];
        if window.len() < self.lookback_bars {
            return Ok(Vec::new());
        }

        let mean_price: f64 = window.iter().sum::<f64>() / window.len() as f64;
        let variance: f64 = window.iter().map(|p| (p - mean_price).powi(2)).sum::<f64>() / window.len() as f64;
        let std_dev = variance.sqrt().max(1e-8);
        let z_score = (close_now - mean_price) / std_dev;

        let mut sc = Canon::new();
        sc.push_str(symbol);
        sc.push_str(venue);
        sc.push_i64(as_of_time);
        sc.push_f64(close_now);
        sc.push_f64(z_score);
        let market_state_hash = sc.finish_blake3_hex();

        let mut episodes = Vec::new();

        if z_score >= self.breakout_threshold_sigma {
            let status = if (z_score - self.breakout_threshold_sigma).abs() < self.ambiguity_band_sigma {
                IdentityStatus::Ambiguous
            } else {
                IdentityStatus::Canonical
            };

            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Long)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                status,
                market_state_hash.clone(),
                format!("{}:trend_long", self.detector_id()),
            )?);
        } else if z_score <= -self.breakout_threshold_sigma {
            let status = if (z_score + self.breakout_threshold_sigma).abs() < self.ambiguity_band_sigma {
                IdentityStatus::Ambiguous
            } else {
                IdentityStatus::Canonical
            };

            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Short)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                status,
                market_state_hash.clone(),
                format!("{}:trend_short", self.detector_id()),
            )?);
        } else if z_score.abs() < self.ambiguity_band_sigma {
            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Neutral)?;
            let valid_until = as_of_time + (4 * 3_600_000_000_000);

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                4,
                IdentityStatus::Unknown,
                market_state_hash,
                format!("{}:chop_neutral", self.detector_id()),
            )?);
        }

        Ok(episodes)
    }
}

// -------------------------------------------------------------------------------------------------
// G1: Trend Continuation Detector (Multi-Window Moving Average & Momentum Slope)
// -------------------------------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct TrendContinuationDetector {
    pub fast_window: usize,
    pub slow_window: usize,
    pub horizon_bars: usize,
}

impl Default for TrendContinuationDetector {
    fn default() -> Self {
        Self {
            fast_window: 8,
            slow_window: 24,
            horizon_bars: 24,
        }
    }
}

impl OpportunityDetector for TrendContinuationDetector {
    fn detector_id(&self) -> &str {
        "G1_TREND_CONTINUATION"
    }

    fn archetype(&self) -> GrammarArchetype {
        GrammarArchetype::TrendContinuation
    }

    fn detect(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError> {
        let n_bars = store.closes.len();
        if bar_idx >= n_bars || bar_idx < self.slow_window {
            return Ok(Vec::new());
        }

        let as_of_time = store.avail[bar_idx];
        let close_now = store.closes[bar_idx];
        let closes_prefix = &store.closes[..=bar_idx];

        let fast_start = closes_prefix.len().saturating_sub(self.fast_window);
        let slow_start = closes_prefix.len().saturating_sub(self.slow_window);

        let fast_sma: f64 = closes_prefix[fast_start..].iter().sum::<f64>() / self.fast_window as f64;
        let slow_sma: f64 = closes_prefix[slow_start..].iter().sum::<f64>() / self.slow_window as f64;
        let prev_close = store.closes[bar_idx - 1];

        let mut sc = Canon::new();
        sc.push_str(symbol);
        sc.push_str(venue);
        sc.push_i64(as_of_time);
        sc.push_f64(fast_sma);
        sc.push_f64(slow_sma);
        let market_state_hash = sc.finish_blake3_hex();

        let mut episodes = Vec::new();

        // Fast > Slow SMA and upward continuation bar
        if fast_sma > slow_sma && close_now > prev_close && close_now > fast_sma {
            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Long)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);
            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                IdentityStatus::Canonical,
                market_state_hash.clone(),
                format!("{}:continuation_long", self.detector_id()),
            )?);
        } else if fast_sma < slow_sma && close_now < prev_close && close_now < fast_sma {
            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Short)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);
            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                IdentityStatus::Canonical,
                market_state_hash,
                format!("{}:continuation_short", self.detector_id()),
            )?);
        }

        Ok(episodes)
    }
}

// -------------------------------------------------------------------------------------------------
// G2: Mean Reversion Detector (Envelope & Range Deceleration)
// -------------------------------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct MeanReversionDetector {
    pub lookback_bars: usize,
    pub envelope_atr_mult: f64,
    pub horizon_bars: usize,
}

impl Default for MeanReversionDetector {
    fn default() -> Self {
        Self {
            lookback_bars: 20,
            envelope_atr_mult: 2.2,
            horizon_bars: 12,
        }
    }
}

impl OpportunityDetector for MeanReversionDetector {
    fn detector_id(&self) -> &str {
        "G2_MEAN_REVERSION"
    }

    fn archetype(&self) -> GrammarArchetype {
        GrammarArchetype::MeanReversion
    }

    fn detect(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError> {
        let n_bars = store.closes.len();
        if bar_idx >= n_bars || bar_idx < self.lookback_bars {
            return Ok(Vec::new());
        }

        let as_of_time = store.avail[bar_idx];
        let close_now = store.closes[bar_idx];
        let current_atr = store.atr.get(bar_idx).copied().unwrap_or(close_now * 0.01);
        let closes_prefix = &store.closes[..=bar_idx];

        let start_idx = closes_prefix.len().saturating_sub(self.lookback_bars);
        let sma: f64 = closes_prefix[start_idx..].iter().sum::<f64>() / self.lookback_bars as f64;
        let upper_band = sma + (self.envelope_atr_mult * current_atr);
        let lower_band = sma - (self.envelope_atr_mult * current_atr);

        let prev_close = store.closes[bar_idx - 1];

        let mut sc = Canon::new();
        sc.push_str(symbol);
        sc.push_str(venue);
        sc.push_i64(as_of_time);
        sc.push_f64(sma);
        sc.push_f64(current_atr);
        let market_state_hash = sc.finish_blake3_hex();

        let mut episodes = Vec::new();

        // Extended above upper band with downward deceleration bar -> Short mean reversion
        if close_now >= upper_band && close_now < prev_close {
            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Short)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);
            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                IdentityStatus::Canonical,
                market_state_hash.clone(),
                format!("{}:mean_rev_short", self.detector_id()),
            )?);
        } else if close_now <= lower_band && close_now > prev_close {
            let exposure = resolver.resolve_ticker(symbol, venue, ExposureDirection::Long)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);
            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                IdentityStatus::Canonical,
                market_state_hash,
                format!("{}:mean_rev_long", self.detector_id()),
            )?);
        }

        Ok(episodes)
    }
}

// -------------------------------------------------------------------------------------------------
// G3: Compression -> Expansion Detector (Volatility Squeeze Breakout)
// -------------------------------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct CompressionExpansionDetector {
    pub compression_lookback: usize,
    pub horizon_bars: usize,
}

impl Default for CompressionExpansionDetector {
    fn default() -> Self {
        Self {
            compression_lookback: 48,
            horizon_bars: 24,
        }
    }
}

impl OpportunityDetector for CompressionExpansionDetector {
    fn detector_id(&self) -> &str {
        "G3_COMPRESSION_EXPANSION"
    }

    fn archetype(&self) -> GrammarArchetype {
        GrammarArchetype::CompressionExpansion
    }

    fn detect(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError> {
        let n_bars = store.closes.len();
        if bar_idx >= n_bars || bar_idx < self.compression_lookback {
            return Ok(Vec::new());
        }

        let as_of_time = store.avail[bar_idx];
        let current_close = store.closes[bar_idx];
        let current_atr = store.atr.get(bar_idx).copied().unwrap_or(current_close * 0.01);

        let atr_start = bar_idx.saturating_sub(self.compression_lookback);
        let mut min_atr = current_atr;
        let mut max_atr = current_atr;
        for i in atr_start..bar_idx {
            if let Some(&a) = store.atr.get(i) {
                min_atr = min_atr.min(a);
                max_atr = max_atr.max(a);
            }
        }

        let is_compressed = (current_atr - min_atr) / (max_atr - min_atr).max(1e-8) < 0.25;
        let prev_close = store.closes[bar_idx - 1];
        let price_change_pct = (current_close - prev_close) / prev_close;

        let mut episodes = Vec::new();

        if is_compressed && price_change_pct.abs() > 0.008 {
            let direction = if price_change_pct > 0.0 {
                ExposureDirection::Long
            } else {
                ExposureDirection::Short
            };

            let mut sc = Canon::new();
            sc.push_str(symbol);
            sc.push_str(venue);
            sc.push_i64(as_of_time);
            sc.push_f64(current_atr);
            sc.push_f64(price_change_pct);
            let market_state_hash = sc.finish_blake3_hex();

            let exposure = resolver.resolve_ticker(symbol, venue, direction)?;
            let valid_until = as_of_time + (self.horizon_bars as i64 * 3_600_000_000_000);

            episodes.push(OpportunityEpisode::new(
                exposure,
                as_of_time,
                valid_until,
                self.horizon_bars,
                IdentityStatus::Canonical,
                market_state_hash,
                format!("{}:squeeze_expansion", self.detector_id()),
            )?);
        }

        Ok(episodes)
    }
}

// -------------------------------------------------------------------------------------------------
// Modular Opportunity Grammar Orchestrator
// -------------------------------------------------------------------------------------------------

pub struct OpportunityGrammar {
    pub grammar_version: String,
    pub detectors: Vec<Box<dyn OpportunityDetector>>,
}

impl Default for OpportunityGrammar {
    fn default() -> Self {
        Self::full_modular("v8.3-modular-grammar-v2")
    }
}

impl OpportunityGrammar {
    /// Baseline G0 (Single-detector Volatility Extreme)
    pub fn baseline_g0(version: impl Into<String>) -> Self {
        Self {
            grammar_version: version.into(),
            detectors: vec![Box::new(VolatilityExtremeDetector::default())],
        }
    }

    /// Full Modular Ensemble (G0 + G1 + G2 + G3)
    pub fn full_modular(version: impl Into<String>) -> Self {
        Self {
            grammar_version: version.into(),
            detectors: vec![
                Box::new(VolatilityExtremeDetector::default()),
                Box::new(TrendContinuationDetector::default()),
                Box::new(MeanReversionDetector::default()),
                Box::new(CompressionExpansionDetector::default()),
            ],
        }
    }

    pub fn with_detectors(version: impl Into<String>, detectors: Vec<Box<dyn OpportunityDetector>>) -> Self {
        Self {
            grammar_version: version.into(),
            detectors,
        }
    }

    /// Scans market state across all modular detectors and deduplicates overlapping episodes.
    pub fn scan_market_state(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        resolver: &ExposureResolver,
    ) -> Result<Vec<OpportunityEpisode>, V8CoreError> {
        let mut episodes = Vec::new();
        let mut seen_keys = HashSet::new();

        for detector in &self.detectors {
            let det_episodes = detector.detect(symbol, venue, store, bar_idx, resolver)?;
            for ep in det_episodes {
                // Deduplicate by (underlying, direction, as_of_time)
                let key = format!("{}:{}:{}", ep.exposure.underlying_factors.join("+"), ep.exposure.direction as u8, ep.as_of_time);
                if seen_keys.insert(key) {
                    episodes.push(ep);
                }
            }
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
                    "open": c - 0.5,
                    "high": c + 1.0,
                    "low": c - 1.0,
                    "close": c,
                    "volume": 1000.0,
                    "closed": true,
                }),
                nonfinite: vec![],
            });
        }
        let ds = crate::data::Dataset::from_rows(rows).unwrap();
        crate::state::build_stores(&ds).into_iter().next().unwrap()
    }

    #[test]
    fn test_modular_grammar_archetype_detections() {
        let mut closes = vec![100.0; 40];
        // Create an upward trend series
        for i in 25..40 {
            closes[i] = 100.0 + (i - 24) as f64 * 2.0;
        }

        let store = build_dummy_store(closes);
        let resolver = ExposureResolver::new();
        let grammar = OpportunityGrammar::default();

        let episodes = grammar.scan_market_state("BTCUSDT", "binance-um", &store, 35, &resolver).unwrap();
        assert!(!episodes.is_empty());
        assert_eq!(episodes[0].exposure.direction, ExposureDirection::Long);
    }
}
