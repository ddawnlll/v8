import io
import json
from decimal import Decimal

import pytest

from v8_next.adapters import binance_capture
from v8_next.adapters.captured_market import load_settled_funding
from v8_next.domain.positioning import positioning_at


def captured(tmp_path, monkeypatch, rows, *, received_ns=2_000_000_000):
    def response(url, **kwargs):
        payload = rows if "fundingRate" in url else []
        if "exchangeInfo" in url:
            payload = {"symbols": [{"symbol": "BTCUSDT"}]}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(binance_capture, "urlopen", response)
    monkeypatch.setattr(binance_capture.time, "time_ns", lambda: received_ns)
    return binance_capture.capture(tmp_path / "fixture")


def test_funding_receipt_is_not_historical_knowledge(tmp_path, monkeypatch):
    row = {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": "0.001"}
    path = captured(tmp_path, monkeypatch, [row, row])
    readings = load_settled_funding(path, max_age_ns=2_000_000_000)
    assert len(readings) == 1
    assert readings[0].event_ns == 1_000_000_000
    assert readings[0].available_ns == 2_000_000_000
    args = (readings, "BTCUSDT-PERP.BINANCE", "settled_funding_rate")
    assert positioning_at(*args, 1_999_999_999) is None
    assert positioning_at(*args, 2_000_000_000) == Decimal(".001")
    assert positioning_at(*args, 3_000_000_000) is None
    stale = load_settled_funding(path, max_age_ns=500_000_000)
    assert positioning_at(stale, args[1], args[2], 2_000_000_000) is None
    (path.parent / "funding.json").write_text("[]")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_settled_funding(path, max_age_ns=1)


@pytest.mark.parametrize("mutation", ["symbol", "future", "conflict", "nonfinite"])
def test_invalid_captured_positioning_rejected(tmp_path, monkeypatch, mutation):
    row = {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": "0.001"}
    rows = [row]
    if mutation == "symbol":
        row["symbol"] = "OTHER"
    elif mutation == "future":
        row["fundingTime"] = 3000
    elif mutation == "conflict":
        rows.append({**row, "fundingRate": "0.002"})
    else:
        row["fundingRate"] = "NaN"
    path = captured(tmp_path, monkeypatch, rows)
    with pytest.raises(ValueError):
        load_settled_funding(path, max_age_ns=2_000_000_000)


@pytest.mark.parametrize("late", [False, True])
def test_verified_capture_reaches_native_paper_decisions(tmp_path, monkeypatch, late):
    from dataclasses import replace

    from test_native_engine import run_qualified_engine
    from test_positioning_experts import context

    from v8_next.adapters.economic_paper import EconomicPaperAdapter
    from v8_next.domain.market import CausalFrame
    from v8_next.economics.controller import InstrumentConstraints
    from v8_next.risk.admission import RiskLimits

    second = 10**9
    decision = 100 * second
    row = {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": "-0.001"}
    path = captured(tmp_path, monkeypatch, [row], received_ns=decision + 1 if late else decision)
    readings = load_settled_funding(path, max_age_ns=200 * second)
    fixture, _ = context()
    frame = CausalFrame(
        "BTCUSDT-PERP.BINANCE",
        decision,
        tuple(
            replace(
                c,
                instrument_id="BTCUSDT-PERP.BINANCE",
                start_ns=c.start_ns * second,
                end_ns=c.end_ns * second,
                received_ns=c.received_ns * second,
                available_ns=c.available_ns * second,
            )
            for c in fixture.candles
        ),
    )
    strategy = EconomicPaperAdapter(
        {decision: frame},
        RiskLimits(Decimal(1), Decimal(".1"), Decimal(100), 0),
        InstrumentConstraints(Decimal(".001"), Decimal(".001"), Decimal(1), Decimal(1)),
        Decimal(100),
        observer="families:funding-crowding-reversal",
        campaign_policy="funding:b:v2",
        positioning_readings=readings,
    )
    run_qualified_engine(strategy=strategy, offset=99 * second, expect_entry=False)
    assert strategy.callback_failure is None
    record = strategy.decisions[0]
    supporting = [s for s in record["stances"] if s["kind"] == "SUPPORT"]
    assert bool(supporting) is not late
    assert (record.get("protection") is not None) is not late
    assert not strategy.campaigns  # Observations do not manufacture calibration.
