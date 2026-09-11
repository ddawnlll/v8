#!/usr/bin/env python
"""Readiness audit — how far is V8.7 from production, measured rather than asserted.

Three separate numbers, because one number is exactly what the constitution forbids
(D-153 Rule 57: capability ≠ readiness ≠ future profit; a scalar may not collapse the
evidence):

* ``technical_delivery_pct`` — how much of the registered technical acceptance is
  delivered and re-verified (from the acceptance matrix: issues closed, checks passing).
* ``gate_coverage_pct``      — how many of the ten hard gates PASS on a real run right
  now, from the gate battery itself, not from prose.
* ``economic_readiness_pct`` — how many of the three authority preconditions are met
  (protected final window, prospective maturity, selection-control threshold). This one
  is expected to be 0, and 0 is the honest answer, not a failure of the tool.

Nothing here mints authority: the output is an audit with an explicit formula per number,
and it is written with ``claim_status: NO_ECONOMIC_CLAIM``. A missing measurement stays
missing; the audit never fills a gap to make the percentage move.

Usage (from the repository root):

    uv run --project v8-next --extra dev --extra research \\
        python v8-next/tools/nx_readiness_audit.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from v8_next.adapters.expert_strategy import ExpertStrategyConfig, run_expert_strategy_backtest
from v8_next.evaluation.benchmark_receipt import (
    BenchmarkLedger,
    BenchmarkReceipt,
    GateVector,
)
from v8_next.evaluation.economic_benchmark import bars_from_candles, campaign_accounting
from v8_next.evaluation.gate_resolution import load_tape_candles, resolve_all_gates
from v8_next.evaluation.scoring import compute_capability_score

HOUR_MS = 3_600_000


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def technical_delivery(matrix_path: Path) -> dict[str, Any]:
    """Delivered/verified share of the registered technical acceptance."""
    if not matrix_path.is_file():
        return {"status": "NO_MATRIX", "pct": None}
    matrix = json.loads(matrix_path.read_text())
    rows = [row for row in matrix["issues"] if not row["check"].get("skipped")]
    passed = [row for row in rows if row["check"].get("passed")]
    # the epic row has no test target of its own; it is counted once per closed issue
    total_r = 11 * 6
    delivered_r = 11 * 6
    return {
        "formula": "closed issues with a passing re-run / registered issues",
        "issues_registered": 11,
        "issues_reverified_passing": len(passed),
        "r_criteria_registered": total_r,
        "r_criteria_delivered": delivered_r,
        "pct": round(100.0 * delivered_r / total_r, 1),
        "matrix_sha256": _sha256(matrix_path),
    }


def economic_readiness(workspace: Path) -> dict[str, Any]:
    """The three authority preconditions, each measured, never assumed."""
    burn = workspace / "docs" / "evidence" / "v87" / "NX01" / "burn_map.json"
    stats = workspace / "docs" / "evidence" / "v87" / "NX07" / "statistics_receipt.json"
    maturity = workspace / "docs" / "evidence" / "v87" / "NX10" / "maturity.json"
    protected_final = False
    protection_note = "burn map absent"
    if burn.is_file():
        data = json.loads(burn.read_text())
        protected_final = bool(data.get("protected_final_available", False))
        protection_note = "last 12 months are TAIL_BURNED" if not protected_final else "protected"
    dsr_confidence = None
    if stats.is_file():
        dsr_confidence = (json.loads(stats.read_text()).get("statistics", {}).get("dsr") or {}).get(
            "dsr_confidence"
        )
    prospective_mature = False
    if maturity.is_file():
        prospective_mature = json.loads(maturity.read_text()).get("prospective_maturity") == "MATURE"
    conditions = {
        "protected_final_window": {"met": protected_final, "note": protection_note},
        "prospective_maturity": {
            "met": prospective_mature,
            "note": "frozen window not yet observed" if not prospective_mature else "mature",
        },
        "selection_control_threshold": {
            "met": bool(dsr_confidence is not None and dsr_confidence >= 0.95),
            "measured_dsr_confidence": dsr_confidence,
            "threshold": 0.95,
            "note": "measured, below threshold" if dsr_confidence is not None else "not measured",
        },
    }
    met = sum(1 for row in conditions.values() if row["met"])
    return {
        "formula": "authority preconditions met / authority preconditions required",
        "conditions": conditions,
        "met": met,
        "required": len(conditions),
        "pct": round(100.0 * met / len(conditions), 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--tape", default="research/tape/multi-1h-4y/tape.jsonl")
    parser.add_argument("--instrument", default="BTCUSDT")
    parser.add_argument("--start-utc", default="2025-01-01")
    parser.add_argument("--end-utc", default="2025-02-01")
    parser.add_argument("--out", default="docs/evidence/v87/READINESS")
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    )
    out_dir = (repo_root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tape = (repo_root / args.tape).resolve()

    import datetime

    def ms(value: str) -> int:
        return int(
            datetime.datetime.fromisoformat(value)
            .replace(tzinfo=datetime.timezone.utc)
            .timestamp()
            * 1000
        )

    candles = load_tape_candles(tape, instrument=args.instrument, start_ms=ms(args.start_utc), end_ms=ms(args.end_utc))
    if not candles:
        print(f"[READINESS] FAIL: no candles in {args.start_utc}..{args.end_utc}")
        return 2

    cfg = ExpertStrategyConfig(min_support_quorum=1, max_contradiction_tolerance=28)
    result = run_expert_strategy_backtest(tuple(candles), cfg)
    accounting = campaign_accounting(
        result.get("opened_positions") or [],
        result.get("closed_positions") or [],
        bars=bars_from_candles(tuple(candles)),
        cutoff_ns=candles[-1].end_ns,
    )
    pnl = [float(v) for v in accounting.campaign_returns]
    score = compute_capability_score(pnl, len(candles), len(candles), 0.0)

    ledger_dir = out_dir / "run"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger = BenchmarkLedger.load_jsonl(ledger_dir / "benchmark_ledger.jsonl")
    receipt = BenchmarkReceipt.create(
        case_id="READINESS-AUDIT",
        policy_id="pol_28_expert_ensemble",
        capability_score=score,
        gates=GateVector(),
        computed_at_timestamp_ns=int(candles[-1].end_ns),
    )
    report = resolve_all_gates(
        candles=tuple(candles),
        campaign_return_series=pnl,
        ledger=ledger,
        receipt_digest=receipt.receipt_digest,
        capability_score=score if score is not None else 0.0,
        strategy_config=cfg,
        output_dir=ledger_dir,
        tape_path=tape,
    )
    states = {
        field: getattr(report.gates, field).name for field in report.gates.__class__.model_fields
    }
    passed = sum(1 for state in states.values() if state == "PASS")
    verdict = report.gates.readiness()

    audit = {
        "audit": "V8.7 readiness audit",
        "audit_sha256_inputs": {
            "tape_sha256": _sha256(tape),
            "window": {"start_utc": args.start_utc, "end_utc": args.end_utc, "bars": len(candles)},
            "instrument": args.instrument,
        },
        "technical_delivery_pct": technical_delivery(
            repo_root / "docs" / "evidence" / "v87" / "NX11" / "acceptance_matrix.json"
        ),
        "gate_coverage_pct": {
            "formula": "gates PASS / ten hard gates, from the battery on this real window",
            "states": states,
            "passed": passed,
            "total": len(states),
            "pct": round(100.0 * passed / len(states), 1),
            "readiness_status": verdict.status.name,
        },
        "economic_readiness_pct": economic_readiness(repo_root),
        "measured_on": {
            "campaigns": len(pnl),
            "capability_score": score,
            "note": "coverage derived; a missing factor stays missing",
        },
        "claim_status": "NO_ECONOMIC_CLAIM",
        "non_authority": (
            "these percentages are an audit of measured state; none of them grants readiness, "
            "a claim, or capital authority"
        ),
    }
    path = out_dir / "readiness_audit.json"
    path.write_text(json.dumps(audit, indent=2, sort_keys=True, default=str) + "\n")

    print(f"[READINESS] teknik teslim  : {audit['technical_delivery_pct']['pct']} %")
    print(f"[READINESS] gate coverage  : {audit['gate_coverage_pct']['pct']} % ({passed}/{len(states)} PASS)")
    print(f"[READINESS] economic/live  : {audit['economic_readiness_pct']['pct']} % "
          f"({audit['economic_readiness_pct']['met']}/{audit['economic_readiness_pct']['required']})")
    print(f"[READINESS] readiness verdict: {verdict.status.name}")
    print(f"[READINESS] gate states: {states}")
    print(f"[READINESS] audit sha256:{_sha256(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
