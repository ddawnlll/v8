"""S5 ledger gate — LEDGER_FORMAT_SPEC §8 cheap tests (issue #109).

The six cheap tests (round-trip, header completeness, byte-stability, tier
honesty, no-decimal-floats scan, retention) run inside the compute plane as
`v8-core ledger-check`, each against a deterministic self-built VALUES-tier
fixture. The gate asserts the driver reports every one PASS and exits 0 — the
ledger-format contract is executable, not prose.

No oracle is involved: the battery's own unit tests in evidence.rs pin the
value-level semantics (regeneration, fail-closed header reads, fingerprint
equality, TierViolation, region-scoped scans, retention records); this file
runs the shipped binary end to end the way the audit tool would be invoked.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

# The six §8 test names exactly as the binary prints them.
S8_TESTS = ("round-trip", "header-completeness", "byte-stability",
            "tier-honesty", "no-decimal-floats", "retention")


def _run_ledger_check(v8_core_binary, request: dict | None, out_dir: Path):
    """Invoke `v8-core ledger-check` (with or without a request file)."""
    cmd = [str(v8_core_binary), "ledger-check"]
    if request is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        req_path = out_dir / "request.json"
        req_path.write_text(json.dumps(request))
        cmd.append(str(req_path))
    return subprocess.run(cmd, capture_output=True, text=True)


def _assert_all_six_pass(proc, request_desc: str):
    assert proc.returncode == 0, (
        f"ledger-check({request_desc}) rc={proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    for name in S8_TESTS:
        assert f"ledger-check: {name}: PASS" in proc.stdout, (
            f"missing PASS line for {name}:\n{proc.stdout}\n{proc.stderr}")
    assert "all 6 tests passed" in proc.stdout, proc.stdout
    assert "FAIL" not in proc.stdout, proc.stdout


def test_ledger_check_fixture_request_all_six_pass(v8_core_binary, tmp_path):
    """§8 battery against a request-provided out_dir and tape hash."""
    out_dir = Path(tmp_path)
    proc = _run_ledger_check(v8_core_binary, {
        "out_dir": str(out_dir),
        "tape_hash": "0123456789abcdef0123456789abcdef01234567",
    }, out_dir)
    _assert_all_six_pass(proc, "fixture request")
    # The battery wrote its fixture artifacts and the retention record into
    # the requested out_dir.
    assert (out_dir / "rt-fixture.v82").is_file()
    assert (out_dir / "retention.jsonl").is_file()


def test_ledger_check_self_built_fixture_all_six_pass(v8_core_binary):
    """§8 battery with no request: the driver builds its own fixture (the
    audit-tool default path)."""
    proc = _run_ledger_check(v8_core_binary, None, Path("."))
    _assert_all_six_pass(proc, "no request")


def test_ledger_check_rejects_extra_args(v8_core_binary):
    """The driver fails closed on a malformed invocation."""
    proc = subprocess.run([str(v8_core_binary), "ledger-check", "a", "b"],
                          capture_output=True, text=True)
    assert proc.returncode == 2, proc.stdout
    assert "usage" in proc.stderr
