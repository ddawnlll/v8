//! 8-Point Automated Audit-of-Audit Sabotage Test Suite (D-132, Rule 32, PH2-003A.2).
//!
//! Enforces:
//! 1. Counterfactual labeled as Realized -> MUST FAIL
//! 2. Missing cashflow ledger PnL claim -> MUST FAIL
//! 3. Tampered receipt hash -> CLAIM_BLOCKED
//! 4. Injected future timestamp (PIT leak) -> CLAIM_BLOCKED
//! 5. 100 clone witnesses -> N_eff remains invariant (1.0)
//! 6. Missing auditor receipt -> SUPPORTED_EDGE BLOCKED
//! 7. Hardcoded profit injection -> Cashflow conservation failure
//! 8. Oracle leakage into execution layer -> Gatekeeper refusal

#[cfg(test)]
mod tests {
    use crate::authority::{
        Authority, ClaimValue, DecisionAuthority, EvidenceAuthority, ExecutionGatekeeper, RealizationStatus,
    };
    use crate::audit::authority::AuthorityAuditor;
    use crate::audit::cashflow::CashflowAuditor;
    use crate::audit::independence::IndependenceAuditor;
    use crate::audit::lineage::LineageAuditor;
    use crate::audit::reconciliation::ReconciliationAuditor;
    use crate::claims::{ClaimRegistry, StatutoryClaimClass};
    use crate::opportunity::book::{IdentityStatus, OpportunityEpisode};
    use crate::opportunity::evidence::{HabitatAssessment, ObserverEvidence, ObserverStance};
    use crate::opportunity::exposure::{EconomicExposureStructure, ExposureDirection};
    use crate::opportunity::reconcile::EvidenceReconciler;

