"""v8_slice_001 experiment runner tests (PREREGISTRATION_V8_SLICE_001).

The runner is gated on the frozen holdout existing; it must fail closed when
the holdout is absent, verify the pre-recorded holdout hash before any
evaluation, and be deterministic (fixed bootstrap seed, no wall clock).
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from v8.schema import sha1_hex
from v8.synth import make_synthetic_tape
from tools.run_experiment import (ALPHA_F, N_RESAMPLES,
                                  block_bootstrap_lower_bound,
                                  resamples_for_alpha, run_experiment,
                                  _block_size, _lag1_autocorrelation)

HOLDOUT_ANCHOR_NS = 1782864000000000000      # 2026-07-01 00:00 UTC


def _write_tape(path: Path, seed: int = 7, n_bars: int = 160) -> str:
    """Write a synthetic holdout stand-in whose kline event range sits inside
    the frozen OOS window [HOLDOUT_ANCHOR_NS, +n_bars): the runner now fails
    closed when the declared window does not match the tape's actual content
    (prereg §13), so the stand-in must satisfy the real constraint."""
    rows = make_synthetic_tape(seed=seed, n_bars=n_bars, symbol='BTCUSDT')
    shift = HOLDOUT_ANCHOR_NS - rows[0].event_time
    if shift < 0:
        raise AssertionError('synthetic tape starts after the anchor')
    shifted = []
    for r in rows:
        d = asdict(r)
        d['event_time'] += shift
        d['available_time'] += shift
        d['ingested_time'] += shift
        shifted.append(d)
    with path.open('w', encoding='utf-8') as fh:
        for d in shifted:
            fh.write(json.dumps(d) + '\n')
    lines = path.read_text(encoding='utf-8').splitlines()
    return sha1_hex([json.loads(l) for l in lines])


def _manifest(tmp_path: Path, tape: Path, data_hash: str) -> Path:
    m = tmp_path / 'manifest.json'
    m.write_text(json.dumps({
        'experiment_id': 'v8_slice_001', 'code_hash': '', 'data_hash': data_hash,
        'universe': ['BTCUSDT'], 'start_ns': HOLDOUT_ANCHOR_NS,
        'end_ns': 0, 'interval': '1h',
        'tape_path': str(tape),
    }), encoding='utf-8')
    return m


def test_fails_closed_without_holdout(tmp_path):
    """No holdout tape -> NO_ECONOMIC_CLAIM report, no fabricated families."""
    m = _manifest(tmp_path, tmp_path / 'missing.jsonl', '')
    report = run_experiment(m)
    assert report['holdout_unavailable'] is True
    assert report['verdict'] == 'NO_ECONOMIC_CLAIM'
    assert report['families']['trend_continuation'] is None
    assert report['families']['failed_breakout_reentry'] is None


def test_validates_frozen_constants(tmp_path):
    """A manifest from a different preregistration must fail closed."""
    m = _manifest(tmp_path, tmp_path / 't.jsonl', '')
    data = json.loads(m.read_text())
    data['experiment_id'] = 'some-other-experiment'
    m.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='experiment_id'):
        run_experiment(m)


def test_holdout_hash_recorded_before_evaluation(tmp_path):
    """The pre-recorded holdout hash (pinned at download time, prereg §16) is
    verified before evaluation; the report carries it and the family stats."""
    tape = tmp_path / 'holdout.jsonl'
    h = _write_tape(tape)
    m = _manifest(tmp_path, tape, h)
    report = run_experiment(m)
    assert report['holdout']['present'] is True
    assert report['holdout']['hash'] == h
    assert report['holdout']['recorded_before_evaluation'] is True
    assert report['verdict'] == 'NO_ECONOMIC_CLAIM'      # no authority receipt
    assert report['d027'] is not None
    assert report['sufficiency']['bars'] == 160
    # A 160-bar tape is far below the prereg §12 minimum (1400 bars), so the
    # sufficiency gate must report not-ok — the runner never overclaims.
    assert report['sufficiency']['episodes_ok'] is False
    for fid in ('trend_continuation', 'failed_breakout_reentry'):
        fam = report['families'][fid]
        assert fam is not None
        assert fam['n'] >= 0
        assert 'mu_hat' in fam and 'ci_lower_2p5' in fam
        assert 'h0_rejected' in fam


def test_holdout_hash_mismatch_fails_closed(tmp_path):
    """A holdout whose tape hash differs from the recorded manifest hash is a
    recorded-before-evaluation violation — fail closed, never evaluate."""
    tape = tmp_path / 'holdout.jsonl'
    _write_tape(tape)
    m = _manifest(tmp_path, tape, 'f' * 40)               # wrong recorded hash
    with pytest.raises(ValueError, match='holdout tape hash'):
        run_experiment(m)


def test_report_scores_the_detrended_series_and_shows_the_bias(tmp_path):
    """D-045: the primary family statistic is the DETRENDED mean, with the raw
    mean kept beside it. On a tape with any drift the two must differ, and the
    difference must have opposite sign for the LONG and the SHORT family —
    that opposition is the position-bias component the uncentered null missed.
    """
    tape = tmp_path / 'holdout.jsonl'
    h = _write_tape(tape, seed=7, n_bars=400)
    report = run_experiment(_manifest(tmp_path, tape, h))
    assert report['detrending']['estimated_on'] == 'frozen-oos-window'
    drift = report['detrending']['mean_log_drift_per_bar']
    assert drift != 0.0                          # the fixture must have a trend
    long_fam = report['families']['trend_continuation']         # LONG pilot
    short_fam = report['families']['failed_breakout_reentry']   # SHORT pilot
    for fam in (long_fam, short_fam):
        assert fam['mu_hat'] != fam['mu_hat_raw'], 'detrending was a no-op'
        assert fam['position_bias_component'] == pytest.approx(
            fam['mu_hat_raw'] - fam['mu_hat'])
    # A LONG family collects the drift for free; a SHORT family pays it.
    assert long_fam['position_bias_component'] > 0.0
    assert short_fam['position_bias_component'] < 0.0


def test_report_carries_the_multiplicity_denominator(tmp_path):
    """D-046: every family statistic states the search universe it was tested
    against, and flags when the declared search exceeds the retained variants
    (the Reality Check then saw only part of it and the p is optimistic)."""
    tape = tmp_path / 'holdout.jsonl'
    h = _write_tape(tape, seed=7, n_bars=400)
    report = run_experiment(_manifest(tmp_path, tape, h))
    for fid in ('trend_continuation', 'failed_breakout_reentry'):
        fam = report['families'][fid]
        assert fam['search_universe_size'] >= fam['variants_evaluated']
        assert fam['multiplicity_undercounted'] is (
            fam['search_universe_size'] > fam['variants_evaluated'])
        # Both pilots declare a search of 1 (prereg §4: parameters frozen in
        # code against synthetic tapes before the dev window existed).
        assert fam['search_universe_size'] == 1
        assert fam['multiplicity_undercounted'] is False


def test_report_carries_effective_search_size_and_expected_false_positives(tmp_path):
    """METH-2/METH-6 (G-01/G-11): the scored report states the honest family
    size (effective_search_size, D-046) and the Aronson expected-false-
    positives line (N x alpha_f) beside every family, plus the program-level
    total. Both pilots declare search_universe_size = 1, so the per-family
    expectation at alpha_f = 0.025 is 0.025 and the program total 0.05."""
    tape = tmp_path / 'holdout.jsonl'
    h = _write_tape(tape, seed=7, n_bars=400)
    report = run_experiment(_manifest(tmp_path, tape, h))
    for fid in ('trend_continuation', 'failed_breakout_reentry'):
        fam = report['families'][fid]
        assert fam['effective_search_size'] == fam['search_universe_size'] == 1
        assert fam['expected_false_positives'] == pytest.approx(1 * 0.025)
    assert report['expected_false_positives']['total'] == pytest.approx(2 * 0.025)


def test_executed_episode_without_a_recorded_r_unit_fails_closed(tmp_path):
    """A pre-D-045 ledger cannot be detrended. Scoring it would silently fall
    back to the uncentered null, so the runner refuses instead."""
    from tools.run_experiment import _family_exposures
    store = tmp_path / 'store'
    store.mkdir()
    (store / 'candidates.jsonl').write_text(json.dumps({
        'candidate_id': 'c1', 'expert_id': 'trend_pullback',
        'direction': 'LONG'}) + '\n', encoding='utf-8')
    (store / 'outcomes.jsonl').write_text(json.dumps({
        'candidate_id': 'c1', 'net_r': 0.5, 'label_status': 'MATURE',
        'horizon_bars': 8, 'entry_price': 0.0,
        'risk_unit_price': 0.0}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='no risk_unit_price'):
        _family_exposures(store)


def test_block_bootstrap_deterministic_and_one_sided():
    net_rs = [0.05] * 60 + [0.1] * 40
    a = block_bootstrap_lower_bound(net_rs)
    b = block_bootstrap_lower_bound(net_rs)
    assert a == b                                        # fixed seed -> identical
    assert a > 0.0                                       # positive mean rejects H0
    assert block_bootstrap_lower_bound([0.0] * 100) <= 0.0
    assert block_bootstrap_lower_bound([]) == 0.0


def test_block_bootstrap_lower_bound_is_the_LOWER_percentile():
    """The bound must sit BELOW the sample mean — the 2.5th-percentile lower
    bound, never the upper (a regression for the inverted-index bug caught by
    the dev-tape smoke run). A negative-mean family must NOT reject H0."""
    net_rs = [-0.1] * 40 + [-0.05] * 60
    mu = sum(net_rs) / len(net_rs)
    lower = block_bootstrap_lower_bound(net_rs)
    assert lower <= mu                                  # lower bound <= mean
    assert lower <= 0.0                                 # negative mean -> no signal


def test_block_size_mechanical_rule():
    """Prereg §9 / D-052: the lag-1 gate at 0.10 still picks the tier; the tier
    values are the episode-unit rate round(n**(1/3)), doubled above the gate.
    The runner delegates to `v8.statistics.select_block_size` — one rule of
    record, so the tool and the decision-path module cannot drift."""
    import random
    rng = random.Random(42)                           # i.i.d. -> ~0 autocorr
    low_ac = [rng.uniform(-0.01, 0.01) for _ in range(60)]
    assert abs(_lag1_autocorrelation(low_ac)) < 0.10
    assert _block_size(low_ac) == 4                   # n=60 -> round(3.91)=4
    high_ac = [0.05] * 40 + [0.1] * 40                # step -> strong +ac
    assert abs(_lag1_autocorrelation(high_ac)) > 0.10
    assert _block_size(high_ac) == 8                  # n=80 -> 2*round(4.31)=8
    # The defect this rule replaces: both tiers must stay strictly below n, or
    # the bootstrap collapses to a point mass and rejects H0 by construction.
    assert _block_size(low_ac) < len(low_ac)
    assert _block_size(high_ac) < len(high_ac)


def test_resamples_for_alpha_keeps_the_tail_index_stable():
    """D-052: the bound is the int(N * alpha)-th smallest resample mean, so N
    cannot be a constant chosen independently of alpha. The defect was not
    visible at THIS runner's alpha_f (0.05/2 -> index 50) — it appeared once a
    slate-wide Bonferroni alpha was used, where the same 2000 put the index at
    3: the 4th-smallest draw standing in for a 0.18th percentile."""
    slate_alpha = 0.05 / 28
    assert int(2000 * slate_alpha) == 3                    # the defect, pinned
    # The property, over every family count the slate could plausibly take.
    for n_families in range(1, 65):
        alpha = 0.05 / n_families
        assert int(resamples_for_alpha(alpha) * alpha) >= 100
    assert resamples_for_alpha(ALPHA_F) >= N_RESAMPLES     # floor never lowered
    for bad in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError, match='alpha must be in'):
            resamples_for_alpha(bad)


def test_lower_bound_has_width_at_the_defect_shape():
    """Regression for the exact report row that motivated D-052: a positive
    mean at n=50 used to select block 168, collapse the bootstrap to a point
    mass, and return ci_lower == mean > 0 — an H0 rejection with a zero-width
    interval. The bound must now sit strictly below the mean."""
    import random
    rng = random.Random(3)
    net_rs = [rng.gauss(0.015, 0.9) for _ in range(50)]
    mu = sum(net_rs) / len(net_rs)
    lower = block_bootstrap_lower_bound(net_rs)
    assert lower < mu                                  # strict: real width
    assert _block_size(net_rs) < len(net_rs)


def test_window_overlapping_dev_is_not_the_holdout(tmp_path):
    """A manifest whose window starts before the 2026-07-01 anchor cannot be
    the holdout (prereg §13) — the runner must fail closed, not evaluate."""
    tape = tmp_path / 'holdout.jsonl'
    h = _write_tape(tape)
    m = _manifest(tmp_path, tape, h)
    data = json.loads(m.read_text())
    data['start_ns'] = HOLDOUT_ANCHOR_NS - 1_000_000_000
    m.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='holdout anchor'):
        run_experiment(m)


def test_missing_recorded_hash_fails_closed(tmp_path):
    """An un-pinned holdout (empty data_hash) must fail closed — the hash is
    recorded at download time before any evaluation (prereg §16)."""
    tape = tmp_path / 'holdout.jsonl'
    _write_tape(tape)
    m = _manifest(tmp_path, tape, '')
    with pytest.raises(ValueError, match='data_hash is empty'):
        run_experiment(m)


def test_holdout_tape_content_must_match_declared_window(tmp_path):
    """data_hash binds the file bytes, not the window: a tape whose kline
    event range lies before the declared holdout window (a dev-period tape)
    must fail closed even when start_ns >= anchor (prereg §13)."""
    tape = tmp_path / 'dev_period.jsonl'
    rows = make_synthetic_tape(seed=7, n_bars=160, symbol='BTCUSDT')
    with tape.open('w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r)) + '\n')
    h = sha1_hex([json.loads(l) for l in tape.read_text(encoding='utf-8').splitlines()])
    m = _manifest(tmp_path, tape, h)
    with pytest.raises(ValueError, match='before the declared window start'):
        run_experiment(m)
