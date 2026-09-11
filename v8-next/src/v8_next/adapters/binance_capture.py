"""Bounded public REST capture; historical availability is explicitly unknown."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

from v8_next.adapters.funding_history import capture_pages, funding_artifacts, validate_page_chain

BASE = "https://fapi.binance.com"
RATIO_PERIODS = frozenset({"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"})


def _fetch(url: str, timeout: int = 120) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return bytes(response.read())


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
    }
    if include_open_interest:
        requests["open_interest"] = ("/fapi/v1/openInterest", {"symbol": symbol})
    if account_ratio_period is not None:
        requests["account_ratio"] = (
            "/futures/data/globalLongShortAccountRatio",
            {"symbol": symbol, "period": account_ratio_period, "limit": 1},
        )
    # The economic decision uses this quote receipt. Acquire auxiliary inputs
    # first so the same capture can use them without backdating availability.
    requests["quote"] = ("/fapi/v1/ticker/bookTicker", {"symbol": symbol})
    artifacts = []
    for name, (endpoint, params) in requests.items():
        if name == "funding" and funding_start_ms is not None:
            artifacts.extend(capture_pages(destination, symbol, funding_start_ms, end_ms))
            continue
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


def capture_agg_trades(
    destination: Path,
    symbol: str = "BTCUSDT",
    *,
    start_ms: int,
    end_ms: int,
    page_limit: int = 1000,
    max_pages: int = 100,
    page_delay_s: float = 1.0,
) -> Path:
    """Page public aggTrades into immutable raw pages plus a manifest.

    Same honesty contract as :func:`capture`: raw venue bytes, request/receive
    clocks, no authentication, no backfilled availability claims. Paging follows
    ``fromId``; each page is stored verbatim so a later reader can re-hash it.
    """
    if not symbol.isascii() or not symbol.isalnum():
        raise ValueError("symbol must be an ASCII alphanumeric venue symbol")
    if type(start_ms) is not int or type(end_ms) is not int or not 0 < start_ms < end_ms:
        raise ValueError("invalid trade capture window")
    if not 1 <= page_limit <= 1000:
        raise ValueError("page_limit must be in [1, 1000]")
    destination.mkdir(parents=True, exist_ok=False)
    artifacts = []
    from_id: int | None = None
    pages = 0
    while pages < max_pages:
        params: dict[str, str | int] = {
            "symbol": symbol,
            "limit": page_limit,
            "startTime": start_ms,
            "endTime": end_ms,
        }
        if from_id is not None:
            params["fromId"] = from_id
        url = BASE + "/fapi/v1/aggTrades?" + urlencode(params)
        requested_ns = time.time_ns()
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read()
        except Exception as exc:
            # Venue weight limits answer 429/418; back off and retry the same
            # page instead of aborting the capture halfway.
            code = getattr(exc, "code", None)
            if code in (429, 418) and page_delay_s >= 0:
                time.sleep(max(page_delay_s, 5.0))
                continue
            raise
        received_ns = time.time_ns()
        payload = json.loads(raw)
        if isinstance(payload, dict) and "code" in payload:
            raise ValueError(f"venue rejected aggTrades: {payload['code']}")
        if not isinstance(payload, list) or not payload:
            break
        path = destination / f"trades-{pages:04d}.json"
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
                "trade_count": len(payload),
                "first_id": payload[0].get("a"),
                "last_id": payload[-1].get("a"),
            }
        )
        pages += 1
        if page_delay_s > 0:
            time.sleep(page_delay_s)
        last_time = payload[-1].get("T")
        if len(payload) < page_limit or (isinstance(last_time, int) and last_time >= end_ms):
            break
        from_id = int(payload[-1]["a"]) + 1
    manifest = {
        "schema_version": 1,
        "symbol": symbol,
        "claim_status": "NO_ECONOMIC_CLAIM",
        "purpose": "raw_aggtrades_not_certified_historical_PIT",
        "window_ms": [start_ms, end_ms],
        "pages": pages,
        "artifacts": artifacts,
    }
    result = destination / "manifest.json"
    result.write_text(json.dumps(manifest, indent=2) + "\n")
    return result


ARCHIVE_BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades"


def agg_trades_dump_stats(payload: bytes) -> dict[str, Any]:
    """Row count, time span and aggressor-flag coverage of one archive payload.

    Read with the same reader the backtest uses, so a downstream window cannot
    be honest while the manifest that describes it is not.
    """
    from v8_next.adapters.trade_tape import _dump_flag, _dump_rows

    rows = 0
    unparsable = 0
    unknown_flag = 0
    first_ms: int | None = None
    last_ms: int | None = None
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".csv"):
                continue
            with zf.open(name) as raw:
                for row in _dump_rows(io.TextIOWrapper(raw, encoding="utf-8", newline="")):
                    rows += 1
                    if len(row) < 7:
                        unparsable += 1
                        continue
                    try:
                        ts_ms = int(row[5])
                    except ValueError:
                        unparsable += 1
                        continue
                    first_ms = ts_ms if first_ms is None else min(first_ms, ts_ms)
                    last_ms = ts_ms if last_ms is None else max(last_ms, ts_ms)
                    if _dump_flag(row[6]) is None:
                        unknown_flag += 1
    return {
        "rows": rows,
        "rows_unparsable": unparsable,
        "rows_unknown_aggressor": unknown_flag,
        "first_transact_time_ms": first_ms,
        "last_transact_time_ms": last_ms,
    }


def capture_agg_trades_dump(
    destination: Path,
    symbol: str = "BTCUSDT",
    *,
    days: tuple[str, ...],
    archive_base: str = ARCHIVE_BASE,
) -> Path:
    """Download public daily aggTrades archives whose checksum the venue signed.

    The REST endpoint only returns recent trades, so a bar+trade run over an
    older bar tape can only be measured against these daily archives. Each
    download is verified against the venue's own ``.CHECKSUM`` file before it is
    stored; a mismatch aborts the capture instead of leaving an unverified tape
    behind. Both files are kept verbatim, so the same tape can be re-hashed.
    """
    if not symbol.isascii() or not symbol.isalnum():
        raise ValueError("symbol must be an ASCII alphanumeric venue symbol")
    if not days:
        raise ValueError("at least one archive day is required")
    if len(set(days)) != len(days):
        raise ValueError("duplicate archive day")
    for day in days:
        try:
            parsed = datetime.date.fromisoformat(day)
        except ValueError:
            raise ValueError(f"archive day must be YYYY-MM-DD, got {day!r}") from None
        if parsed.isoformat() != day:
            raise ValueError(f"archive day must be zero-padded YYYY-MM-DD, got {day!r}")
    destination.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, Any]] = []
    for day in sorted(days):
        name = f"{symbol}-aggTrades-{day}.zip"
        url = f"{archive_base}/{symbol}/{name}"
        requested_ns = time.time_ns()
        payload = _fetch(url)
        checksum = _fetch(url + ".CHECKSUM")
        received_ns = time.time_ns()
        digest = hashlib.sha256(payload).hexdigest()
        declared = checksum.decode().split()[0].strip()
        if digest != declared:
            raise ValueError(f"venue checksum mismatch for {name}")
        stats = agg_trades_dump_stats(payload)
        if stats["rows"] == 0:
            raise ValueError(f"archive {name} carries no rows")
        (destination / name).write_bytes(payload)
        (destination / (name + ".CHECKSUM")).write_bytes(checksum)
        artifacts.append(
            {
                "day": day,
                "path": name,
                "checksum_path": name + ".CHECKSUM",
                "sha256": digest,
                "venue_declared_sha256": declared,
                "source_url": url,
                "request_time_ns": requested_ns,
                "received_time_ns": received_ns,
                "historical_available_time_ns": None,
                "historical_pit_status": "UNKNOWN",
                **stats,
            }
        )
        if time.time_ns() < received_ns:  # pragma: no cover - clock sanity
            raise ValueError("capture clocks are not monotonic")
    manifest = {
        "schema_version": 1,
        "symbol": symbol,
        "source": "BINANCE_DATA_VISION_DAILY_AGGTRADES_ARCHIVE",
        "claim_status": "NO_ECONOMIC_CLAIM",
        "purpose": "raw_aggtrades_archive_not_certified_historical_PIT",
        "days": sorted(days),
        "rows": sum(a["rows"] for a in artifacts),
        "artifacts": artifacts,
    }
    result = destination / "manifest.json"
    result.write_text(json.dumps(manifest, indent=2) + "\n")
    return result


def validate_dump_capture(manifest_path: Path) -> None:
    """Validate an aggTrades archive capture: integrity, coverage, provenance."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("claim_status") != "NO_ECONOMIC_CLAIM":
        raise ValueError("unsupported dump capture schema or claim")
    symbol = manifest.get("symbol")
    if not isinstance(symbol, str) or not symbol.isascii() or not symbol.isalnum():
        raise ValueError("invalid capture symbol")
    root = manifest_path.parent.resolve()
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("empty dump capture")
    if manifest.get("days") != sorted(a["day"] for a in artifacts):
        raise ValueError("manifest days do not match its archives")
    for artifact in artifacts:
        path = (root / artifact["path"]).resolve()
        checksum_path = (root / artifact["checksum_path"]).resolve()
        if path.parent != root or checksum_path.parent != root:
            raise ValueError("artifact escapes capture directory")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != artifact["sha256"] or digest != artifact["venue_declared_sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        declared = checksum_path.read_text().split()[0].strip()
        if declared != digest:
            raise ValueError(f"venue checksum file disagrees: {checksum_path.name}")
        if artifact.get("historical_pit_status") != "UNKNOWN":
            raise ValueError("archive capture cannot certify historical availability")
    if manifest.get("rows") != sum(a["rows"] for a in artifacts):
        raise ValueError("manifest row total does not match its archives")


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
    validate_page_chain(manifest_path.parent, manifest)
    pages = funding_artifacts(manifest)
    for i, page in enumerate(pages):
        expected = "funding.json" if i == 0 else f"funding-page-{i:03d}.json"
        if page["path"] != expected:
            raise ValueError("invalid funding page sequence")
        endpoints[expected] = "/fapi/v1/fundingRate"
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
    parser.add_argument("--account-ratio-period", choices=sorted(RATIO_PERIODS))
    parser.add_argument(
        "--funding-start-ms", type=int, help="Inclusive funding-history start, Unix milliseconds"
    )
    parser.add_argument(
        "--agg-trades-dump-day",
        action="append",
        default=[],
        help="Download one verified daily aggTrades archive (YYYY-MM-DD); repeatable. "
        "Switches the capture to archive mode, which carries historical aggressor evidence.",
    )
    args = parser.parse_args()
    if args.agg_trades_dump_day:
        dump_manifest = capture_agg_trades_dump(
            args.destination, args.symbol, days=tuple(args.agg_trades_dump_day)
        )
        validate_dump_capture(dump_manifest)
        print(dump_manifest)
        return
    manifest = capture(
        args.destination,
        args.symbol,
        funding_start_ms=args.funding_start_ms,
        include_open_interest=args.include_open_interest,
        account_ratio_period=args.account_ratio_period,
    )
    verify(manifest)
    print(manifest)


if __name__ == "__main__":
    main()
