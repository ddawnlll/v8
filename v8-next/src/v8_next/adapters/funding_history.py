"""Raw bounded funding pagination; receipt clocks belong to individual pages."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


def capture_pages(
    destination: Path, symbol: str, start_ms: int, end_ms: int
) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    cursor = start_ms
    while cursor <= end_ms:
        # Bound work, not evidence: reaching this cap fails without a manifest.
        if len(artifacts) >= 100:
            raise ValueError("funding pagination request budget exhausted")
        url = "https://fapi.binance.com/fapi/v1/fundingRate?" + urlencode(
            dict(symbol=symbol, startTime=cursor, endTime=end_ms, limit=1000)
        )
        requested = time.time_ns()
        with urlopen(url, timeout=30) as response:
            raw = response.read()
        received = time.time_ns()
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError("invalid funding page")
        times = [row["fundingTime"] for row in rows]
        if (
            any(type(t) is not int for t in times)
            or times != sorted(set(times))
            or any(
                row["symbol"] != symbol or not cursor <= t <= end_ms
                for row, t in zip(rows, times, strict=True)
            )
        ):
            raise ValueError("funding page outside requested chronology")
        name = "funding.json" if not artifacts else f"funding-page-{len(artifacts):03d}.json"
        (destination / name).write_bytes(raw)
        artifacts.append(
            dict(
                path=name,
                sha256=hashlib.sha256(raw).hexdigest(),
                source_url=url,
                request_time_ns=requested,
                received_time_ns=received,
                historical_available_time_ns=None,
                historical_pit_status="UNKNOWN",
            )
        )
        if len(rows) < 1000:
            break
        cursor = times[-1] + 1
    return artifacts


def funding_artifacts(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        a
        for a in metadata["artifacts"]
        if a["path"] == "funding.json"
        or (a["path"].startswith("funding-page-") and a["path"].endswith(".json"))
    ]
