import hashlib
import json
from decimal import Decimal

import pytest

from v8_next.adapters.settlements import FinalFunding, missing_announced_settlements


def test_accounting_replay_preserves_economic_boundary_and_receipt_separately():
    record = FinalFunding(
        "BTCUSDT-PERP.BINANCE", 10, 20, Decimal("0.001"), Decimal(10000), "test-only"
    )
    mark, funding = record.execution_replay_events(20)
    assert mark.ts_event == funding.ts_event == 10
    assert funding.ts_init == 10
    assert record.received_ns == 20
    with pytest.raises(ValueError, match="cutoff"):
        record.execution_replay_events(19)


def test_future_boundary_cannot_be_disguised_as_final_settlement():
    record = FinalFunding(
        "BTCUSDT-PERP.BINANCE", 30, 20, Decimal("0.001"), Decimal(10000), "test-only"
    )
    with pytest.raises(ValueError, match="settled"):
        record.execution_replay_events(40)


def test_announced_boundary_requires_final_record_without_using_forecast_rate(tmp_path):
    raw = json.dumps(
        {"symbol": "BTCUSDT", "nextFundingTime": 20, "lastFundingRate": "0.987"}
    ).encode()
    (tmp_path / "funding_schedule.json").write_bytes(raw)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "artifacts": [
                    {
                        "path": "funding_schedule.json",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "received_time_ns": 10_000_000,
                        "source_url": "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT",
                    }
                ],
            }
        )
    )
    assert missing_announced_settlements([manifest], (), 0, 30_000_000) == (20_000_000,)
    final = FinalFunding(
        "BTCUSDT-PERP.BINANCE",
        20_000_000,
        25_000_000,
        Decimal("0.001"),
        Decimal(10000),
        "test-only",
    )
    assert missing_announced_settlements([manifest], (final,), 0, 30_000_000) == ()
