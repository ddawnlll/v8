"""Native-backed causal feature calculations, with explicit warmup and seeds."""

import math

import polars as pl

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import numeric


def close_series(frame: CausalFrame) -> pl.Series:
    if not frame.continuous:
        raise ValueError("source gap")
    s = frame.df["close"]
    if not s.is_finite().all():
        raise ValueError("price outside finite float domain")
    return s


def high_series(frame: CausalFrame) -> pl.Series:
    if not frame.continuous:
        raise ValueError("source gap")
    s = frame.df["high"]
    if not s.is_finite().all():
        raise ValueError("price outside finite float domain")
    return s


def low_series(frame: CausalFrame) -> pl.Series:
    if not frame.continuous:
        raise ValueError("source gap")
    s = frame.df["low"]
    if not s.is_finite().all():
        raise ValueError("price outside finite float domain")
    return s


def volume_series(frame: CausalFrame) -> pl.Series:
    if not frame.continuous:
        raise ValueError("source gap")
    s = frame.df["volume"]
    if not s.is_finite().all():
        raise ValueError("volume outside finite float domain")
    return s


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
    if len(frame.candles) < 20:
        raise ValueError("EMA warmup requires 20 bars")
    indicators = frame.indicator_df
    return (
        numeric(indicators["ema_5"][-1]),
        numeric(indicators["ema_20"][-1]),
    )


def significant_swings(frame: CausalFrame, strength: int = 10) -> tuple[int | None, int | None]:
    """Latest strict, confirmed pivots with bar range >= current mean range14.

    Indices refer to the supplied causal prefix. Right-hand confirmation uses
    only bars already inside that prefix. This preserves the legacy significance
    hypothesis (mean high-low range, not a silently substituted Wilder ATR).
    """
    if strength < 1:
        raise ValueError("positive pivot strength required")
    cache_key = ("significant_swings", strength)
    cached = frame.memo_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    result: tuple[int | None, int | None]
    if not frame.continuous:
        raise ValueError("source gap")
    if len(frame.candles) < max(14, 2 * strength + 1):
        result = (None, None)
        frame.memo_set(cache_key, result)
        return result
    values = frame.df.select(["high", "low"])
    if not values["high"].is_finite().all() or not values["low"].is_finite().all():
        raise ValueError("price outside finite float domain")
    ranges = values["high"] - values["low"]
    threshold = numeric(ranges.tail(14).mean())
    if threshold <= 0:
        result = (None, None)
        frame.memo_set(cache_key, result)
        return result
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
    result = (found[0], found[1])
    frame.memo_set(cache_key, result)
    return result


def macd_line(frame: CausalFrame) -> float:
    """Source 34-bar availability; first-close EMA12 minus EMA26."""
    if len(frame.candles) < 34:
        raise ValueError("MACD requires 34 bars")
    return numeric(frame.indicator_df["macd_line"][-1])


def _ohlc_columns(
    highs: list[float], lows: list[float], closes: list[float], period: int
) -> pl.DataFrame:
    if type(period) is not int or period < 1:
        raise ValueError("positive integer indicator period required")
    if len(highs) != len(lows) or len(highs) != len(closes):
        raise ValueError("aligned indicator inputs required")
    if any(not math.isfinite(v) for column in (highs, lows, closes) for v in column):
        raise ValueError("non-finite indicator input")
    if any(not 0 < lo <= close <= hi for hi, lo, close in zip(highs, lows, closes, strict=True)):
        raise ValueError("invalid indicator price range")
    return pl.DataFrame(
        {"high": highs, "low": lows, "close": closes},
        schema={"high": pl.Float64, "low": pl.Float64, "close": pl.Float64},
    )


def _wilder(values: pl.Series, period: int) -> pl.Series:
    seed = numeric(values.head(period).mean())
    return pl.concat([pl.Series([seed]), values.slice(period)]).ewm_mean(
        alpha=1 / period, adjust=False
    )


def adx_series(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    """Wilder DMI: SMA seed, first ADX at index 2*period-1; absent warmup.

    Polars owns vector arithmetic and smoothing. Supplied history origin is part
    of the experiment: truncating that origin changes recursive indicators.
    """
    data = _ohlc_columns(highs, lows, closes, period)
    if len(closes) < 2 * period:
        return [None] * len(closes)
    data = data.with_columns(
        pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - pl.col("close").shift()).abs(),
            (pl.col("low") - pl.col("close").shift()).abs(),
        ).alias("tr"),
        pl.col("high").diff().alias("up"),
        (-pl.col("low").diff()).alias("down"),
    ).slice(1)
    data = data.with_columns(
        pl.when((pl.col("up") > pl.col("down")) & (pl.col("up") > 0))
        .then(pl.col("up"))
        .otherwise(0.0)
        .alias("plus"),
        pl.when((pl.col("down") > pl.col("up")) & (pl.col("down") > 0))
        .then(pl.col("down"))
        .otherwise(0.0)
        .alias("minus"),
    )
    smooth = pl.DataFrame({key: _wilder(data[key], period) for key in ("tr", "plus", "minus")})
    dx = smooth.select(
        pl.when((pl.col("tr") > 0) & ((pl.col("plus") + pl.col("minus")) > 0))
        .then(100 * (pl.col("plus") - pl.col("minus")).abs() / (pl.col("plus") + pl.col("minus")))
        .otherwise(0.0)
        .alias("dx")
    )["dx"]
    return [None] * (2 * period - 1) + [numeric(v) for v in _wilder(dx, period)]


