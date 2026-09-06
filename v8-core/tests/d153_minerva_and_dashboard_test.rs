//! Dedicated Integration Tests for D-153 MinervaScore, Monte Carlo Futures, and Evidence Dashboard.

use v8_core::benchmark::case::{BenchmarkCase, BenchmarkVersion, PolicyTarget};
use v8_core::benchmark::certificate::PolicyCertificate;
use v8_core::benchmark::minerva::{MinervaEvaluator, PrudexCompass};
use v8_core::benchmark::projection::CapitalOutcomeProjection;
use v8_core::benchmark::report::BenchmarkReportGenerator;
use v8_core::benchmark::runner::BenchmarkRunner;
use v8_core::benchmark::types::{CapabilityDomain, EvaluationPopulation, GateState};

#[test]
fn test_minerva_hard_gating_and_seal_denial() {
    // 1. All pass scenario: DSR >= 0.95, PBO < 0.50, SPA <= 0.05, MinTRL satisfied, Regime >= floor
    let pass_res = MinervaEvaluator::evaluate(
        0.98,
        0.20,
        0.02,
        365.0,
        180.0,
        100.0,
        -1000.0,
        Some(PrudexCompass {
            profitability: 0.85,
            risk: 0.80,
            universality: 0.75,
            diversity: 0.70,
            reliability: 0.80,
            explainability: 0.90,
        }),
    );
    assert!(pass_res.gate_vector.all_passed());
    assert!(pass_res.raw_score >= 80.0);
    assert!(pass_res.seal_granted);
    assert!(pass_res.effective_score >= 80.0);

    // 2. Single gate failure (e.g. SPA p=0.15 > 0.05)
    let fail_spa = MinervaEvaluator::evaluate(
        0.99,
        0.10,
        0.15, // FAIL SPA
        365.0,
        180.0,
        100.0,
        -1000.0,
        None,
    );
    assert_eq!(fail_spa.gate_vector.spa_gate, GateState::Blocked);
    assert!(!fail_spa.gate_vector.all_passed());
    assert!(!fail_spa.seal_granted);
    assert!(fail_spa.effective_score < 80.0, "Gate failure must hard-cap effective score below 80");

    // 3. PBO failure (PBO = 0.60 >= 0.50)
    let fail_pbo = MinervaEvaluator::evaluate(
        0.99,
        0.60, // FAIL PBO
        0.01,
        365.0,
        180.0,
        100.0,
        -1000.0,
        None,
    );
    assert_eq!(fail_pbo.gate_vector.pbo_gate, GateState::Blocked);
    assert!(!fail_pbo.seal_granted);
    assert!(fail_pbo.effective_score < 80.0);

    // 4. MinTRL failure (track length 100 days < 180 min_trl)
    let fail_trl = MinervaEvaluator::evaluate(
        0.99,
        0.20,
        0.01,
        100.0, // FAIL MinTRL
        180.0,
        100.0,
        -1000.0,
        None,
    );
    assert_eq!(fail_trl.gate_vector.min_trl_gate, GateState::Blocked);
    assert!(!fail_trl.seal_granted);
    assert!(fail_trl.effective_score < 80.0);
}

#[test]
fn test_monte_carlo_futures_simulation() {
    let returns = vec![
        -50.0, 80.0, 120.0, -30.0, 70.0, 110.0, -40.0, 90.0, 45.0, 140.0,
        -60.0, 75.0, 130.0, -20.0, 85.0, 105.0, -25.0, 95.0, 50.0, 150.0,
        -45.0, 65.0, 115.0, -35.0, 75.0, 125.0, -15.0, 85.0, 55.0, 135.0,
    ];

    let mc = CapitalOutcomeProjection::simulate_monte_carlo_futures(
        &returns,
        1000.0,
        10_000,
        252,
        42,
    );

    assert_eq!(mc.n_simulations, 10_000);
    assert_eq!(mc.horizon_trades, 252);
    assert_eq!(mc.initial_capital_usd, 1000.0);

    // Percentiles should be monotonic: P5 <= P25 <= P50 <= P75 <= P95
    assert!(mc.p5_terminal_usd <= mc.p25_terminal_usd);
    assert!(mc.p25_terminal_usd <= mc.p50_terminal_usd);
    assert!(mc.p50_terminal_usd <= mc.p75_terminal_usd);
    assert!(mc.p75_terminal_usd <= mc.p95_terminal_usd);

    // Risk of ruin must be a valid probability percentage [0.0, 100.0]
    assert!(mc.risk_of_ruin_pct >= 0.0 && mc.risk_of_ruin_pct <= 100.0);
    assert!(mc.conditional_notice.contains("Conditional historical projection"));
}

#[test]
fn test_policy_certificate_and_dashboard_e2e() {
    let target = PolicyTarget {
        policy_id: "test_policy_minerva".into(),
        commit_hash: "commit_abc".into(),
        binary_digest: "digest_123".into(),
        family: "cand".into(),
    };
    let case = BenchmarkCase::new(
        "case_minerva_test".into(),
        BenchmarkVersion::new_v8_5(),
        target,
        CapabilityDomain::ALL.to_vec(),
        vec![EvaluationPopulation::BurnedDiagnosticReal],
        60,
    );

    let runner = BenchmarkRunner::default();
    let receipt = runner.run_benchmark(&case).unwrap();

    let returns = vec![
        -45.0, 80.0, 120.0, -20.0, 65.0, 110.0, -35.0, 95.0, 40.0, 150.0,
        -60.0, 75.0, 130.0, -15.0, 85.0, 105.0, -25.0, 90.0, 55.0, 140.0,
        -50.0, 70.0, 125.0, -30.0, 80.0, 115.0, -40.0, 100.0, 60.0, 160.0,
    ];

    let proj = CapitalOutcomeProjection::project_from_returns(
        &receipt,
        &returns,
        1000.0,
        false,
    ).unwrap();

    let cert = PolicyCertificate::generate(&receipt, Some(&proj));

    // Multiplicative readiness index must be calculated correctly
    let expected_readiness = (cert.research_capability_score / 100.0)
        * cert.evidence_multiplier
        * (cert.minerva_robustness_score / 100.0)
        * (cert.economic_score / 100.0)
        * 100.0;
    assert!((cert.readiness_index - (expected_readiness * 10.0).round() / 10.0).abs() < 0.2);

    // Render ASCII box and verify contents
    let ascii = cert.render_ascii();
    assert!(ascii.contains("V8 EVIDENCE DASHBOARD & POLICY CERTIFICATE"));
    assert!(ascii.contains("1. RESEARCH CAPABILITY SCORE"));
    assert!(ascii.contains("2. ECONOMIC EVIDENCE & MINERVA ROBUSTNESS"));
    assert!(ascii.contains("3. RISK-ADJUSTED CAPITAL PROJECTION"));
    assert!(ascii.contains("READINESS INDEX"));

    // Render HTML and verify all 3 panels
    let html = BenchmarkReportGenerator::render_html(&receipt, Some(&proj));
    assert!(html.contains("Panel 1: Research Capability & Domain Decomposition"));
    assert!(html.contains("Panel 2: Economic Evidence Profile & Minerva Robustness"));
    assert!(html.contains("Panel 3: Risk-Adjusted Capital Projection"));
    assert!(html.contains("READINESS INDEX"));
}
