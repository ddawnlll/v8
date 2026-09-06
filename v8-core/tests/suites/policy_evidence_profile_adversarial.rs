//! Adversarial suite for D-152 scenario-centric measurement (G0-G9).
//!
//! Each test attempts a forbidden promotion and must fail closed:
//! quad promotion, synthetic escalation, holdout reuse, scenario cherry-picking,
//! correlated-world inflation, certificate scalar collapse.

use v8_core::assurance::case::{CaseIdentity, EvaluationEpoch};
use v8_core::assurance::claim::AssuranceClaim;
use v8_core::assurance::evidence_profile::{
    audit_statistical_triple, gate_g0, gate_g1, synthetic_fail_may_challenge,
    synthetic_pass_confirms_no_edge, DataRole, EconomicConclusion, FrozenOOSState, LiveState,
    PolicyEvidenceProfile, RobustnessTopology, ScenarioCell, ShadowState,
};
use v8_core::assurance::receipt::ClaimStatus;
use v8_core::assurance::{CertificateStatus, GateId};
use v8_core::evaluation::allegory::ArchetypeId;
use v8_core::world::{GeneratorPassport, SyntheticPopulation, WorldFamily, WorldSpec};

fn dummy_profile() -> PolicyEvidenceProfile {
    PolicyEvidenceProfile {
        policy_id: "policy-test".to_string(),
        policy_hash: "ph".to_string(),
        config_hash: "ch".to_string(),
        code_hash: "code".to_string(),
        lineage_id: "lin-1".to_string(),
        evaluation_case_id: CaseIdentity("case-1".to_string()),
        epoch_id: EvaluationEpoch(1),
        historical_net_usdt: 509.24,
        historical_gross_usdt: 1155.56,
        historical_fee_usdt: 646.32,
        historical_role: DataRole::BurnedDiagnostic,
        max_drawdown_pct: 6.3,
        trade_count: 820,
        asset_concentration_pct: 67.0,
        scenario_cells: vec![],
        robustness: RobustnessTopology {
            nearest_plausible_defeater: None,
            minimal_defeater_distance: None,
            failed_scenario_families: vec![],
            unknown_regions: vec!["ALL".to_string()],
            passport_bindings: Default::default(),
            world_coverage_manifest: None,
        },
        frozen_oos: FrozenOOSState::NotRun,
        shadow: ShadowState::NotAvailable,
        live: LiveState::None,
        certificate: CertificateStatus::Revoked("MULTI_DIMENSIONAL_STATUS_DEFICIT".to_string()),
        gates: vec![],
        conclusion: EconomicConclusion::NotProductionSupported,
    }
}

#[test]
fn adv_quad_cannot_mint_edge() {
    let p = dummy_profile();
    assert_eq!(p.historical_role.promotion_authority(), "NONE");
    assert_eq!(p.derive_conclusion(), EconomicConclusion::NotProductionSupported);
    let text = p.render_text();
    assert!(text.contains("BURNED_DIAGNOSTIC"));
    assert!(text.contains("NONE"));
    assert!(!text.contains("SUPPORTED_EDGE"));
}

#[test]
fn adv_quad_render_never_bare_number() {
    let p = dummy_profile();
    let text = p.render_text();
    assert!(text.contains("Historical Diagnostic Net Growth"));
    assert!(text.contains("Data role: BURNED_DIAGNOSTIC"));
}

#[test]
fn adv_synthetic_pass_grants_nothing() {
    let passport = GeneratorPassport::new_v2(
        "gen-good".to_string(), 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
    );
    assert!(passport.passport_passed);
    assert!(synthetic_pass_confirms_no_edge(&passport));
    assert!(passport.does_not_confer_economic_edge());
    assert!(!AssuranceClaim::EconomicReplication.accepts_synthetic_evidence());
    assert!(!AssuranceClaim::RealizedCashflow.accepts_synthetic_evidence());
}

#[test]
fn adv_garbage_generator_cannot_veto() {
    let garbage = GeneratorPassport::new_v2(
        "gen-garbage".to_string(), 0.2, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
    );
    assert!(!garbage.passport_passed);
    assert!(!synthetic_fail_may_challenge(&garbage, AssuranceClaim::StructuralRobustness));
    assert!(!synthetic_fail_may_challenge(&garbage, AssuranceClaim::EconomicReplication));
}

#[test]
fn adv_valid_generator_scoped_authority_only() {
    let valid = GeneratorPassport::new_v2(
        "gen-valid".to_string(), 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
    );
    assert!(synthetic_fail_may_challenge(&valid, AssuranceClaim::StructuralRobustness));
    assert!(!synthetic_fail_may_challenge(&valid, AssuranceClaim::EconomicReplication));
    assert!(!synthetic_fail_may_challenge(&valid, AssuranceClaim::RealizedCashflow));
    assert!(!synthetic_fail_may_challenge(&valid, AssuranceClaim::DeploymentQualified));
}

