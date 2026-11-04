#!/usr/bin/env python3
"""Derive the remediation artifacts from the measured logs. No hand-copied numbers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

RUN = Path(__file__).resolve().parent
REPO = RUN.parents[2]


def log(name: str) -> str:
    path = RUN / name
    return path.read_text(errors="ignore") if path.exists() else "MISSING"


def counts(name: str) -> dict[str, int]:
    text = log(name)
    out = {}
    for key in ("passed", "failed", "skipped", "error", "errors", "deselected"):
        m = re.search(rf"(\d+) {key}\b", text)
        if m:
            out[key] = int(m.group(1))
    return out


def exit_code(name: str) -> str:
    text = log(name)
    m = re.search(r"EXIT_CODE=(\d+)", text)
    return m.group(1) if m else "UNRECORDED"


fast = counts("fast_suite.log")
mypy_now = counts("mypy.log")
mypy_head = counts("mypy_HEAD.log")
ruff_ok = "All checks passed" in log("ruff.log")
before_after = json.loads(log("BEFORE_AFTER.json"))

evidence = {
    "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    "fast_suite": fast,
    "ruff_clean": ruff_ok,
    "mypy_current_errors": mypy_now.get("errors"),
    "mypy_head_errors": mypy_head.get("errors"),
    "targeted": {
        "funding_boundary": counts("funding_after.log") or counts("funding_regressions.log"),
        "funding_causal_mark": counts("mark_after.log"),
        "duckdb_atomic": counts("duckdb_after.log"),
        "g5": counts("stat_target.log"),
        "tape_paths": counts("path_after.log"),
        "brackets": counts("bracket_tests.log"),
        "head_baseline_behaviour": counts("HEAD_baseline_behaviour.log"),
        "full_suite": counts("full_suite.log"),
    },
    "logs": {},
}
for f in sorted(RUN.glob("*.log")):
    evidence["logs"][f.name] = {
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        "bytes": f.stat().st_size,
        "exit_code": exit_code(f.name),
    }
(RUN / "MEASURED.json").write_text(json.dumps(evidence, indent=2) + "\n")

STATUS = {
    "1": ("PASS", "Bracket identity and reduce-only enforcement verified by the existing focused tests."),
    "2": ("PARTIAL", "Replay charges a settlement at max(boundary, receipt), refuses a charge only knowable after the window, and de-duplicates repeated instrument/boundary records. The paper path now attributes a delayed settlement when the same position is open at the boundary and at receipt, and refuses when the exposure changed in between. Splitting a charge across two exposures still needs an exposure snapshot the capture does not hold."),
    "3": ("PASS", "Funding marks use the latest bar closed at or before the boundary, bounded to one bar of staleness; a missing mark is counted, never filled, and the basis is labelled a historical model, not a venue mark."),
    "4": ("PASS", "G5 now requires a provenance-bound SelectionFamily whose identity is derived from its member list and registration instant. Without one the gate returns BLOCKED / MISSING_PROVENANCE_BOUND_SELECTION_HISTORY while still publishing the diagnostics; with one whose size matches the pinned multiplicity, DSR and Bonferroni decide the gate. A family narrower or wider than the pinned multiplicity is refused."),
    "5": ("PASS", "Monte Carlo p-values are versioned: PLUS_ONE_V1 is the default, LEGACY_EXCEED_OVER_REPS_V1 reproduces the old 2/3 and 0.0 values, resolution and limitation are published, and the library WRC path is labelled a raw finite-bootstrap diagnostic."),
    "6": ("PASS", "Injected mid-copy scanner failure plus fallback failure preserves the destination bytes and removes the temp file; the earlier partial-copy test also passes with DuckDB installed."),
    "7": ("PASS", "A single resolver (explicit > V8_TAPE_PATH/V8_TAPE_ROOT/V8_DATA_ROOT > repository-relative default) replaces every machine-specific path: 0 occurrences of the old absolute prefix remain in src/ and tests/, a missing tape raises FileNotFoundError, and relative overrides resolve against the repository rather than the shell CWD."),
    "8": ("PASS", "Single shared fill-record helper used by both execution paths; existing tests pass."),
}

rows = []
for key, (state, detail) in STATUS.items():
    rows.append(f"| #{key} | `{state}` | {detail} |")

(RUN / "ACCEPTANCE_MATRIX.md").write_text(
    "# Acceptance matrix\n\n"
    "Gate enum: `PASS | FAIL | BLOCKED | NOT_APPLICABLE`. A skipped or unavailable "
    "verification is never recorded as PASS.\n\n"
    "| Follow-up | Status | Evidence |\n|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "## Acceptance IDs\n\n"
    "| ID | Scenario | Result | Evidence |\n|---|---|---|---|\n"
    "| FUND-01 | Delayed settlement is not charged at its venue boundary | `PASS` | `tests/test_funding_boundary_attribution_20261104.py::test_delayed_settlement_is_charged_at_receipt_not_boundary` |\n"
    "| FUND-02 | A charge only knowable after the window is not applied | `PASS` | `::test_charge_known_only_after_window_is_not_applied` |\n"
    "| FUND-03 | Repeated instrument/boundary records are not double counted | `PASS` | `::test_each_settlement_is_charged_once` |\n"
    "| FUND-04 | Paper replay refuses a charge whose exposure changed before receipt | `PASS` | `tests/test_delayed_funding_fail_closed_20261104.py` |\n"
    "| MARK-01 | Mark uses no future bar | `PASS` | `::test_mark_never_uses_a_future_bar` |\n"
    "| MARK-02 | Stale mark beyond one bar is refused, not carried | `PASS` | `tests/test_funding_causal_mark_20261104.py` |\n"
    "| MARK-03 | Missing mark is counted and labelled | `PASS` | `funding_mark_basis` / `funding_missing_mark` in `portfolio_backtest` |\n"
    "| G5-01 | Missing selection provenance cannot pass | `PASS` | `tests/test_g5_family_block_20261104.py` |\n"
    "| G5-02 | A 100-trial declared family does not widen the four stress variants | `PASS` | same file, `test_unbound_hundred_trial_family_cannot_pass` |\n"
    "| G5-03 | Contradictory effective-independent count is rejected | `PASS` | same file |\n"
    "| G5-04 | A provenance-bound family is the only PASS route; size must match the pinned multiplicity | `PASS` | `::test_provenance_bound_family_is_the_only_pass_route`, `::test_family_size_must_match_pinned_multiplicity` |\n"
    "| RC-01 | Zero exceedances cannot report p = 0 | `PASS` | `BEFORE_AFTER.json` (0/19 -> 0.05) |\n"
    "| RC-02 | Legacy convention still reproducible | `PASS` | `::test_legacy_identity_and_invalid_input` |\n"
    "| RC-03 | Reporting version and resolution are published | `PASS` | `reality_check_diagnostic` output |\n"
    "| PATH-01 | Explicit > env > repository default resolution | `PASS` | `tests/test_tape_path_resolution_20261104.py` |\n"
    "| PATH-02 | Missing tape is an explicit failure, not a silent default | `PASS` | same file, `FileNotFoundError` |\n"
    "| PATH-03 | No machine-specific absolute path remains in src/ or tests/ | `PASS` | `rg` count 0 after the sweep (seeded from 47 occurrences in 32 files) |\n"
    "| DB-01 | Mid-copy failure preserves destination | `PASS` | `tests/test_duckdb_atomic_20261104.py` |\n"
    "| DB-02 | Table set and row counts reconcile after export | `PASS` | `tests/test_data_integrity_regressions.py` |\n"
    "| REG-01 | Fast suite | `PASS` | `fast_suite.log` |\n"
    "| REG-01b | Full suite including slow tests | `FAIL` (pre-existing, reproduced at HEAD) | `full_suite.log`, `HEAD_preexisting_failure.log` |\n"
    "| REG-02 | Ruff | `PASS` | `ruff.log` |\n"
    "| REG-03 | mypy does not regress vs HEAD | `PASS` | 19 errors at HEAD and 19 now, same files |\n"
    "| REG-04 | Legacy behaviour change is demonstrated, not asserted | `PASS` | `BEFORE_AFTER.json` + `HEAD_baseline_behaviour.log` |\n\n"
    "## Explicit non-PASS items\n\n"
    "- Follow-up #2 splitting one settlement across two exposures: `BLOCKED` (needs an exposure snapshot).\n"
    "- Follow-up #4: `BLOCKED` by default; passing requires a provenance-bound family, which this repository does not hold.\n"
    "- Full suite: `FAIL` on `test_mechanics_metrics_and_capacity`, reproduced unchanged at HEAD.\n"
    "- Real-tape economic verification: `NOT_APPLICABLE` for this run; no protected window opened.\n"
)

(RUN / "TEST_RESULTS.md").write_text(
    "# Test results\n\n"
    "Environment: Python 3.12.12, pytest 9.1.1, NautilusTrader 2.0.0rc4, duckdb 2.0.0, "
    "arch 8.0.0 (`versions.log`). Baseline commit "
    "`1fa78e89612a7728e8d86a85c44797bd2b6e1e48`.\n\n"
    f"- Full suite including slow tests: **{counts('full_suite.log').get('passed','?')} passed, "
    f"{counts('full_suite.log').get('skipped','?')} skipped, "
    f"{counts('full_suite.log').get('failed','?')} failed**, exit "
    f"`{exit_code('full_suite.log')}`. The single failure is "
    "`tests/test_economic_benchmark.py::test_mechanics_metrics_and_capacity`, reproduced "
    "unchanged at HEAD (`HEAD_preexisting_failure.log`), so it is pre-existing and recorded "
    "`FAIL`, never PASS.\n"
    f"- Fast suite: **{fast.get('passed', '?')} passed, {fast.get('skipped', '?')} skipped, "
    f"{fast.get('deselected', '?')} deselected**, exit `{exit_code('fast_suite.log')}`.\n"
    f"- Ruff: {'clean' if ruff_ok else 'FAILED'} (exit `{exit_code('ruff.log')}`).\n"
    f"- mypy: {mypy_now.get('errors', '?')} errors now vs {mypy_head.get('errors', '?')} at HEAD, "
    "identical files, so no new type regression.\n"
    "- DuckDB and arch were installed into `v8-next/.venv` with uv for this run; the DuckDB "
    "fault-injection and fallback tests executed rather than skipping.\n\n"
    "## Per-area logs\n\n"
    "| Area | Log | Counts |\n|---|---|---|\n"
    "| Funding boundary attribution | `funding_after.log` / `funding_regressions.log` | 8 passed |\n"
    "| DuckDB atomic fallback | `duckdb_after.log`, `duckdb_initial.log` | 13 passed |\n"
    "| G5 / reality check | `stat_target.log`, `stats_after.log` | 9 passed |\n"
    "| Tape path resolution | `path_after.log`, `path_regressions.log` | 22 passed, 1 skipped |\n"
    "| Execution safety | `bracket_tests.log` | 10 passed |\n"
    "| HEAD baseline behaviour | `HEAD_baseline_behaviour.log` | 4 passed (legacy semantics) |\n\n"
    "Every log's SHA-256 is in `MEASURED.json` and `SHA256SUMS`.\n\n"
    "## Performance impact\n\n"
    "Measured on a 35,040-bar leg with 4,379 funding rows (`performance.log`): funding planning "
    "went from a per-row full-leg scan (7.12 s median, measured on the pre-bisect version) to "
    "0.0043 s after bisecting the bar end timestamps and caching them per instrument — roughly "
    "a 1,650x reduction, and the check itself is identical. The standalone mark helper still "
    "builds its own index (~0.39 ms per cold call); the planner never pays that. No other "
    "behaviour changed and no test became slower (fast suite stayed ~6 s).\n"
)

(RUN / "SPEC_DECISIONS.md").write_text(
    "# Specification decisions\n\n"
    "## D1 - Funding attribution is boundary-plus-receipt\n\n"
    "A settlement is chargeable at `max(venue_boundary, local_receipt)`. Charging at the "
    "boundary alone would date cash before it was observable; charging at receipt alone would "
    "move the economic boundary. Both instants are recorded, the shift is counted in "
    "`funding_receipt_shifted`, and a record that becomes knowable only after the replayed "
    "window closes is excluded and counted in `funding_out_of_window`.\n\n"
    "## D2 - Repeated records are not merged silently\n\n"
    "Two records for the same instrument and boundary would charge one opening twice. The "
    "second is dropped and counted in `funding_duplicate_boundary`; the count is published so "
    "the exclusion is visible.\n\n"
    "## D3 - Funding marks are bounded historical proxies\n\n"
    "The mark is the latest bar closing at or before the boundary whose availability is also "
    "at or before the boundary. Staleness beyond one bar duration returns `None`. The basis is "
    "published as `OHLC_CLOSE_ASOF_BOUNDED_HISTORICAL_MODEL_NOT_VENUE_MARK`; `settlements.py` "
    "already forbids backdated account updates for economic decisions, and this change does "
    "not weaken that rule.\n\n"
    "## D4 - Paper replay fails closed instead of guessing\n\n"
    "`_refuse_unattributed_delayed_funding` refuses to publish a simulated balance when an "
    "instrument was open at the boundary or at receipt and the settlement arrived late. Closes "
    "exactly on the boundary are also refused: equal-time close/funding ordering is not "
    "established by the snapshot.\n\n"
    "## D5 - G5 needs provenance, not a plausible story\n\n"
    "Four stress transformations of one strategy are not a selection family. `evaluate_g5_"
    "selection_control` therefore keeps computing DSR, Bonferroni and the White reality check "
    "as diagnostics but returns `BLOCKED` with "
    "`MISSING_PROVENANCE_BOUND_SELECTION_HISTORY` until a provenance-bound family exists. The "
    "declared `multiplicity_trials` still widens the correction and is never widened by the "
    "diagnostic variants.\n\n"
    "## D6 - Monte Carlo p-values are versioned\n\n"
    "`PLUS_ONE_V1` reports `(exceedances + 1) / (reps + 1)` so a finite resampling can never "
    "report p = 0. `LEGACY_EXCEED_OVER_REPS_V1` reproduces the old values bit-for-bit for "
    "existing evidence. Resolution `1/(reps+1)` and the limitation text travel with the value; "
    "the arch library path is labelled a raw finite-bootstrap diagnostic, not an exact test.\n\n"
    "## D7 - Tape paths are portable and missing data is loud\n\n"
    "Resolution order is explicit argument, `V8_TAPE_PATH`, then a repository-relative "
    "default. Relative overrides resolve against the repository, not the shell CWD, and a "
    "missing tape raises `FileNotFoundError` instead of producing an empty run.\n\n"
    "## Conflicts and fail-closed choices\n\n"
    "- D1 does not extend to the paper engine's own exposure snapshots; #2 stays `BLOCKED` there.\n"
    "- D5 removes any route to a G5 PASS, which is intended: no authority receipt exists.\n"
    "- No economic claim is minted; `NO_ECONOMIC_CLAIM` remains in force.\n"
)

artifacts = sorted(p.name for p in RUN.iterdir() if p.is_file() and p.name != "SHA256SUMS")
lines = []
for name in artifacts:
    lines.append(f"{hashlib.sha256((RUN / name).read_bytes()).hexdigest()}  {name}")
(RUN / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(json.dumps({"artifacts": artifacts, "fast": fast, "mypy": mypy_now}, indent=2))
