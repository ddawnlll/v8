"""E-03 range_breakout_1to1 expert tests (`consolidation_breakout` /
`range_breakout` family, variants a..f).

Covers: D-044/D-046 variant accounting, setup detection on crafted
consolidation-breakout tapes (no-filter, 3%/5% completion, one-ATR, volume
expansion, low-volume timing), the 1:1 measuring-objective geometry in R
(D-028), single-bar setup guarantee, no-setup / no-habitat rejection,
still_valid invalidation (close back inside the range) and fail-open,
requires-vs-consumption audit, determinism, and a lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.experts.range_breakout_1to1 import (
    RangeBreakout1To1Expert, RangeBreakout1To1B, RangeBreakout1To1C,
    RangeBreakout1To1D, RangeBreakout1To1E, RangeBreakout1To1F,
    VARIANTS_EVALUATED, RANGE_N, WIDTH_MAX, FILTER_3PCT, FILTER_5PCT,
    VOL_MIN_PROXIMITY_MAX)

UNIVERSE = ('SOLUSDT',)

VARIANTS = {'a': RangeBreakout1To1Expert, 'b': RangeBreakout1To1B,
            'c': RangeBreakout1To1C, 'd': RangeBreakout1To1D,
            'e': RangeBreakout1To1E, 'f': RangeBreakout1To1F}


def _tape(bars, vols=None, start=0):
    """Deterministic 1h tape from (open, high, low, close) tuples."""
    rows = []
    for i, (o, h, l, c) in enumerate(bars, start=start):
        v = vols[i] if vols else 1.0
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': v, 'closed': True}))
    return rows


def _wide(c, w=0.01):
    return (c, c * (1 + w), c * (1 - w), c)


def _cons(n=30, lo=100.0, hi=101.0):
    """A narrow consolidation (width ~1%, inside WIDTH_MAX): alternating closes
    lo/hi with small bars."""
    return [_wide(lo if i % 2 == 0 else hi) for i in range(n)]


def _state(rows, bar_idx):
    as_of = rows[bar_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _eval(expert, rows, bar_idx):
    return expert.evaluate(_state(rows, bar_idx))


# --- D-044 / D-046 variant accounting --------------------------------------

def test_variants_evaluated_complete():
    """Every declared variant is implemented and listed (losers included); the
    reported variant_id is a member; the search cannot be smaller than the
    retained set (D-044, D-046)."""
    ex = RangeBreakout1To1Expert()
    assert set(ex.variants_evaluated) == set(VARIANTS_EVALUATED) == \
        {'a', 'b', 'c', 'd', 'e', 'f'}
    for vid, cls in VARIANTS.items():
        assert cls().variant_id == vid, f'{vid} maps to {cls.__name__}'
        assert vid in ex.variants_evaluated
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)
    assert RANGE_N == 20 and WIDTH_MAX == 0.03
    assert FILTER_3PCT == 1.03 and FILTER_5PCT == 1.05
    assert VOL_MIN_PROXIMITY_MAX == 0.25


# --- setup detection --------------------------------------------------------

def test_variant_a_detected():
    """Close beyond the narrow 20-bar range extreme -> LONG with the 1:1
    range-height measuring objective expressed in R (D-028): target_r =
    stop_r = range_height_20 / atr."""
    rows = _tape(_cons(30) + [(105.0, 105.5, 104.2, 105.0)])
    idx = len(rows) - 1
    ev = _eval(RangeBreakout1To1Expert(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.instrument == 'SOLUSDT'
    f = _state(rows, idx).features
    atr = float(f['SOLUSDT.atr'].value)
    rh = float(f['SOLUSDT.range_height_20'].value)
    wl = float(f['SOLUSDT.window_low_20'].value)
    wh = float(f['SOLUSDT.window_high_20'].value)
    assert d.risk_geometry['entry'] == 'NEXT_BAR_CLOSE'
    assert d.risk_geometry['expiry_bars'] == 8
    assert d.risk_geometry['atr_ref'] == atr
    assert d.risk_geometry['variant'] == 'a'
    assert abs(d.risk_geometry['target_r'] - rh / atr) < 1e-9
    assert abs(d.risk_geometry['stop_r'] - rh / atr) < 1e-9
    assert d.risk_geometry['prior_low_ref'] == wl
    assert d.risk_geometry['breakout_ref'] == wh
    # 2:1 secondary profit-taking level (frozen price reference, Ch13.2).
    assert abs(d.risk_geometry['target_2x_ref'] - (wh + 2.0 * rh)) < 1e-9
    # Single-bar setup: the anchor is the breakout bar itself.
    assert d.setup_anchor_event_id == f'SOLUSDT:{idx + 1}'


def test_variant_b_c_d_filters_detected():
    """The 3%/5% completion filters and the one-ATR filter fire on a stronger
    breakout close (108 > 105% of the range high)."""
    rows = _tape(_cons(30) + [(108.0, 108.6, 107.0, 108.0)])
    idx = len(rows) - 1
    for cls, vid in ((RangeBreakout1To1B, 'b'), (RangeBreakout1To1C, 'c'),
                     (RangeBreakout1To1D, 'd')):
        ev = _eval(cls(), rows, idx)
        assert ev.decision == 'CANDIDATE' and ev.draft is not None
        assert ev.draft.direction == 'LONG'
        assert ev.draft.risk_geometry['variant'] == vid
    # A mere 1.5% breakout is below every completion filter.
    rows_shallow = _tape(_cons(30) + [(102.6, 103.0, 101.9, 102.6)])
    for cls in (RangeBreakout1To1B, RangeBreakout1To1C, RangeBreakout1To1D):
        ev = _eval(cls(), rows_shallow, 30)
        assert ev.decision == 'NO_SETUP' and ev.draft is None


def test_variant_e_volume_expansion_detected():
    """Breakout-with-volume: the breakout bar's volume exceeds its 20-bar
    smoothed average (Dow volume confirmation)."""
    vols = [1.0] * 30 + [2.5]
    rows = _tape(_cons(30) + [(105.0, 105.5, 104.2, 105.0)], vols=vols)
    idx = len(rows) - 1
    ev = _eval(RangeBreakout1To1E(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'e'
    # Without the volume expansion the same breakout is NOT a setup for e.
    rows_flat = _tape(_cons(30) + [(105.0, 105.5, 104.2, 105.0)])
    ev = _eval(RangeBreakout1To1E(), rows_flat, 30)
    assert ev.decision == 'NO_SETUP' and ev.draft is None


def test_variant_f_low_volume_timing_detected():
    """Low-volume breakout timing: volume at its 100-bar historical minimum
    (vol_min_proximity <= 0.25) with expansion on the breakout bar."""
    bars = _cons(100)
    vols = [1.0] * 100
    vols[20] = 6.0                       # one early spike sets the max
    rows = _tape(bars + [(105.0, 105.5, 104.2, 105.0)], vols=vols + [1.5])
    idx = len(rows) - 1
    f = _state(rows, idx).features
    assert float(f['SOLUSDT.vol_min_proximity'].value) <= VOL_MIN_PROXIMITY_MAX
    ev = _eval(RangeBreakout1To1F(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'f'


def test_no_setup_rejected():
    """A flat tape never breaks the range: NO_SETUP, no draft."""
    rows = _tape([_wide(100.0) for _ in range(40)])
    for cls in VARIANTS.values():
        ev = _eval(cls(), rows, 39)
        assert ev.decision in ('NO_SETUP', 'NO_HABITAT') and ev.draft is None
    ev = _eval(RangeBreakout1To1Expert(), rows, 39)
    assert ev.decision == 'NO_SETUP'


def test_no_habitat_on_warmup():
    """10 bars: the 20-bar window / ATR warmup not satisfied -> NO_HABITAT
    (warmup-gated features are ABSENT, never zero)."""
    rows = _tape([_wide(100.0) for _ in range(10)])
    for cls in VARIANTS.values():
        ev = _eval(cls(), rows, 9)
        assert ev.decision == 'NO_HABITAT' and ev.draft is None


def test_unknown_variant_fails_closed():
    class Bogus(RangeBreakout1To1Expert):
        variant_id = 'zz'
    try:
        _eval(Bogus(), _tape(_cons(30) + [(105.0, 105.5, 104.2, 105.0)]), 30)
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- still_valid ------------------------------------------------------------

def test_still_valid_breakout_holds():
    """The thesis is 'the breakout holds': a close back inside the range
    (below the FROZEN breakout level for a long) before the 1:1 objective is
    the book's invalidation (Ch4.1)."""
    ex = RangeBreakout1To1Expert()
    rows = _tape(_cons(30) + [(105.0, 105.5, 104.2, 105.0)])
    idx = len(rows) - 1
    ev = _eval(ex, rows, idx)
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    ref = ev.draft.risk_geometry['breakout_ref']
    # A close above the frozen breakout level keeps the thesis alive.
    tail = _tape([(103.5, 104.0, 102.8, 103.6)], start=idx + 1)
    assert ex.still_valid(_state(rows + tail, idx + 1), ev.draft) is True
    # A close back inside the range kills it.
    tail = _tape([(101.0, 101.8, 100.6, 101.2)], start=idx + 1)
    assert ex.still_valid(_state(rows + tail, idx + 1), ev.draft) is False
    assert float(ref) > 0