def simple_atr_series(highs: list[float], lows: list[float], period: int = 14) -> list[float]:
    """Legacy range14, NOT gap-aware ATR; complete rolling high-low means."""
    data = _ohlc_columns(highs, lows, lows, period)
    if len(highs) < period:
        return []
    result = data.select((pl.col("high") - pl.col("low")).rolling_mean(period).alias("range"))[
        "range"
    ]
    return [numeric(v) for v in result.slice(period - 1)]


def bollinger_bands(
    closes: pl.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pl.Series, pl.Series, pl.Series, pl.Series, pl.Series]:
    """Calculate (mid, sd, upper, lower, bandwidth) using Polars rolling kernels.

    sd uses population standard deviation (ddof=0) matching V8 convention.
    """
    mid = closes.rolling_mean(period)
    sd = closes.rolling_std(period, ddof=0)
    upper = mid + num_std * sd
    lower = mid - num_std * sd
    bandwidth = (2 * num_std * sd) / mid
    return mid, sd, upper, lower, bandwidth


def donchian_channel(
    highs: pl.Series, lows: pl.Series, period: int = 20
) -> tuple[pl.Series, pl.Series]:
    """Calculate (channel_high, channel_low) rolling max/min over period bars."""
    return highs.rolling_max(period), lows.rolling_min(period)


def true_range_series(highs: pl.Series, lows: pl.Series, closes: pl.Series) -> pl.Series:
    """Vectorized True Range via Polars max_horizontal."""
    return pl.select(
        pl.max_horizontal(
            highs - lows,
            (highs - closes.shift(1)).abs(),
            (lows - closes.shift(1)).abs(),
        )
    ).to_series()


def wilder_atr_series(
    highs: pl.Series, lows: pl.Series, closes: pl.Series, period: int = 14
) -> list[float | None]:
    """Wilder ATR: SMA seed over initial period, then Wilder exponential smoothing."""
    if len(closes) < period:
        return [None] * len(closes)
    tr = true_range_series(highs, lows, closes).slice(1)
    seed = numeric(tr.head(period).mean())
    smoothed = pl.concat([pl.Series([seed]), tr.slice(period)]).ewm_mean(
        alpha=1 / period, adjust=False
    )
    return [None] * period + [numeric(v) for v in smoothed]


def mean_range(frame: CausalFrame, period: int = 14) -> float:
    """Vectorized mean high-low range over the latest period bars."""
    if len(frame.candles) < period:
        return 0.0
    if period == 14:
        r = frame.indicator_df["range_mean_14"][-1]
    else:
        r = (frame.df["high"] - frame.df["low"]).tail(period).mean()
    return numeric(r) if r is not None else 0.0


def compute_indicator_pipeline(frame: CausalFrame) -> pl.DataFrame:
    """Complete zero-custom-loop Polars lazy/rolling indicator pipeline.

    Computes RSI, Bollinger (mid/sd/upper/lower/bandwidth/pct_b), Donchian (20),
    EMAs (5, 20), MACD line, and True Range in a single vectorized lazy execution pass.
    """
    df = frame.df
    if len(df) == 0:
        return df

    lazy_plan = (
        df.lazy()
        .with_columns(
            # EMAs
            pl.col("close").ewm_mean(span=5, adjust=False).alias("ema_5"),
            pl.col("close").ewm_mean(span=20, adjust=False).alias("ema_20"),
            pl.col("close").ewm_mean(span=12, adjust=False).alias("ema_12"),
            pl.col("close").ewm_mean(span=26, adjust=False).alias("ema_26"),
            # Donchian 20
            pl.col("high").rolling_max(20).alias("donchian_high_20"),
            pl.col("low").rolling_min(20).alias("donchian_low_20"),
            # Bollinger 20
            pl.col("close").rolling_mean(20).alias("bb_mid_20"),
            pl.col("close").rolling_std(20, ddof=0).alias("bb_std_20"),
            # Bar and rolling high-low ranges
            (pl.col("high") - pl.col("low")).alias("bar_range"),
            (pl.col("high") - pl.col("low")).rolling_mean(14).alias("range_mean_14"),
            # True Range
            pl.max_horizontal(
                pl.col("high") - pl.col("low"),
                (pl.col("high") - pl.col("close").shift(1)).abs(),
                (pl.col("low") - pl.col("close").shift(1)).abs(),
            ).alias("true_range"),
        )
        .with_columns(
            (pl.col("ema_12") - pl.col("ema_26")).alias("macd_line"),
            (4 * pl.col("bb_std_20") / pl.col("bb_mid_20")).alias("bb_bandwidth_20"),
            (
                (pl.col("close") - (pl.col("bb_mid_20") - 2 * pl.col("bb_std_20")))
                / (4 * pl.col("bb_std_20"))
            ).alias("bb_pct_b_20"),
        )
    )

    result = lazy_plan.collect()
    # Keep the exact legacy Wilder convention, but materialize it once for the
    # shared causal prefix so RSI observers do not rerun the recursive kernel.
    result = result.with_columns(pl.Series("rsi_14", wilder_rsi(df["close"]), dtype=pl.Float64))
    return result


def rsi_series(frame: CausalFrame, period: int = 14) -> tuple[float | None, ...]:
    """Return the causal RSI vector from the shared indicator cache."""
    if period != 14:
        return wilder_rsi(close_series(frame), period)
    return tuple(
        None if value is None else float(value)
        for value in frame.indicator_df["rsi_14"].to_list()
    )
