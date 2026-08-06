"""E-21 gap_exhaustion expert tests (`gap_reaction` family).

Crafted 1h tapes with verbatim gaps (type-3: open beyond the prior extreme)
for the exact gap-sequence rules, plus synthetic-tape lab smoke. Cover:
setup detection per variant (breakaway up/down, runaway, third-gap
exhaustion up/down), the gap-zone S/R reference, no-setup rejection (no gap,
wrong count, gap not beyond the range), no-habitat on warmup, still_valid
gap-fill / gap-hold invalidation + fail-open, D-044 variants_evaluated
completeness, requires-vs-consumption audit, determinism.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, MarketState, \
    FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.gap_exhaustion import GapExhaustionExpert

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
    e = GapExhaustionExpert()
    assert e.expert_id == 'gap_exhaustion'
    assert e.mechanism_family_id == 'gap_reaction'
    assert e.behavior_family_id == 'gap_reaction'
    assert set(e.requires) == {'candle_shape', 'location', 'volatility',
                               'history'}
    assert e.variants_evaluated == ('a', 'b', 'c')
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)
    for vid in e.variants_evaluated:
        assert GapExhaustionExpert(variant_id=vid).variant_id == vid


def test_unknown_variant_fails_closed():
    try:
        GapExhaustionExpert(variant_id='d')
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- variant b: breakaway gap (first gap beyond the range) -------------------

def _breakaway_up_tape():
    return [(99.8, 100.2, 99.6, 100.0)] * 21 + [(100.8, 101.2, 100.7, 101.0)]


def test_variant_b_breakaway_up():
    rows = _tape(_breakaway_up_tape())
    st = _state_at(rows, 21)
    ev = GapExhaustionExpert(variant_id='b').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'b'
    assert g['level_ref'] == 100.2          # gap bottom = frozen S/R
    assert g['stop_ref'] == 100.2
    assert g['gap_top_ref'] == 100.8
    assert g['gap_bottom_ref'] == 100.2
    assert g['prior_low_ref'] == 100.2
    assert g['target_r'] == 1.0             # book gives no measuring objective
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (101.0 - 100.2) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:22'


def _breakaway_down_tape():
    return [(100.2, 100.8, 99.8, 100.0)] * 21 + [(99.4, 99.6, 99.0, 99.2)]


def test_variant_b_breakaway_down():
    rows = _tape(_breakaway_down_tape())
    st = _state_at(rows, 21)
    ev = GapExhaustionExpert(variant_id='b').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['level_ref'] == 99.8           # gap top = frozen S/R
    assert g['gap_top_ref'] == 99.8
    assert g['gap_bottom_ref'] == 99.4
    assert g['prior_high_ref'] == 99.8
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (99.8 - 99.2) / atr) < 1e-9


def test_variant_b_gap_not_beyond_range_no_setup():
    """An up-gap that opens above the prior bar but NOT above the 20-bar
    range high is not a breakaway (not out of a consolidation)."""
    bars = [(99.8, 100.2, 99.6, 100.0)] * 21
    bars[5] = (99.8, 101.2, 99.6, 100.0)          # a higher old high
    bars += [(100.5, 101.0, 100.4, 100.7)]        # gap up, inside the range
    rows = _tape(bars)
    ev = GapExhaustionExpert(variant_id='b').evaluate(_state_at(rows, 21))
    assert ev.decision == 'NO_SETUP'


# --- variant c: runaway / midway gap (second gap) ----------------------------

def _runaway_up_tape():
    return ([(99.8, 100.2, 99.6, 100.0)] * 14       # bars 0-13
            + [(100.6, 101.0, 100.5, 100.8)]        # bar 14 gap #1
            + [(100.6, 100.9, 100.4, 100.7)] * 4    # bars 15-18
            + [(101.2, 101.6, 101.1, 101.4)])       # bar 19 gap #2 (runaway)


def test_variant_c_runaway_up():
    rows = _tape(_runaway_up_tape())
    st = _state_at(rows, 19)
    ev = GapExhaustionExpert(variant_id='c').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'c'
    assert g['gap_top_ref'] == 101.2
    assert g['gap_bottom_ref'] == 100.9
    assert g['level_ref'] == 100.9
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (101.4 - 100.9) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:20'


def test_variant_c_first_gap_not_runaway_no_setup():
    """The FIRST gap in the direction is breakaway (variant b), not runaway."""
    rows = _tape(_breakaway_up_tape())              # only gap #1
    ev = GapExhaustionExpert(variant_id='c').evaluate(_state_at(rows, 21))
    assert ev.decision == 'NO_SETUP'


# --- variant a: third-gap exhaustion reversal --------------------------------

def _exhaustion_up_tape():
    return ([(99.8, 100.2, 99.6, 100.0)] * 11       # bars 0-10
            + [(100.6, 101.0, 100.5, 100.8)]        # bar 11 gap #1
            + [(100.6, 100.9, 100.4, 100.7)] * 3    # bars 12-14
            + [(101.1, 101.5, 101.0, 101.3)]        # bar 15 gap #2
            + [(101.1, 101.4, 100.9, 101.2)] * 3    # bars 16-18
            + [(101.6, 101.9, 101.0, 101.2)])       # bar 19 gap #3, stall


def test_variant_a_third_gap_exhaustion_short():
    rows = _tape(_exhaustion_up_tape())
    st = _state_at(rows, 19)
    ev = GapExhaustionExpert(variant_id='a').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'a'
    assert g['gap_top_ref'] == 101.6
    assert g['gap_bottom_ref'] == 101.4
    assert g['level_ref'] == 101.6          # the gap top is the S/R
    assert g['prior_high_ref'] == 101.6
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (101.6 - 101.2) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:20'


def _exhaustion_down_tape():
    return ([(100.2, 100.8, 99.8, 100.0)] * 11      # bars 0-10
            + [(99.4, 99.6, 99.0, 99.2)]            # bar 11 gap #1
            + [(99.4, 99.7, 99.2, 99.5)] * 3        # bars 12-14
            + [(98.9, 99.2, 98.5, 98.7)]            # bar 15 gap #2
            + [(98.9, 99.2, 98.7, 99.0)] * 3        # bars 16-18
            + [(98.4, 99.0, 98.1, 98.8)])           # bar 19 gap #3, stall


def test_variant_a_third_gap_exhaustion_long():
    rows = _tape(_exhaustion_down_tape())
    st = _state_at(rows, 19)
    ev = GapExhaustionExpert(variant_id='a').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['gap_top_ref'] == 98.7
    assert g['gap_bottom_ref'] == 98.4
    assert g['level_ref'] == 98.4
    assert g['prior_low_ref'] == 98.4
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (98.8 - 98.4) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:20'


def _two_gaps_tape():
    return ([(99.8, 100.2, 99.6, 100.0)] * 11       # bars 0-10
            + [(100.6, 101.0, 100.5, 100.8)]        # bar 11 gap #1
            + [(100.6, 100.9, 100.4, 100.7)] * 3    # bars 12-14
            + [(101.1, 101.5, 101.0, 101.3)]        # bar 15 gap #2
            + [(101.1, 101.4, 100.9, 101.2)] * 4)   # bars 16-19


def test_variant_a_two_gaps_no_exhaustion():
    """Only two gaps in the window: NO_SETUP for the exhaustion variant."""
    rows = _tape(_two_gaps_tape())
    ev = GapExhaustionExpert(variant_id='a').evaluate(_state_at(rows, 19))
    assert ev.decision == 'NO_SETUP'


# --- rejection paths ---------------------------------------------------------

def test_no_setup_without_gap():
    flat = [(100.0, 100.4, 99.6, 100.0)] * 30
    rows = _tape(flat)
    st = _state_at(rows, 29)
    for vid in GapExhaustionExpert.variants_evaluated:
        ev = GapExhaustionExpert(variant_id=vid).evaluate(st)
        assert ev.decision == 'NO_SETUP', vid


def test_no_habitat_on_warmup():
    rows = _tape([(100.0, 100.4, 99.6, 100.0)] * 5)
    ev = GapExhaustionExpert().evaluate(_state_at(rows, 4))
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


# --- still_valid -------------------------------------------------------------

def test_still_valid_exhaustion_gap_fill():
    """The exhaustion thesis is that the gap FILLS: a close back above the
    frozen gap top says the gap held and the reversal is dead."""
    e = GapExhaustionExpert(variant_id='a')
    rows = _tape(_exhaustion_up_tape())
    ev = e.evaluate(_state_at(rows, 19))
    assert ev.draft is not None and ev.draft.direction == 'SHORT'
    tail = _tape([(101.2, 101.4, 100.8, 101.0), (101.0, 102.0, 101.0, 101.8)],
                 start=20)
    rows2 = rows + tail
    assert e.still_valid(_state_at(rows2, 20), ev.draft) is True    # filling
    assert e.still_valid(_state_at(rows2, 21), ev.draft) is False   # gap held


def test_still_valid_breakaway_gap_holds():
    """The breakaway thesis is that the gap HOLDS: a close back into the gap
    (below the frozen gap bottom) says it filled and the thesis is dead."""
    e = GapExhaustionExpert(variant_id='b')
    rows = _tape(_breakaway_up_tape())
    ev = e.evaluate(_state_at(rows, 21))
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    tail = _tape([(101.0, 101.4, 100.6, 100.9), (100.9, 101.1, 100.0, 100.1)],
                 start=22)
    rows2 = rows + tail
    assert e.still_valid(_state_at(rows2, 22), ev.draft) is True
    assert e.still_valid(_state_at(rows2, 23), ev.draft) is False


def test_still_valid_fail_open():
    e = GapExhaustionExpert(variant_id='a')
    draft = CandidateDraft(
        expert_id='gap_exhaustion', expert_version='v1',
        instrument='SOLUSDT', direction='SHORT', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'a', 'level_ref': 101.6,
                       'gap_top_ref': 101.6, 'gap_bottom_ref': 101.4},
        birth_time=0)
    st = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                     lineage_hash='h')
    assert e.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ----------------------------------

def test_requires_audited_against_consumption():
    e = GapExhaustionExpert()
    for g in e.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'gap_dir', 'gap_size',
                   'gap_levels', 'window_high_20', 'window_low_20'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape(_exhaustion_up_tape())
    e = GapExhaustionExpert(variant_id='a')
    a = e.evaluate(_state_at(rows, 19))
    b = e.evaluate(_state_at(rows, 19))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=23, n_bars=240))
    m = ExperimentManifest(experiment_id='exp-e21', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [GapExhaustionExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
