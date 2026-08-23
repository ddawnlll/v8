//! V8.3 Opportunity Sovereignty Module (Issue #231, Decisions D-128..D-130).
//!
//! Owning Authority: V8 Constitution v0.2 Rules 4, 6, 13, 18, 19, 20, 21, 22, 23, 24, 26, 27.
//!
//! The 7 Canonical Constitutional Primitives (Rule 4 / D-130):
//! 1. MarketState (reused from crate::state)
//! 2. EconomicExposureStructure (crate::opportunity::exposure)
//! 3. OpportunityEpisode (crate::opportunity::opportunity)
//! 4. ObserverEvidence (crate::opportunity::evidence)
//! 5. ReconciledOpportunityState (crate::opportunity::reconcile)
//! 6. ExecutionCampaign (crate::opportunity::campaign)
//! 7. Order / Fill / Position / Outcome (reused from crate::simulator / crate::account / crate::cashflow)
//!
//! Derived Decision & Diagnostic Artifacts:
//! - SelectiveUtilityDecision (crate::opportunity::utility)
//! - WitnessScorecard (crate::opportunity::evidence)

pub mod exposure;
pub mod book;
pub mod grammar;
pub mod evidence;
pub mod reconcile;
pub mod utility;
pub mod campaign;
pub mod runloop;
pub mod harness_t1_t12;
pub mod funnel;
pub mod frontier;

