"""CSCV selection-overfitting diagnostic over aligned negative-return losses."""

import importlib
import importlib.metadata
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Any, Literal

import numpy as np

from v8_next.evaluation.alignment import IntervalLoss, paired_differentials


@dataclass(frozen=True)
class CSCVPlan:
    partitions: int
    metric: Literal["mean_return", "sharpe"]
    max_splits: int
    registered_variants: tuple[str, ...]


def pbo_diagnostic(
    losses: dict[str, tuple[IntervalLoss, ...]],
    *,
    registered_variants: tuple[str, ...],
    frozen_ns: int,
    evaluation_end_ns: int,
    decision_ns: int,
    partitions: int,
    metric: Literal["mean_return", "sharpe"],
    max_splits: int,
) -> dict[str, Any]:
    """Caller declares loss = negative net return per equal-duration interval.

    This evaluates selection among precomputed strategies, not model fitting.
    Caller still owns complete search lineage and source/holdout admissibility.
    Tied training maxima share equal weight; test ranks use average ranks.
    """
    names = sorted(losses)
    if (
        len(names) < 2
        or len(set(registered_variants)) != len(registered_variants)
        or set(names) != set(registered_variants)
    ):
        raise ValueError("complete registered comparison family required")
    if metric not in {"mean_return", "sharpe"}:
        raise ValueError("explicit supported performance metric required")
    baseline = losses[names[0]]
    n = len(baseline)
    if partitions < 2 or partitions % 2 or n % partitions or n // 2 < 2:
        raise ValueError("even equal-sized CSCV partitions required without truncation")
    split_count = comb(partitions, partitions // 2)
    if max_splits < 1 or split_count > max_splits:
        raise ValueError("declared CSCV work budget exceeded; no sampled substitute")
    for name in names:
        paired_differentials(
            baseline,
            losses[name],
            frozen_ns=frozen_ns,
            evaluation_end_ns=evaluation_end_ns,
            decision_ns=decision_ns,
        )
    if len({r.end_ns - r.start_ns for r in baseline}) != 1:
        raise ValueError("equal-duration return intervals required")
    matrix = -np.asarray(
        [[float(r.loss) for r in losses[name] if r.loss is not None] for name in names]
    ).T
    if not np.isfinite(matrix).all():
        raise ValueError("nonfinite return matrix")
    if np.unique(matrix, axis=1).shape[1] != len(names):
        raise ValueError("identical performance columns need an explicit equivalence policy")
    stats = importlib.import_module("scipy.stats")
    blocks = np.arange(n).reshape(partitions, n // partitions)
    splits = []
    for selected in combinations(range(partitions), partitions // 2):
        other = [i for i in range(partitions) if i not in selected]
        train, test = matrix[blocks[list(selected)].ravel()], matrix[blocks[other].ravel()]
        train_score, test_score = train.mean(axis=0), test.mean(axis=0)
        if metric == "sharpe":
            train_sd, test_sd = train.std(axis=0, ddof=1), test.std(axis=0, ddof=1)
            if np.any(train_sd == 0) or np.any(test_sd == 0):
                raise ValueError("undefined Sharpe in CSCV split; cannot discard the split")
            train_score, test_score = train_score / train_sd, test_score / test_sd
        if not np.isfinite(train_score).all() or not np.isfinite(test_score).all():
            raise ValueError("nonfinite CSCV scores")
        winners = np.flatnonzero(train_score == np.max(train_score))
        relative_ranks = stats.rankdata(test_score, method="average")[winners] / (len(names) + 1)
        logits = np.log(relative_ranks / (1 - relative_ranks))
        splits.append(
            {
                "training_blocks": list(selected),
                "testing_blocks": other,
                "selected_variants": [names[i] for i in winners],
                "oos_relative_ranks": relative_ranks.tolist(),
                "logits": logits.tolist(),
                "overfit_weight": float(np.mean(logits <= 0)),
            }
        )
    return {
        "method": "CSCV_EQUAL_WEIGHT_TIES_V1",
        "metric": metric,
        "input_measure": "negative_net_period_return",
        "variants": names,
        "partitions": partitions,
        "split_count": split_count,
        "sample_intervals": n,
        "pbo": float(np.mean([s["overfit_weight"] for s in splits])),
        "splits": splits,
        "tie_policy": "equal_weight_IS_maxima_OOS_midranks_zero_logit_counts_as_overfit",
        "dependency_versions": {
            name: importlib.metadata.version(name) for name in ("numpy", "scipy")
        },
        "claim_status": "NO_ECONOMIC_CLAIM",
        "promotion_eligible": False,
        "lineage_status": "DECLARED_FAMILY_NOT_INDEPENDENTLY_CERTIFIED",
        "limitations": [
            "CSCV_not_forward_walk_forward",
            "no_purging_of_overlapping_trade_labels",
            "few_variants_or_partitions_limit_resolution",
            "not_a_profitability_test",
        ],
    }
