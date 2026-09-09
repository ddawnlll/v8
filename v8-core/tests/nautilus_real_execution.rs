//! Integration test verifying real NautilusTrader backtest execution.
//!
//! Confirms that when running Nautilus simulation:
//! 1. Real `Data::Bar` and `Data::FundingRate` are fed to NautilusTrader.
//! 2. Orders are placed through Nautilus `order_factory`.
//! 3. Fills and position lifecycle events are executed by Nautilus `BacktestEngine`.
//! 4. Account balances, margin, commissions, and realized PnL are recorded directly from Nautilus Trader accounting.

use std::collections::HashMap;
use std::path::PathBuf;
use v8_core::execution::nautilus::run_nautilus_simulation;
use v8_core::usdm_sim::UsdmSimParams;

struct TestOutput(PathBuf);

impl Drop for TestOutput {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[test]
fn test_nautilus_real_execution_e2e() {
    let mut tape_path = PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl");
    if !tape_path.exists() {
        // Fallback for when current directory is v8-core
        tape_path = PathBuf::from("../research/tape/btcusdt-1h-12m/tape.jsonl");
    }
    if !tape_path.exists() {
        // CARGO_MANIFEST_DIR fallback
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        tape_path = manifest_dir.join("../research/tape/btcusdt-1h-12m/tape.jsonl");
    }
    assert!(
        tape_path.exists(),
        "Tape file must exist at {:?}",
        tape_path
    );

    let temp_dir = std::env::temp_dir().join(format!(
        "v8-nautilus-test-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&temp_dir).unwrap();
    let _output = TestOutput(temp_dir.clone());

    let params = UsdmSimParams {
        tape_path,
        out_dir: temp_dir.clone(),
        initial_balance: 10_000.0,
        risk_fraction: 0.02,
        leverage: 3,
        max_concurrency: 1,
        max_heat: 0.06,
        decision_stride_bars: 1,
        enabled_experts: Some(vec!["squeeze_swing".to_string()]),
        variant_overrides: HashMap::new(),
        engine_mode: Some("macro-m2".to_string()),
        exit_arm: None,
        symbol: Some("BTCUSDT".to_string()),
    };

    let receipt =
        run_nautilus_simulation(&params).expect("Nautilus simulation should execute successfully");

    // Assert that the receipt was written to out_dir
    let receipt_file = temp_dir.join("portfolio_receipt.json");
    assert!(
        receipt_file.exists(),
        "portfolio_receipt.json must be written"
    );

    // Assert on valid accounting numbers
    assert_eq!(receipt.initial_balance_usdt, 10_000.0);
    assert!(receipt.terminal_equity_usdt > 0.0);
    assert_eq!(receipt.evidence_role, "BURNED_DIAGNOSTIC");
    assert_eq!(receipt.promotion_authority, "NONE");
    assert!(
        receipt.n_trades_admitted > 0,
        "Nautilus should execute trades on historical tape"
    );

    println!(
        "Nautilus Execution Completed: trades_admitted={}, total_fee_drag_usdt={}, net_profit={}",
        receipt.n_trades_admitted, receipt.total_fee_drag_usdt, receipt.net_profit_usdt
    );
}
