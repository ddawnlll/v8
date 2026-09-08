"""Immutable causal inputs; observation time is never historical availability."""

from dataclasses import dataclass
from decimal import Decimal


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
