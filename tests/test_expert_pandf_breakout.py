"""E-24 pandf_breakout expert tests (`boxed_price_breakout` family).

Covers: D-044/D-046 variant accounting, the LOCKED box filter (k=1.0*ATR,
reversal 3), double/triple top-bottom box breakout detection on crafted
series, no-setup / no-habitat rejection, risk_geometry values (book vertical-
count target + lowest-X stop in R), still_valid invalidation + fail-open,
D-026 anchor stability, requires-vs-consumption audit, determinism, and a
lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, MarketState, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.pandf_breakout import (
    PandfBreakoutExpert, _columns, BOX_ATR_K, REVERSAL_BOXES, MIN_HISTORY_BARS)

UNIVERSE = ('SOLUSDT',)
VARIANTS = ('a', 'b', 'c', 'd')


def _bar(i, c):
    """Closed 1h bar with range exactly 1.0 (h = c+0.5, l = c-0.5) so the
    14-bar ATR is exactly 1.0 and the box size is exactly 1.0."""
    return TapeRow(
        source='binance-um', channel='kline', instrument='SOLUSDT',
        event_time=HOUR_NS * i, available_time=HOUR_NS * i,
        ingested_time=HOUR_NS * i, venue_sequence=i + 1,
        event_id=f'SOLUSDT:{i + 1}',
        payload={'open': c, 'high': c + 0.5, 'low': c - 0.5, 'close': c,
                 'volume': 1.0, 'closed': True})


def _state(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _tape(closes):
    return [_bar(i, c) for i, c in enumerate(closes)]


# --- crafted setup tapes -----------------------------------------------------

def _double_top_tape():
    """Rise to 106, pull back to 100, rise to 107: at bar 37 the X column's
    top (107) exceeds the prior X top (106) -> double top LONG."""
    closes = [100.0] * 20 + [101, 102, 103, 104, 105, 106,
                             105, 104, 103, 102, 101, 100,
                             101, 102, 103, 104, 105, 107]
    return _tape(closes)


def _double_bottom_tape():
    """Fall to 94, bounce to 100, fall to 93: at bar 37 the O column's bottom
    (93) is below the prior O bottom (94) -> double bottom SHORT."""
    closes = [100.0] * 20 + [99, 98, 97, 96, 95, 94,
                             95, 96, 97, 98, 99, 100,
                             99, 98, 97, 96, 95, 93]
    return _tape(closes)


def _triple_top_tape():
    """X(104) O(100) X(103) O(99) X(105): the last X top exceeds BOTH prior X
    tops -> triple top LONG at bar 38."""
    closes = [100.0] * 20 + [101, 102, 103, 104,
                             103, 102, 101, 100,
                             101, 102, 103,
                             102, 101, 100, 99,
                             100, 101, 105]
    return _tape(closes)


def _triple_bottom_tape():
    """Mirror: O(96) X(100) O(97) X(101) O(95) -> triple bottom SHORT at bar
    38."""
    closes = [100.0] * 20 + [99, 98, 97, 96,
                             97, 98, 99, 100,
                             99, 98, 97,
                             98, 99, 100, 101,
                             100, 99, 95]
    return _tape(closes)


# --- ontology + variants (D-044/D-046) --------------------------------------

def test_ontology_declared():
    e = PandfBreakoutExpert()
    assert e.expert_id == 'pandf_breakout'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'boxed_price_breakout'
    assert e.behavior_family_id == 'boxed_price_breakout'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == VARIANTS
    assert set(e.requires) == {'volatility', 'history'}


def test_variants_evaluated_completeness():
    e = PandfBreakoutExpert()
    assert set(e.variants_evaluated) == set(VARIANTS)
    assert e.variant_id in e.variants_evaluated
    # The book card's signal grid enumerates 8 signals; 4 are implemented and
    # 4 dropped before evaluation (angle-classification triples and the O-013
    # catapult), so the consumed search is 8.
    assert e.search_universe_size == 8 >= len(e.variants_evaluated)
    for vid in VARIANTS:
        assert PandfBreakoutExpert(vid).variant_id == vid


def test_locked_box_filter():
    """The orchestrator LOCKED box = 1.0*ATR and reversal = 3."""
    assert BOX_ATR_K == 1.0
    assert REVERSAL_BOXES == 3


def test_unknown_variant_fails_closed():
    rows = _double_top_tape()
    try:
        PandfBreakoutExpert('zz').evaluate(_state(rows, 37))
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- setup detection per variant --------------------------------------------

def test_variant_a_double_top_long():
    rows = _double_top_tape()
    ev = PandfBreakoutExpert('a').evaluate(_state(rows, 37))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'a'
    assert d.risk_geometry['atr_ref'] == 1.0
    assert d.risk_geometry['reversal'] == 3


def test_variant_b_double_bottom_short():
    rows = _double_bottom_tape()
    ev = PandfBreakoutExpert('b').evaluate(_state(rows, 37))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'b'


def test_variant_c_triple_top_long():
    rows = _triple_top_tape()
    ev = PandfBreakoutExpert('c').evaluate(_state(rows, 37))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'c'


def test_variant_d_triple_bottom_short():
    rows = _triple_bottom_tape()
    ev = PandfBreakoutExpert('d').evaluate(_state(rows, 37))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'd'


def test_signal_is_column_structure():
    """The double-top signal comes from the boxed column structure: two X
    columns with the newer top higher, separated by an O column."""
    closes = [float(b.payload['close']) for b in _double_top_tape()][-32:]
    cols = _columns(closes, 1.0, 3)
    xs = [c for c in cols if c[0] > 0]
    assert len(xs) == 2
    assert xs[-1][2][-1] > xs[-2][2][-1]


# --- no-setup / no-habitat ---------------------------------------------------

def test_no_setup_within_same_box_level():
    """A double top where the second X column only REACHES the prior top (not
    a new X above it) is not a breakout -> NO_SETUP."""
    closes = [100.0] * 20 + [101, 102, 103, 104,
                             103, 102, 101, 100,
                             101, 102, 103, 104]   # second top == first top
    rows = _tape(closes)
    ev = PandfBreakoutExpert('a').evaluate(_state(rows, 31))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_setup_flat_tape():
    rows = _tape([100.0] * 40)
    ev = PandfBreakoutExpert('a').evaluate(_state(rows, 39))
    assert ev.decision == 'NO_SETUP'


def test_no_habitat_on_warmup():
    rows = _tape([100.0] * 10)
    ev = PandfBreakoutExpert('a').evaluate(_state(rows, 9))
    assert ev.decision == 'NO_HABITAT'
    assert MIN_HISTORY_BARS == 20


# --- risk geometry (book vertical count + lowest-X stop) --------------------

def test_risk_geometry_values():
    rows = _double_top_tape()
    d = PandfBreakoutExpert('a').evaluate(_state(rows, 37)).draft
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['expiry_bars'] == 8
    assert g['atr_ref'] == 1.0
    # Stop below the lowest X in the breakout column (101.0, the column's
    # first box); close 107 -> 6R.
    assert g['prior_low_ref'] == 101.0
    assert g['stop_r'] == (107.0 - 101.0) / 1.0
    # Vertical count (Ch15.3): lowestBox + colBoxes*box*reversal =
    # 101 + 6*1*3 = 119 -> target_r = (119 - 107)/1 = 12R.
    assert g['target_r'] == (101.0 + 6 * 1 * 3 - 107.0) / 1.0


def test_short_geometry_mirrors():
    rows = _double_bottom_tape()
    d = PandfBreakoutExpert('b').evaluate(_state(rows, 37)).draft
    g = d.risk_geometry
    assert g['prior_high_ref'] == 99.0     # highest O in the breakout column
    assert g['stop_r'] == (99.0 - 93.0) / 1.0
    assert g['target_r'] == (93.0 - (99.0 - 6 * 1 * 3)) / 1.0


# --- still_valid -------------------------------------------------------------

def test_still_valid_invalidated_on_column_retrace():
    e = PandfBreakoutExpert('a')
    rows = _double_top_tape()
    draft = e.evaluate(_state(rows, 37)).draft
    assert e.still_valid(_state(rows, 37), draft) is True
    # A later close back through the frozen column low (101.0) retraces the
    # whole breakout column -> the boxed breakout thesis is dead.
    later = _tape([float(b.payload['close']) for b in rows]
                  + [108.0, 106.0, 104.0, 102.0, 100.0])
    assert e.still_valid(_state(later, 37), draft) is True
    assert e.still_valid(_state(later, 42), draft) is False


def test_still_valid_fail_open():
    e = PandfBreakoutExpert('a')
    rows = _double_top_tape()
    draft = e.evaluate(_state(rows, 37)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- D-026 anchor stability --------------------------------------------------

def test_anchor_stable_across_consecutive_clocks():
    """The breakout column's first bar is the anchor; it is stable while the
    column persists (a fresh extension does not move it)."""
    e = PandfBreakoutExpert('a')
    closes = [100.0] * 20 + [101, 102, 103, 104, 105, 106,
                             105, 104, 103, 102, 101, 100,
                             101, 102, 103, 104, 105, 107,
                             108]
    rows = _tape(closes)
    d1 = e.evaluate(_state(rows, 37)).draft
    d2 = e.evaluate(_state(rows, 38)).draft
    assert d1 is not None and d2 is not None
    assert d1.setup_anchor_event_id == d2.setup_anchor_event_id


# --- registry audit + determinism + lab -------------------------------------

def test_requires_audited_against_consumption():
    e = PandfBreakoutExpert()
    assert all(g in FEATURE_GROUPS for g in e.requires)
    consumption = {'close', 'atr', 'history'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _double_top_tape()
    a = PandfBreakoutExpert('a').evaluate(_state(rows, 37))
    b = PandfBreakoutExpert('a').evaluate(_state(rows, 37))
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
    lab.ingest(make_synthetic_tape(seed=13, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-e24', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [PandfBreakoutExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')
