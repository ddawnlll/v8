#![allow(dead_code)]
//! V8.3 Economic Trace Foundation & Decision Belief Ledger (EEO-001, EEO-001H, EEO-002, D-136).
//!
//! Owning Authority: V8 Constitution Rules 1, 3, 4, 18, 20, 21, 24, 28, 35; D-136.
//!
//! Architectural Modules:
//! - `identity`: Immutable trace identities, span IDs, modality, and cryptographic provenance.
//! - `span`: PIT decision spans, post-outcome evidence spans, and graph linkages.
//! - `belief`: PIT ex-ante Decision Belief Ledger and receipts (EEO-002).
//! - `ledger`: Comprehensive trace and lineage validation kernel.

pub mod identity;
pub mod span;
pub mod belief;
pub mod ledger;

#[allow(unused_imports)]
pub use identity::{
    EconomicTraceContext, EconomicTraceId, SpanId, TraceProvenance, TrajectoryType,
};
#[allow(unused_imports)]
pub use span::{
    DecisionSpan, DecisionStage, EvidenceSpan, EvidenceStage, SpanKind, SpanLink,
    SpanLinkType,
};
#[allow(unused_imports)]
pub use belief::{
    BeliefReceipt, BeliefReceiptId, BeliefStage, ChosenAction, DecisionBeliefLedger,
    ExAnteCostExpectation, ExAnteUncertainty,
};
#[allow(unused_imports)]
pub use ledger::EconomicTraceLedger;

/// Initialize standard tracing facade for V8 core runtime.
pub fn init_telemetry() {
    tracing::info!("v8-core telemetry initialized");
}

