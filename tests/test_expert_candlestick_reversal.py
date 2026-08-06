"""E-04 candlestick_reversal expert tests (`bar_shape_reversal` family).

Crafted 1h tapes with verbatim OHLC for the exact Ch14.2 pattern predicates,
plus synthetic-tape lab smoke. Cover: setup detection per pattern variant,
no-setup rejection, no-habitat on warmup, still_valid trigger-cross
invalidation + fail-open, risk-geometry values (book pattern-extreme stop in
R, frozen trigger), D-044 variants_evaluated completeness, unknown-variant
fail-closed, requires-vs-consumption audit, determinism.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, MarketState, \
    FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.candlestick_reversal import CandlestickReversalExpert

UNIVERSE = ('SOLUSDT',)


def _bar(o, h, l, c, i):
    return TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                   event_time=HOUR_NS * i, available_time=HOUR_NS * i,
                   ingested_time=HOUR_NS * i, venue_sequence=i + 1,
                   event_id=f'SOLUSDT:{i + 1}',
                   payload={'open': o, 'high': h, 'low': l, 'close': c,
                            'volume': 1.0, 'closed': True})


def _tape(bars, start=0):
    return [_bar(o, h, l, c, i) for i, (o, h, l, c) in enumerate(bars, start=start)]


def _state_at(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of], as_of, UNIVERSE)


def _decline(n=31, start=110.0, step=0.3):
    """n down bars: close falls by step each bar; small fixed range (1.0)."""
    out = []
    for i in range(n):
        c = start - step * i
        o = c + 0.2
        out.append((o, o + 0.4, c - 0.4, c))
    return out


def _rally(n=31, start=100.0, step=0.3):
    """n up bars: close rises by step each bar; small fixed range (1.0)."""
    out = []
    for i in range(n):
        c = start + step * i
        o = c - 0.2
        out.append((o, c + 0.4, o - 0.4, c))
    return out


# --- ontology + D-044 variant accounting ------------------------------------

def test_ontology_and_variants_evaluated():
    e = CandlestickReversalExpert()
    assert e.expert_id == 'candlestick_reversal'
    assert e.mechanism_family_id == 'bar_shape_reversal'
    assert e.behavior_family_id == 'candlestick_reversal'
    assert set(e.requires) == {'candle_shape', 'volatility', 'history'}
    assert set(e.variants_evaluated) == {
        'hammer', 'shooting_star', 'bullish_engulfing', 'bearish_engulfing',
        'bullish_harami', 'bearish_harami', 'three_white_soldiers',
        'three_black_crows'}
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)
    for vid in e.variants_evaluated:
        assert CandlestickReversalExpert(variant_id=vid).variant_id == vid


def test_unknown_variant_fails_closed():
    try:
        CandlestickReversalExpert(variant_id='doji')
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- setup detection per pattern ---------------------------------------------

def test_hammer_detected():
    rows = _tape(_decline() + [(99.5, 100.2, 96.0, 100.0)])
    st = _state_at(rows, 31)
    ev = CandlestickReversalExpert(variant_id='hammer').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'hammer'
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['expiry_bars'] == 8
    atr = float(st.features['SOLUSDT.atr'].value)
    assert g['atr_ref'] == atr
    assert g['stop_ref'] == 96.0            # the pattern extreme (hammer low)
    assert g['trigger_ref'] == 100.2        # high of the hammer itself
    assert g['prior_low_ref'] == 96.0
    assert abs(g['stop_r'] - (100.0 - 96.0) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:32'


def test_shooting_star_detected():
    rows = _tape(_rally() + [(100.5, 104.0, 99.8, 100.0)])
    st = _state_at(rows, 31)
    ev = CandlestickReversalExpert(variant_id='shooting_star').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'shooting_star'
    assert g['stop_ref'] == 104.0           # high of the reversal candle
    assert abs(g['trigger_ref'] - 108.4) < 1e-9   # low of the PRECEDING candle
    assert g['prior_high_ref'] == 104.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (104.0 - 100.0) / atr) < 1e-9


def test_bullish_engulfing_detected():
    rows = _tape(_decline() + [(100.5, 103.4, 100.0, 103.0)])
    st = _state_at(rows, 31)
    ev = CandlestickReversalExpert(variant_id='bullish_engulfing').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['stop_ref'] == 100.0           # low of the second (engulfing) bar
    assert g['trigger_ref'] == 103.4        # high of the second bar
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (103.0 - 100.0) / atr) < 1e-9


def test_bearish_engulfing_detected():
    rows = _tape(_rally() + [(109.5, 109.8, 105.6, 106.0)])
    st = _state_at(rows, 31)
    ev = CandlestickReversalExpert(variant_id='bearish_engulfing').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['stop_ref'] == 109.8           # high of the second bar
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (109.8 - 106.0) / atr) < 1e-9


def test_bullish_harami_detected():
    bars = _decline()
    bars[30] = (101.6, 101.8, 100.6, 100.8)          # big down body
    bars += [(101.0, 101.3, 100.9, 101.2)]           # small bullish inside
    rows = _tape(bars)
    st = _state_at(rows, 31)
    ev = CandlestickReversalExpert(variant_id='bullish_harami').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['stop_ref'] == 100.6           # low of the FIRST candle
    assert g['trigger_ref'] == 101.8        # high of the FIRST candle
    f = st.features
    atr = float(f['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (101.2 - 100.6) / atr) < 1e-9


def test_bearish_harami_detected():
    bars = _rally()
    bars[30] = (100.8, 101.8, 100.6, 101.6)          # big up body
    bars += [(101.2, 101.3, 100.9, 101.0)]           # small bearish inside
    rows = _tape(bars)
    ev = CandlestickReversalExpert(variant_id='bearish_harami').evaluate(
        _state_at(rows, 31))
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['stop_ref'] == 101.8           # high of the FIRST candle
    assert g['trigger_ref'] == 100.6        # low of the FIRST candle


def test_three_white_soldiers_detected():
    bars = _decline(n=28)
    bars += [(102.1, 102.5, 101.5, 101.9)]           # last decline bar
    bars += [(102.0, 103.2, 101.8, 103.0),           # soldier 1
             (103.0, 104.2, 102.8, 104.0),           # soldier 2
             (104.0, 105.2, 103.8, 105.0)]           # soldier 3
    rows = _tape(bars)
    st = _state_at(rows, 31)
    ev = CandlestickReversalExpert(variant_id='three_white_soldiers').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['stop_ref'] == 101.8           # low of the FIRST candle
    assert g['trigger_ref'] == 104.2        # high of the SECOND candle
    f = st.features
    atr = float(f['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (105.0 - 101.8) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:32'


def test_three_black_crows_detected():
    bars = _rally(n=28)
    bars += [(101.9, 102.5, 101.5, 102.1)]           # last rally bar
    bars += [(105.0, 105.2, 103.8, 104.0),           # crow 1
             (104.0, 104.2, 102.8, 103.0),           # crow 2
             (103.0, 103.2, 101.8, 102.0)]           # crow 3
    rows = _tape(bars)
    ev = CandlestickReversalExpert(variant_id='three_black_crows').evaluate(
        _state_at(rows, 31))
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['stop_ref'] == 105.2           # high of the FIRST candle
    assert g['trigger_ref'] == 102.8        # low of the SECOND candle


# --- rejection paths ---------------------------------------------------------

def test_no_setup_on_flat_tape():
    """A flat tape (no reversal pattern, no decline/rally context) never
    fires any variant: NO_SETUP."""
    bars = [(100.0, 100.6, 99.4, 100.0)] * 40
    rows = _tape(bars)
    st = _state_at(rows, 39)
    for vid in CandlestickReversalExpert.variants_evaluated:
        ev = CandlestickReversalExpert(variant_id=vid).evaluate(st)
        assert ev.decision == 'NO_SETUP', vid
        assert ev.draft is None


def test_no_habitat_on_warmup():
    """10 bars: the 14-bar ATR is warmup-gated -> NO_HABITAT."""
    rows = _tape(_decline(n=10))
    ev = CandlestickReversalExpert().evaluate(_state_at(rows, 9))
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


# --- still_valid -------------------------------------------------------------

def test_still_valid_hammer_trigger_cross():
    e = CandlestickReversalExpert(variant_id='hammer')
    rows = _tape(_decline() + [(99.5, 100.2, 96.0, 100.0)])
    ev = e.evaluate(_state_at(rows, 31))
    assert ev.draft is not None
    assert ev.draft.risk_geometry['trigger_ref'] == 100.2
    # A later close above the frozen trigger keeps the thesis alive.
    tail = _tape([(100.0, 101.2, 99.8, 101.0), (101.0, 101.4, 98.6, 99.0)],
                 start=32)
    rows2 = rows + tail
    assert e.still_valid(_state_at(rows2, 32), ev.draft) is True
    # A close back below the trigger says the follow-through failed.
    assert e.still_valid(_state_at(rows2, 33), ev.draft) is False


def test_still_valid_short_shooting_star():
    e = CandlestickReversalExpert(variant_id='shooting_star')
    rows = _tape(_rally() + [(100.5, 104.0, 99.8, 100.0)])
    ev = e.evaluate(_state_at(rows, 31))
    assert ev.draft is not None and ev.draft.direction == 'SHORT'
    tail = _tape([(100.0, 108.0, 99.0, 99.5), (99.5, 109.0, 99.0, 109.0)],
                 start=32)
    rows2 = rows + tail
    assert e.still_valid(_state_at(rows2, 32), ev.draft) is True
    assert e.still_valid(_state_at(rows2, 33), ev.draft) is False


def test_still_valid_fail_open():
    e = CandlestickReversalExpert(variant_id='hammer')
    draft = CandidateDraft(
        expert_id='candlestick_reversal', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'hammer', 'trigger_ref': 100.2},
        birth_time=0)
    st = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                     lineage_hash='h')
    assert e.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ----------------------------------

def test_requires_audited_against_consumption():
    e = CandlestickReversalExpert()
    for g in e.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'real_body', 'body_range_ratio',
                   'upper_shadow', 'lower_shadow', 'close_position'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape(_decline() + [(99.5, 100.2, 96.0, 100.0)])
    e = CandlestickReversalExpert(variant_id='hammer')
    a = e.evaluate(_state_at(rows, 31))
    b = e.evaluate(_state_at(rows, 31))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id
    assert a.draft.birth_time == b.draft.birth_time


def test_lab_smoke_no_economic_claim(tmp_path):
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e04', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [CandlestickReversalExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
