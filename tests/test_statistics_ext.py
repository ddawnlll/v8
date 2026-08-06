"""METH-1..METH-6 statistics extensions (EV_METHODS E-01/E-02/E-04/E-05,
G-01/G-06/G-08/G-11/G-12; Aronson Ch5/Ch6/Ch7/Ch9). Synthetic-data unit tests
only — deterministic (fixed seed, no wall clock), stdlib-pure.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from v8.statistics import (PermutationRealityCheckResult, block_bootstrap_means,
                           bootstrap_ci,
                           detrend_net_r, effective_independent_episodes,
                           effective_search_size, expected_false_positives,
                           mean_log_drift_per_bar,
                           monte_carlo_permutation_p_value,
                           placebo_exposures, practical_significance,
                           reality_check_p_value, regime_slices,
                           select_block_size, streak_vs_null)


# --- D-052: block-bootstrap non-degeneracy invariants ----------------------
# Properties that must hold for EVERY input, not examples. The bar-unit block
# defect survived a full example-based suite because those tests asserted the
# rule's output value (24 / 168) — the same wrong assumption the code held.
# An invariant cannot be satisfied by agreeing with the code.


def test_block_bootstrap_rejects_a_block_that_reaches_n():
    """With block_size >= n the circular sampler draws a rotation of the whole
    series: every resample holds each element once, so every resample mean is
    the sample mean. Must raise — a silent point mass is indistinguishable
    from a real interval in the report."""
    xs = [0.3, -1.0, 0.7, -0.2, 1.5, -0.9, 0.1]
    for bad in (len(xs), len(xs) + 1, 168):
        with pytest.raises(ValueError, match='degenerate block bootstrap'):
            block_bootstrap_means(xs, bad, 50, 7)


def test_block_bootstrap_is_never_a_point_mass_under_the_rule():
    """For any sample the mechanical rule admits (n >= 2, values not all
    equal), the resample distribution must have width. This is the property
    the report's `ci_lower == mu_hat` rows violated."""
    rng = random.Random(11)
    for n in (5, 17, 30, 50, 74, 168, 200):
        xs = [rng.gauss(0.0, 0.9) for _ in range(n)]
        block = select_block_size(xs)
        assert block < n                              # rule side of the invariant
        means = block_bootstrap_means(xs, block, 200, 7)
        assert len(set(means)) > 1, f'point mass at n={n}, block={block}'




# --- METH-1: centering correctness (G-02 / Aronson Appendix A) -------------


def test_meth1_centering_precedes_the_family_tests():
    """G-02 core, shown end to end: a zero-skill LONG-biased placebo family on
    a trending tape has a strongly positive RAW mean — fed to the WRC
    uncentered it "rejects" (p = 0.0). The caller's pre-centering
    (detrend_net_r, D-045) collapses the family mean toward 0 and the SAME WRC
    no longer rejects. The family tests never recenter for position bias
    inside — centering is explicit, before the call."""
    import math
    rng = random.Random(13)
    price, closes = 100.0, []
    for _ in range(3000):
        price *= math.exp(0.0005 + rng.gauss(0.0, 0.004))
        closes.append(price)
    drift = mean_log_drift_per_bar(closes)
    placebo = placebo_exposures(closes, long_share=0.95, horizon_bars=8,
                                risk_unit_frac=0.01, n_episodes=300, seed=5)
    raw = [e.net_r for e in placebo]
    centered = detrend_net_r(placebo, drift)
    assert sum(raw) / len(raw) > 0.05               # the bias is material
    assert abs(sum(centered) / len(centered)) < abs(sum(raw) / len(raw))
    raw_res = reality_check_p_value({'placebo': raw}, block_size=24,
                                    n_resamples=500, seed=9)
    cen_res = reality_check_p_value({'placebo': centered}, block_size=24,
                                    n_resamples=500, seed=9)
    assert raw_res.p_value < 0.05                   # uncentered noise can "pass"
    assert cen_res.p_value > 0.05                   # centered noise does not
    assert cen_res.p_value > raw_res.p_value


# --- METH-3: Monte-Carlo permutation Reality Check (EV_METHODS E-02) -------


