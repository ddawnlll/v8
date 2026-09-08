"""Optional arch SPA calculation; no certification or utility authorization."""

import importlib
import importlib.metadata
from typing import Any

import numpy as np

from v8_next.evaluation.alignment import IntervalLoss, paired_differentials


def spa_diagnostic(
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
    """Stationary bootstrap, studentized SPA, all columns resampled jointly.

    Caller owns preregistration, complete search-family provenance, loss definition
    and source admissibility. This function cannot establish them from numbers.
    """
    if not variants or not 1 <= block_size < len(baseline) or reps < 2 or seed < 0:
        raise ValueError("explicit valid bootstrap plan and nonempty family required")
    names = sorted(variants)
    for name in names:
        paired_differentials(
            baseline,
            variants[name],
            frozen_ns=frozen_ns,
            evaluation_end_ns=evaluation_end_ns,
            decision_ns=decision_ns,
        )
    benchmark = np.array([float(r.loss) for r in baseline if r.loss is not None])
    models = np.array(
        [[float(r.loss) for r in variants[name] if r.loss is not None] for name in names]
    ).T
    differences = benchmark[:, None] - models
    if not np.isfinite(differences).all() or np.any(np.std(differences, axis=0) == 0):
        raise ValueError("nonfinite or degenerate loss differentials")
    arch = importlib.import_module("arch")
    bootstrap = importlib.import_module("arch.bootstrap")
    test = bootstrap.SPA(
        benchmark,
        models,
        block_size=block_size,
        reps=reps,
        bootstrap="stationary",
        studentize=True,
        nested=False,
        seed=seed,
    )
    test.compute()
    pvalues = {str(k): float(v) for k, v in test.pvalues.items()}
    if any(not np.isfinite(v) or not 0 <= v <= 1 for v in pvalues.values()):
        raise ValueError("invalid library inference output")
    return {
        "claim_status": "NO_ECONOMIC_CLAIM",
        "method": "arch.SPA",
        "library_version": arch.__version__,
        "dependency_versions": {
            name: importlib.metadata.version(name)
            for name in ("arch", "numpy", "scipy", "pandas", "statsmodels")
        },
        "sample_intervals": len(baseline),
        "null": "no_variant_has_positive_expected_baseline_minus_variant_loss",
        "evidence_scope": "NUMERICAL_DIAGNOSTIC_WITHOUT_SOURCE_OR_HOLDOUT_CERTIFICATION",
        "bootstrap": "stationary",
        "studentize": True,
        "nested": False,
        "block_size": block_size,
        "reps": reps,
        "seed": seed,
        "variants": names,
        "pvalues": pvalues,
        "wrc": None,
        "dsr": None,
        "pbo": None,
        "promotion_eligible": False,
    }