pub use exposure::{
    EconomicExposureStructure, ExposureDirection, ExposureLeg, ExposureResolver, HorizonClass,
    InstrumentType, PayoffStructure, SymbolDescriptor,
};
pub use book::{IdentityStatus, OpportunityBook, OpportunityEpisode};
pub use grammar::{
    CompressionExpansionDetector, GrammarArchetype, MeanReversionDetector, OpportunityDetector,
    OpportunityGrammar, TrendContinuationDetector, VolatilityExtremeDetector,
};
pub use evidence::{
    AbstentionReason, HabitatAssessment, ObserverEvidence, ObserverStance, WitnessScorecard,
};
pub use reconcile::{EvidenceReconciler, ReconciledOpportunityState, ReconciledStance};
pub use utility::{FrictionModel, SelectiveUtility, SelectiveUtilityDecision, UtilityAction};
pub use campaign::{
    CampaignIntent, CampaignLeg, CampaignStatus, ExecutionCampaign, PortfolioFeasibilityConfig,
    PortfolioFeasibilityEngine,
};
pub use runloop::{OpportunityCycleLedger, V83Runloop};
pub use funnel::{CanonicalFunnelReport, CanonicalOpportunityFunnelTracker, EconomicAuthority, OpportunityFunnelStage};

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::V8CoreError;

    #[test]
    fn test_r1_seven_canonical_primitives_composition() {
        // 1. MarketState (represented via state hash & lineage)
        let state_hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        let lineage_hash = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";

        // 2. EconomicExposureStructure
        let exposure = EconomicExposureStructure::single_perp(
            "BTCUSDT",
            "BTC",
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .expect("Valid perp exposure");
        assert!(!exposure.exposure_id.is_empty());
        assert_eq!(exposure.underlying_factors, vec!["BTC".to_string()]);

        // 3. OpportunityEpisode
        let episode = OpportunityEpisode::new(
            exposure.clone(),
            1_751_328_000_000_000_000,
            1_751_331_600_000_000_000,
            24,
            IdentityStatus::Canonical,
            state_hash,
            lineage_hash,
        )
        .expect("Valid episode");
        assert!(!episode.episode_id.is_empty());

        // 4. ObserverEvidence
        let evidence = ObserverEvidence::new(
            &episode.episode_id,
            "trend_pullback",
            "v1.0.0",
            "momentum",
            "trend_following",
            "trend_group_a",
            ObserverStance::Support {
                confidence: 0.85,
                expected_edge_r: 0.25,
            },
            HabitatAssessment::InHabitat,
            0.10,
            1_751_328_000_000_000_000,
            "lineage_v1",
        )
        .expect("Valid evidence");
        assert!(!evidence.evidence_id.is_empty());
        assert!(evidence.is_active_support());

        // 5. ReconciledOpportunityState
        let reconciled = EvidenceReconciler::reconcile(&episode, std::slice::from_ref(&evidence))
            .expect("Reconciliation succeeds");
        assert_eq!(reconciled.aggregate_stance, ReconciledStance::Supported);
        assert_eq!(reconciled.effective_observer_count, 1.0);

        // 6. SelectiveUtilityDecision & CampaignIntent
        let friction = FrictionModel::default();
        let decision = SelectiveUtility::evaluate(&episode, &reconciled, &friction, 25.0)
            .expect("Utility evaluation succeeds");
        assert!(decision.is_executable());

        let intent = CampaignIntent::new(
            &episode.episode_id,
            &decision.decision_id,
            exposure.clone(),
            0.5,
            1000.0,
            1_751_328_000_000_000_000,
        )
        .expect("Valid campaign intent");
        assert!(!intent.intent_id.is_empty());

        // 6. ExecutionCampaign
        let leg = CampaignLeg::new("BTCUSDT", "binance-um", 0.05, Some(100000.0));
        let campaign = ExecutionCampaign::new(
            &intent,
            500.0,
            0.5,
            vec![leg],
            vec!["price_below_stop".to_string()],
            1_751_328_000_000_000_000,
        )
        .expect("Valid execution campaign");
        assert_eq!(campaign.status, CampaignStatus::PendingAdmission);
    }

    #[test]
    fn test_r2_cryptographic_blake3_determinism() {
        let exp1 = EconomicExposureStructure::single_spot(
            "ETHUSDT",
            "ETH",
            "binance-spot",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        let exp2 = EconomicExposureStructure::single_spot(
            "ETHUSDT",
            "ETH",
            "binance-spot",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        // Deterministic hash equality
        assert_eq!(exp1.exposure_id, exp2.exposure_id);
        assert_eq!(exp1.exposure_id.len(), 64); // 256-bit BLAKE3 hex
    }

    #[test]
    fn test_r3_zero_capital_authority_on_raw_evidence() {
        let exp = EconomicExposureStructure::single_perp(
            "SOLUSDT",
            "SOL",
            "binance-um",
            "USDT",
            ExposureDirection::Short,
        )
        .unwrap();

        let episode = OpportunityEpisode::new(
            exp,
            1000,
            2000,
            10,
            IdentityStatus::Canonical,
            "shash",
            "lhash",
        )
        .unwrap();

        // 10 duplicate observer stances (clones)
        let mut evidence_clones = Vec::new();
        for i in 0..10 {
            evidence_clones.push(
                ObserverEvidence::new(
                    &episode.episode_id,
                    format!("clone_expert_{i}"),
                    "v1",
                    "fam",
                    "beh",
                    "collinear_clone_group", // Shared dependency group!
                    ObserverStance::Support {
                        confidence: 0.90,
                        expected_edge_r: 0.30,
                    },
                    HabitatAssessment::InHabitat,
                    0.05,
                    1000,
                    "lineage",
                )
                .unwrap(),
            );
        }

        // Reconcile clones: Effective observer count MUST be discounted to 1.0 (N_eff = 1.0)
        let reconciled = EvidenceReconciler::reconcile(&episode, &evidence_clones).unwrap();
        assert_eq!(reconciled.effective_observer_count, 1.0);
        assert!((reconciled.support_weight - 0.855).abs() < 1e-6);
    }

    #[test]
    fn test_r4_typed_v83_error_taxonomy() {
        let invalid_exp = EconomicExposureStructure::new(
            vec![], // Empty factors -> error
            InstrumentType::Spot,
            "binance",
            "USDT",
            ExposureDirection::Long,
            PayoffStructure::Linear,
            vec![],
            HorizonClass::Intraday,
        );

        match invalid_exp {
            Err(V8CoreError::InvalidExposureStructure(msg)) => {
                assert!(msg.contains("underlying_factors cannot be empty"));
            }
            other => panic!("Expected InvalidExposureStructure error, got: {:?}", other),
        }
    }

    #[test]
    fn test_false_collapse_basis_protection() {
        let basis = EconomicExposureStructure::spot_perp_basis(
            "BTC",
            "BTCUSDT",
            "binance-spot",
            "BTCUSDT",
            "binance-um",
            "USDT",
        )
        .unwrap();

        assert!(basis.is_basis_or_spread());
        assert_eq!(basis.legs.len(), 2);
        assert_eq!(basis.direction, ExposureDirection::Neutral);
        assert_eq!(basis.legs[0].instrument_type, InstrumentType::Spot);
        assert_eq!(basis.legs[1].instrument_type, InstrumentType::Perpetual);
    }

    #[test]
    fn test_selective_utility_sub_friction_suppression() {
        let exp = EconomicExposureStructure::single_perp("DOGEUSDT", "DOGE", "binance-um", "USDT", ExposureDirection::Long).unwrap();
        let ep = OpportunityEpisode::new(exp, 100, 200, 5, IdentityStatus::Canonical, "s", "l").unwrap();
        let ev = ObserverEvidence::new(
            &ep.episode_id,
            "noisy_expert",
            "v1",
            "noise",
            "scalp",
            "grp",
            ObserverStance::Support { confidence: 0.5, expected_edge_r: 0.05 },
            HabitatAssessment::InHabitat,
            0.1,
            100,
            "lin",
        ).unwrap();

        let rec = EvidenceReconciler::reconcile(&ep, std::slice::from_ref(&ev)).unwrap();
        let friction = FrictionModel::default(); // total hurdle = 15bps + 5bps = 20bps

        // Gross edge is only 5 bps (sub-friction)
        let dec = SelectiveUtility::evaluate(&ep, &rec, &friction, 5.0).unwrap();
        assert_eq!(dec.action, UtilityAction::NoTrade);
        assert!(!dec.is_executable());
    }
}