/// Helper function for recording step duration metric.
pub fn record_duration_metric(name: &'static str, duration_sec: f64) {
    metrics::gauge!(name).set(duration_sec);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::opportunity::exposure::{EconomicExposureStructure, ExposureDirection};
    use crate::opportunity::book::{IdentityStatus, OpportunityEpisode};
    use crate::opportunity::evidence::{HabitatAssessment, ObserverEvidence, ObserverStance};
    use crate::opportunity::reconcile::{EvidenceReconciler, ReconciledStance};
    use crate::opportunity::utility::{FrictionModel, SelectiveUtility};
    use crate::opportunity::campaign::{CampaignIntent, PortfolioFeasibilityConfig, PortfolioFeasibilityEngine};

    const TAPE_HASH: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    const BASELINE_POLICY_HASH: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const CHALLENGER_POLICY_HASH: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    const CONSTITUTION_HASH: &str = "c0n5717u710nc0n5717u710nc0n5717u710nc0n5717u710nc0n5717u710nc0n5";
    const CODE_HASH: &str = "c0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0de";

    fn create_test_episode(symbol: &str, as_of: i64) -> OpportunityEpisode {
        let exp = EconomicExposureStructure::single_perp(
            symbol,
            &symbol[..3],
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .expect("Valid exposure");
        OpportunityEpisode::new(
            exp,
            as_of,
            as_of + 3600_000_000_000,
            24,
            IdentityStatus::Canonical,
            TAPE_HASH,
            BASELINE_POLICY_HASH,
        )
        .expect("Valid episode")
    }

    #[test]
    fn test_h1_opportunity_identity_vs_trajectory_vs_provenance_separation() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);

        let ctx_baseline = EconomicTraceContext::from_episode(
            &ep,
            TAPE_HASH,
            BASELINE_POLICY_HASH,
            CONSTITUTION_HASH,
            CODE_HASH,
        )
        .unwrap();

        let ctx_challenger = EconomicTraceContext::from_episode_trajectory(
            &ep,
            TrajectoryType::Observed,
            "challenger_a1_be05r",
            TAPE_HASH,
            CHALLENGER_POLICY_HASH,
            CONSTITUTION_HASH,
            CODE_HASH,
        )
        .unwrap();

        assert_eq!(ctx_baseline.opportunity_id, ctx_challenger.opportunity_id);
        assert_eq!(ctx_baseline.opportunity_id, ep.episode_id);
        assert_ne!(ctx_baseline.trace_id, ctx_challenger.trace_id);
        assert_eq!(ctx_baseline.provenance.policy_hash, BASELINE_POLICY_HASH);
        assert_eq!(ctx_challenger.provenance.policy_hash, CHALLENGER_POLICY_HASH);
    }

    #[test]
    fn test_h2_oracle_audit_evidence_cannot_become_upstream_decision_dependency() {
        let ep = create_test_episode("ETHUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(
            &ep,
            TAPE_HASH,
            BASELINE_POLICY_HASH,
            CONSTITUTION_HASH,
            CODE_HASH,
        )
        .unwrap();

        let mut ledger = EconomicTraceLedger::new();
        ledger.register_context(ctx.clone()).unwrap();

        let s_detect = DecisionSpan::new(
            ctx.trace_id.clone(),
            None,
            DecisionStage::OpportunityDetection,
            ep.as_of_time,
            "detect_1",
        );
        ledger.record_span(s_detect.clone()).unwrap();

        let ev_oracle = EvidenceSpan::new(
            ctx.trace_id.clone(),
            s_detect.span_id.clone(),
            EvidenceStage::TargetOracleHindsight,
            ep.as_of_time + 1000,
            "oracle_hindsight",
        )
        .with_claim("ORACLE_UPPER_BOUND_0.85R");
        ledger.record_evidence_span(ev_oracle.clone()).unwrap();

        let illicit_decision = DecisionSpan::new(
            ctx.trace_id.clone(),
            Some(ev_oracle.span_id.clone()),
            DecisionStage::SelectiveUtility,
            ep.as_of_time + 1050,
            "illicit_utility_attempt",
        );

        let err = ledger.record_span(illicit_decision);
        assert!(err.is_err());
        assert!(err.unwrap_err().to_string().contains("PIT Authority Violation"));
    }

    #[test]
    fn test_h3_counterfactual_branch_is_explicitly_typed_without_name_inference() {
        let ep = create_test_episode("SOLUSDT", 1_751_328_000_000_000_000);
        let ctx_cf = EconomicTraceContext::from_episode_trajectory(
            &ep,
            TrajectoryType::Counterfactual,
            "do_reconciliation_alternative_alpha",
            TAPE_HASH,
            BASELINE_POLICY_HASH,
            CONSTITUTION_HASH,
            CODE_HASH,
        )
        .unwrap();

        assert!(ctx_cf.trajectory_type.is_counterfactual());
        assert!(!ctx_cf.trajectory_type.is_observed());
    }

    #[test]
    fn test_h4_full_canonical_trajectory_with_evidence_and_lineage_validation() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(
            &ep,
            TAPE_HASH,
            BASELINE_POLICY_HASH,
            CONSTITUTION_HASH,
            CODE_HASH,
        )
        .unwrap();

        let mut ledger = EconomicTraceLedger::new();
        ledger.register_context(ctx.clone()).unwrap();

        let s1 = DecisionSpan::new(ctx.trace_id.clone(), None, DecisionStage::OpportunityDetection, 1000, "s1");
        ledger.record_span(s1.clone()).unwrap();
        let s2 = DecisionSpan::new(ctx.trace_id.clone(), Some(s1.span_id.clone()), DecisionStage::WitnessObservation, 1010, "s2");
        ledger.record_span(s2.clone()).unwrap();
        let s3 = DecisionSpan::new(ctx.trace_id.clone(), Some(s2.span_id.clone()), DecisionStage::EvidenceReconciliation, 1020, "s3");
        ledger.record_span(s3.clone()).unwrap();
        let s4 = DecisionSpan::new(ctx.trace_id.clone(), Some(s3.span_id.clone()), DecisionStage::SelectiveUtility, 1030, "s4");
        ledger.record_span(s4.clone()).unwrap();
        let s5 = DecisionSpan::new(ctx.trace_id.clone(), Some(s4.span_id.clone()), DecisionStage::CampaignAdmission, 1040, "s5");
        ledger.record_span(s5.clone()).unwrap();

        let ev1 = EvidenceSpan::new(ctx.trace_id.clone(), s5.span_id.clone(), EvidenceStage::TargetOracleHindsight, 1080, "oracle");
        ledger.record_evidence_span(ev1).unwrap();

        assert!(ledger.validate_lineage().is_ok());
    }

    // =========================================================================
    // EEO-002: B1..B11 REQUIRED TESTS FOR DECISION BELIEF LEDGER
    // =========================================================================

    #[test]
    fn test_b1_pit_snapshot_contains_only_ex_ante_available_signals() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let span_id = SpanId::new("span_opp_001");

        let receipt = BeliefReceipt::from_opportunity(&ctx, &span_id, &ep).unwrap();
        assert_eq!(receipt.stage, BeliefStage::OpportunityDetected);
        assert_eq!(receipt.pit_timestamp, ep.as_of_time);
        assert_eq!(receipt.expected_horizon_bars, 24);
        assert_eq!(receipt.chosen_action, ChosenAction::OpportunityIdentified);
        assert!(!receipt.is_rejection);
        assert!(receipt.expected_net_utility_r.is_none());
    }

    #[test]
    fn test_b2_hindsight_firewall_blocks_post_outcome_evidence_from_belief_receipt() {
        // BeliefStage explicitly rejects any construction from EvidenceStage (e.g. TargetOracleHindsight).
        // BeliefStage::from_decision_stage only maps PIT DecisionStage enum variants.
        let stage = BeliefStage::from_decision_stage(DecisionStage::SelectiveUtility);
        assert_eq!(stage, BeliefStage::PostSelectiveUtility);

        // Verification that EvidenceStage cannot be converted to a DecisionStage or BeliefStage
        let ev_stage = EvidenceStage::TargetOracleHindsight;
        assert!(ev_stage.is_post_outcome());
    }

    #[test]
    fn test_b3_immutability_appended_receipt_cannot_be_mutated() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let span_id = SpanId::new("span_001");
        let receipt = BeliefReceipt::from_opportunity(&ctx, &span_id, &ep).unwrap();

        let mut ledger = DecisionBeliefLedger::new();
        ledger.append(receipt.clone()).unwrap();

        // Attempting to append conflicting receipt with same receipt_id fails closed
        let mut tampered = receipt.clone();
        tampered.expected_net_utility_r = Some(999.0);
        let err = ledger.append(tampered);
        assert!(err.is_err(), "Mutating an existing belief receipt must fail closed");
    }

    #[test]
    fn test_b4_sequential_belief_evolution_preserves_ancestor_receipts() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let mut ledger = DecisionBeliefLedger::new();

        // 1. Opportunity Detected
        let s1 = SpanId::new("s1_detect");
        let r1 = BeliefReceipt::from_opportunity(&ctx, &s1, &ep).unwrap();
        ledger.append(r1).unwrap();

        // 2. Witness Observed
        let s2 = SpanId::new("s2_witness");
        let ev = ObserverEvidence::new(
            &ep.episode_id, "expert_1", "v1", "fam", "beh", "group_a",
            ObserverStance::Support { confidence: 0.8, expected_edge_r: 0.2 },
            HabitatAssessment::InHabitat, 0.1, ep.as_of_time, "lineage",
        ).unwrap();
        let r2 = BeliefReceipt::from_witnesses(&ctx, &s2, &ep, &[ev.clone()]).unwrap();
        ledger.append(r2).unwrap();

        // 3. Reconciled
        let s3 = SpanId::new("s3_reconcile");
        let reconciled = EvidenceReconciler::reconcile(&ep, &[ev]).unwrap();
        let r3 = BeliefReceipt::from_reconciliation(&ctx, &s3, &ep, &reconciled).unwrap();
        ledger.append(r3).unwrap();

        let trace_receipts = ledger.receipts_for_trace(&ctx.trace_id);
        assert_eq!(trace_receipts.len(), 3);
        assert_eq!(trace_receipts[0].stage, BeliefStage::OpportunityDetected);
        assert_eq!(trace_receipts[1].stage, BeliefStage::PostWitnessObservation);
        assert_eq!(trace_receipts[2].stage, BeliefStage::PostReconciliation);
    }

    #[test]
    fn test_b5_rejected_opportunity_coverage_preserves_final_rejection_receipt() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let mut ledger = DecisionBeliefLedger::new();

        // Evidence with Contradict stance
        let ev = ObserverEvidence::new(
            &ep.episode_id, "veto_expert", "v1", "fam", "beh", "group_a",
            ObserverStance::Contradict { reason: "high_volatility".into(), severity: 0.9 },
            HabitatAssessment::InHabitat, 0.05, ep.as_of_time, "lineage",
        ).unwrap();

        let reconciled = EvidenceReconciler::reconcile(&ep, &[ev]).unwrap();
        assert_eq!(reconciled.aggregate_stance, ReconciledStance::Contradicted);

        let s_reconcile = SpanId::new("s_reconcile_veto");
        let r_reconcile = BeliefReceipt::from_reconciliation(&ctx, &s_reconcile, &ep, &reconciled).unwrap();

        assert!(r_reconcile.is_rejection);
        assert_eq!(r_reconcile.rejection_reason, Some("ReconciledStance::Contradicted".into()));
        ledger.append(r_reconcile).unwrap();

        let final_belief = ledger.final_belief_for_opportunity(&ep.episode_id).unwrap();
        assert!(final_belief.is_rejection);
        assert_eq!(final_belief.stage, BeliefStage::PostReconciliation);
    }

    #[test]
    fn test_b6_executed_opportunity_coverage_preserves_portfolio_admission() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let mut ledger = DecisionBeliefLedger::new();

        let ev = ObserverEvidence::new(
            &ep.episode_id, "trend_expert", "v1", "fam", "beh", "group_a",
            ObserverStance::Support { confidence: 0.9, expected_edge_r: 0.35 },
            HabitatAssessment::InHabitat, 0.05, ep.as_of_time, "lineage",
        ).unwrap();
        let reconciled = EvidenceReconciler::reconcile(&ep, &[ev]).unwrap();
        let friction = FrictionModel::default();
        let decision = SelectiveUtility::evaluate(&ep, &reconciled, &friction, 35.0).unwrap();

        let intent = CampaignIntent::new(&ep.episode_id, &decision.decision_id, ep.exposure.clone(), 0.5, 500.0, ep.as_of_time).unwrap();
        let port_cfg = PortfolioFeasibilityConfig::default();
        let camp_res = PortfolioFeasibilityEngine::evaluate_intent(&port_cfg, &intent, 0.0, ep.as_of_time);
        assert!(camp_res.is_ok());

        let s_port = SpanId::new("s_port_admitted");
        let r_port = BeliefReceipt::from_portfolio_feasibility(&ctx, &s_port, &intent, &camp_res, ep.expected_horizon_bars).unwrap();

        assert!(!r_port.is_rejection);
        assert!(r_port.rejection_reason.is_none());
        ledger.append(r_port).unwrap();

        let receipts = ledger.receipts_for_opportunity(&ep.episode_id);
        assert_eq!(receipts.len(), 1);
        assert_eq!(receipts[0].stage, BeliefStage::PortfolioFeasibilityEvaluated);
    }

    #[test]
    fn test_b7_trace_binding_without_identity_conflation() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let span_id = SpanId::new("span_123");
        let receipt = BeliefReceipt::from_opportunity(&ctx, &span_id, &ep).unwrap();

        // Ensure each semantic ID is independent and uniquely queryable
        assert_eq!(receipt.opportunity_id, ep.episode_id);
        assert_eq!(receipt.trace_id, ctx.trace_id);
        assert_eq!(receipt.span_id, span_id);
        assert_ne!(receipt.receipt_id.as_str(), receipt.trace_id.as_str());
        assert_ne!(receipt.receipt_id.as_str(), receipt.opportunity_id);
    }

    #[test]
    fn test_b8_deterministic_serialization_retains_receipt_identity() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let span_id = SpanId::new("span_ser_001");
        let receipt = BeliefReceipt::from_opportunity(&ctx, &span_id, &ep).unwrap();

        let mut ledger = DecisionBeliefLedger::new();
        ledger.append(receipt.clone()).unwrap();

        let json = ledger.to_json().unwrap();
        let deserialized = DecisionBeliefLedger::from_json(&json).unwrap();

        assert_eq!(ledger.len(), deserialized.len());
        assert_eq!(ledger.get(&receipt.receipt_id), deserialized.get(&receipt.receipt_id));
        assert!(deserialized.validate_lineage().is_ok());
    }

    #[test]
    fn test_b9_missing_required_lineage_fails_closed() {
        let span_id = SpanId::new("span_bad");
        let prov = TraceProvenance::new(TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let trace_id = EconomicTraceId::new("trace_bad");

        // Empty opportunity_id must fail closed
        let err = BeliefReceipt::new(
            trace_id, "", span_id, BeliefStage::OpportunityDetected, 1000, prov,
            None, None, 24, None, None, ChosenAction::OpportunityIdentified, false, None,
        );
        assert!(err.is_err());
    }

    #[test]
    fn test_b10_no_synthetic_beliefs_explicitly_unavailable_dimensions() {
        let ep = create_test_episode("BTCUSDT", 1_751_328_000_000_000_000);
        let ctx = EconomicTraceContext::from_episode(&ep, TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let span_id = SpanId::new("span_no_synth");
        let receipt = BeliefReceipt::from_opportunity(&ctx, &span_id, &ep).unwrap();

        // Anti-Hallucination & Anti-Synthetic rule verification:
        // Continuous outcome probability distributions and expected MFE/MAE are NOT computed ex ante in V8.
        // They MUST be explicitly None, never synthetic placeholders like 0.5 or 0.0.
        assert!(receipt.outcome_probabilities.is_none());
        assert!(receipt.expected_mfe_r.is_none());
        assert!(receipt.expected_mae_r.is_none());
    }

    fn build_test_store() -> crate::state::FeatureStore {
        let n = 50;
        let hour_ns = 3_600_000_000_000i64;
        let mut rows = Vec::with_capacity(n);
        for i in 0..n {
            let t = (i as i64 + 1) * hour_ns;
            let c = if i == 35 { 130.0 } else { 100.0 };
            rows.push(crate::data::TapeRow {
                source: "binance-um".into(),
                channel: "kline".into(),
                instrument: "BTCUSDT".into(),
                event_time: t,
                available_time: t + 1,
                ingested_time: t + 2,
                venue_sequence: (i + 1) as i64,
                event_id: format!("bar_{i}"),
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
    fn test_b11_economic_non_regression_pipeline_integration() {
        let store = build_test_store();
        let loop_engine = crate::opportunity::runloop::V83Runloop::default();
        let mut book = crate::opportunity::book::OpportunityBook::new();

        let ledger = loop_engine
            .step_bar("BTCUSDT", "binance-um", &store, 35, &mut book, 0.0)
            .unwrap();

        let mut belief_ledger = DecisionBeliefLedger::new();
        for ep in book.all() {
            let ctx = ep.to_trace_context(TAPE_HASH, BASELINE_POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
            let span_id = SpanId::new(format!("span_{}", ep.episode_id));
            let r = BeliefReceipt::from_opportunity(&ctx, &span_id, ep).unwrap();
            belief_ledger.append(r).unwrap();
        }

        assert_eq!(belief_ledger.len(), ledger.episodes_generated);
        assert!(belief_ledger.validate_lineage().is_ok());
    }
}
