"""E-01 failed_breakout_2b expert tests (`liquidity_vacuum_reentry` /
`failed_breakout_reentry` family, variants b..g).

Covers: D-044/D-046 variant accounting (variant `a` is the registered pilot's
and is NOT implemented here — CRIT-4), setup detection on crafted false-
breakout tapes (2B swing, Hikkake bull/bear, Oops, failed cloud, failed S/R),
no-setup / no-habitat rejection, risk_geometry values (frozen level refs in
R-geometry, D-028), still_valid invalidation (close back through the frozen
level) and fail-open, requires-vs-consumption audit, determinism, and a
lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.experts.failed_breakout_2b import (
    FailedBreakout2BExpert, FailedBreakout2BC, FailedBreakout2BD,
    FailedBreakout2BE, FailedBreakout2BF, FailedBreakout2BG,
    VARIANTS_EVALUATED, HIKKAKE_WINDOW_BARS, CLOUD_N)

UNIVERSE = ('SOLUSDT',)

VARIANTS = {'b': FailedBreakout2BExpert, 'c': FailedBreakout2BC,
            'd': FailedBreakout2BD, 'e': FailedBreakout2BE,
            'f': FailedBreakout2BF, 'g': FailedBreakout2BG}


def _tape(bars, start=0):
    """Deterministic 1h tape from (open, high, low, close) tuples."""
    rows = []
    for i, (o, h, l, c) in enumerate(bars, start=start):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': 1.0, 'closed': True}))
    return rows


def _wide(c, w=0.01):
    return (c, c * (1 + w), c * (1 - w), c)


def _ctx(n=30, base=100.0, step=0.5):
    return [_wide(base + (i % 3) * step) for i in range(n)]


def _state(rows, bar_idx):
    as_of = rows[bar_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _eval(expert, rows, bar_idx):
    return expert.evaluate(_state(rows, bar_idx))


# --- D-044 / D-046 variant accounting --------------------------------------

def test_variants_evaluated_complete():
    """Variant `a` is the registered pilot's and is deliberately not in this
    module's variants_evaluated (CRIT-4); b..g are all implemented, the
    reported variant_id is a member, and the search universe cannot be smaller
    than the retained set (D-044, D-046)."""
    ex = FailedBreakout2BExpert()
    assert ex.variant_id == 'b'
    assert set(ex.variants_evaluated) == set(VARIANTS_EVALUATED) == \
        {'b', 'c', 'd', 'e', 'f', 'g'}
    assert 'a' not in ex.variants_evaluated
    for vid, cls in VARIANTS.items():
        assert cls().variant_id == vid, f'{vid} maps to {cls.__name__}'
        assert vid in ex.variants_evaluated
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)
    assert HIKKAKE_WINDOW_BARS == 3 and CLOUD_N == 26


# --- setup detection --------------------------------------------------------

def test_variant_b_2b_swing_detected():
    """2B non-failure swing: prior close below the significant swing low,
    current close back above it -> LONG, close-based reclaim."""
    bars = []
    c = 130.0
    for i in range(19):
        bars.append(_wide(c))
        c -= 1.0
    bars.append(_wide(c, w=0.06))                # swing-low bar (low ~104.3)
    for i in range(15):
        c += 1.0
        bars.append(_wide(c))
    bars.append((124.0, 124.5, 103.5, 103.8))    # failed breakdown
    bars.append((104.0, 105.0, 103.5, 106.0))    # reclaim above the swing low
    rows = _tape(bars)
    idx = len(rows) - 1
    ev = _eval(FailedBreakout2BExpert(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    f = _state(rows, idx).features
    sw_low = float(f['SOLUSDT.swing_low_10'].value)
    assert sw_low > 0
    assert d.risk_geometry['prior_low_ref'] == sw_low
    assert d.risk_geometry['entry'] == 'NEXT_BAR_CLOSE'
    assert d.risk_geometry['target_r'] == 1.0
    assert d.risk_geometry['stop_r'] == 1.0
    assert d.risk_geometry['expiry_bars'] == 8
    assert d.risk_geometry['atr_ref'] == float(f['SOLUSDT.atr'].value)
    assert d.risk_geometry['variant'] == 'b'
    # Single-bar completion: the anchor is the reclaim bar itself.
    assert d.setup_anchor_event_id == f'SOLUSDT:{idx + 1}'


def test_variant_c_hikkake_bullish_detected():
    """Hikkake bullish: inside bar, false close below its low, then a close
    back above its high within 3 bars -> LONG."""
    bars = _ctx(30) + [
        (101.0, 102.5, 97.5, 101.0),   # prior bar
        (101.0, 102.0, 98.0, 101.0),   # inside bar
        (97.0, 101.5, 96.8, 97.2),     # false breakdown
        (102.8, 103.0, 101.8, 102.8),  # reclaim above inside high
    ]
    rows = _tape(bars)
    idx = len(rows) - 1
    ev = _eval(FailedBreakout2BC(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'c'
    assert abs(d.risk_geometry['prior_low_ref'] - 98.0) < 1e-9  # inside low
    assert d.setup_anchor_event_id == f'SOLUSDT:{idx + 1}'


def test_variant_d_hikkake_bearish_detected():
    """Hikkake bearish: inside bar, false close above its high, then a close
    back below its low -> SHORT."""
    bars = _ctx(30) + [
        (101.0, 102.5, 97.5, 101.0),
        (101.0, 102.0, 98.0, 101.0),   # inside bar
        (103.0, 103.4, 98.5, 102.8),   # false breakout
        (97.4, 102.2, 97.0, 97.4),     # reclaim below inside low
    ]
    rows = _tape(bars)
    idx = len(rows) - 1
    ev = _eval(FailedBreakout2BD(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    assert abs(d.risk_geometry['prior_high_ref'] - 102.0) < 1e-9  # inside high
    assert d.risk_geometry['variant'] == 'd'


def test_variant_e_oops_detected():
    """William's Oops: a gap open beyond the prior range reclaimed by a close
    back through the prior extreme (buy-stop at the prior low)."""
    bars = _ctx(30) + [(99.2, 100.4, 98.9, 100.3)]
    rows = _tape(bars)
    idx = len(rows) - 1
    f = _state(rows, idx).features
    assert float(f['SOLUSDT.gap_dir'].value) == -1.0     # gap down
    ev = _eval(FailedBreakout2BE(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    prior_low = float(f['SOLUSDT.history'].value[-2][3])
    assert abs(d.risk_geometry['prior_low_ref'] - prior_low) < 1e-9


def test_variant_f_failed_cloud_detected():
    """Ichimoku failed cloud: a close above the cloud-proxy top then a close
    back below it -> SHORT."""
    bars = _ctx(34) + [
        (105.5, 106.0, 105.0, 105.2),  # close above the cloud
        (99.5, 100.5, 99.2, 99.5),     # close back below
    ]
    rows = _tape(bars)
    idx = len(rows) - 1
    f = _state(rows, idx).features
    hist = f['SOLUSDT.history'].value
    # The cloud proxy at the PRIOR bar: midrange(26) of the 26 bars before it.
    # In the 32-bar history window (bars n-32..n-1) the prior bar is index 30
    # and its 26 preceding bars are indices 4..29.
    top = (max(b[2] for b in hist[4:30])
           + min(b[3] for b in hist[4:30])) / 2.0
    ev = _eval(FailedBreakout2BF(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    assert abs(d.risk_geometry['prior_high_ref'] - top) < 1e-9
    assert d.risk_geometry['variant'] == 'f'


def test_variant_g_failed_sr_long_detected():
    """Failed S/R close-through (long): a close through the 20-bar window low
    then a close back through it."""
    bars = _ctx(30) + [
        (97.0, 98.0, 96.6, 97.2),      # close through the window low
        (99.0, 100.0, 98.4, 99.8),     # close back through it
    ]
    rows = _tape(bars)
    idx = len(rows) - 1
    f = _state(rows, idx).features
    hist = f['SOLUSDT.history'].value
    level = min(b[3] for b in hist[-22:-2])      # the prior-bar window low
    ev = _eval(FailedBreakout2BG(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'LONG'
    assert abs(d.risk_geometry['prior_low_ref'] - level) < 1e-9


def test_variant_g_failed_sr_short_detected():
    """Failed S/R close-through (short)."""
    bars = _ctx(30) + [
        (103.2, 103.6, 102.2, 103.0),  # close through the window high
        (100.2, 102.6, 100.0, 100.5),  # close back through it
    ]
    rows = _tape(bars)
    idx = len(rows) - 1
    f = _state(rows, idx).features
    hist = f['SOLUSDT.history'].value
    level = max(b[2] for b in hist[-22:-2])      # the prior-bar window high
    ev = _eval(FailedBreakout2BG(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert d.direction == 'SHORT'
    assert abs(d.risk_geometry['prior_high_ref'] - level) < 1e-9


def test_no_setup_rejected():
    """A flat tape has no false move and no significant swing: NO_SETUP."""
    rows = _tape([_wide(100.0) for _ in range(40)])
    for cls in VARIANTS.values():
        ev = _eval(cls(), rows, 39)
        assert ev.decision in ('NO_SETUP', 'NO_HABITAT') and ev.draft is None
    ev = _eval(FailedBreakout2BExpert(), rows, 39)
    assert ev.decision == 'NO_SETUP'


def test_no_habitat_on_warmup():
    """10 bars: ATR / history warmup not satisfied -> NO_HABITAT (warmup-gated
    features are ABSENT, never zero)."""
    rows = _tape([_wide(100.0) for _ in range(10)])
    for cls in VARIANTS.values():
        ev = _eval(cls(), rows, 9)
        assert ev.decision == 'NO_HABITAT' and ev.draft is None


def test_unknown_variant_fails_closed():
    class Bogus(FailedBreakout2BExpert):
        variant_id = 'zz'
    try:
        _eval(Bogus(), _tape([_wide(100.0)] * 40), 39)
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- still_valid ------------------------------------------------------------

def test_still_valid_2b_swing():
    """The thesis is 'the false move failed': the long holds while the close
    stays above the frozen swing low; a close back below it is thesis
    invalidation (D-029), distinct from a price stop."""
    bars = []
    c = 130.0
    for i in range(19):
        bars.append(_wide(c))
        c -= 1.0
    bars.append(_wide(c, w=0.06))
    for i in range(15):
        c += 1.0
        bars.append(_wide(c))
    bars.append((124.0, 124.5, 103.5, 103.8))
    bars.append((104.0, 105.0, 103.5, 106.0))
    rows = _tape(bars)
    idx = len(rows) - 1
    ex = FailedBreakout2BExpert()
    ev = _eval(ex, rows, idx)
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    ref = ev.draft.risk_geometry['prior_low_ref']
    # A close above the level keeps the thesis alive.
    tail = _tape([(106.0, 106.5, 105.0, 106.2)], start=idx + 1)
    assert ex.still_valid(_state(rows + tail, idx + 1), ev.draft) is True
    # A close back below the frozen swing low kills it.
    tail = _tape([(104.0, 104.5, 103.2, 103.5)], start=idx + 1)
    assert ex.still_valid(_state(rows + tail, idx + 1), ev.draft) is False
    assert float(ev.draft.risk_geometry['prior_low_ref']) > 0


def test_still_valid_hikkake_short():
    """A bearish Hikkake short dies when the close rises back above the frozen
    inside-bar high."""
    bars = _ctx(30) + [
        (101.0, 102.5, 97.5, 101.0),
        (101.0, 102.0, 98.0, 101.0),
        (103.0, 103.4, 98.5, 102.8),
        (97.4, 102.2, 97.0, 97.4),
    ]
    rows = _tape(bars)
    idx = len(rows) - 1
    ex = FailedBreakout2BD()
    ev = _eval(ex, rows, idx)
    assert ev.draft is not None and ev.draft.direction == 'SHORT'
    tail = _tape([(98.0, 98.6, 97.4, 98.2)], start=idx + 1)
    assert ex.still_valid(_state(rows + tail, idx + 1), ev.draft) is True
    tail = _tape([(102.4, 103.0, 101.8, 102.6)], start=idx + 1)
    assert ex.still_valid(_state(rows + tail, idx + 1), ev.draft) is False


def test_still_valid_fail_open():
    """Unobservable inputs fail OPEN: an unreadable thesis is not a dead
    thesis. A draft on an instrument the state carries no features for (the
    close is unobservable) must not terminate the thesis."""
    ex = FailedBreakout2BExpert()
    draft = CandidateDraft(
        expert_id='failed_breakout_2b', expert_version='v1',
        instrument='ETHUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'prior_low_ref': 100.0, 'variant': 'b'},
        birth_time=0)
    st = _state(_tape([_wide(100.0)] * 5), 4)     # SOLUSDT features only
    assert ex.still_valid(st, draft) is True
    # A draft without a frozen reference also fails open (legacy drafts).
    draft2 = CandidateDraft(
        expert_id='failed_breakout_2b', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'b'},
        birth_time=0)
    assert ex.still_valid(st, draft2) is True


# --- registry audit, determinism, lab smoke ---------------------------------

def test_requires_audited_against_consumption():
    """Declared requires exist and cover every group actually read (raw is the
    base layer everyone may read) — mirrors test_expert_registry."""
    ex = FailedBreakout2BExpert()
    assert ex.requires == ('location', 'volatility', 'history', 'candle_shape')
    for g in ex.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'swing_low_10',
                   'window_high_20', 'window_low_20',
                   'inside_bar', 'outside_bar', 'gap_dir', 'gap_size'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(ex.requires) | {'raw'}


def test_evaluation_deterministic():
    bars = []
    c = 130.0
    for i in range(19):
        bars.append(_wide(c))
        c -= 1.0
    bars.append(_wide(c, w=0.06))
    for i in range(15):
        c += 1.0
        bars.append(_wide(c))
    bars.append((124.0, 124.5, 103.5, 103.8))
    bars.append((104.0, 105.0, 103.5, 106.0))
    rows = _tape(bars)
    idx = len(rows) - 1
    a = _eval(FailedBreakout2BExpert(), rows, idx)
    b = _eval(FailedBreakout2BExpert(), rows, idx)
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
    m = ExperimentManifest(experiment_id='exp-fb2b', code_hash='',
                           data_hash='', universe=UNIVERSE, start_ns=0,
                           end_ns=0)
    r = lab.run(m, [FailedBreakout2BExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
