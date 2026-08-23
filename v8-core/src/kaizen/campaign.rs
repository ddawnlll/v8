//! Multi-Sensor Persistent Campaign Clustering & Multi-Family Evidence Graph (Issue #215 / CAMP-001 / D-126).
//!
//! Normative Traceability: D-108, D-123, D-126, CANDIDATE_LIFECYCLE_SPEC §1.1.
//!
//! Key Architectural Invariants:
//! 1. Multi-Bar Persistent Identity: A campaign spans across bars until structural invalidation or resolution.
//! 2. Multi-Family Evidence Graph: Experts are mapped to 7 distinct mechanism families:
//!    - PriceStructure, Trend, Volatility, Volume, Derivatives, SpotFlow, ReversalExhaustion.
//!      Multiple triggers from the SAME family count as 1 family confirmation (Anti-Correlation Inflation).
//! 3. New triggers matching an existing active campaign become `CAMPAIGN_EVIDENCE_UPDATE`, not new trades.
//! 4. Zero Hardcoded Fixed Take-Profit (suggested_target_r = 2.0 removed).
//! 5. Structural Invalidation is determined by market structure, not arbitrary widest stop.

use std::collections::BTreeMap;
use serde::{Deserialize, Serialize};

/// The 7 Independent Mechanism Families.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub enum MechanismFamily {
    PriceStructure,
    Trend,
    Volatility,
    Volume,
    Derivatives,
    SpotFlow,
    ReversalExhaustion,
}

