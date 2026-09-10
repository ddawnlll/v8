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

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.common import LogLevel
from nautilus_trader.config import BacktestEngineConfig, LoggerConfig
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
from v8_next.adapters.execution_models import (
    DEFAULT_PROFILE,
    ExecutionProfile,
    profile_summary,
    resolve_profile,
    venue_kwargs,
)
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


def _native_fill_records(engine: BacktestEngine) -> tuple[list[dict[str, Any]], str]:
    """Normalise the engine's order-fills report into JSON-safe records.

    NautilusTrader 2.0.0rc4 returns the report as a table (``to_dicts`` /
    ``to_dict``) rather than a declared stub type, so the shape is probed at
    runtime and reported verbatim instead of being assumed.
    """
    try:
        report = engine.generate_order_fills_report()
    except Exception as exc:  # pragma: no cover - engine-level failure
        return [], f"UNAVAILABLE:{type(exc).__name__}"
    if report is None:
        return [], "NONE"
    records: list[dict[str, Any]] = []
    try:
        if hasattr(report, "to_dicts"):
            records = [dict(r) for r in report.to_dicts()]
        elif hasattr(report, "to_dict"):
            try:
                raw = report.to_dict("records")
                records = [dict(r) for r in raw]
            except TypeError:
                records = [dict(report.to_dict())]
        elif isinstance(report, (list, tuple)):
            records = [dict(r) for r in report if isinstance(r, dict)]
    except Exception:  # pragma: no cover - defensive
        return [], f"UNPARSABLE:{type(report).__name__}"
    safe: list[dict[str, Any]] = []
    for rec in records:
        safe.append({str(key): _json_safe(value) for key, value in rec.items()})
    return safe, type(report).__name__


#: Fill-report columns that carry execution semantics. The set is intersected
#: with the columns the engine actually emitted, so a Nautilus version that
#: renames a column cannot silently produce an all-identical signature.
SIGNATURE_COLUMNS = (
    "instrument_id",
    "side",
    "quantity",
    "filled_qty",
    "last_px",
    "avg_px",
    "slippage",
    "commissions",
    "liquidity_side",
    "position_id",
    "order_list_id",
    "venue_order_id",
    "trade_id",
    "ts_event",
    "ts_init",
    "ts_last",
)


def _fill_signature(records: list[dict[str, Any]]) -> str:
    """Identity of executed fills: instrument/side/qty/price/cost/time, sorted.

    Price, slippage and commission columns are part of the identity on purpose:
    a signature that ignores them cannot detect that two profiles filled at
    different prices, which is exactly what an execution claim depends on.
    """
    import hashlib as _hl
    import json as _js

    if not records:
        return _hl.sha256(b'{"columns":[],"rows":[]}').hexdigest()
    available = set(records[0])
    pick = [c for c in SIGNATURE_COLUMNS if c in available]
    if not pick:  # unknown schema: fall back to every column, still deterministic
        pick = sorted(available)
    rows = sorted(tuple(str(r.get(k, "")) for k in pick) for r in records)
    payload = _js.dumps({"columns": pick, "rows": rows}, sort_keys=True)
    return _hl.sha256(payload.encode()).hexdigest()


