"""Online paper applies verified final funding at capture receipt, never backdated."""

import hashlib
import json
from pathlib import Path

SOURCE = Path("/tmp/v8-next-funding-window-1788872557488881000/capture-1788872557502463000")


def _write_artifact(directory: Path, name: str, payload: bytes, source_url: str,
                    requested_ns: int, received_ns: int) -> dict:
    (directory / name).write_bytes(payload)
    return {
        "path": name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "source_url": source_url,
        "request_time_ns": requested_ns,
        "received_time_ns": received_ns,
        "historical_available_time_ns": None,
        "historical_pit_status": "UNKNOWN",
    }


def _copy_manifest(tmp_path: Path, name: str, quote_time_ms: int, quote_received_ns: int,
                   funding_rows: list[dict], funding_received_ns: int) -> Path:
    dest = tmp_path / name
    dest.mkdir()
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    quote_url = next(a["source_url"] for a in manifest["artifacts"] if a["path"] == "quote.json")
    funding_url = next(
        a["source_url"] for a in manifest["artifacts"] if a["path"] == "funding.json"
    )
    artifacts = []
    for artifact in manifest["artifacts"]:
        path = artifact["path"]
        if path == "quote.json":
            quote = json.loads((SOURCE / "quote.json").read_text())
            quote["time"] = quote_time_ms
            payload = json.dumps(quote).encode()
            artifacts.append(
                _write_artifact(
                    dest, path, payload, quote_url, quote_received_ns - 1_000_000_000,
                    quote_received_ns,
                )
            )
        elif path == "funding.json":
            payload = json.dumps(funding_rows).encode()
            artifacts.append(
                _write_artifact(
                    dest, path, payload, funding_url, funding_received_ns - 1_000_000_000,
                    funding_received_ns,
                )
            )
        else:
            payload = (SOURCE / path).read_bytes()
            (dest / path).write_bytes(payload)
            artifacts.append({**artifact})
    (dest / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "claim_status": "NO_ECONOMIC_CLAIM",
                "symbol": "BTCUSDT",
                "artifacts": artifacts,
            }
        )
    )
    return dest / "manifest.json"


def test_online_paper_applies_receipt_known_funding_without_position(tmp_path):
    quote_ms = 1788872560902
    first_received = 1788872560959620000
    second_received = first_received + 60_000_000_000
    old_row = {
        "symbol": "BTCUSDT",
        "fundingTime": 1788854400002,
        "fundingRate": "0.00008180",
        "markPrice": "78445.10000000",
    }
    # Boundary 30s after the first quote, known at a receipt before the second quote.
    new_row = {
        "symbol": "BTCUSDT",
        "fundingTime": quote_ms + 30_000,
        "fundingRate": "0.00010000",
        "markPrice": "78457.40000000",
    }
    first = _copy_manifest(
        tmp_path, "capture-1", quote_ms, first_received, [old_row], first_received - 5_000_000_000,
    )
    second = _copy_manifest(
        tmp_path, "capture-2", quote_ms + 60_000, second_received,
        [new_row], first_received + 40_000_000_000,
    )
    try:
        from v8_next.app.paper import replay_account
    except ImportError:
        import pytest

        pytest.skip("v8_next runtime not importable")
    config = {
        "symbols": ["BTCUSDT"],
        "observer_policy": "squeeze",
        "grammar_policy": "range-breakout-48-v1",
        "campaign_policy": "timeout-only-v1",
        "maker_fee": "0.0002",
        "taker_fee": "0.0005",
        "initial_balance": "10000",
        "max_notional": "100",
        "max_exposure_fraction": "0.1",
    }
    first_only = replay_account([first], config)
    assert first_only["online_funding_settlements_applied"] == 0
    assert first_only["funding_status"] == "NO_EXPOSURE_IN_SESSION_NO_FUNDING_LIABILITY"
    both = replay_account([first, second], config)
    # Only the receipt-known in-window boundary is applied; the pre-window row is not.
    assert both["online_funding_settlements_applied"] == 1
    (applied,) = both["online_funding_settlements"]
    assert applied["boundary_ns"] == (quote_ms + 30_000) * 1_000_000
    assert applied["received_ns"] == first_received + 40_000_000_000
    assert applied["rate"] == "0.00010000"
    assert both["balance_total"] == first_only["balance_total"] == "10000.00000000 USDT"
    assert both["funding_status"] == "NO_EXPOSURE_IN_SESSION_NO_FUNDING_LIABILITY"
    assert not both["positions"]


def test_online_funding_never_backdates_knowledge(tmp_path):
    from v8_next.adapters.settlements import final_funding

    quote_ms = 1788872560902
    first_received = 1788872560959620000
    # A record whose boundary is already past but only received after the session
    # cutoff must not be selected for the earlier accounting window.
    late_row = {
        "symbol": "BTCUSDT",
        "fundingTime": quote_ms + 10_000,
        "fundingRate": "0.00010000",
        "markPrice": "78457.40000000",
    }
    only = _copy_manifest(
        tmp_path, "capture-1", quote_ms, first_received, [late_row],
        first_received + 3600_000_000_000,
    )
    assert final_funding([only], quote_ms * 1_000_000, first_received, first_received) == ()


def test_real_capture_source_present():
    assert SOURCE.is_dir(), "real capture fixture required for manifest bytes"
