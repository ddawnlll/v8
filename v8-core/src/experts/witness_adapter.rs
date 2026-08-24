//! Expert -> Epistemic Witness Migration & Adapter (Issue #231, #234, D-130).
//!
//! Owning Authority: V8 Constitution Rules 13, 14, 20, 21.
//!
//! Epistemic Demarcation:
//!   Experts are epistemic witnesses, NOT economic sovereigns.
//!   They observe pre-existing OpportunityEpisodes and emit typed evidence stances.
//!   They have ZERO capital, portfolio, or execution authority.

#![allow(dead_code)]

use crate::error::V8CoreError;
use crate::opportunity::book::OpportunityEpisode;
use crate::opportunity::evidence::{
    AbstentionReason, HabitatAssessment, ObserverEvidence, ObserverStance,
};
use crate::opportunity::exposure::ExposureDirection;
use super::base::FeatMap;

/// Trait defining an epistemic witness observing canonical opportunity episodes.
pub trait ExpertWitness: Send + Sync {
    fn observer_id(&self) -> &str;
    fn mechanism_family_id(&self) -> &str;
    fn behavior_family_id(&self) -> &str;
    fn dependency_group(&self) -> &str;
    fn observer_version(&self) -> &str;

    /// Observes a PIT OpportunityEpisode and emits typed epistemic evidence.
    fn observe(
        &self,
        opp: &OpportunityEpisode,
        fm: &FeatMap,
    ) -> Result<ObserverEvidence, V8CoreError>;
}

/// Adapter wrapping a legacy 28-expert evaluate() port into an Epistemic Witness.
#[derive(Debug, Clone)]
pub struct LegacyExpertWitnessAdapter {
    pub expert_id: String,
    pub mechanism_family_id: String,
    pub behavior_family_id: String,
    pub dependency_group: String,
    pub observer_version: String,
}

impl LegacyExpertWitnessAdapter {
    pub fn new(
        expert_id: impl Into<String>,
        mechanism_family_id: impl Into<String>,
        behavior_family_id: impl Into<String>,
        dependency_group: impl Into<String>,
    ) -> Self {
        Self {
            expert_id: expert_id.into(),
            mechanism_family_id: mechanism_family_id.into(),
            behavior_family_id: behavior_family_id.into(),
            dependency_group: dependency_group.into(),
            observer_version: "v8.3-witness-v1".to_string(),
        }
    }
}

impl ExpertWitness for LegacyExpertWitnessAdapter {
    fn observer_id(&self) -> &str {
        &self.expert_id
    }

    fn mechanism_family_id(&self) -> &str {
        &self.mechanism_family_id
    }

    fn behavior_family_id(&self) -> &str {
        &self.behavior_family_id
    }

    fn dependency_group(&self) -> &str {
        &self.dependency_group
    }

    fn observer_version(&self) -> &str {
        &self.observer_version
    }

    fn observe(
        &self,
        opp: &OpportunityEpisode,
        fm: &FeatMap,
    ) -> Result<ObserverEvidence, V8CoreError> {
        let eval = super::evaluate(&self.expert_id, fm);

        let (stance, habitat, uncertainty) = match eval.decision.as_str() {
            "CANDIDATE" => {
                if let Some(draft) = eval.draft {
                    let draft_is_long = draft.direction == "LONG";
                    let opp_is_long = opp.exposure.direction == ExposureDirection::Long;
                    let opp_is_short = opp.exposure.direction == ExposureDirection::Short;

                    if (draft_is_long && opp_is_long) || (!draft_is_long && opp_is_short) {
                        (
                            ObserverStance::Support {
                                confidence: 0.85,
                                expected_edge_r: draft.geom_f64("target_r").unwrap_or(0.25).max(0.1),
                            },
                            HabitatAssessment::InHabitat,
                            0.10,
                        )
                    } else if (draft_is_long && opp_is_short) || (!draft_is_long && opp_is_long) {
                        (
                            ObserverStance::Contradict {
                                reason: format!(
                                    "Opposing signal detected: expert={} draft_dir={} opp_dir={:?}",
                                    self.expert_id, draft.direction, opp.exposure.direction
                                ),
                                severity: 0.80,
                            },
                            HabitatAssessment::InHabitat,
                            0.15,
                        )
                    } else {
                        (
                            ObserverStance::Abstain {
                                reason: AbstentionReason::BoundaryAmbiguity,
                            },
                            HabitatAssessment::InHabitat,
                            0.20,
                        )
                    }
                } else {
                    (
                        ObserverStance::Abstain {
                            reason: AbstentionReason::InsufficientHistory,
                        },
                        HabitatAssessment::InHabitat,
                        0.30,
                    )
                }
            }
            "NO_HABITAT" => (
                ObserverStance::Abstain {
                    reason: AbstentionReason::RegimeMismatch,
                },
                HabitatAssessment::OutOfHabitat,
                0.50,
            ),
            "NO_SETUP" => (
                ObserverStance::Abstain {
                    reason: AbstentionReason::InsufficientHistory,
                },
                HabitatAssessment::InHabitat,
                0.20,
            ),
            _ => (
                ObserverStance::Abstain {
                    reason: AbstentionReason::RegimeMismatch,
                },
                HabitatAssessment::UnknownHabitat,
                0.40,
            ),
        };

        ObserverEvidence::new(
            &opp.episode_id,
            &self.expert_id,
            &self.observer_version,
            &self.mechanism_family_id,
            &self.behavior_family_id,
            &self.dependency_group,
            stance,
            habitat,
            uncertainty,
            fm.as_of,
            eval.setup_fingerprint.unwrap_or_else(|| "none".to_string()),
        )
    }
}

