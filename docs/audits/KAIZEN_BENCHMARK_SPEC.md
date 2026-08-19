# V8 Kaizen Continuous Improvement & Historical Benchmark Ledger Specification (v8.kaizen.v1)

**Status:** ACTIVE_SPECIFICATION  
**Scope:** Defines the immutable benchmark ledger, audit history repository, and automated regression/progression comparator enabling autonomous Kaizen agents and developers to systematically track, compare, and optimize strategy performance over time.

---

## 1. Objective & Architecture

To achieve continuous mathematical improvement (Kaizen) without risk of silent regression or overfitting, every evaluation run is captured as a content-addressed snapshot in the **Kaizen Audit Repository** (`.audit/history/`) and indexed in the **Append-Only Benchmark Ledger** (`.audit/benchmark_ledger.jsonl`).

```
                    ┌────────────────────────────────────────────────────────┐
                    │       v8-core Engine (Pipeline / USD-M Sim)            │
                    └──────────────────────────┬─────────────────────────────┘
                                               │
                                               ▼
                              .audit/rust_audit_current/
                      (Active Live Working Directory - Ephemeral)
                                               │
                                               ▼
                         ┌───────────────────────────────────────────┐
                         │   tools/kaizen_audit.py (Snapshot Engine) │
                         └─────────────────────┬─────────────────────┘
                                               │
                      ┌────────────────────────┴────────────────────────┐
                      ▼                                                 ▼
             .audit/history/                               .audit/benchmark_ledger.jsonl
    <timestamp>_<tag_or_run_id>/                    (Immutable Machine-Readable Append Log)
    ├── portfolio_receipt.json                              │
    ├── economic-cashflow.jsonl (sample)                    │
    ├── oracle_coverage_receipt.json                        │
    ├── report.html                                         │
    └── snapshot_meta.json                                  │
                      │                                     │
                      └────────────────────────┬────────────┘
                                               ▼
                                  tools/compare_audits.py
                       (Delta Analysis & Regression Radar for Agents)
                                               │
                      ┌────────────────────────┴────────────────────────┐
                      ▼                                                 ▼
          Terminal Delta Matrix                               Autonomous Agent Findings
    (Progression / Regression / TCA)                              (v8.eval.v1 JSON)
```

---

## 2. Benchmark Ledger Schema (`.audit/benchmark_ledger.jsonl`)

Each line is a single JSON object adhering to `v8.kaizen.v1`:

```json
{
  "run_id": "20260819_103000_issue164_baseline",
  "timestamp_utc": "2026-08-19T07:30:00Z",
  "git_commit": "a1b2c3d4",
  "git_branch": "main",
  "tag": "baseline_full",
  "description": "Issue #164 Baseline full 28-expert unconstrained run",
  "tape_path": "research/tape/btcusdt-1h-12m/tape.jsonl",
  "duration_days": 365.0,
  "initial_balance_usdt": 1000.0,
  "terminal_equity_usdt": 7.01,
  "net_profit_usdt": -992.99,
  "total_return_pct": -99.30,
  "max_drawdown_pct": 99.31,
  "profit_factor": 0.746,
  "win_rate_pct": 41.50,
  "total_fee_drag_usdt": 384.54,
  "n_trades_admitted": 2460,
  "experts_summary": {
    "fib_retracement_continuation": { "trades": 15, "net_r": 3.95, "win_rate": 66.7, "pf": 1.74 },
    "liquidity_sweep_reclaim": { "trades": 6, "net_r": 0.22, "win_rate": 50.0, "pf": 1.09 }
  },
  "rejections_by_reason": {
    "CAPITAL_CONSTRAINT_REJECTION": 7433,
    "QUANTITY_ROUNDS_TO_ZERO": 32428,
    "INSUFFICIENT_AVAILABLE_BALANCE": 297
  },
  "snapshot_dir": ".audit/history/20260819_103000_issue164_baseline",
  "contract_hash": "9fb5d2136dbac7de8400e3c5127ff6254f50cf53"
}
```

---

## 3. Tooling Interfaces

1. **Snapshot Creation**:
   ```bash
   python tools/kaizen_audit.py snapshot --tag "baseline_full" --desc "Full 28-expert baseline"
   ```
2. **History Listing**:
   ```bash
   python tools/kaizen_audit.py list
   ```
3. **Run Comparison (Kaizen Delta & Regression Radar)**:
   ```bash
   python tools/compare_audits.py --base <run_id_or_index> --target <run_id_or_index>
   # Or compare latest against previous:
   python tools/compare_audits.py --latest
   ```
