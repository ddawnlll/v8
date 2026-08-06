"""E-11 breakout_retest expert tests (`breakout_retest` registered family).

Crafted 1h tapes with verbatim OHLC for the exact role-reversal, validation-
level and neckline-retest rules, plus synthetic-tape lab smoke. Cover: setup
detection per variant (long and short), no-setup rejection, no-habitat on
warmup, still_valid retest-hold invalidation + fail-open, risk-geometry
values (frozen level ref, book stop, 1:1 measuring-objective targets in R),
D-044 variants_evaluated completeness (variant d is NOT claimed: the cloud
retest is O-020-blocked), requires-vs-consumption audit, determinism.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, MarketState, \
    FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.breakout_retest import BreakoutRetestExpert

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


FLAT = (99.8, 100.3, 99.7, 100.0)            # small range bar (0.6)


# --- ontology + D-044 variant accounting ------------------------------------

def test_ontology_and_variants_evaluated():
    e = BreakoutRetestExpert()
    assert e.expert_id == 'breakout_retest'
    assert e.mechanism_family_id == 'breakout_retest'
    assert e.behavior_family_id == 'breakout_retest'
    assert set(e.requires) == {'location', 'volatility', 'history'}
    # variant d (Ichimoku cloud retest) is NOT implemented: the displaced
    # cloud needs ~78 bars, which the 32-bar history pin (O-020) cannot
    # carry. D-044 forbids claiming a variant that was never evaluated.
    assert e.variants_evaluated == ('a', 'b', 'c')
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)
    for vid in e.variants_evaluated:
        assert BreakoutRetestExpert(variant_id=vid).variant_id == vid


def test_unknown_variant_fails_closed():
    try:
        BreakoutRetestExpert(variant_id='d')
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- variant a: role-reversal retest on a significant swing level ------------

def _long_retest_tape():
    bars = [FLAT] * 10
    bars += [(101.5, 103.0, 99.5, 102.0)]                # pivot high 103
    bars += [FLAT] * 10
    bars += [(103.2, 104.2, 103.0, 104.0)]               # breakout close
    bars += [(104.0, 104.6, 103.8, 104.4),               # drift higher
             (104.4, 105.0, 104.2, 104.8),
             (104.8, 105.4, 104.6, 105.2),
             (105.2, 105.8, 105.0, 105.6)]
    bars += [(104.0, 104.5, 102.5, 103.5)]               # retest hold
    return bars


def test_variant_a_long_resistance_retest():
    rows = _tape(_long_retest_tape())
    st = _state_at(rows, 26)
    ev = BreakoutRetestExpert(variant_id='a').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'a'
    assert g['level_ref'] == 103.0          # the breached resistance, frozen
    assert g['stop_ref'] == 103.0
    assert g['prior_low_ref'] == 103.0
    assert g['target_r'] == 1.0             # no pattern -> family default
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['expiry_bars'] == 8
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (103.5 - 103.0) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:27'


def _short_retest_tape():
    bars = [(100.2, 100.7, 99.7, 100.0)] * 10
    bars += [(98.5, 100.5, 97.0, 98.0)]                  # pivot low 97
    bars += [(100.2, 100.7, 99.7, 100.0)] * 10
    bars += [(96.8, 97.0, 95.8, 96.0)]                   # breakdown close
    bars += [(96.0, 96.4, 95.4, 95.6),
             (95.6, 96.0, 95.0, 95.2),
             (95.2, 95.6, 94.6, 94.8),
             (94.8, 95.2, 94.2, 94.4)]
    bars += [(96.0, 97.5, 95.5, 96.5)]                   # retest hold
    return bars


def test_variant_a_short_support_retest():
    rows = _tape(_short_retest_tape())
    st = _state_at(rows, 26)
    ev = BreakoutRetestExpert(variant_id='a').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['level_ref'] == 97.0           # the breached support, frozen
    assert g['prior_high_ref'] == 97.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['stop_r'] - (97.0 - 96.5) / atr) < 1e-9


# --- variant b: validation-level retest (double top / bottom) ----------------

def _double_top_tape():
    bars = [(99.8, 100.4, 99.6, 100.0)] * 10
    bars += [(100.0, 102.0, 99.8, 101.5)]                # peak 1
    bars += [(101.5, 101.8, 100.3, 100.5),
             (100.5, 101.7, 100.2, 100.3),
             (100.3, 101.6, 100.1, 100.1),
             (100.1, 101.5, 100.0, 99.9),
             (99.9, 101.4, 99.9, 99.7)]
    bars += [(100.5, 100.9, 99.0, 99.3)]                 # trough = validation 99
    bars += [(99.3, 99.6, 99.1, 99.4),
             (99.4, 99.8, 99.2, 99.6),
             (99.6, 100.0, 99.4, 99.8),
             (99.8, 100.3, 99.6, 100.1)]
    bars += [(100.4, 101.8, 100.2, 101.2)]               # peak 2
    bars += [(101.0, 101.2, 98.3, 98.5),                 # breakdown below 99
             (98.5, 98.8, 97.8, 98.0),
             (98.0, 98.4, 97.3, 97.5),
             (97.5, 97.8, 96.8, 97.0)]
    bars += [(98.0, 99.3, 97.8, 98.7)]                   # retest hold
    return bars


def test_variant_b_double_top_validation_retest():
    rows = _tape(_double_top_tape())
    st = _state_at(rows, 26)
    ev = BreakoutRetestExpert(variant_id='b').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'b'
    assert g['level_ref'] == 99.0           # the validation level (trough)
    assert g['stop_ref'] == 102.0           # above the higher peak
    assert g['prior_high_ref'] == 102.0
    atr = float(st.features['SOLUSDT.atr'].value)
    # 1:1 measuring objective: height = higher peak - validation level = 3.0
    assert abs(g['target_r'] - 3.0 / atr) < 1e-9
    assert abs(g['stop_r'] - (102.0 - 98.7) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:27'


def _double_bottom_tape():
    bars = [(100.2, 100.7, 99.7, 100.0)] * 10
    bars += [(100.0, 100.6, 98.0, 98.5)]                 # trough 1
    bars += [(98.5, 100.3, 99.7, 99.5),
             (99.5, 100.5, 100.0, 100.2),
             (100.2, 101.0, 100.4, 100.6),
             (100.6, 101.4, 100.8, 101.0),
             (101.0, 101.8, 101.2, 101.4)]
    bars += [(101.4, 102.0, 100.9, 101.5)]               # peak = validation 102
    bars += [(101.5, 101.8, 100.6, 100.9),
             (100.9, 101.2, 100.2, 100.5),
             (100.5, 100.8, 99.8, 100.1),
             (100.1, 100.4, 99.4, 99.7)]
    bars += [(99.7, 100.0, 98.2, 98.5)]                  # trough 2
    bars += [(99.0, 103.5, 98.9, 103.0),                 # breakout above 102
             (103.0, 104.0, 102.6, 103.5),
             (103.5, 104.5, 103.1, 104.0),
             (104.0, 105.0, 103.6, 104.5)]
    bars += [(102.0, 102.8, 101.3, 102.4)]               # retest hold
    return bars


def test_variant_b_double_bottom_validation_retest():
    rows = _tape(_double_bottom_tape())
    st = _state_at(rows, 26)
    ev = BreakoutRetestExpert(variant_id='b').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['level_ref'] == 102.0           # the validation level (peak)
    assert g['stop_ref'] == 98.0             # below the lower trough
    assert g['prior_low_ref'] == 98.0
    atr = float(st.features['SOLUSDT.atr'].value)
    assert abs(g['target_r'] - 4.0 / atr) < 1e-9
    assert abs(g['stop_r'] - (102.4 - 98.0) / atr) < 1e-9


# --- variant c: neckline retest (head-and-shoulders) -------------------------

def _hs_top_tape():
    bars = [(100.0, 100.3, 99.8, 100.1),
            (100.1, 100.7, 99.9, 100.5),
            (100.5, 101.1, 100.3, 100.9)]
    bars += [(100.9, 102.0, 100.6, 101.5)]               # left shoulder
    bars += [(101.5, 101.8, 101.0, 101.2),
             (101.2, 101.6, 100.6, 100.8),
             (100.8, 101.4, 100.2, 100.4)]
    bars += [(100.4, 100.6, 99.6, 99.8)]                 # left trough
    bars += [(99.8, 101.2, 99.9, 100.2),
             (100.2, 101.6, 100.3, 100.6),
             (100.6, 102.0, 100.7, 101.0)]
    bars += [(101.0, 105.0, 100.8, 104.2)]               # head
    bars += [(104.2, 104.0, 103.0, 103.2),
             (103.2, 103.0, 102.0, 102.2),
             (102.2, 102.0, 101.0, 101.2)]
    bars += [(101.2, 101.2, 100.2, 100.5)]               # right trough
    bars += [(100.5, 100.6, 100.3, 100.4),
             (100.4, 100.8, 100.4, 100.6)]
    bars += [(101.0, 102.6, 100.8, 102.2)]               # right shoulder
    bars += [(101.0, 101.2, 100.0, 100.1)]               # neckline break
    bars += [(100.1, 100.4, 99.7, 99.9),
             (99.9, 100.2, 99.5, 99.7),
             (99.7, 100.0, 99.3, 99.5),
             (99.5, 99.8, 99.1, 99.3),
             (99.3, 99.6, 98.9, 99.1)]
    bars += [(99.5, 100.4, 99.3, 99.9)]                  # retest hold
    return bars


def test_variant_c_hs_top_neckline_retest():
    rows = _tape(_hs_top_tape())
    st = _state_at(rows, 25)
    ev = BreakoutRetestExpert(variant_id='c').evaluate(st)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'c'
    assert abs(g['level_ref'] - 100.2) < 1e-9    # the (flat) neckline
    assert g['stop_ref'] == 102.6                # above the right shoulder
    assert g['prior_high_ref'] == 102.6
    atr = float(st.features['SOLUSDT.atr'].value)
    # 1:1 head-to-neckline objective: height = 105.0 - 100.2 = 4.8
    assert abs(g['target_r'] - 4.8 / atr) < 1e-9
    assert abs(g['stop_r'] - (102.6 - 99.9) / atr) < 1e-9
    assert d.setup_anchor_event_id == 'SOLUSDT:26'


def test_variant_c_no_retest_without_break():
    """The H&S structure must be COMPLETED by a neckline break before the
    retest bar; a tape where price never closed below the neckline (all
    closes after the right shoulder stay above it) is NO_SETUP even though
    the current bar touches the neckline."""
    bars = _hs_top_tape()
    bars[19] = (100.8, 101.0, 100.4, 100.5)      # hold above the neckline
    bars[20] = (100.5, 100.9, 100.3, 100.6)
    bars[21] = (100.6, 101.0, 100.4, 100.7)
    bars[22] = (100.7, 101.1, 100.5, 100.6)
    bars[23] = (100.6, 101.0, 100.4, 100.5)
    bars[24] = (100.5, 100.9, 100.3, 100.4)
    bars[25] = (99.9, 100.4, 99.3, 99.9)         # touch below, but NO prior break
    rows2 = _tape(bars)
    ev = BreakoutRetestExpert(variant_id='c').evaluate(_state_at(rows2, 25))
    assert ev.decision == 'NO_SETUP'


# --- rejection paths ---------------------------------------------------------

def test_no_setup_on_flat_tape():
    rows = _tape([FLAT] * 40)
    st = _state_at(rows, 39)
    for vid in BreakoutRetestExpert.variants_evaluated:
        ev = BreakoutRetestExpert(variant_id=vid).evaluate(st)
        assert ev.decision == 'NO_SETUP', vid
        assert ev.draft is None


def test_no_habitat_on_warmup():
    rows = _tape([FLAT] * 6)
    ev = BreakoutRetestExpert().evaluate(_state_at(rows, 5))
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


# --- still_valid -------------------------------------------------------------

def test_still_valid_long_holds_and_invalidates():
    e = BreakoutRetestExpert(variant_id='a')
    rows = _tape(_long_retest_tape())
    ev = e.evaluate(_state_at(rows, 26))
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['level_ref'] == 103.0
    tail = _tape([(103.5, 104.2, 102.9, 103.8), (103.8, 104.0, 102.2, 102.8)],
                 start=27)
    rows2 = rows + tail
    assert e.still_valid(_state_at(rows2, 27), ev.draft) is True
    # a close back through the flipped level kills the retest thesis
    assert e.still_valid(_state_at(rows2, 28), ev.draft) is False


def test_still_valid_short_holds_and_invalidates():
    e = BreakoutRetestExpert(variant_id='c')
    rows = _tape(_hs_top_tape())
    ev = e.evaluate(_state_at(rows, 25))
    assert ev.draft is not None and ev.draft.direction == 'SHORT'
    tail = _tape([(99.5, 100.0, 99.0, 99.4), (99.4, 100.9, 99.4, 100.8)],
                 start=26)
    rows2 = rows + tail
    # bar 26: close 99.4 stays below the frozen neckline -> thesis alive
    assert e.still_valid(_state_at(rows2, 26), ev.draft) is True
    # bar 27: close 100.8 back above the neckline -> the retest failed
    assert e.still_valid(_state_at(rows2, 27), ev.draft) is False


def test_still_valid_fail_open():
    e = BreakoutRetestExpert(variant_id='a')
    draft = CandidateDraft(
        expert_id='breakout_retest', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'a', 'level_ref': 103.0},
        birth_time=0)
    st = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                     lineage_hash='h')
    assert e.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ----------------------------------

def test_requires_audited_against_consumption():
    e = BreakoutRetestExpert()
    for g in e.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'swing_high_10', 'swing_low_10'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape(_long_retest_tape())
    e = BreakoutRetestExpert(variant_id='a')
    a = e.evaluate(_state_at(rows, 26))
    b = e.evaluate(_state_at(rows, 26))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=13, n_bars=220))
    m = ExperimentManifest(experiment_id='exp-e11', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [BreakoutRetestExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
