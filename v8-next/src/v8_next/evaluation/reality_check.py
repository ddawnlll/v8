"""White family max-mean diagnostic using arch's circular block resampler."""

import importlib
import importlib.metadata
from typing import Any

import numpy as np

from v8_next.evaluation.alignment import IntervalLoss, paired_differentials


def reality_check_diagnostic(
    baseline: tuple[IntervalLoss, ...],
    variants: dict[str, tuple[IntervalLoss, ...]],
    *,
    frozen_ns: int,
    evaluation_end_ns: int,
    decision_ns: int,
    block_size: int,
    reps: int,
    seed: int,
) -> dict[str, Any]:
    """Match legacy compound-null/tail semantics, not legacy RNG sequences.

    All candidates share each library-generated draw. Each mean is recentered
    on its own observed mean before the family maximum; exceedance includes ties.
    These are aligned loss differences, not concatenated variant trade lists.
    """
    if not variants or not 1 <= block_size < len(baseline) or reps < 2 or seed < 0:
        raise ValueError("explicit valid bootstrap plan and nonempty family required")
    names = sorted(variants)
    matrix = np.column_stack(
        [
            np.asarray(
                paired_differentials(
                    baseline,
                    variants[name],
                    frozen_ns=frozen_ns,
                    evaluation_end_ns=evaluation_end_ns,
                    decision_ns=decision_ns,
                ),
                dtype=float,
            )
            for name in names
        ]
    )
    if not np.isfinite(matrix).all() or np.all(np.std(matrix, axis=0) == 0):
        raise ValueError("nonfinite or degenerate loss differentials")
    means = matrix.mean(axis=0)
    observed = float(np.max(means))
    bootstrap = importlib.import_module("arch.bootstrap")
    sampler = bootstrap.CircularBlockBootstrap(block_size, matrix, seed=seed)
    exceed = 0
    for positional, _ in sampler.bootstrap(reps):
        null_max = float(np.max(positional[0].mean(axis=0) - means))
        exceed += int(null_max >= observed)
    return {
        "method": "WHITE_MAX_MEAN_CIRCULAR_BLOCK_V2",
        "library": "arch.bootstrap.CircularBlockBootstrap",
        "library_version": importlib.metadata.version("arch"),
        "numpy_version": np.__version__,
        "null": "no_variant_has_positive_expected_baseline_minus_variant_loss",
        "centering": "each_variant_own_observed_mean",
        "bootstrap": "circular_fixed_block_joint_columns",
        "tail": "greater_or_equal",
        "studentize": False,
        "sample_intervals": len(baseline),
        "variants": names,
        "observed_max": observed,
        "argmax_variant": names[int(np.argmax(means))],
        "tie_policy": "lexicographic_variant_id",
        "p_value": exceed / reps,
        "exceedances": exceed,
        "reps": reps,
        "block_size": block_size,
        "seed": seed,
        "claim_status": "NO_ECONOMIC_CLAIM",
        "promotion_eligible": False,
        "evidence_scope": "NUMERICAL_DIAGNOSTIC_WITHOUT_SOURCE_OR_HOLDOUT_CERTIFICATION",
    }
