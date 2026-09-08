from decimal import Decimal

import pytest

from v8_next.evaluation.alignment import IntervalLoss
from v8_next.evaluation.inference import spa_diagnostic


def test_spa_is_repeatable_and_never_promotes_test_fixture():
    pytest.importorskip("arch")
    baseline = tuple(IntervalLoss(i, i + 1, i + 1, Decimal(i % 3)) for i in range(30))
    variant = tuple(IntervalLoss(i, i + 1, i + 1, Decimal(i % 5)) for i in range(30))
    kwargs = dict(frozen_ns=0, evaluation_end_ns=30, decision_ns=31, block_size=3, reps=99, seed=7)
    result = spa_diagnostic(baseline, {"test-only": variant}, **kwargs)
    assert result == spa_diagnostic(baseline, {"test-only": variant}, **kwargs)
    cloned = spa_diagnostic(baseline, {"test-only": variant, "same-feed": variant}, **kwargs)
    assert cloned["pvalues"] == result["pvalues"]
    assert set(result["pvalues"]) == {"lower", "consistent", "upper"}
    assert all(0 <= v <= 1 for v in result["pvalues"].values())
    assert not result["promotion_eligible"]
    assert result["wrc"] is result["dsr"] is result["pbo"] is None
    with pytest.raises(ValueError, match="degenerate"):
        spa_diagnostic(baseline, {"clone": baseline}, **kwargs)


def test_trajectory_spa_preserves_missingness_and_exploratory_scope():
    from v8_next.evaluation.inference import trajectory_spa_diagnostic

    rows = [
        {
            "start_ns": i,
            "end_ns": i + 1,
            "breakout_baseline": {"incremental_cash_return": str(i % 3)},
            "squeeze": {"incremental_cash_return": str(i % 5)},
        }
        for i in range(30)
    ]
    kwargs = dict(decision_ns=31, block_size=3, reps=99, seed=7)
    rows[0]["squeeze"]["incremental_cash_return"] = None
    missing = trajectory_spa_diagnostic({"rows": rows}, **kwargs)
    assert missing["status"] == "MISSING_CASH_INTERVAL_NO_IMPUTATION"
    assert missing["result"] is None
    rows[0]["squeeze"]["incremental_cash_return"] = "0"
    pytest.importorskip("arch")
    result = trajectory_spa_diagnostic({"rows": rows}, **kwargs)
    assert result["status"] == "COMPUTED_EXPLORATORY_NOT_QUALIFIED"
    assert result["preregistration"] == "NOT_VERIFIED_EXPLORATORY_ONLY"
    assert result["promotion_eligible"] is False
    for row in rows:
        row["squeeze"] = row["breakout_baseline"].copy()
    flat = trajectory_spa_diagnostic({"rows": rows}, **kwargs)
    assert flat["status"] == "DEGENERATE_DIFFERENTIAL_NO_PVALUE"
    assert flat["result"] is None