def test_monte_carlo_permutation_known_edge_gives_small_p():
    """A configuration whose net_R sits far above what random direction/move
    re-pairing can produce must reject the signal-content null. The 'edge'
    variant is LONG on every episode while the market moves are ~N(0, 0.02);
    re-pairing destroys the alignment, so the observed max (mean net_R = 1.0)
    is almost never matched by a permuted max."""
    n = 40
    rng = random.Random(11)
    moves = [rng.gauss(0.0, 0.02) for _ in range(n)]
    directions = {'edge': [1] * n,
                  'noise': [1 if rng.random() < 0.5 else -1 for _ in range(n)]}
    net_r = {'edge': [1.0] * n,
             'noise': [rng.gauss(0.0, 0.05) for _ in range(n)]}
    res = monte_carlo_permutation_p_value(moves, directions, net_r,
                                          n_permutations=500, seed=42)
    assert res.argmax_config == 'edge'
    assert res.observed_max == pytest.approx(1.0)
    assert res.p_value < 0.05


def test_monte_carlo_permutation_pure_noise_p_not_small():
    """A family whose directions are INDEPENDENT of the market moves (the
    signal-content null is true by construction) must not reject: the observed
    max is a draw from the same distribution as the permuted maxima."""
    n = 60
    rng = random.Random(23)
    moves = [rng.gauss(0.0, 0.05) for _ in range(n)]
    dirs = [1 if rng.random() < 0.5 else -1 for _ in range(n)]
    net_r = [d * m for d, m in zip(dirs, moves)]   # no edge, no cost
    res = monte_carlo_permutation_p_value(moves, {'a': dirs}, {'a': net_r},
                                          n_permutations=500, seed=7)
    assert 0.0 <= res.p_value <= 1.0
    assert res.p_value > 0.05


def test_monte_carlo_permutation_deterministic_given_seed():
    moves = [0.1, -0.05, 0.03, 0.02, -0.08, 0.06] * 5
    directions = {'a': [1, -1, 1, -1, 1, -1] * 5}
    net_r = {'a': [0.2, -0.1, 0.15, -0.05, 0.1, -0.2] * 5}
    r1 = monte_carlo_permutation_p_value(moves, directions, net_r, 100, seed=3)
    r2 = monte_carlo_permutation_p_value(moves, directions, net_r, 100, seed=3)
    assert r1 == r2
    assert isinstance(r1, PermutationRealityCheckResult)


def test_monte_carlo_permutation_validates_input():
    moves = [0.1, 0.2]
    with pytest.raises(ValueError, match='same variants'):
        monte_carlo_permutation_p_value(moves, {'a': [1, 1]}, {'b': [1.0, 1.0]},
                                        10, 0)
    with pytest.raises(ValueError, match='share length'):
        monte_carlo_permutation_p_value(moves, {'a': [1]}, {'a': [1.0]}, 10, 0)
    with pytest.raises(ValueError, match='LONG'):
        monte_carlo_permutation_p_value(moves, {'a': [0, 1]}, {'a': [1.0, 1.0]},
                                        10, 0)
    with pytest.raises(ValueError, match='n_permutations'):
        monte_carlo_permutation_p_value(moves, {'a': [1, 1]}, {'a': [1.0, 1.0]},
                                        0, 0)
    with pytest.raises(ValueError, match='no configurations'):
        monte_carlo_permutation_p_value(moves, {}, {}, 10, 0)


# --- METH-4: bootstrap CI + effective independent episodes (E-01/E-04) -----


def test_bootstrap_ci_deterministic_and_contains_mean():
    # A NON-periodic series (a series repeating exactly every `block_size`
    # entries collapses every resample mean to the same value, which is a
    # degenerate-but-correct bootstrap outcome, not a useful CI test).
    rng = random.Random(9)
    series = [rng.uniform(-0.2, 0.2) for _ in range(120)]
    a = bootstrap_ci(series, block_size=6, n_resamples=1000, seed=7)
    b = bootstrap_ci(series, block_size=6, n_resamples=1000, seed=7)
    assert a == b
    mean = sum(series) / len(series)
    assert a[0] <= mean <= a[1]
    assert a[0] < a[1]


def test_bootstrap_ci_constant_series_collapses():
    # Zero variance -> every resample mean is identical -> CI collapses.
    lo, hi = bootstrap_ci([0.5] * 50, block_size=5, n_resamples=100, seed=1)
    assert lo == pytest.approx(0.5)
    assert hi == pytest.approx(0.5)


def test_bootstrap_ci_validates_level_and_empty():
    with pytest.raises(ValueError, match='ci must be in'):
        bootstrap_ci([1.0, 2.0], block_size=1, n_resamples=10, seed=0, ci=1.5)
    assert bootstrap_ci([], block_size=1, n_resamples=10, seed=0) == (0.0, 0.0)
    with pytest.raises(ValueError, match='n_resamples'):
        bootstrap_ci([1.0, 2.0], block_size=1, n_resamples=0, seed=0)


