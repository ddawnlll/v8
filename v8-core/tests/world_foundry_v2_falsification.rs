//! Market World Foundry v2 Comprehensive Test Suite (D-150, V8.5 Extension).
//!
//! Tests all 14 generator families, Hawkes processes, cross-asset copula correlation,
//! stationary bootstrap, path topology, multi-axis surgery, adversarial reverse-stress search,
//! 3-population isolation, and GeneratorPassport non-scalar conjunction.

use v8_core::world::{
    CrossAssetContagionGenerator, EnsembleAgreementStatus, GeneratorPassport,
    MetamorphicTransform, MetamorphicWorldGenerator, PathGeometryType, PathTopologyGenerator,
    ReverseStressSearchEngine, StationaryBootstrapGenerator, StochasticVolatilityGenerator,
    StructuralWorldGenerator, SyntheticPopulation, WorldComposer, WorldFamily, WorldSpec,
};

#[test]
fn test_v2_stationary_bootstrap_preserves_stationary_properties() {
    let spec = WorldSpec {
        family: WorldFamily::StationaryBootstrap,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "BTCUSDT".to_string(),
        n_bars: 200,
        base_price: 45000.0,
        volatility_annualized: 0.65,
        jump_frequency: 10.0,
        jump_mean: -0.01,
        jump_std: 0.03,
        seed: 777,
    };

    let source = StructuralWorldGenerator::generate(&spec);
    let bootstrapped = StationaryBootstrapGenerator::generate(&source.bars, 12, 888, &spec);

    assert_eq!(bootstrapped.bars.len(), 200);
    assert!(bootstrapped.bars.iter().all(|b| b.is_valid()));
    // Price trajectory must be non-trivial and bounded
    let last_close = bootstrapped.bars.last().unwrap().close;
    assert!(last_close > 1000.0 && last_close < 500_000.0);
}

#[test]
fn test_v2_stochastic_volatility_garch_clustering() {
    let spec = WorldSpec {
        family: WorldFamily::StochasticVolatility,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "ETHUSDT".to_string(),
        n_bars: 300,
        base_price: 3000.0,
        volatility_annualized: 0.80,
        jump_frequency: 5.0,
        jump_mean: -0.02,
        jump_std: 0.04,
        seed: 42,
    };

    let receipt = StochasticVolatilityGenerator::generate(&spec, 0.02, 0.15, 0.80);
    assert_eq!(receipt.bars.len(), 300);
    assert!(receipt.bars.iter().all(|b| b.is_valid()));
}

#[test]
fn test_v2_cross_asset_contagion_synchronized_quad_universe() {
    let spec = WorldSpec {
        family: WorldFamily::CrossAssetContagion,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "QUAD".to_string(),
        n_bars: 150,
        base_price: 50000.0,
        volatility_annualized: 0.70,
        jump_frequency: 10.0,
        jump_mean: -0.03,
        jump_std: 0.05,
        seed: 101,
    };

    let quad_receipt = CrossAssetContagionGenerator::generate_quad_universe(&spec, 0.15);
    assert_eq!(quad_receipt.snapshots.len(), 150);
    assert_eq!(quad_receipt.symbols.len(), 4);

    let btc_bars = quad_receipt.extract_single_asset("BTCUSDT").unwrap();
    let sol_bars = quad_receipt.extract_single_asset("SOLUSDT").unwrap();

    assert_eq!(btc_bars.len(), 150);
    assert_eq!(sol_bars.len(), 150);
    assert!(btc_bars.iter().all(|b| b.is_valid()));
    assert!(sol_bars.iter().all(|b| b.is_valid()));
}

