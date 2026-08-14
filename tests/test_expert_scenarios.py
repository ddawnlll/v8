"""Per-Expert scenario correctness audit (rule 10: contract tests, not
economics). Hand-crafted bar sequences with a known correct fire/no-fire/
geometry outcome for each of the three pilot Experts, plus a cross-Expert
metamorphic invariant over synthetic noise. No Lab/CandidateRegistry
involved — `expert.evaluate(state)` is inspected directly, the same pattern
`tests/test_vertical_slice.py` already established (`_draft_at`).
"""
from __future__ import annotations

import pytest

from v8.schema import TapeRow, MarketState, FeatureValue, ExpertEvaluation
from v8.marketstate import build_state
from v8.experts import (TrendPullbackExpert, FailedBreakoutExpert,
                        LiquiditySweepReclaimExpert)
from v8.synth import make_synthetic_tape, HOUR_NS

UNIVERSE = ('SOLUSDT',)
SYM = 'SOLUSDT'


def _tape(bars: list[tuple[float, float, float, float]], symbol: str = SYM) -> list[TapeRow]:
    """bars: list of (open, high, low, close). One closed kline per hour."""
    rows: list[TapeRow] = []
    for i, (o, h, l, c) in enumerate(bars):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument=symbol,
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'{symbol}:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': 1.0, 'closed': True}))
    return rows


def _flat(c: float) -> tuple[float, float, float, float]:
    return (c, c + 0.5, c - 0.5, c)


def _state_at(rows: list[TapeRow], bar_idx: int) -> MarketState:
    as_of = rows[bar_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of], as_of, UNIVERSE)


def _eval_at(rows: list[TapeRow], expert, bar_idx: int) -> ExpertEvaluation:
    return expert.evaluate(_state_at(rows, bar_idx))


def _draft_at(rows: list[TapeRow], expert, bar_idx: int):
    ev = _eval_at(rows, expert, bar_idx)
    assert ev.draft is not None, f'no draft at bar {bar_idx} ({ev.decision})'
    return ev.draft


def _fv(name: str, value, group: str = '') -> FeatureValue:
    return FeatureValue(f'{SYM}.{name}', value, 'float', 'v1', 0, group=group)


def _hand_state(**feature_values) -> MarketState:
    """A MarketState built directly from named feature values (bypassing
    build_state entirely), for boundary cases where hand-deriving the exact
    EMA/ATR path to land a real tape on an equality is impractical."""
    features = {f'{SYM}.{k}': (_fv(k, v) if not isinstance(v, FeatureValue) else v)
                for k, v in feature_values.items()}
    return MarketState(state_id='hand-built', as_of=0, universe=UNIVERSE,
                       features=features, lineage_hash='hand-built')


# =====================================================================
# trend_pullback: ema_fast > ema_slow (strict) and close < ema_slow (strict)
# =====================================================================

def _trend_tape() -> list[TapeRow]:
    """40 flat bars (EMA convergence) + 20 bars rising 101..120 (clean
    uptrend, no pullback) + a shallow dip 108,107 (pullback run, pinned:
    ema_fast crosses below ema_slow at bar 62/close 106)."""
    closes = [100.0] * 40
    closes += [100.0 + (i + 1) for i in range(20)]
    closes += [108.0, 107.0]
    closes += [106.0, 115.0, 120.0, 124.0, 126.0]
    return _tape([(c, c * 1.002, c * 0.998, c) for c in closes])


def test_trend_pullback_fires_on_pullback_in_uptrend():
    """Canonical setup: uptrend with a pullback below the slow EMA."""
    rows = _trend_tape()
    draft = _draft_at(rows, TrendPullbackExpert(), 60)   # close 108, dip bar 1
    assert draft.direction == 'LONG'
    assert draft.setup_anchor_event_id == 'SOLUSDT:61'
    geo = draft.risk_geometry
    assert geo['entry'] == 'NEXT_BAR_CLOSE'
    assert geo['target_r'] == pytest.approx(1.0)
    assert geo['stop_r'] == pytest.approx(1.0)
    assert geo['expiry_bars'] == 8
    assert geo['atr_ref'] > 0
    assert set(geo) == {'entry', 'target_r', 'stop_r', 'expiry_bars', 'atr_ref'}


