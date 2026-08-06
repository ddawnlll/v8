"""Fib-projection-reversal expert tests (E-13).

Covers: setup detection at a measured 161.8% projection of an up-impulse
(short) and a down-impulse (long); no-setup rejection before the level is
tested; D-026 episode-key stability across consecutive spike bars; the frozen
projection level as the invalidation reference; still_valid invalidation +
fail-open; variants_evaluated completeness (D-044) with one crafted tape per
extension ratio; requires-vs-consumption; and a lab.run smoke test that never
implies an economic claim (rule 12).
"""
from __future__ import annotations

import pytest

from v8.schema import (TapeRow, MarketState, CandidateDraft, ExperimentManifest,
                       FEATURE_TO_GROUP, sha1_hex)
from v8.marketstate import build_state
from v8.lifecycle import episode_key
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.lab import Lab
from v8.experts.fib_projection_reversal import FibProjectionReversalExpert

UNIVERSE = ('SOLUSDT',)

# Up-spike tape: swing low bar 60 (low 97.5), swing high bar 64 (high 113.5),
# range 16, sideways 65..74 confirming the anchor, extension 75..79 spiking at
# bar 79. The 161.8% projection = 113.5 + 1.618*16 = 139.388 (variant a);
# 127.2% -> 133.852 (b); 261.8% -> 155.388 (c).


def _tape(closes, rng_by_idx):
    rows = []
    for i, c in enumerate(closes):
        r = rng_by_idx(i)
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c + r, 'low': c - r, 'close': c,
                     'volume': 1.0, 'closed': True}))
    return rows


def _state(rows, idx: int) -> MarketState:
    return build_state(rows[:idx + 1], rows[idx].available_time, UNIVERSE)


def _up_spike_tape(close79: float, rng79: float, close80: float = 132.0,
                   rng80: float = 1.0):
    """Up-impulse tape with an extension spike at bar 79 (high = close79+rng79)
    and an optional second spike bar 80."""
    closes = [100.0] * 60
    closes += [99.0, 103.0, 106.0, 109.0, 112.0]          # low 60, high 64
    closes += [111.0, 110.0, 109.0, 108.0, 107.5, 107.0,
               107.5, 108.0, 108.5, 109.0]                # sideways 65..74
    closes += [114.0, 118.0, 123.0, 128.0, close79, close80]

    def rng(i):
        if i < 60:
            return 0.3
        if i in (60, 64):
            return 1.5
        if i == 79:
            return rng79
        if i == 80:
            return rng80
        return 1.0
    return _tape(closes, rng)


def _down_spike_tape(close79: float, rng79: float):
    """Down-impulse mirror: swing high bar 60, swing low bar 64, sideways
    65..74, extension down spiking at bar 79 (low = close79-rng79)."""
    closes = [100.0] * 60
    closes += [112.0, 109.0, 106.0, 103.0, 99.0]          # high 60, low 64
    closes += [100.0, 101.0, 101.5, 102.0, 102.5, 103.0,
               103.5, 104.0, 104.5, 105.0]                # sideways 65..74
    closes += [96.0, 92.0, 87.0, 82.0, close79]

    def rng(i):
        if i < 60:
            return 0.3
        if i in (60, 64):
            return 1.5
        if i == 79:
            return rng79
        return 1.0
    return _tape(closes, rng)


def _draft(rows, idx: int, expert) -> CandidateDraft:
    ev = expert.evaluate(_state(rows, idx))
    assert ev.draft is not None, f'no draft at bar {idx} ({ev.decision})'
    return ev.draft


def _geo(draft: CandidateDraft) -> str:
    structural = {k: v for k, v in draft.risk_geometry.items()
                  if k not in ('atr_ref', 'prior_low_ref', 'prior_high_ref')}
    return sha1_hex(structural)


# --- setup detection ---------------------------------------------------------

def test_short_setup_at_upside_projection():
    ex = FibProjectionReversalExpert()                  # variant a: 161.8%
    rows = _up_spike_tape(close79=135.0, rng79=4.5)     # high 139.5 >= 139.388
    d = _draft(rows, 79, ex)
    assert d.direction == 'SHORT'
    assert d.setup_anchor_event_id == 'SOLUSDT:80'
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['stop_r'] == 1.0
    assert g['expiry_bars'] == 8
    # The projection level is frozen as the invalidation reference.
    assert g['prior_high_ref'] == pytest.approx(113.5 + 1.618 * 16.0)


