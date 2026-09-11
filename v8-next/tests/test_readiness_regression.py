"""Regression gate for the locked benchmark: a drop is reported, never re-baselined away."""

from __future__ import annotations

from v8_next.app.readiness import REGRESSION_TOLERANCES, regression_against

BASE = {
    "readiness": 12.5,
    "gate_passes": 5,
    "pillars_measured": 3,
    "per_policy": {
        "plain_swing": {"net_measured_sum": -0.5, "win_rate_pct": 10.0, "campaigns": 100},
    },
}


def test_identical_state_is_ok() -> None:
    result = regression_against(BASE, BASE)
    assert result["verdict"] == "OK"
    assert not result["regressions"]


def test_an_improvement_is_ok_and_recorded() -> None:
    better = {
        **BASE,
        "readiness": 18.0,
        "gate_passes": 6,
        "per_policy": {"plain_swing": {"net_measured_sum": -0.4, "win_rate_pct": 12.0}},
    }
    result = regression_against(BASE, better)
    assert result["verdict"] == "OK"
    deltas = {row["metric"]: row["delta"] for row in result["findings"]}
    assert deltas["readiness"] == 5.5 and deltas["gate_passes"] == 1


def test_a_dropped_gate_is_a_regression() -> None:
    worse = {**BASE, "gate_passes": 4}
    result = regression_against(BASE, worse)
    assert result["verdict"] == "REGRESSION"
    assert any("gate_passes" in line for line in result["regressions"])


def test_a_dropped_score_is_a_regression_even_within_float_noise() -> None:
    worse = {**BASE, "readiness": 12.49}
    result = regression_against(BASE, worse)
    assert result["verdict"] == "REGRESSION"


def test_tolerances_bound_the_paper_trade_metrics() -> None:
    marginal = {
        **BASE,
        "per_policy": {"plain_swing": {"net_measured_sum": -0.5004, "win_rate_pct": 10.4}},
    }
    assert regression_against(BASE, marginal)["verdict"] == "OK"
    beyond = {
        **BASE,
        "per_policy": {"plain_swing": {"net_measured_sum": -0.51, "win_rate_pct": 9.0}},
    }
    result = regression_against(BASE, beyond)
    assert result["verdict"] == "REGRESSION"
    assert len(result["regressions"]) == 2


def test_a_missing_policy_is_a_regression() -> None:
    result = regression_against(BASE, {**BASE, "per_policy": {}})
    assert result["verdict"] == "REGRESSION"
    assert "missing" in result["regressions"][0]


def test_tolerances_are_declared_not_implicit() -> None:
    assert set(REGRESSION_TOLERANCES) == {
        "readiness", "gate_passes", "pillars_measured", "net_measured_sum", "win_rate_pct",
    }
    assert REGRESSION_TOLERANCES["readiness"] == 0.0