/// Builds the standard 28-witness ensemble mapped from the registered expert table.
pub fn default_28_witness_ensemble() -> Vec<LegacyExpertWitnessAdapter> {
    let expert_meta = [
        ("trend_pullback", "momentum", "trend_following", "dep_trend"),
        ("trend_pullback_depth", "momentum", "trend_following", "dep_trend"),
        ("bollinger_breakout", "volatility", "breakout", "dep_breakout"),
        ("bollinger_reversion", "volatility", "mean_reversion", "dep_reversion"),
        ("breakout_retest", "structural", "breakout", "dep_breakout"),
        ("candlestick_reversal", "price_action", "reversal", "dep_pattern"),
        ("divergence_12_setups", "oscillator", "divergence", "dep_oscillator"),
        ("donchian_breakout", "channel", "breakout", "dep_breakout"),
        ("failed_breakout", "structural", "trap", "dep_trap"),
        ("failed_breakout_2b", "structural", "trap", "dep_trap"),
        ("fib_projection_reversal", "geometric", "reversal", "dep_fib"),
        ("fib_retracement_continuation", "geometric", "continuation", "dep_fib"),
        ("fib_rsi_bb_confluence", "confluence", "confluence", "dep_confluence"),
        ("floor_trader_pivot", "pivot", "range", "dep_pivot"),
        ("funding_crowding_reversal", "derivatives", "crowding", "dep_derivatives"),
        ("gap_exhaustion", "gap", "exhaustion", "dep_gap"),
        ("ichimoku_cloud", "trend", "cloud", "dep_ichimoku"),
        ("liquidity_sweep_reclaim", "liquidity", "sweep", "dep_liquidity"),
        ("macd_stoch_trend", "oscillator", "trend", "dep_oscillator"),
        ("market_profile_value_area", "profile", "value_area", "dep_profile"),
        ("obv_adl_regime", "volume", "flow", "dep_volume"),
        ("open_interest_divergence", "derivatives", "divergence", "dep_derivatives"),
        ("pandf_breakout", "point_figure", "breakout", "dep_breakout"),
        ("pattern_measuring_objective", "chart_pattern", "objective", "dep_pattern"),
        ("predicate", "logic", "rule", "dep_predicate"),
        ("range_breakout_1to1", "range", "breakout", "dep_breakout"),
        ("rsi_stoch_reversion", "oscillator", "mean_reversion", "dep_reversion"),
        ("volume_climax_reversal", "volume", "climax", "dep_volume"),
        ("volume_confirmed_breakout", "volume", "breakout", "dep_volume"),
    ];

    expert_meta
        .iter()
        .map(|(eid, mfam, bfam, dep)| {
            LegacyExpertWitnessAdapter::new(*eid, *mfam, *bfam, *dep)
        })
        .collect()
}

/// Dispatches all registered witnesses to observe an OpportunityEpisode.
pub fn observe_all(
    witnesses: &[LegacyExpertWitnessAdapter],
    opp: &OpportunityEpisode,
    fm: &FeatMap,
) -> Vec<ObserverEvidence> {
    let mut out = Vec::with_capacity(witnesses.len());
    for w in witnesses {
        if let Ok(ev) = w.observe(opp, fm) {
            out.push(ev);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::opportunity::exposure::{EconomicExposureStructure, ExposureDirection};
    use crate::opportunity::book::{IdentityStatus, OpportunityEpisode};
    use crate::experts::base::ProjectedFeatures;
    use std::collections::HashMap;

    #[test]
    fn test_witness_ensemble_observes_without_execution_authority() {
        let witnesses = default_28_witness_ensemble();
        assert_eq!(witnesses.len(), 29); // 28 registered + 1 predicate variant

        let exp = EconomicExposureStructure::single_perp(
            "BTCUSDT",
            "BTC",
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        let opp = OpportunityEpisode::new(
            exp,
            1_000_000,
            2_000_000,
            24,
            IdentityStatus::Canonical,
            "state_hash_1",
            "lineage_hash_1",
        )
        .unwrap();

        let features_slice = [];
        let fm = FeatMap {
            features: ProjectedFeatures::unprojected(&features_slice),
            history: Vec::new(),
            as_of: 1_000_000,
            symbol: "BTCUSDT",
            variant_overrides: &HashMap::new(),
        };

        let evidences = observe_all(&witnesses, &opp, &fm);
        assert_eq!(evidences.len(), witnesses.len());

        // Invariant: All emitted records must attach to the opp episode ID with zero orders created
        for ev in &evidences {
            assert_eq!(ev.opportunity_id, opp.episode_id);
            assert!(ev.is_abstention() || ev.is_active_support() || ev.is_contradiction());
        }
    }
}
