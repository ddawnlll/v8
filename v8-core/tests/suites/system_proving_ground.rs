//! Constitutional Sabotage Suite — Part 4: AF-T12, AF-T18 (D-147, D-149, Rule 44).

use v8_core::system_proving::run::SystemProvingGroundRunner;
use v8_core::system_proving::attribution::{FailureAttributionBreakdown, FailureDomain};
use v8_core::world::spec::{SyntheticPopulation, WorldFamily, WorldSpec};
use v8_core::world::structural::StructuralWorldGenerator;

#[test]
fn test_af_t12_system_proving_ground_exercises_full_pipeline() {
    let spec = WorldSpec {
        family: WorldFamily::StructuralRegime,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "ETHUSDT".to_string(),
        n_bars: 200,
        base_price: 3000.0,
        volatility_annualized: 0.70,
        jump_frequency: 8.0,
        jump_mean: -0.03,
        jump_std: 0.05,
        seed: 777,
    };

    let world_receipt = StructuralWorldGenerator::generate(&spec);

    let receipt = SystemProvingGroundRunner::run_full_chain(
        "policy-full-chain-macro",
        &world_receipt,
        1000.0,
        1700000000000000000,
    );

    // Invariant (AF-T12): Must exercise full campaign lifecycle, double entry, and multi-step execution
    assert!(receipt.exercises_full_pipeline);
    assert!(receipt.total_trades > 0);
    assert!(receipt.total_campaigns > 0);
    assert!(receipt.metrics.is_double_entry_reconciled());
}

#[test]
fn test_af_t18_failure_attribution_conservation_and_domain_mapping() {
    let mut attribution = FailureAttributionBreakdown::default();

    attribution.record_failure(FailureDomain::Detection);
    attribution.record_failure(FailureDomain::Reconciliation);
    attribution.record_failure(FailureDomain::Execution);
    attribution.record_failure(FailureDomain::Exit);
    attribution.record_failure(FailureDomain::Exit);

    assert_eq!(attribution.total_failures, 5);
    assert_eq!(attribution.counts_by_domain.get(&FailureDomain::Exit), Some(&2));
    assert_eq!(attribution.counts_by_domain.get(&FailureDomain::Detection), Some(&1));

    // Invariant (AF-T18): Domain sum must conserve total failures exactly
    assert!(attribution.verify_conservation());
}
