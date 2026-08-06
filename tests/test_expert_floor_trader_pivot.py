"""E-19 floor_trader_pivot expert tests (`pivot_level_reaction` family).

Crafted 1h tapes with a verbatim prior-day bar (the pivot set PP/S1..S4/
R1..R4 follows G-25 exactly) plus a reaction bar, and synthetic-tape lab
smoke. Cover: setup detection per variant (long and short), the level-ladder
targets and behind-the-line stops in R, no-setup rejection, no-habitat on
warmup, still_valid level-cross invalidation + fail-open, D-044
variants_evaluated completeness, requires-vs-consumption audit, determinism.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, MarketState, \
    FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.floor_trader_pivot import FloorTraderPivotExpert

UNIVERSE = ('SOLUSDT',)

# Prior-day bar: H=100, L=96, C=98 -> PP=(100+96+98)/3=98, R1=100, R2=102,
# R3=104, S1=96, S2=94, S3=92 (G-25; the current bar is bar 24, session 1).
BASE = (98.0, 100.0, 96.0, 98.0)


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


def _tape_with_reaction(reaction_bar):
    return _tape([BASE] * 24 + [reaction_bar])


# --- ontology + D-044 variant accounting ------------------------------------

def test_ontology_and_variants_evaluated():
    e = FloorTraderPivotExpert()
    assert e.expert_id == 'floor_trader_pivot'
    assert e.mechanism_family_id == 'pivot_level_reaction'
    assert e.behavior_family_id == 'pivot_level_reaction'
    assert set(e.requires) == {'location', 'volatility', 'history', 'session'}
    assert e.variants_evaluated == ('a', 'b', 'c', 'd')
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)
    for vid in e.variants_evaluated:
        assert FloorTraderPivotExpert(variant_id=vid).variant_id == vid


def test_unknown_variant_fails_closed():
    try:
        FloorTraderPivotExpert(variant_id='e')
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- variant a: PP drift -----------------------------------------------------

def test_variant_a_open_above_pp_drift_long():
    rows = _tape_with_reaction((98.5, 99.5, 98.3, 99.2))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='a').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'a'
    assert g['level_ref'] == 98.0            # PP
    assert g['prior_low_ref'] == 98.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (100.0 - 99.2) / atr) < 1e-9   # target R1
    assert abs(g['stop_r'] - (99.2 - 98.0) / atr) < 1e-9      # stop behind PP
    assert d.setup_anchor_event_id == 'SOLUSDT:25'


def test_variant_a_open_below_pp_drift_short():
    rows = _tape_with_reaction((97.5, 98.5, 96.5, 97.2))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='a').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['level_ref'] == 98.0
    assert g['prior_high_ref'] == 98.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (97.2 - 96.0) / atr) < 1e-9   # target S1
    assert abs(g['stop_r'] - (98.0 - 97.2) / atr) < 1e-9


# --- variant b: S1/R1 reaction -----------------------------------------------

def test_variant_b_s1_reaction_long():
    rows = _tape_with_reaction((97.0, 98.0, 95.8, 96.5))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='b').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['level_ref'] == 96.0            # S1
    assert g['prior_low_ref'] == 96.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (98.0 - 96.5) / atr) < 1e-9   # target PP
    assert abs(g['stop_r'] - (96.5 - 96.0) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:25'


def test_variant_b_r1_reaction_short():
    rows = _tape_with_reaction((99.0, 100.4, 98.8, 99.5))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='b').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['level_ref'] == 100.0           # R1
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (99.5 - 98.0) / atr) < 1e-9   # target PP
    assert abs(g['stop_r'] - (100.0 - 99.5) / atr) < 1e-9


# --- variant c: S2/R2 violation (strong trend) -------------------------------

def test_variant_c_r2_violation_long():
    rows = _tape_with_reaction((101.0, 103.0, 100.8, 102.5))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='c').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'c'
    assert g['level_ref'] == 102.0           # R2
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (104.0 - 102.5) / atr) < 1e-9   # target R3
    assert abs(g['stop_r'] - (102.5 - 102.0) / atr) < 1e-9


def test_variant_c_s2_violation_short():
    rows = _tape_with_reaction((95.0, 95.5, 93.2, 93.5))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='c').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['level_ref'] == 94.0            # S2
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (93.5 - 92.0) / atr) < 1e-9   # target S3
    assert abs(g['stop_r'] - (94.0 - 93.5) / atr) < 1e-9


# --- variant d: S3/R3 extreme reversion --------------------------------------

def test_variant_d_s3_reclaim_long():
    rows = _tape_with_reaction((93.0, 93.5, 91.5, 92.8))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='d').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'd'
    assert g['level_ref'] == 92.0            # S3
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (94.0 - 92.8) / atr) < 1e-9   # target S2
    assert abs(g['stop_r'] - (92.8 - 92.0) / atr) < 1e-9


def test_variant_d_r3_reclaim_short():
    rows = _tape_with_reaction((103.0, 104.5, 102.8, 103.2))
    st = _state_at(rows, 24)
    ev = FloorTraderPivotExpert(variant_id='d').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['level_ref'] == 104.0           # R3
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - (103.2 - 102.0) / atr) < 1e-9   # target R2
    assert abs(g['stop_r'] - (104.0 - 103.2) / atr) < 1e-9


# --- rejection paths ---------------------------------------------------------

def test_no_setup_without_reaction():
    """A bar that reacts to NO level (98.5/99.0/97.5/98.0 stays inside the
    S1..R1 band with no drift) fires no variant."""
    rows = _tape_with_reaction((98.5, 99.0, 97.5, 98.0))
    st = _state_at(rows, 24)
    for vid in FloorTraderPivotExpert.variants_evaluated:
        ev = FloorTraderPivotExpert(variant_id=vid).evaluate(st)
        assert ev.decision == 'NO_SETUP', vid
        assert ev.draft is None


def test_no_habitat_on_warmup():
    rows = _tape([BASE] * 6)
    ev = FloorTraderPivotExpert().evaluate(_state_at(rows, 5))
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


# --- still_valid -------------------------------------------------------------

def test_still_valid_long_holds_and_invalidates():
    e = FloorTraderPivotExpert(variant_id='a')
    rows = _tape_with_reaction((98.5, 99.5, 98.3, 99.2))
    ev = e.evaluate(_state_at(rows, 24))
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    tail = _tape([(99.2, 99.6, 98.4, 99.4), (99.4, 99.6, 97.2, 97.6)], start=25)
    rows2 = rows + tail
    assert e.still_valid(_state_at(rows2, 25), ev.draft) is True
    # a close back below PP (98) kills the drift thesis
    assert e.still_valid(_state_at(rows2, 26), ev.draft) is False


def test_still_valid_fail_open():
    e = FloorTraderPivotExpert(variant_id='b')
    draft = CandidateDraft(
        expert_id='floor_trader_pivot', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'b', 'level_ref': 96.0},
        birth_time=0)
    st = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                     lineage_hash='h')
    assert e.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ----------------------------------

def test_requires_audited_against_consumption():
    e = FloorTraderPivotExpert()
    for g in e.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'pivot_points_day',
                   'bar_of_session'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape_with_reaction((98.5, 99.5, 98.3, 99.2))
    e = FloorTraderPivotExpert(variant_id='a')
    a = e.evaluate(_state_at(rows, 24))
    b = e.evaluate(_state_at(rows, 24))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=19, n_bars=220))
    m = ExperimentManifest(experiment_id='exp-e19', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [FloorTraderPivotExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
