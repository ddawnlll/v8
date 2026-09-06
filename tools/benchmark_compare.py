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

    def load_receipt(path: Path) -> dict:
        content = path.read_text()
        start = content.find('{')
        if start != -1:
            return json.loads(content[start:])
        return json.loads(content)

    inc = load_receipt(inc_p)
    cha = load_receipt(cha_p)

    inc_score = inc.get("composite_capability_score", inc.get("composite_score", 0.0))
    cha_score = cha.get("composite_capability_score", cha.get("composite_score", 0.0))
    score_delta = cha_score - inc_score

    print(f"=== BENCHMARK RECEIPT COMPARISON ===")
    print(f"Incumbent:  {inc.get('policy_id')} (Score: {inc_score:.2f})")
    print(f"Challenger: {cha.get('policy_id')} (Score: {cha_score:.2f})")
    print(f"Score Delta: {score_delta:+.2f}")
    
    gate_vec = cha.get("gate_vector", {})
    if isinstance(gate_vec, dict):
        has_hard_fail = any(v in ("Blocked", "BLOCKED", "Defeated", "DEFEATED") for v in gate_vec.values())
    else:
        has_hard_fail = False
    print(f"Challenger Hard Gates: {'FAIL' if has_hard_fail else 'PASS'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
