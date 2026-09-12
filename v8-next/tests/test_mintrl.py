"""MECHANICS ONLY: declared MinTRL arithmetic and refusal semantics."""

from v8_next.evaluation.mintrl import MinTRLPlan, estimate_min_trl


def test_mintrl_requires_declared_plan() -> None:
    result = estimate_min_trl(None, 10)
    assert result.status == "UNSUPPORTED"
    assert result.required_intervals is None


def test_mintrl_is_deterministic_and_dependence_sensitive() -> None:
    base = MinTRLPlan(
        target_sharpe=1.0,
        null_sharpe=0.0,
        confidence=0.95,
        power=0.8,
        variance=1.0,
        dependence_factor=1.0,
        interval_unit="daily",
        annualization_factor=252.0,
        method_version="mintrl.v1",
    )
    dependent = base.model_copy(update={"dependence_factor": 2.0})
    first = estimate_min_trl(base, 1)
    second = estimate_min_trl(base, 1)
    assert first == second
    assert first.status == "UNDERPOWERED"
    assert estimate_min_trl(dependent, 1).required_intervals > first.required_intervals
