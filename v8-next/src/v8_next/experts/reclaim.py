"""Sweep/reclaim and role-reversal observations; no execution authority."""

from dataclasses import replace

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, Stance
from v8_next.experts.common import context_reason, directional_stance
from v8_next.experts.features import significant_swings
from v8_next.experts.patterns import pattern_retest_direction


def observe_liquidity_reclaim(frame: CausalFrame, opportunity: Opportunity | None) -> Stance:
    reason = context_reason(frame, opportunity, 2)
    direction = None
    if reason is None:
        current, history = frame.candles[-1], frame.candles[:-1]
        low, high = min(c.low for c in history), max(c.high for c in history)
        if current.low < low and current.close > low:
            direction, reason = "LONG", "LOW_SWEEP_RECLAIM"
        elif current.high > high and current.close < high:
            direction, reason = "SHORT", "HIGH_SWEEP_RECLAIM"
        else:
            reason = "NO_SWEEP_RECLAIM"
    return directional_stance(
        frame,
        opportunity,
        family="liquidity-sweep-reclaim",
        dependency="ohlcv-sweep-v1",
        mechanism="liquidity-reclaim-hypothesis",
        direction=direction,
        reason=reason,
    )


def observe_breakout_retest(
    frame: CausalFrame, opportunity: Opportunity | None, *, variant: str = "a"
) -> Stance:
    """Variant a: retest a confirmed significant swing with a recent breach."""
    if variant not in {"a", "b", "c"}:
        raise ValueError("unsupported retest variant")
    reason = context_reason(frame, opportunity, 21)
    direction = None
    if reason is None and variant != "a":
        direction = pattern_retest_direction(frame, variant)
        reason = "PATTERN_RETEST" if direction else "NO_PATTERN_RETEST"
    if reason is None:
        high_index, low_index = significant_swings(frame)
        current = frame.candles[-1]
        recent = frame.candles[-7:-1]
        reason = "NO_RECENT_RETEST"
        if high_index is None and low_index is None:
            reason = "MISSING_CONFIRMED_SWING"
        if high_index is not None:
            high = frame.candles[high_index].high
            if current.low <= high < current.close and any(c.close > high for c in recent):
                direction, reason = "LONG", "ROLE_REVERSAL_RETEST"
        if direction is None and low_index is not None:
            low = frame.candles[low_index].low
            if current.high >= low > current.close and any(c.close < low for c in recent):
                direction, reason = "SHORT", "ROLE_REVERSAL_RETEST"
    stance = directional_stance(
        frame,
        opportunity,
        family="breakout-retest",
        dependency="ohlcv-swing-retest-v1",
        mechanism="role-reversal-hypothesis",
        direction=direction,
        reason=reason,
    )

    return replace(stance, variant_id=variant)
