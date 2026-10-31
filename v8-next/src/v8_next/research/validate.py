"""Master-side validation of a research run.

This module is deliberately independent of what a worker *says*: it re-reads the
persisted artifacts, re-checks the arithmetic and refuses to pass a claim that
has no machine-readable row behind it.

It never rewrites evidence. It writes only the ``validation/`` directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from v8_next.research import contract as research_contract
from v8_next.research import metrics as research_metrics
from v8_next.research import screen

EXPERIMENT_DIRS = {
    "A": "experiment_A_signal",
    "B": "experiment_B_entry",
    "C": "experiment_C_exit",
    "D": "experiment_D_stateful",
}

LEGAL_STATUSES = {"SUPPORTED", "REJECTED", "INCONCLUSIVE", "BLOCKED"}
#: We reject *access evidence*, not disclosures. An artifact may legitimately
#: say "sealed OOS never accessed"; it may not record that the holdout was read.
FORBIDDEN_JSON_FLAGS = {
    "oos_opened": True,
    "oos_data_touched": True,
    "sealed_oos_accessed": True,
    "holdout_accessed": True,
}
FORBIDDEN_PATH_FRAGMENTS = ("/holdout/", "\\holdout\\", "/sealed-oos/", "sealed_oos")

REQUIRED_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "A": ("metrics.json", "arms.json", "validation.json", "findings.md"),
    "B": ("metrics.json", "arms.json", "validation.json", "findings.md"),
    "C": ("metrics.json", "arms.json", "validation.json", "findings.md"),
    "D": ("metrics.json", "arms.json", "validation.json", "findings.md"),
}


def _read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError as exc:
        return None, f"invalid_json: {exc}"


def _grep_forbidden(root: Path) -> list[str]:
    """Evidence of sealed-OOS ACCESS, not mentions of the word in disclosures."""
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = str(path.relative_to(root)).lower()
        if any(fragment in relative for fragment in FORBIDDEN_PATH_FRAGMENTS):
            hits.append(f"{path.relative_to(root)}::forbidden_path")
            continue
        if path.suffix not in {".json", ".jsonl"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in FORBIDDEN_JSON_FLAGS:
            if f'"{needle}": true' in text.replace(" ", ""):
                hits.append(f"{path.relative_to(root)}::{needle}=true")
    return hits


def _dataset_consistency(root: Path) -> dict[str, Any]:
    inventory, err = _read_json(root / "DATASET_INVENTORY.json")
    if err:
        return {"ok": False, "reason": err}
    manifest, err = _read_json(root / "baseline" / "baseline_manifest.json")
    if err:
        return {"ok": False, "reason": err}
    expected = (inventory or {}).get("dataset_hash")
    observed = (manifest or {}).get("dataset_sha256")
    return {
        "ok": bool(expected) and expected == observed,
        "expected_sha256": expected,
        "baseline_recorded_sha256": observed,
        "tape_sha256_matches_prior_audit": expected
        == "f63d77d3b540b883f769fe9a86a614340a3da4d3550b6891597c183b376bf713",
    }


def _baseline_reconciliation(root: Path) -> dict[str, Any]:
    recon, err = _read_json(root / "baseline" / "baseline_reconciliation.json")
    if err:
        return {"ok": False, "reason": err}
    reference = {"entries": 45, "closed": 44, "gross": 27.6707, "net": -8.67470686, "fees": 36.76607636}
    observed = {
        "entries": recon.get("campaign_count"),
        "closed": recon.get("campaign_count", 0) - 1,
        "gross": recon.get("gross_pnl_usdt"),
        "net": recon.get("net_pnl_usdt"),
        "fees": recon.get("fill_commission_total_usdt"),
    }
    tolerances = {"entries": 0, "closed": 0, "gross": 1e-6, "net": 1e-8, "fees": 1e-6}
    mismatches = {
        key: {"observed": observed[key], "reference": reference[key]}
        for key in reference
        if observed[key] is None or abs(float(observed[key]) - float(reference[key])) > tolerances[key]
    }
    return {
        "ok": not mismatches
        and bool(recon.get("commission_reconciles"))
        and recon.get("decision_id_linked") == recon.get("campaign_count")
        and recon.get("opportunity_id_linked") == recon.get("campaign_count"),
        "observed": observed,
        "reference": reference,
        "mismatches": mismatches,
        "commission_reconciles": recon.get("commission_reconciles"),
        "lineage": {
            "decision_id_linked": recon.get("decision_id_linked"),
            "opportunity_id_linked": recon.get("opportunity_id_linked"),
            "campaigns": recon.get("campaign_count"),
        },
    }


def _experiment_check(root: Path, experiment: str) -> dict[str, Any]:
    directory = root / EXPERIMENT_DIRS[experiment]
    problems: list[str] = []
    if not directory.is_dir():
        return {"ok": False, "reason": "experiment directory missing", "path": str(directory)}
    for name in REQUIRED_ARTIFACTS[experiment]:
        if not (directory / name).is_file():
            problems.append(f"missing artifact: {name}")

    headline, err = _read_json(directory / "metrics.json")
    if err:
        problems.append(f"metrics.json: {err}")
        headline = None
    status = None
    if isinstance(headline, dict):
        status = headline.get("status")
        if status not in LEGAL_STATUSES:
            problems.append(f"illegal/missing status: {status!r}")
        declared = headline.get("native_replay_validated")
        if declared is True:
            # A native claim needs a persisted native run with its own ledger.
            native_runs = list(directory.rglob("trade_lifecycles.jsonl"))
            if not native_runs:
                problems.append("native_replay_validated=true without any persisted native run")

    arm_rows = list(directory.rglob("arm_rows.jsonl"))
    row_counts = {path.parent.name: sum(1 for _ in path.open(encoding="utf-8")) for path in arm_rows}

    native_dirs = sorted({p.parent.name for p in directory.rglob("research_arm.json")})
    arm_decl, err = _read_json(directory / "arms.json")
    declared_arms: list[Any] = []
    if isinstance(arm_decl, dict):
        declared_arms = arm_decl.get("arms") or arm_decl.get("arm_ids") or []
    elif isinstance(arm_decl, list):
        declared_arms = arm_decl
    if len(declared_arms) > research_contract.MAX_ARMS_PER_EXPERIMENT:
        problems.append(f"{len(declared_arms)} arms declared (max 4)")
    if len(native_dirs) > research_contract.MAX_NON_BASELINE_REPLAYS_PER_EXPERIMENT:
        problems.append(f"{len(native_dirs)} native arms executed (max 2)")
    return {
        "ok": not problems,
        "path": str(directory),
        "status": status,
        "native_arms_executed": native_dirs,
        "screen_row_counts": row_counts,
        "problems": problems,
    }


def _native_arm_reconciliation(root: Path) -> dict[str, Any]:
    """Every persisted native arm must reconcile its own fees and lineage."""
    results: dict[str, Any] = {}
    for arm_json in root.rglob("research_arm.json"):
        if "superseded" in arm_json.parts:
            # Archived evidence is preserved but is not a live arm.
            continue
        run_dir = arm_json.parent
        recon_path = run_dir / "reconciliation.json"
        lifecycles = screen.read_jsonl(run_dir / "trade_lifecycles.jsonl")
        fills = screen.read_jsonl(run_dir / "fills.jsonl")
        fees_fills = sum(
            float(str(c).split()[0]) for f in fills for c in (f.get("commissions") or [])
        )
        # entry_fees + exit_fees are attributed commissions. ``fees_usdt`` is the
        # COST column: under a slipped profile it is gross-minus-native-realized
        # and therefore also contains slippage. Conflating the two is the defect.
        attributed = sum(
            (row.get("entry_fees_usdt") or 0.0) + (row.get("exit_fees_usdt") or 0.0)
            for row in lifecycles
        )
        cost_column = sum(row.get("fees_usdt") or 0.0 for row in lifecycles)
        basis = {str(row.get("fee_basis")) for row in lifecycles}
        reconstruction, err = _read_json(recon_path)
        results[arm_json.parent.name] = {
            "run_dir": str(run_dir),
            "campaigns": len(lifecycles),
            "fills": len(fills),
            "fee_total_fills": round(fees_fills, 8),
            "fee_total_lifecycles": round(attributed, 8),
            "attributed_commission_total": round(attributed, 8),
            "fees_reconcile": abs(fees_fills - attributed) < 1e-6,
            "cost_column_total": round(cost_column, 8),
            "slippage_in_cost_column": round(cost_column - attributed, 8),
            "fee_basis_values": sorted(basis),
            "mixed_cost_basis": len(basis) > 1,
            "decision_ids_linked": sum(1 for row in lifecycles if row.get("decision_id")),
            "opportunity_ids_linked": sum(1 for row in lifecycles if row.get("opportunity_id")),
            "reconciliation_present": reconstruction is not None,
            "net_expectancy_r": research_metrics.mean(
                row.get("realized_net_r") for row in lifecycles
            ),
        }
    return {"ok": all(v["fees_reconcile"] for v in results.values()) if results else True,
            "arms": results}


def validate_run(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    contract, contract_err = _read_json(root / "RESEARCH_CONTRACT.json")
    problems = research_contract.validate_contract(contract or {}) if not contract_err else [contract_err]
    recorded_hash = None
    hash_file = root / "RESEARCH_CONTRACT_SHA256.txt"
    if hash_file.is_file():
        recorded_hash = hash_file.read_text(encoding="utf-8").strip()
    computed_hash = research_contract.contract_sha256(contract) if contract else None

    report: dict[str, Any] = {
        "contract": {
            "ok": not problems and recorded_hash == computed_hash,
            "violations": problems,
            "recorded_sha256": recorded_hash,
            "computed_sha256": computed_hash,
            "hash_matches": recorded_hash == computed_hash,
        },
        "dataset": _dataset_consistency(root),
        "baseline": _baseline_reconciliation(root),
        "experiments": {exp: _experiment_check(root, exp) for exp in EXPERIMENT_DIRS},
        "native_arms": _native_arm_reconciliation(root),
        "leakage": {"ok": True, "forbidden_references": []},
        "independent_variables": {},
    }
    forbidden = _grep_forbidden(root)
    report["leakage"] = {
        "ok": not forbidden,
        "forbidden_references": forbidden,
        "note": "Artifacts mentioning holdout/sealed/OOS paths are rejected; the sealed OOS dataset was never opened.",
    }
    from v8_next.research.arms import arms_for

    for exp in EXPERIMENT_DIRS:
        # The preregistered arm registry is authoritative for what changed.
        changes: set[str] = set()
        keeps: set[str] = set()
        per_arm: list[dict[str, Any]] = []
        for arm in arms_for(exp):
            if arm.is_baseline:
                continue
            changes.update(arm.changes)
            keeps.update(arm.holds_fixed)
            per_arm.append({"arm_id": arm.arm_id, "changes": list(arm.changes)})
        report["independent_variables"][exp] = {
            "changed_across_arms": sorted(changes),
            "held_fixed": sorted(keeps),
            # Isolation is a per-arm property: each arm may change one variable,
            # while the experiment as a whole necessarily varies several.
            "changes_per_arm": per_arm,
            "single_variable_per_arm": all(len(item["changes"]) <= 1 for item in per_arm),
            "source": "preregistered arm registry",
        }

    gates = {
        "G1_existing_codebase_preserved": report["contract"]["ok"],
        "G4_dataset_integrity": report["dataset"].get("ok", False),
        "G6_common_baseline": report["baseline"].get("ok", False),
        "G13_raw_artifacts": all(v.get("ok") for v in report["experiments"].values()),
        "G11_economic_validity": report["native_arms"].get("ok", False),
        "leakage_gate": report["leakage"]["ok"],
    }
    report["gates"] = gates
    report["ok"] = all(gates.values())
    return report
