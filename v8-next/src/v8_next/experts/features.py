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
