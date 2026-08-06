"""Fib-retracement-continuation expert tests (E-12).

Covers: setup detection on a known up-impulse pullback-reclaim and its
down-impulse mirror; no-setup rejection; D-026 episode-key stability across
consecutive decision clocks; the frozen 78.6% invalidation reference;
still_valid invalidation + fail-open; variants_evaluated completeness (D-044)
with one crafted tape per retracement ratio; requires-vs-consumption; and a
lab.run smoke test that never implies an economic claim (rule 12).
"""
from __future__ import annotations

import pytest

from v8.schema import (TapeRow, MarketState, CandidateDraft, ExperimentManifest,
                       FEATURE_TO_GROUP, sha1_hex)
from v8.marketstate import build_state
from v8.lifecycle import episode_key
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.lab import Lab
from v8.experts.fib_retracement_continuation import (
    FibRetracementContinuationExpert, DEEP_RETRACEMENT)

UNIVERSE = ('SOLUSDT',)

# The up-impulse tape (impulse high at bar 66): swing low 97, swing high 113,
# range 16. Retracement levels are anchor - ratio*range (38.2% -> 106.888,
# 50% -> 105.0, 61.8% -> 103.112, 23.6% -> 109.224, 78.6% -> 100.424).


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


def _up_tape(reclaim_close: float, reclaim_low: float):
    """Up-impulse tape (low bar 61, high bar 66) with a 10-bar pullback
    (67..75), a reclaim bar at 76 whose low dips to `reclaim_low` and whose
    close is `reclaim_close`, then drift up."""
    closes = [100.0] * 60
    closes += [99.0, 98.0, 100.0, 104.0, 107.0, 110.0, 112.0]
    closes += [111.0, 110.0, 109.0, 108.5, 108.0, 107.5, 107.0, 106.8, 106.5]
    closes.append(reclaim_close)                       # bar 76: reclaim
    closes += [reclaim_close + 0.8, reclaim_close + 1.5, reclaim_close + 2.0]

    def rng(i):
        if i < 60:
            return 0.3
        if i == 76:
            return max(1.0, reclaim_close - reclaim_low + 0.4)
        return 1.0
    return _tape(closes, rng)


def _crash_tape() -> list[TapeRow]:
    """The base up-tape followed by a price crash below the frozen 78.6% level,
    for the still_valid dead-thesis check. Appended rows continue the event
    clock and ids (no collisions with the base tape)."""
    base = _up_tape_base()
    rows = list(base)
    start = len(base)                                  # 80 bars (0..79)
    for j, c in enumerate((99.5, 99.0)):
        i = start + j
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c + 1.0, 'low': c - 1.0, 'close': c,
                     'volume': 1.0, 'closed': True}))
    return rows


def _up_tape_base() -> list[TapeRow]:
    """The fixed detection tape: pullback low 106.0, reclaim close 107.0 at
    bar 76 (a 38.2% reclaim)."""
    return _up_tape(107.0, 106.0)


def _down_tape() -> list[TapeRow]:
    """Down-impulse mirror (high bar 60, low bar 66, range 16): rally 67..75
    toward the 38.2% retracement (103.112), then a spike-reject bar 76 that
    reaches the level and closes back below it."""
    closes = [100.0] * 60
    closes += [112.0, 110.0, 108.0, 106.0, 104.0, 102.0, 98.0]
    closes += [99.0, 100.0, 101.0, 102.0, 102.5, 103.0, 103.2, 103.0]
    closes += [101.5, 101.0, 100.5, 100.0]

    def rng(i):
        if i < 60:
            return 0.3
        if i == 76:
            return 3.5                     # spike-reject bar
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

def test_long_setup_detection_on_up_impulse_reclaim():
    ex = FibRetracementContinuationExpert()          # variant a: 38.2%
    rows = _up_tape_base()
    d = _draft(rows, 76, ex)
    assert d.direction == 'LONG'
    assert d.setup_anchor_event_id == 'SOLUSDT:77'   # first bar of the reclaim run
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['stop_r'] == 1.0
    assert g['expiry_bars'] == 8
    # atr_ref is the state's 14-bar ATR: a positive declared risk unit (D-028).
    atr = _state(rows, 76).features['SOLUSDT.atr'].value
    assert g['atr_ref'] == pytest.approx(atr)
    assert g['atr_ref'] > 0.0
    # The frozen invalidation reference is the deepest retracement (78.6%).
    assert g['prior_low_ref'] == pytest.approx(113.0 - DEEP_RETRACEMENT * 16.0)


