"""E-09 failed_breakout expert tests (`failed_breakout` registered family).

Crafted 1h tapes for the two-step hypothesis — a prior bar must first CLOSE
above its own prior high (the breakout leg, Ch7.3 p228) before a later close
back below that level is a failed-breakout SHORT. Cover: the two-step gate
(no-setup on a plain downtrend with no breakout anywhere), the frozen
breakout-level reference, the anchor being the first failure bar after the
breakout, fresh-high rejection, no-habitat warmup, still_valid invalidation
and fail-open.
"""
from __future__ import annotations

import pytest

from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.schema import MarketState, CandidateDraft, TapeRow
from v8.experts.failed_breakout import FailedBreakoutExpert

UNIVERSE = ('SOLUSDT',)


def _bar(o, h, l, c, i):
    return TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                   event_time=HOUR_NS * i, available_time=HOUR_NS * i,
                   ingested_time=HOUR_NS * i, venue_sequence=i + 1,
                   event_id=f'SOLUSDT:{i + 1}',
                   payload={'open': o, 'high': h, 'low': l, 'close': c,
                            'volume': 1000.0, 'closed': True})


def _tape(bars, start=0):
    return [_bar(o, h, l, c, i) for i, (o, h, l, c) in enumerate(bars, start=start)]


def _state_at(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of], as_of, UNIVERSE)


def _f_level(bars, upto):
    """Max high of the bars strictly before index `upto`."""
    return max(b[1] for b in bars[:upto])


# --- ontology ----------------------------------------------------------------

def test_ontology():
    e = FailedBreakoutExpert()
    assert e.expert_id == 'failed_breakout'
    assert e.mechanism_family_id == 'liquidity_vacuum_reentry'
    assert e.behavior_family_id == 'failed_breakout_reentry'
    assert e.variant_id == 'a'
    assert set(e.requires) == {'location', 'volatility', 'history'}


# --- the two-step gate --------------------------------------------------------

def test_no_setup_on_downtrend_without_any_breakout():
    """Regression (B1): the old gate fired a SHORT on ANY close below the
    windowed prior high — a plain downtrend with no close-breakout anywhere
    produced a candidate. The thesis requires the breakout leg: no breakout,
    no failed breakout."""
    bars = []
    for i in range(32):
        o = 100.0 - i * 0.5
        bars.append((o, o + 0.2, o - 0.2, o + 0.1 if i % 2 else o - 0.1))
    rows = _tape(bars)
    st = _state_at(rows, len(rows) - 1)
    ev = FailedBreakoutExpert().evaluate(st)
    assert ev.applicability == 'NOT_APPLICABLE' and ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_candidate_after_breakout_then_fail():
    """A close above the prior max high (bar 10), then a close back below the
    SAME level is the valid two-step setup -> SHORT candidate with the frozen
    breakout level as prior_high_ref and the first failure bar as the anchor."""
    bars = []
    for i in range(32):
        o = 100.0 - i * 0.3
        if i < 10:
            bars.append((o, o + 0.5, o - 0.5, o))               # drift lower
        elif i == 10:
            prior = _f_level(bars, i)
            bars.append((o, o + 2.0, o - 0.5, prior + 1.0))     # breakout close
        else:
            lev = _f_level(bars, 10)
            bars.append((o, max(lev + 1.0, o + 0.5),
                         min(lev - 1.0, o - 0.5), lev - 0.5))   # fail below level
    rows = _tape(bars)
    st = _state_at(rows, len(rows) - 1)
    ev = FailedBreakoutExpert().evaluate(st)
    assert ev.applicability == 'APPLICABLE' and ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d is not None
    assert d.direction == 'SHORT'
    assert d.risk_geometry['prior_high_ref'] == pytest.approx(_f_level(bars, 10))
    assert d.risk_geometry['entry'] == 'NEXT_BAR_CLOSE'
    # the anchor is the FIRST failure bar after the breakout (bar 11, event
    # 'SOLUSDT:12'), not the newest bar — episode-key dedup is stable across
    # the failure run.
    assert d.setup_anchor_event_id == 'SOLUSDT:12'


def test_no_setup_on_fresh_high():
    """A bar whose close is below its prior max high but that never had a
    close-breakout is not a failure -> NO_SETUP."""
    bars = []
    for i in range(32):
        o = 100.0 + i * 0.3
        bars.append((o, o + 0.5, o - 0.5, o + 0.1))
    rows = _tape(bars)
    st = _state_at(rows, len(rows) - 1)
    ev = FailedBreakoutExpert().evaluate(st)
    assert ev.applicability == 'NOT_APPLICABLE' and ev.decision == 'NO_SETUP'


def test_no_setup_while_close_above_breakout_level():
    """A failure bar must have closed BACK BELOW the breakout level; a close
    still above it is not a failure."""
    bars = []
    for i in range(32):
        o = 100.0 - i * 0.3
        if i < 10:
            bars.append((o, o + 0.5, o - 0.5, o))
        elif i == 10:
            prior = _f_level(bars, i)
            bars.append((o, o + 2.0, o - 0.5, prior + 1.0))     # breakout
        else:
            lev = _f_level(bars, 10)
            bars.append((o, lev + 1.5, lev + 0.5, lev + 0.8))   # stays above level
    rows = _tape(bars)
    st = _state_at(rows, len(rows) - 1)
    ev = FailedBreakoutExpert().evaluate(st)
    assert ev.applicability == 'NOT_APPLICABLE' and ev.decision == 'NO_SETUP'


def test_no_habitat_on_warmup():
    rows = _tape([(100.0, 100.5, 99.5, 100.0)] * 5)
    st = _state_at(rows, len(rows) - 1)
    ev = FailedBreakoutExpert().evaluate(st)
    assert ev.applicability == 'NOT_APPLICABLE' and ev.decision == 'NO_HABITAT'


# --- still_valid --------------------------------------------------------------

def _state_with_close(close_value):
    features = {f'{UNIVERSE[0]}.close': close_value} \
        if close_value is not None else {}
    return MarketState(universe=UNIVERSE, as_of=0, state_id='s',
                       features=features, lineage_hash='h')


def _short_draft(level=100.5):
    return CandidateDraft(expert_id='failed_breakout', expert_version='v1',
                          instrument='SOLUSDT', direction='SHORT',
                          setup_fingerprint='f', risk_geometry={'prior_high_ref': level},
                          birth_time=0, setup_anchor_event_id='a')


def test_still_valid_short_holds_below_and_invalidates_above_frozen_level():
    e = FailedBreakoutExpert()
    draft = _short_draft(level=100.5)
    from v8.schema import FeatureValue
    below = _state_with_close(FeatureValue(f'{UNIVERSE[0]}.close', 99.0,
                                           'close', 'v1', 0))
    above = _state_with_close(FeatureValue(f'{UNIVERSE[0]}.close', 101.0,
                                           'close', 'v1', 0))
    assert e.still_valid(below, draft) is True
    assert e.still_valid(above, draft) is False


def test_still_valid_fails_open_when_close_unobservable():
    e = FailedBreakoutExpert()
    st = _state_with_close(None)
    assert e.still_valid(st, _short_draft()) is True