def _as_float(value: Any) -> float | None:
    """Convert a ledger/report value to a finite float, or None. Never guesses."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _json_safe(value: Any) -> Any:
    """JSON-safe scalar: pandas timestamps become epoch ns, non-finite floats None."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    if type(value).__name__ == "Timestamp" and hasattr(value, "value"):
        return int(value.value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def _money_amounts(value: Any) -> dict[str, float]:
    """Parse Nautilus money values into ``{currency: summed amount}``.

    The fills report carries commissions as ``["0.49407624 USDT"]``; custom fee
    models can surface ``Money(0.5, USDT)`` instead. Both are accepted, and
    amounts in different currencies are never summed together.
    """
    out: dict[str, float] = {}
    if value is None or isinstance(value, bool):
        return out
    if isinstance(value, (list, tuple)):
        for item in value:
            for currency, amount in _money_amounts(item).items():
                out[currency] = out.get(currency, 0.0) + amount
        return out
    if isinstance(value, (int, float)):
        if value != value:
            return out
        out[""] = float(value)
        return out
    text = str(value)
    for amount, currency in re.findall(r"([-+]?[0-9]*\.?[0-9]+)\s+([A-Za-z]{2,10})\b", text):
        try:
            parsed = float(amount)
        except ValueError:
            continue
        out[currency.upper()] = out.get(currency.upper(), 0.0) + parsed
    for amount, currency in re.findall(
        r"Money\(\s*([-+]?[0-9]*\.?[0-9]+)\s*,\s*([A-Za-z]{2,10})", text
    ):
        try:
            parsed = float(amount)
        except ValueError:
            continue
        out[currency.upper()] = out.get(currency.upper(), 0.0) + parsed
    return out


def _execution_telemetry(
    profile: ExecutionProfile,
    fill_records: list[dict[str, Any]],
    fill_report_type: str,
    opened: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure execution quality from fills versus the decision price.

    Implementation shortfall here is the signed cost of the fill against the
    close of the decision bar that authorised it: positive means the fill was
    adverse (paid above for a buy, sold below for a sell). Decision-to-fill
    latency is measured from the decision bar timestamp to the native
    position-open event, so a modeller's latency becomes visible instead of
    being invisible inside the engine.
    """
    # Decisions are matched per instrument: comparing a fill against the last
    # decision of a *different* leg compares BTC against AVAX and yields a
    # nonsense shortfall (observed as -2.4e6 bps before this was fixed).
    per_instrument: dict[str, list[tuple[int, Any]]] = {}
    for d in decisions:
        inst = str(d.get("instrument_id", ""))
        per_instrument.setdefault(inst, []).append(
            (int(d.get("decision_ns", 0) or 0), d.get("close"))
        )
    for rows in per_instrument.values():
        rows.sort(key=lambda r: r[0])

    slippage_bps: list[float] = []
    latencies: list[int] = []
    unmatched = 0
    for pos in opened:
        side = str(pos.get("side", "")).upper()
        fill_px = _as_float(pos.get("avg_px_open"))
        if fill_px is None or fill_px <= 0:
            unmatched += 1
            continue
        event_ns = int(pos.get("event_ns", 0) or 0)
        rows = per_instrument.get(str(pos.get("instrument_id", "")), [])
        prior = [r for r in rows if r[0] <= event_ns]
        if not prior:
            unmatched += 1
            continue
        ref_ns, ref_close = prior[-1]
        ref_px = _as_float(ref_close)
        if ref_px is not None and ref_px > 0:
            sign = 1.0 if side.startswith("B") else -1.0
            slippage_bps.append(sign * (fill_px - ref_px) / ref_px * 1e4)
        latencies.append(event_ns - ref_ns)

    commission_totals: dict[str, float] = {}
    for rec in fill_records:
        for key in rec:
            if "commission" in key.lower():
                for currency, amount in _money_amounts(rec[key]).items():
                    commission_totals[currency] = commission_totals.get(currency, 0.0) + amount

    # Order lifetime is directly observable from the engine's own fill rows
    # (ts_last - ts_init), unlike decision-to-event time which bar execution
    # stamps at the bar boundary.
    order_lifetime: list[int] = []
    for rec in fill_records:
        start, end = rec.get("ts_init"), rec.get("ts_last")
        if isinstance(start, int) and isinstance(end, int) and end >= start:
            order_lifetime.append(end - start)

    configured_latency = sum(
        (
            profile.base_latency_nanos,
            profile.insert_latency_nanos,
            profile.update_latency_nanos,
            profile.cancel_latency_nanos,
        )
    )
    block = profile_summary(profile)
    block.update(
        {
            "fill_signature": _fill_signature(fill_records),
            "fills_count": len(fill_records),
            "fills_report_type": fill_report_type,
            "slippage_samples": len(slippage_bps),
            "slippage_unmatched_positions": unmatched,
            "slippage_bps_mean": (
                round(sum(slippage_bps) / len(slippage_bps), 6) if slippage_bps else None
            ),
            "slippage_bps_max": round(max(slippage_bps), 6) if slippage_bps else None,
            "slippage_bps_min": round(min(slippage_bps), 6) if slippage_bps else None,
            "decision_to_position_event_ns_mean": (
                int(sum(latencies) / len(latencies)) if latencies else None
            ),
            "decision_to_position_event_ns_max": max(latencies) if latencies else None,
            "order_to_fill_ns_mean": (
                int(sum(order_lifetime) / len(order_lifetime)) if order_lifetime else None
            ),
            "order_to_fill_ns_max": max(order_lifetime) if order_lifetime else None,
            "configured_latency_nanos": configured_latency,
            "latency_observability": (
                "BAR_EXECUTION_STAMPS_FILLS_AT_BAR_TIME"
                if configured_latency > 0 and not any(latencies)
                else "MEASURED_ORDER_LIFETIME"
                if order_lifetime
                else "NOT_OBSERVABLE"
            ),
            "commission_totals_by_currency": {
                cur: round(amt, 10) for cur, amt in sorted(commission_totals.items())
            },
            "commission_total": (
                round(next(iter(commission_totals.values())), 10)
                if len(commission_totals) == 1
                else None
            ),
        }
    )
    return block


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
    funding_dropped: int = 0,
    execution_profile: str | ExecutionProfile = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Execute the portfolio through one shared Nautilus account.

    legs maps raw symbols (BTCUSDT) to chronological candles; instrument ids
    are derived as <RAW>-PERP.BINANCE.

    funding_dropped counts malformed funding records skipped at tape load
    (MultiTape.funding_dropped). It is reported in the result, never ignored:
    a zero-funding P&L with dropped records is flagged, not presented as
    fully-covered.
    """
    if not legs:
        raise ValueError("at least one instrument leg required")
    frac = sum(s.notional_fraction for s in sleeves)
    if abs(frac - 1.0) > 1e-9:
        raise ValueError(f"sleeve fractions must sum to 1.0, got {frac}")
    curr = Currency.from_str(currency)
    ven = Venue(venue)
    profile = resolve_profile(execution_profile)
    engine = BacktestEngine(
        BacktestEngineConfig(
            bypass_logging=True,
            logging=LoggerConfig(stdout_level=LogLevel.WARNING),
        )
    )
    try:
        # Execution semantics are explicit and digestible: fill model, fee model
        # and latency model all come from the named profile rather than from
        # engine defaults that were never written down.
        engine.add_venue(
            ven,
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money(float(initial_balance), curr)],
            default_leverage=Decimal(1),
            liquidation_enabled=False,
            **venue_kwargs(profile),
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
        out_of_window = 0
        unknown_leg = 0
        for row in funding:
            boundary = row.funding_time_ms * 1_000_000
            if not window_start <= boundary <= window_end:
                out_of_window += 1
                continue
            fund_iid = InstrumentId.from_str(f"{row.instrument}-PERP.BINANCE")
            leg = legs.get(row.instrument)
            if leg is None:
                unknown_leg += 1
                continue
            mark = next((float(c.close) for c in leg if c.end_ns >= boundary), None)
            if mark is None:
                unknown_leg += 1
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
        all_decisions: list[dict[str, Any]] = []
        for strat in strategies:
            opened.extend(strat.opened_positions)
            closed.extend(strat.closed_positions)
            # Tag each decision with its instrument: execution telemetry must
            # match a fill to the decision of the SAME leg, never to another
            # asset's price.
            all_decisions.extend(
                {**d, "instrument_id": str(strat.instrument_id)} for d in strat.decisions
            )

        fill_records, fill_report_type = _native_fill_records(engine)
        execution = _execution_telemetry(
            profile, fill_records, fill_report_type, opened, all_decisions
        )
        return {
            "legs": sorted(legs),
            "sleeves": [s.name for s in sleeves],
            "total_bars": sum(len(c) for c in legs.values()),
            "decisions_count": len(all_decisions),
            "opened_positions": opened,
            "closed_positions": closed,
            "account": account,
            "execution": execution,
            "fill_signature": _fill_signature(fill_records),
            "fill_records": fill_records,
            "funding_settlements_fed": settlements,
            "funding_rows_available": len(funding),
            # Coverage accounting: a zero-funding P&L must be distinguishable
            # from a fully-covered one. NO_FUNDING_ROWS is explicit (the
            # no-fund experimental arm or a tape without funding records);
            # DROPPED_RECORDS flags cost that never reached the engine.
            "funding_dropped_at_load": funding_dropped,
            "funding_out_of_window": out_of_window,
            "funding_unknown_leg": unknown_leg,
            "funding_coverage": (
                "NO_FUNDING_ROWS"
                if not funding
                else (
                    "DROPPED_RECORDS"
                    if (funding_dropped or unknown_leg)
                    else "FULL"
                )
            ),
        }
    finally:
        engine.dispose()
