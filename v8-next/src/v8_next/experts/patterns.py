"""Confirmed structural pattern levels for retest variants b/c.

These are observation hypotheses, not calibrated economic forecasts.
"""

from decimal import Decimal

import polars as pl

from v8_next.domain.market import CausalFrame


def pattern_pivots(frame: CausalFrame, *, high: bool, strength: int = 3) -> tuple[int, ...]:
    if strength < 1:
        raise ValueError("positive pivot strength required")
    if not frame.continuous:
        raise ValueError("source gap")
    values = pl.Series([float(c.high if high else c.low) for c in frame.candles])
    if not values.is_finite().all():
        raise ValueError("price outside finite float domain")
    roll = values.rolling_max(strength) if high else values.rolling_min(strength)
    left, right = roll.shift(1), roll.shift(-strength)
    mask = (values > left) & (values > right) if high else (values < left) & (values < right)
    return tuple(int(i) for i in mask.fill_null(False).arg_true())


def retests(frame: CausalFrame, direction: str, level: Decimal) -> bool:
    current, recent = frame.candles[-1], frame.candles[-7:-1]
    if direction == "LONG":
        return current.low <= level < current.close and any(c.close > level for c in recent)
    return current.high >= level > current.close and any(c.close < level for c in recent)


def pattern_retest_direction(frame: CausalFrame, variant: str) -> str | None:
    if variant not in {"b", "c"}:
        raise ValueError("unsupported pattern retest variant")
    bars = frame.candles
    highs, lows = pattern_pivots(frame, high=True), pattern_pivots(frame, high=False)
    # Top before bottom matches the legacy pattern variants' precedence.
    for side, peaks, troughs in (("SHORT", highs, lows), ("LONG", lows, highs)):
        top = side == "SHORT"

        def price(i: int, top: bool = top) -> Decimal:
            return bars[i].high if top else bars[i].low

        if variant == "b":
            if len(peaks) < 2:
                continue
            left, right = peaks[-2:]
            between = bars[left + 1 : right]
            if not between:
                continue
            level = min(c.low for c in between) if top else max(c.high for c in between)
            valid = all(price(i) > level if top else price(i) < level for i in (left, right))
        else:
            if len(peaks) < 3 or len(troughs) < 2:
                continue
            select = max if top else min
            head = select(peaks, key=price)
            lefts, rights = [i for i in peaks if i < head], [i for i in peaks if i > head]
            if not lefts or not rights:
                continue
            left, right = select(lefts, key=price), select(rights, key=price)
            if not all(
                price(i) < price(head) if top else price(i) > price(head) for i in (left, right)
            ):
                continue
            left_levels = [bars[i].low if top else bars[i].high for i in troughs if left < i < head]
            right_levels = [
                bars[i].low if top else bars[i].high for i in troughs if head < i < right
            ]
            if not left_levels or not right_levels:
                continue
            level = (
                max(max(left_levels), max(right_levels))
                if top
                else min(min(left_levels), min(right_levels))
            )
            valid = level < price(head) if top else level > price(head)
        breached = any(c.close < level if top else c.close > level for c in bars[right:-1])
        if valid and breached and retests(frame, side, level):
            return side
    return None
