"""E-20 market_profile_value_area expert tests (`value_area_reversion` family).

Covers: D-044/D-046 variant accounting, prior-session POC / value-area /
pressure-gauge setup detection on crafted profiles, no-setup / no-habitat
rejection, risk_geometry values (book POC target + prior-day-range stop in R),
still_valid invalidation + fail-open, D-026 anchor stability, requires-vs-
consumption audit, determinism, and a lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, MarketState, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.market_profile_value_area import (
    MarketProfileValueAreaExpert, _tpo_profile)

UNIVERSE = ('SOLUSDT',)
VARIANTS = ('a', 'b', 'c', 'd')


def _bar(i, c):
    """Closed 1h bar with range exactly 0.5 (h = c+0.25, l = c-0.25) so the
    14-bar ATR is exactly 0.5 and the profile bucket is exactly 0.5."""
    return TapeRow(
        source='binance-um', channel='kline', instrument='SOLUSDT',
        event_time=HOUR_NS * i, available_time=HOUR_NS * i,
        ingested_time=HOUR_NS * i, venue_sequence=i + 1,
        event_id=f'SOLUSDT:{i + 1}',
        payload={'open': c, 'high': c + 0.25, 'low': c - 0.25, 'close': c,
                 'volume': 1.0, 'closed': True})


def _state(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _profile_a():
    """Prior day with an extreme-low tail: POC = 99.5 (bucket 199), VA =
    [99.0, 100.0], day range [98.75, 100.25]. Then bar 24 (bar_of_session 1)
    is the current bar."""
    return [_bar(i, c) for i, c in enumerate([99.0] * 4 + [99.5] * 8 + [100.0] * 12)]


def _profile_b():
    """Prior day with buying pressure: 8 bars at 99.5 + 16 bars at 100.0;
    POC = 99.5, above-POC share 16/24 = 0.667 >= 0.55."""
    return [_bar(i, c) for i, c in enumerate([99.5] * 8 + [100.0] * 16)]


# --- ontology + variants (D-044/D-046) --------------------------------------

def test_ontology_declared():
    e = MarketProfileValueAreaExpert()
    assert e.expert_id == 'market_profile_value_area'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'value_area_reversion'
    assert e.behavior_family_id == 'value_area_reversion'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == VARIANTS
    assert set(e.requires) == {'session', 'volatility', 'history'}


def test_variants_evaluated_completeness():
    e = MarketProfileValueAreaExpert()
    assert set(e.variants_evaluated) == set(VARIANTS)
    assert e.variant_id in e.variants_evaluated
    # The book card enumerates variants a..e; `e` (six-degrees classification)
    # is behavioral and dropped before evaluation, so the consumed search is 5.
    assert e.search_universe_size == 5 >= len(e.variants_evaluated)
    for vid in VARIANTS:
        assert MarketProfileValueAreaExpert(vid).variant_id == vid


def test_unknown_variant_fails_closed():
    try:
        MarketProfileValueAreaExpert('zz').evaluate(
            _state(_profile_a() + [_bar(24, 99.3)], 24))
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- setup detection per variant --------------------------------------------

def test_variant_a_long_below_poc():
    rows = _profile_a() + [_bar(24, 99.3)]
    ev = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 24))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'a'
    assert d.setup_anchor_event_id == 'SOLUSDT:25'
    assert d.risk_geometry['poc_ref'] == 99.5


def test_variant_a_short_above_poc():
    rows = _profile_a() + [_bar(24, 99.8)]
    ev = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 24))
    assert ev.decision == 'CANDIDATE'
    assert ev.draft.direction == 'SHORT'
    assert ev.draft.risk_geometry['poc_ref'] == 99.5


def test_variant_b_long_beyond_va_low():
    rows = _profile_a() + [_bar(24, 98.9)]
    ev = MarketProfileValueAreaExpert('b').evaluate(_state(rows, 24))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'b'
    assert d.risk_geometry['va_low_ref'] == 99.0


def test_variant_c_buying_pressure_long():
    rows = _profile_b() + [_bar(24, 100.1)]
    ev = MarketProfileValueAreaExpert('c').evaluate(_state(rows, 24))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'c'
    # Initiative: target is the prior-day range high, hold level the POC.
    assert d.risk_geometry['target_r'] > 0
    assert d.risk_geometry['prior_low_ref'] == d.risk_geometry['poc_ref']


def test_variant_d_deep_deviation_long():
    rows = _profile_a() + [_bar(24, 99.0)]
    ev = MarketProfileValueAreaExpert('d').evaluate(_state(rows, 24))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'd'
    # close 99.0 is >= 0.5 * ATR (0.25) below the POC 99.5.
    assert d.risk_geometry['poc_ref'] - d.risk_geometry['target_r'] * d.risk_geometry['atr_ref'] \
        <= 99.0 + 1e-9


# --- no-setup / no-habitat ---------------------------------------------------

def test_no_setup_close_inside_value():
    """A close at the POC is neither below nor above it -> NO_SETUP."""
    rows = _profile_a() + [_bar(24, 99.5)]
    for vid in VARIANTS:
        ev = MarketProfileValueAreaExpert(vid).evaluate(_state(rows, 24))
        assert ev.decision in ('NO_SETUP', 'NO_HABITAT'), vid
        assert ev.draft is None


def test_no_setup_breaks_prior_day_low():
    """A close through the prior-day low (the stop reference) is not a clean
    reversion -> NO_SETUP."""
    rows = _profile_a() + [_bar(24, 98.5)]
    ev = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 24))
    assert ev.decision == 'NO_SETUP'


def test_no_setup_c_low_pressure_profile():
    """On a balanced profile neither pressure tail reaches 55% -> NO_SETUP."""
    rows = _profile_a() + [_bar(24, 100.1)]
    ev = MarketProfileValueAreaExpert('c').evaluate(_state(rows, 24))
    assert ev.decision == 'NO_SETUP'


def test_no_habitat_on_warmup():
    """Too short a tape: no prior session -> NO_HABITAT."""
    rows = _profile_a()[:10]
    ev = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 9))
    assert ev.decision == 'NO_HABITAT'
    assert ev.draft is None


def test_profile_helper_matches_book_algorithm():
    """The 68% value-area expansion and POC tie-breaks (Ch17.1 p656-657)."""
    prior = _profile_a()[:24]
    # The profile consumes the marketstate history-tuple shape
    # (event_id, open, high, low, close, ema_fast, ema_slow).
    hist_bars = tuple((b.event_id, b.payload['open'], b.payload['high'],
                       b.payload['low'], b.payload['close'], 0.0, 0.0)
                      for b in prior)
    poc, va_low, va_high, total, above, below = _tpo_profile(hist_bars, 0.5, 0.68)
    assert total == 48
    assert poc == 99.5 and va_low == 99.0 and va_high == 100.0
    # Shares of the two tails around the POC (above 12, below 16 of 48).
    assert above == 12 / 48 and below == 16 / 48


# --- risk geometry -----------------------------------------------------------

def test_risk_geometry_values():
    rows = _profile_a() + [_bar(24, 99.3)]
    d = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 24)).draft
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['expiry_bars'] == 8
    assert g['atr_ref'] == 0.5
    assert g['variant'] == 'a'
    assert g['poc_ref'] == 99.5
    assert g['prior_low_ref'] == 98.75
    # Target = reversion to the POC, stop = beyond the prior-day low, in R.
    assert g['target_r'] == (99.5 - 99.3) / 0.5
    assert g['stop_r'] == (99.3 - 98.75) / 0.5


# --- still_valid -------------------------------------------------------------

def test_still_valid_invalidated_through_hold_level():
    e = MarketProfileValueAreaExpert('a')
    rows = _profile_a() + [_bar(24, 99.3)]
    draft = e.evaluate(_state(rows, 24)).draft
    assert e.still_valid(_state(rows, 24), draft) is True
    # A later close through the frozen prior-day low kills the reversion.
    later = _profile_a() + [_bar(24, 99.3), _bar(25, 98.5)]
    assert e.still_valid(_state(later, 25), draft) is False


def test_still_valid_fail_open():
    e = MarketProfileValueAreaExpert('a')
    draft = e.evaluate(_state(_profile_a() + [_bar(24, 99.3)], 24)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- D-026 anchor stability --------------------------------------------------

def test_anchor_stable_across_consecutive_clocks():
    """The setup anchor (first bar of the run below the POC) is stable while
    the deviation persists (D-026)."""
    e = MarketProfileValueAreaExpert('a')
    rows = _profile_a() + [_bar(24, 99.3), _bar(25, 99.2)]
    d1 = e.evaluate(_state(rows, 24)).draft
    d2 = e.evaluate(_state(rows, 25)).draft
    assert d1.setup_anchor_event_id == d2.setup_anchor_event_id == 'SOLUSDT:25'


# --- registry audit + determinism + lab -------------------------------------

def test_requires_audited_against_consumption():
    e = MarketProfileValueAreaExpert()
    assert all(g in FEATURE_GROUPS for g in e.requires)
    consumption = {'close', 'atr', 'history', 'bar_of_session'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _profile_a() + [_bar(24, 99.3)]
    a = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 24))
    b = MarketProfileValueAreaExpert('a').evaluate(_state(rows, 24))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    """Rule-12 guard: a lab run on the synthetic tape never implies an
    economic claim."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=31, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-e20', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [MarketProfileValueAreaExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')
