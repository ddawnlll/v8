#!/usr/bin/env python3
"""Audit the Rust/Python ownership boundary.

This is a stdlib-only policy check. It does not run the Python oracle. It
verifies the frozen oracle tree, rejects dirty oracle edits, and checks the
owner's local-only verification boundary.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs" / "legacy" / "PYTHON_ORACLE_LOCK.json"
WORKFLOWS = ROOT / ".github" / "workflows"


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

    for workflow in sorted(WORKFLOWS.glob("*")):
        if workflow.suffix in {".yml", ".yaml"}:
            errors.append(f"GitHub workflow present despite local-only checks: {workflow.name}")

    if errors:
        print("python boundary: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("python boundary: OK (oracle frozen; local-only Rust verification)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
