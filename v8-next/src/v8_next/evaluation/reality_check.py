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
    bootstrap: str = "circular",
) -> dict[str, Any]:
    """Match legacy compound-null/tail semantics, not legacy RNG sequences.

    Supports both stationary bootstrap (Politis & Romano 1994) and circular block
    bootstrap via arch.bootstrap. All candidates share each library-generated draw.
    Each mean is recentered on its own observed mean before the family maximum;
    exceedance includes ties. Aligned loss differences, not concatenated variant trade lists.
    """
    if not variants or not 1 <= block_size < len(baseline) or reps < 2 or seed < 0:
        raise ValueError("explicit valid bootstrap plan and nonempty family required")
    if bootstrap not in {"circular", "stationary"}:
        raise ValueError(f"unsupported bootstrap '{bootstrap}', choose from 'circular', 'stationary'")
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
    bootstrap_mod = importlib.import_module("arch.bootstrap")

    if bootstrap == "stationary":
        sampler = bootstrap_mod.StationaryBootstrap(block_size, matrix, seed=seed)
        bootstrap_name = "stationary_geometric_block_joint_columns"
        library_name = "arch.bootstrap.StationaryBootstrap"
        uncertainty_method = "sample_sd_of_joint_stationary_block_means_ddof_1"
        method_name = "WHITE_MAX_MEAN_STATIONARY_BOOTSTRAP_V2"
    else:
        sampler = bootstrap_mod.CircularBlockBootstrap(block_size, matrix, seed=seed)
        bootstrap_name = "circular_fixed_block_joint_columns"
        library_name = "arch.bootstrap.CircularBlockBootstrap"
        uncertainty_method = "sample_sd_of_joint_circular_block_means_ddof_1"
        method_name = "WHITE_MAX_MEAN_CIRCULAR_BLOCK_V2"

    exceed = 0
    draw_means = []
    for positional, _ in sampler.bootstrap(reps):
        draw_mean = positional[0].mean(axis=0)
        draw_means.append(draw_mean)
        null_max = float(np.max(draw_mean - means))
        exceed += int(null_max >= observed)
    standard_errors = np.std(np.asarray(draw_means), axis=0, ddof=1)
    if not np.isfinite(standard_errors).all():
        raise ValueError("nonfinite bootstrap mean uncertainty")

    # Direct arch.bootstrap.RealityCheck execution when available
    arch_rc: dict[str, Any] | None = None
    if hasattr(bootstrap_mod, "RealityCheck"):
        try:
            benchmark = np.asarray([float(r.loss) for r in baseline if r.loss is not None])
            models = np.column_stack(
                [
                    np.asarray([float(r.loss) for r in variants[name] if r.loss is not None])
                    for name in names
                ]
            )
            rc_instance = bootstrap_mod.RealityCheck(
                benchmark,
                models,
                block_size=block_size,
                reps=reps,
                bootstrap=bootstrap,
                studentize=False,
                seed=seed,
            )
            rc_instance.compute()
            arch_rc = {
                "method": "arch.bootstrap.RealityCheck",
                "pvalues": {str(k): float(v) for k, v in rc_instance.pvalues.items()},
                "upper_wrc_pvalue": float(rc_instance.pvalues["upper"]),
                "consistent_pvalue": float(rc_instance.pvalues["consistent"]),
                "lower_pvalue": float(rc_instance.pvalues["lower"]),
            }
        except Exception:
            arch_rc = None

    return {
        "effect_estimates": {
            name: {
                "mean_baseline_minus_variant_loss": float(means[index]),
                "bootstrap_mean_standard_error": float(standard_errors[index]),
            }
            for index, name in enumerate(names)
        },
        "effect_units": "same_as_input_interval_loss",
        "effect_scope": "IN_SAMPLE_BASELINE_RELATIVE_NOT_GROSS_EDGE_OR_UTILITY",
        "uncertainty_method": uncertainty_method,
        "method": method_name,
        "library": library_name,
        "library_version": importlib.metadata.version("arch"),
        "numpy_version": np.__version__,
        "null": "no_variant_has_positive_expected_baseline_minus_variant_loss",
        "centering": "each_variant_own_observed_mean",
        "bootstrap": bootstrap_name,
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
        "arch_reality_check": arch_rc,
        "claim_status": "NO_ECONOMIC_CLAIM",
        "promotion_eligible": False,
        "evidence_scope": "NUMERICAL_DIAGNOSTIC_WITHOUT_SOURCE_OR_HOLDOUT_CERTIFICATION",
    }
