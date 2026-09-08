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


def capture(destination: Path, symbol: str = "BTCUSDT") -> Path:
    """Write immutable raw responses and a manifest; never send authenticated requests."""
    if not symbol.isascii() or not symbol.isalnum():
        raise ValueError("symbol must be an ASCII alphanumeric venue symbol")
    destination.mkdir(parents=True, exist_ok=False)
    requests: dict[str, tuple[str, dict[str, str | int]]] = {
        "instruments": ("/fapi/v1/exchangeInfo", {}),
        "bars": ("/fapi/v1/klines", {"symbol": symbol, "interval": "1h", "limit": 500}),
        "funding": ("/fapi/v1/fundingRate", {"symbol": symbol, "limit": 100}),
        "funding_schedule": ("/fapi/v1/premiumIndex", {"symbol": symbol}),
        "quote": ("/fapi/v1/ticker/bookTicker", {"symbol": symbol}),
    }
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
    }
    names = [a["path"] for a in manifest["artifacts"]]
    required = set(endpoints) - {"funding_schedule.json"}
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
    args = parser.parse_args()
    manifest = capture(args.destination, args.symbol)
    verify(manifest)
    print(manifest)


if __name__ == "__main__":
    main()
