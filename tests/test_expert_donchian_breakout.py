"""E-10 donchian_breakout expert tests (`channel_breakout` family).

Covers: D-044/D-046 variant accounting, close-confirm breakout detection on a
crafted series, no-setup / no-habitat rejection, risk_geometry values (frozen
channel band stop in R), still_valid channel-exit invalidation (including the
responsive / significant-extreme variants), fail-open, requires-vs-consumption
audit, determinism, and a lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.experts.donchian_breakout import (
    DonchianBreakoutExpert, DonchianBreakoutB, DonchianBreakoutC,
    DonchianBreakoutD, DonchianBreakoutE, DonchianBreakoutF,
    CHANNEL_N, RESPONSIVE_EXIT_N, SIGNIFICANT_EXTREME_N)

UNIVERSE = ('SOLUSDT',)

VARIANTS = {'a': DonchianBreakoutExpert, 'b': DonchianBreakoutB,
            'c': DonchianBreakoutC, 'd': DonchianBreakoutD,
            'e': DonchianBreakoutE, 'f': DonchianBreakoutF}


def _tape(closes, start=0):
    """Deterministic 1h tape; OHLC invariants hold (h=1.002c, l=0.998c)."""
    rows = []
    for i, c in enumerate(closes, start=start):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c * 1.002, 'low': c * 0.998,
                     'close': c, 'volume': 1.0, 'closed': True}))
    return rows


def _state(rows, bar_idx):
    as_of = rows[bar_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _eval(expert, rows, bar_idx):
    return expert.evaluate(_state(rows, bar_idx))


def _breakout_tape():
    """40 flat bars then a +1/bar rise to 120: at bar 59 the close (120)
    breaks the 20-bar channel high (~119.2) -> LONG setup, anchor bar 40."""
    return _tape([100.0] * 40 + [100.0 + (i + 1) for i in range(20)])


def _downside_tape():
    """40 flat bars then a -1/bar fall to 80: at bar 59 the close (80) breaks
    the 20-bar channel low -> SHORT setup, anchor bar 40."""
    return _tape([100.0] * 40 + [99.0 - i for i in range(20)])


# --- D-044 / D-046 variant accounting --------------------------------------

def test_variants_evaluated_complete():
    """Every declared variant is implemented and listed (losers included);
    the reported variant_id is a member; the search cannot be smaller than
    the retained set (D-044, D-046)."""
    ex = DonchianBreakoutExpert()
    assert set(ex.variants_evaluated) == set(CHANNEL_N) == \
        {'a', 'b', 'c', 'd', 'e', 'f'}
    for vid, cls in VARIANTS.items():
        assert cls().variant_id == vid, f'{vid} maps to {cls.__name__}'
        assert vid in ex.variants_evaluated
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)


# --- setup detection --------------------------------------------------------

def test_long_breakout_detected():
    ex = DonchianBreakoutExpert()
    rows = _breakout_tape()
    ev = _eval(ex, rows, 59)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.instrument == 'SOLUSDT'
    assert d.setup_anchor_event_id == 'SOLUSDT:41'   # run start = bar 40
    assert d.risk_geometry['entry'] == 'NEXT_BAR_CLOSE'
    assert d.risk_geometry['channel_n'] == 20
    assert d.risk_geometry['variant'] == 'a'
    assert d.risk_geometry['target_r'] == 1.0
    assert d.risk_geometry['expiry_bars'] == 8
    # The stop is the FROZEN lower band, in R (D-028): (close - band)/atr.
    f = _state(rows, 59).features
    atr = float(f['SOLUSDT.atr'].value)
    low_ref = float(f['SOLUSDT.window_low_20'].value)
    high_ref = float(f['SOLUSDT.window_high_20'].value)
    assert d.risk_geometry['atr_ref'] == atr
    assert d.risk_geometry['prior_low_ref'] == low_ref
    assert d.risk_geometry['prior_high_ref'] == high_ref
    assert abs(d.risk_geometry['stop_r'] - (120.0 - low_ref) / atr) < 1e-9
    # Issue #63: the stop IS the frozen lower band level (structural stop).
    assert d.risk_geometry['stop_ref'] == low_ref


def test_short_breakout_variant_b():
    rows = _downside_tape()
    ev = _eval(DonchianBreakoutB(), rows, 59)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'b'
    f = _state(rows, 59).features
    atr = float(f['SOLUSDT.atr'].value)
    high_ref = float(f['SOLUSDT.window_high_20'].value)
    assert d.risk_geometry['prior_high_ref'] == high_ref
    # short stop just above the upper band, in R.
    assert abs(d.risk_geometry['stop_r'] - (high_ref - 80.0) / atr) < 1e-9
    # Issue #63: the stop IS the frozen upper band level (structural stop).
    assert d.risk_geometry['stop_ref'] == high_ref


def test_variant_a_long_only():
    """Variant a is unidirectional: a downside breakout is NO_SETUP, never a
    short."""
    ev = _eval(DonchianBreakoutExpert(), _downside_tape(), 59)
    assert ev.decision == 'NO_SETUP' and ev.draft is None


def test_variant_d_uses_50_bar_window():
    """The book's N=55 is implemented on the nearest declared 50-bar window
    (window_high_50/window_low_50, G-22) — the gate reference is the 50-bar
    channel."""
    rows = _breakout_tape()          # 60 bars: the 50-bar window is present
    ev = _eval(DonchianBreakoutD(), rows, 59)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.risk_geometry['channel_n'] == 50
    assert ev.draft.risk_geometry['variant'] == 'd'
    f = _state(rows, 59).features
    assert ev.draft.risk_geometry['prior_low_ref'] == \
        float(f['SOLUSDT.window_low_50'].value)


def test_no_setup_rejected():
    """A flat tape never breaks the channel: NO_SETUP, no draft."""
    ev = _eval(DonchianBreakoutExpert(), _tape([100.0] * 40), 39)
    assert ev.decision == 'NO_SETUP' and ev.draft is None


def test_no_habitat_on_warmup():
    """10 bars: the 20-bar channel and the 14-bar ATR are absent -> NO_HABITAT
    (warmup-gated features are ABSENT, never zero)."""
    ev = _eval(DonchianBreakoutExpert(), _tape([100.0] * 10), 9)
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


def test_unknown_variant_fails_closed():
    class Bogus(DonchianBreakoutExpert):
        variant_id = 'zz'
    try:
        _eval(Bogus(), _breakout_tape(), 59)
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- still_valid ------------------------------------------------------------

def test_still_valid_channel_exit():
    """A long run ends when a close makes a new 20-bar low (Turtle channel
    exit); it holds while close stays above the LIVE channel low."""
    ex = DonchianBreakoutExpert()
    rows = _breakout_tape()
    ev = _eval(ex, rows, 59)
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    # Still valid on the next bar (close 115 above the live 20-bar low).
    assert ex.still_valid(_state(rows, 59), ev.draft) is True
    # A sharp drop that closes below the live 20-bar low kills the thesis.
    tail = _tape([115.0, 110.0, 105.0, 100.0, 95.0, 90.0], start=60)
    rows2 = rows + tail
    assert ex.still_valid(_state(rows2, 60), ev.draft) is True
    assert ex.still_valid(_state(rows2, 65), ev.draft) is False


def test_still_valid_short_channel_exit():
    ex = DonchianBreakoutB()
    rows = _downside_tape()
    ev = _eval(ex, rows, 59)
    assert ev.draft is not None and ev.draft.direction == 'SHORT'
    tail = _tape([85.0, 90.0, 95.0, 100.0, 105.0, 110.0], start=60)
    rows2 = rows + tail
    assert ex.still_valid(_state(rows2, 60), ev.draft) is True
    assert ex.still_valid(_state(rows2, 65), ev.draft) is False


def test_still_valid_responsive_exit_variant_e():
    """Variant e exits on the declared 5-bar responsive band, not the 20-bar
    channel: a shallow drift below the 5-bar low ends the thesis even while
    the 20-bar channel holds."""
    ex = DonchianBreakoutE()
    rows = _breakout_tape()
    ev = _eval(ex, rows, 59)
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'e'
    assert RESPONSIVE_EXIT_N == 5
    tail = _tape([119.0, 118.0, 117.0, 116.0, 115.0, 114.0], start=60)
    rows2 = rows + tail
    # close 114 at bar 65 < the previous 5 bars' low (~114.78) -> exit fires.
    assert ex.still_valid(_state(rows2, 65), ev.draft) is False


def test_still_valid_significant_extreme_variant_f():
    ex = DonchianBreakoutF()
    rows = _breakout_tape()
    ev = _eval(ex, rows, 59)
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'f'
    assert SIGNIFICANT_EXTREME_N == 3
    tail = _tape([119.0, 118.0, 117.0], start=60)
    rows2 = rows + tail
    # close 117 at bar 62 < the previous 3 bars' low (~117.76) -> exit fires.
    assert ex.still_valid(_state(rows2, 62), ev.draft) is False


def test_still_valid_fail_open():
    """Unobservable inputs (a state without the channel features) fail OPEN:
    an unreadable thesis is not a dead thesis."""
    ex = DonchianBreakoutExpert()
    draft = CandidateDraft(
        expert_id='donchian_breakout', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'channel_n': 20, 'variant': 'a'},
        birth_time=0)
    st = _state(_tape([100.0] * 5), 4)          # no window_* features
    assert ex.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ---------------------------------

def test_requires_audited_against_consumption():
    """Declared requires exist and cover every group actually read (raw is
    the base layer everyone may read) — mirrors test_expert_registry."""
    ex = DonchianBreakoutExpert()
    assert ex.requires == ('location', 'volatility', 'history')
    for g in ex.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'window_high_20', 'window_low_20', 'history'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(ex.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _breakout_tape()
    a = _eval(DonchianBreakoutExpert(), rows, 59)
    b = _eval(DonchianBreakoutExpert(), rows, 59)
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
    m = ExperimentManifest(experiment_id='exp-donchian', code_hash='',
                           data_hash='', universe=UNIVERSE, start_ns=0,
                           end_ns=0)
    r = lab.run(m, [DonchianBreakoutExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
