"""Detrended-null tests (D-045, METH-1 / EV_METHODS G-02, Aronson Appendix A).

The null "mean episode net_R <= 0" is only mean-zero for a no-skill rule on
DETRENDED data. On a trending tape a long-biased family with zero predictive
power earns positive expected net_R purely from position bias x trend, so an
uncentered gate is mis-centered and can pass noise.

These tests first REPRODUCE that bias (it must be visible, or the correction
would be untestable), then assert the same-exposure benchmark removes it.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from v8.statistics import (EpisodeExposure, appendix_a_invariant,
                           detrend_net_r, invariant_holds,
                           mean_log_drift_per_bar, passive_benchmark_r,
                           placebo_exposures)

DRIFT_PER_BAR = 0.0005          # ~0.05%/bar uptrend, the position-bias source
RISK_UNIT_FRAC = 0.01           # one R = 1% of entry price (ATR-like, scales)
HORIZON = 8                     # matches the pilots' expiry_bars


def _trending_closes(n: int = 4000, *, drift: float = DRIFT_PER_BAR,
                     noise: float = 0.004, seed: int = 11) -> list[float]:
    """Geometric uptrend with seeded noise. Deterministic; never a wall clock."""
    rng = random.Random(seed)
    price, out = 100.0, []
    for _ in range(n):
        price *= math.exp(drift + rng.gauss(0.0, noise))
        out.append(price)
    return out


def _mean(xs) -> float:
    return sum(xs) / len(xs)


def test_drift_estimate_recovers_the_generating_trend():
    """The centering constant must actually measure the window's drift."""
    closes = _trending_closes()
    assert mean_log_drift_per_bar(closes) == pytest.approx(DRIFT_PER_BAR,
                                                           abs=2e-4)
    assert mean_log_drift_per_bar([100.0]) == 0.0          # too short: no drift
    with pytest.raises(ValueError, match='non-positive close'):
        mean_log_drift_per_bar([100.0, 0.0])


def test_position_bias_is_real_and_scales_with_long_share():
    """Aronson's result reproduced: two ZERO-SKILL families differing only in
    long occupancy earn materially different raw net_R on a trending tape
    (90%-long 7.31%/yr vs 60%-long 1.78%/yr on his S&P sample). If this ever
    stops holding, the detrending correction is testing nothing."""
    closes = _trending_closes()
    mostly_long = _mean([e.net_r for e in placebo_exposures(
        closes, long_share=0.90, horizon_bars=HORIZON,
        risk_unit_frac=RISK_UNIT_FRAC, n_episodes=4000, seed=3)])
    mixed = _mean([e.net_r for e in placebo_exposures(
        closes, long_share=0.60, horizon_bars=HORIZON,
        risk_unit_frac=RISK_UNIT_FRAC, n_episodes=4000, seed=3)])
    assert mostly_long > 0.0                    # zero skill, still profitable
    assert mixed > 0.0
    assert mostly_long > mixed                  # bias scales with occupancy


def test_detrending_neutralises_the_placebo_at_every_occupancy():
    """The Appendix A invariant: after subtracting the same-exposure passive
    benchmark, a zero-skill family's mean net_R collapses toward 0 regardless
    of its long/short mix — which is what makes `mu_f <= 0` a true null."""
    closes = _trending_closes()
    drift = mean_log_drift_per_bar(closes)
    for long_share in (0.0, 0.5, 0.9, 1.0):
        placebo = placebo_exposures(closes, long_share=long_share,
                                    horizon_bars=HORIZON,
                                    risk_unit_frac=RISK_UNIT_FRAC,
                                    n_episodes=4000, seed=5)
        raw = _mean([e.net_r for e in placebo])
        detrended = _mean(detrend_net_r(placebo, drift))
        assert abs(detrended) < abs(raw) or abs(raw) < 1e-3
        # Residual is bounded but not exactly zero: the benchmark is
        # exp(mu*h) while a realised path is exp(sum of steps), and by
        # Jensen's inequality the noisy realisation sits slightly above it.
        assert abs(detrended) < 0.05, (
            f'long_share={long_share}: detrended mean {detrended} still '
            f'carries position bias (raw was {raw})')


