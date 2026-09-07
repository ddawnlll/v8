//! Comprehensive V8.6 Migration Verification Suite (M04-M12).
//!
//! Tests:
//! 1. CLI argument parsing with `clap` (M09).
//! 2. Work scheduling and deterministic chunk aggregation via `rayon` (M10).
//! 3. Production RNG streams with `rand` StdRng / Box-Muller (M11).
//! 4. HTML report template compilation and rendering via `minijinja` (M12).
//! 5. Execution boundary lifecycle contracts and cashflow reconciliation (M04, M08).

use clap::Parser;
use v8_core::cli::{Cli, Commands};
use v8_core::execution_boundary::*;
use v8_core::report_template::ReportRenderer;
use v8_core::rnd::ProductionRng;
use v8_core::scheduler::parallel_map;

#[test]
fn test_m09_clap_cli_parsing() {
    let args = vec!["v8-core", "registry"];
    let cli = Cli::try_parse_from(args).expect("should parse registry command");
    match cli.command {
        Commands::Registry => {}
        _ => panic!("unexpected command parsed"),
    }

    let args_ingest = vec!["v8-core", "ingest", "test_req.json"];
    let cli_ingest = Cli::try_parse_from(args_ingest).expect("should parse ingest command");
    match cli_ingest.command {
        Commands::Ingest(req) => {
            assert_eq!(req.request_path.to_str().unwrap(), "test_req.json");
        }
        _ => panic!("unexpected command parsed"),
    }
}

#[test]
fn test_m10_rayon_scheduler_determinism() {
    let n = 1000;
    let threads = 4;
    let results = parallel_map(threads, n, &|i| Ok(i * 2)).expect("parallel_map should succeed");
    assert_eq!(results.len(), n);
    for (i, res) in results.into_iter().enumerate() {
        assert_eq!(res.unwrap(), i * 2);
    }
}

#[test]
fn test_m11_production_rng_determinism() {
    let seed = 424242u64;
    let mut rng1 = ProductionRng::from_seed(seed);
    let mut rng2 = ProductionRng::from_seed(seed);

    let draws1: Vec<f64> = (0..100).map(|_| rng1.gen_f64()).collect();
    let draws2: Vec<f64> = (0..100).map(|_| rng2.gen_f64()).collect();
    assert_eq!(draws1, draws2);

    let norm1: Vec<f64> = (0..100).map(|_| rng1.gen_standard_normal()).collect();
    let norm2: Vec<f64> = (0..100).map(|_| rng2.gen_standard_normal()).collect();
    assert_eq!(norm1, norm2);
}

#[test]
fn test_m12_minijinja_report_template() {
    let renderer = ReportRenderer::new().expect("template should initialize");
    let ctx = serde_json::json!({
        "title": "V8.6 Diagnostic Report",
        "subtitle": "Test run",
        "status_badge": "PASS",
        "runtime": "v8-core",
        "architecture": "Rust + Rayon + Clap",
        "verification": "Deterministic",
        "authority": "PROVISIONAL",
        "css": "body { margin: 0; }",
        "pipeline_steps": [
            { "name": "S0 Ingest", "detail": "1000 bars" },
            { "name": "S4 Evaluate", "detail": "28 experts" }
        ]
    });
    let rendered = renderer.render_audit_report(ctx).expect("rendering should succeed");
    assert!(rendered.contains("V8.6 Diagnostic Report"));
    assert!(rendered.contains("S0 Ingest"));
}

#[test]
fn test_m04_m08_cashflow_reconciliation_exact_conservation() {
    let mut reconciler = CashflowReconciler::new(10_000.0);

    reconciler.record_cashflow(&CashflowEvent {
        cashflow_id: "cf-1".to_string(),
        reference_id: "trade-1".to_string(),
        event_time_ns: 1_000_000,
        cashflow_type: CashflowType::RealizedPnL,
        amount: 250.0,
        currency: "USDT".to_string(),
    });

    reconciler.record_cashflow(&CashflowEvent {
        cashflow_id: "cf-2".to_string(),
        reference_id: "trade-1".to_string(),
        event_time_ns: 1_000_000,
        cashflow_type: CashflowType::TradingFee,
        amount: 10.0,
        currency: "USDT".to_string(),
    });

    reconciler.record_cashflow(&CashflowEvent {
        cashflow_id: "cf-3".to_string(),
        reference_id: "funding-1".to_string(),
        event_time_ns: 2_000_000,
        cashflow_type: CashflowType::FundingFee,
        amount: -2.5,
        currency: "USDT".to_string(),
    });

    // Expected equity = 10000 + 250 - 10 + (-2.5) + 50 (unrealized) = 10287.5
    assert!(reconciler.reconcile_equity(10287.5, 50.0).is_ok());
    assert!(reconciler.reconcile_equity(10280.0, 50.0).is_err());
}
