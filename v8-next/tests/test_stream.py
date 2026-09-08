import io
import json

import pytest
from nautilus_trader.model import InstrumentId, Price, Quantity, QuoteTick

from v8_next.app.stream import QuoteRecorder


@pytest.mark.parametrize("event,received", [(10, 20), (21, 20)])
def test_native_quote_record_preserves_receipt_and_rejects_reversed_clocks(
    monkeypatch, event, received
):
    monkeypatch.setattr("v8_next.app.stream.time.time_ns", lambda: 30)
    output = io.StringIO()
    actor = QuoteRecorder(output)
    quote = QuoteTick(
        InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
        Price.from_str("100.00"),
        Price.from_str("100.01"),
        Quantity.from_str("1.000"),
        Quantity.from_str("1.000"),
        event,
        received,
    )
    if event > received:
        with pytest.raises(ValueError, match="clocks"):
            actor.on_quote(quote)
        assert actor.failure
        assert not output.getvalue()
    else:
        actor.on_quote(quote)
        row = json.loads(output.getvalue())
        assert (row["event_ns"], row["received_ns"], row["recorded_ns"]) == (10, 20, 30)
        assert actor.count == 1


def test_disk_failure_stops_native_node_once_and_suppresses_later_records(monkeypatch):
    monkeypatch.setattr("v8_next.app.stream.time.time_ns", lambda: 30)

    class BrokenOutput(io.StringIO):
        def write(self, text):
            raise OSError("disk unavailable")

    stopped = []
    actor = QuoteRecorder(BrokenOutput())
    actor.stop_node = lambda: stopped.append(True)
    quote = QuoteTick(
        InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
        Price.from_str("100.00"),
        Price.from_str("100.01"),
        Quantity.from_str("1.000"),
        Quantity.from_str("1.000"),
        10,
        20,
    )
    with pytest.raises(OSError):
        actor.on_quote(quote)
    actor.on_quote(quote)
    assert stopped == [True]
    assert actor.count == 0
    assert actor.failure == "OSError: disk unavailable"


def test_stream_warmup_uses_receipt_and_expires_at_next_bar(tmp_path, monkeypatch):
    from decimal import Decimal

    from v8_next.domain.market import Candle
    from v8_next.economics.stream_observation import StreamObservations

    hour = 3600 * 10**9
    symbol = "BTCUSDT-PERP.BINANCE"
    source = tmp_path / "manifest.json"
    source.write_text("{}")
    candle = Candle(
        symbol,
        0,
        hour,
        Decimal(100),
        Decimal(101),
        Decimal(99),
        Decimal(100),
        Decimal(1),
        hour + 10,
        None,
        "fixture",
    )
    monkeypatch.setattr("v8_next.economics.stream_observation.load_candles", lambda _: (candle,))
    observer = StreamObservations((source,), "range-breakout-48-v1")
    assert observer.observe(symbol, hour + 9)["warmup_status"] == "WARMUP_UNAVAILABLE"
    row = observer.observe(symbol, hour + 10)
    assert row["warmup_status"] == "READY"
    assert len(row["stances"]) == 64
    assert row["opportunity"] is None
    assert row["admission_status"] == "UNVERIFIED_CALIBRATION"
    assert observer.observe(symbol, hour + 11) is None
    assert observer.observe(symbol, 2 * hour)["warmup_status"] == "NEXT_CLOSED_BAR_REQUIRED"
