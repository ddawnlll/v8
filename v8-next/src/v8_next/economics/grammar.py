"""Expert-independent, versioned market episode hypotheses from legacy G0–G3."""

import hashlib
import json
from decimal import Decimal

import polars as pl

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, linear_exposure_id, numeric, opportunity_at
from v8_next.experts.features import close_series

POLICIES = frozenset(
    {
        "range-breakout-48-v1",
        "volatility-extreme-v2",
        "trend-continuation-v2",
        "mean-reversion-v2",
        "compression-expansion-v2",
    }
)


def grammar_opportunity(frame: CausalFrame, policy: str) -> Opportunity | None:
    if policy not in POLICIES:
        raise ValueError("unknown opportunity grammar")
    if policy == "range-breakout-48-v1":
        return opportunity_at(frame)
    bars = frame.candles
    exposure = linear_exposure_id(frame.instrument_id)
    if exposure is None or not frame.continuous:
        return None
    warmup = (
        62
        if policy == "compression-expansion-v2"
        else (25 if policy == "trend-continuation-v2" else 21)
    )
    if len(bars) < warmup:
        return None
    closes = close_series(frame)
    close, previous = bars[-1].close, bars[-2].close
    direction = None
    status = "CANONICAL"
    horizon = 24
    if policy == "volatility-extreme-v2":
        mean, std = numeric(closes.tail(20).mean()), numeric(closes.tail(20).std(ddof=0))
        if std <= 0:
            return None
        z = (float(close) - mean) / std
        horizon = 48
        if abs(z) >= 1.8:
            direction = "LONG" if z > 0 else "SHORT"
            status = "AMBIGUOUS" if abs(z) - 1.8 < 0.3 else "CANONICAL"
        elif abs(z) < 0.3:
            direction, status, horizon = "NEUTRAL", "UNKNOWN", 4
    elif policy == "trend-continuation-v2":
        fast, slow = numeric(closes.tail(8).mean()), numeric(closes.tail(24).mean())
        if fast > slow and close > previous and float(close) > fast:
            direction = "LONG"
        elif fast < slow and close < previous and float(close) < fast:
            direction = "SHORT"
    elif policy == "mean-reversion-v2":
        mean_price = sum((c.close for c in bars[-20:]), Decimal(0)) / 20
        span = sum((c.high - c.low for c in bars[-14:]), Decimal(0)) / 14
        if span <= 0:
            return None
        horizon = 12
        if close >= mean_price + Decimal("2.2") * span and close < previous:
            direction = "SHORT"
        elif close <= mean_price - Decimal("2.2") * span and close > previous:
            direction = "LONG"
    else:
        ranges = pl.Series([float(c.high - c.low) for c in bars]).rolling_mean(14).tail(49)
        current, low, high = numeric(ranges[-1]), numeric(ranges.min()), numeric(ranges.max())
        if high <= low or current <= 0:
            return None
        change = (close - previous) / previous
        if (current - low) / (high - low) < 0.25 and abs(change) > Decimal(".008"):
            direction = "LONG" if change > 0 else "SHORT"
    if direction is None:
        return None
    duration = bars[-1].end_ns - bars[-1].start_ns
    if any(c.end_ns - c.start_ns != duration for c in bars):
        raise ValueError("grammar requires regular bar durations")
    anchor = bars[-1].end_ns
    identity = json.dumps(
        [policy, exposure, frame.instrument_id, direction, anchor, duration], separators=(",", ":")
    )
    return Opportunity(
        hashlib.sha256(identity.encode()).hexdigest(),
        exposure,
        frame.instrument_id,
        direction,
        anchor,
        anchor + horizon * duration,
        policy,
        status,
    )
