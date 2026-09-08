"""Native-backed causal feature calculations, with explicit warmup and seeds."""

import math

import polars as pl

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import numeric


def close_series(frame: CausalFrame) -> pl.Series:
    if not frame.continuous:
        raise ValueError("source gap")
    values = [float(c.close) for c in frame.candles]
    if any(not math.isfinite(v) for v in values):
        raise ValueError("price outside finite float domain")
    return pl.Series("close", values, dtype=pl.Float64)


def wilder_rsi(closes: pl.Series, period: int = 14) -> tuple[float | None, ...]:
    """SMA seed over period deltas, then Wilder EMA through Polars.

    Flat seed maps to 50, gain-only to 100, loss-only to zero, matching the
    declared legacy RSI convention. No warmup zero or partial seed is emitted.
    """
    if period < 1:
        raise ValueError("positive RSI period required")
    if not closes.is_finite().all() or closes.null_count():
        raise ValueError("RSI requires finite closes")
    if len(closes) <= period:
        return (None,) * len(closes)
    deltas = closes.diff().slice(1)
    gains, losses = deltas.clip(lower_bound=0), (-deltas).clip(lower_bound=0)

    def smoothed(series: pl.Series) -> pl.Series:
        seed = numeric(series.head(period).mean())
        return pl.concat([pl.Series([seed]), series.slice(period)]).ewm_mean(
            alpha=1 / period, adjust=False
        )

    values = pl.DataFrame({"gain": smoothed(gains), "loss": smoothed(losses)}).select(
        pl.when(pl.col("loss") == 0)
        .then(pl.when(pl.col("gain") > 0).then(100.0).otherwise(50.0))
        .otherwise(100 - 100 / (1 + pl.col("gain") / pl.col("loss")))
        .alias("rsi")
    )["rsi"]
    return (None,) * period + tuple(float(v) for v in values)


def trend_emas(frame: CausalFrame) -> tuple[float, float]:
    closes = close_series(frame)
    if len(closes) < 20:
        raise ValueError("EMA warmup requires 20 bars")
    return (
        numeric(closes.ewm_mean(span=5, adjust=False)[-1]),
        numeric(closes.ewm_mean(span=20, adjust=False)[-1]),
    )


def significant_swings(frame: CausalFrame, strength: int = 10) -> tuple[int | None, int | None]:
    """Latest strict, confirmed pivots with bar range >= current mean range14.

    Indices refer to the supplied causal prefix. Right-hand confirmation uses
    only bars already inside that prefix. This preserves the legacy significance
    hypothesis (mean high-low range, not a silently substituted Wilder ATR).
    """
    if strength < 1:
        raise ValueError("positive pivot strength required")
    if not frame.continuous:
        raise ValueError("source gap")
    if len(frame.candles) < max(14, 2 * strength + 1):
        return None, None
    values = pl.DataFrame(
        {
            "high": [float(c.high) for c in frame.candles],
            "low": [float(c.low) for c in frame.candles],
        }
    )
    if not all(values[c].is_finite().all() for c in ("high", "low")):
        raise ValueError("price outside finite float domain")
    ranges = values["high"] - values["low"]
    threshold = numeric(ranges.tail(14).mean())
    if threshold <= 0:
        return None, None
    found: list[int | None] = []
    for name, high in (("high", True), ("low", False)):
        series = values[name]
        rolling = series.rolling_max(strength) if high else series.rolling_min(strength)
        left, right = rolling.shift(1), rolling.shift(-strength)
        mask = (
            ((series > left) & (series > right)) if high else ((series < left) & (series < right))
        )
        indices = (mask & (ranges >= threshold)).fill_null(False).arg_true()
        found.append(int(indices[-1]) if len(indices) else None)
    return found[0], found[1]
