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
from tools.run_experiment import (block_bootstrap_lower_bound, run_experiment)


def _write_tape(path: Path, seed: int = 7, n_bars: int = 160) -> str:
    rows = make_synthetic_tape(seed=seed, n_bars=n_bars, symbol='BTCUSDT')
    with path.open('w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r)) + '\n')
    lines = path.read_text(encoding='utf-8').splitlines()
    return sha1_hex([json.loads(l) for l in lines])


def _manifest(tmp_path: Path, tape: Path, data_hash: str) -> Path:
    m = tmp_path / 'manifest.json'
    m.write_text(json.dumps({
        'experiment_id': 'v8_slice_001', 'code_hash': '', 'data_hash': data_hash,
        'universe': ['BTCUSDT'], 'start_ns': 0, 'end_ns': 0, 'interval': '1h',
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


def test_block_bootstrap_deterministic_and_one_sided():
    net_rs = [0.05] * 60 + [0.1] * 40
    a = block_bootstrap_lower_bound(net_rs)
    b = block_bootstrap_lower_bound(net_rs)
    assert a == b                                        # fixed seed -> identical
    assert a > 0.0                                       # positive mean rejects H0
    assert block_bootstrap_lower_bound([0.0] * 100) <= 0.0
    assert block_bootstrap_lower_bound([]) == 0.0
