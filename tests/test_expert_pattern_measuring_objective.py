"""E-14 pattern_measuring_objective expert tests (`geometric_pattern_breakout`
family).

Crafted 1h tapes with verbatim OHLC for the exact Ch13 pattern predicates,
plus synthetic-tape lab smoke. Cover: setup detection per pattern (H&S top/
bottom, double top/bottom, triangle), the 1:1 measuring-objective target in R
(the book's Ch13.2 p499-501 doctrine), book stops, no-setup rejection (missing
structure, missing prior consolidation), no-habitat on warmup, still_valid
completion-line invalidation + fail-open, D-044 variants_evaluated
completeness, requires-vs-consumption audit, determinism.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, MarketState, \
    FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.pattern_measuring_objective import PatternMeasuringObjectiveExpert

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


# --- ontology + D-044 variant accounting ------------------------------------

def test_ontology_and_variants_evaluated():
    e = PatternMeasuringObjectiveExpert()
    assert e.expert_id == 'pattern_measuring_objective'
    assert e.mechanism_family_id == 'geometric_pattern_breakout'
    assert e.behavior_family_id == 'geometric_pattern_breakout'
    assert set(e.requires) == {'location', 'volatility', 'history'}
    assert set(e.variants_evaluated) == {'head_shoulders', 'double_top',
                                         'triangle'}
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)
    for vid in e.variants_evaluated:
        assert PatternMeasuringObjectiveExpert(variant_id=vid).variant_id == vid


def test_unknown_variant_fails_closed():
    try:
        PatternMeasuringObjectiveExpert(variant_id='rounding_bottom')
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- head and shoulders ------------------------------------------------------

def _hs_top_tape():
    return [
        (100.0, 100.3, 99.8, 100.1), (100.1, 100.7, 99.9, 100.5),
        (100.5, 101.1, 100.3, 100.9),
        (100.9, 102.0, 100.6, 101.5),                 # left shoulder
        (101.5, 101.8, 101.0, 101.2), (101.2, 101.6, 100.6, 100.8),
        (100.8, 101.4, 100.2, 100.4),
        (100.4, 100.6, 99.6, 99.8),                   # left trough
        (99.8, 101.2, 99.9, 100.2), (100.2, 101.6, 100.3, 100.6),
        (100.6, 102.0, 100.7, 101.0),
        (101.0, 105.0, 100.8, 104.2),                 # head
        (104.2, 104.0, 103.0, 103.2), (103.2, 103.0, 102.0, 102.2),
        (102.2, 102.0, 101.0, 101.2),
        (101.2, 101.2, 100.2, 100.5),                 # right trough
        (100.5, 100.6, 100.3, 100.4), (100.4, 100.8, 100.4, 100.6),
        (101.0, 102.6, 100.8, 102.2),                 # right shoulder
        (101.0, 101.2, 100.0, 100.1),                 # neckline break
        (100.1, 100.4, 99.7, 99.9), (99.9, 100.2, 99.5, 99.7),
    ]


def test_head_shoulders_top_breakout():
    rows = _tape(_hs_top_tape())
    st = _state_at(rows, 21)          # right shoulder confirmed (flank 3)
    ev = PatternMeasuringObjectiveExpert(variant_id='head_shoulders').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'head_shoulders'
    assert abs(g['level_ref'] - 100.2) < 1e-9    # the neckline
    assert g['stop_ref'] == 105.0                # beyond the head
    assert g['prior_high_ref'] == 105.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - 4.8 / atr) < 1e-9   # head-to-neckline 1:1
    assert abs(g['stop_r'] - (105.0 - 99.7) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:20'   # the break bar


def _hs_bottom_tape():
    return [
        (100.0, 100.3, 99.7, 99.9), (99.9, 100.1, 99.3, 99.5),
        (99.5, 99.7, 98.9, 99.1),
        (99.1, 99.3, 98.0, 98.5),                   # left shoulder
        (98.5, 99.0, 98.4, 98.7), (98.7, 99.4, 98.5, 99.0),
        (99.0, 99.8, 98.8, 99.4),
        (99.4, 99.9, 99.0, 99.5),                   # left peak
        (99.5, 99.7, 98.9, 99.1), (99.1, 99.3, 98.5, 98.7),
        (98.7, 98.9, 98.1, 98.3),
        (98.3, 98.5, 95.0, 95.8),                   # head
        (95.8, 97.0, 95.6, 96.6), (96.6, 97.8, 96.4, 97.4),
        (97.4, 98.6, 97.2, 98.2),
        (98.2, 99.0, 97.8, 98.6),                   # right peak
        (98.6, 98.8, 97.8, 98.0), (98.0, 98.2, 97.2, 97.4),
        (97.4, 97.6, 96.4, 96.8),                   # right shoulder
        (96.8, 99.6, 96.6, 99.2),                   # neckline break
        (99.2, 99.6, 99.0, 99.4), (99.4, 99.8, 99.2, 99.6),
    ]


def test_head_shoulders_bottom_breakout():
    rows = _tape(_hs_bottom_tape())
    st = _state_at(rows, 21)
    ev = PatternMeasuringObjectiveExpert(variant_id='head_shoulders').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert abs(g['level_ref'] - 99.0) < 1e-9    # the neckline (lower peak)
    assert g['stop_ref'] == 95.0                # beyond the head
    assert g['prior_low_ref'] == 95.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - 4.0 / atr) < 1e-9
    assert abs(g['stop_r'] - (99.6 - 95.0) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:20'


def test_head_shoulders_no_breakout_no_setup():
    """An H&S structure that never closes beyond the neckline is NO_SETUP."""
    rows = _tape(_hs_top_tape())
    bars = _hs_top_tape()
    bars[19] = (101.0, 101.4, 100.4, 100.6)     # no break: close above 100.2
    bars[20] = (100.6, 101.0, 100.4, 100.7)
    bars[21] = (100.7, 101.1, 100.5, 100.8)
    rows2 = _tape(bars)
    ev = PatternMeasuringObjectiveExpert(variant_id='head_shoulders').evaluate(
        _state_at(rows2, 21))
    assert ev.decision == 'NO_SETUP'


# --- double top / bottom -----------------------------------------------------

def _double_top_tape():
    bars = [(99.8, 100.4, 99.6, 100.0)] * 10
    bars += [(100.0, 102.0, 99.8, 101.5)]                # peak 1
    bars += [(101.5, 101.8, 100.3, 100.5),
             (100.5, 101.7, 100.2, 100.3),
             (100.3, 101.6, 100.1, 100.1),
             (100.1, 101.5, 100.0, 99.9),
             (99.9, 101.4, 99.9, 99.7)]
    bars += [(100.5, 100.9, 99.0, 99.3)]                 # validation trough 99
    bars += [(99.3, 99.6, 99.1, 99.4),
             (99.4, 99.8, 99.2, 99.6),
             (99.6, 100.0, 99.4, 99.8),
             (99.8, 100.3, 99.6, 100.1)]
    bars += [(100.4, 101.8, 100.2, 101.2)]               # peak 2
    bars += [(101.0, 101.2, 98.3, 98.5),                 # breakdown below 99
             (98.5, 98.8, 97.8, 98.0),
             (98.0, 98.4, 97.3, 97.5)]
    return bars


def test_double_top_validation_break():
    rows = _tape(_double_top_tape())
    st = _state_at(rows, 24)          # both peaks confirmed (flank 3)
    ev = PatternMeasuringObjectiveExpert(variant_id='double_top').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'double_top'
    assert g['level_ref'] == 99.0           # the validation level (trough)
    assert g['stop_ref'] == 102.0           # beyond the higher peak
    assert g['prior_high_ref'] == 102.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - 3.0 / atr) < 1e-9
    assert abs(g['stop_r'] - (102.0 - 97.5) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:23'   # the break bar


def _double_bottom_tape():
    bars = [(100.2, 100.7, 99.7, 100.0)] * 10
    bars += [(100.0, 100.6, 98.0, 98.5)]                 # trough 1
    bars += [(98.5, 100.3, 99.7, 99.5),
             (99.5, 100.5, 100.0, 100.2),
             (100.2, 101.0, 100.4, 100.6),
             (100.6, 101.4, 100.8, 101.0),
             (101.0, 101.8, 101.2, 101.4)]
    bars += [(101.4, 102.0, 100.9, 101.5)]               # validation peak 102
    bars += [(101.5, 101.8, 100.6, 100.9),
             (100.9, 101.2, 100.2, 100.5),
             (100.5, 100.8, 99.8, 100.1),
             (100.1, 100.4, 99.4, 99.7)]
    bars += [(99.7, 100.0, 98.2, 98.5)]                  # trough 2
    bars += [(99.0, 103.5, 98.9, 103.0),                 # breakout above 102
             (103.0, 104.0, 102.6, 103.5),
             (103.5, 104.5, 103.1, 104.0)]
    return bars


def test_double_bottom_validation_break():
    rows = _tape(_double_bottom_tape())
    st = _state_at(rows, 24)
    ev = PatternMeasuringObjectiveExpert(variant_id='double_top').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['level_ref'] == 102.0          # the validation level (peak)
    assert g['stop_ref'] == 98.0            # below the lower trough
    assert g['prior_low_ref'] == 98.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - 4.0 / atr) < 1e-9
    assert abs(g['stop_r'] - (104.0 - 98.0) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:23'


# --- triangle ----------------------------------------------------------------

def _triangle_tape():
    bars = [(99.9, 100.6, 99.3, 100.0)]                    # b0
    bars += [(100.0, 100.2, 99.8, 100.0)] * 4              # b1-b4
    bars += [(100.0, 100.2, 99.4, 100.0)]                  # b5  pivot low 99.4
    bars += [(100.0, 100.5, 99.7, 100.0)]                  # b6  pivot high 100.5
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b7
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b8
    bars += [(100.0, 100.4, 99.8, 100.0)]                  # b9  (high 100.4)
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b10
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b11
    bars += [(100.0, 100.1, 99.5, 100.0)]                  # b12 pivot low 99.5
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b13
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b14
    bars += [(100.0, 100.3, 99.9, 100.0)]                  # b15 pivot high 100.3
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b16
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b17
    bars += [(100.0, 100.1, 99.6, 100.0)]                  # b18 pivot low 99.6
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b19
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b20
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b21
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b22
    bars += [(100.0, 100.2, 99.8, 100.0)]                  # b23
    bars += [(100.0, 100.1, 99.9, 100.0)]                  # b24
    bars += [(100.0, 101.0, 99.9, 100.8)]                  # b25 breakout
    return bars


def test_triangle_breakout():
    rows = _tape(_triangle_tape())
    st = _state_at(rows, 25)
    ev = PatternMeasuringObjectiveExpert(variant_id='triangle').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'triangle'
    assert g['level_ref'] == 100.5          # the broken range high
    assert g['stop_ref'] == 99.4            # behind the opposite range bound
    assert g['prior_low_ref'] == 99.4
    atr = float(st.features['SOLUSDT.atr'].value)
    rh = float(st.features['SOLUSDT.range_height_20'].value)
    assert abs(g['target_r'] - rh / atr) < 1e-9    # 1:1 range-height target
    assert abs(g['stop_r'] - (100.8 - 99.4) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:26'


def test_triangle_no_consolidation_no_setup():
    """A flat tape never converges (no declining highs / rising lows) -> the
    triangle structure is absent -> NO_SETUP."""
    flat = [(100.0, 100.4, 99.6, 100.0)] * 26
    rows = _tape(flat)
    ev = PatternMeasuringObjectiveExpert(variant_id='triangle').evaluate(
        _state_at(rows, 25))
    assert ev.decision == 'NO_SETUP'


def test_triangle_breakout_without_prior_range_no_setup():
    """A close beyond the range that was NOT preceded by an in-range bar (no
    consolidation immediately before the break) is NO_SETUP."""
    bars = _triangle_tape()
    bars[24] = (100.3, 100.8, 100.2, 100.6)     # prev bar already beyond range
    rows = _tape(bars)
    ev = PatternMeasuringObjectiveExpert(variant_id='triangle').evaluate(
        _state_at(rows, 25))
    assert ev.decision == 'NO_SETUP'


# --- rejection paths ---------------------------------------------------------

def test_no_habitat_on_warmup():
    rows = _tape([(100.0, 100.4, 99.6, 100.0)] * 6)
    ev = PatternMeasuringObjectiveExpert().evaluate(_state_at(rows, 5))
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


def test_no_setup_on_flat_tape():
    flat = [(100.0, 100.4, 99.6, 100.0)] * 40
    rows = _tape(flat)
    st = _state_at(rows, 39)
    for vid in PatternMeasuringObjectiveExpert.variants_evaluated:
        ev = PatternMeasuringObjectiveExpert(variant_id=vid).evaluate(st)
        assert ev.decision == 'NO_SETUP', vid


# --- still_valid -------------------------------------------------------------

def test_still_valid_holds_and_invalidates():
    e = PatternMeasuringObjectiveExpert(variant_id='head_shoulders')
    rows = _tape(_hs_top_tape())
    ev = e.evaluate(_state_at(rows, 21))
    assert ev.draft is not None and ev.draft.direction == 'SHORT'
    tail = _tape([(99.5, 100.0, 99.0, 99.4), (99.4, 100.9, 99.4, 100.8)],
                 start=22)
    rows2 = rows + tail
    # bar 22 close 99.4 stays below the neckline -> thesis alive
    assert e.still_valid(_state_at(rows2, 22), ev.draft) is True
    # bar 23 close 100.8 back above the neckline -> pattern failed
    assert e.still_valid(_state_at(rows2, 23), ev.draft) is False


def test_still_valid_fail_open():
    e = PatternMeasuringObjectiveExpert(variant_id='triangle')
    draft = CandidateDraft(
        expert_id='pattern_measuring_objective', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 2.0,
                       'stop_r': 2.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'triangle', 'level_ref': 100.5},
        birth_time=0)
    st = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                     lineage_hash='h')
    assert e.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ----------------------------------

def test_requires_audited_against_consumption():
    e = PatternMeasuringObjectiveExpert()
    for g in e.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'window_high_20', 'window_low_20',
                   'range_height_20', 'consolidation_range'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape(_hs_top_tape())
    e = PatternMeasuringObjectiveExpert(variant_id='head_shoulders')
    a = e.evaluate(_state_at(rows, 21))
    b = e.evaluate(_state_at(rows, 21))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=17, n_bars=240))
    m = ExperimentManifest(experiment_id='exp-e14', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [PatternMeasuringObjectiveExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