def test_trend_pullback_no_setup_during_clean_uptrend():
    """No pullback yet: for a monotonically rising close series, ema_slow(t)
    < close(t) always (EMA of an increasing sequence trails below it by
    induction), so the setup must never fire during the pure rise."""
    rows = _trend_tape()
    ev = _eval_at(rows, TrendPullbackExpert(), 55)   # deep in the 101..120 rise
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_trend_pullback_no_setup_during_downtrend():
    """A monotonically falling close series never satisfies ema_fast >
    ema_slow (the mirror of the rising case), so no pullback setup can ever
    be detected regardless of price level."""
    closes = [100.0] * 40 + [100.0 - (i + 1) for i in range(40)]
    rows = _tape([(c, c + 0.3, c - 0.3, c) for c in closes])
    ev = _eval_at(rows, TrendPullbackExpert(), 70)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_trend_pullback_boundary_close_equals_slow_ema_does_not_fire():
    """The gate is strict (`close < ema_slow`, never `<=`): a bar closing
    EXACTLY on the slow EMA must not fire."""
    st = _hand_state(close=100.0, ema_fast=105.0, ema_slow=100.0, atr=2.0,
                     history=((('SOLUSDT:1', 100.0, 100.0, 100.0, 100.0,
                                100.0, 100.0),)))
    ev = TrendPullbackExpert().evaluate(st)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_trend_pullback_thesis_dies_when_uptrend_dies():
    """still_valid tracks `ema_fast > ema_slow` on the FROZEN thesis: alive
    one bar into the pullback, dead the bar the uptrend itself dies (bar 62,
    close 106 — pinned fact, matches the crafted tape's EMA crossover)."""
    ex = TrendPullbackExpert()
    rows = _trend_tape()
    draft = _draft_at(rows, ex, 60)
    alive = _state_at(rows, 61)
    dead = _state_at(rows, 62)
    assert ex.still_valid(alive, draft) is True
    assert ex.still_valid(dead, draft) is False


# =====================================================================
# failed_breakout: a bar that closed above the prior window high (the
# breakout leg), later closed back below that SAME frozen level (the
# failure leg). Always SHORT.
# =====================================================================

def _failed_breakout_tape(tail: list[float]) -> list[TapeRow]:
    """30 bars rising 100..129 (every bar is its own momentary "breakout" —
    close exceeds the prior window high by construction, so the gate never
    fires mid-rise) followed by `tail` closes (quiet/rally continuation)."""
    closes = [100.0 + i for i in range(30)]
    closes += tail
    return _tape([(c, c + 0.5, c - 0.5, c) for c in closes])


def test_failed_breakout_fires_on_failed_breakout():
    """Bar 30 drops to 100, closing back below the frozen breakout level
    (bar 29's close 129 broke bar 28's prior high 128.5 -> level 128.5)."""
    rows = _failed_breakout_tape([100.0] * 16)
    draft = _draft_at(rows, FailedBreakoutExpert(), 30)
    assert draft.direction == 'SHORT'
    assert draft.risk_geometry['prior_high_ref'] == pytest.approx(128.5)
    assert draft.setup_anchor_event_id == 'SOLUSDT:31'
    geo = draft.risk_geometry
    assert geo['entry'] == 'NEXT_BAR_CLOSE'
    assert geo['target_r'] == pytest.approx(1.0)
    # Issue #63: the stop IS the frozen breakout level (structural stop); the
    # old fixed 1.0R ATR-multiple stop is gone.
    assert geo['stop_ref'] == pytest.approx(128.5)
    close = rows[-1].payload['close']
    atr = _state_at(rows, 30).features['SOLUSDT.atr'].value
    assert geo['stop_r'] == pytest.approx((128.5 - close) / atr)
    assert geo['expiry_bars'] == 8
    assert geo['atr_ref'] > 0


def test_failed_breakout_no_setup_during_clean_breakout_holding():
    """Mid-rise: the newest bar's close exceeds the SAME window high it is
    compared against (that is why it registers as a breakout at all), so
    `close < ref` can never hold while the breakout is still standing."""
    rows = _failed_breakout_tape([])
    ev = _eval_at(rows, FailedBreakoutExpert(), 25)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_failed_breakout_no_setup_during_plain_downtrend():
    """A close that never exceeds an earlier prior-high has no breakout leg
    at all (`_last_breakout` finds none) -> no failure is possible."""
    closes = [100.0 - i for i in range(40)]
    rows = _tape([(c, c + 0.3, c - 0.3, c) for c in closes])
    ev = _eval_at(rows, FailedBreakoutExpert(), 30)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_failed_breakout_boundary_close_equals_prior_high_ref_does_not_fire():
    """The failure leg is strict (`close < level`, never `<=`): a close
    exactly reclaiming the frozen breakout level must not fire."""
    hist = ((('SOLUSDT:1', 100.0, 100.0, 100.0, 100.0, 100.0, 100.0),
             ('SOLUSDT:2', 100.0, 110.0, 100.0, 110.0, 100.0, 100.0),   # breakout, level 100.0
             ('SOLUSDT:3', 110.0, 110.0, 100.0, 100.0, 100.0, 100.0)))  # close == level
    st = _hand_state(close=100.0, atr=1.0, history=hist)
    ev = FailedBreakoutExpert().evaluate(st)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_failed_breakout_still_valid_tracks_frozen_level():
    """Alive while quiet below the frozen level; dies the bar price reclaims
    back above it (not the live, ever-drifting prior_high — the frozen
    setup-time reference)."""
    ex = FailedBreakoutExpert()
    quiet = _failed_breakout_tape([100.0, 100.0, 100.0])
    draft = _draft_at(quiet, ex, 30)
    assert ex.still_valid(_state_at(quiet, 32), draft) is True
    reclaim = _failed_breakout_tape([100.0, 130.0])
    assert ex.still_valid(_state_at(reclaim, 31), draft) is False


