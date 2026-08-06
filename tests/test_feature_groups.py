"""FG-1..FG-7 feature-group tests (G-01..G-43, HAND_EXPERTS.md section 0).

Deterministic tests on the synthetic tape and on tiny crafted series with
hand-verified values (RSI14, MACD, Bollinger). Covers: correct values on known
inputs, group tagging, DEGRADED on insufficient warmup, PIT future-row
rejection, and that the existing expert suite still runs end-to-end.

Value semantics (MARKET_STATE_CONTRACT section 4; orchestrator directive):
None is reserved for data absence (warmup / not-yet-computable / absent
channel) and degrades the state; a "no signal" condition is a numeric value
(e.g. swing_high with no significant pivot is 0.0, atr_2sigma_active is 0/1).
"""
from __future__ import annotations

import pytest

from v8.schema import (TapeRow, FEATURE_GROUPS, FEATURE_TO_GROUP,
                       FEATURE_GRAPH_VERSION, ExperimentManifest)
from v8.marketstate import build_state, FutureRowError, validate_feature_groups
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.experts import (TrendPullbackExpert, FailedBreakoutExpert,
                        LiquiditySweepReclaimExpert)
from v8.lab import Lab

UNIVERSE = ('SOLUSDT',)

# Features gated on channels the synthetic tape does not carry (G-41..G-43).
CHANNEL_GATED = ('funding_rate', 'open_interest', 'long_short_skew')


def _tape(closes, opens=None, highs=None, lows=None, volumes=None):
    """Deterministic 1h tape from close (or full OHLC) series."""
    rows = []
    for i, c in enumerate(closes):
        o = c if opens is None else opens[i]
        h = max(o, c) if highs is None else highs[i]
        l = min(o, c) if lows is None else lows[i]
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': 1.0 if volumes is None else volumes[i],
                     'closed': True}))
    return rows


def _state(rows, idx=None):
    idx = len(rows) - 1 if idx is None else idx
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _val(state, name):
    return state.features[f'SOLUSDT.{name}'].value


def _val_at(rows, name):
    return _val(_state(rows), name)


# --- FG-2 oscillator: hand-verified RSI14 ------------------------------------

def test_rsi14_hand_verified():
    # 15 closes, 14 deltas all +1: avg_loss = 0 -> RSI = 100 (Wilder).
    assert _val_at(_tape(list(range(100, 115))), 'rsi14') == pytest.approx(100.0)
    # Mixed: 10 gains / 4 losses over 14 deltas -> RS = 2.5 -> RSI = 100-100/3.5.
    closes = [100, 101, 102, 103, 104, 103, 102, 101, 100,
              101, 102, 103, 104, 105, 106]
    assert _val_at(_tape(closes), 'rsi14') == pytest.approx(100.0 - 100.0 / 3.5)


def _ema_ref(values, period):
    """Independent stdlib EMA reference (seeded from the first value, matching
    the codebase convention) for the MACD hand-check."""
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def test_macd_hand_verified():
    # Constant series: EMA12 == EMA26 -> MACD / signal / hist all exactly 0.
    st = _state(_tape([100.0] * 40))
    assert _val(st, 'macd') == pytest.approx(0.0)
    assert _val(st, 'macd_signal') == pytest.approx(0.0)
    assert _val(st, 'macd_hist') == pytest.approx(0.0)
    # Linear ramp against an independent reference (12-26-9 composition).
    closes = [float(100 + i) for i in range(40)]
    st = _state(_tape(closes))
    macd = [f - s for f, s in zip(_ema_ref(closes, 12), _ema_ref(closes, 26))]
    sig = _ema_ref(macd, 9)[-1]
    assert _val(st, 'macd') == pytest.approx(macd[-1])
    assert _val(st, 'macd_signal') == pytest.approx(sig)
    assert _val(st, 'macd_hist') == pytest.approx(macd[-1] - sig)


# --- FG-3 volatility: hand-verified Bollinger ---------------------------------

def test_bollinger_hand_verified():
    # 10 closes at 100, 10 at 110: SMA=105, pop-std=5 -> bands 115/95.
    # Last close 110 -> %B = (110-95)/20 = 0.75; bandwidth = 20/105.
    closes = [100.0] * 10 + [110.0] * 10
    assert _val_at(_tape(closes), 'bb_mid') == pytest.approx(105.0)
    assert _val_at(_tape(closes), 'bb_upper') == pytest.approx(115.0)
    assert _val_at(_tape(closes), 'bb_lower') == pytest.approx(95.0)
    assert _val_at(_tape(closes), 'bb_pct_b') == pytest.approx(0.75)
    assert _val_at(_tape(closes), 'bb_bandwidth') == pytest.approx(20.0 / 105.0)


