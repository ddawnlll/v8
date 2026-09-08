import hashlib
import io
import json
from decimal import Decimal

import pytest
from nautilus_trader.model import Bar, BarType, InstrumentId, Price, Quantity, QuoteTick

from v8_next.app.stream import QuoteRecorder
from v8_next.domain.market import Candle
from v8_next.economics.stream_observation import StreamObservations
from v8_next.evaluation.store import canonical
from v8_next.evaluation.stream_replay import replay_stream


@pytest.mark.parametrize("mutation", [None, "sequence", "observation"])
def test_stream_replays_interleaved_bars_and_quotes(tmp_path, monkeypatch, mutation):
    hour = 3600 * 10**9
    instrument = "BTCUSDT-PERP.BINANCE"
    source = tmp_path / "warmup.json"
    source.write_text("{}")
    seed = Candle(
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
        "warmup",
    )
    monkeypatch.setattr("v8_next.economics.stream_observation.load_candles", lambda _: (seed,))
    monkeypatch.setattr("v8_next.evaluation.stream_replay.source_hash", lambda: "fixture")
    monkeypatch.setattr("v8_next.app.stream.time.time_ns", lambda: 3 * hour)
    actor = QuoteRecorder(io.StringIO())
    actor.bar_output = io.StringIO()
    actor.observation_output = io.StringIO()
    actor.observations = StreamObservations((source,), "range-breakout-48-v1")

    def quote(clock):
        return QuoteTick(
            InstrumentId.from_str(instrument),
            Price.from_str("100.00"),
            Price.from_str("100.01"),
            Quantity.from_str("1.000"),
            Quantity.from_str("1.000"),
            clock,
            clock,
        )

    actor.on_quote(quote(hour + 10))
    actor.on_bar(
        Bar(
            BarType.from_str(f"{instrument}-1-HOUR-LAST-EXTERNAL"),
            Price.from_str("100.00"),
            Price.from_str("101.00"),
            Price.from_str("99.00"),
            Price.from_str("100.00"),
            Quantity.from_str("1.000"),
            2 * hour - 1_000_000,
            2 * hour + 1,
        )
    )
    actor.on_quote(quote(2 * hour + 10))
    (tmp_path / "quotes.jsonl").write_text(actor.output.getvalue())
    (tmp_path / "bars.jsonl").write_text(actor.bar_output.getvalue())
    observations = actor.observation_output.getvalue()
    if mutation == "observation":
        observations = observations.replace('"UNVERIFIED_CALIBRATION"', '"FORGED"')
    (tmp_path / "observations.jsonl").write_text(observations)
    if mutation == "sequence":
        p = tmp_path / "quotes.jsonl"
        p.write_text(p.read_text().replace('"sequence":2', '"sequence":1'))
    (tmp_path / "session.json").write_text(
        canonical(
            dict(
                code_and_lock_hash="fixture",
                warmup_manifests=[str(source)],
                warmup_manifest_hashes=actor.observations.source_hashes,
                grammar="range-breakout-48-v1",
                instruments=[instrument],
            )
        )
    )
    result = dict(quote_count=2, bar_count=1)
    for filename, key in (
        ("quotes.jsonl", "quote_sha256"),
        ("bars.jsonl", "bar_sha256"),
        ("observations.jsonl", "observation_sha256"),
        ("session.json", "session_sha256"),
    ):
        result[key] = hashlib.sha256((tmp_path / filename).read_bytes()).hexdigest()
    (tmp_path / "result.json").write_text(json.dumps(result))
    if mutation:
        with pytest.raises(ValueError):
            replay_stream(tmp_path)
    else:
        report = replay_stream(tmp_path)
        assert report["event_count"] == 3
        assert report["observation_count"] == 2