def test_detrending_is_direction_symmetric():
    """Log-space subtraction must treat LONG and SHORT as mirror images; a
    simple-return benchmark would over-correct one side (Ch1 p28-29)."""
    closes = _trending_closes()
    drift = mean_log_drift_per_bar(closes)
    long_b = passive_benchmark_r(EpisodeExposure(
        net_r=0.0, direction='LONG', entry_price=100.0,
        risk_unit_price=100.0 * RISK_UNIT_FRAC, horizon_bars=HORIZON), drift)
    short_b = passive_benchmark_r(EpisodeExposure(
        net_r=0.0, direction='SHORT', entry_price=100.0,
        risk_unit_price=100.0 * RISK_UNIT_FRAC, horizon_bars=HORIZON), drift)
    assert long_b > 0.0                          # uptrend rewards passive long
    assert short_b == pytest.approx(-long_b)


def test_detrending_is_a_noop_on_a_driftless_window():
    """Centering a window with no trend must not move the series — otherwise
    the correction would manufacture signal where there was no bias."""
    closes = _trending_closes(drift=0.0, seed=23)
    drift = mean_log_drift_per_bar(closes)
    placebo = placebo_exposures(closes, long_share=0.9, horizon_bars=HORIZON,
                                risk_unit_frac=RISK_UNIT_FRAC, n_episodes=2000,
                                seed=5)
    raw = _mean([e.net_r for e in placebo])
    detrended = _mean(detrend_net_r(placebo, drift))
    assert abs(detrended - raw) < 0.02


def test_detrending_fails_closed_without_a_recorded_r_unit():
    """An episode with no recorded R unit cannot be centered; passing its raw
    net_R through would silently reintroduce the uncentered null."""
    bad = EpisodeExposure(net_r=1.0, direction='LONG', entry_price=100.0,
                          risk_unit_price=0.0, horizon_bars=HORIZON)
    with pytest.raises(ValueError, match='risk_unit_price'):
        passive_benchmark_r(bad, 0.0005)
    unknown = EpisodeExposure(net_r=1.0, direction='FLAT', entry_price=100.0,
                              risk_unit_price=1.0, horizon_bars=HORIZON)
    with pytest.raises(ValueError, match='LONG or SHORT'):
        passive_benchmark_r(unknown, 0.0005)


def test_placebo_is_deterministic_for_a_fixed_seed():
    closes = _trending_closes()
    a = placebo_exposures(closes, long_share=0.9, horizon_bars=HORIZON,
                          risk_unit_frac=RISK_UNIT_FRAC, n_episodes=200, seed=17)
    b = placebo_exposures(closes, long_share=0.9, horizon_bars=HORIZON,
                          risk_unit_frac=RISK_UNIT_FRAC, n_episodes=200, seed=17)
    assert a == b


def test_appendix_a_invariant_now_frozen_relative_rule():
    """METH-1 (EV_METHODS G-02): the Appendix A tolerance is a preregistration
    choice and is now FROZEN as the relative reading |detrended| <= 0.25*|raw|
    (with an absolute floor when the window measured no bias at all). A placebo
    on a trending window must satisfy it; a centering that did not remove the
    bias must fail it."""
    # Enough placebo episodes that the sample mean is a tight estimate of the
    # expectation: per-episode noise is ~1.1 R over an 8-bar hold, so n=2000
    # puts |detrended| well inside the 0.25*|raw| tolerance when it works.
    closes = _trending_closes(n=2000)
    check = appendix_a_invariant(closes, long_share=0.9, horizon_bars=HORIZON,
                                 risk_unit_frac=RISK_UNIT_FRAC,
                                 n_episodes=2000, seed=5)
    assert check.placebo_mean_raw != 0.0            # the window had bias
    assert check.holds is True
    # Direct threshold arithmetic: the relative reading.
    assert invariant_holds(1.0, 0.2) is True        # 0.2 <= 0.25 * 1.0
    assert invariant_holds(1.0, 0.3) is False       # centering removed < 75%
    # Absolute fallback when the window measured no bias at all.
    assert invariant_holds(0.001, 0.001) is True
    assert invariant_holds(0.001, 0.1) is False
    # A centering that leaves the bias in place must fail the invariant.
    drift = mean_log_drift_per_bar(closes)
    placebo = placebo_exposures(closes, long_share=0.9, horizon_bars=HORIZON,
                                risk_unit_frac=RISK_UNIT_FRAC,
                                n_episodes=2000, seed=5)
    raw = _mean([e.net_r for e in placebo])
    undetrended = _mean([e.net_r for e in placebo])    # drift NOT subtracted
    assert invariant_holds(raw, undetrended) is False
    assert drift != 0.0
