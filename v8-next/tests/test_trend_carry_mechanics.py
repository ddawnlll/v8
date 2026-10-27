"""MECHANICS ONLY: synthetic panels test accounting and causality, zero evaluative weight."""

import numpy as np
import pytest

from v8_next.economics import trend_carry as tc

DAY_NS = 86_400 * 10**9


def _panel(close: np.ndarray, funding: np.ndarray | None = None) -> tc.Panel:
    t, n = close.shape
    return tc.Panel(
        np.arange(t, dtype=np.int64) * DAY_NS,
        tuple(f"S{i}" for i in range(n)),
        close,
        np.zeros_like(close) if funding is None else funding,
    )


def _walk(t: int, n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(rng.normal(0, 0.03, (t, n)), axis=0))


def test_weight_decided_at_close_cannot_earn_that_days_return() -> None:
    close = np.ones((5, 1)) * 100
    close[3:] = 200  # jump realised on day 3
    w = np.zeros((5, 1))
    w[3] = 1.0  # decided after observing day-3 close
    sim = tc.simulate(_panel(close), w, cost_per_turnover=0.0)
    assert sim.gross[3] == 0.0 and sim.gross.sum() == 0.0
    w[2] = 1.0  # decided before the jump
    assert tc.simulate(_panel(close), w, cost_per_turnover=0.0).gross[3] == pytest.approx(1.0)


def test_same_bar_execution_is_refused() -> None:
    close = np.ones((3, 1))
    with pytest.raises(ValueError):
        tc.simulate(_panel(close), np.zeros((3, 1)), cost_per_turnover=0.0, lag=0)


def test_long_pays_positive_funding_and_turnover_pays_cost() -> None:
    close = np.ones((4, 2)) * 100
    funding = np.full((4, 2), 0.001)
    w = np.zeros((4, 2))
    w[0:2] = [1.0, -1.0]
    sim = tc.simulate(_panel(close, funding), w, cost_per_turnover=0.0005)
    assert sim.funding[1] == pytest.approx(0.0)  # long pays, short receives
    w[0:2] = [1.0, 0.0]
    sim = tc.simulate(_panel(close, funding), w, cost_per_turnover=0.0005)
    assert sim.funding[1] == pytest.approx(-0.001)
    assert sim.turnover.tolist() == [0.0, 1.0, 0.0, 1.0]
    assert sim.cost[1] == pytest.approx(0.0005)


def test_xs_rank_bounds_and_minimum_cross_section() -> None:
    x = np.array([[1.0, 2, 3, 4, 5, 6], [1.0, 2, 3, 4, 5, np.nan]])
    valid = np.ones_like(x, dtype=bool)
    r = tc.xs_rank(x, valid)
    assert r[0].tolist() == pytest.approx([-1, -0.6, -0.2, 0.2, 0.6, 1])
    assert np.isnan(r[1]).all()


def test_hold_keeps_weights_between_rebalances() -> None:
    w = np.arange(6, dtype=float).reshape(6, 1)
    assert tc.hold(w, 3)[:, 0].tolist() == [0, 0, 0, 3, 3, 3]


def test_signals_ignore_future_data() -> None:
    close = _walk(400, 8)
    altered = close.copy()
    altered[300:] *= 3.0
    for name, fn in tc.SLEEVES.items():
        a, b = fn(_panel(close)), fn(_panel(altered))
        assert np.allclose(a[:300], b[:300]), name


def test_portfolio_scales_use_in_sample_only() -> None:
    close = _walk(500, 8, seed=1)
    funding = np.random.default_rng(2).normal(0, 1e-4, close.shape)
    ins = np.arange(500) < 350
    altered = close.copy()
    altered[400:] *= np.linspace(1, 2, 100)[:, None]
    _, s1 = tc.portfolio_weights(_panel(close, funding), ins, cost_per_turnover=0.0007)
    _, s2 = tc.portfolio_weights(_panel(altered, funding), ins, cost_per_turnover=0.0007)
    assert s1 == pytest.approx(s2)


def test_summary_drawdown_and_sharpe_arithmetic() -> None:
    daily = np.array([0.01, -0.02, 0.01, 0.02])
    s = tc.summary(daily)
    assert s["max_drawdown"] == pytest.approx(-0.02)
    assert s["sharpe_annualised"] == pytest.approx(daily.mean() / daily.std(ddof=1) * np.sqrt(365))