# =====================================================================
# liquidity_sweep_reclaim: a wick through a windowed prior extreme that
# reclaims it by the close. LONG on a swept low, SHORT on a swept high.
# =====================================================================

def _rising_sweep_tape() -> list[TapeRow]:
    """25 bars rising 100..124 (prior_low pinned 99.5), then one bar that
    sweeps below it (low 99.0) and reclaims by the close (100.5) -> LONG."""
    closes = [100.0 + i for i in range(25)]
    rows = _tape([(c, c + 0.5, c - 0.5, c) for c in closes])
    rows.append(TapeRow(
        source='binance-um', channel='kline', instrument=SYM,
        event_time=HOUR_NS * 25, available_time=HOUR_NS * 25,
        ingested_time=HOUR_NS * 25, venue_sequence=26, event_id='SOLUSDT:26',
        payload={'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.5,
                 'volume': 1.0, 'closed': True}))
    return rows


def _flat_range_tape(final_bar: tuple[float, float, float, float]) -> list[TapeRow]:
    """25 flat bars (range 99.5..100.5, prior_high pinned 100.5, prior_low
    pinned 99.5) then one caller-supplied bar."""
    rows = _tape([_flat(100.0) for _ in range(25)])
    o, h, l, c = final_bar
    rows.append(TapeRow(
        source='binance-um', channel='kline', instrument=SYM,
        event_time=HOUR_NS * 25, available_time=HOUR_NS * 25,
        ingested_time=HOUR_NS * 25, venue_sequence=26, event_id='SOLUSDT:26',
        payload={'open': o, 'high': h, 'low': l, 'close': c,
                 'volume': 1.0, 'closed': True}))
    return rows


def test_liquidity_sweep_reclaim_fires_long_on_low_sweep():
    rows = _rising_sweep_tape()
    draft = _draft_at(rows, LiquiditySweepReclaimExpert(), 25)
    assert draft.direction == 'LONG'
    assert draft.risk_geometry['prior_low_ref'] == pytest.approx(99.5)
    assert 'prior_high_ref' not in draft.risk_geometry


def test_liquidity_sweep_reclaim_fires_short_on_high_sweep():
    """Mirror of the LONG case: a wick above the prior high that closes
    back below it."""
    rows = _flat_range_tape((100.0, 101.5, 99.8, 99.8))
    draft = _draft_at(rows, LiquiditySweepReclaimExpert(), 25)
    assert draft.direction == 'SHORT'
    assert draft.risk_geometry['prior_high_ref'] == pytest.approx(100.5)
    assert 'prior_low_ref' not in draft.risk_geometry


def test_liquidity_sweep_reclaim_no_setup_without_sweep():
    rows = _flat_range_tape((100.0, 100.3, 99.7, 100.0))   # stays inside the range
    ev = _eval_at(rows, LiquiditySweepReclaimExpert(), 25)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_liquidity_sweep_reclaim_boundary_touch_without_breach_does_not_fire():
    """Both gates are strict (`<`/`>`, never `<=`/`>=`): a low that exactly
    TOUCHES the prior low (not below it) is not a sweep, on either side."""
    hist = ((('SOLUSDT:1', 100.0, 100.0, 99.0, 99.5, 100.0, 100.0),
             ('SOLUSDT:2', 99.5, 100.0, 99.0, 100.2, 100.0, 100.0)))
    st = _hand_state(close=100.2, atr=1.0, history=hist)
    ev = LiquiditySweepReclaimExpert().evaluate(st)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_liquidity_sweep_reclaim_still_valid_long():
    ex = LiquiditySweepReclaimExpert()
    rows = _rising_sweep_tape()
    draft = _draft_at(rows, ex, 25)
    assert ex.still_valid(_state_at(rows, 25), draft) is True   # close 100.5 > 99.5
    drop = list(rows)
    drop.append(TapeRow(
        source='binance-um', channel='kline', instrument=SYM,
        event_time=HOUR_NS * 26, available_time=HOUR_NS * 26,
        ingested_time=HOUR_NS * 26, venue_sequence=27, event_id='SOLUSDT:27',
        payload={'open': 100.0, 'high': 100.5, 'low': 98.0, 'close': 98.5,
                 'volume': 1.0, 'closed': True}))
    assert ex.still_valid(_state_at(drop, 26), draft) is False