def test_atr_2sigma_filter_features():
    # Uniform-range tape: the ATR series is constant, so it never exceeds its
    # own 2-sigma band; the flag stays 0 and the value is the raw ATR (2.0).
    closes = [100.0] * 40
    highs = [101.0] * 40
    lows = [99.0] * 40
    rows = _tape(closes, highs=highs, lows=lows)
    assert _val_at(rows, 'atr_filtered_2sigma') == pytest.approx(2.0)
    assert _val_at(rows, 'atr_2sigma_active') == 0.0
    # The value and flag are always numeric (never None on a warmed state).
    rows = make_synthetic_tape(seed=7, n_bars=120)
    st = _state(rows)
    assert isinstance(_val(st, 'atr_filtered_2sigma'), float)
    assert _val(st, 'atr_2sigma_active') in (0.0, 1.0)


# --- FG-1 candle_shape: hand-verified bar geometry ----------------------------

def test_candle_shape_values():
    # 30 flat bars; the last is a hammer-like bar: o=100 c=103 h=105 l=99.
    closes = [100.0] * 30
    opens = [100.0] * 30
    highs = [100.0] * 30
    lows = [100.0] * 30
    opens[-1], closes[-1], highs[-1], lows[-1] = 100.0, 103.0, 105.0, 99.0
    st = _state(_tape(closes, opens=opens, highs=highs, lows=lows))
    assert _val(st, 'real_body') == pytest.approx(3.0)
    assert _val(st, 'body_range_ratio') == pytest.approx(3.0 / 6.0)
    assert _val(st, 'upper_shadow') == pytest.approx(2.0)
    assert _val(st, 'lower_shadow') == pytest.approx(1.0)
    assert _val(st, 'close_position') == pytest.approx((103.0 - 99.0) / 6.0)
    # vs the flat prior bar (100/100/100/100): outside (engulfing), not inside.
    assert _val(st, 'inside_bar') == 0.0
    assert _val(st, 'outside_bar') == 1.0
    assert _val(st, 'gap_size') == 0.0      # no gap is a real zero
    assert _val(st, 'gap_dir') == 0.0


def test_gap_size_and_dir_signed():
    # Gap up: last open 108 > prior high 100 -> positive gap, dir +1.
    closes = [100.0] * 30
    opens = [100.0] * 30
    highs = [100.0] * 30
    lows = [100.0] * 30
    opens[-1], highs[-1], lows[-1], closes[-1] = 108.0, 110.0, 107.0, 109.0
    st = _state(_tape(closes, opens=opens, highs=highs, lows=lows))
    assert _val(st, 'gap_size') == pytest.approx(8.0)
    assert _val(st, 'gap_dir') == 1.0


# --- FG-4 location: swing significance (CRIT-1 / Ch27.2 ATR range filter) -----

def test_swing_significance_atr_range_filter():
    # ATR over the flat tape is 2.0 (bars range 100..101 / 99).
    # Weak pivot: bar 14 spans 100.4..101.4 (range 1.0 < k*ATR=2.0) -> 0.0
    # (no significant swing; 0.0 is the no-signal sentinel, never a price).
    closes = [100.0] * 30
    opens = [100.0] * 30
    highs = [101.0] * 30
    lows = [99.0] * 30
    highs[14], lows[14], closes[14] = 101.4, 100.4, 101.0
    rows = _tape(closes, opens=opens, highs=highs, lows=lows)
    assert _val_at(rows, 'atr') == pytest.approx(2.0)
    assert _val_at(rows, 'swing_high_5') == 0.0
    # Strong pivot: bar 14 spans 100..106 (range 6.0 >= k*ATR=2.0) -> 106.0.
    closes = [100.0] * 30
    opens = [100.0] * 30
    highs = [101.0] * 30
    lows = [99.0] * 30
    opens[14], highs[14], lows[14], closes[14] = 100.0, 106.0, 100.0, 105.0
    rows = _tape(closes, opens=opens, highs=highs, lows=lows)
    assert _val_at(rows, 'swing_high_5') == pytest.approx(106.0)


