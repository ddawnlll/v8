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