    fn make_test_episode() -> OpportunityEpisode {
        let exp = EconomicExposureStructure::single_perp(
            "BTCUSDT",
            "BTC",
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        OpportunityEpisode::new(
            exp,
            1_000_000,
            2_000_000,
            24,
            IdentityStatus::Canonical,
            "state_hash",
            "lineage_hash",
        )
        .unwrap()
    }

    /// Sabotage Invariant 1: Counterfactual value labeled as Realized Cashflow MUST FAIL.
    #[test]
    fn test_sabotage_1_counterfactual_labeled_as_realized_must_fail() {
        let auth_illegal = Authority::new(
            EvidenceAuthority::Counterfactual,
            DecisionAuthority::ExecutionAuthorized,
            RealizationStatus::CashflowSettled,
        );

        let validation = StatutoryClaimClass::CounterfactualPotential.validate_authority(&auth_illegal);
        assert!(validation.is_err(), "Sabotage 1: Counterfactual with CashflowSettled MUST fail validation");

        let claim = ClaimValue::new(5000.0, auth_illegal, "receipt_sabotage_1");
        assert!(
            ExecutionGatekeeper::authorize_economic_claim(&claim, "sabotage_1").is_err(),
            "Sabotage 1: Economic gatekeeper MUST block counterfactual claim"
        );
    }

    /// Sabotage Invariant 2: PnL claim without a valid Cashflow Ledger MUST FAIL.
    #[test]
    fn test_sabotage_2_missing_cashflow_ledger_pnl_claim_must_fail() {
        let mut registry = ClaimRegistry::new();
        let unverified_pnl = registry.register_claim(
            StatutoryClaimClass::RealizedCashflow,
            1200.0,
            "USDT",
            Authority::counterfactual_diagnostic(), // Missing cashflow ledger authority
            vec![],
            None,
            None,
            None,
            1_000_000,
        );
        assert!(unverified_pnl.is_err(), "Sabotage 2: Unverified PnL claim without physical ledger MUST fail");
    }

    /// Sabotage Invariant 3: Tampered Receipt Hash MUST BLOCK CLAIM.
    #[test]
    fn test_sabotage_3_tampered_receipt_hash_must_block_claim() {
        let ep = make_test_episode();
        let ev = ObserverEvidence::new(
            &ep.episode_id,
            "expert_sabotage",
            "v1",
            "momentum",
            "trend",
            "group_a",
            ObserverStance::Support {
                confidence: 0.90,
                expected_edge_r: 0.50,
            },
            HabitatAssessment::InHabitat,
            0.10,
            1_000_000,
            "lineage",
        )
        .unwrap();

        let (state, mut receipt) = EvidenceReconciler::reconcile_with_receipt(&ep, &[ev]).unwrap();
        // Tamper receipt payload
        receipt.raw_support_weight += 10.0;

        assert!(
            ReconciliationAuditor::audit_receipt(&state, &receipt).is_err(),
            "Sabotage 3: Tampered receipt hash MUST fail reconciliation audit"
        );
        assert!(
            state.verify_authority(&receipt).is_err(),
            "Sabotage 3: State authority verification MUST fail on tampered receipt"
        );
    }

    /// Sabotage Invariant 4: Injected Future Timestamp (PIT Leak) MUST FAIL.
    #[test]
    fn test_sabotage_4_injected_future_timestamp_must_block_claim() {
        let decision_clock = 1_000_000;
        let inputs = vec![
            ("feat_past".to_string(), 999_999),
            ("feat_current".to_string(), 1_000_000),
            ("feat_leaked_future".to_string(), 1_000_001), // Future leakage
        ];

        let res = LineageAuditor::audit_pit_causality(decision_clock, &inputs);
        assert!(res.is_err(), "Sabotage 4: Future timestamp MUST fail PIT causality audit");
        assert!(res.unwrap_err().contains("PIT_FUTURE_LEAKAGE"));
    }

    /// Sabotage Invariant 5: 100 Clone Witnesses MUST Yield N_eff = 1.0 (Clone Multiplicity Invariance).
    #[test]
    fn test_sabotage_5_100_clone_witnesses_invariance_n_eff_equals_one() {
        let ep = make_test_episode();
        let mut evidences = Vec::with_capacity(100);

        for i in 0..100 {
            evidences.push(
                ObserverEvidence::new(
                    &ep.episode_id,
                    format!("clone_expert_{i}"),
                    "v1",
                    "momentum",
                    "trend",
                    "single_dependency_group", // All 100 in the SAME dependency group
                    ObserverStance::Support {
                        confidence: 0.90,
                        expected_edge_r: 0.50,
                    },
                    HabitatAssessment::InHabitat,
                    0.10,
                    1_000_000,
                    "lineage",
                )
                .unwrap(),
            );
        }

        let (state, receipt) = EvidenceReconciler::reconcile_with_receipt(&ep, &evidences).unwrap();
        assert_eq!(
            state.effective_observer_count, 1.0,
            "Sabotage 5: 100 clones in 1 group MUST yield exactly N_eff = 1.0"
        );
        assert_eq!(
            receipt.effective_observer_count, 1.0,
            "Sabotage 5: Receipt effective count MUST remain exactly 1.0"
        );
    }

    /// Sabotage Invariant 6: Missing Auditor Receipt MUST Block SUPPORTED_EDGE Claim.
    #[test]
    fn test_sabotage_6_missing_auditor_receipt_blocks_supported_edge() {
        // Implementer and Auditor are the same agent
        let collusion_res = IndependenceAuditor::audit_dual_key(
            "agent_alpha",
            "agent_alpha", // Self-grading violation!
            "digest_123",
            "digest_123",
            true,
        );
        assert!(
            collusion_res.is_err(),
            "Sabotage 6: Self-grading attempt MUST fail independence audit"
        );

        // Auditor failed zero-synthetic check
        let synthetic_leak_res = IndependenceAuditor::audit_dual_key(
            "agent_worker",
            "agent_auditor",
            "digest_456",
            "digest_456",
            false, // Failed zero synthetic
        );
        assert!(
            synthetic_leak_res.is_err(),
            "Sabotage 6: Synthetic leak audit failure MUST block verification"
        );
    }

    /// Sabotage Invariant 7: Hardcoded Profit Injection Violates Double-Entry Conservation.
    #[test]
    fn test_sabotage_7_hardcoded_pnl_injection_violates_conservation() {
        let initial_equity = 10_000.0;
        let cashflows = vec![100.0, -50.0, 25.0]; // Sum = +75.0
        let open_positions = 0.0;
        let injected_final_equity = 10_175.0; // Fabricated +$100 extra!

        let res = CashflowAuditor::audit_conservation(
            initial_equity,
            injected_final_equity,
            &cashflows,
            open_positions,
        );
        assert!(
            res.is_err(),
            "Sabotage 7: Fabricated equity injection MUST fail double-entry conservation"
        );
        assert!(res.unwrap_err().contains("CASHFLOW_CONSERVATION_VIOLATION"));
    }

    /// Sabotage Invariant 8: Oracle/Counterfactual Leakage to Execution Layer MUST FAIL.
    #[test]
    fn test_sabotage_8_oracle_leakage_to_execution_must_fail() {
        let oracle_claim = ClaimValue::new(
            1.0,
            Authority::new(
                EvidenceAuthority::Counterfactual,
                DecisionAuthority::DiagnosticOnly,
                RealizationStatus::Hypothetical,
            ),
            "receipt_oracle_hindsight",
        );

        let auth_res = ExecutionGatekeeper::authorize_execution(&oracle_claim, "dispatch_to_exchange");
        assert!(
            auth_res.is_err(),
            "Sabotage 8: Diagnostic oracle claim MUST be blocked by ExecutionGatekeeper"
        );

        let monotonicity_check = AuthorityAuditor::audit_monotonicity(
            &Authority::realized_cashflow(),
            &[oracle_claim.authority],
        );
        assert!(
            monotonicity_check.is_err(),
            "Sabotage 8: Attempting to escalate oracle authority to realized cashflow MUST fail monotonicity audit"
        );
    }
}
