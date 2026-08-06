"""Within-family Reality-Check multiplicity test (D-044;
PREREGISTRATION_V8_SLICE_001 section 11). Synthetic-data unit tests only —
`tools/run_experiment.py` (the Phase-4 runner) does not exist yet, so this
module has never been exercised against a real LabReport.
"""
from __future__ import annotations

import pytest

from v8.statistics import (RealityCheckResult, _block_bootstrap_indices,
                           reality_check_p_value, select_block_size)


def test_reality_check_deterministic_given_seed():
    """Same inputs + same seed reproduce the identical result (no module
    reads the wall clock; the caller's seed is the only source of
    randomness — PERSISTENCE_REPLAY_SPEC section 4)."""
    series = {'a': [0.1, -0.2, 0.3, 0.05, -0.1, 0.2] * 5,
              'b': [-0.05, 0.1, -0.15, 0.2, 0.0, -0.1] * 5}
    r1 = reality_check_p_value(series, block_size=6, n_resamples=100, seed=7)
    r2 = reality_check_p_value(series, block_size=6, n_resamples=100, seed=7)
    assert r1 == r2


def test_reality_check_p_value_in_bounds():
    series = {'a': [0.1, -0.2, 0.3, 0.05, -0.1, 0.2] * 5,
              'b': [-0.05, 0.1, -0.15, 0.2, 0.0, -0.1] * 5,
              'c': [0.02, -0.01, 0.03, -0.02, 0.01, 0.0] * 5}
    r = reality_check_p_value(series, block_size=4, n_resamples=200, seed=1)
    assert 0.0 <= r.p_value <= 1.0
    assert r.argmax_config in series


def test_reality_check_finds_argmax():
    """The reported argmax is whichever configuration actually has the
    highest sample mean — deliberately made unambiguous here."""
    series = {'a': [1.0] * 20, 'b': [-1.0] * 20, 'c': [0.0] * 20}
    r = reality_check_p_value(series, block_size=5, n_resamples=50, seed=3)
    assert r.argmax_config == 'a'
    assert r.observed_max == pytest.approx(1.0)


def test_reality_check_dominant_configuration_gets_low_p_value():
    """A configuration whose mean is far above both zero variance and the
    noise of its competitors should almost never be matched by resampling
    noise alone — the compound null (no configuration beats 0 by more than
    search-induced noise explains) should be easy to reject here."""
    noise = [0.05, -0.03, 0.02, -0.04, 0.01, -0.02, 0.03, -0.01] * 6
    series = {
        'dominant': [5.0] * len(noise),  # zero variance, mean 5.0
        'noise_a': noise,
        'noise_b': [-x for x in noise],
    }
    r = reality_check_p_value(series, block_size=1, n_resamples=300, seed=42)
    assert r.argmax_config == 'dominant'
    assert r.p_value < 0.05


def test_reality_check_rejects_empty_input():
    with pytest.raises(ValueError):
        reality_check_p_value({}, block_size=4, n_resamples=10, seed=0)


def test_reality_check_rejects_mismatched_lengths():
    """Cross-family series are not aligned by episode index — this must
    fail loudly rather than silently misapply the max statistic (O-021)."""
    series = {'a': [0.1, 0.2, 0.3], 'b': [0.1, 0.2]}
    with pytest.raises(ValueError):
        reality_check_p_value(series, block_size=1, n_resamples=10, seed=0)


def test_reality_check_rejects_zero_resamples():
    series = {'a': [0.1, 0.2, 0.3]}
    with pytest.raises(ValueError):
        reality_check_p_value(series, block_size=1, n_resamples=0, seed=0)


def test_block_bootstrap_indices_length_and_bounds():
    import random
    rng = random.Random(5)
    idx = _block_bootstrap_indices(n=20, block_size=6, rng=rng)
    assert len(idx) == 20
    assert all(0 <= i < 20 for i in idx)


def test_block_bootstrap_indices_are_contiguous_within_a_block():
    """Each block of `block_size` consecutive output positions must be a
    contiguous run of source indices (mod n) — the section-9 dependence
    unit, never spliced across an arbitrary boundary."""
    import random
    rng = random.Random(9)
    n, block_size = 20, 5
    idx = _block_bootstrap_indices(n=n, block_size=block_size, rng=rng)
    for block_start in range(0, len(idx), block_size):
        block = idx[block_start:block_start + block_size]
        for a, b in zip(block, block[1:]):
            assert b == (a + 1) % n


def test_block_bootstrap_indices_empty_series():
    import random
    assert _block_bootstrap_indices(0, 4, random.Random(1)) == []


def test_select_block_size_low_autocorrelation_stays_daily():
    # Balanced +1/-1 period-4 pattern: lag-1 autocorrelation ~ -0.025.
    series = [1.0, -1.0, -1.0, 1.0] * 10
    assert select_block_size(series) == 24


def test_select_block_size_high_autocorrelation_goes_weekly():
    # Monotonic ramp: lag-1 autocorrelation approaches 1.
    series = [float(i) for i in range(50)]
    assert select_block_size(series) == 168


def test_select_block_size_short_series_defaults_small():
    assert select_block_size([0.1, 0.2]) == 24
    assert select_block_size([]) == 24


def test_reality_check_result_is_frozen_dataclass():
    r = RealityCheckResult(observed_max=1.0, argmax_config='a', p_value=0.5,
                           n_resamples=10, block_size=24, seed=1)
    with pytest.raises(Exception):
        r.p_value = 0.9  # type: ignore[misc]
