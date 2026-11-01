"""Finish the issue-body pass: #389's Evidence block and a status line on #477 / #495."""
from __future__ import annotations

import sys

sys.path.insert(0, "audit_out/critical_fixes_20261101")
from update_issues import gh  # noqa: E402

EDITS: dict[str, list[tuple[str, str]]] = {
    "389": [
        ("## Evidence\n\nPENDING",
         "## Evidence\n\nFIXED on PR #501 (open, unmerged, base `a921da2`).\n\n"
         "- `EXIT_LEDGER_QUARANTINED = 3`; a BROKEN chain renders no `PolicyCertificate`; an empty ledger "
         "is its own named state instead of an early `return 0`.\n"
         "- `tests/test_cli_status_ledger_quarantine_389.py`: 3 failed / 4 passed on clean "
         "`main@a921da2` (`assert 0 == 3`), 7 passed on the branch. Branch suite 1014 passed / 9 skipped.\n"
         "- Full detail: `audit_out/critical_fixes_20261101/389_evidence.md`, `verify_389/`."),
    ],
    "477": [
        ("### Evidence",
         "### Status\n\nPARTIAL on PR #502 (open, unmerged, base `a921da2`). R1, R2, R3, R5 and gate 2 for "
         "**every** published entry are delivered and verified end-to-end on a real producer run "
         "(`E2E_EVIDENCE.md`, `e2e/477_post/`): 6 of 6 `capacity_scenarios` entries carry a contract "
         "status, where the committed receipt had `MEASURED_LINEAR_BOUND` with no `status` at all. "
         "R4 is not fully satisfied: the canonical 12-month `quad-1h-12m` tape is absent, so the receipt "
         "was re-taken from a real 4-leg rebuild of the same window, not from the committed canonical "
         "artifact. The PR says `Refs #477 — do not close on merge`.\n\n### Evidence"),
    ],
    "495": [
        ("## Acceptance",
         "## Status\n\nFIXED on PR #505 (open, unmerged, base `a921da2`): R1 (rename + read-side alias, "
         "D-164-safe, and the `site/app.html` renderer), R2 (producer calls the real resolver), R3 "
         "(`G3ScenarioBasis` travels with the state, named `G3_SCENARIO_BASIS_ABSENT` refusal), and gates 2 "
         "and 3 executed on a real run — the ledger entry publishes `['g3_scenario_robustness'] -> "
         "['BLOCKED']` with a four-regime basis and no `g3_benchmark_coverage` anywhere. `BLOCKED` because "
         "every regime recorded `trades: 0`: fail-closed with its measured inputs attached. Evidence: "
         "`495_evidence.md`, `E2E_EVIDENCE.md`, `e2e/495_post/`. The PR says `Closes #495`.\n\n## Acceptance"),
    ],
}

for number, pairs in EDITS.items():
    body = gh("issue", "view", number, "--json", "body", "-q", ".body").stdout
    for old, new in pairs:
        if old not in body:
            print(f"#{number}: pattern not found {old[:60]!r}")
            continue
        body = body.replace(old, new, 1)
    path = f"audit_out/critical_fixes_20261101/issue_body_{number}.md"
    open(path, "w", encoding="utf-8").write(body)
    r = gh("issue", "edit", number, "--body-file", path)
    print(f"#{number} body edit rc={r.returncode} {r.stderr.strip()[:120]}")
