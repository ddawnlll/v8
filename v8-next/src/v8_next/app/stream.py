"""Native public Binance quote capture; no execution client or capital authority."""

import argparse
import asyncio
import json
import time
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
from nautilus_trader.model import InstrumentId, QuoteTick, TraderId

from v8_next.app.observe import source_hash
from v8_next.evaluation.store import canonical

INSTRUMENTS = ("BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE")


class QuoteRecorder(DataActor):
    def __init__(self, output: TextIO) -> None:
        super().__init__()
        self.output = output
        self.count = 0
        self.failure: str | None = None

    def on_start(self) -> None:
        for name in INSTRUMENTS:
            self.subscribe_quotes(InstrumentId.from_str(name))

    def on_quote(self, quote: QuoteTick) -> None:
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
        except Exception as error:
            self.failure = f"{type(error).__name__}: {error}"
            raise


async def capture_stream(destination: Path, duration_seconds: int) -> dict:
    if duration_seconds <= 0:
        raise ValueError("positive observation duration required")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "session.json").write_text(
        canonical(
            dict(
                instruments=INSTRUMENTS,
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
    with (destination / "quotes.jsonl").open("x") as output:
        actor = QuoteRecorder(output)
        node.add_actor(actor)

        async def stop_after() -> None:
            await asyncio.sleep(duration_seconds)
            node.handle().stop()

        stopper = asyncio.create_task(stop_after())
        try:
            await node.run_async()
            if actor.failure:
                raise ValueError(actor.failure)
            result = dict(
                quote_count=actor.count,
                ended_ns=time.time_ns(),
                status="OBSERVED" if actor.count else "NO_QUOTES_OBSERVED",
                claim_status="NO_ECONOMIC_CLAIM",
            )
            (destination / "result.json").write_text(canonical(result) + "\n")
            return result
        finally:
            stopper.cancel()
            await asyncio.gather(stopper, return_exceptions=True)
            node.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--duration-seconds", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(capture_stream(args.destination, args.duration_seconds))))


if __name__ == "__main__":
    main()
