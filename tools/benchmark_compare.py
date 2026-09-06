#!/usr/bin/env python3
"""D-153 Benchmark Comparison Tool.

Compares benchmark receipts between Challenger and Incumbent policies.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two Benchmark Fabric receipts")
    parser.add_argument("incumbent", help="Path to incumbent BenchmarkReceipt JSON")
    parser.add_argument("challenger", help="Path to challenger BenchmarkReceipt JSON")
    args = parser.parse_args()

    inc_p = Path(args.incumbent)
    cha_p = Path(args.challenger)

    if not inc_p.exists() or not cha_p.exists():
        print("Error: receipt file not found", file=sys.stderr)
        return 1

    with open(inc_p) as f:
        inc = json.load(f)
    with open(cha_p) as f:
        cha = json.load(f)

    score_delta = cha.get("composite_score", 0.0) - inc.get("composite_score", 0.0)
    print(f"=== BENCHMARK RECEIPT COMPARISON ===")
    print(f"Incumbent:  {inc.get('policy_id')} (Score: {inc.get('composite_score', 0.0):.2f})")
    print(f"Challenger: {cha.get('policy_id')} (Score: {cha.get('composite_score', 0.0):.2f})")
    print(f"Score Delta: {score_delta:+.2f}")
    
    gates_ok = cha.get("gate_vector", {}).get("all_pass", False) if isinstance(cha.get("gate_vector"), dict) else True
    print(f"Challenger Hard Gates: {'PASS' if gates_ok else 'FAIL'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
