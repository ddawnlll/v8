"""Read-only paper report with recomputed decision and accounting provenance."""

import argparse
import json
from pathlib import Path
from typing import Any

from v8_next.app.evaluate import evaluate
from v8_next.evaluation.calibration import inspect_calibration_source


def report(run: Path, decision_ns: int) -> dict[str, Any]:
    observations = evaluate(run)
    outcomes = inspect_calibration_source(run, decision_ns)
    return {
        "schema_version": 1,
        "claim_status": "NO_ECONOMIC_CLAIM",
        "observations": observations,
        "outcomes": outcomes,
        "comparison": {
            "status": "NOT_COMPUTED",
            "reason": outcomes["reason"],
            "paired_loss_sample": None,
            "spa": None,
            "wrc": None,
            "dsr": None,
            "pbo": None,
            "additional_requirement": "verified_aligned_baseline_and_variant_account_intervals",
        },
        "promotion_eligible": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--decision-ns", type=int, required=True)
    args = parser.parse_args()
    result = report(args.run_directory, args.decision_ns)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
