//! Explicit real-tape acceptance: no synthetic fallback and no economic claim.
//! V8_REAL_TAPE=/absolute/path/tape.jsonl cargo test --test runnable_main -- --ignored --nocapture
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{fs, path::PathBuf, process::Command};

fn number(v: &Value, key: &str) -> f64 {
    let n = v[key]
        .as_f64()
        .unwrap_or_else(|| panic!("missing numeric {key}"));
    assert!(n.is_finite(), "nonfinite {key}");
    n
}

#[test]
#[ignore = "requires explicit real Binance BTCUSDT hourly tape and its source archives"]
fn real_tape_cli_reconciles_and_replays() {
    let tape = PathBuf::from(
        std::env::var("V8_REAL_TAPE").expect("set V8_REAL_TAPE; no fixture fallback"),
    );
    let tape = tape.canonicalize().unwrap();
    let source: Value =
        serde_json::from_slice(&fs::read(tape.with_file_name("source.json")).unwrap()).unwrap();
    assert_eq!(source["symbol"], "BTCUSDT");
    let bytes = fs::read(&tape).unwrap();
    let rows: Vec<Value> = std::str::from_utf8(&bytes)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    assert_eq!(rows.len() as u64, source["row_count"].as_u64().unwrap());
    assert!(rows
        .iter()
        .all(|r| r["source"] == "binance-um" && r["instrument"] == "BTCUSDT"));
    assert!(rows.iter().any(|r| r["channel"] == "funding"));
    for archive in source["archives"].as_array().unwrap() {
        let channel = match archive["channel"].as_str().unwrap() {
            "funding" => "fundingRate",
            "kline" => "1h",
            other => panic!("unexpected archive {other}"),
        };
        let filename = format!(
            "BTCUSDT-{channel}-{}.zip",
            archive["month"].as_str().unwrap()
        );
        let archive_bytes = fs::read(tape.with_file_name(filename)).unwrap();
        assert_eq!(
            format!("{:x}", Sha256::digest(&archive_bytes)),
            archive["zip_sha256"].as_str().unwrap()
        );
    }
    let root = std::env::var_os("V8_ACCEPTANCE_OUT")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            std::env::temp_dir().join(format!("v8-main-acceptance-{}", std::process::id()))
        });
    assert!(!root.exists(), "use a fresh output directory");
    fs::create_dir_all(&root).unwrap();
    let mut runs = Vec::new();
    for name in ["first", "repeat"] {
        let out = root.join(name);
        let result = Command::new(env!("CARGO_BIN_EXE_v8-core"))
            .args(["usdm-sim", "--tape"])
            .arg(&tape)
            .arg("--out")
            .arg(&out)
            .args([
                "--experts",
                "trend_continuation",
                "--initial-balance",
                "1000",
                "--risk-fraction",
                "0.005",
                "--max-concurrency",
                "1",
                "--max-heat",
                "0.05",
            ])
            .output()
            .unwrap();
        fs::write(root.join(format!("{name}.stdout")), &result.stdout).unwrap();
        fs::write(root.join(format!("{name}.stderr")), &result.stderr).unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let receipt_bytes = fs::read(out.join("portfolio_receipt.json")).unwrap();
        let receipt: Value = serde_json::from_slice(&receipt_bytes).unwrap();
        assert_eq!(receipt["promotion_authority"], "NONE");
        let ledger_bytes = fs::read(out.join("economic-cashflow.jsonl")).unwrap();
        let flows: Vec<Value> = std::str::from_utf8(&ledger_bytes)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .collect();
        assert!(
            !flows.is_empty(),
            "real-data acceptance must exercise execution"
        );
        assert_eq!(
            flows.len() as u64,
            receipt["n_trades_admitted"].as_u64().unwrap()
        );
        let mut net = 0.0;
        let mut funding = 0.0;
        for flow in &flows {
            let expected = number(flow, "gross_market_pnl_usdt") - number(flow, "commission_usdt")
                + number(flow, "funding_cashflow_usdt")
                - number(flow, "slippage_usdt")
                - number(flow, "gap_through_stop_usdt");
            assert!((expected - number(flow, "net_pnl_usdt")).abs() < 1e-6);
            assert!(
                (number(flow, "wallet_balance_before") + expected
                    - number(flow, "wallet_balance_after"))
                .abs()
                    < 1e-6
            );
            net += expected;
            funding += number(flow, "funding_cashflow_usdt");
        }
        assert!(
            flows
                .iter()
                .any(|f| number(f, "funding_cashflow_usdt") != 0.0),
            "settlement events must not be skipped by delayed decision clocks"
        );
        assert!((funding - number(&receipt, "total_funding_usdt")).abs() < 1e-6);
        assert!(
            (number(&receipt, "initial_balance_usdt") + net
                - number(&receipt, "terminal_equity_usdt"))
            .abs()
                < 1e-6
        );
        assert!((net - number(&receipt, "net_profit_usdt")).abs() < 1e-6);
        runs.push((receipt_bytes, ledger_bytes));
    }
    assert_eq!(
        runs[0], runs[1],
        "identical input/configuration must replay identically"
    );
    let summary = serde_json::json!({
        "status": "RUNNABLE_DIAGNOSTIC_ONLY", "economic_claim": "NO_ECONOMIC_CLAIM",
        "binary_sha256": format!("{:x}", Sha256::digest(fs::read(env!("CARGO_BIN_EXE_v8-core")).unwrap())),
        "tape_path": tape, "tape_sha256": format!("{:x}", Sha256::digest(&bytes)),
        "rows": rows.len(), "source_archives_verified": source["archives"].as_array().unwrap().len(),
        "receipt_sha256": format!("{:x}", Sha256::digest(&runs[0].0)),
        "ledger_sha256": format!("{:x}", Sha256::digest(&runs[0].1)),
        "limitations": "Historical bar simulation; funding notional uses observed bar open, not venue mark. No live-execution or profitability certification."
    });
    fs::write(
        root.join("verification.json"),
        serde_json::to_vec_pretty(&summary).unwrap(),
    )
    .unwrap();
    println!("Verified artifacts: {}", root.display());
}
