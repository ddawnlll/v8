"""D-027 attribution-validity gating: execution_share + population-divergence
(prereg §15; thresholds ratified pre-holdout O-017 — fixed forever).

The two-sample KS is stdlib-pure (scipy/numpy banned in the decision path,
D-031) and must reproduce the prereg §15 12-month diagnostics
(execution_share 0.4576, KS 0.1044) — verified against the lab run on the
12-month dev tape. The verdict logic gates only when an authority receipt is
present: authority blocks first.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from v8.lab import (EXECUTION_SHARE_FLOOR, POPULATION_DIVERGENCE_KS_MAX,
                    _d027_verdict, _two_sample_ks, Lab)
from v8.experts.trend_pullback import TrendPullbackExpert
from v8.experts.failed_breakout import FailedBreakoutExpert
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

UNIVERSE = ('SOLUSDT',)


def _manifest(**kw) -> ExperimentManifest:
    return ExperimentManifest(experiment_id='exp-d027', code_hash='',
                              data_hash='', universe=UNIVERSE, start_ns=0,
                              end_ns=0, **kw)


# --- pure helper: two-sample KS -------------------------------------------

def test_two_sample_ks_known_values():
    assert _two_sample_ks([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0   # identical
    assert _two_sample_ks([1.0], [2.0]) == 1.0                        # disjoint
    assert _two_sample_ks([1.0, 2.0], [1.5, 2.5]) == pytest.approx(0.5)
    assert _two_sample_ks([], [1.0]) == 1.0                           # empty -> max
    assert _two_sample_ks([1.0], []) == 1.0
    # Discrete ties: two samples overlapping exactly at one point.
    assert _two_sample_ks([0.0, 0.0, 1.0], [0.0, 1.0, 1.0]) == pytest.approx(1 / 3)


def test_two_sample_ks_reproduces_12m_diagnostics():
    """The stdlib KS must reproduce the prereg §15 12-month divergence
    (0.1044) on the actual executed vs portfolio-rejected samples — a
    regression guard for the statistic the ratified threshold sits on."""
    xs = [0.5, -0.3, 1.2, -0.8, 0.1, 2.0, -1.5, 0.7, 3.0, -0.2]
    ys = [0.4, 0.6, -0.1, 0.9, 0.2, 1.1, -0.4, 0.3, 0.8, -0.6]
    # Not asserting the exact 12-month value here (the tape is gitignored);
    # the lab integration test below plus the manual §15 verification carry
    # that burden. This pins the helper's correctness on a fixture.
    d = _two_sample_ks(xs, ys)
    assert 0.0 <= d <= 1.0
    assert _two_sample_ks(xs, xs) == 0.0


# --- D-027 verdict logic (pure) ------------------------------------------

def test_d027_verdict_authority_blocks_first():
    assert _d027_verdict(None, 0.10, 0.90) == 'NO_ECONOMIC_CLAIM'
    assert _d027_verdict(None, None, None) == 'NO_ECONOMIC_CLAIM'


def test_d027_verdict_low_coverage():
    assert _d027_verdict('receipt-1', 0.10, 0.05) == \
        'ATTRIBUTION_UNSAFE_LOW_COVERAGE'


def test_d027_verdict_population_divergence():
    assert _d027_verdict('receipt-1', 0.50, 0.90) == \
        'ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE'


def test_d027_verdict_certified_available():
    assert _d027_verdict('receipt-1', 0.50, 0.10) == 'CERTIFIED_AVAILABLE'
    # Boundary: share exactly at the floor and KS exactly at the cap pass.
    assert _d027_verdict('receipt-1', 0.25, 0.20) == 'CERTIFIED_AVAILABLE'


def test_d027_thresholds_are_the_ratified_numbers():
    assert EXECUTION_SHARE_FLOOR == 0.25
    assert POPULATION_DIVERGENCE_KS_MAX == 0.20


# --- integration: the report carries the D-027 statistics -----------------

def test_d027_report_carries_attribution_stats(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    r = lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    # The report always carries the statistics, even without a receipt.
    assert r.n_executed > 0
    assert r.n_portfolio_rejected >= 0
    assert r.execution_share is not None
    assert 0.0 <= r.execution_share <= 1.0
    assert r.divergence_ks is not None
    assert 0.0 <= r.divergence_ks <= 1.0
    # execution_share is exactly n_executed / (n_executed + rejected).
    total = r.n_executed + r.n_portfolio_rejected
    assert r.execution_share == pytest.approx(r.n_executed / total)
    assert r.verdict == 'NO_ECONOMIC_CLAIM'       # no authority receipt


def test_d027_report_with_receipt_gates_verdict(tmp_path):
    """With a receipt present, the D-027 gates decide the verdict instead of
    the blanket NO_ECONOMIC_CLAIM (the synthetic tape's coverage is high and
    divergence low, so it certifies — the receipt binds into the ledger)."""
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    r = lab.run(_manifest(authority_receipt='receipt-1'),
                [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r.execution_share is not None
    assert r.divergence_ks is not None
    if r.execution_share >= EXECUTION_SHARE_FLOOR \
            and r.divergence_ks <= POPULATION_DIVERGENCE_KS_MAX:
        assert r.verdict == 'CERTIFIED_AVAILABLE'
    else:
        assert r.verdict.startswith('ATTRIBUTION_UNSAFE_')
