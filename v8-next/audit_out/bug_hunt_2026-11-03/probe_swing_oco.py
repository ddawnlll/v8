#!/usr/bin/env python
"""MECHANICS ONLY probe for the swing-adapter OCO/reduce-only chain.

Synthetic bars; no economic assertion. It reproduces the engine-facing semantics
the swing adapter relies on:

1. ``on_order_filled`` runs BEFORE ``on_position_opened``, so the adapter's
   ``active_position_id`` is still None when it submits bracket legs.
2. ``Strategy.cancel_order(order)`` raises TypeError (it wants a ClientOrderId);
   NautilusTrader swallows callback exceptions, so the sibling leg stays live.
3. Both legs filling + non-reduce-only turns the stale leg into an opposite
   position the adapter never tracks.

Run: uv run --project v8-next python v8-next/audit_out/bug_hunt_2026-11-03/probe_swing_oco.py
"""

from __future__ import annotations

import json
from decimal import Decimal

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model import (
    AccountType,
    Bar,
    BarType,
    CryptoPerpetual,
    Currency,
    InstrumentId,
    Money,
    OmsType,
    OrderSide,
    Price,
    Quantity,
    Symbol,
    Venue,
)
from nautilus_trader.trading import Strategy, StrategyConfig

H = 3_600_000_000_000
USDT = Currency.from_str("USDT")
IID = InstrumentId(Symbol("BTCUSDT-PERP"), Venue("BINANCE"))
BAR_TYPE = BarType.from_str(f"{IID}-1-HOUR-LAST-EXTERNAL")


def instrument() -> CryptoPerpetual:
    return CryptoPerpetual(
        instrument_id=IID,
        raw_symbol=Symbol("BTCUSDT"),
        base_currency=Currency.from_str("BTC"),
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=2,
        size_precision=3,
        price_increment=Price(0.01, 2),
        size_increment=Quantity(0.001, 3),
        min_quantity=Quantity(0.001, 3),
        max_quantity=Quantity(100, 3),
        min_notional=Money(1, USDT),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal("1"),
        margin_maint=Decimal("0.05"),
        maker_fee=Decimal("0"),
        taker_fee=Decimal("0"),
    )


class Probe(Strategy):
    def __init__(self, config: StrategyConfig | None = None) -> None:
        super().__init__(config or StrategyConfig())
        self.seq: list[list[str]] = []
        self.entry_sent = False
        self.bracket_sent = False
        self.stop_id = None
        self.target_id = None

    def on_start(self) -> None:
        self.subscribe_bars(BAR_TYPE)

    def on_bar(self, bar: Bar) -> None:
        if self.entry_sent:
            return
        self.entry_sent = True
        self.submit_order(
            self.order_factory.market(
                instrument_id=IID, order_side=OrderSide.BUY, quantity=Quantity(1, 3)
            )
        )

    def on_order_filled(self, event) -> None:  # noqa: ANN001
        cid = str(event.client_order_id)
        self.seq.append(["filled", cid, str(event.last_px)])
        if not self.bracket_sent:
            self.bracket_sent = True
            # Exactly the adapter's situation: PositionOpened has not run yet.
            pid = self.cache.positions_open(instrument_id=IID)
            self.seq.append(["positions_open_at_entry_fill", str(len(pid))])
            stop = self.order_factory.stop_market(
                instrument_id=IID,
                order_side=OrderSide.SELL,
                quantity=Quantity(1, 3),
                trigger_price=Price(95, 2),
            )
            target = self.order_factory.limit(
                instrument_id=IID,
                order_side=OrderSide.SELL,
                quantity=Quantity(1, 3),
                price=Price(105, 2),
            )
            self.stop_id = str(stop.client_order_id)
            self.target_id = str(target.client_order_id)
            self.submit_order(stop)
            self.submit_order(target)
            self.seq.append(
                [
                    "bracket_submitted",
                    str(stop.position_id),
                    str(target.position_id),
                    str(stop.is_reduce_only),
                    str(target.is_reduce_only),
                ]
            )
        elif cid == self.stop_id:
            # The adapter does this: pass the Order object, not a ClientOrderId.
            orders = list(self.cache.orders_open(instrument_id=IID))
            target_order = next(
                (o for o in orders if str(o.client_order_id) == self.target_id), None
            )
            try:
                assert target_order is not None
                self.cancel_order(target_order)
                self.seq.append(["cancel_order_returned", str(self.target_id)])
            except Exception as error:  # noqa: BLE001 - the finding is the exception
                self.seq.append(["cancel_order_raised", type(error).__name__, str(error)])

    def on_position_opened(self, event) -> None:  # noqa: ANN001
        self.seq.append(["position_opened", str(event.position_id)])

    def on_position_closed(self, event) -> None:  # noqa: ANN001
        self.seq.append(["position_closed", str(event.position_id)])


def bar(open_: int, high: int, low: int, close: int, hour: int) -> Bar:
    return Bar(
        BAR_TYPE,
        Price(open_, 2),
        Price(high, 2),
        Price(low, 2),
        Price(close, 2),
        Quantity(100, 3),
        hour * H,
        hour * H,
    )


def main() -> None:
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True))
    try:
        engine.add_venue(
            Venue("BINANCE"),
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money(100_000, USDT)],
            default_leverage=Decimal(1),
        )
        engine.add_instrument(instrument())
        strategy = Probe()
        engine.add_strategy(strategy)
        engine.add_data(
            [
                bar(100, 100, 100, 100, 1),
                bar(100, 101, 99, 100, 2),   # entry fills
                bar(100, 101, 90, 95, 3),    # stop triggers; cancel is attempted
                bar(100, 110, 100, 105, 4),  # stale target fills
                bar(100, 100, 100, 100, 5),
            ]
        )
        engine.run()
        positions = [
            {"side": str(p.side), "quantity": str(p.quantity), "avg_px": str(p.avg_px_open)}
            for p in engine.cache.positions()
            if not p.is_closed
        ]
        print(
            json.dumps(
                {
                    "event_sequence": strategy.seq,
                    "open_positions_at_end": positions,
                    "result": (
                        "FAIL"
                        if any(p["side"] == "SHORT" for p in positions)
                        else "PASS"
                    ),
                },
                indent=2,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