def test_effective_independent_episodes_arithmetic():
    # Overlap correction: n / max_hold_bars is the upper bound on independent
    # observations (E-04: block length must be >= the longest hold).
    assert effective_independent_episodes(200, 8) == pytest.approx(25.0)
    assert effective_independent_episodes(30, 30) == pytest.approx(1.0)
    assert effective_independent_episodes(0, 8) == 0.0
    with pytest.raises(ValueError, match='max_hold_bars'):
        effective_independent_episodes(10, 0)
    with pytest.raises(ValueError, match='n_episodes'):
        effective_independent_episodes(-1, 8)


# --- METH-6: expected false positives (E-05 / G-11) ------------------------


def test_expected_false_positives_arithmetic():
    # Aronson's calibration verbatim: 6,402 rules x 0.05 = 320.1, and ~320
    # were naively significant — exactly chance (Ch9 p443).
    assert expected_false_positives(6402, 0.05) == pytest.approx(320.1)
    assert expected_false_positives(2, 0.025) == pytest.approx(0.05)
    assert expected_false_positives(0, 0.05) == 0.0
    with pytest.raises(ValueError):
        expected_false_positives(-1, 0.05)
    with pytest.raises(ValueError):
        expected_false_positives(10, 0.0)


# --- METH-5: streak-vs-null + regime slices + practical significance -------


def test_streak_vs_null_deterministic():
    series = [0.1, -0.1, 0.05, 0.08, -0.02, 0.03] * 10
    r1 = streak_vs_null(series, block_size=6, n_resamples=200, seed=5)
    r2 = streak_vs_null(series, block_size=6, n_resamples=200, seed=5)
    assert r1 == r2


def test_streak_vs_null_long_observed_streak_is_in_the_null_tail():
    """G-08: a 40-consecutive-profitable run is in the LOWER TAIL of the
    no-edge bootstrap null (p ~ 0.06: only ~6% of zero-centered circular
    resamples produce a run that long). The circular wrap lets the null reach
    runs up to the full series length, so the calibration is conservative —
    it never over-hypes a streak; it reports its percentile."""
    series = [0.1] * 40 + [-0.1] * 20
    res = streak_vs_null(series, block_size=6, n_resamples=300, seed=11)
    assert res.observed_streak == 40
    assert 0.0 <= res.p_value <= 1.0
    assert len(res.null_best_streaks) == 300
    assert all(0 <= s <= len(series) for s in res.null_best_streaks)
    assert res.p_value <= 0.10


def test_streak_vs_null_trivial_streak_not_extreme():
    # Alternating signs: observed streak is 1, and almost every no-edge
    # resample contains at least one positive run of length >= 1.
    series = [-0.1, 0.1] * 30
    res = streak_vs_null(series, block_size=6, n_resamples=300, seed=21)
    assert res.observed_streak == 1
    assert res.p_value >= 0.95


def test_streak_vs_null_validates():
    with pytest.raises(ValueError, match='empty'):
        streak_vs_null([], block_size=4, n_resamples=10, seed=0)


def test_regime_slices_correctness():
    series = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    slices = regime_slices(series, slice_bars=3)
    assert [s.mean_net_r for s in slices] == pytest.approx([2.0, 5.0, 7.5])
    assert [s.n for s in slices] == [3, 3, 2]
    assert slices[0].start_idx == 0 and slices[0].end_idx == 3
    assert slices[2].start_idx == 6 and slices[2].end_idx == 8
    assert regime_slices([], slice_bars=4) == []
    with pytest.raises(ValueError):
        regime_slices([1.0], 0)


def test_practical_significance():
    ok, note = practical_significance([0.2, 0.3, 0.1] * 20,
                                      min_net_r=0.1, min_trades=30)
    assert ok is True
    assert 'mean net_R 0.2000' in note
    assert 'episodes 60' in note
    bad, note2 = practical_significance([0.01, 0.02] * 10,
                                        min_net_r=0.1, min_trades=50)
    assert bad is False
    assert 'below' in note2
    assert practical_significance([], min_net_r=0.1, min_trades=5)[0] is False
    with pytest.raises(ValueError):
        practical_significance([1.0], 0.0, 5)
    with pytest.raises(ValueError):
        practical_significance([1.0], 0.1, 0)


# --- METH-2: effective search size (G-01 / D-046) --------------------------


def test_effective_search_size():
    assert effective_search_size(1, 1) == 1
    assert effective_search_size(3, 40) == 40        # honest search dominates
    with pytest.raises(ValueError, match='smaller than what it retained'):
        effective_search_size(5, 3)
    with pytest.raises(ValueError):
        effective_search_size(-1, 3)
    with pytest.raises(ValueError):
        effective_search_size(1, True)               # bool is not an int count
