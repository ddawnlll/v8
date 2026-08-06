"""E-18 ichimoku_cloud expert tests (`cloud_trend` family).

Covers: D-044 honest variant accounting (a/b/d declared but NOT evaluated on
the 32-bar history pin), Tenkan-Kijun crossover detection on a crafted series
(bullish and bearish), no-setup / no-habitat rejection, risk_geometry values,
still_valid Kijun-thesis invalidation, fail-open, requires-vs-consumption
audit, and a lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, CandidateDraft, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.experts.ichimoku_cloud import (IchimokuCloudExpert, TENKAN_N, KIJUN_N)

UNIVERSE = ('SOLUSDT',)


def _tape(closes, start=0):
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


def _bullish_cross_tape():
    """26 flat bars, a 2-bar dip to 95, then a rally to 113. The dip exits the
    9-bar Tenkan window while still inside the 26-bar Kijun window at bar 36,
    so Tenkan jumps above Kijun exactly there (a fresh bullish cross with
    close 113 > Kijun ~104)."""
    closes = [100.0] * 26 + [95.0, 95.0]
    closes += [97.0, 99.0, 101.0, 103.0, 105.0, 107.0, 109.0, 111.0, 113.0]
    return _tape(closes)


def _bearish_cross_tape():
    """Mirror: 26 flat bars, a 2-bar spike to 105, then a fall to 87. The
    spike exits the Tenkan window while still inside the Kijun window at bar
    36 -> a fresh bearish cross with close 87 < Kijun ~96."""
    closes = [100.0] * 26 + [105.0, 105.0]
    closes += [103.0, 101.0, 99.0, 97.0, 95.0, 93.0, 91.0, 89.0, 87.0]
    return _tape(closes)


# --- D-044 / D-046 honest accounting ---------------------------------------

def test_variants_evaluated_honest():
    """Only the implemented+tested variant is claimed evaluated (D-044);
    variants a/b/d need the 78-bar displaced cloud and are explicitly NOT in
    variants_evaluated (prereg section 11 reads that field as implemented
    episode series)."""
    ex = IchimokuCloudExpert()
    assert ex.variant_id == 'c'
    assert ex.variants_evaluated == ('c',)
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)
    assert ex.DECLARED_NOT_EVALUATED == ('a', 'b', 'd')
    for vid in ex.DECLARED_NOT_EVALUATED:
        assert vid not in ex.variants_evaluated, \
            f'{vid}: a declared-but-unevaluated variant must not be counted'


# --- setup detection --------------------------------------------------------

def test_bullish_cross_detected():
    ex = IchimokuCloudExpert()
    rows = _bullish_cross_tape()
    ev = _eval(ex, rows, 36)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    d = ev.draft
    assert TENKAN_N == 9 and KIJUN_N == 26       # declared Ichimoku params
    assert d.direction == 'LONG'
    assert d.instrument == 'SOLUSDT'
    assert d.setup_anchor_event_id == 'SOLUSDT:37'      # the cross bar
    assert d.risk_geometry['entry'] == 'NEXT_BAR_CLOSE'
    assert d.risk_geometry['target_r'] == 1.0
    assert d.risk_geometry['stop_r'] == 1.0
    assert d.risk_geometry['expiry_bars'] == 8
    f = _state(rows, 36).features
    assert d.risk_geometry['atr_ref'] == float(f['SOLUSDT.atr'].value)
    assert d.risk_geometry['variant'] == 'c'


def test_cross_does_not_fire_before_the_cross_bar():
    """The crossover is a discrete event: bars before the cross are NO_SETUP
    even though the tape is trending (Tenkan == Kijun during a symmetric
    move)."""
    ex = IchimokuCloudExpert()
    rows = _bullish_cross_tape()
    for bar_idx in (34, 35):
        ev = _eval(ex, rows, bar_idx)
        assert ev.decision == 'NO_SETUP' and ev.draft is None, bar_idx


def test_bearish_cross_detected():
    ex = IchimokuCloudExpert()
    rows = _bearish_cross_tape()
    ev = _eval(ex, rows, 36)
    assert ev.decision == 'CANDIDATE' and ev.draft is not None
    assert ev.draft.direction == 'SHORT'
    assert ev.draft.setup_anchor_event_id == 'SOLUSDT:37'


def test_no_setup_rejected():
    """A flat tape never crosses (Tenkan == Kijun): NO_SETUP, no draft."""
    ev = _eval(IchimokuCloudExpert(), _tape([100.0] * 40), 39)
    assert ev.decision == 'NO_SETUP' and ev.draft is None


def test_no_habitat_on_warmup():
    """Fewer than 27 bars: Kijun (26) plus the previous bar's values are not
    computable -> NO_HABITAT (warmup is absence, never a value)."""
    ev = _eval(IchimokuCloudExpert(), _tape([100.0] * 20), 19)
    assert ev.decision == 'NO_HABITAT' and ev.draft is None


# --- still_valid ------------------------------------------------------------

def test_still_valid_kijun_thesis():
    """The thesis is the cross aligned with the trend line: holding while the
    close stays above the LIVE Kijun; a close back through it kills it."""
    ex = IchimokuCloudExpert()
    rows = _bullish_cross_tape()
    ev = _eval(ex, rows, 36)
    assert ev.draft is not None and ev.draft.direction == 'LONG'
    # Next bar (close 105 > Kijun ~104): thesis alive.
    tail = _tape([105.0, 100.0, 95.0, 90.0], start=37)
    rows2 = rows + tail
    assert ex.still_valid(_state(rows2, 37), ev.draft) is True
    # A drop to 90 closes well below the live Kijun: thesis dead.
    assert ex.still_valid(_state(rows2, 40), ev.draft) is False


def test_still_valid_fail_open():
    """Unobservable inputs (too few bars for a Kijun) fail OPEN."""
    ex = IchimokuCloudExpert()
    draft = CandidateDraft(
        expert_id='ichimoku_cloud', expert_version='v1',
        instrument='SOLUSDT', direction='LONG', setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0,
                       'variant': 'c'},
        birth_time=0)
    st = _state(_tape([100.0] * 5), 4)          # 5 bars: no Kijun
    assert ex.still_valid(st, draft) is True


# --- registry audit, determinism, lab smoke ---------------------------------

def test_requires_audited_against_consumption():
    """The declared requires cover every group actually read (Tenkan/Kijun are
    computed inside the expert from the `history` OHLC, so no location/trend
    group is consumed) — mirrors test_expert_registry."""
    ex = IchimokuCloudExpert()
    assert ex.requires == ('volatility', 'history')
    for g in ex.requires:
        assert g in FEATURE_GROUPS
    consumption = {'close', 'atr', 'history'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(ex.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _bullish_cross_tape()
    a = _eval(IchimokuCloudExpert(), rows, 36)
    b = _eval(IchimokuCloudExpert(), rows, 36)
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
    m = ExperimentManifest(experiment_id='exp-ichimoku', code_hash='',
                           data_hash='', universe=UNIVERSE, start_ns=0,
                           end_ns=0)
    r = lab.run(m, [IchimokuCloudExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
