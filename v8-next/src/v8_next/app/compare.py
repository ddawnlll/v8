"""Compare a complete recorded DEVELOPMENT family; never grant economic authority."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from v8_next.evaluation.family import compare_family
from v8_next.evaluation.overfitting import CSCVPlan
from v8_next.evaluation.store import ResearchStore, canonical


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--family", required=True)
    parser.add_argument("--baseline", required=True, help="Registered baseline trial ID")
    parser.add_argument("--block-size", required=True, type=int)
    parser.add_argument("--reps", required=True, type=int)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--pbo-plan", type=Path, help="Explicit CSCV JSON plan; baseline excluded")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("comparison output already exists")
    if not args.store.is_file():
        raise ValueError("existing research registry required")
    records = []
    inputs = []
    for path in args.results:
        raw = path.read_bytes()
        records.append(json.loads(raw))
        inputs.append({"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()})
    pbo_plan = None
    if args.pbo_plan is not None:
        raw = args.pbo_plan.read_bytes()
        plan = json.loads(raw)
        if set(plan) != {"partitions", "metric", "max_splits", "registered_variants"}:
            raise ValueError("PBO plan requires exactly the documented fields")
        if (
            type(plan["partitions"]) is not int
            or type(plan["max_splits"]) is not int
            or plan["metric"] not in {"mean_return", "sharpe"}
            or not isinstance(plan["registered_variants"], list)
            or any(not isinstance(v, str) or not v for v in plan["registered_variants"])
        ):
            raise ValueError("invalid typed PBO plan")
        pbo_plan = CSCVPlan(
            plan["partitions"],
            plan["metric"],
            plan["max_splits"],
            tuple(plan["registered_variants"]),
        )
        inputs.append(
            {"path": str(args.pbo_plan.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    store = ResearchStore(args.store)
    try:
        decision_ns = time.time_ns()
        report = compare_family(
            records,
            store=store,
            family=args.family,
            baseline_trial_id=args.baseline,
            decision_ns=decision_ns,
            block_size=args.block_size,
            reps=args.reps,
            seed=args.seed,
            pbo_plan=pbo_plan,
        )
        report["inputs"] = inputs
        report["decision_ns"] = decision_ns
        serialized = canonical(report)
        with args.output.open("x") as stream:
            stream.write(serialized + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