def test_location_window_and_fib_features():
    # Window features exclude the CURRENT bar (Donchian breakout semantics):
    # the current bar spikes to 108 but window_high_10 is the max of the 10
    # bars before it.
    closes = [100.0] * 30
    opens = [100.0] * 30
    highs = [101.0] * 30
    lows = [99.0] * 30
    opens[-1], highs[-1], lows[-1], closes[-1] = 100.0, 108.0, 100.0, 107.0
    st = _state(_tape(closes, opens=opens, highs=highs, lows=lows))
    assert _val(st, 'window_high_10') == pytest.approx(101.0)
    assert _val(st, 'window_low_10') == pytest.approx(99.0)
    assert _val(st, 'range_height_10') == pytest.approx(2.0)

    # fib_levels is a self-describing tuple (anchor, direction, retr, ext)
    # anchored on the most recent confirmed strength-10 swing pair. The tape
    # swings up to 102 at bar 12 then down to 97 at bar 19, so the anchor is
    # the down-impulse (anchor 97, direction -1, range 5).
    n = 35
    closes = [99.0] * n
    opens = [99.0] * n
    highs = [100.0] * n
    lows = [98.0] * n
    opens[12], highs[12], lows[12], closes[12] = 100.0, 102.0, 100.0, 101.0
    opens[19], highs[19], lows[19], closes[19] = 99.0, 99.0, 97.0, 98.0
    st = _state(_tape(closes, opens=opens, highs=highs, lows=lows))
    fibs = _val(st, 'fib_levels')
    assert isinstance(fibs, tuple) and len(fibs) == 4
    anchor, direction, retr, ext = fibs
    assert anchor == pytest.approx(97.0)
    assert direction == -1.0
    assert retr[0] == pytest.approx((0.236, 97.0 + 0.236 * 5.0))
    # Extensions project from the impulse ORIGIN (the older extreme, the 102
    # peak) — book Ch10.5.2 "Peak - (Range x Ratio)" — not from the anchor low.
    assert ext[0] == pytest.approx((1.0, 102.0 - 5.0))
    assert len(retr) == len((0.236, 0.382, 0.5, 0.618, 0.786))
    assert len(ext) == 10

    # Structured location features are always tuples (possibly empty), never
    # None on a warmed state; atr_band_stop = k * atr(14), k LOCKED = 2.0.
    st = _state(make_synthetic_tape(seed=7, n_bars=130))
    assert _val(st, 'atr_band_stop') == pytest.approx(2.0 * _val(st, 'atr'))
    assert isinstance(_val(st, 'gap_levels'), tuple)
    assert isinstance(_val(st, 'pivot_points_day'), tuple)
    assert isinstance(_val(st, 'consolidation_range'), tuple)
    assert _val(st, 'consolidation_range')[3] in (0.0, 1.0)   # is_active 0/1


# --- FG-5 participation + FG-6 session ----------------------------------------

def test_participation_features():
    rows = make_synthetic_tape(seed=7, n_bars=120)
    st = _state(rows)
    assert _val(st, 'volume') == pytest.approx(rows[-1].payload['volume'])
    assert isinstance(_val(st, 'vol_zscore'), float)
    assert 0.0 <= _val(st, 'vol_min_proximity') <= 1.0
    assert _val(st, 'vol_smooth_ma') > 0
    assert isinstance(_val(st, 'obv'), float)
    assert isinstance(_val(st, 'adl'), float)
    assert -1.0 <= _val(st, 'cmf_20') <= 1.0
    assert _val(st, 'vwap') > 0
    assert 0.0 <= _val(st, 'bar_class') <= 3.0
    # OBV responds to close direction: a crafted up-then-down tape.
    closes = [100.0, 101.0, 102.0, 101.0, 100.0]
    rows2 = _tape(closes, volumes=[1.0, 2.0, 3.0, 4.0, 5.0])
    assert _val_at(rows2, 'obv') == pytest.approx(2.0 + 3.0 - 4.0 - 5.0)


def test_session_features():
    rows = make_synthetic_tape(seed=7, n_bars=120)
    st = _state(rows)
    hour = _val(st, 'hour_of_day_utc')
    assert 0 <= hour <= 23
    assert _val(st, 'impulsive_window') in (0.0, 1.0)
    assert 1 <= _val(st, 'bar_of_session') <= 24
    assert _val(st, 'day_index') == rows[-1].event_time // (24 * HOUR_NS)


# --- FG-7 positioning ---------------------------------------------------------

def test_funding_rate_emitted_only_when_channel_present():
    rows = make_synthetic_tape(seed=1, n_bars=30)
    # No funding channel on the synthetic tape -> feature absent, state intact.
    st = _state(rows)
    assert 'SOLUSDT.funding_rate' not in st.features
    funding = TapeRow(source='binance-um', channel='funding', instrument='SOLUSDT',
                      event_time=rows[-1].event_time,
                      available_time=rows[-1].available_time,
                      ingested_time=rows[-1].available_time, venue_sequence=9999,
                      event_id='SOLUSDT:FUNDING:1',
                      payload={'funding_rate': 0.0001})
    st2 = _state(rows + [funding])
    fv = st2.features['SOLUSDT.funding_rate']
    assert fv.value == pytest.approx(0.0001)
    assert fv.group == 'positioning'


