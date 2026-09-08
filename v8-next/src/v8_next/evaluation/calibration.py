"""Inspect actual prospective accounting evidence before permitting calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from v8_next.adapters.accounting_replay import replay_frozen_campaigns
from v8_next.adapters.engine_state import reconcile_replay
from v8_next.app.evaluate import evaluate
from v8_next.app.paper import replay_account
from v8_next.domain.campaign import PaperCampaign


def inspect_calibration_source(run: Path, decision_ns: int) -> dict[str, Any]:
    """Recompute source accounting; never trust a serialized verified flag.

    This is evidence admission, not an estimator or a certificate issuer. No
    forecast value is produced until a complete eligible outcome sample exists.
    """
    evaluation = evaluate(run)
    frozen = json.loads((run / "policy.json").read_text())
    checkpoint = json.loads((run / "paper-state.json").read_text())
    if checkpoint["policy_hash"] != evaluation["policy_hash"]:
        raise ValueError("accounting belongs to another policy")
    revised = checkpoint["revised_accounting"]
    cutoff = int(revised["accounting_as_of_ns"])
    if cutoff >= decision_ns:
        raise ValueError("calibration evidence reaches decision time or future")
    paths = []
    for name, expected_hash in zip(
        checkpoint["manifests"], checkpoint["manifest_hashes"], strict=True
    ):
        path = (run / name).resolve()
        if not path.is_relative_to(run.resolve()):
            raise ValueError("calibration source escapes run")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("calibration source hash mismatch")
        paths.append(path)
    recovered_decisions = replay_account(paths, frozen["policy"]["paper_config"])
    reconcile_replay(checkpoint["native_state"], recovered_decisions)
    campaigns = tuple(
        PaperCampaign.from_record(c)
        for c in recovered_decisions["campaigns"]
    )
    recomputed = replay_frozen_campaigns(paths, campaigns, frozen["policy"]["paper_config"], cutoff)
    reconcile_replay(revised, recomputed)
    positions = recomputed["positions"]
    closed = [p for p in positions if p["is_closed"]]
    if any(
        p["closed_ns"] is None or not p["opened_ns"] <= p["closed_ns"] <= cutoff for p in closed
    ):
        raise ValueError("closed outcome has invalid accounting clocks")
    if not positions:
        reason = "NO_EXECUTED_OUTCOME_SAMPLE"
    elif not closed:
        reason = "NO_CLOSED_OUTCOME_SAMPLE"
    elif recomputed["funding_coverage"] != "COMPLETE":
        reason = "FUNDING_COVERAGE_UNQUALIFIED"
    else:
        reason = "STATISTICAL_METHOD_AND_TRIAL_FAMILY_REVIEW_REQUIRED"
    return {
        "claim_status": "NO_ECONOMIC_CLAIM",
        "source_policy_hash": evaluation["policy_hash"],
        "source_checkpoint_sha256": hashlib.sha256(
            (run / "paper-state.json").read_bytes()
        ).hexdigest(),
        "accounting_recomputed": True,
        "campaign_decisions_recomputed": True,
        "position_records": len(positions),
        "closed_position_records": len(closed),
        "open_position_records": len(positions) - len(closed),
        "outcome_realization": recomputed["realization"],
        "funding_coverage": recomputed["funding_coverage"],
        "closed_outcomes": sorted(closed, key=lambda p: (p["closed_ns"], p["instrument_id"])),
        "eligible_for_utility": False,
        "reason": reason,
        "gross_edge": None,
        "uncertainty": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--decision-ns", type=int, required=True)
    args = parser.parse_args()
    result = inspect_calibration_source(args.run_directory, args.decision_ns)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
