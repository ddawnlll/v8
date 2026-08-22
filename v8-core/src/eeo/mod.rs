#![allow(dead_code, unused_imports, unused_variables, unused_mut)]
//! V8.3 Economic Evidence & Observability Architecture (EEO-003 through EEO-010, D-136).
//!
//! Owning Authority: V8 Constitution Rules 1, 3, 4, 18, 20, 21, 24, 28, 35; D-136.
//!
//! Architectural Modules:
//! - `contract`: Universal Evidence Provider Interface, Evidence Bundle Contract & Registry (EEO-003).
//! - `foundational`: Foundational Deterministic Providers P01–P04 (EEO-004).
//! - `graph`: Directed Evidence Graph & Central Audit Adjudication (EEO-005).
//! - `diagnostic`: Diagnostic Providers P05–P09 & Economic Pathology Map (EEO-006).
//! - `replay`: Registered Counterfactual Replay & Market Response Models (EEO-007).
//! - `alignment`: Path Alignment & Pairwise Interaction Analysis (EEO-008).
//! - `challenge`: Challenge Layer P11–P12 & Multiplicity Ledger (EEO-009).
//! - `qualification`: Constitution Qualification Harness Q01–Q15 (EEO-010).

pub mod contract;
pub mod foundational;
pub mod graph;
pub mod diagnostic;
pub mod replay;
pub mod alignment;
pub mod challenge;
pub mod qualification;
pub mod report;

#[allow(unused_imports)]
pub use contract::{
    Assumption, AuditEvidenceProvider, EvidenceAuthority, EvidenceBundle, EvidenceClaim,
    EvidenceContext, EvidenceCoverage, EvidenceDependency, EvidenceScope, ProviderIdentity,
    ProviderLifecycle, ProviderRegistry, UncertaintyDescriptor,
};
#[allow(unused_imports)]
pub use foundational::{
    P01CashflowConservationProvider, P02TraceLineageIntegrityProvider,
    P03PitProvenanceFirewallProvider, P04ExecutionFidelityProvider,
};
#[allow(unused_imports)]
pub use graph::{ClaimEdge, ClaimRelationship, ClaimVerdict, EvidenceGraph};
#[allow(unused_imports)]
pub use diagnostic::{
    EconomicPathologyMap, P05BeliefCalibrationProvider, P06OracleGapCoverageProvider,
    P07ExpertEvidenceQualityProvider, P08DecisionTransferEfficiencyProvider,
    P09ImplementationShortfallProvider, PathologyClass, PathologyRecord,
};
#[allow(unused_imports)]
pub use replay::{
    ContinuationPolicy, CounterfactualReplayEngine, MarketResponseModel, RegisteredIntervention,
    ReplayContext,
};
#[allow(unused_imports)]
pub use alignment::{
    AlignedOpportunityRecord, AlignmentClass, InteractionEffect, PathAlignmentEngine,
};
#[allow(unused_imports)]
pub use challenge::{
    CommonModeAuditor, CriticFalsificationOutcome, P11RobustnessMultiplicityProvider,
    P12CausalCriticProvider, ResearchMultiplicityEntry, ResearchMultiplicityLedger,
};
#[allow(unused_imports)]
pub use qualification::{QualificationHarness, QualificationMetrics};
#[allow(unused_imports)]
pub use report::{
    BaselineEconomics, CashflowConservationSummary, EconomicPathologyReport,
    OracleFunnelSummary, RunIdentity,
};

#[cfg(test)]
mod tests {
    use super::*;
    use crate::telemetry::{
        DecisionBeliefLedger, DecisionSpan, DecisionStage, EconomicTraceContext, EconomicTraceLedger,
        SpanId, TraceProvenance,
    };

    const TAPE_HASH: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    const POLICY_HASH: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const CONSTITUTION_HASH: &str = "c0n5717u710nc0n5717u710nc0n5717u710nc0n5717u710nc0n5717u710nc0n5";
    const CODE_HASH: &str = "c0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0de";

    fn create_test_context() -> (EconomicTraceLedger, DecisionBeliefLedger, EconomicTraceContext) {
        let prov = TraceProvenance::new(TAPE_HASH, POLICY_HASH, CONSTITUTION_HASH, CODE_HASH).unwrap();
        let ctx = EconomicTraceContext::new("ep_btc_001", crate::telemetry::TrajectoryType::Observed, "canonical", 1_751_328_000_000_000_000, prov).unwrap();
        let mut trace_ledger = EconomicTraceLedger::new();
        trace_ledger.register_context(ctx.clone()).unwrap();

        let s1 = DecisionSpan::new(ctx.trace_id.clone(), None, DecisionStage::OpportunityDetection, 1_751_328_000_000_000_000, "s1");
        trace_ledger.record_span(s1).unwrap();

        let belief_ledger = DecisionBeliefLedger::new();
        (trace_ledger, belief_ledger, ctx)
    }