#[test]
fn adv_g0_blocks_on_synthetic_leak() {
    let v = gate_g0(false, true, true);
    assert_eq!(v.status, ClaimStatus::Blocked);
    assert!(v.is_blocking());
    assert!(v.authority_denied.contains(&"SUPPORTED_EDGE".to_string()));
}

#[test]
fn adv_g1_blocks_without_estimand() {
    let v = gate_g1(false, true, true);
    assert_eq!(v.status, ClaimStatus::Blocked);
    assert!(v.is_blocking());
    let ok = gate_g1(true, true, true);
    assert_eq!(ok.status, ClaimStatus::Verified);
}

#[test]
fn adv_statistical_triple_still_blocks() {
    let audit = audit_statistical_triple();
    assert!(audit.blocks_support);
    assert!(!audit.dsr_genuine);
    assert!(audit.rationale.contains("NO_ECONOMIC_CLAIM"));
}

#[test]
fn adv_no_scalar_average_hides_failure() {
    let mut p = dummy_profile();
    p.scenario_cells = vec![
        ScenarioCell {
            scenario_id: "trend".to_string(),
            archetype: Some(ArchetypeId::A02SlowGrindTrend),
            world_family: None,
            coverage_bars: 1000,
            episode_count: 10,
            net_utility_usdt: 200.0,
            survival: true,
            max_drawdown_pct: 3.0,
            fee_retention_pct: 60.0,
            failure_phenotype: None,
            evidence_authority: "HISTORICAL_ARCHETYPE".to_string(),
            status: ClaimStatus::Verified,
        },
        ScenarioCell {
            scenario_id: "chop".to_string(),
            archetype: Some(ArchetypeId::A08ChopWhipsawHell),
            world_family: None,
            coverage_bars: 1000,
            episode_count: 10,
            net_utility_usdt: -300.0,
            survival: false,
            max_drawdown_pct: 18.0,
            fee_retention_pct: 10.0,
            failure_phenotype: Some("CHOP_DEATH".to_string()),
            evidence_authority: "HISTORICAL_ARCHETYPE".to_string(),
            status: ClaimStatus::Blocked,
        },
    ];
    p.robustness.failed_scenario_families = vec!["chop".to_string()];
    let text = p.render_text();
    assert!(text.contains("1/2 survived"));
    assert!(text.contains("chop"));
    assert_eq!(p.derive_conclusion(), EconomicConclusion::NotProductionSupported);
}

#[test]
fn adv_unknown_coverage_stays_unknown() {
    let cell = ScenarioCell::unknown("liquidity_stress");
    assert_eq!(cell.status, ClaimStatus::Unresolved);
    assert_eq!(cell.episode_count, 0);
}

#[test]
fn adv_frozen_oos_alone_not_production() {
    let mut p = dummy_profile();
    p.frozen_oos = FrozenOOSState::Pass { receipt: "oos-1".to_string() };
    assert_eq!(p.derive_conclusion(), EconomicConclusion::NotProductionSupported);
}

#[test]
fn adv_certificate_decorative_without_enforcement() {
    let p = dummy_profile();
    assert!(matches!(p.certificate, CertificateStatus::Revoked(_)));
    assert_eq!(p.conclusion, EconomicConclusion::NotProductionSupported);
}

#[test]
fn adv_synthetic_population_maps_to_no_authority() {
    assert_eq!(DataRole::from(SyntheticPopulation::SyntheticDev).promotion_authority(), "NONE");
    assert_eq!(
        DataRole::from(SyntheticPopulation::SyntheticQualification).promotion_authority(),
        "NONE"
    );
    assert_eq!(DataRole::from(SyntheticPopulation::SyntheticNovelty).promotion_authority(), "NONE");
    assert_eq!(DataRole::BurnedDiagnostic.promotion_authority(), "NONE");
    assert_eq!(DataRole::FrozenOOS.promotion_authority(), "REPLICATION_ONLY");
}

#[test]
fn adv_world_spec_deterministic_receipt() {
    let spec = WorldSpec {
        family: WorldFamily::StructuralRegime,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "BTCUSDT".to_string(),
        n_bars: 50,
        base_price: 50000.0,
        volatility_annualized: 0.65,
        jump_frequency: 12.0,
        jump_mean: -0.015,
        jump_std: 0.03,
        seed: 7,
    };
    let a = v8_core::world::structural::StructuralWorldGenerator::generate(&spec);
    let b = v8_core::world::structural::StructuralWorldGenerator::generate(&spec);
    assert_eq!(a.world_digest, b.world_digest);
    assert!(a.bars.iter().all(|bar| bar.is_valid()));
    let _ = GateId::G4SyntheticFalsification.as_str();
}