def test_liquidity_sweep_reclaim_still_valid_short():
    ex = LiquiditySweepReclaimExpert()
    rows = _flat_range_tape((100.0, 101.5, 99.8, 99.8))
    draft = _draft_at(rows, ex, 25)
    assert ex.still_valid(_state_at(rows, 25), draft) is True   # close 99.8 < 100.5
    rally = list(rows)
    rally.append(TapeRow(
        source='binance-um', channel='kline', instrument=SYM,
        event_time=HOUR_NS * 26, available_time=HOUR_NS * 26,
        ingested_time=HOUR_NS * 26, venue_sequence=27, event_id='SOLUSDT:27',
        payload={'open': 100.0, 'high': 101.5, 'low': 99.5, 'close': 101.0,
                 'volume': 1.0, 'closed': True}))
    assert ex.still_valid(_state_at(rally, 26), draft) is False


# =====================================================================
# Shared habitat gate (all three pilots require the same 20-closed-bar
# warmup for `atr`, transitively required by all three via `_need`).
# =====================================================================

def test_all_pilots_no_habitat_below_warmup():
    rows = _tape([_flat(100.0) for _ in range(10)])
    for ex in (TrendPullbackExpert(), FailedBreakoutExpert(), LiquiditySweepReclaimExpert()):
        ev = _eval_at(rows, ex, 9)
        assert ev.decision == 'NO_HABITAT', ex.expert_id
        assert ev.draft is None


# =====================================================================
# Cross-Expert metamorphic invariant: whenever an Expert fires, an
# independent re-derivation of its documented predicate (from the raw
# `history` tuple, not the Expert's own private methods) must also hold.
# =====================================================================

def _ref_trend_fires(hist) -> bool:
    _e, _o, _h, _l, close, fast, slow = hist[-1]
    return fast > slow and close < slow


def _ref_failed_breakout_fires(hist) -> bool:
    for j in range(len(hist) - 1, 0, -1):
        prior = max(h for (_e, _o, h, _l, _c, _f, _s) in hist[:j])
        if hist[j][4] > prior:
            return hist[-1][4] < prior
    return False


def _ref_sweep_direction(hist) -> str | None:
    if len(hist) < 2:
        return None
    prior_low = min(l for (_e, _o, _h, l, _c, _f, _s) in hist[:-1])
    prior_high = max(h for (_e, _o, h, _l, _c, _f, _s) in hist[:-1])
    _e, _o, high, low, close, _f, _s = hist[-1]
    if low < prior_low and close > prior_low:
        return 'LONG'
    if high > prior_high and close < prior_high:
        return 'SHORT'
    return None


def test_no_spurious_fire_cross_expert_invariant():
    """Metamorphic check over synthetic noise: every CANDIDATE any pilot
    emits must be reproducible from an independent re-derivation of its
    documented setup predicate against the raw `history` tuple, and every
    draft's geometry must be well-formed. Seed 7 is included because it is
    the pinned seed `test_vertical_slice_runs_deterministically` already
    proves fires at least one candidate, so the check is not vacuous."""
    experts = (TrendPullbackExpert(), FailedBreakoutExpert(), LiquiditySweepReclaimExpert())
    checked = 0
    for seed in (2, 3, 5, 7):
        rows = make_synthetic_tape(seed=seed, n_bars=150)
        for idx in range(25, len(rows)):
            st = _state_at(rows, idx)
            hist_fv = st.features.get(f'{SYM}.history')
            if hist_fv is None or not hist_fv.value:
                continue
            hist = tuple(hist_fv.value)
            for ex in experts:
                ev = ex.evaluate(st)
                if ev.decision != 'CANDIDATE':
                    continue
                checked += 1
                geo = ev.draft.risk_geometry
                assert geo['entry'] == 'NEXT_BAR_CLOSE'
                assert geo['target_r'] > 0 and geo['stop_r'] > 0
                assert geo['expiry_bars'] > 0
                assert geo['atr_ref'] > 0
                if ex.expert_id == 'trend_pullback':
                    assert ev.draft.direction == 'LONG'
                    assert _ref_trend_fires(hist), 'fired without its own predicate holding'
                elif ex.expert_id == 'failed_breakout':
                    assert ev.draft.direction == 'SHORT'
                    assert 'prior_high_ref' in geo
                    assert _ref_failed_breakout_fires(hist), \
                        'fired without its own predicate holding'
                else:
                    ref_dir = _ref_sweep_direction(hist)
                    assert ref_dir == ev.draft.direction, \
                        'fired direction disagrees with an independent re-derivation'
                    ref_key = 'prior_low_ref' if ref_dir == 'LONG' else 'prior_high_ref'
                    assert ref_key in geo
    assert checked > 0, 'no CANDIDATE fired across any seed — invariant is vacuous'