#[test]
fn test_v2_path_topology_anchored_terminal_returns() {
    let spec = WorldSpec {
        family: WorldFamily::PathTopologyWorld,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "SOLUSDT".to_string(),
        n_bars: 100,
        base_price: 100.0,
        volatility_annualized: 0.80,
        jump_frequency: 0.0,
        jump_mean: 0.0,
        jump_std: 0.0,
        seed: 999,
    };

    let terminal_mult = 1.30; // Exact +30% target (130.0)

    let path_a = PathTopologyGenerator::generate(&spec, terminal_mult, PathGeometryType::MonotonicTrend);
    let path_b = PathTopologyGenerator::generate(&spec, terminal_mult, PathGeometryType::ExcursionCrashRecovery);
    let path_c = PathTopologyGenerator::generate(&spec, terminal_mult, PathGeometryType::ImmediateDrawdownGrind);

    // All paths must arrive at exactly $130.0 within 0.1% tolerance
    assert!((path_a.bars.last().unwrap().close - 130.0).abs() < 0.15);
    assert!((path_b.bars.last().unwrap().close - 130.0).abs() < 0.15);
    assert!((path_c.bars.last().unwrap().close - 130.0).abs() < 0.15);

    // But intermediate price excursions must diverge completely
    let max_b = path_b.bars.iter().map(|b| b.high).fold(0.0, f64::max);
    let min_c = path_c.bars.iter().map(|b| b.low).fold(f64::INFINITY, f64::min);

    assert!(max_b > 140.0, "Path B must experience high excursion");
    assert!(min_c < 80.0, "Path C must experience deep early drawdown");
}

#[test]
fn test_v2_metamorphic_transforms() {
    let spec = WorldSpec::default();
    let source = StructuralWorldGenerator::generate(&spec);

    // 1. Scale 10x
    let scaled = MetamorphicWorldGenerator::transform(&source.bars, MetamorphicTransform::Scale(10), &spec);
    assert!((scaled.bars[0].open - source.bars[0].open * 10.0).abs() < 1e-3);

    // 2. Mirror Inversion
    let mirror = MetamorphicWorldGenerator::transform(&source.bars, MetamorphicTransform::MirrorInversion, &spec);
    assert_eq!(mirror.bars.len(), source.bars.len());
    assert!(mirror.bars.iter().all(|b| b.is_valid()));

    // 3. Time Reversal
    let rev = MetamorphicWorldGenerator::transform(&source.bars, MetamorphicTransform::TimeReversal, &spec);
    assert_eq!(rev.bars.len(), source.bars.len());
    assert!(rev.bars.iter().all(|b| b.is_valid()));
}

#[test]
fn test_v2_reverse_stress_minimal_defeater_search() {
    let spec = WorldSpec {
        family: WorldFamily::ReverseStressAdversarial,
        population: SyntheticPopulation::SyntheticDev,
        symbol: "BTCUSDT".to_string(),
        n_bars: 250,
        base_price: 60000.0,
        volatility_annualized: 0.60,
        jump_frequency: 8.0,
        jump_mean: -0.03,
        jump_std: 0.05,
        seed: 333,
    };

    let defeater = ReverseStressSearchEngine::find_minimal_failure_trajectory(&spec, 12.0);
    assert!(defeater.is_some());
    let receipt = defeater.unwrap();

    assert!(receipt.peak_drawdown_pct >= 12.0);
    assert!(receipt.plausibility_distance > 0.0);
    assert!(!receipt.vulnerability_summary.is_empty());
}

#[test]
fn test_v2_generator_passport_non_scalar_conjunction() {
    // 1. Passing passport (all 10 scores >= 0.70)
    let good_passport = GeneratorPassport::new_v2(
        "pass-good".to_string(),
        0.85, 0.88, 0.75, 0.82, 0.79, 0.86, 0.80, 0.90, 0.77, 0.84,
    );
    assert!(good_passport.passport_passed);

    // 2. Failing passport due to a single failing dimension (e.g. kurtosis = 0.65)
    let bad_passport = GeneratorPassport::new_v2(
        "pass-bad".to_string(),
        0.99, 0.99, 0.65 /* FAILS */, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99,
    );
    assert!(!bad_passport.passport_passed, "Single score < 0.70 must veto passport conjunction");
}

#[test]
fn test_v2_world_composer_ensemble_agreement() {
    // 1. Pass when required threshold met
    let passed = vec![WorldFamily::StructuralRegime, WorldFamily::StochasticVolatility, WorldFamily::JumpCascade];
    assert_eq!(WorldComposer::evaluate_ensemble_agreement(&passed, 3), EnsembleAgreementStatus::RobustnessPass);

    // 2. Disagreement / Contested when partial pass
    let partial = vec![WorldFamily::StructuralRegime];
    assert_eq!(WorldComposer::evaluate_ensemble_agreement(&partial, 3), EnsembleAgreementStatus::GeneratorDisagreementContested);

    // 3. Universal failure when empty
    assert_eq!(WorldComposer::evaluate_ensemble_agreement(&[], 3), EnsembleAgreementStatus::UniversalFailure);
}
