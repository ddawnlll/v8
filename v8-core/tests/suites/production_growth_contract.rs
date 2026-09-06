//! Constitutional Sabotage Suite — Part 2: AF-T10, AF-T11, AF-T17 (D-147, D-149, Rule 44).

use v8_core::evaluation::production_growth::{ProductionGrowthContract, ProductionGrowthError};
use v8_core::evaluation::scope::ScopeDiagnostics;
use v8_core::evaluation::friction::FrictionRetentionProfile;
use v8_core::claims::StatutoryClaimClass;
use v8_core::authority::{Authority, EvidenceAuthority, DecisionAuthority, RealizationStatus};

#[test]
fn test_af_t10_broad_universe_single_asset_allocation_is_legal() {
    let symbols = vec![
        "BTCUSDT".to_string(),
        "ETHUSDT".to_string(),
        "SOLUSDT".to_string(),
        "BNBUSDT".to_string(),
    ];

    let mut diagnostics = ScopeDiagnostics::new("universe-quad-v1".to_string(), symbols);

    // Only BTCUSDT had valid edge; ETH, SOL, BNB had 0 allocations
    diagnostics.record_allocation("BTCUSDT", 42, 500.0);
    diagnostics.record_allocation("ETHUSDT", 0, 0.0);
    diagnostics.record_allocation("SOLUSDT", 0, 0.0);
    diagnostics.record_allocation("BNBUSDT", 0, 0.0);

    // Invariant: Concentrating in the only symbol with genuine edge is completely legal
    assert!(diagnostics.is_legal_scope_state());
    assert_eq!(diagnostics.symbol_allocated_capital.get("BTCUSDT"), Some(&500.0));
    assert_eq!(diagnostics.symbol_allocated_capital.get("ETHUSDT"), Some(&0.0));
}

#[test]
fn test_af_t11_weekly_shortfall_cannot_alter_decision_thresholds() {
    let contract = ProductionGrowthContract::default();

    let base_threshold = 1.5; // Requires 1.5R expected edge to enter trade

    // 1. Unaltered threshold passes anti-target-chasing check
    assert!(contract.verify_anti_target_chasing(base_threshold, 0.0, 1.5).is_ok());

    // 2. An illegal threshold lowering (e.g. lowering threshold to 0.8R to force trades during shortfall)
    // must trigger TargetChasingDetected error
    let tampered_threshold = 0.8;
    let shortfall_pct = 50.0; // 50% below weekly target
    let res = contract.verify_anti_target_chasing(base_threshold, shortfall_pct, tampered_threshold);

    assert!(matches!(
        res,
        Err(ProductionGrowthError::TargetChasingDetected(
            "DECISION_THRESHOLD_MUTATED_DUE_TO_CALENDAR_TARGET_SHORTFALL"
        ))
    ));
}

#[test]
fn test_af_t17_realized_cashflow_requires_physical_fills() {
    // 1. Hypothetical simulated authority cannot validate RealizedCashflow claim
    let simulated_auth = Authority::new(
        EvidenceAuthority::ModelDerived,
        DecisionAuthority::ExecutionAuthorized,
        RealizationStatus::Simulated,
    );

    let claim = StatutoryClaimClass::RealizedCashflow;
    let res = claim.validate_authority(&simulated_auth);
    assert!(res.is_err());
    assert_eq!(res.unwrap_err(), "REALIZED_CASHFLOW_REQUIRES_FULL_OBSERVED_SETTLEMENT");

    // 2. Only physical cashflow settled authority can validate RealizedCashflow
    let physical_settled_auth = Authority::new(
        EvidenceAuthority::Observed,
        DecisionAuthority::ExecutionAuthorized,
        RealizationStatus::CashflowSettled,
    );

    assert!(claim.validate_authority(&physical_settled_auth).is_ok());
}

#[test]
fn test_lgng_calculation_and_drawdown_bounds() {
    let contract = ProductionGrowthContract {
        max_allowed_drawdown_pct: 10.0,
        ..Default::default()
    };

    // 1. Monotonically increasing equity curve produces positive LGNG
    let winning_curve = vec![1000.0, 1020.0, 1050.0, 1100.0, 1150.0];
    let lgng = contract.compute_lgng(&winning_curve).expect("LGNG calculation failed");
    assert!(lgng > 0.0);

    // 2. Drawdown breaching contract limit (e.g. 1000 -> 800 is 20% DD > 10% max)
    let bad_dd_curve = vec![1000.0, 1050.0, 800.0, 850.0];
    let err = contract.compute_lgng(&bad_dd_curve).unwrap_err();
    assert!(matches!(err, ProductionGrowthError::MaxDrawdownExceeded { .. }));
}

#[test]
fn test_friction_retention_profile() {
    // Gross PnL: $100, Fees: $20, Funding: $5, Slippage: $5 -> Net: $70, Retention: 70%
    let profile = FrictionRetentionProfile::compute(100.0, 20.0, 5.0, 5.0);
    assert_eq!(profile.net_pnl, 70.0);
    assert!((profile.friction_retention_ratio - 0.70).abs() < 1e-6);
}
