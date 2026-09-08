"""Bounded public REST capture; historical availability is explicitly unknown."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

BASE = "https://fapi.binance.com"
RATIO_PERIODS = frozenset({"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"})


def capture(
    destination: Path,
    symbol: str = "BTCUSDT",
    *,
    funding_start_ms: int | None = None,
    include_open_interest: bool = False,
    account_ratio_period: str | None = None,
) -> Path:
    """Write immutable raw responses and a manifest; never send authenticated requests."""
    if not symbol.isascii() or not symbol.isalnum():
        raise ValueError("symbol must be an ASCII alphanumeric venue symbol")
    funding_params: dict[str, str | int] = {"symbol": symbol, "limit": 100}
    if funding_start_ms is not None:
        end_ms = time.time_ns() // 1_000_000
        if type(funding_start_ms) is not int or not 0 <= funding_start_ms <= end_ms:
            raise ValueError("invalid funding history start")
        funding_params.update(startTime=funding_start_ms, endTime=end_ms, limit=1000)
    if account_ratio_period is not None and account_ratio_period not in RATIO_PERIODS:
        raise ValueError("unsupported account ratio period")
    destination.mkdir(parents=True, exist_ok=False)
    requests: dict[str, tuple[str, dict[str, str | int]]] = {
        "instruments": ("/fapi/v1/exchangeInfo", {}),
        "bars": ("/fapi/v1/klines", {"symbol": symbol, "interval": "1h", "limit": 500}),
        "funding": ("/fapi/v1/fundingRate", funding_params),
        "funding_schedule": ("/fapi/v1/premiumIndex", {"symbol": symbol}),
        "quote": ("/fapi/v1/ticker/bookTicker", {"symbol": symbol}),
    }
    if include_open_interest:
        requests["open_interest"] = ("/fapi/v1/openInterest", {"symbol": symbol})
    if account_ratio_period is not None:
        requests["account_ratio"] = (
            "/futures/data/globalLongShortAccountRatio",
            {"symbol": symbol, "period": account_ratio_period, "limit": 1},
        )
    artifacts = []
    for name, (endpoint, params) in requests.items():
        url = BASE + endpoint + ("?" + urlencode(params) if params else "")
        requested_ns = time.time_ns()
        with urlopen(url, timeout=30) as response:
            raw = response.read()
        received_ns = time.time_ns()
        payload = json.loads(raw)
        if isinstance(payload, dict) and "code" in payload:
            raise ValueError(f"venue rejected {name}: {payload['code']}")
        if name == "instruments" and not any(
            item["symbol"] == symbol for item in payload["symbols"]
        ):
            raise ValueError("instrument absent from current venue metadata")
        if name == "funding" and funding_start_ms is not None:
            if not isinstance(payload, list) or len(payload) >= 1000:
                raise ValueError("funding history possibly truncated; bounded pagination required")
            boundaries = [int(row["fundingTime"]) for row in payload]
            if boundaries != sorted(set(boundaries)) or any(
                row["symbol"] != symbol or not funding_start_ms <= boundary <= end_ms
                for row, boundary in zip(payload, boundaries, strict=True)
            ):
                raise ValueError("funding response outside requested chronology")
        path = destination / f"{name}.json"
        path.write_bytes(raw)
        artifacts.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_url": url,
                "request_time_ns": requested_ns,
                "received_time_ns": received_ns,
                "historical_available_time_ns": None,
                "historical_pit_status": "UNKNOWN",
            }
        )
    manifest = {
        "schema_version": 1,
        "symbol": symbol,
        "claim_status": "NO_ECONOMIC_CLAIM",
        "purpose": "raw_capture_not_certified_historical_PIT",
        "artifacts": artifacts,
    }
    result = destination / "manifest.json"
    result.write_text(json.dumps(manifest, indent=2) + "\n")
    return result


def verify(manifest_path: Path) -> None:
    """Reject absent, substituted, or escaping artifact references."""
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parent.resolve()
    for artifact in manifest["artifacts"]:
        path = (root / artifact["path"]).resolve()
        if path.parent != root:
            raise ValueError("artifact escapes capture directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")


def validate_capture(manifest_path: Path) -> None:
    """Validate the complete capture contract, in addition to artifact integrity."""
    verify(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("claim_status") != "NO_ECONOMIC_CLAIM":
        raise ValueError("unsupported capture schema or claim")
    symbol = manifest.get("symbol")
    if not isinstance(symbol, str) or not symbol.isascii() or not symbol.isalnum():
        raise ValueError("invalid capture symbol")
    endpoints = {
        "instruments.json": "/fapi/v1/exchangeInfo",
        "bars.json": "/fapi/v1/klines",
        "funding.json": "/fapi/v1/fundingRate",
        "quote.json": "/fapi/v1/ticker/bookTicker",
        "funding_schedule.json": "/fapi/v1/premiumIndex",
        "open_interest.json": "/fapi/v1/openInterest",
        "account_ratio.json": "/futures/data/globalLongShortAccountRatio",
    }
    names = [a["path"] for a in manifest["artifacts"]]
    required = set(endpoints) - {
        "funding_schedule.json",
        "open_interest.json",
        "account_ratio.json",
    }
    if len(names) != len(set(names)) or not required <= set(names) or set(names) - set(endpoints):
        raise ValueError("incomplete, duplicate or unknown capture artifacts")
    for artifact in manifest["artifacts"]:
        url = urlsplit(artifact["source_url"])
        name = artifact["path"]
        if url.scheme != "https" or url.netloc != "fapi.binance.com" or url.path != endpoints[name]:
            raise ValueError("unexpected capture source")
        query = parse_qs(url.query)
        if name != "instruments.json" and query.get("symbol") != [symbol]:
            raise ValueError("capture source symbol mismatch")
        if name == "bars.json" and query.get("interval") != ["1h"]:
            raise ValueError("unsupported bar interval")
        if name == "account_ratio.json" and (
            len(query.get("period", [])) != 1 or query["period"][0] not in RATIO_PERIODS
        ):
            raise ValueError("unsupported account ratio capture period")
        requested, received = artifact["request_time_ns"], artifact["received_time_ns"]
        if type(requested) is not int or type(received) is not int or not 0 < requested <= received:
            raise ValueError("invalid capture clocks")
        if (
            artifact.get("historical_pit_status") != "UNKNOWN"
            or artifact.get("historical_available_time_ns") is not None
        ):
            raise ValueError("capture cannot certify historical availability")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--include-open-interest", action="store_true")
    args = parser.parse_args()
    manifest = capture(
        args.destination, args.symbol, include_open_interest=args.include_open_interest
    )
    verify(manifest)
    print(manifest)


if __name__ == "__main__":
    main()
