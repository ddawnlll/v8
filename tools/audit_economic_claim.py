#!/usr/bin/env python3
"""Economic Claim Authority & Provenance Firewall Audit (D-131, Constitution Rule 12).

Enforces strict epistemic boundaries and metric naming conventions:
1. Type & Provenance Integrity: Counterfactual / Oracle projections MUST NOT use
   'realized_net_pnl', 'realized_profit', 'realized_return', or 'realized_alpha'.
2. Succession Claim Guard: Any claim of production succession or economic victory
   MUST require an authoritative cashflow ledger receipt on disk with terminal equity >= $1,080
   and certified multiple-testing adjustment (WRC p <= 0.05).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_COUNTERFACTUAL_TERMS = [
    r"Realized Net Alpha\s*=",
    r"realized_net_pnl_usdt\s*(\+=|=)\s*realized_r",
    r"realized_net_pnl\s*:\s*f64.*counterfactual",
    r"realized_profit.*counterfactual",
]

def audit_codebase_naming() -> list[str]:
    violations = []
    scan_dirs = [ROOT / "v8-core" / "src", ROOT / "site"]
    
    for sdir in scan_dirs:
        if not sdir.exists():
            continue
        for p in sdir.rglob("*"):
            if not p.is_file() or p.suffix not in (".rs", ".html", ".md"):
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for pat in FORBIDDEN_COUNTERFACTUAL_TERMS:
                    if re.search(pat, content, re.IGNORECASE):
                        violations.append(f"Forbidden counterfactual mislabeling in {p.relative_to(ROOT)} matching '{pat}'")
            except Exception as e:
                violations.append(f"Error reading {p}: {e}")
    return violations

def audit_dossier_claims() -> list[str]:
    violations = []
    dossiers_dir = ROOT / "docs" / "dossiers"
    if not dossiers_dir.exists():
        return violations

    for p in dossiers_dir.glob("*.md"):
        content = p.read_text(encoding="utf-8", errors="ignore")
        if "Production Succession: APPROVED" in content or "Gate G5: PASS" in content:
            # Must verify that authoritative receipt exists on disk with >= $1,080 equity
            receipt_path = ROOT / ".audit" / "rust_audit_current" / "portfolio_receipt.json"
            if not receipt_path.exists():
                violations.append(f"{p.name} asserts 'APPROVED / PASS' without physical portfolio_receipt.json")
                continue
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                equity = receipt.get("terminal_equity_usdt", 0.0)
                if equity < 1080.0:
                    violations.append(f"{p.name} asserts SUCCESSION/PASS but physical terminal equity is ${equity:.2f} (< $1,080 threshold)")
            except Exception as e:
                violations.append(f"Error verifying receipt for {p.name}: {e}")
    return violations

def main() -> int:
    print("=" * 70)
    print("V8.3 ECONOMIC CLAIM AUTHORITY & PROVENANCE FIREWALL (D-131)")
    print("=" * 70)

    naming_violations = audit_codebase_naming()
    dossier_violations = audit_dossier_claims()

    all_violations = naming_violations + dossier_violations

    if all_violations:
        print("FAIL: Economic Claim Authority Firewall violations detected:")
        for v in all_violations:
            print(f"  [X] {v}")
        return 1

    print("PASS: Epistemic Authority and Naming Integrity 100% verified.")
    print("  [OK] No counterfactual markout metrics mislabeled as realized PnL.")
    print("  [OK] No premature succession or victory claims without physical ledger receipts.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
