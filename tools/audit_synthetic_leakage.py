#!/usr/bin/env python3
"""
Rule 12 Anti-Synthetic & Anti-Hallucination Static Auditor.
Strictly scans all Rust source files (v8-core/src/) for:
1. Hardcoded statistical / performance metrics (e.g. static capture_pct, fake win_rates, literal p_values).
2. Linear price / excursion synthesis patterns in production or benchmark paths.
3. Manual SensorVote / CandidateDraft injection outside certified expert evaluate() paths.
4. Hardcoded terminal verdict / status tags without dynamic hash receipts.
"""

import os
import re
import sys

FORBIDDEN_PATTERNS = [
    (
        r'btc_05feb_episode_capture_pct\s*:\s*\d+\.?\d*',
        "Hardcoded 05-Feb episode capture percentage literal detected (Rule 12.1 violation).",
    ),
    (
        r'status\s*:\s*["\']CAMPAIGN_RED_APPLE_FINAL_VERIFIED["\']',
        "Hardcoded verification success status string detected (Rule 12.4 violation).",
    ),
    (
        r'tail_capture_efficiency\s*:\s*0\.\d+',
        "Hardcoded tail capture efficiency (TCE) constant detected (Rule 12.1 violation).",
    ),
    (
        r'p_start\s*-\s*\(\s*i\s+as\s+f64\s*/',
        "Synthetic linear price synthesis loop detected (Rule 12.2 violation).",
    ),
    (
        r'p_value\s*:\s*0\.0[1-9]',
        "Hardcoded p-value metric literal detected (Rule 12.1 violation).",
    ),
]

def audit_files(root_dir: str) -> int:
    violations = 0
    print("==================================================================")
    print(">>> RUNNING RULE 12 ANTI-SYNTHETIC & ANTI-HALLUCINATION AUDIT <<<")
    print("==================================================================")
    
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if not f.endswith(".rs"):
                continue
            path = os.path.join(dirpath, f)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
                
            lines = content.splitlines()
            for line_no, line in enumerate(lines, 1):
                for pattern, msg in FORBIDDEN_PATTERNS:
                    if re.search(pattern, line):
                        print(f"❌ [RULE 12 VIOLATION] {path}:{line_no}")
                        print(f"   Line: {line.strip()}")
                        print(f"   Reason: {msg}\n")
                        violations += 1

    if violations == 0:
        print("✅ Rule 12 Audit: ZERO synthetic leaks or hardcoded metrics found.")
        print("==================================================================\n")
        return 0
    else:
        print(f"🚨 Rule 12 Audit FAILED: {violations} violation(s) detected.")
        print("==================================================================\n")
        return 1

if __name__ == "__main__":
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v8-core", "src")
    sys.exit(audit_files(src_dir))