def test_still_valid_fail_open():
    """Unobservable inputs fail OPEN: an unreadable thesis is not a dead
    thesis."""
    ex = RangeBreakout1To1Expert()
    draft = CandidateDraft(
        expert_id='range_breakout_1to1', expert_version='v1',
        instrument='ETHUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.5,
                       'stop_r': 1.5, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'breakout_ref': 102.0, 'variant': 'a'},
        birth_time=0)
    st = _state(_tape([_wide(100.0)] * 5), 4)     # SOLUSDT features only
    assert ex.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ---------------------------------

def test_requires_audited_against_consumption():
    """Declared requires exist and cover every group actually read (raw is the
    base layer everyone may read) — mirrors test_expert_registry."""
    ex = RangeBreakout1To1Expert()
    assert ex.requires == ('location', 'volatility', 'history', 'participation')
    for g in ex.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'window_high_20', 'window_low_20',
                   'range_height_20', 'consolidation_range',
                   'volume', 'vol_smooth_ma', 'vol_min_proximity'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(ex.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape(_cons(30) + [(105.0, 105.5, 104.2, 105.0)])
    idx = len(rows) - 1
    a = _eval(RangeBreakout1To1Expert(), rows, idx)
    b = _eval(RangeBreakout1To1Expert(), rows, idx)
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id
    assert a.draft.birth_time == b.draft.birth_time


def test_lab_smoke_no_economic_claim(tmp_path):
    """Rule-12 guard: a lab run on the synthetic tape never implies an
    economic claim."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-rb11', code_hash='',
                           data_hash='', universe=UNIVERSE, start_ns=0,
                           end_ns=0)
    r = lab.run(m, [RangeBreakout1To1Expert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
