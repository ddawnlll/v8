#!/usr/bin/env python3
"""D-153 Benchmark Fabric Runner Tool.

Orchestrates execution of the canonical V8.5 Benchmark Fabric via v8-core CLI.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main() -> int:
    parser = argparse.ArgumentParser(description="V8.5 Benchmark Fabric Tool Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Run benchmark fabric constitutional audit")
    eval_parser = subparsers.add_parser("eval", help="Evaluate a policy through the benchmark fabric")
    eval_parser.add_argument("policy_id", help="Target policy identifier")
    eval_parser.add_argument("--out", help="Optional output receipt file path")

    ledger_parser = subparsers.add_parser("ledger", help="Verify benchmark ledger integrity")
    ledger_parser.add_argument("ledger_path", help="Path to benchmark ledger JSONL")

    args = parser.parse_args()

    cmd = ["cargo", "run", "--manifest-path", "v8-core/Cargo.toml", "--bin", "v8-core", "--", "benchmark"]
    if args.command == "audit":
        cmd.append("audit")
    elif args.command == "eval":
        cmd.extend(["eval", args.policy_id])
        if args.out:
            cmd.append(args.out)
    elif args.command == "ledger":
        cmd.extend(["ledger", args.ledger_path])

    res = subprocess.run(cmd, cwd=ROOT)
    return res.returncode

if __name__ == "__main__":
    sys.exit(main())