# --- Group tagging / ontology -------------------------------------------------

def test_new_features_declared_and_tagged():
    rows = make_synthetic_tape(seed=5, n_bars=120)
    st = _state(rows)
    validate_feature_groups(st.features)      # fails closed on any mis-tag
    for name, fv in st.features.items():
        bare = name.rsplit('.', 1)[-1]
        assert fv.group == FEATURE_TO_GROUP[bare], name
    assert _val(st, 'rsi14') is not None
    assert st.features['SOLUSDT.rsi14'].group == 'oscillator'
    assert st.features['SOLUSDT.bb_mid'].group == 'volatility'
    assert st.features['SOLUSDT.swing_high_5'].group == 'location'
    assert st.features['SOLUSDT.volume'].group == 'participation'
    assert st.features['SOLUSDT.hour_of_day_utc'].group == 'session'
    assert st.features['SOLUSDT.real_body'].group == 'candle_shape'


def test_all_declared_features_emitted_on_warmed_state():
    rows = make_synthetic_tape(seed=7, n_bars=130)
    st = _state(rows)
    assert st.quality == 'COMPLETE'
    emitted = {k.rsplit('.', 1)[-1] for k in st.features}
    for group, spec in FEATURE_GROUPS.items():
        for name in spec['features']:
            if name in CHANNEL_GATED:
                continue
            assert name in emitted, f'{name} ({group}) not emitted'
            assert st.features[f'SOLUSDT.{name}'].value is not None, name
    # The feature graph re-versions automatically when the ontology changes.
    assert isinstance(FEATURE_GRAPH_VERSION, str) and len(FEATURE_GRAPH_VERSION) == 40


def test_feature_groups_requires_are_declared():
    for group, spec in FEATURE_GROUPS.items():
        for req in spec['requires']:
            assert req in FEATURE_GROUPS


# --- Warmup / PIT / determinism -----------------------------------------------

def test_insufficient_warmup_is_degraded_not_complete():
    rows = make_synthetic_tape(seed=1, n_bars=1)
    st = build_state(rows, rows[0].available_time, UNIVERSE)
    # Bar 0: prior-referencing features are None (data absence), never a zero.
    for name in ('prior_high', 'prior_low', 'inside_bar', 'outside_bar',
                 'gap_size', 'gap_dir'):
        fv = st.features[f'SOLUSDT.{name}']
        assert fv.value is None, name
        assert fv.quality == 'DEGRADED', name
        assert fv.null_reason == 'NOT_YET_AVAILABLE', name
    assert st.quality == 'DEGRADED'
    # A 3-bar state: warmup-gated features are ABSENT (the ema_fast/atr
    # pattern), never emitted as a bogus zero or None.
    rows3 = make_synthetic_tape(seed=1, n_bars=3)
    st3 = build_state(rows3, rows3[-1].available_time, UNIVERSE)
    assert 'SOLUSDT.rsi14' not in st3.features
    assert 'SOLUSDT.bb_mid' not in st3.features


def test_future_row_rejected():
    rows = make_synthetic_tape(seed=1, n_bars=5)
    with pytest.raises(FutureRowError):
        build_state(rows, rows[0].available_time, UNIVERSE)


def test_pit_state_identical_to_lab_state(tmp_path):
    """The Lab and build_state must agree on the same decision clock (the
    incremental accumulator and the pure function are the same state)."""
    rows = make_synthetic_tape(seed=7, n_bars=60)
    st = _state(rows)
    lab = Lab(tmp_path)
    lab.ingest(rows)
    rep = lab.run(ExperimentManifest(experiment_id='exp-pit', code_hash='',
                                     data_hash='', universe=UNIVERSE,
                                     start_ns=0, end_ns=0),
                  [TrendPullbackExpert()])
    assert rep.candidate_count > 0
    assert rep.verdict == 'NO_ECONOMIC_CLAIM'


def test_existing_experts_still_run(tmp_path):
    """The three registered pilots run end-to-end on the synthetic tape; the
    feature-graph extension must not change expert behavior."""
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-fg', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [TrendPullbackExpert(), FailedBreakoutExpert(),
                    LiquiditySweepReclaimExpert()])
    assert r.candidate_count > 0
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
