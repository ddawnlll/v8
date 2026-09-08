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


def test_closed_stream_bar_advances_once_without_revision_or_gap(tmp_path, monkeypatch):
    from dataclasses import replace
    from decimal import Decimal

    from v8_next.domain.market import Candle
    from v8_next.economics.stream_observation import StreamObservations

    hour = 3600 * 10**9
    symbol = "BTCUSDT-PERP.BINANCE"
    observer = StreamObservations((), "range-breakout-48-v1")
    first = Candle(
        symbol,
        0,
        hour,
        Decimal(100),
        Decimal(101),
        Decimal(99),
        Decimal(100),
        Decimal(1),
        hour + 1,
        hour + 1,
        "first",
    )
    assert observer.add_closed_candle(first)
    assert observer.observe(symbol, hour + 1)["latest_closed_bar_ns"] == hour
    assert observer.observe(symbol, 2 * hour)["warmup_status"] == "NEXT_CLOSED_BAR_REQUIRED"
    second = replace(
        first,
        start_ns=hour,
        end_ns=2 * hour,
        received_ns=2 * hour + 1,
        available_ns=2 * hour + 1,
        source_hash="second",
    )
    assert observer.add_closed_candle(second)
    row = observer.observe(symbol, 2 * hour + 1)
    assert row["warmup_status"] == "READY"
    assert row["candle_source_hashes"] == ["first", "second"]
    assert not observer.add_closed_candle(
        replace(second, received_ns=2 * hour + 2, available_ns=2 * hour + 2)
    )
    assert observer.observe(symbol, 2 * hour + 2) is None
    assert observer.candles[symbol][-1].received_ns == 2 * hour + 1
    with pytest.raises(ValueError, match="revision"):
        observer.add_closed_candle(replace(second, close=Decimal(101)))
    with pytest.raises(ValueError, match="gap"):
        observer.add_closed_candle(
            replace(
                second,
                start_ns=3 * hour,
                end_ns=4 * hour,
                received_ns=4 * hour + 1,
                available_ns=4 * hour + 1,
            )
        )


@pytest.mark.parametrize("offset", [0, 1_000_000])
def test_native_binance_bar_boundary_reaches_stream_frame(monkeypatch, offset):
    from nautilus_trader.model import Bar, BarType

    from v8_next.economics.stream_observation import StreamObservations

    hour = 3600 * 10**9
    monkeypatch.setattr("v8_next.app.stream.time.time_ns", lambda: hour + 100)
    actor = QuoteRecorder(io.StringIO())
    actor.observations = StreamObservations((), "range-breakout-48-v1")
    actor.bar_output = io.StringIO()
    actor.observation_output = io.StringIO()
    bar = Bar(
        BarType.from_str("BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"),
        Price.from_str("100.00"),
        Price.from_str("101.00"),
        Price.from_str("99.00"),
        Price.from_str("100.00"),
        Quantity.from_str("1.000"),
        hour - 1_000_000 + offset,
        hour + 10,
    )
    if offset:
        with pytest.raises(ValueError, match="closed-bar"):
            actor.on_bar(bar)
        assert actor.bar_count == 0
        return
    actor.on_bar(bar)
    stored = actor.observations.candles["BTCUSDT-PERP.BINANCE"][0]
    assert (stored.start_ns, stored.end_ns, stored.received_ns) == (0, hour, hour + 10)
    actor.on_quote(
        QuoteTick(
            InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
            Price.from_str("100.00"),
            Price.from_str("100.01"),
            Quantity.from_str("1.000"),
            Quantity.from_str("1.000"),
            hour + 15,
            hour + 20,
        )
    )
    observation = json.loads(actor.observation_output.getvalue())
    assert observation["latest_closed_bar_ns"] == hour
    assert observation["candle_source_hashes"] == [stored.source_hash]
    assert len(observation["stances"]) == 64


@pytest.mark.parametrize("gap", [False, True])
def test_restart_backfill_is_receipt_qualified_and_atomic(tmp_path, monkeypatch, gap):
    from dataclasses import replace
    from decimal import Decimal

    from v8_next.domain.market import Candle
    from v8_next.economics.stream_observation import StreamObservations

    hour = 3600 * 10**9
    instrument = "BTCUSDT-PERP.BINANCE"
    observer = StreamObservations((), "range-breakout-48-v1")
    first = Candle(
        instrument,
        0,
        hour,
        Decimal(100),
        Decimal(101),
        Decimal(99),
        Decimal(100),
        Decimal(1),
        hour + 1,
        hour + 1,
        "first",
    )
    observer.add_closed_candle(first)
    receipt = 5 * hour + 1 if gap else 3 * hour + 1
    second = replace(
        first,
        start_ns=hour,
        end_ns=2 * hour,
        received_ns=receipt,
        available_ns=None,
        source_hash="backfill",
    )
    third = replace(second, start_ns=(3 if gap else 2) * hour, end_ns=(4 if gap else 3) * hour)
    path = tmp_path / "backfill.json"
    path.write_text("{}")
    monkeypatch.setattr(
        "v8_next.economics.stream_observation.load_candles", lambda _: (second, third)
    )
    if gap:
        with pytest.raises(ValueError, match="gap"):
            observer.backfill((path,), receipt)
        assert observer.candles[instrument] == (first,)
        assert observer.source_hashes == []
    else:
        with pytest.raises(ValueError, match="unknown"):
            observer.backfill((path,), receipt - 1)
        observer.backfill((path,), receipt)
        assert observer.observe(instrument, receipt - 1)["latest_closed_bar_ns"] == hour
        row = observer.observe(instrument, receipt)
        assert row["latest_closed_bar_ns"] == 3 * hour
        assert row["warmup_status"] == "READY"
        assert len(observer.source_hashes) == 1
