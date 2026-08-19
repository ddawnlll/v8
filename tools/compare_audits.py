#!/usr/bin/env python3
"""Kaizen Automated Audit & Benchmark Comparator for V8 (v8.kaizen.v1).

Performs rigorous delta comparisons across historical snapshots or live runs,
detecting performance progressions, statistical regressions, and fee drag shifts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / ".audit"
LEDGER_FILE = AUDIT_DIR / "benchmark_ledger.jsonl"


def load_ledger() -> list[dict]:
    if not LEDGER_FILE.exists():
        return []
    records = []
    with LEDGER_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def load_record_by_ref(ref: str, records: list[dict]) -> dict:
    # 1. Try numeric index (1-based)
    if ref.isdigit():
        idx = int(ref) - 1
        if 0 <= idx < len(records):
            return records[idx]
        raise ValueError(f"Run index {ref} out of bounds (1..{len(records)})")

    # 2. Try match by run_id or tag
    for r in records:
        if r.get("run_id") == ref or r.get("tag") == ref:
            return r

    # 3. Try match as a snapshot directory / json file path
    p = Path(ref)
    if p.is_dir() and (p / "snapshot_meta.json").exists():
        return json.loads((p / "snapshot_meta.json").read_text(encoding="utf-8"))
    if p.is_file() and p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))

    raise ValueError(f"Could not resolve audit reference: '{ref}'")


def format_delta(base: float, target: float, unit: str = "", is_pct: bool = False, reverse_better: bool = False) -> str:
    diff = target - base
    if is_pct:
        text = f"{base:.1f}% -> {target:.1f}% ({diff:+.1f}%)"
    else:
        text = f"{base:,.2f}{unit} -> {target:,.2f}{unit} ({diff:+,.2f}{unit})"

    is_good = (diff < 0) if reverse_better else (diff > 0)
    is_neutral = abs(diff) < 1e-6

    if is_neutral:
        return f"{text} ⚖️"
    elif is_good:
        return f"{text} 🟢"
    else:
        return f"{text} 🔴"


def compare_runs(base: dict, target: dict, output_json: bool = False) -> dict:
    delta_profit = target.get("net_profit_usdt", 0.0) - base.get("net_profit_usdt", 0.0)
    delta_return = target.get("total_return_pct", 0.0) - base.get("total_return_pct", 0.0)
    delta_wr = target.get("win_rate_pct", 0.0) - base.get("win_rate_pct", 0.0)
    delta_pf = target.get("profit_factor", 0.0) - base.get("profit_factor", 0.0)
    delta_dd = target.get("max_drawdown_pct", 0.0) - base.get("max_drawdown_pct", 0.0)
    delta_trades = target.get("n_trades_admitted", 0) - base.get("n_trades_admitted", 0)
    delta_fees = target.get("total_fee_drag_usdt", 0.0) - base.get("total_fee_drag_usdt", 0.0)

    base_exp = base.get("experts_summary", {})
    targ_exp = target.get("experts_summary", {})
    all_eids = sorted(set(base_exp.keys()) | set(targ_exp.keys()))

    expert_diffs = []
    for eid in all_eids:
        b_info = base_exp.get(eid, {"trades": 0, "net_r": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0})
        t_info = targ_exp.get(eid, {"trades": 0, "net_r": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0})
        b_r = b_info.get("net_r", 0.0)
        t_r = t_info.get("net_r", 0.0)
        d_r = t_r - b_r
        
        status = "NEUTRAL"
        if d_r > 0.05:
            status = "IMPROVED"
        elif d_r < -0.05:
            status = "REGRESSED"

        expert_diffs.append({
            "expert_id": eid,
            "base_trades": b_info.get("trades", 0),
            "target_trades": t_info.get("trades", 0),
            "base_net_r": b_r,
            "target_net_r": t_r,
            "delta_net_r": round(d_r, 2),
            "status": status,
        })

    expert_diffs.sort(key=lambda x: x["delta_net_r"], reverse=True)

    summary = {
        "base_run_id": base.get("run_id"),
        "target_run_id": target.get("run_id"),
        "base_tag": base.get("tag"),
        "target_tag": target.get("tag"),
        "delta_profit_usdt": round(delta_profit, 2),
        "delta_return_pct": round(delta_return, 2),
        "delta_win_rate_pct": round(delta_wr, 2),
        "delta_profit_factor": round(delta_pf, 3),
        "delta_max_drawdown_pct": round(delta_dd, 2),
        "delta_fee_drag_usdt": round(delta_fees, 2),
        "delta_trades": delta_trades,
        "expert_diffs": expert_diffs,
    }

    if output_json:
        print(json.dumps(summary, indent=2))
        return summary

    print("\n" + "=" * 90)
    print(" 🚀 V8 KAIZEN AUDIT COMPARISON & PROGRESSION RADAR (v8.kaizen.v1)")
    print("=" * 90)
    print(f" BASELINE : [{base.get('tag')}] {base.get('run_id')} ({base.get('git_commit', 'unknown')})")
    print(f" TARGET   : [{target.get('tag')}] {target.get('run_id')} ({target.get('git_commit', 'unknown')})")
    print("-" * 90)
    print(f" • Net Profit ($)      : {format_delta(base.get('net_profit_usdt', 0.0), target.get('net_profit_usdt', 0.0), unit='$')}")
    print(f" • Total Return (%)    : {format_delta(base.get('total_return_pct', 0.0), target.get('total_return_pct', 0.0), is_pct=True)}")
    print(f" • Win Rate (%)        : {format_delta(base.get('win_rate_pct', 0.0), target.get('win_rate_pct', 0.0), is_pct=True)}")
    print(f" • Profit Factor       : {format_delta(base.get('profit_factor', 0.0), target.get('profit_factor', 0.0))}")
    print(f" • Max Drawdown (%)    : {format_delta(base.get('max_drawdown_pct', 0.0), target.get('max_drawdown_pct', 0.0), is_pct=True, reverse_better=True)}")
    print(f" • Fee Drag ($)        : {format_delta(base.get('total_fee_drag_usdt', 0.0), target.get('total_fee_drag_usdt', 0.0), unit='$', reverse_better=True)}")
    print(f" • Admitted Trades     : {base.get('n_trades_admitted', 0)} -> {target.get('n_trades_admitted', 0)} ({delta_trades:+d})")
    print("-" * 90)
    print(" 📊 PER-EXPERT PROGRESSION / REGRESSION BREAKDOWN:")
    print("------------------------------------------------------------------------------------------")
    print(f" | {'Expert Family':<28} | {'Base Net R':<11} | {'Target Net R':<12} | {'Delta Lift':<11} | {'Status':<14} |")
    print("------------------------------------------------------------------------------------------")
    for ed in expert_diffs:
        status_icon = "🚀 IMPROVED" if ed["status"] == "IMPROVED" else "⚠️ REGRESSED" if ed["status"] == "REGRESSED" else "⚖️ NEUTRAL"
        print(f" | {ed['expert_id']:<28} | {ed['base_net_r']:>+10.2f}R | {ed['target_net_r']:>+11.2f}R | {ed['delta_net_r']:>+10.2f}R | {status_icon:<14} |")
    print("------------------------------------------------------------------------------------------")
    
    improved_count = sum(1 for e in expert_diffs if e["status"] == "IMPROVED")
    regressed_count = sum(1 for e in expert_diffs if e["status"] == "REGRESSED")
    print(f" Kaizen Verdict: {improved_count} Improved 🟢 | {regressed_count} Regressed 🔴 | {len(expert_diffs) - improved_count - regressed_count} Neutral ⚖️\n")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", "-b", help="Base run reference (index, run_id, or tag)")
    parser.add_argument("--target", "-t", help="Target run reference (index, run_id, or tag)")
    parser.add_argument("--latest", "-l", action="store_true", help="Compare latest run vs previous run in ledger")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format for agents")

    args = parser.parse_args()
    records = load_ledger()

    if not records:
        print("Error: No runs found in .audit/benchmark_ledger.jsonl. Run 'python tools/kaizen_audit.py snapshot' first.")
        return 1

    if args.latest:
        if len(records) < 2:
            print("Error: Need at least 2 recorded runs to compare with --latest.")
            return 1
        base = records[-2]
        target = records[-1]
    else:
        if not args.base or not args.target:
            print("Error: Specify both --base and --target, or use --latest.")
            return 2
        try:
            base = load_record_by_ref(args.base, records)
            target = load_record_by_ref(args.target, records)
        except ValueError as e:
            print(f"Error: {e}")
            return 1

    compare_runs(base, target, output_json=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
