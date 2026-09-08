"""Joint native outcome-component estimates; not a calibrated utility provider."""

import hashlib
import importlib
import importlib.metadata
from decimal import Decimal
from typing import Any

import numpy as np

from v8_next.evaluation.store import canonical

FIELDS = (
    "price_return_on_entry_notional",
    "commission_fraction",
    "funding_return_on_entry_notional",
    "other_adjustment_return_on_entry_notional",
)


def estimate_components(
    outcomes: dict[str, Any], *, decision_ns: int, block_size: int, reps: int, seed: int
) -> dict[str, Any]:
    result: dict[str, Any] = dict(
        scope="NATIVE_MODEL_COHORT_COMPONENTS_NOT_EXPECTED_UTILITY",
        claim_status="NO_ECONOMIC_CLAIM",
        eligible_for_utility=False,
        estimates=None,
        source_sha256=hashlib.sha256(canonical(outcomes).encode()).hexdigest(),
    )
    rows = outcomes["rows"]
    if not rows or any(r["status"] != "CLOSED_UNDER_NATIVE_MODEL" for r in rows):
        return {**result, "reason": "COMPLETE_CLOSED_COHORT_REQUIRED"}
    if outcomes["reconciliation"] != "CLOSED_CASH_RECONCILED":
        return {**result, "reason": "RECONCILED_COHORT_REQUIRED"}
    if any(any(r.get(k) is None for k in FIELDS) for r in rows):
        return {**result, "reason": "COMPONENTS_UNAVAILABLE"}
    if len({r["campaign_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate component sample")
    if not 1 <= block_size < len(rows) or reps < 2 or seed < 0:
        raise ValueError("invalid component resampling plan")
    ordered = sorted(rows, key=lambda r: (r["opened_ns"], r["closed_ns"], r["campaign_id"]))
    values = []
    for row in ordered:
        if not row["opened_ns"] <= row["closed_ns"] <= row["observed_ns"] < decision_ns:
            raise ValueError("component evidence reaches future")
        vector = [Decimal(row[k]) for k in FIELDS]
        net = Decimal(row["net_return_on_entry_notional"])
        if any(not v.is_finite() for v in (*vector, net)) or vector[1] < 0:
            raise ValueError("invalid component value")
        amounts = [
            Decimal(row[k])
            for k in (
                "native_price_pnl",
                "observed_commissions",
                "observed_funding_pnl",
                "observed_other_adjustment_pnl",
                "native_net_pnl",
            )
        ]
        notional = Decimal(row["entry_notional"])
        if not notional.is_finite() or notional <= 0 or any(not v.is_finite() for v in amounts):
            raise ValueError("invalid component cash amounts")
        if amounts[0] - amounts[1] + amounts[2] + amounts[3] != amounts[4]:
            raise ValueError("component cash arithmetic does not reconcile")
        if [v / notional for v in amounts] != [*vector, net]:
            raise ValueError("component fractions do not match native cash amounts")
        values.append([float(v) for v in (*vector, net)])
    matrix = np.asarray(values)
    if not np.isfinite(matrix).all():
        raise ValueError("component conversion overflow")
    bootstrap = importlib.import_module("arch.bootstrap")
    sampler = bootstrap.CircularBlockBootstrap(block_size, matrix, seed=seed)
    means = np.asarray([positional[0].mean(axis=0) for positional, _ in sampler.bootstrap(reps)])
    standard_errors = means.std(axis=0, ddof=1)
    if not np.isfinite(standard_errors).all():
        raise ValueError("nonfinite component uncertainty")
    names = (*FIELDS, "net_return_on_entry_notional")
    return {
        **result,
        "reason": "METHOD_AND_OUT_OF_SAMPLE_QUALIFICATION_REQUIRED",
        "sample_count": len(rows),
        "block_size": block_size,
        "reps": reps,
        "seed": seed,
        "method": "JOINT_CIRCULAR_BLOCK_MEAN_BY_CAMPAIGN_ENTRY_ORDER",
        "library_version": importlib.metadata.version("arch"),
        "numpy_version": np.__version__,
        "weighting": "equal_weight_per_selected_closed_campaign",
        "estimates": {
            name: dict(mean=float(mean), mean_standard_error=float(se))
            for name, mean, se in zip(names, matrix.mean(axis=0), standard_errors, strict=True)
        },
        "limitations": [
            "execution_and_completion_conditioned_sample",
            "native_cost_model_not_measured_market_impact",
            "no_search_adjustment_or_holdout_certification",
            "event_order_blocks_not_calendar_time_blocks",
        ],
    }
