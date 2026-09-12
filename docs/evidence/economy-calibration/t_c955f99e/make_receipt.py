#!/usr/bin/env python3
"""Regenerate this task's machine receipt and gate log.

Run from anywhere:  python3 docs/evidence/economy-calibration/t_c955f99e/make_receipt.py

The script re-runs the declared gates (ruff, mypy, targeted tests, fast loop),
asserts the outcome contract of this change, and writes ``receipt.json`` plus
``gates.log`` next to itself.  It mutates nothing outside this directory and
makes no economic claim.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import TypedDict


class PytestSummary(TypedDict):
    summary_line: str
    failed: list[str]
    counts: dict[str, str]


EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVIDENCE_DIR.parents[3]
TASK_ID = "t_c955f99e"

TOUCHED = (
    "v8-next/src/v8_next/evaluation/capacity.py",
    "v8-next/src/v8_next/evaluation/costs.py",
    "v8-next/src/v8_next/evaluation/mintrl.py",
    "v8-next/tests/test_capacity.py",
    "v8-next/tests/test_operating_net.py",
    "v8-next/tests/test_mintrl.py",
)
TOUCHED_SRC = tuple(path for path in TOUCHED if "/src/" in path)

# Failures that exist in a fresh worktree for environmental reasons (gitignored
# artifacts absent): the book library and the *.jsonl capture batches.  They are
# present in the pre-change baseline too and are asserted to be the ONLY
# failures, so a new regression cannot hide behind them.
ENVIRONMENTAL_FAILURES = frozenset(
    {
        "v8-next/tests/test_books.py::test_mapped_filenames_exist_in_library",
        "v8-next/tests/test_books.py::test_coverage_reports_mapped_vs_unmapped",
        "v8-next/tests/test_public_shadow_nx10.py::"
        "test_capture_manifest_chain_and_maturity_report",
    }
)

RUFF = ["uv", "run", "--project", "v8-next", "--extra", "dev", "ruff", "check",
        "v8-next/src", "v8-next/tests"]
MYPY = ["uv", "run", "--project", "v8-next", "--extra", "dev", "mypy", "v8-next/src"]
FAST_LOOP = ["uv", "run", "--project", "v8-next", "--extra", "dev", "--extra", "research",
             "pytest", "-q", "v8-next/tests"]
TARGETED = ["uv", "run", "--project", "v8-next", "--extra", "dev", "pytest", "-q", *TOUCHED[3:]]


def run(argv: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def digest(path: Path) -> dict[str, object]:
    content = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def git(*args: str) -> str:
    code, out = run(["git", *args])
    assert code == 0, f"git {' '.join(args)} failed: {out}"
    return out.strip()


def grep_lines(path: Path, pattern: str) -> list[str]:
    return [line for line in path.read_text().splitlines() if re.search(pattern, line)]


def l2_tape_census() -> dict[str, object]:
    """Census of the captured depth tapes; they are gitignored, so the primary
    checkout is used when the worktree does not carry them."""

    candidates = [REPO_ROOT / "research/tape", Path("/Users/hootie/src/v8/research/tape")]
    root = next((path for path in candidates if path.is_dir()), None)
    if root is None:
        return {"resolved_root": None, "status": "TAPE_NOT_PRESENT"}
    tapes: list[dict[str, object]] = []
    scanned = 0
    carrying = 0
    skipped_large = 0
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
                continue
            if path.stat().st_size > 4_000_000:
                skipped_large += 1
                continue
            scanned += 1
            content = path.read_text(errors="replace")
            if "filled_qty" in content or "fill_price" in content:
                carrying += 1
        depths = sorted(directory.glob("depth-*.json"))
        if not depths:
            continue
        first = json.loads(depths[0].read_text())
        last = json.loads(depths[-1].read_text())
        span_s = (last["E"] - first["E"]) / 1000.0
        tapes.append(
            {
                "tape": directory.name,
                "snapshot_files": len(depths),
                "span_s": round(span_s, 1),
                "poll_interval_s": round(span_s / max(1, len(depths) - 1), 2),
                "bid_levels": len(first["bids"]),
                "ask_levels": len(first["asks"]),
            }
        )
    return {
        "resolved_root": str(root),
        "tapes": tapes,
        "tape_files_scanned": scanned,
        "files_skipped_over_4MB": skipped_large,
        "files_carrying_fill_fields": carrying,
        "reading": (
            "REST snapshots polled at seconds-scale intervals are not event-sequenced "
            "top-of-book updates, and no tape file carries observed fills, so no OFI/impact "
            "coefficient can be estimated (memo section 2.2 / 2.5, DATA_BLOCKED)."
        ),
    }


def pytest_summary(output: str) -> PytestSummary:
    failed: list[str] = sorted(set(re.findall(r"^FAILED (\S+)", output, flags=re.MULTILINE)))
    tail = output.strip().splitlines()[-1] if output.strip() else ""
    counts: dict[str, str] = dict(re.findall(r"(\d+) (passed|failed|deselected|error)", tail))
    return PytestSummary(summary_line=tail, failed=failed, counts=counts)


def main() -> int:
    ruff_code, ruff_out = run(RUFF)
    mypy_code, mypy_out = run(MYPY)
    targeted_code, targeted_out = run(TARGETED)
    fast_code, fast_out = run(FAST_LOOP)

    assert ruff_code == 0, f"ruff not clean:\n{ruff_out}"
    mypy_errors = re.findall(r"^(\S+\.py):\d+: error:", mypy_out, flags=re.MULTILINE)
    touched_errors = sorted({path for path in mypy_errors if path in TOUCHED_SRC})
    assert not touched_errors, f"mypy errors in touched files: {touched_errors}"

    targeted = pytest_summary(targeted_out)
    assert targeted_code == 0, f"targeted tests failed:\n{targeted_out}"
    fast = pytest_summary(fast_out)
    assert set(fast["failed"]) == ENVIRONMENTAL_FAILURES, (
        "fast loop failed outside the recorded environmental set: "
        f"{sorted(set(fast['failed']) - ENVIRONMENTAL_FAILURES)}"
    )
    assert fast_code == 1, "the fast loop is expected to fail only on the environmental set"

    gates_log = "\n\n".join(
        [
            "# Gates — t_c955f99e (economy calibration: operating net, venue costs, guards)",
            f"# base_commit {git('rev-parse', 'HEAD')}",
            f"# branch {git('rev-parse', '--abbrev-ref', 'HEAD')}",
            f"$ {' '.join(RUFF)}\n{ruff_out}",
            f"$ {' '.join(MYPY)}\n{mypy_out}",
            f"$ {' '.join(TARGETED)}\n{targeted_out}",
            f"$ {' '.join(FAST_LOOP)}   # fast loop\n{fast_out}",
        ]
    )
    (EVIDENCE_DIR / "gates.log").write_text(gates_log + "\n")

    memo = REPO_ROOT / "docs/research/arXiv-economy-2026-09-12.md"
    pyproject = REPO_ROOT / "v8-next/pyproject.toml"
    foundry = REPO_ROOT / "v8-next/src/v8_next/world/foundry.py"
    proving_test = REPO_ROOT / "v8-next/tests/test_proving_ground.py"
    static_evidence = {
        "dev_loop_collection_break": {
            "pyproject_extras": grep_lines(pyproject, r"^dev = \[|^research = \[|^    \"arch"),
            "foundry_module_scope_import": grep_lines(foundry, r"^from arch"),
            "proving_test_pytestmark": grep_lines(proving_test, r"pytestmark"),
            "reading": (
                "arch is declared only in the research extra, imported at module scope by "
                "v8_next.world.foundry, and test_proving_ground.py imports foundry at module "
                "scope with no slow marker: a fresh '--extra dev' interpreter cannot collect "
                "the documented bare fast loop."
            ),
        },
        "l2_tape_census": l2_tape_census(),
        "mypy_baseline_method": {
            "steps": [
                "cp the three touched src files aside",
                "git checkout -- v8-next/src/v8_next/evaluation/{capacity,costs,mintrl}.py",
                "uv run --project v8-next --extra dev mypy v8-next/src  -> baseline report",
                "restore the saved files and verify their sha256 are unchanged",
                "diff baseline changed -> empty",
            ],
            "baseline_report": "12 errors in 7 files (checked 182 source files)",
            "conclusion": "no mypy error is introduced by this change",
        },
    }
    (EVIDENCE_DIR / "gates.log").write_text(
        (EVIDENCE_DIR / "gates.log").read_text()
        + "\n\n# Static evidence (recomputed by make_receipt.py)\n"
        + json.dumps(static_evidence, indent=2)
        + "\n"
    )
    receipt = {
        "task": TASK_ID,
        "board": "v8",
        "profile": "v8-engineer",
        "change_class": "CONTRACT_IMPLEMENTATION",
        "base_commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "economic_claim": "NO_ECONOMIC_CLAIM",
        "authority": {
            "card": TASK_ID,
            "merge_authority": "docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md (D-163)",
            "prohibited": [
                "no economic claim minted; every published status is NO_ECONOMIC_CLAIM / "
                "DATA_BLOCKED / UNRESOLVED / UNSUPPORTED",
                "no hardcoded coefficient, effect size or p-value",
                "no synthetic input reaches a runtime path",
            ],
        },
        "source_memo": {
            **digest(memo),
            "role": "navigation only; not completion evidence for any claim inside it",
        },
        "changed_files": [digest(REPO_ROOT / path) for path in TOUCHED],
        "gates": {
            "ruff": {"command": " ".join(RUFF), "result": "All checks passed!"},
            "mypy": {
                "command": " ".join(MYPY),
                "result": f"{len(mypy_errors)} pre-existing errors, 0 in touched files",
                "touched_file_errors": touched_errors,
                "baseline": (
                    "same command with the three touched src files restored to base_commit "
                    "produced a byte-identical report (diff empty); the baseline is "
                    "12 errors in 7 files."
                ),
            },
            "targeted_tests": {"command": " ".join(TARGETED), **targeted},
            "fast_loop": {
                "command": " ".join(FAST_LOOP),
                **fast,
                "environmental_failures": sorted(ENVIRONMENTAL_FAILURES),
                "note": (
                    "a fresh worktree lacks the gitignored book library and *.jsonl capture "
                    "batches; the same three tests fail at base_commit."
                ),
            },
        },
        "static_evidence": static_evidence,
        "guards": {
            "capacity.py": [
                "UNSEQUENCED_MICROSTRUCTURE_OBSERVATIONS: observations must be one strictly "
                "increasing event sequence",
                "UNSINGLE_INSTRUMENT_OBSERVATIONS: rows must come from one instrument",
                "OBSERVED_FILLS_AT_OTHER_SCALE: a counterfactual requested size is reported as "
                "a labelled projection with status UNRESOLVED, never as a measured fill/impact",
                "NO_MICROSTRUCTURE_OBSERVATIONS: DATA_BLOCKED",
            ],
            "costs.py": [
                "venue-cost.v2 receipt carries venue, fee tier and fee effective date, and "
                "separates maker from taker quantity-weighted fee rates",
                "FRICTION_NET_BASIS_NOT_EVIDENCED: price_pnl_already_net_of_friction requires "
                "an ArtifactBinding for the net-of-friction basis, else DATA_BLOCKED",
                "MISSING_FUNDING_FEES_OR_EXPENSES: DATA_BLOCKED",
                "artifact hash/size verification on the fee schedule, expenses and friction basis",
            ],
            "mintrl.py": [
                "the plan must declare identity POWER_REQUIRED_N or BAILEY_LDP_2012; an "
                "undeclared identity does not construct",
                "inputs the declared identity does not consume are rejected (no silent "
                "fallback to the other formula)",
                "MINTRL_CLOSED_FORM_UNDEFINED: non-positive gap or non-positive variance "
                "correction returns UNSUPPORTED with required_intervals=None",
                "DECLARED_MINTRL_PLAN_REQUIRED: UNSUPPORTED (unchanged)",
            ],
        },
        "findings": [
            {
                "id": "F1",
                "issue": "#378",
                "finding": (
                    "The published Bailey & Lopez de Prado (2012) MinTRL closed form and the "
                    "previously implemented estimator are different identities; the plan now "
                    "declares which one it means and the closed form is cross-checked against "
                    "the published expression, not against a stored constant."
                ),
                "artifact": "v8-next/src/v8_next/evaluation/mintrl.py",
                "test": "v8-next/tests/test_mintrl.py::"
                "test_mintrl_closed_form_matches_the_published_expression",
            },
            {
                "id": "F2",
                "issue": "#378",
                "finding": (
                    "The non-normality term is evaluated at the OBSERVED Sharpe and the gap at "
                    "(observed - benchmark). The memo's section 4.1 renders SR* in both places; "
                    "the implemented convention is the one carried by the published expression "
                    "and by independent implementations, and the discrimination is pinned by a "
                    "test where the two conventions give different integers."
                ),
                "artifact": "v8-next/tests/test_mintrl.py",
                "test": "v8-next/tests/test_mintrl.py::"
                "test_mintrl_closed_form_uses_the_observed_sharpe_in_the_variance_term",
            },
            {
                "id": "F3",
                "issue": "#382",
                "finding": (
                    "measure_capacity documented a sequencing/single-instrument contract it "
                    "never enforced, and published a counterfactual participation beside "
                    "observed-scale fill/impact (the linear extrapolation the memo lists as "
                    "REJECTED_OPTION). Both are now guarded."
                ),
                "artifact": "v8-next/src/v8_next/evaluation/capacity.py",
                "test": "v8-next/tests/test_capacity.py",
            },
            {
                "id": "F4",
                "issue": "#382",
                "finding": (
                    "The measured part of #382 stays DATA_BLOCKED on real tape: the captured "
                    "depth tapes are 20-level REST snapshots polled every ~3.3s (52/72/117 "
                    "files), not event-sequenced top-of-book updates, and none of the 293 "
                    "scanned tape files (4 skipped as >4MB) carries fill fields. No impact "
                    "coefficient is estimated or invented."
                ),
                "artifact": "docs/evidence/economy-calibration/t_c955f99e/gates.log",
            },
            {
                "id": "F5",
                "issue": "#385",
                "finding": (
                    "A venue-cost receipt without (venue, tier, effective date) collapses venue "
                    "heterogeneity; maker and taker fills now calibrate separately."
                ),
                "artifact": "v8-next/src/v8_next/evaluation/costs.py",
            },
            {
                "id": "F6",
                "issue": "#385",
                "finding": (
                    "price_pnl_already_net_of_friction was the only guard against a spread "
                    "double-count and was caller-declared with no evidence; it now requires a "
                    "verified ArtifactBinding or the ledger fails closed."
                ),
                "artifact": "v8-next/src/v8_next/evaluation/costs.py",
            },
            {
                "id": "F7",
                "issue": "#453",
                "finding": (
                    "Pre-existing, not introduced here: the documented bare fast loop "
                    "('--extra dev' only) cannot collect a fresh interpreter because "
                    "v8_next/world/foundry.py imports arch.bootstrap, declared only in the "
                    "research extra, from a test module with no slow marker. This run needed "
                    "'--extra research' present in the venv."
                ),
                "artifact": "docs/evidence/economy-calibration/t_c955f99e/gates.log",
                "follow_up_card": "created by this worker (see completion metadata)",
            },
        ],
        "remaining_blocked": {
            "#382_measured_impact": (
                "needs event-sequenced top-of-book quotes plus observed fills; the tape has "
                "neither, so no OFI/impact coefficient is published"
            ),
            "#385_funding_attribution": (
                "funding is still an aggregate scalar in compute_operating_net; the memo's "
                "settlement-period attribution (funding carry vs margin/liquidation events) "
                "needs settlement records that do not exist"
            ),
            "#385_permanent_vs_temporary": (
                "splitting fill-vs-mid friction needs post-fill reference observations "
                "(reversion test); absent, so no split is published"
            ),
            "#393_multiplicity": (
                "DSR inputs N and V must come from v8's own multiplicity ledger, not a worker; "
                "verdicts stay NO_ECONOMIC_CLAIM"
            ),
        },
    }
    (EVIDENCE_DIR / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=False) + "\n")
    print(f"wrote {EVIDENCE_DIR / 'gates.log'}")
    print(f"wrote {EVIDENCE_DIR / 'receipt.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
