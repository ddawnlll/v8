"""Decode verified venue responses without inventing historical availability."""

import json
from decimal import Decimal
from pathlib import Path

from v8_next.adapters.binance_capture import validate_capture
from v8_next.domain.market import Candle


def load_candles(manifest_path: Path) -> tuple[Candle, ...]:
    validate_capture(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    artifact = next(a for a in manifest["artifacts"] if a["path"] == "bars.json")
    rows = json.loads((manifest_path.parent / "bars.json").read_text())
    received_ns = int(artifact["received_time_ns"])
    result = []
    for row in rows:
        # Binance kline closeTime is the inclusive final millisecond.
        end_ns = (int(row[6]) + 1) * 1_000_000
        if end_ns > received_ns:
            continue  # The current mutable candle is not a closed-bar observation.
        result.append(
            Candle(
                instrument_id=f"{manifest['symbol']}-PERP.BINANCE",
                start_ns=int(row[0]) * 1_000_000,
                end_ns=end_ns,
                open=Decimal(row[1]),
                high=Decimal(row[2]),
                low=Decimal(row[3]),
                close=Decimal(row[4]),
                volume=Decimal(row[5]),
                received_ns=received_ns,
                available_ns=None,
                source_hash=artifact["sha256"],
            )
        )
    return tuple(result)
