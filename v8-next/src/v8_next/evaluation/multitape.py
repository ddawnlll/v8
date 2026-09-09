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

    @property
    def n_bars(self) -> int:
        return min(len(v) for v in self.candles.values()) if self.candles else 0


def _file_sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_multitape(tape_path: Path | str, limit: int | None = None) -> MultiTape:
    """Load every instrument in the quad tape with aligned chronological bars."""
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
    if "funding" in df["channel"].unique().to_list():
        for row in df.filter(pl.col("channel") == "funding")["payload"].to_list():
            try:
                funding.append(
                    FundingRow(
                        instrument=str(row.get("instrument") or ""),
                        funding_time_ms=int(row["funding_time_ms"]),
                        funding_rate=Decimal(str(row["funding_rate"])),
                        interval_hours=float(row.get("funding_interval_hours") or 8.0),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
    # Attribute instrument names from the sibling column when payload lacks them.
    if funding and not funding[0].instrument:
        names = df.filter(pl.col("channel") == "funding")["instrument"].to_list()
        payloads = df.filter(pl.col("channel") == "funding")["payload"].to_list()
        funding = [
            FundingRow(
                instrument=str(nm),
                funding_time_ms=int(pay["funding_time_ms"]),
                funding_rate=Decimal(str(pay["funding_rate"])),
                interval_hours=float(pay.get("funding_interval_hours") or 8.0),
            )
            for nm, pay in zip(names, payloads, strict=False)
            if "funding_time_ms" in pay and "funding_rate" in pay
        ]
    return MultiTape(
        instruments=tuple(instruments),
        candles=candles,
        quote_volumes=volumes,
        funding=tuple(sorted(funding, key=lambda r: r.funding_time_ms)),
        tape_path=str(p),
        tape_sha256=sha,
    )

