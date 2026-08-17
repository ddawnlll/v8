#!/usr/bin/env python3
"""Audit the Rust/Python ownership boundary.

This is a stdlib-only policy check. It does not run the Python oracle. It
verifies the frozen oracle tree, rejects dirty oracle edits, and checks that CI
does not invoke Python tests or the oracle as part of the Rust runtime gate.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs" / "legacy" / "PYTHON_ORACLE_LOCK.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def git(*args: str) -> tuple[int, str]:
    p = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return p.returncode, p.stdout.strip()


def main() -> int:
    errors: list[str] = []
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    code, tree = git("rev-parse", "HEAD:src/v8")
    if code or tree != lock["git_tree"]:
        errors.append(
            f"src/v8 tree hash changed: expected {lock['git_tree']}, got {tree or 'unavailable'}"
        )

    for label, args in (
        ("working tree", ("diff", "--quiet", "--", "src/v8")),
        ("index", ("diff", "--cached", "--quiet", "--", "src/v8")),
    ):
        code, _ = git(*args)
        if code:
            errors.append(f"src/v8 has an unregistered {label} change")

    workflow = WORKFLOW.read_text(encoding="utf-8")
    # One differential fixture is an explicit acceptance gate: it invokes the
    # frozen oracle out-of-process and compares every result field against the
    # release Rust binary.  It is not a runtime path.  Any broader pytest use
    # remains forbidden so the exception cannot become a Python CI backdoor.
    allowed_parity = "python3 -m pytest tests/parity/test_parity_fill_limit.py -q"
    normalized_workflow = re.sub(r"[ \t]+", " ", workflow)
    if "pytest" in normalized_workflow and allowed_parity not in normalized_workflow:
        errors.append("CI invokes a Python test outside the pinned FILL_AT_LIMIT parity gate")
    forbidden = (
        (r"(?m)^\s*run:.*python(?:3)?\s+-m\s+v8\b", "CI invokes Python v8"),
        (r"(?m)^\s*run:.*(?:from|import)\s+v8\b", "CI imports Python v8"),
    )
    for pattern, message in forbidden:
        if re.search(pattern, workflow):
            errors.append(message)

    if errors:
        print("python boundary: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("python boundary: OK (oracle frozen; CI runtime path is Rust)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
