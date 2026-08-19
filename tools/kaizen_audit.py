#!/usr/bin/env python3
"""Kaizen Historical Audit Snapshot & Benchmark Ledger Manager for V8 (v8.kaizen.v1).

Manages immutable historical run snapshots in `.audit/history/` and maintains
the append-only benchmark ledger in `.audit/benchmark_ledger.jsonl`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / ".audit"
CURRENT_DIR = AUDIT_DIR / "rust_audit_current"
HISTORY_DIR = AUDIT_DIR / "history"
LEDGER_FILE = AUDIT_DIR / "benchmark_ledger.jsonl"


def get_git_info() -> tuple[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True
        ).strip()
        return commit, branch
    except Exception:
        return "unknown", "unknown"


def extract_expert_metrics(audit_path: Path) -> dict[str, dict]:
    cands_file = audit_path / "candidates.jsonl"
    cube_file = audit_path / "cube-reduced.v82"

    if not cands_file.exists() or not cube_file.exists():
        return {}

    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from render_rust_audit_html import read_v82_cube
    except ImportError:
        return {}

    cand_exp = {}
    with cands_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    cid = r.get("candidate_id")
                    eid = r.get("expert_id")
                    if cid and eid:
                        cand_exp[cid] = eid
                except Exception:
                    pass

    columns = read_v82_cube(cube_file)
    cids = columns.get("candidate_id", [])
    aus = columns.get("actual_utility", [])

    stats = defaultdict(lambda: {"trades": 0, "net_r": 0.0, "wins": 0, "losses": 0, "gross_win": 0.0, "gross_loss": 0.0})

    for cid, au in zip(cids, aus):
        if au is not None:
            eid = cand_exp.get(cid, "generic")
            s = stats[eid]
            s["trades"] += 1
            s["net_r"] += au
            if au > 0:
                s["wins"] += 1
                s["gross_win"] += au
            else:
                s["losses"] += 1
                s["gross_loss"] += abs(au)

    result = {}
    for eid, s in stats.items():
        wr = (s["wins"] / s["trades"] * 100.0) if s["trades"] > 0 else 0.0
        pf = (s["gross_win"] / s["gross_loss"]) if s["gross_loss"] > 0 else 99.0
        result[eid] = {
            "trades": s["trades"],
            "net_r": round(s["net_r"], 2),
            "avg_r": round(s["net_r"] / max(s["trades"], 1), 4),
            "win_rate_pct": round(wr, 1),
            "profit_factor": round(pf, 2),
        }
    return result


def create_snapshot(tag: str, desc: str, source_dir: Path | None = None) -> dict:
    source = (source_dir or CURRENT_DIR).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source audit directory does not exist: {source}")

    now = datetime.now(timezone.utc)
    ts_str = now.strftime("%Y%m%d_%H%M%S")
    sanitized_tag = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in tag)
    run_id = f"{ts_str}_{sanitized_tag}"

    dest_dir = HISTORY_DIR / run_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    receipt_file = source / "portfolio_receipt.json"
    pr = {}
    if receipt_file.exists():
        try:
            pr = json.loads(receipt_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    expert_metrics = extract_expert_metrics(source)
    git_commit, git_branch = get_git_info()

    record = {
        "run_id": run_id,
        "timestamp_utc": now.isoformat(),
        "git_commit": git_commit,
        "git_branch": git_branch,
        "tag": tag,
        "description": desc,
        "tape_path": "research/tape/btcusdt-1h-12m/tape.jsonl",
        "duration_days": 365.0,
        "initial_balance_usdt": pr.get("initial_balance_usdt", 1000.0),
        "terminal_equity_usdt": round(pr.get("terminal_equity_usdt", 0.0), 2),
        "net_profit_usdt": round(pr.get("net_profit_usdt", 0.0), 2),
        "total_return_pct": round(pr.get("total_return_pct", 0.0), 2),
        "max_drawdown_pct": round(pr.get("max_drawdown_pct", 0.0), 2),
        "max_margin_utilization_pct": round(pr.get("max_margin_utilization_pct", 0.0), 1),
        "profit_factor": round(pr.get("profit_factor", 0.0), 3),
        "win_rate_pct": round(pr.get("win_rate_pct", 0.0), 2),
        "total_fee_drag_usdt": round(pr.get("total_fee_drag_usdt", 0.0), 2),
        "n_trades_admitted": pr.get("n_trades_admitted", 0),
        "rejections_by_reason": pr.get("rejections_by_reason", {}),
        "experts_summary": expert_metrics,
        "snapshot_dir": str(dest_dir.relative_to(ROOT)),
        "contract_hash": pr.get("venue_contract_hash", "binance_usdm_btc_v1"),
    }

    # Copy core evidence files into snapshot dir
    for fname in [
        "portfolio_receipt.json",
        "oracle_coverage_receipt.json",
        "report.html",
        "request_evaluate.json",
        "request_oracle_coverage.json",
    ]:
        fpath = source / fname
        if fpath.exists():
            shutil.copy2(fpath, dest_dir / fname)

    # Save meta json
    (dest_dir / "snapshot_meta.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )

    # Append to benchmark ledger
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def list_history() -> list[dict]:
    if not LEDGER_FILE.exists():
        print("No historical Kaizen benchmark ledger found at: .audit/benchmark_ledger.jsonl")
        return []

    records = []
    with LEDGER_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    print("==========================================================================================================================")
    print(f"| {'#':<3} | {'Run ID':<32} | {'Tag':<16} | {'Return %':<10} | {'Net PnL ($)':<12} | {'Win %':<7} | {'PF':<6} | {'MaxDD %':<8} | {'Trades':<6} |")
    print("==========================================================================================================================")
    for idx, r in enumerate(records, 1):
        ret = r.get("total_return_pct", 0.0)
        pnl = r.get("net_profit_usdt", 0.0)
        wr = r.get("win_rate_pct", 0.0)
        pf = r.get("profit_factor", 0.0)
        dd = r.get("max_drawdown_pct", 0.0)
        trades = r.get("n_trades_admitted", 0)
        tag = r.get("tag", "")[:16]
        run_id = r.get("run_id", "")[:32]
        print(f"| {idx:<3} | {run_id:<32} | {tag:<16} | {ret:>+9.2f}% | {pnl:>+11.2f}$ | {wr:>6.1f}% | {pf:>5.2f} | {dd:>7.1f}% | {trades:>6} |")
    print("==========================================================================================================================")
    print(f"Total Historical Snapshots: {len(records)}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snap_parser = subparsers.add_parser("snapshot", help="Snapshot current audit run into history")
    snap_parser.add_argument("--tag", required=True, help="Short identifier tag (e.g. baseline_issue164)")
    snap_parser.add_argument("--desc", default="", help="Detailed description of changes or config")
    snap_parser.add_argument("--source", type=Path, default=None, help="Source directory (default: .audit/rust_audit_current)")

    subparsers.add_parser("list", help="List all benchmark runs in history ledger")

    args = parser.parse_args()

    if args.command == "snapshot":
        rec = create_snapshot(args.tag, args.desc, args.source)
        print(f"✅ Created Kaizen Snapshot: {rec['run_id']}")
        print(f"   Directory: {rec['snapshot_dir']}")
        print(f"   Return: {rec['total_return_pct']:+.2f}% | Net PnL: ${rec['net_profit_usdt']:+,.2f} | WinRate: {rec['win_rate_pct']:.1f}%")
        return 0
    elif args.command == "list":
        list_history()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
