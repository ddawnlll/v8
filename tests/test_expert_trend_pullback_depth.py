"""E-02 trend_pullback_depth expert tests (`trend_continuation` /
`pullback_in_trend` family, variants a..g).

Covers: D-044/D-046 variant accounting, setup detection on crafted
uptrend+dip tapes (depth gates 38.2/50/61.8%, Dow 1/3-2/3 band, MA-rebound,
double-MA-fan, dip-low close-reclaim), no-setup / no-habitat rejection,
risk_geometry values (frozen impulse/dip-low reference in R-geometry, D-028),
still_valid invalidation (trend flip / close through the frozen low) and
fail-open, requires-vs-consumption audit, determinism, and a lab.run rule-12
smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.experts.trend_pullback_depth import (
    TrendPullbackDepthExpert, TrendPullbackDepthB, TrendPullbackDepthC,
    TrendPullbackDepthD, TrendPullbackDepthE, TrendPullbackDepthF,
    TrendPullbackDepthG, VARIANTS_EVALUATED, DIP_LOW_N)

UNIVERSE = ('SOLUSDT',)

VARIANTS = {'a': TrendPullbackDepthExpert, 'b': TrendPullbackDepthB,
            'c': TrendPullbackDepthC, 'd': TrendPullbackDepthD,
            'e': TrendPullbackDepthE, 'f': TrendPullbackDepthF,
            'g': TrendPullbackDepthG}


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


def _wide(c, w=0.025):
    return (c, c * (1 + w), c * (1 - w), c)


def _base():
    """40-bar impulse: a decline, a wide swing-low bar, a rise, a wide
    spike bar whose HIGH is the swing high (the significance filter needs
    wide pivot bars, Ch27.2)."""
    bars = []
    c = 130.0
    for i in range(19):
        bars.append(_wide(c))
        c -= 1.0
    bars.append(_wide(c, w=0.05))                # swing-low bar (low ~105.45)
    c = 111.0
    for i in range(19):
        c += 1.0
        bars.append(_wide(c))
    bars.append((130.0, 130.0 * 1.06, 130.0 * 0.94, 130.0))   # spike high
    return bars


def _state(rows, bar_idx):
    as_of = rows[bar_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _eval(expert, rows, bar_idx):
    return expert.evaluate(_state(rows, bar_idx))


def _depth_tape():
    """V-shaped dip (5 down to 123, 5 up to 127) plus hold bars after the
    spike; the swing pair confirms at bar 49 where the depth variants fire."""
    bars = _base()
    c = 130.0
    for i in range(5):
        c -= (130.0 - 123.0) / 5.0
        bars.append(_wide(c))
    for i in range(5):
        c += (127.0 - 123.0) / 5.0
        bars.append(_wide(c))
    for x in (127.0, 127.2, 127.4):
        bars.append(_wide(x))
    return _tape(bars)


# --- D-044 / D-046 variant accounting --------------------------------------

def test_variants_evaluated_complete():
    """Every declared variant is implemented and listed (losers included); the
    reported variant_id is a member; the search cannot be smaller than the
    retained set (D-044, D-046)."""
    ex = TrendPullbackDepthExpert()
    assert set(ex.variants_evaluated) == set(VARIANTS_EVALUATED) == \
        {'a', 'b', 'c', 'd', 'e', 'f', 'g'}
    for vid, cls in VARIANTS.items():
        assert cls().variant_id == vid, f'{vid} maps to {cls.__name__}'
        assert vid in ex.variants_evaluated
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)


# --- setup detection --------------------------------------------------------

def test_depth_variants_detected():
    """Variants a/b/c (depth gates 38.2/50/61.8%) and g (Dow 1/3-2/3 band)
    fire on the reclaimed V-dip tape at bar 49; all emit LONG drafts with the
    frozen impulse swing low as prior_low_ref."""
    rows = _depth_tape()
    idx = 49
    f = _state(rows, idx).features
    sh = float(f['SOLUSDT.swing_high_10'].value)
    sl = float(f['SOLUSDT.swing_low_10'].value)
    close = float(f['SOLUSDT.close'].value)
    assert sh > sl > 0
    depth = (sh - close) / (sh - sl)
    assert depth <= 0.382          # satisfies the strictest gate
    for cls in (TrendPullbackDepthExpert, TrendPullbackDepthB,
                TrendPullbackDepthC, TrendPullbackDepthG):
        ev = _eval(cls(), rows, idx)
        assert ev.decision == 'CANDIDATE' and ev.draft is not None
        d = ev.draft
        assert d.direction == 'LONG'
        assert d.risk_geometry['entry'] == 'NEXT_BAR_CLOSE'
        assert d.risk_geometry['target_r'] == 1.0
        assert d.risk_geometry['stop_r'] == 1.0
        assert d.risk_geometry['expiry_bars'] == 8
        assert d.risk_geometry['atr_ref'] == float(f['SOLUSDT.atr'].value)
        assert d.risk_geometry['prior_low_ref'] == sl
        assert d.risk_geometry['variant'] == cls().variant_id


def test_depth_variant_anchors():
    """The depth anchor is the first bar of the current run inside the depth
    band with the trend aligned (D-026), stable across detection clocks."""
    rows = _depth_tape()
    a49 = _eval(TrendPullbackDepthExpert(), rows, 49)
    a50 = _eval(TrendPullbackDepthExpert(), rows, 50)
    assert a49.draft is not None and a50.draft is not None
    assert a49.draft.setup_anchor_event_id == 'SOLUSDT:49'
    assert a50.draft.setup_anchor_event_id == 'SOLUSDT:49'   # key stability
    g49 = _eval(TrendPullbackDepthG(), rows, 49)
    assert g49.draft is not None
    assert g49.draft.setup_anchor_event_id == 'SOLUSDT:43'


def test_variant_d_ma_rebound_detected():
    """MA-rebound: the fast EMA crosses back above the slow EMA (the short MA
    rebounds off the long MA) with the close above the slow EMA."""
    bars = _base()
    c = 130.0
    for i in range(10):
        c -= 0.6
        bars.append(_wide(c))
    for x in (123.8, 123.6, 127.0, 129.0, 130.5):
        bars.append(_wide(x))
    rows = _tape(bars)
    idx = 52
    ev = _eval(TrendPullbackDepthD(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'd'
    assert ev.draft.setup_anchor_event_id == 'SOLUSDT:53'   # the cross bar


def test_variant_e_fan_detected():
    """Double-MA-fan: fan aligned (fast > slow), close held above the slow EMA
    through a shallow dip that reclaimed the fast-EMA zone."""
    bars = _base()
    c = 130.0
    for i in range(8):
        c -= 0.5
        bars.append(_wide(c))
    for x in (126.5, 127.0, 127.5, 128.0):
        bars.append(_wide(x))
    rows = _tape(bars)
    idx = 49
    ev = _eval(TrendPullbackDepthE(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'e'
    assert ev.draft.setup_anchor_event_id == 'SOLUSDT:50'


def test_variant_f_dip_reclaim_detected():
    """Close-reclaim of the dip low: a fresh dip low reclaimed by a close back
    above it while the current bar does not extend the dip."""
    bars = _base()
    c = 130.0
    for i in range(10):
        c -= 0.6
        bars.append(_wide(c))
    bars.append((123.5, 124.2, 123.5, 123.5))   # dip bar (low 123.5)
    bars.append((125.5, 126.3, 125.0, 125.5))   # reclaim
    bars.append((127.0, 127.8, 126.4, 127.0))
    rows = _tape(bars)
    idx = 52
    ev = _eval(TrendPullbackDepthF(), rows, idx)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'f'
    # The frozen structural low is the recent dip low (min low of the
    # DIP_LOW_N bars before the newest).
    hist = _state(rows, idx).features['SOLUSDT.history'].value
    dip = min(b[3] for b in hist[-(DIP_LOW_N + 1):-1])
    assert abs(ev.draft.risk_geometry['prior_low_ref'] - dip) < 1e-9
    assert ev.draft.setup_anchor_event_id == 'SOLUSDT:53'


def test_no_setup_rejected():
    """A flat tape has no uptrend / no dip: NO_SETUP, no draft."""
    rows = _tape([_wide(100.0) for _ in range(50)])
    for cls in VARIANTS.values():
        ev = _eval(cls(), rows, 49)
        assert ev.decision == 'NO_SETUP' and ev.draft is None


def test_no_habitat_on_warmup():
    """10 bars: EMA/ATR warmup not satisfied -> NO_HABITAT (warmup-gated
    features are ABSENT, never zero)."""
    rows = _tape([_wide(100.0) for _ in range(10)])
    for cls in VARIANTS.values():
        ev = _eval(cls(), rows, 9)
        assert ev.decision == 'NO_HABITAT' and ev.draft is None


def test_unknown_variant_fails_closed():
    class Bogus(TrendPullbackDepthExpert):
        variant_id = 'zz'
    try:
        _eval(Bogus(), _depth_tape(), 49)
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- still_valid ------------------------------------------------------------

def test_still_valid_depth():
    """The thesis is 'pullback inside an intact uptrend': it dies when the
    trend alignment flips (fast <= slow) or the close breaks the frozen
    impulse swing low."""
    ex = TrendPullbackDepthExpert()
    rows = _depth_tape()
    ev = _eval(ex, rows, 49)
    assert ev.draft is not None
    ref = ev.draft.risk_geometry['prior_low_ref']
    # A close above the frozen swing low keeps the thesis alive.
    tail = _tape([_wide(128.0)], start=len(rows))
    assert ex.still_valid(_state(rows + tail, len(rows)), ev.draft) is True
    # A close below the frozen impulse low kills it.
    tail = _tape([_wide(105.0)], start=len(rows))
    assert ex.still_valid(_state(rows + tail, len(rows)), ev.draft) is False
    assert float(ref) > 0


def test_still_valid_trend_flip():
    """A trend flip (fast <= slow) ends the thesis even while the price stays
    above the structural low."""
    ex = TrendPullbackDepthB()
    rows = _depth_tape()
    ev = _eval(ex, rows, 49)
    assert ev.draft is not None
    # A long slide that leaves price above the swing low but kills the
    # fast/slow alignment invalidates the pullback thesis.
    tail = _tape([_wide(120.0), _wide(117.0), _wide(115.0),
                  _wide(113.0), _wide(112.0)], start=len(rows))
    assert ex.still_valid(_state(rows + tail, len(rows) + 3), ev.draft) is False


def test_still_valid_fail_open():
    """Unobservable inputs fail OPEN: an unreadable thesis is not a dead
    thesis."""
    ex = TrendPullbackDepthExpert()
    draft = CandidateDraft(
        expert_id='trend_pullback_depth', expert_version='v1',
        instrument='ETHUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'prior_low_ref': 100.0, 'variant': 'a'},
        birth_time=0)
    st = _state(_tape([_wide(100.0)] * 5), 4)     # SOLUSDT features only
    assert ex.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ---------------------------------

def test_requires_audited_against_consumption():
    """Declared requires exist and cover every group actually read (raw is the
    base layer everyone may read) — mirrors test_expert_registry."""
    ex = TrendPullbackDepthExpert()
    assert ex.requires == ('trend', 'location', 'volatility', 'history')
    for g in ex.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history', 'ema_fast', 'ema_slow',
                   'swing_high_10', 'swing_low_10'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(ex.requires) | {'raw'}
    assert DIP_LOW_N == 5


def test_evaluation_deterministic():
    rows = _depth_tape()
    a = _eval(TrendPullbackDepthExpert(), rows, 49)
    b = _eval(TrendPullbackDepthExpert(), rows, 49)
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
    m = ExperimentManifest(experiment_id='exp-tpdepth', code_hash='',
                           data_hash='', universe=UNIVERSE, start_ns=0,
                           end_ns=0)
    r = lab.run(m, [TrendPullbackDepthExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
