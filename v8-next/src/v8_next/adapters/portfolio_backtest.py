"""Multi-asset portfolio backtest: one account, N instruments, real funding feed.

P and P+E both execute inside a single Nautilus MARGIN/NETTING account with
shared capital and margin. P attaches one incumbent ensemble per leg; P+E
attaches incumbent + challenger ensembles per leg with halved notionals, so
the total per-leg risk budget is identical and the comparison is engine-level,
never a summation of standalone P&Ls.

Funding settles natively: every in-window tape funding row becomes a
MarkPriceUpdate (mark = leg close at the boundary, labeled mark-proxy) plus a
FundingRateUpdate. Settlement counts and funding-paid reconciliation are
reported; rows outside the window are excluded, never extrapolated.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model import (
    AccountType,
    Bar,
    BarType,
    CryptoPerpetual,
    Currency,
    FundingRateUpdate,
    InstrumentId,
    MarkPriceUpdate,
    Money,
    OmsType,
    Price,
    Quantity,
    Symbol,
    Venue,
)

from v8_next.adapters.engine_state import economic_state
from v8_next.adapters.expert_strategy import ExpertEnsembleStrategy, ExpertStrategyConfig
from v8_next.domain.market import Candle
from v8_next.domain.positioning import PositioningReading
from v8_next.evaluation.multitape import FundingRow

BASE_CURRENCIES = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL", "AVAXUSDT": "AVAX"}


@dataclass(frozen=True)
class SleeveSpec:
    name: str  # incumbent | challenger
    quorum: int
    tolerance: int
    notional_fraction: float  # share of the per-leg notional budget


def _instrument(instrument_id: str, raw_symbol: str, base: str, currency: Currency,
                maker_fee: Decimal, taker_fee: Decimal) -> CryptoPerpetual:
    return CryptoPerpetual(
        instrument_id=InstrumentId.from_str(instrument_id),
        raw_symbol=Symbol(raw_symbol),
        base_currency=Currency.from_str(base),
        quote_currency=currency,
        settlement_currency=currency,
        is_inverse=False,
        price_precision=2,
        size_precision=3,
        price_increment=Price(0.01, 2),
        size_increment=Quantity(0.001, 3),
        min_quantity=Quantity(0.001, 3),
        max_quantity=Quantity(1000.0, 3),
        min_notional=Money(1, currency),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal("1"),
        margin_maint=Decimal("0.05"),
        maker_fee=maker_fee,
        taker_fee=taker_fee,
    )


def _bars(candles: tuple[Candle, ...], bar_type: BarType) -> list[Bar]:
    return [
        Bar(
            bar_type,
            Price(float(c.open), 2),
            Price(float(c.high), 2),
            Price(float(c.low), 2),
            Price(float(c.close), 2),
            Quantity(float(c.volume), 3),
            c.end_ns,
            c.end_ns,
        )
        for c in candles
    ]


def trade_signature(result: dict[str, Any]) -> str:
    """Identity of executed trades: instrument/side/qty/avg/time per open."""
    import hashlib as _hl
    import json as _js

    opens = sorted(
        (
            str(p.get("instrument_id", "")),
            str(p.get("side", "")),
            str(p.get("quantity", "")),
            str(p.get("avg_px_open", "")),
            int(p.get("event_ns", 0) or 0),
        )
        for p in result.get("opened_positions", [])
        if isinstance(p, dict)
    )
    return _hl.sha256(_js.dumps(opens).encode()).hexdigest()


def run_portfolio_backtest(
    legs: dict[str, tuple[Candle, ...]],
    sleeves: tuple[SleeveSpec, ...],
    funding: tuple[FundingRow, ...] = (),
    *,
    per_leg_notional: Decimal = Decimal("1000"),
    maker_fee: Decimal = Decimal("0.0002"),
    taker_fee: Decimal = Decimal("0.0005"),
    initial_balance: Decimal = Decimal("10000"),
    venue: str = "BINANCE",
    currency: str = "USDT",
    bracket_stop_pct: Decimal | None = Decimal("0.02"),
    bracket_target_pct: Decimal | None = Decimal("0.04"),
    readings: tuple[PositioningReading, ...] = (),
) -> dict[str, Any]:
    """Execute the portfolio through one shared Nautilus account.

    legs maps raw symbols (BTCUSDT) to chronological candles; instrument ids
    are derived as <RAW>-PERP.BINANCE.
    """
    if not legs:
        raise ValueError("at least one instrument leg required")
    frac = sum(s.notional_fraction for s in sleeves)
    if abs(frac - 1.0) > 1e-9:
        raise ValueError(f"sleeve fractions must sum to 1.0, got {frac}")
    curr = Currency.from_str(currency)
    ven = Venue(venue)
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True))
    try:
        engine.add_venue(
            ven,
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money(float(initial_balance), curr)],
            default_leverage=Decimal(1),
            liquidation_enabled=False,
        )
        strategies: list[ExpertEnsembleStrategy] = []
        window_start = min(c[0].end_ns for c in legs.values())
        window_end = max(c[-1].end_ns for c in legs.values())
        for raw, candles in legs.items():
            instrument_id = f"{raw}-PERP.BINANCE"
            base = BASE_CURRENCIES.get(raw, "BTC")
            engine.add_instrument(
                _instrument(instrument_id, raw, base, curr, maker_fee, taker_fee)
            )
            bar_type = BarType.from_str(f"{instrument_id}-1-HOUR-LAST-EXTERNAL")
            engine.add_data(_bars(candles, bar_type))
            source_map = {c.end_ns: c for c in candles}
            for sleeve in sleeves:
                cfg = ExpertStrategyConfig(
                    instrument_id=instrument_id,
                    bar_type_str=str(bar_type),
                    min_support_quorum=sleeve.quorum,
                    max_contradiction_tolerance=sleeve.tolerance,
                    target_notional=per_leg_notional * Decimal(str(sleeve.notional_fraction)),
                    bracket_stop_pct=bracket_stop_pct,
                    bracket_target_pct=bracket_target_pct,
                    max_concurrent_positions=1,
                )
                strat = ExpertEnsembleStrategy(cfg, source_candles=source_map, readings=readings)
                strategies.append(strat)
                engine.add_strategy(strat)

        settlements = 0
        for row in funding:
            boundary = row.funding_time_ms * 1_000_000
            if not window_start <= boundary <= window_end:
                continue
            fund_iid = InstrumentId.from_str(f"{row.instrument}-PERP.BINANCE")
            leg = legs.get(row.instrument)
            if leg is None:
                continue
            mark = next((float(c.close) for c in leg if c.end_ns >= boundary), None)
            if mark is None:
                continue
            engine.add_data([MarkPriceUpdate(fund_iid, Price(mark, 2), boundary, boundary)])
            engine.add_data([
                FundingRateUpdate(
                    fund_iid, row.funding_rate, boundary, boundary,
                    next_funding_ns=boundary,
                )
            ])
            settlements += 1

        engine.run()
        account = economic_state(engine, ven, curr)
        opened: list[dict[str, Any]] = []
        closed: list[dict[str, Any]] = []
        decisions = 0
        for strat in strategies:
            opened.extend(strat.opened_positions)
            closed.extend(strat.closed_positions)
            decisions += len(strat.decisions)
        return {
            "legs": sorted(legs),
            "sleeves": [s.name for s in sleeves],
            "total_bars": sum(len(c) for c in legs.values()),
            "decisions_count": decisions,
            "opened_positions": opened,
            "closed_positions": closed,
            "account": account,
            "funding_settlements_fed": settlements,
            "funding_rows_available": len(funding),
        }
    finally:
        engine.dispose()
