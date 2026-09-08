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


def test_revised_accounting_settles_after_last_quote_before_cutoff(tmp_path, monkeypatch):
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.config import BacktestEngineConfig
    from nautilus_trader.model import (
        AccountType,
        CryptoPerpetual,
        Currency,
        InstrumentId,
        Money,
        OmsType,
        Price,
        Quantity,
        Symbol,
        Venue,
    )

    from v8_next.adapters.accounting_replay import replay_frozen_campaigns
    from v8_next.domain.campaign import PaperCampaign

    def test_engine(*args, **kwargs):
        engine = BacktestEngine(BacktestEngineConfig())
        usdt = Currency.from_str("USDT")
        engine.add_venue(
            Venue("BINANCE"),
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money.from_str("10000 USDT")],
            default_leverage=Decimal(1),
        )
        engine.add_instrument(
            CryptoPerpetual(
                instrument_id=InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
                raw_symbol=Symbol("BTCUSDT"),
                base_currency=Currency.from_str("BTC"),
                quote_currency=usdt,
                settlement_currency=usdt,
                is_inverse=False,
                price_precision=2,
                size_precision=3,
                price_increment=Price.from_str("0.01"),
                size_increment=Quantity.from_str("0.001"),
                maker_fee=Decimal("0.001"),
                taker_fee=Decimal("0.001"),
                ts_event=0,
                ts_init=0,
            )
        )
        return engine, {}

    # Only instrument setup is a test fixture. Production capture decoding,
    # settlement cutoff selection and native accounting all run unchanged.
    monkeypatch.setattr("v8_next.adapters.accounting_replay.build_engine", test_engine)
    manifests = []
    for second in (1, 2):
        folder = tmp_path / str(second)
        folder.mkdir()
        artifacts = []
        for name, endpoint, received, payload in (
            (
                "quote.json",
                "ticker/bookTicker",
                second * 10**9,
                {
                    "symbol": "BTCUSDT",
                    "time": second * 1000,
                    "bidPrice": "10000.00",
                    "askPrice": "10000.00",
                    "bidQty": "1.000",
                    "askQty": "1.000",
                },
            ),
            (
                "funding.json",
                "fundingRate",
                4 * 10**9,
                [
                    {
                        "symbol": "BTCUSDT",
                        "fundingTime": 3000,
                        "fundingRate": "0.01",
                        "markPrice": "10000.00",
                    }
                ],
            ),
            (
                "funding_schedule.json",
                "premiumIndex",
                second * 10**9,
                {"symbol": "BTCUSDT", "nextFundingTime": 3000},
            ),
        ):
            raw = json.dumps(payload).encode()
            (folder / name).write_bytes(raw)
            artifacts.append(
                {
                    "path": name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "received_time_ns": received,
                    "source_url": f"https://fapi.binance.com/fapi/v1/{endpoint}?symbol=BTCUSDT",
                }
            )
        manifest = folder / "manifest.json"
        manifest.write_text(json.dumps({"symbol": "BTCUSDT", "artifacts": artifacts}))
        manifests.append(manifest)
    campaign = PaperCampaign(
        "cutoff-test",
        "cutoff-opportunity",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal("0.010"),
        10**9,
        10 * 10**9,
    )
    config = {"maker_fee": "0.001", "taker_fee": "0.001", "initial_balance": "10000"}
    unknown = replay_frozen_campaigns(manifests, (campaign,), config, 3 * 10**9)
    assert unknown["settlement_sources"] == []
    assert unknown["missing_announced_settlements"] == [3 * 10**9]
    known = replay_frozen_campaigns(manifests, (campaign,), config, 4 * 10**9)
    assert len(known["settlement_sources"]) == 1
    assert known["missing_announced_settlements"] == []
    assert Decimal(unknown["balance_total"].split()[0]) == Decimal("9999.90")
    assert Decimal(known["balance_total"].split()[0]) == Decimal("9998.90")
    assert known["realization"] == "SIMULATED"