def test_long_setup_at_downside_projection():
    ex = FibProjectionReversalExpert()
    rows = _down_spike_tape(close79=75.0, rng79=4.5)    # low 70.5 <= 71.612
    d = _draft(rows, 79, ex)
    assert d.direction == 'LONG'
    assert d.setup_anchor_event_id == 'SOLUSDT:80'
    assert d.risk_geometry['prior_low_ref'] == pytest.approx(97.5 - 1.618 * 16.0)


def test_no_setup_before_level_is_tested():
    ex = FibProjectionReversalExpert()
    rows = _up_spike_tape(close79=135.0, rng79=4.5)
    # Bar 78: the extension high (129.0) has not reached the 161.8% projection
    # (139.388) -> the projection test predicate does not hold.
    ev = ex.evaluate(_state(rows, 78))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_episode_key_stable_across_consecutive_spike_bars():
    """Two consecutive bars both testing and rejecting the same projection
    level anchor to the same run start -> the same episode_key (D-026)."""
    ex = FibProjectionReversalExpert()
    rows = _up_spike_tape(close79=135.0, rng79=4.5,
                          close80=134.0, rng80=5.5)     # bar 80: high 139.5 >= level
    d79 = _draft(rows, 79, ex)
    d80 = _draft(rows, 80, ex)
    assert d79.setup_anchor_event_id == d80.setup_anchor_event_id == 'SOLUSDT:80'
    keys = {episode_key(ex.expert_id, ex.version, d.instrument, d.direction,
                        d.setup_anchor_event_id, _geo(d)) for d in (d79, d80)}
    assert len(keys) == 1


# --- still_valid -------------------------------------------------------------

def test_still_valid_invalidation_and_fail_open():
    ex = FibProjectionReversalExpert()
    rows = _up_spike_tape(close79=135.0, rng79=4.5)
    draft = _draft(rows, 79, ex)
    ref = draft.risk_geometry['prior_high_ref']
    assert ref == pytest.approx(139.388)
    # Close below the frozen projection level: the extension was rejected,
    # reversal thesis alive.
    assert ex.still_valid(_state(rows, 79), draft) is True
    # Close back THROUGH the projection level: the extension continued after
    # all -> dead thesis.
    breach = _up_spike_tape(close79=135.0, rng79=4.5,
                            close80=140.5, rng80=1.0)   # close 140.5 > 139.388
    assert ex.still_valid(_state(breach, 80), draft) is False
    # Unobservable close: fail open.
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE,
                       features={}, lineage_hash='')
    assert ex.still_valid(bare, draft) is True


# --- variants (D-044 / rule 13) ----------------------------------------------

def test_variants_evaluated_complete_and_each_fires():
    ex = FibProjectionReversalExpert()
    assert ex.variant_id == 'a'
    assert set(ex.variants_evaluated) == set(ex._RATIO)
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)
    base = _up_spike_tape(close79=135.0, rng79=4.5)
    fibs = _state(base, 79).features['SOLUSDT.fib_levels'].value
    for variant, ratio in ex._RATIO.items():
        level = next(lv for r, lv in fibs[3] if abs(r - ratio) < 1e-9)
        vx = FibProjectionReversalExpert()
        vx.variant_id = variant
        d = _draft(_up_spike_tape(level - 2.0, level + 0.5 - (level - 2.0)),
                   79, vx)
        assert d.direction == 'SHORT'
        assert d.risk_geometry['prior_high_ref'] == pytest.approx(level)


# --- requires / consumption audit -------------------------------------------

def test_requires_audited_against_consumption():
    ex = FibProjectionReversalExpert()
    assert ex.requires, 'requires must be non-empty'
    consumed = {'close', 'atr', 'history', 'fib_levels', 'swing_high_10',
                'swing_low_10'}
    read_groups = {FEATURE_TO_GROUP[n] for n in consumed}
    allowed = set(ex.requires) | {'raw'}
    assert read_groups <= allowed


# --- lab smoke -----------------------------------------------------------------

def test_lab_run_smoke_verdict_stays_no_economic_claim(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-fib-13', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [FibProjectionReversalExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'              # rule 12
    assert sum(r.terminal_distribution.values()) == r.candidate_count
    lab2 = Lab(tmp_path / 'crafted')
    lab2.ingest(_up_spike_tape(close79=135.0, rng79=4.5))
    m2 = ExperimentManifest(experiment_id='exp-fib-13b', code_hash='', data_hash='',
                            universe=UNIVERSE, start_ns=0, end_ns=0)
    r2 = lab2.run(m2, [FibProjectionReversalExpert()])
    assert r2.candidate_count > 0
    assert r2.verdict == 'NO_ECONOMIC_CLAIM'
