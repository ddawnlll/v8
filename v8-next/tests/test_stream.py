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
