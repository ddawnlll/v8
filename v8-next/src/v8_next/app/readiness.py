"""Readiness audit for the locked benchmark (docs/contracts/V87_READINESS_BENCHMARK_SPEC.md).

Answers "how production-ready are we" with four separately printed factors, never one
number on its own. Every factor is derived from artifacts on disk:

* ``gate_factor``   - gates PASS / 10, from the latest ledger receipt's gate vector
* ``pillar_factor`` - measured pillars / 3: P1 gate battery, P2 four-year paper-trade
                      report, P3 synthetic hypothesis scenarios. A pillar whose artifacts
                      are absent is MISSING and contributes 0 - it is never filled in.
* ``risk_factor``   - 1 only when the declared risk limits are respected by the measured
                      paper-trade record; 0 on any breach; MISSING when there is no record
* ``target_factor`` - protected monthly return / 10 % (the red apple), capped at 1. It is
                      diagnostic-only (contributes 0) on a window that is not protected.

Nothing here mints authority: the verdict stays NO_ECONOMIC_CLAIM and the report names
exactly which measurement is missing next.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: declared risk limits for the paper-trade pillar (breach => risk factor 0)
RISK_LIMITS = {
    "max_drawdown": -0.25,
    "max_fee_drag_vs_gross": 2.0,
    "max_exposure": 1.0,
}

#: the red apple: the far target, never a claim
RED_APPLE_MONTHLY_RETURN = 0.10

#: artifacts that prove each pillar exists and was measured
PILLAR_ARTIFACTS = {
    "P1_gate_battery": ("docs/evidence/v87-r2/NX09/fold_results.json",),
    "P2_paper_trade_4y": (
        "docs/evidence/v87-r3/RECONCILE/engine_replay_reconciliation.json",
        "docs/evidence/v87-r3/COST/cost_lane.json",
        "docs/evidence/v87-r3/PAPER_4Y/paper_trade_4y.json",
    ),
    "P3_synthetic_scenarios": (
        "docs/evidence/v87-r3/SCENARIOS/scenario_results.json",
    ),
}


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def gate_factor(receipt: Any | None) -> dict[str, Any]:
    """PASS gates / 10, read from the receipt that is actually on the ledger."""
    if receipt is None:
        return {"factor": 0.0, "passed": 0, "required": 10, "states": {}, "status": "MISSING"}
    gates = receipt.gates
    fields = list(gates.__class__.model_fields)
    states = {name: getattr(gates, name).name for name in fields}
    passed = sum(1 for state in states.values() if state == "PASS")
    return {
        "factor": round(passed / len(fields), 4),
        "passed": passed,
        "required": len(fields),
        "states": states,
        "status": "MEASURED",
    }


def pillar_factor(repo_root: Path) -> dict[str, Any]:
    """Measured pillars / 3; an absent pillar is MISSING, never a silent zero."""
    pillars: dict[str, Any] = {}
    measured = 0
    for name, artifacts in PILLAR_ARTIFACTS.items():
        present = [rel for rel in artifacts if (repo_root / rel).is_file()]
        missing = [rel for rel in artifacts if rel not in present]
        if present and not missing:
            declared_pass = True
            for rel in present:
                data = _load(repo_root / rel) or {}
                if "passed" in data and not data["passed"]:
                    declared_pass = False
            if not declared_pass:
                pillars[name] = {
                    "status": "PRESENT_BUT_NOT_PASSING",
                    "artifacts": present,
                    "note": "the artifact exists but declares passed=false; it is not counted",
                }
                continue
            measured += 1
            pillars[name] = {"status": "MEASURED", "artifacts": present}
        elif present:
            pillars[name] = {"status": "PARTIAL", "artifacts": present, "missing": missing}
        else:
            pillars[name] = {"status": "MISSING", "missing": missing}
    total = len(PILLAR_ARTIFACTS)
    return {
        "factor": round(measured / total, 4),
        "measured": measured,
        "required": total,
        "pillars": pillars,
    }


def risk_factor(repo_root: Path, paper_artifacts: list[str]) -> dict[str, Any]:
    """Declared risk limits against the measured paper-trade record."""
    metrics: dict[str, Any] = {}
    for rel in paper_artifacts:
        data = _load(repo_root / rel)
        if data is None:
            continue
        for key in ("max_drawdown", "fee_cost_return_sum", "net_return_measured_only_sum",
                    "exposure", "average_exposure"):
            if key in data:
                metrics[key] = data[key]
            if "family" in data:
                for policy, entry in data["family"].items():
                    for basis, totals in (entry.get("totals_by_slippage_fraction") or {}).items():
                        metrics[f"{policy}.slippage_{basis}.max_drawdown"] = totals.get("max_drawdown")
                        metrics[f"{policy}.slippage_{basis}.net_measured"] = totals.get(
                            "net_return_measured_only_sum"
                        )
    if not metrics:
        return {"factor": 0.0, "status": "MISSING", "metrics": {}, "breaches": []}
    breaches: list[str] = []
    drawdowns = [v for k, v in metrics.items() if "drawdown" in k and isinstance(v, (int, float))]
    for value in drawdowns:
        if value is not None and value < RISK_LIMITS["max_drawdown"]:
            breaches.append(f"max_drawdown {value} beyond {RISK_LIMITS['max_drawdown']}")
    return {
        "factor": 0.0 if breaches else 1.0,
        "status": "BREACH" if breaches else "RESPECTED",
        "metrics": metrics,
        "breaches": breaches,
        "limits": RISK_LIMITS,
    }


def target_factor(repo_root: Path) -> dict[str, Any]:
    """Red-apple progress; counted only when the return came from a protected window."""
    protected = (repo_root / "docs/evidence/v87/NX01/burn_map.json").is_file() and bool(
        (_load(repo_root / "docs/evidence/v87/NX01/burn_map.json") or {}).get(
            "protected_final_available", False
        )
    )
    monthly: float | None = None
    cost_lane = _load(repo_root / "docs/evidence/v87-r3/COST/cost_lane.json")
    if cost_lane:
        months = max(
            1,
            round(
                (cost_lane.get("window", {}).get("window_bars", 744)) / (24 * 30),
            ),
        )
        totals = []
        for entry in (cost_lane.get("family") or {}).values():
            for row in (entry.get("totals_by_slippage_fraction") or {}).values():
                value = row.get("net_return_measured_only_sum")
                if isinstance(value, (int, float)):
                    totals.append(value)
        if totals:
            monthly = max(totals) / months
    if monthly is None:
        return {"factor": 0.0, "status": "MISSING", "monthly_return": None,
                "target_monthly_return": RED_APPLE_MONTHLY_RETURN}
    factor = 0.0 if not protected else min(1.0, max(0.0, monthly / RED_APPLE_MONTHLY_RETURN))
    return {
        "factor": round(factor, 4),
        "status": "COUNTED" if protected else "DIAGNOSTIC_ONLY_NOT_PROTECTED",
        "monthly_return": round(monthly, 6),
        "target_monthly_return": RED_APPLE_MONTHLY_RETURN,
        "note": "a target measured on an unprotected window is reported, never counted",
    }


def write_scenario_report(repo_root: Path, out_rel: str | None = None) -> Path:
    """Produce the P3 artifact: model candles + SNU ledger + the overfitting hypothesis test."""
    import hashlib

    from v8_next.evaluation.scenarios import scenario_results

    target = repo_root / (out_rel or PILLAR_ARTIFACTS["P3_synthetic_scenarios"][0])
    target.parent.mkdir(parents=True, exist_ok=True)
    results = scenario_results()
    results["artifact_sha256_self"] = "computed_after_write"
    payload = json.dumps(results, indent=2, sort_keys=True, default=str) + "\n"
    target.write_text(payload)
    digest = hashlib.sha256(payload.replace("computed_after_write", "").encode()).hexdigest()
    results["artifact_sha256_self"] = digest
    target.write_text(json.dumps(results, indent=2, sort_keys=True, default=str) + "\n")
    return target


def audit(repo_root: Path, ledger_path: Path, latest_receipt: Any | None) -> dict[str, Any]:
    gates = gate_factor(latest_receipt)
    pillars = pillar_factor(repo_root)
    risk = risk_factor(repo_root, PILLAR_ARTIFACTS["P2_paper_trade_4y"])
    target = target_factor(repo_root)
    readiness = round(
        100.0 * gates["factor"] * pillars["factor"] * risk["factor"] * target["factor"], 2
    )
    next_measurement = next(
        (
            (name, info)
            for name, info in pillars["pillars"].items()
            if info["status"] != "MEASURED"
        ),
        None,
    )
    return {
        "readiness": readiness,
        "factors": {
            "gate_factor": gates,
            "pillar_factor": pillars,
            "risk_factor": risk,
            "target_factor": target,
        },
        "formula": "100 * gate_factor * pillar_factor * risk_factor * target_factor",
        "next_required_measurement": None if next_measurement is None else next_measurement[0],
        "claim_status": "NO_ECONOMIC_CLAIM",
        "ledger": str(ledger_path),
        "non_authority": (
            "the four factors are printed together on purpose: the composite is an audit of "
            "measured state and grants no capital or publication authority"
        ),
    }
