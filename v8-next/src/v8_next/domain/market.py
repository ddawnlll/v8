"""Immutable causal inputs; observation time is never historical availability."""

from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property

import polars as pl


@dataclass(frozen=True)
class Candle:
    instrument_id: str
    start_ns: int
    end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    received_ns: int
    available_ns: int | None
    source_hash: str

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if any(not value.is_finite() for value in values):
            raise ValueError("non-finite candle")
        if min(values[:4]) <= 0 or self.volume < 0:
            raise ValueError("invalid price or volume")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("invalid OHLC ordering")
        if self.start_ns >= self.end_ns:
            raise ValueError("invalid bar interval")
        if self.available_ns is not None and self.available_ns < self.end_ns:
            raise ValueError("completed candle cannot be available before close")


@dataclass(frozen=True)
class CausalFrame:
    instrument_id: str
    decision_ns: int
    candles: tuple[Candle, ...]

    def __post_init__(self) -> None:
        previous_end = -1
        for candle in self.candles:
            if candle.instrument_id != self.instrument_id:
                raise ValueError("mixed instruments")
            if candle.available_ns is None or candle.available_ns > self.decision_ns:
                raise ValueError("unavailable input")
            if candle.start_ns < previous_end:
                raise ValueError("duplicate or overlapping candles")
            previous_end = candle.end_ns

    @property
    def continuous(self) -> bool:
        return all(
            a.end_ns == b.start_ns for a, b in zip(self.candles, self.candles[1:], strict=False)
        )

    @cached_property
    def df(self) -> pl.DataFrame:
        if not self.candles:
            return pl.DataFrame(
                schema={
                    "start_ns": pl.Int64,
                    "end_ns": pl.Int64,
                    "open": pl.Float64,
                    "high": pl.Float64,
                    "low": pl.Float64,
                    "close": pl.Float64,
                    "volume": pl.Float64,
                }
            )
        return pl.DataFrame(
            {
                "start_ns": [c.start_ns for c in self.candles],
                "end_ns": [c.end_ns for c in self.candles],
                "open": [float(c.open) for c in self.candles],
                "high": [float(c.high) for c in self.candles],
                "low": [float(c.low) for c in self.candles],
                "close": [float(c.close) for c in self.candles],
                "volume": [float(c.volume) for c in self.candles],
            },
            schema={
                "start_ns": pl.Int64,
                "end_ns": pl.Int64,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Float64,
            },
        )

    def lazy(self) -> pl.LazyFrame:
        return self.df.lazy()


def frame_at(instrument_id: str, decision_ns: int, candles: tuple[Candle, ...]) -> CausalFrame:
    """Select admissible versions; duplicates must agree, never silently overwrite."""
    unique: dict[int, Candle] = {}
    for candle in candles:
        if candle.instrument_id != instrument_id:
            continue
        if candle.available_ns is None or candle.available_ns > decision_ns:
            continue
        previous = unique.get(candle.start_ns)
        if previous is not None and previous != candle:
            raise ValueError("conflicting bar versions require explicit revision policy")
        unique[candle.start_ns] = candle
    return CausalFrame(instrument_id, decision_ns, tuple(unique[t] for t in sorted(unique)))
