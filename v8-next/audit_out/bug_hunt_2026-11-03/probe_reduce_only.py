#!/usr/bin/env python
"""MECHANICS ONLY: does `submit_order(..., position_id=pid)` make an order reduce-only?

The swing adapter's comment says submitting the bracket "against the open position"
means "the legs can only reduce it". This probe submits the protection order after
`PositionOpened`, with the position id supplied, and reads the resulting order.
It then submits a second order built with `reduce_only=True` as the control.
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


def make_instrument() -> CryptoPerpetual:
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
        self.ids: list[str] = []
        self.sent = False

    def on_start(self) -> None:
        self.subscribe_bars(BAR_TYPE)

    def on_bar(self, bar: Bar) -> None:
        if self.sent:
            return
        self.sent = True
        self.submit_order(
            self.order_factory.market(
                instrument_id=IID, order_side=OrderSide.BUY, quantity=Quantity(1, 3)
            )
        )

    def on_position_opened(self, event) -> None:  # noqa: ANN001
        pid = event.position_id
        with_pid = self.order_factory.stop_market(
            instrument_id=IID,
            order_side=OrderSide.SELL,
            quantity=Quantity(1, 3),
            trigger_price=Price(90, 2),
        )
        control = self.order_factory.stop_market(
            instrument_id=IID,
            order_side=OrderSide.SELL,
            quantity=Quantity(1, 3),
            trigger_price=Price(80, 2),
            reduce_only=True,
        )
        self.submit_order(with_pid, position_id=pid)
        self.submit_order(control, position_id=pid)
        self.ids = [str(with_pid.client_order_id), str(control.client_order_id)]


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
        engine.add_instrument(make_instrument())
        strategy = Probe()
        engine.add_strategy(strategy)
        engine.add_data(
            [
                Bar(BAR_TYPE, *(Price(100, 2),) * 4, Quantity(100, 3), h * H, h * H)
                for h in (1, 2, 3)
            ]
        )
        engine.run()
        rows = []
        for client_id in strategy.ids:
            order = engine.cache.order(__import__("nautilus_trader").model.ClientOrderId(client_id))
            rows.append(
                {
                    "client_order_id": client_id,
                    "position_id": str(order.position_id) if order.position_id else None,
                    "is_reduce_only": bool(order.is_reduce_only),
                }
            )
        print(json.dumps({"orders": rows}, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