def test_short_setup_detection_on_down_impulse_reject():
    ex = FibRetracementContinuationExpert()
    rows = _down_tape()
    d = _draft(rows, 76, ex)
    assert d.direction == 'SHORT'
    assert d.setup_anchor_event_id == 'SOLUSDT:77'
    # Down-impulse: retracements lie ABOVE the anchor low (97); the deepest
    # (78.6%) is 97 + 0.786*16 = 109.576 and becomes the frozen prior_high_ref.
    assert d.risk_geometry['prior_high_ref'] == pytest.approx(
        97.0 + DEEP_RETRACEMENT * 16.0)
    assert d.risk_geometry['target_r'] == 1.0
    assert d.risk_geometry['stop_r'] == 1.0


def test_setup_rejected_before_run_and_after_run():
    ex = FibRetracementContinuationExpert()
    rows = _up_tape_base()
    # Bar 75: the fib anchor high (bar 66) is not yet flank-confirmed -> habitat
    # unavailable (fib_levels absent during warmup).
    assert ex.evaluate(_state(rows, 75)).decision == 'NO_HABITAT'
    # Bar 78: price has moved well above the 38.2% level (low > level) -> the
    # pullback-reclaim predicate no longer holds -> NO_SETUP.
    ev = ex.evaluate(_state(rows, 78))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_episode_key_stable_across_consecutive_clocks():
    """The same reclaim run observed on two consecutive decision clocks hashes
    to the same key (D-026): the anchor (run start) is unchanged, so dedup can
    fire."""
    ex = FibRetracementContinuationExpert()
    rows = _up_tape_base()
    d76 = _draft(rows, 76, ex)
    d77 = _draft(rows, 77, ex)
    assert d76.setup_anchor_event_id == d77.setup_anchor_event_id == 'SOLUSDT:77'
    keys = {episode_key(ex.expert_id, ex.version, d.instrument, d.direction,
                        d.setup_anchor_event_id, _geo(d)) for d in (d76, d77)}
    assert len(keys) == 1


# --- still_valid -------------------------------------------------------------

def test_still_valid_invalidation_and_fail_open():
    ex = FibRetracementContinuationExpert()
    rows = _up_tape_base()
    draft = _draft(rows, 76, ex)
    ref = draft.risk_geometry['prior_low_ref']
    assert ref == pytest.approx(100.424)
    # Above the deep level: thesis alive.
    assert ex.still_valid(_state(rows, 77), draft) is True
    # Price crashing below the frozen deep level: deep correction -> dead.
    crash = _crash_tape()
    assert ex.still_valid(_state(crash, 80), draft) is False
    # Unobservable close: fail open (an unreadable thesis is not a dead one).
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE,
                       features={}, lineage_hash='')
    assert ex.still_valid(bare, draft) is True


# --- variants (D-044 / rule 13) ----------------------------------------------

def test_variants_evaluated_complete_and_each_fires():
    ex = FibRetracementContinuationExpert()
    assert ex.variant_id == 'a'
    assert set(ex.variants_evaluated) == set(ex._RATIO)
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)
    # Every retracement-ratio variant must fire on a tape whose pullback reaches
    # its level and is reclaimed by a close (losers listed, none skipped).
    base = _up_tape_base()
    fibs = _state(base, 76).features['SOLUSDT.fib_levels'].value
    for variant, ratio in ex._RATIO.items():
        level = next(lv for r, lv in fibs[2] if abs(r - ratio) < 1e-9)
        rows = _up_tape(level + 0.3, level - 0.8)
        vx = FibRetracementContinuationExpert()
        vx.variant_id = variant
        d = _draft(rows, 76, vx)
        assert d.direction == 'LONG'
        assert d.risk_geometry['prior_low_ref'] == pytest.approx(
            next(lv for r, lv in fibs[2] if abs(r - DEEP_RETRACEMENT) < 1e-9))


# --- requires / consumption audit -------------------------------------------

def test_requires_audited_against_consumption():
    ex = FibRetracementContinuationExpert()
    assert ex.requires, 'requires must be non-empty'
    consumed = {'close', 'atr', 'history', 'fib_levels'}
    read_groups = {FEATURE_TO_GROUP[n] for n in consumed}
    allowed = set(ex.requires) | {'raw'}
    assert read_groups <= allowed


# --- lab smoke -----------------------------------------------------------------

def test_lab_run_smoke_verdict_stays_no_economic_claim(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-fib-12', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [FibRetracementContinuationExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'            # rule 12
    assert sum(r.terminal_distribution.values()) == r.candidate_count
    # The setup is engineered to fire on the crafted tape through the full
    # lifecycle too (no fabricated trade path).
    lab2 = Lab(tmp_path / 'crafted')
    lab2.ingest(_up_tape_base())
    m2 = ExperimentManifest(experiment_id='exp-fib-12b', code_hash='', data_hash='',
                            universe=UNIVERSE, start_ns=0, end_ns=0)
    r2 = lab2.run(m2, [FibRetracementContinuationExpert()])
    assert r2.candidate_count > 0
    assert r2.verdict == 'NO_ECONOMIC_CLAIM'