impl MechanismFamily {
    pub fn classify_expert(expert_id: &str) -> Self {
        match expert_id {
            "breakout_retest" | "floor_trader_pivot" | "range_breakout_1to1"
            | "pandf_breakout" | "pattern_measuring_objective" => Self::PriceStructure,

            "macd_stoch_trend" | "trend_pullback" | "trend_pullback_depth"
            | "ichimoku_cloud" | "donchian_breakout" | "trend_continuation" => Self::Trend,

            "bollinger_breakout" | "bollinger_reversion" | "fib_rsi_bb_confluence" | "squeeze_swing" => {
                Self::Volatility
            }

            "volume_climax_reversal" | "volume_confirmed_breakout" | "obv_adl_regime" => {
                Self::Volume
            }

            "funding_crowding_reversal" | "open_interest_divergence" => Self::Derivatives,

            "market_profile_value_area" | "liquidity_sweep_reclaim" => Self::SpotFlow,

            _ => Self::ReversalExhaustion,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CampaignDirection {
    Long,
    Short,
    ConflictNeutral,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorVote {
    pub sensor_id: String,
    pub symbol: String,
    pub direction: String, // "LONG" or "SHORT"
    pub entry_price: f64,
    pub stop_price: f64,
    pub timestamp_ns: i64,
    pub bar_index: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CampaignCluster {
    pub campaign_id: String,
    pub symbol: String,
    pub direction: CampaignDirection,
    pub start_bar_index: usize,
    pub last_update_bar_index: usize,
    pub timestamp_ns: i64,
    pub participating_sensors: Vec<String>,
    pub confirmed_families: Vec<MechanismFamily>,
    pub family_count: usize,
    pub total_sensor_count: usize,
    pub evidence_diversity_score: f64, // Normalized score based on distinct families [1.0 .. 7.0]
    pub consensus_entry: f64,
    pub structural_invalidation_price: f64,
    pub is_active: bool,
    pub trail_policy_id: String,
    pub redundancy_reduction_ratio: f64,
}

#[derive(Debug, Default)]
pub struct PersistentCampaignRegistry {
    pub active_campaigns: BTreeMap<String, CampaignCluster>,
}

impl PersistentCampaignRegistry {
    pub fn new() -> Self {
        Self {
            active_campaigns: BTreeMap::new(),
        }
    }

    /// Ingests a new sensor vote and matches it against persistent active campaigns.
    /// Returns (CampaignCluster, is_new_campaign).
    pub fn ingest_vote(&mut self, vote: SensorVote, _current_price: f64) -> (CampaignCluster, bool) {
        let dir = if vote.direction == "LONG" {
            CampaignDirection::Long
        } else {
            CampaignDirection::Short
        };

        let family = MechanismFamily::classify_expert(&vote.sensor_id);
        let sym = if vote.symbol.is_empty() { "BTCUSDT".to_string() } else { vote.symbol.clone() };

        // Check if there is an existing active campaign for this symbol & direction within 24 bars
        let mut matched_id = None;
        for (cid, camp) in &self.active_campaigns {
            if camp.is_active
                && camp.symbol == sym
                && camp.direction == dir
                && (vote.bar_index.saturating_sub(camp.last_update_bar_index) <= 24)
            {
                // Invalidation basin overlap check
                let stop_dist = (camp.structural_invalidation_price - vote.stop_price).abs();
                let max_stop_dist = (camp.consensus_entry * 0.03).max(1e-4);
                if stop_dist <= max_stop_dist {
                    matched_id = Some(cid.clone());
                    break;
                }
            }
        }

        if let Some(cid) = matched_id {
            // Update existing campaign (CAMPAIGN_EVIDENCE_UPDATE)
            let camp = self.active_campaigns.get_mut(&cid).unwrap();
            camp.last_update_bar_index = vote.bar_index;
            if !camp.participating_sensors.contains(&vote.sensor_id) {
                camp.participating_sensors.push(vote.sensor_id);
            }
            if !camp.confirmed_families.contains(&family) {
                camp.confirmed_families.push(family);
            }
            camp.family_count = camp.confirmed_families.len();
            camp.total_sensor_count = camp.participating_sensors.len();
            camp.evidence_diversity_score = camp.family_count as f64;
            camp.redundancy_reduction_ratio = 1.0 - (1.0 / camp.total_sensor_count as f64);
            (camp.clone(), false)
        } else {
            // Create a brand new persistent campaign
            let cid = format!(
                "CAMP_{}_{}_{}_{}",
                sym,
                vote.bar_index,
                if dir == CampaignDirection::Long { "L" } else { "S" },
                vote.sensor_id
            );

            let camp = CampaignCluster {
                campaign_id: cid.clone(),
                symbol: sym,
                direction: dir,
                start_bar_index: vote.bar_index,
                last_update_bar_index: vote.bar_index,
                timestamp_ns: vote.timestamp_ns,
                participating_sensors: vec![vote.sensor_id.clone()],
                confirmed_families: vec![family],
                family_count: 1,
                total_sensor_count: 1,
                evidence_diversity_score: 1.0,
                consensus_entry: vote.entry_price,
                structural_invalidation_price: vote.stop_price,
                is_active: true,
                trail_policy_id: "CHANDELIER_ATR_TRAIL".to_string(),
                redundancy_reduction_ratio: 0.0,
            };

            self.active_campaigns.insert(cid, camp.clone());
            (camp, true)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mechanism_family_classification() {
        assert_eq!(MechanismFamily::classify_expert("bollinger_breakout"), MechanismFamily::Volatility);
        assert_eq!(MechanismFamily::classify_expert("donchian_breakout"), MechanismFamily::Trend);
        assert_eq!(MechanismFamily::classify_expert("macd_stoch_trend"), MechanismFamily::Trend);
        assert_eq!(MechanismFamily::classify_expert("volume_climax_reversal"), MechanismFamily::Volume);
    }

    #[test]
    fn test_persistent_campaign_multi_bar_update() {
        let mut reg = PersistentCampaignRegistry::new();
        
        let vote1 = SensorVote {
            sensor_id: "bollinger_breakout".to_string(),
            symbol: "BTCUSDT".to_string(),
            direction: "LONG".to_string(),
            entry_price: 65000.0,
            stop_price: 64000.0,
            timestamp_ns: 1000,
            bar_index: 10,
        };

        let (camp1, is_new1) = reg.ingest_vote(vote1, 65000.0);
        assert!(is_new1);
        assert_eq!(camp1.family_count, 1);

        // Second vote on next bar from Trend family
        let vote2 = SensorVote {
            sensor_id: "macd_stoch_trend".to_string(),
            symbol: "BTCUSDT".to_string(),
            direction: "LONG".to_string(),
            entry_price: 65200.0,
            stop_price: 64100.0,
            timestamp_ns: 2000,
            bar_index: 11,
        };

        let (camp2, _is_new2) = reg.ingest_vote(vote2, 65200.0);
        assert_eq!(camp2.family_count, 2); // 2 distinct families: Volatility + Trend
    }
}
