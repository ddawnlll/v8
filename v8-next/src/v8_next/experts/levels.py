"""Session pivot reaction and volume-qualified narrow-range breakout."""

from dataclasses import dataclass, replace
from decimal import Decimal

import polars as pl

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, Stance, numeric
from v8_next.experts.common import context_reason, directional_stance

HOUR_NS = 3600 * 10**9
DAY_NS = 24 * HOUR_NS


@dataclass(frozen=True)
class PivotLevels:
    session_start_ns: int
    pivot: Decimal
    resistance1: Decimal
    support1: Decimal


def daily_pivots(frame: CausalFrame) -> PivotLevels | None:
    """Previous complete UTC day's H/L/final close, fixed throughout the session."""
    if not frame.continuous:
        raise ValueError("source gap")
    if not frame.candles:
        return None
    session = frame.candles[-1].start_ns // DAY_NS * DAY_NS
    previous = tuple(
        c for c in frame.candles if session - DAY_NS <= c.start_ns and c.end_ns <= session
    )
    if (
        len(previous) != 24
        or previous[0].start_ns != session - DAY_NS
        or previous[-1].end_ns != session
        or any(c.end_ns - c.start_ns != HOUR_NS for c in previous)
    ):
        return None
    high, low = max(c.high for c in previous), min(c.low for c in previous)
    pivot = (high + low + previous[-1].close) / 3
    return PivotLevels(session, pivot, 2 * pivot - low, 2 * pivot - high)


def observe_floor_pivot(frame: CausalFrame, opportunity: Opportunity | None) -> Stance:
    reason = context_reason(frame, opportunity, 25)
    direction = None
    if reason is None:
        levels = daily_pivots(frame)
        reason = "MISSING_COMPLETE_PREVIOUS_DAY"
        if levels is not None:
            current = frame.candles[-1]
            if levels.pivot < current.open < current.close < levels.resistance1:
                direction, reason = "LONG", "PIVOT_DRIFT"
            elif levels.support1 < current.close < current.open < levels.pivot:
                direction, reason = "SHORT", "PIVOT_DRIFT"
            else:
                reason = "NO_POSITIVE_PIVOT_TARGET"
    stance = directional_stance(
        frame,
        opportunity,
        family="floor-trader-pivot",
        dependency="ohlcv-utc-day-pivot-v2",
        mechanism="session-pivot-drift-hypothesis",
        direction=direction,
        reason=reason,
    )
    return replace(stance, version="floor-trader-pivot-utc-session-v2")


def observe_range_breakout(frame: CausalFrame, opportunity: Opportunity | None) -> Stance:
    reason = context_reason(frame, opportunity, 100)
    direction = None
    if reason is None:
        current, prior = frame.candles[-1], frame.candles[-21:-1]
        high, low = max(c.high for c in prior), min(c.low for c in prior)
        volumes = pl.Series([float(c.volume) for c in frame.candles[-100:]])
        if not volumes.is_finite().all():
            raise ValueError("volume outside finite float domain")
        sd = numeric(volumes.std(ddof=0))
        reason = "NO_NARROW_RANGE"
        if high > low and (high - low) / current.close <= Decimal("0.03"):
            if sd <= 0:
                reason = "MISSING_VOLUME_DISPERSION"
            elif (numeric(volumes[-1]) - numeric(volumes.mean())) / sd < 0.20:
                reason = "NO_VOLUME_EXPANSION"
            else:
                side = "LONG" if current.close > high else "SHORT" if current.close < low else None
                preceding = frame.candles[-22:-2]
                previous = frame.candles[-2]
                prior_broke = (
                    previous.close > max(c.high for c in preceding)
                    if side == "LONG"
                    else previous.close < min(c.low for c in preceding)
                )
                if side and not prior_broke:
                    direction, reason = side, "FRESH_NARROW_RANGE_BREAKOUT"
                else:
                    reason = "NO_FRESH_BREAKOUT"
    return directional_stance(
        frame,
        opportunity,
        family="range-breakout-1to1",
        dependency="ohlcv-volume-channel-v1",
        mechanism="range-measuring-objective-hypothesis",
        direction=direction,
        reason=reason,
    )