    #[test]
    fn test_eeo003_provider_registry_and_contract_integrity() {
        let mut registry = ProviderRegistry::new();
        registry.register(Box::new(P01CashflowConservationProvider::default()));
        registry.register(Box::new(P02TraceLineageIntegrityProvider::default()));
        registry.register(Box::new(P03PitProvenanceFirewallProvider::default()));
        registry.register(Box::new(P04ExecutionFidelityProvider::default()));

        assert_eq!(registry.providers().len(), 4);
        assert!(registry.get_by_id("P01_CASHFLOW_CONSERVATION").is_some());
    }

    #[test]
    fn test_eeo004_foundational_providers_deterministic_evaluation() {
        let (trace_ledger, belief_ledger, ctx) = create_test_context();
        let scope = EvidenceScope::single_trace("BTCUSDT", "binance-um", 1_751_328_000_000_000_000, ctx.trace_id.clone());
        let ev_ctx = EvidenceContext::new(&trace_ledger, &belief_ledger, &scope, 1_751_328_000_000_000_000);

        let p01 = P01CashflowConservationProvider::default();
        let b01 = p01.evaluate(&ev_ctx).unwrap();
        assert_eq!(b01.provider.provider_id, "P01_CASHFLOW_CONSERVATION");
        assert_eq!(b01.claims.len(), 1);

        let p02 = P02TraceLineageIntegrityProvider::default();
        let b02 = p02.evaluate(&ev_ctx).unwrap();
        assert_eq!(b02.provider.provider_id, "P02_TRACE_LINEAGE_INTEGRITY");

        let p03 = P03PitProvenanceFirewallProvider::default();
        let b03 = p03.evaluate(&ev_ctx).unwrap();
        assert_eq!(b03.provider.provider_id, "P03_PIT_PROVENANCE_FIREWALL");
    }

    #[test]
    fn test_eeo005_evidence_graph_and_audit_adjudication_with_anti_self_certification() {
        let (trace_ledger, belief_ledger, ctx) = create_test_context();
        let scope = EvidenceScope::single_trace("BTCUSDT", "binance-um", 1_751_328_000_000_000_000, ctx.trace_id.clone());
        let ev_ctx = EvidenceContext::new(&trace_ledger, &belief_ledger, &scope, 1_751_328_000_000_000_000);

        let p02 = P02TraceLineageIntegrityProvider::default();
        let b02 = p02.evaluate(&ev_ctx).unwrap();
        let p03 = P03PitProvenanceFirewallProvider::default();
        let b03 = p03.evaluate(&ev_ctx).unwrap();

        let mut graph = EvidenceGraph::new();
        graph.ingest_bundle(&b02);
        graph.ingest_bundle(&b03);

        let claim_p02 = &b02.claims[0].claim_id;
        let claim_p03 = &b03.claims[0].claim_id;

        // P03 supports P02 claim -> Valid cross-provider support
        assert!(graph.add_edge(claim_p03, claim_p02, ClaimRelationship::Supports).is_ok());

        // P02 supporting its own claim -> Violates Anti-Self-Certification rule
        let self_support_err = graph.add_edge(claim_p02, claim_p02, ClaimRelationship::Supports);
        // Self-loop on same provider is rejected by Anti-Self-Certification
        assert!(self_support_err.is_err());
        graph.adjudicate();
        assert_eq!(graph.get_verdict(claim_p02), Some(ClaimVerdict::Supported));
    }

    #[test]
    fn test_eeo006_diagnostic_providers_and_pathology_map() {
        let (trace_ledger, belief_ledger, ctx) = create_test_context();
        let scope = EvidenceScope::single_trace("BTCUSDT", "binance-um", 1_751_328_000_000_000_000, ctx.trace_id.clone());
        let ev_ctx = EvidenceContext::new(&trace_ledger, &belief_ledger, &scope, 1_751_328_000_000_000_000);

        let p05 = P05BeliefCalibrationProvider::default();
        let b05 = p05.evaluate(&ev_ctx).unwrap();

        let p06 = P06OracleGapCoverageProvider::default();
        let b06 = p06.evaluate(&ev_ctx).unwrap();
        assert_eq!(b06.claims.len(), 1); // Oracle gap unavailable when no funnel provided

        let mut graph = EvidenceGraph::new();
        graph.ingest_bundle(&b05);
        graph.ingest_bundle(&b06);
        graph.adjudicate();

        let path_map = EconomicPathologyMap::build_from_adjudication(&graph, &belief_ledger);
        assert!(!path_map.is_empty());
    }

    #[test]
    fn test_eeo007_registered_counterfactual_replay_upstream_invalidation() {
        let (mut trace_ledger, mut belief_ledger, ctx) = create_test_context();
        let prov = ctx.provenance.clone();
        let intervention = RegisteredIntervention::a1_breakeven_ratchet();

        let replay_ctx = ReplayContext {
            baseline_trace_id: ctx.trace_id.clone(),
            opportunity_id: ctx.opportunity_id.clone(),
            intervention,
            continuation_policy: ContinuationPolicy::CanonicalContinuation,
            market_response: MarketResponseModel::ExogenousTape,
            start_time: 1_751_328_000_000_000_000,
        };

        let cf_ctx = CounterfactualReplayEngine::execute_replay(
            &replay_ctx,
            &mut trace_ledger,
            &mut belief_ledger,
            prov,
        )
        .unwrap();

        assert!(cf_ctx.trajectory_type.is_counterfactual());
        assert!(trace_ledger.validate_lineage().is_ok());
    }

