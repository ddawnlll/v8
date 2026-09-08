"""Native public Binance quote capture; no execution client or capital authority."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from nautilus_trader.adapters.binance import (
    BinanceDataClientConfig,
    BinanceDataClientFactory,
    BinanceInstrumentProviderConfig,
    BinanceProductType,
)
from nautilus_trader.common import DataActor, Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import Bar, BarType, InstrumentId, QuoteTick, TraderId

from v8_next.app.observe import source_hash
from v8_next.domain.market import Candle
from v8_next.economics.stream_observation import StreamObservations
from v8_next.evaluation.store import canonical

INSTRUMENTS = ("BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE")


class QuoteRecorder(DataActor):
    def __init__(self, output: TextIO) -> None:
        super().__init__()
        self.output = output
        self.stop_node: Callable[[], None] | None = None
        self.count = 0
        self.bar_count = 0
        self.bar_output: TextIO | None = None
        self.observations: StreamObservations | None = None
        self.observation_output: TextIO | None = None
        self.failure: str | None = None

    def on_start(self) -> None:
        for name in INSTRUMENTS:
            self.subscribe_quotes(InstrumentId.from_str(name))
            if self.observations is not None:
                self.subscribe_bars(BarType.from_str(f"{name}-1-HOUR-LAST-EXTERNAL"))

    def on_bar(self, bar: Bar) -> None:
        if self.failure is not None:
            return
        try:
            instrument = str(bar.bar_type.instrument_id)
            hour, millisecond = 3600 * 10**9, 10**6
            end = bar.ts_event + millisecond
            if (
                instrument not in INSTRUMENTS
                or str(bar.bar_type) != f"{instrument}-1-HOUR-LAST-EXTERNAL"
                or end % hour != 0
                or not 0 < end <= bar.ts_init <= time.time_ns()
            ):
                raise ValueError("unqualified Binance closed-bar clocks or type")
            if self.bar_output is None or self.observations is None:
                raise ValueError("closed-bar recorder not configured")
            record = dict(
                sequence=self.count + self.bar_count,
                instrument_id=instrument,
                start_ns=end - hour,
                end_ns=end,
                native_event_ns=bar.ts_event,
                received_ns=bar.ts_init,
                open=str(bar.open),
                high=str(bar.high),
                low=str(bar.low),
                close=str(bar.close),
                volume=str(bar.volume),
                source="NAUTILUS_BINANCE_CLOSED_KLINE_V2_0_0RC4",
            )
            serialized = canonical(record)
            candle = Candle(
                instrument,
                end - hour,
                end,
                bar.open.as_decimal(),
                bar.high.as_decimal(),
                bar.low.as_decimal(),
                bar.close.as_decimal(),
                bar.volume.as_decimal(),
                bar.ts_init,
                bar.ts_init,
                hashlib.sha256(serialized.encode()).hexdigest(),
            )
            self.bar_output.write(serialized + "\n")
            self.bar_output.flush()
            self.observations.add_closed_candle(candle)
            self.bar_count += 1
        except Exception as error:
            self.failure = f"{type(error).__name__}: {error}"
            if self.stop_node is not None:
                self.stop_node()
            raise

    def on_quote(self, quote: QuoteTick) -> None:
        if self.failure is not None:
            return
        try:
            observed = time.time_ns()
            if (
                str(quote.instrument_id) not in INSTRUMENTS
                or not 0 < quote.ts_event <= quote.ts_init <= observed
            ):
                raise ValueError("unqualified quote identity or clocks")
            if (
                quote.bid_price.as_decimal() <= 0
                or quote.ask_price.as_decimal() < quote.bid_price.as_decimal()
            ):
                raise ValueError("invalid quote prices")
            self.output.write(
                canonical(
                    dict(
                        sequence=self.count + self.bar_count,
                        instrument_id=str(quote.instrument_id),
                        event_ns=quote.ts_event,
                        received_ns=quote.ts_init,
                        recorded_ns=observed,
                        bid=str(quote.bid_price),
                        ask=str(quote.ask_price),
                        bid_size=str(quote.bid_size),
                        ask_size=str(quote.ask_size),
                        claim_status="NO_ECONOMIC_CLAIM",
                    )
                )
                + "\n"
            )
            self.output.flush()
            self.count += 1
            if self.observations is not None and self.observation_output is not None:
                observation = self.observations.observe(str(quote.instrument_id), quote.ts_init)
                if observation is not None:
                    observation["trigger_sequence"] = self.count + self.bar_count - 1
                    self.observation_output.write(canonical(observation) + "\n")
                    self.observation_output.flush()
        except Exception as error:
            self.failure = f"{type(error).__name__}: {error}"
            if self.stop_node is not None:
                self.stop_node()
            raise


async def capture_stream(
    destination: Path,
    duration_seconds: int,
    *,
    manifests: tuple[Path, ...] = (),
    grammar: str | None = None,
    resume_from: Path | None = None,
) -> dict:
    if duration_seconds <= 0:
        raise ValueError("positive observation duration required")
    observations: StreamObservations | None
    parent_hash = None
    if resume_from is not None:
        from v8_next.evaluation.stream_replay import restore_stream

        if manifests:
            raise ValueError("resume inherits warmup sources")
        observations = restore_stream(resume_from)
        if grammar is not None and grammar != observations.grammar:
            raise ValueError("resume cannot change grammar")
        grammar = observations.grammar
        parent_session = json.loads((resume_from / "session.json").read_text())
        manifests = tuple(Path(p) for p in parent_session["warmup_manifests"])
        parent_raw = (resume_from / "result.json").read_bytes()
        if json.loads(parent_raw)["ended_ns"] > time.time_ns():
            raise ValueError("resume source reaches future")
        parent_hash = hashlib.sha256(parent_raw).hexdigest()
    else:
        grammar = grammar or "range-breakout-48-v1"
        observations = StreamObservations(manifests, grammar) if manifests else None
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "session.json").write_text(
        canonical(
            dict(
                instruments=INSTRUMENTS,
                resume_from=str(resume_from.resolve()) if resume_from else None,
                parent_result_sha256=parent_hash,
                grammar=grammar,
                warmup_manifest_hashes=observations.source_hashes if observations else [],
                warmup_manifests=[str(p.resolve()) for p in manifests],
                started_ns=time.time_ns(),
                duration_seconds=duration_seconds,
                code_and_lock_hash=source_hash(),
                scope="PUBLIC_NATIVE_QUOTES_NOT_ECONOMIC_OPERATION",
                claim_status="NO_ECONOMIC_CLAIM",
            )
        )
        + "\n"
    )
    builder = LiveNode.builder("v8-market-observer", TraderId("V8-001"), Environment.LIVE)
    builder.add_data_client(
        "BINANCE",
        BinanceDataClientFactory(),
        BinanceDataClientConfig(
            product_type=BinanceProductType.USD_M,
            instrument_provider=BinanceInstrumentProviderConfig(load_ids=list(INSTRUMENTS)),
        ),
    )
    node = builder.build()
    with (
        (destination / "quotes.jsonl").open("x") as output,
        (destination / "observations.jsonl").open("x") as observation_output,
        (destination / "bars.jsonl").open("x") as bar_output,
    ):
        actor = QuoteRecorder(output)
        actor.stop_node = node.handle().stop
        actor.observations = observations
        actor.observation_output = observation_output
        actor.bar_output = bar_output
        node.add_actor(actor)

        async def stop_after() -> None:
            await asyncio.sleep(duration_seconds)
            node.handle().stop()

        stopper = asyncio.create_task(stop_after())
        try:
            await node.run_async()
            if actor.failure:
                raise ValueError(actor.failure)
            bar_output.flush()
            os.fsync(bar_output.fileno())
            output.flush()
            os.fsync(output.fileno())
            observation_output.flush()
            os.fsync(observation_output.fileno())
            with (destination / "quotes.jsonl").open("rb") as recorded:
                quotes_hash = hashlib.file_digest(recorded, "sha256").hexdigest()
            result = dict(
                quote_sha256=quotes_hash,
                bar_count=actor.bar_count,
                bar_sha256=hashlib.sha256((destination / "bars.jsonl").read_bytes()).hexdigest(),
                observation_sha256=hashlib.sha256(
                    (destination / "observations.jsonl").read_bytes()
                ).hexdigest(),
                session_sha256=hashlib.sha256(
                    (destination / "session.json").read_bytes()
                ).hexdigest(),
                quote_count=actor.count,
                ended_ns=time.time_ns(),
                status="OBSERVED" if actor.count else "NO_QUOTES_OBSERVED",
                claim_status="NO_ECONOMIC_CLAIM",
            )
            (destination / "result.json").write_text(canonical(result) + "\n")
            return result
        except Exception as error:
            (destination / "failure.json").write_text(
                canonical(
                    dict(
                        status="FAILED",
                        error_type=type(error).__name__,
                        callback_failure=actor.failure,
                        completed_quote_count=actor.count,
                        ended_ns=time.time_ns(),
                        claim_status="NO_ECONOMIC_CLAIM",
                    )
                )
                + "\n"
            )
            raise
        finally:
            stopper.cancel()
            await asyncio.gather(stopper, return_exceptions=True)
            node.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--duration-seconds", type=int, required=True)
    parser.add_argument("--warmup-manifest", type=Path, action="append", default=[])
    parser.add_argument("--grammar")
    parser.add_argument("--resume-from", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(
                capture_stream(
                    args.destination,
                    args.duration_seconds,
                    manifests=tuple(args.warmup_manifest),
                    grammar=args.grammar,
                    resume_from=args.resume_from,
                )
            )
        )
    )


if __name__ == "__main__":
    main()
