//! Constitutional Sabotage Suite — Part 3: AF-T01, AF-T13, AF-T14 (D-147, D-149, D-150, Rule 44).

use v8_core::world::spec::{SyntheticPopulation, WorldFamily, WorldSpec};
use v8_core::world::structural::StructuralWorldGenerator;
use v8_core::world::resample::BlockResampleGenerator;
use v8_core::world::surgery::{CounterfactualSurgeryEngine, SurgeryConfig};
use v8_core::world::passport::GeneratorPassport;
use v8_core::world::reverse_stress::ReverseStressSearchEngine;
use v8_core::assurance::{AssuranceClaim, EvidenceAttestation, AttestationStatus, AuthorityProjection, AdmissibilityVerdict};
use v8_core::authority::{Authority, EvidenceAuthority, DecisionAuthority, RealizationStatus};
use serde_json::json;

#[test]
fn test_af_t13_generator_validity_and_economic_validity_are_separate_claims() {
    // 1. Create a GeneratorPassport with perfect realism across all dimensions
    let passport = GeneratorPassport::new_v2(
        "gen-structural-v1".to_string(),
        0.95, // univariate
        0.92, // temporal
        0.88, // kurtosis
        0.91, // vol clustering
        0.89, // regime duration
        0.88, // multivariate
        0.91, // activity
        0.94, // v8 compat
        0.89, // failure coverage
        0.85, // opp density
    );

    assert!(passport.passport_passed);

    // Invariant: Passport validity certifies synthetic generator realism, NOT policy alpha
    assert!(passport.does_not_confer_economic_edge());

    // 2. An attestation derived from this synthetic generator cannot claim EconomicReplication
    let source_auth = Authority::new(
        EvidenceAuthority::ModelDerived,
        DecisionAuthority::DiagnosticOnly,
        RealizationStatus::Hypothetical,
    );
    let proj = AuthorityProjection::from_source(&source_auth);

    let synthetic_attestation = EvidenceAttestation {
        attestation_id: "att-synth-1".to_string(),
        provider_id: passport.generator_id.clone(),
        provider_lineage: "synthetic-structural-lineage".to_string(),
        target_claim: AssuranceClaim::EconomicReplication,
        authority: proj,
        artifact_hash: "0123456789abcdef0123456789abcdef".to_string(),
        is_synthetic: true,
        status: AttestationStatus::Verified,
        confidence_score: 0.99,
        metric_payload: json!({ "gross_r": 100.0 }),
    };

    assert_eq!(
        synthetic_attestation.check_admissibility(),
        AdmissibilityVerdict::Inadmissible(
            "SYNTHETIC_EVIDENCE_FORBIDDEN_FOR_ECONOMIC_OR_SETTLEMENT_CLAIMS"
        )
    );
}

#[test]
fn test_af_t14_reverse_stress_failure_fraction_is_not_ruin_probability() {
    let spec = WorldSpec {
        family: WorldFamily::StructuralRegime,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "BTCUSDT".to_string(),
        n_bars: 500,
        base_price: 50000.0,
        volatility_annualized: 0.60,
        jump_frequency: 10.0,
        jump_mean: -0.05,
        jump_std: 0.08,
        seed: 42,
    };

    // Run reverse stress search for a 15% drawdown shock
    let failure_defeater = ReverseStressSearchEngine::find_minimal_failure_trajectory(&spec, 15.0);

    assert!(failure_defeater.is_some());
    let defeater = failure_defeater.unwrap();

    // The discovered failure trajectory is an adversarial counterexample for falsification,
    // NOT a forecast of future market ruin probability.
    assert!(defeater.peak_drawdown_pct >= 15.0);
    assert!(defeater.minimal_vector.vol_multiplier >= 1.0);
}

#[test]
fn test_structural_and_resample_and_surgery_generators() {
    let spec = WorldSpec {
        family: WorldFamily::StructuralRegime,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "BTCUSDT".to_string(),
        n_bars: 100,
        base_price: 30000.0,
        volatility_annualized: 0.50,
        jump_frequency: 5.0,
        jump_mean: -0.02,
        jump_std: 0.04,
        seed: 12345,
    };

    // 1. Structural generator
    let structural_receipt = StructuralWorldGenerator::generate(&spec);
    assert_eq!(structural_receipt.bars.len(), 100);
    assert!(structural_receipt.bars.iter().all(|b| b.is_valid()));

    // 2. Block resampling generator
    let resampled_receipt = BlockResampleGenerator::resample(
        &structural_receipt.bars,
        10,
        999,
        &spec,
    );
    assert_eq!(resampled_receipt.bars.len(), 100);
    assert!(resampled_receipt.bars.iter().all(|b| b.is_valid()));

    // 3. Counterfactual surgery generator
    let cfg = SurgeryConfig::default();
    let surgery_receipt = CounterfactualSurgeryEngine::apply_multi_axis_surgery(
        &structural_receipt.bars,
        &cfg,
        888,
        &spec,
    );
    assert_eq!(surgery_receipt.bars.len(), 100);
    assert!(surgery_receipt.bars.iter().all(|b| b.is_valid()));
}