    #[test]
    fn test_eeo008_path_alignment_and_pairwise_interaction() {
        let (base_tl, base_bl, ctx_base) = create_test_context();
        let (chall_tl, chall_bl, ctx_chall) = create_test_context();

        let opps = vec![ctx_base.opportunity_id.clone()];
        let aligned = PathAlignmentEngine::align_trajectories(
            &opps, &base_tl, &chall_tl, &base_bl, &chall_bl,
        );

        assert_eq!(aligned.len(), 1);
        assert_eq!(aligned[0].alignment_class, AlignmentClass::SameOpportunityDifferentExpression);

        let interaction = PathAlignmentEngine::compute_interaction("int_a", "int_b", 0.15, 0.10, 0.30);
        assert!(interaction.is_synergistic);
        assert!((interaction.interaction_delta_r - 0.05).abs() < 1e-9);
    }

    #[test]
    fn test_eeo009_challenge_layer_and_common_mode_auditor() {
        let mut mult_ledger = ResearchMultiplicityLedger::new();
        mult_ledger.record_trial(ResearchMultiplicityEntry {
            experiment_id: "exp_1".to_string(),
            candidate_hypotheses_tested: 12,
            temporal_slices_evaluated: 4,
            symbols_evaluated: 4,
            bonferroni_adjusted_significance_level: 0.0041,
            effective_search_size: 12,
        });
        assert_eq!(mult_ledger.total_hypotheses_tested(), 12);

        let p01 = P01CashflowConservationProvider::default();
        let (trace_ledger, belief_ledger, ctx) = create_test_context();
        let scope = EvidenceScope::single_trace("BTCUSDT", "binance-um", 1_751_328_000_000_000_000, ctx.trace_id);
        let ev_ctx = EvidenceContext::new(&trace_ledger, &belief_ledger, &scope, 1_751_328_000_000_000_000)
            .with_multiplicity_ledger(&mult_ledger);
        let b01 = p01.evaluate(&ev_ctx).unwrap();

        let downgraded = CommonModeAuditor::audit_common_mode(&[b01], &["v8-cashflow-core".to_string()]);
        assert_eq!(downgraded.len(), 1);
        assert_eq!(downgraded[0], "P01_CASHFLOW_CONSERVATION");
    }

    #[test]
    fn test_eeo010_qualification_harness_suite_metrics() {
        let metrics = QualificationHarness::run_qualification_suite();
        assert_eq!(metrics.injected_faults, 14);
        assert_eq!(metrics.correctly_localized, 14);
        assert_eq!(metrics.top_1_localization_rate, 1.0);
        assert_eq!(metrics.false_accusations_on_clean_controls, 0);
        assert_eq!(metrics.provider_crashes, 0);
    }

    #[test]
    fn test_eeo015_economic_pathology_report_compilation() {
        let (trace_ledger, belief_ledger, ctx) = create_test_context();
        let run_id = RunIdentity {
            tape_hash: TAPE_HASH.to_string(),
            policy_hash: POLICY_HASH.to_string(),
            constitution_hash: CONSTITUTION_HASH.to_string(),
            code_hash: CODE_HASH.to_string(),
            run_timestamp_ns: 1_751_328_000_000_000_000,
            symbol: "BTCUSDT".to_string(),
            venue: "binance-um".to_string(),
        };

        let baseline = BaselineEconomics {
            initial_balance_usdt: 1000.0,
            terminal_equity_usdt: 1050.0,
            net_profit_usdt: 50.0,
            total_return_pct: 5.0,
            profit_factor: 1.25,
            win_rate_pct: 42.0,
            max_drawdown_pct: 3.5,
            total_fee_drag_usdt: 12.0,
            n_trades_admitted: 40,
        };

        let cashflow_summary = CashflowConservationSummary {
            total_flows: 40,
            total_gross_pnl_usdt: 62.0,
            total_fees_usdt: 12.0,
            total_funding_usdt: 0.0,
            total_slippage_usdt: 0.0,
            total_unexplained_delta_usdt: 0.0,
            is_conserved: true,
        };

        let oracle_funnel = OracleFunnelSummary {
            grammar_detected: 100,
            witness_reached: 100,
            reconciled_supported: 70,
            utility_positive: 50,
            portfolio_admitted: 40,
            executed: 40,
            raw_oracle_gap: 60,
            realizable_gap: 0,
        };

        let mut graph = EvidenceGraph::new();
        let path_map = EconomicPathologyMap::new();
        let metrics = QualificationHarness::run_qualification_suite();

        let report = EconomicPathologyReport::compile(
            run_id,
            baseline,
            cashflow_summary,
            oracle_funnel,
            2800,
            &path_map,
            &graph,
            metrics,
        );

        assert_eq!(report.final_verdict, "QUALIFIED_FOR_CONSTITUTIONAL_RATIFICATION");
        let json = report.to_json().unwrap();
        assert!(json.contains("v8.3-eeo-d136-v1.0"));
    }
}

