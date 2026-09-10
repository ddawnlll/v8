"""Multi-asset tape loading: real venue klines, funding rows, quote volumes.

Reads the quad tape.jsonl directly (channel/instrument/payload records with
per-record hashes). Nothing is synthesized: instruments, spans and funding
rows are whatever the file contains. Single-asset BTC loading stays in
gate_resolution.load_tape_candles; this module owns the multi-asset path.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl

from v8_next.domain.market import Candle

INSTRUMENT_SUFFIX = "-PERP.BINANCE"


@dataclass(frozen=True)
class FundingRow:
    instrument: str  # e.g. BTCUSDT
    funding_time_ms: int
    funding_rate: Decimal
    interval_hours: float


@dataclass(frozen=True)
class MultiTape:
    instruments: tuple[str, ...]  # e.g. ("BTCUSDT", ...)
    candles: dict[str, tuple[Candle, ...]]
    quote_volumes: dict[str, tuple[float, ...]]  # per-bar quote volume, same order
    funding: tuple[FundingRow, ...]
    tape_path: str
    tape_sha256: str
    # Malformed funding records skipped at load (never silently free).
    # Consumers must surface this alongside funding cost, not ignore it.
    funding_dropped: int = 0
    funding_raw_count: int = 0

    @property
    def n_bars(self) -> int:
        return min(len(v) for v in self.candles.values()) if self.candles else 0


def funding_interval_hours(payload: dict[str, Any]) -> float:
    """Extract the funding interval, accepting known key variants.

    Falls back to the 8h venue convention only when the record carries no
    interval key at all; callers still report that the default applied.
    """
    for key in ("funding_interval_hours", "fundingIntervalHours", "interval_hours"):
        value = payload.get(key)
        if value is not None:
            return float(value)
    return 8.0


def _file_sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_multitape(
    tape_path: Path | str, limit: int | None = None, offset: int = 0
) -> MultiTape:
    """Load every instrument in the quad tape with aligned chronological bars.

    offset skips that many leading bars per leg (frozen-OOS windowing); limit
    caps the leg length after the offset.
    """
    p = Path(tape_path)
    if p.is_dir():
        p = p / "tape.jsonl"
    if not p.is_file():
        raise FileNotFoundError(f"Multi tape not found at {p}")
    sha = _file_sha(p)
    df = pl.read_ndjson(p)

    kline = df.filter(pl.col("channel") == "kline").sort(["instrument", "event_time"])
    instruments: list[str] = sorted(kline["instrument"].unique().to_list())
    if not instruments:
        raise ValueError("no kline instruments in tape")
    # Per-leg end_ns -> (candle, quote_volume), then intersect on chronology.
    leg_maps: dict[str, dict[int, tuple[Candle, float]]] = {}
    for inst in instruments:
        sub = kline.filter(pl.col("instrument") == inst)
        if offset:
            sub = sub.slice(offset)
        if limit is not None:
            sub = sub.head(limit)
        m: dict[int, tuple[Candle, float]] = {}
        for row in sub["payload"].to_list():
            if not row.get("closed", True):
                continue
            c = Candle(
                instrument_id=f"{inst}{INSTRUMENT_SUFFIX}",
                start_ns=int(row["open_time_ms"]) * 1_000_000,
                end_ns=(int(row["close_time_ms"]) + 1) * 1_000_000,
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
                volume=Decimal(str(row["volume"])),
                received_ns=(int(row["close_time_ms"]) + 1) * 1_000_000,
                available_ns=(int(row["close_time_ms"]) + 1) * 1_000_000,
                source_hash=str(row["payload_hash"]),
            )
            m[c.end_ns] = (c, float(row.get("quote_asset_volume") or 0.0))
        if not m:
            raise ValueError(f"no closed bars for {inst}")
        leg_maps[inst] = m

    common_sorted = sorted(set.intersection(*[set(m) for m in leg_maps.values()]))
    if len(common_sorted) < 2:
        raise ValueError("no common chronological window across legs")
    candles = {inst: tuple(leg_maps[inst][ns][0] for ns in common_sorted) for inst in instruments}
    volumes = {inst: tuple(leg_maps[inst][ns][1] for ns in common_sorted) for inst in instruments}

    funding: list[FundingRow] = []
    funding_raw = (
        df.filter(pl.col("channel") == "funding")["payload"].to_list()
        if "funding" in df["channel"].unique().to_list()
        else []
    )
    funding_dropped = 0
    for row in funding_raw:
        try:
            funding.append(
                FundingRow(
                    instrument=str(row.get("instrument") or ""),
                    funding_time_ms=int(row["funding_time_ms"]),
                    funding_rate=Decimal(str(row["funding_rate"])),
                    interval_hours=funding_interval_hours(row),
                )
            )
        except (KeyError, ValueError, TypeError):
            # Never silently free: dropped records are counted on the tape.
            funding_dropped += 1
    # Attribute instrument names from the sibling column when payload lacks them.
    if funding and not funding[0].instrument:
        names = df.filter(pl.col("channel") == "funding")["instrument"].to_list()
        payloads = df.filter(pl.col("channel") == "funding")["payload"].to_list()
        rebuilt: list[FundingRow] = []
        for nm, pay in zip(names, payloads, strict=False):
            if "funding_time_ms" not in pay or "funding_rate" not in pay:
                funding_dropped += 1
                continue
            try:
                rebuilt.append(
                    FundingRow(
                        instrument=str(nm),
                        funding_time_ms=int(pay["funding_time_ms"]),
                        funding_rate=Decimal(str(pay["funding_rate"])),
                        interval_hours=funding_interval_hours(pay),
                    )
                )
            except (KeyError, ValueError, TypeError):
                funding_dropped += 1
        funding = rebuilt
    return MultiTape(
        instruments=tuple(instruments),
        candles=candles,
        quote_volumes=volumes,
        funding=tuple(sorted(funding, key=lambda r: r.funding_time_ms)),
        tape_path=str(p),
        tape_sha256=sha,
        funding_dropped=funding_dropped,
        funding_raw_count=len(funding_raw),
    )

