"""Final funding records for execution-only accounting replay, never decision inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from nautilus_trader.model import FundingRateUpdate, InstrumentId, MarkPriceUpdate, Price

from v8_next.adapters.binance_capture import verify


@dataclass(frozen=True)
class FinalFunding:
    instrument_id: str
    boundary_ns: int
    received_ns: int
    rate: Decimal
    mark_price: Decimal
    source_sha256: str

    def execution_replay_events(
        self, accounting_as_of_ns: int
    ) -> tuple[MarkPriceUpdate, FundingRateUpdate]:
        """Historical accounting time is not the record's availability time.

        Only replay frozen campaigns; never run economic decision logic against
        these backdated account updates. Availability remains in this source record.
        """
        if self.received_ns > accounting_as_of_ns or self.boundary_ns > self.received_ns:
            raise ValueError("funding was not settled and known by accounting cutoff")
        if not self.rate.is_finite() or not self.mark_price.is_finite() or self.mark_price <= 0:
            raise ValueError("invalid final funding values")
        instrument = InstrumentId.from_str(self.instrument_id)
        return (
            MarkPriceUpdate(
                instrument, Price.from_str(str(self.mark_price)), self.boundary_ns, self.boundary_ns
            ),
            FundingRateUpdate(
                instrument,
                self.rate,
                self.boundary_ns,
                self.boundary_ns,
                next_funding_ns=self.boundary_ns,
            ),
        )


def final_funding(
    manifests: list[Path], start_ns: int, end_ns: int, accounting_as_of_ns: int
) -> tuple[FinalFunding, ...]:
    records: dict[tuple[str, int], FinalFunding] = {}
    for manifest in manifests:
        verify(manifest)
        metadata = json.loads(manifest.read_text())
        artifact = next(a for a in metadata["artifacts"] if a["path"] == "funding.json")
        if not artifact["source_url"].startswith("https://fapi.binance.com/fapi/v1/fundingRate?"):
            raise ValueError("only final funding history is accepted, never forecasts")
        received = int(artifact["received_time_ns"])
        if received > accounting_as_of_ns:
            continue
        for row in json.loads((manifest.parent / "funding.json").read_text()):
            if row["symbol"] != metadata["symbol"]:
                raise ValueError("funding instrument mismatch")
            boundary = int(row["fundingTime"]) * 1_000_000
            if not start_ns <= boundary <= end_ns:
                continue
            if not row.get("markPrice"):
                raise ValueError("settlement mark missing")
            record = FinalFunding(
                f"{row['symbol']}-PERP.BINANCE",
                boundary,
                received,
                Decimal(row["fundingRate"]),
                Decimal(row["markPrice"]),
                artifact["sha256"],
            )
            record.execution_replay_events(accounting_as_of_ns)
            key = (record.instrument_id, boundary)
            old = records.get(key)
            if old is not None:
                if (old.rate, old.mark_price) != (record.rate, record.mark_price):
                    raise ValueError("conflicting final funding records")
                if old.received_ns <= received:
                    continue
            records[key] = record
    return tuple(records[key] for key in sorted(records))


def missing_announced_settlements(
    manifests: list[Path], records: tuple[FinalFunding, ...], start_ns: int, end_ns: int
) -> tuple[int, ...] | None:
    """Check observed announcements only; never infer an eight-hour schedule.

    None means schedule evidence is absent. An empty tuple means no missing
    *observed* announcement, not proof that no unobserved schedule change occurred.
    The premiumIndex rate is a forecast and is never consumed as a final rate.
    """
    announced: set[int] = set()
    saw_schedule = False
    for manifest in manifests:
        verify(manifest)
        metadata = json.loads(manifest.read_text())
        entries = [a for a in metadata["artifacts"] if a["path"] == "funding_schedule.json"]
        if not entries:
            continue
        artifact = entries[0]
        received = int(artifact["received_time_ns"])
        if received > end_ns:
            continue
        if not artifact["source_url"].startswith("https://fapi.binance.com/fapi/v1/premiumIndex?"):
            raise ValueError("invalid schedule source")
        row = json.loads((manifest.parent / "funding_schedule.json").read_text())
        if row["symbol"] != metadata["symbol"]:
            raise ValueError("schedule instrument mismatch")
        boundary = int(row["nextFundingTime"]) * 10**6
        saw_schedule = True
        if start_ns <= boundary <= end_ns and received < boundary:
            announced.add(boundary)
    if not saw_schedule:
        return None
    settled = {r.boundary_ns for r in records}
    return tuple(sorted(announced - settled))


def funding_query_windows(
    manifests: list[Path], accounting_as_of_ns: int
) -> list[dict[str, int | str]]:
    """Observed REST response coverage, not a guarantee against later venue revisions."""
    from urllib.parse import parse_qs, urlsplit

    windows = []
    for manifest in manifests:
        verify(manifest)
        metadata = json.loads(manifest.read_text())
        artifact = next(a for a in metadata["artifacts"] if a["path"] == "funding.json")
        received = int(artifact["received_time_ns"])
        if received > accounting_as_of_ns:
            continue
        url = urlsplit(artifact["source_url"])
        query = parse_qs(url.query)
        if not {"startTime", "endTime"} <= query.keys():
            continue  # Legacy recent-history requests establish no explicit interval.
        if (url.scheme, url.netloc, url.path) != (
            "https",
            "fapi.binance.com",
            "/fapi/v1/fundingRate",
        ) or query.get("symbol") != [metadata["symbol"]]:
            raise ValueError("invalid bounded funding source")
        if any(len(query.get(key, [])) != 1 for key in ("startTime", "endTime", "limit")):
            raise ValueError("ambiguous funding query")
        start, end, limit = (int(query[key][0]) for key in ("startTime", "endTime", "limit"))
        requested = int(artifact["request_time_ns"])
        if (
            not 0 <= start <= end
            or not end * 10**6 <= requested <= received
            or not 1 <= limit <= 1000
        ):
            raise ValueError("invalid funding query boundaries")
        rows = json.loads((manifest.parent / "funding.json").read_text())
        if not isinstance(rows, list) or len(rows) >= limit:
            raise ValueError("funding response may be truncated")
        times = [int(row["fundingTime"]) for row in rows]
        if times != sorted(set(times)) or any(
            row["symbol"] != metadata["symbol"] or not start <= boundary <= end
            for row, boundary in zip(rows, times, strict=True)
        ):
            raise ValueError("funding response outside bounded query")
        windows.append(
            {
                "instrument_id": f"{metadata['symbol']}-PERP.BINANCE",
                "start_inclusive_ns": start * 10**6,
                "end_inclusive_ns": end * 10**6,
                "received_ns": received,
                "source_sha256": artifact["sha256"],
                "status": "BOUNDED_RESPONSE_NOT_FINALITY_CERTIFICATE",
            }
        )
    return sorted(windows, key=lambda w: (int(w["start_inclusive_ns"]), int(w["end_inclusive_ns"])))


def position_funding_query_coverage(
    positions: list[dict[str, Any]], windows: list[dict[str, int | str]], cutoff: int
) -> list[dict[str, Any]]:
    """Match native exposure lifetimes to a full bounded response per position.

    Query coverage is not funding finality or venue cash settlement. Open positions
    require coverage through cutoff; closed positions through their actual close.
    """
    result = []
    for position in positions:
        start = position["opened_ns"]
        end = position["closed_ns"] if position["is_closed"] else cutoff
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= cutoff:
            raise ValueError("invalid native exposure interval")
        sources = [
            window["source_sha256"]
            for window in windows
            if window["instrument_id"] == position["instrument_id"]
            and int(window["start_inclusive_ns"]) <= start
            and int(window["end_inclusive_ns"]) >= end
            and int(window["received_ns"]) <= cutoff
        ]
        result.append(
            {
                "instrument_id": position["instrument_id"],
                "opened_ns": start,
                "exposure_end_ns": end,
                "is_closed": position["is_closed"],
                "query_status": "BOUNDED_RESPONSE_COVERS_EXPOSURE"
                if sources
                else "EXPOSURE_NOT_FULLY_QUERIED",
                "source_sha256": sorted(set(sources)),
                "cashflow_finality": "UNQUALIFIED",
            }
        )
    return result
