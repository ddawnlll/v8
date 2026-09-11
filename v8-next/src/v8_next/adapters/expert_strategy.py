"""Native NautilusTrader Strategy adapter for the canonical 28-expert ensemble.

Epistemic & Execution Demarcation (matching V8_NEXT_IMPLEMENTATION_SCOPE.md):
- Python owns opportunity identity, the 28 expert witness stances, and consensus gating.
- NautilusTrader owns generic bar dispatch, order lifecycle, order lists, positions,
  margin accounting, and fee/funding settlement.
- No custom simulator or manual scheduling loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
    InstrumentId,
    Money,
    OmsType,
    OrderSide,
    OrderType,
    Price,
    Quantity,
    Symbol,
    Venue,
)
from nautilus_trader.trading import Strategy

from v8_next.adapters.engine_state import economic_state
from v8_next.adapters.execution_models import (
    ExecutionProfile,
    resolve_profile,
    venue_kwargs,
)
from v8_next.adapters.execution_telemetry import (
    execution_telemetry,
    fill_signature,
    native_fill_records,
)
from v8_next.domain.market import Candle, CausalFrame, build_candle_dataframe, frame_at
from v8_next.domain.positioning import PositioningReading
from v8_next.economics.decisions import Opportunity, StanceKind, opportunity_at
from v8_next.economics.grammar import grammar_opportunity
from v8_next.experts.registry import observe_all_28
from v8_next.opportunities.book import OpportunityBook
from v8_next.opportunities.exposure import ExposureResolver
from v8_next.opportunities.models import (
    ExposureDirection,
    OpportunityRecord,
    OpportunityStatus,
)

_FIXED_AGGREGATION_NS = {
    "SECOND": 1_000_000_000,
    "MINUTE": 60_000_000_000,
    "HOUR": 3_600_000_000_000,
    "DAY": 86_400_000_000_000,
    "WEEK": 604_800_000_000_000,
}


def _bar_duration_ns(bar: Bar) -> int:
    """Derive a bar's duration from its own BarType; never assume 1h.

    Raises on non-fixed aggregations (e.g. MONTH, tick-based) instead of
    guessing start_ns, which would silently corrupt causal alignment.
    """
    spec = bar.bar_type.spec  # BarSpecification(step, aggregation, price_type)
    agg = getattr(spec.aggregation, "name", str(spec.aggregation))
    name = str(agg).split(".")[-1].upper()
    step = int(spec.step)
    if name not in _FIXED_AGGREGATION_NS or step <= 0:
        raise ValueError(f"non-fixed bar aggregation {agg!r}; refusing to guess start_ns")
    return step * _FIXED_AGGREGATION_NS[name]


@dataclass(frozen=True)
class ExpertStrategyConfig:
    """Execution parameters and consensus gates for the 28-expert ensemble strategy."""

    instrument_id: str = "BTCUSDT-PERP.BINANCE"
    bar_type_str: str = "BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"
    grammar_policy: str = "range-breakout-48-v1"
    min_support_quorum: int = 1
    max_contradiction_tolerance: int = 0
    order_quantity: Decimal = Decimal("0.01")
    target_notional: Decimal | None = None
    #: Entry order type for new positions: MARKET or LIMIT (at the decision
    #: close). LIMIT rests in the book and fills only when touched, so it is
    #: the passive path; MARKET crosses immediately. Anything else fails closed
    #: at config validation instead of silently becoming a market order.
    entry_order_type: str = "MARKET"
    #: Child-order execution algorithm for entries: NONE sends the full size at
    #: once; TWAP splits the parent quantity into twap_slices equal children
    #: submitted on consecutive bars. NONE keeps the previous path byte-identical.
    execution_algo: str = "NONE"
    twap_slices: int = 4
    #: Fraction of account equity risked per trade (FixedRiskSizer). When set,
    #: quantity comes from entry/stop distance instead of target_notional.
    #: None keeps the previous sizing path byte-identical.
    risk_fraction: Decimal | None = None
    #: Hard per-order notional cap (RiskEngineConfig.max_notional_per_order
    #: equivalent). Orders above it are denied pre-submit and counted. None
    #: means no guard configured.
    max_notional_per_order: Decimal | None = None
    bracket_stop_pct: Decimal | None = None
    bracket_target_pct: Decimal | None = None
    max_concurrent_positions: int = 1


class ExpertEnsembleStrategy(Strategy):
    """NautilusTrader Strategy powered by the canonical 28-expert witness ensemble.

    On every native Bar tick:
    1. Updates the causal prefix and builds a continuous PIT CausalFrame.
    2. Identifies opportunities via the configured grammar.
    3. Invokes observe_all_28() across all 28 canonical active witnesses.
    4. Evaluates consensus (support quorum vs contradiction tolerance).
    5. Dispatches native orders via NautilusTrader's OrderFactory when admitted.
    6. Retains full decision and stance ledgers for post-run audit.
    """

    def __new__(cls, *args: object, **kwargs: object) -> ExpertEnsembleStrategy:
        return super().__new__(cls)

    def __init__(
        self,
        config: ExpertStrategyConfig | None = None,
        *,
        source_candles: dict[int, Candle] | None = None,
        readings: tuple[PositioningReading, ...] = (),
    ) -> None:
        super().__init__()
        self.ensemble_config = config or ExpertStrategyConfig()
        self.instrument_id = InstrumentId.from_str(self.ensemble_config.instrument_id)
        self.bar_type = BarType.from_str(self.ensemble_config.bar_type_str)
        self.source_candles = source_candles or {}
        ordered_source = tuple(sorted(self.source_candles.values(), key=lambda c: c.end_ns))
        self._ordered_source = ordered_source
        self._source_prefix_df = build_candle_dataframe(ordered_source) if ordered_source else None
        self.readings = readings

        # Opportunity book & exposure resolver
        self.opportunity_book = OpportunityBook()
        self.exposure_resolver = ExposureResolver()

        # Internal state & diagnostic ledgers
        self.candles: list[Candle] = []
        self.decisions: list[dict[str, Any]] = []
        self.order_events: list[dict[str, Any]] = []
        self.opened_positions: list[dict[str, Any]] = []
        self.closed_positions: list[dict[str, Any]] = []
        # Pending TWAP child slices: dicts with side/quantity/bracket/prices.
        self.pending_twap: list[dict[str, Any]] = []

    def on_start(self) -> None:
        """Subscribe to configured bar type on strategy start."""
        self.subscribe_bars(self.bar_type)

    def _account_equity(self, instrument: Any) -> Any | None:
        """Quote-currency account equity, or None when it cannot be read.

        Never guesses: a missing portfolio/account/balance keeps the caller
        failing closed instead of sizing against an assumed balance.
        """
        try:
            portfolio = self.portfolio
            account = portfolio.account() if portfolio is not None else None
            if account is None:
                return None
            quote = getattr(instrument, "quote_currency", None)
            balance = account.balance(quote) if quote is not None else None
            if balance is None:
                balances = account.balances()
                balance = next(iter(balances.values()), None) if balances else None
            if balance is None:
                return None
            return balance.total
        except Exception:
            return None

    def _twap_slices(self, quantity: Decimal, step: Decimal, n: int) -> list[Decimal]:
        """Split a parent quantity into n step-aligned child slices.

        First n-1 slices are floored to the step; the last takes the remainder
        so the children always sum back to the parent.
        """
        if n <= 1 or step <= 0 or quantity <= 0:
            return [quantity]
        child = (quantity / n // step) * step
        slices = [child] * (n - 1)
        slices.append(quantity - sum(slices))
        return [s for s in slices if s > 0]

    def _drain_twap_slice(self, instrument: Any, record: Any) -> str | None:
        """Submit one pending TWAP child; return its action or None."""
        if not self.pending_twap or self.ensemble_config.execution_algo != "TWAP":
            return None
        sl = self.pending_twap.pop(0)
        qty = Quantity.from_str(format(sl["quantity"], f".{instrument.size_precision}f"))
        if sl["bracket"]:
            order_list = self.order_factory.bracket(
                instrument_id=self.instrument_id,
                order_side=sl["side"],
                quantity=qty,
                entry_order_type=sl["entry_order_type"],
                entry_price=sl.get("entry_price"),
                sl_trigger_price=sl["sl_price"],
                tp_price=sl["tp_price"],
            )
            self.submit_order_list(order_list)
        elif sl["entry_order_type"] == OrderType.LIMIT:
            self.submit_order(
                self.order_factory.limit(
                    instrument_id=self.instrument_id,
                    order_side=sl["side"],
                    quantity=qty,
                    price=sl["entry_price"],
                )
            )
        else:
            self.submit_order(
                self.order_factory.market(
                    instrument_id=self.instrument_id,
                    order_side=sl["side"],
                    quantity=qty,
                )
            )
        if record is not None:
            self.opportunity_book.update_status(
                record.opportunity_id, OpportunityStatus.ADMITTED
            )
        return f"TWAP_CHILD_{sl['done']}/{sl['total']}"

    def on_bar(self, bar: Bar) -> None:
        """Process incoming native Bar tick through the 28-expert ensemble."""
        # 1. Obtain or construct causal Candle
        use_prefix = False
        if bar.ts_event in self.source_candles:
            candle = self.source_candles[bar.ts_event]
            # Positional guard: the prefix cache is only valid while the live
            # sequence is exactly the ordered source (identity + position).
            # Any deviation (gap, reorder, duplicate) falls back to frame_at.
            if (
                self._source_prefix_df is not None
                and len(self.candles) < len(self._ordered_source)
                and self._ordered_source[len(self.candles)] is candle
            ):
                use_prefix = True
        else:
            duration_ns = _bar_duration_ns(bar)
            start_ns = bar.ts_event - duration_ns if bar.ts_event >= duration_ns else 0
            candle = Candle(
                instrument_id=str(self.instrument_id),
                start_ns=start_ns,
                end_ns=bar.ts_event,
                open=bar.open.as_decimal(),
                high=bar.high.as_decimal(),
                low=bar.low.as_decimal(),
                close=bar.close.as_decimal(),
                volume=bar.volume.as_decimal(),
                received_ns=bar.ts_init,
                available_ns=bar.ts_init,
                source_hash="nautilus-bar-feed",
            )
        self.candles.append(candle)

        # 2. Advance OpportunityBook with newly closed candle (invalidation & TTL check)
        self.opportunity_book.on_candle(candle)

        # 3. Build CausalFrame
        if use_prefix:
            frame = CausalFrame.from_ordered_prefix(
                str(self.instrument_id), bar.ts_init, tuple(self.candles), self._source_prefix_df
            )
        else:
            frame = frame_at(str(self.instrument_id), bar.ts_init, tuple(self.candles))

        # 4. Detect Opportunity
        opportunity: Opportunity | None
        if self.ensemble_config.grammar_policy == "range-breakout-48-v1":
            opportunity = opportunity_at(frame)
        else:
            opportunity = grammar_opportunity(frame, self.ensemble_config.grammar_policy)

        # 5. Record into OpportunityBook if newly detected
        record: OpportunityRecord | None = None
        if opportunity is not None:
            dir_enum = (
                ExposureDirection.LONG
                if opportunity.direction == "LONG"
                else ExposureDirection.SHORT
            )
            raw_sym = str(self.instrument_id).split(".")[0].replace("-PERP", "")
            venue_str = "binance-um"
            try:
                exposure = self.exposure_resolver.resolve_ticker(raw_sym, venue_str, dir_enum)
            except Exception:
                from v8_next.opportunities.models import EconomicExposureStructure
                exposure = EconomicExposureStructure.single_perp(
                    raw_sym, raw_sym.replace("USDT", ""), venue_str, "USDT", dir_enum
                )

            entry_px = bar.close.as_decimal()
            stop_px: Decimal | None = None
            target_px: Decimal | None = None
            if self.ensemble_config.bracket_stop_pct is not None:
                stop_dist = entry_px * self.ensemble_config.bracket_stop_pct
                stop_px = entry_px - stop_dist if dir_enum == ExposureDirection.LONG else entry_px + stop_dist
            if self.ensemble_config.bracket_target_pct is not None:
                target_dist = entry_px * self.ensemble_config.bracket_target_pct
                target_px = entry_px + target_dist if dir_enum == ExposureDirection.LONG else entry_px - target_dist

            record = OpportunityRecord.create(
                exposure=exposure,
                instrument_id=str(self.instrument_id),
                direction=dir_enum,
                entry_price=entry_px,
                stop_price=stop_px,
                target_price=target_px,
                as_of_time_ns=candle.end_ns,
                valid_until_ns=opportunity.expires_ns,
                status=OpportunityStatus.CANDIDATE,
            )
            self.opportunity_book.insert(record)

        # 6. Invoke all 28 canonical active witnesses
        stances = observe_all_28(frame, opportunity, readings=self.readings)
        supports = [s for s in stances if s.kind == StanceKind.SUPPORT]
        contradicts = [s for s in stances if s.kind == StanceKind.CONTRADICT]
        abstains = [s for s in stances if s.kind == StanceKind.ABSTAIN]

        # 7. Evaluate Consensus & Admission
        is_supported = (
            opportunity is not None
            and len(supports) >= self.ensemble_config.min_support_quorum
            and len(contradicts) <= self.ensemble_config.max_contradiction_tolerance
        )
        if record is not None and is_supported:
            self.opportunity_book.update_status(record.opportunity_id, OpportunityStatus.CONFIRMED)

        # 6. Execute Native Orders via NautilusTrader OrderFactory
        action = "NO_ACTION"
        sizing_mode = "FLAT"
        # Drain one pending TWAP child even when this bar carries no supported
        # opportunity: children continue a scheduled parent. A drained bar emits
        # only the child (parent gate below is skipped for it).
        twap_action = None
        if self.ensemble_config.execution_algo == "TWAP" and self.pending_twap:
            drain_instrument = self.cache.instrument(self.instrument_id)
            if drain_instrument is not None:
                twap_action = self._drain_twap_slice(drain_instrument, record)
        if twap_action is not None:
            action = twap_action
            sizing_mode = "TWAP"
        if is_supported and opportunity is not None and twap_action is None:
            open_positions = [
                p
                for p in self.cache.positions_open()
                if p.instrument_id == self.instrument_id and not p.is_closed
            ]
            open_orders = [
                o
                for o in self.cache.orders_open()
                if o.instrument_id == self.instrument_id and not o.is_closed
            ]

            if len(open_positions) < self.ensemble_config.max_concurrent_positions and not open_orders:
                instrument = self.cache.instrument(self.instrument_id)
                if instrument is not None:
                    side = OrderSide.BUY if opportunity.direction == "LONG" else OrderSide.SELL
                    base_qty = self.ensemble_config.order_quantity
                    if self.ensemble_config.target_notional is not None:
                        px = bar.close.as_decimal()
                        step = instrument.size_increment.as_decimal()
                        if px > 0 and step > 0:
                            steps = (self.ensemble_config.target_notional / px) // step
                            base_qty = steps * step
                    sizing_mode = "FLAT"
                    if self.ensemble_config.risk_fraction is not None:
                        # Risk-fraction sizing (FixedRiskSizer): quantity from
                        # entry/stop distance and account equity. Fail closed
                        # when the stop distance or the equity is unavailable.
                        from v8_next.adapters.risk_sizing import risk_sized_quantity

                        sizing_mode = "RISK_FRACTION"
                        stop_pct = self.ensemble_config.bracket_stop_pct
                        entry_px = bar.close.as_decimal()
                        equity = self._account_equity(instrument)
                        if stop_pct is None or entry_px <= 0 or equity is None:
                            action = "RISK_SIZING_NO_STOP_OR_EQUITY"
                            base_qty = Decimal(0)
                        else:
                            stop_dist = entry_px * stop_pct
                            stop_px = (
                                entry_px - stop_dist
                                if opportunity.direction == "LONG"
                                else entry_px + stop_dist
                            )
                            base_qty = risk_sized_quantity(
                                instrument,
                                Price(float(entry_px), instrument.price_precision),
                                Price(float(stop_px), instrument.price_precision),
                                equity,
                                self.ensemble_config.risk_fraction,
                            ).as_decimal()
                    if (
                        base_qty > 0
                        and self.ensemble_config.max_notional_per_order is not None
                    ):
                        from v8_next.adapters.risk_sizing import check_max_notional

                        allowed, _notional = check_max_notional(
                            base_qty,
                            bar.close,
                            self.ensemble_config.max_notional_per_order,
                        )
                        if not allowed:
                            action = "DENIED_MAX_NOTIONAL"
                            base_qty = Decimal(0)
                    qty_str = format(base_qty, f".{instrument.size_precision}f")
                    quantity: Quantity | None = None
                    if Decimal(qty_str) < instrument.min_quantity.as_decimal():
                        action = "BELOW_MIN_QUANTITY"
                    else:
                        quantity = Quantity.from_str(qty_str)

                    # Determine if bracket protection order list is configured
                    if quantity is None:
                        pass
                    elif (
                        self.ensemble_config.bracket_stop_pct is not None
                        and self.ensemble_config.bracket_target_pct is not None
                    ):
                        entry_px = bar.close.as_decimal()
                        stop_dist = entry_px * self.ensemble_config.bracket_stop_pct
                        target_dist = entry_px * self.ensemble_config.bracket_target_pct
                        if opportunity.direction == "LONG":
                            stop_px = entry_px - stop_dist
                            target_px = entry_px + target_dist
                        else:
                            stop_px = entry_px + stop_dist
                            target_px = entry_px - target_dist

                        sl_price = Price(float(stop_px), instrument.price_precision)
                        tp_price = Price(float(target_px), instrument.price_precision)

                        entry_type = self.ensemble_config.entry_order_type
                        if entry_type == "MARKET":
                            entry_order_type = OrderType.MARKET
                            entry_limit_price = None
                        elif entry_type == "LIMIT":
                            entry_order_type = OrderType.LIMIT
                            entry_limit_price = Price(
                                float(entry_px), instrument.price_precision
                            )
                        else:
                            action = f"REJECTED_UNKNOWN_ENTRY_TYPE_{entry_type}"
                            entry_order_type = None
                            entry_limit_price = None
                        if entry_order_type is None:
                            quantity = None
                        else:
                            submit_qty = quantity
                            twap_tag = ""
                            if (
                                self.ensemble_config.execution_algo == "TWAP"
                                and quantity is not None
                            ):
                                slices = self._twap_slices(
                                    quantity.as_decimal(),
                                    instrument.size_increment.as_decimal(),
                                    self.ensemble_config.twap_slices,
                                )
                                if len(slices) > 1:
                                    submit_qty = Quantity.from_str(
                                        format(slices[0], f".{instrument.size_precision}f")
                                    )
                                    for idx, s in enumerate(slices[1:], start=2):
                                        self.pending_twap.append(
                                            {
                                                "side": side,
                                                "quantity": s,
                                                "bracket": True,
                                                "entry_order_type": entry_order_type,
                                                "entry_price": entry_limit_price,
                                                "sl_price": sl_price,
                                                "tp_price": tp_price,
                                                "done": idx,
                                                "total": len(slices),
                                            }
                                        )
                                    twap_tag = f"TWAP_PARENT_1/{len(slices)}_"
                            order_list = self.order_factory.bracket(
                                instrument_id=self.instrument_id,
                                order_side=side,
                                quantity=submit_qty,
                                entry_order_type=entry_order_type,
                                entry_price=entry_limit_price,
                                sl_trigger_price=sl_price,
                                tp_price=tp_price,
                            )
                            self.submit_order_list(order_list)
                            if record is not None:
                                self.opportunity_book.update_status(record.opportunity_id, OpportunityStatus.ADMITTED)
                            action = f"{twap_tag}SUBMITTED_BRACKET_{entry_type}_{side.name}_{qty_str}"
                    else:
                        entry_type = self.ensemble_config.entry_order_type
                        if entry_type == "LIMIT":
                            order = self.order_factory.limit(
                                instrument_id=self.instrument_id,
                                order_side=side,
                                quantity=quantity,
                                price=Price(float(bar.close.as_decimal()), instrument.price_precision),
                            )
                        elif entry_type == "MARKET":
                            order = self.order_factory.market(
                                instrument_id=self.instrument_id,
                                order_side=side,
                                quantity=quantity,
                            )
                        else:
                            order = None
                            action = f"REJECTED_UNKNOWN_ENTRY_TYPE_{entry_type}"
                        if order is not None:
                            submit_order = order
                            twap_tag = ""
                            if self.ensemble_config.execution_algo == "TWAP":
                                slices = self._twap_slices(
                                    quantity.as_decimal(),
                                    instrument.size_increment.as_decimal(),
                                    self.ensemble_config.twap_slices,
                                )
                                if len(slices) > 1:
                                    if entry_type == "LIMIT":
                                        submit_order = self.order_factory.limit(
                                            instrument_id=self.instrument_id,
                                            order_side=side,
                                            quantity=Quantity.from_str(
                                                format(slices[0], f".{instrument.size_precision}f")
                                            ),
                                            price=Price(float(bar.close.as_decimal()), instrument.price_precision),
                                        )
                                    else:
                                        submit_order = self.order_factory.market(
                                            instrument_id=self.instrument_id,
                                            order_side=side,
                                            quantity=Quantity.from_str(
                                                format(slices[0], f".{instrument.size_precision}f")
                                            ),
                                        )
                                    for idx, s in enumerate(slices[1:], start=2):
                                        self.pending_twap.append(
                                            {
                                                "side": side,
                                                "quantity": s,
                                                "bracket": False,
                                                "entry_order_type": (
                                                    OrderType.LIMIT if entry_type == "LIMIT" else OrderType.MARKET
                                                ),
                                                "entry_price": (
                                                    Price(float(bar.close.as_decimal()), instrument.price_precision)
                                                    if entry_type == "LIMIT"
                                                    else None
                                                ),
                                                "sl_price": None,
                                                "tp_price": None,
                                                "done": idx,
                                                "total": len(slices),
                                            }
                                        )
                                    twap_tag = f"TWAP_PARENT_1/{len(slices)}_"
                            self.submit_order(submit_order)
                            if record is not None:
                                self.opportunity_book.update_status(record.opportunity_id, OpportunityStatus.ADMITTED)
                            action = f"{twap_tag}SUBMITTED_{entry_type}_{side.name}_{qty_str}"
            else:
                action = "POSITION_OCCUPIED"

        # 7. Record Full Diagnostic Trace
        self.decisions.append(
            {
                "bar_idx": len(self.candles) - 1,
                "decision_ns": bar.ts_init,
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
                "opportunity": asdict(opportunity) if opportunity else None,
                "support_count": len(supports),
                "contradict_count": len(contradicts),
                "abstain_count": len(abstains),
                "consensus_supported": is_supported,
                "action": action,
                "sizing_mode": sizing_mode,
                "stances": [asdict(s) for s in stances],
            }
        )

    def on_order_event(self, event: Any) -> None:
        """Track native order state transitions."""
        self.order_events.append(
            {
                "event_type": type(event).__name__,
                "client_order_id": str(getattr(event, "client_order_id", "")),
                "instrument_id": str(getattr(event, "instrument_id", "")),
                "event_ns": getattr(event, "ts_event", 0),
                "received_ns": getattr(event, "ts_init", 0),
            }
        )

    def on_position_opened(self, event: Any) -> None:
        """Track newly opened native position."""
        self.opened_positions.append(
            {
                "position_id": str(getattr(event, "position_id", "")),
                "instrument_id": str(getattr(event, "instrument_id", "")),
                "side": str(getattr(event, "side", "")),
                "quantity": str(getattr(event, "quantity", "")),
                "avg_px_open": str(getattr(event, "avg_px_open", "")),
                "event_ns": getattr(event, "ts_event", 0),
            }
        )

    def on_position_closed(self, event: Any) -> None:
        """Track closed native position and realized PnL."""
        self.closed_positions.append(
            {
                "position_id": str(getattr(event, "position_id", "")),
                "instrument_id": str(getattr(event, "instrument_id", "")),
                "realized_pnl": str(getattr(event, "realized_pnl", "")),
                "realized_return": str(getattr(event, "realized_return", "")),
                "avg_px_close": str(getattr(event, "avg_px_close", "") or ""),
                "event_ns": getattr(event, "ts_event", 0),
            }
        )


def run_expert_strategy_backtest(
    candles: tuple[Candle, ...],
    config: ExpertStrategyConfig | None = None,
    *,
    maker_fee: Decimal = Decimal("0.0002"),
    taker_fee: Decimal = Decimal("0.0005"),
    initial_balance: Decimal = Decimal("10000"),
    venue: str = "BINANCE",
    currency: str = "USDT",
    readings: tuple[PositioningReading, ...] = (),
    fill_model: Any = None,
    latency_model: Any = None,
    fee_model: Any = None,
    execution_profile: str | ExecutionProfile | None = None,
) -> dict[str, Any]:
    """Execute the 28-expert ensemble strategy through NautilusTrader's BacktestEngine.

    Constructs a qualified simulation environment, feeds causal bars, dispatches
    to the Strategy adapter, and returns economic accounting and witness trace ledgers.
    """
    cfg = config or ExpertStrategyConfig()
    curr = Currency.from_str(currency)
    ven = Venue(venue)
    instrument_id = InstrumentId.from_str(cfg.instrument_id)
    bar_type = BarType.from_str(cfg.bar_type_str)

    # 1. Construct CryptoPerpetual instrument
    instrument = CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=Symbol(cfg.instrument_id.split(".")[0].replace("-PERP", "")),
        base_currency=Currency.from_str("BTC"),
        quote_currency=curr,
        settlement_currency=curr,
        is_inverse=False,
        price_precision=2,
        size_precision=3,
        price_increment=Price(0.01, 2),
        size_increment=Quantity(0.001, 3),
        min_quantity=Quantity(0.001, 3),
        max_quantity=Quantity(100.0, 3),
        min_notional=Money(1, curr),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal("1"),
        margin_maint=Decimal("0.05"),
        maker_fee=maker_fee,
        taker_fee=taker_fee,
    )

    # 2. Build Nautilus Bars
    bars = [
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

    # Execution semantics: an explicit profile supplies the fill/fee/latency
    # models plus the liquidity-consumption and queue-position knobs. Explicit
    # model arguments still win over the profile, so existing callers that pass
    # their own models keep behaving exactly as before.
    profile = resolve_profile(execution_profile) if execution_profile is not None else None
    if profile is not None:
        venue_exec: dict[str, Any] = dict(venue_kwargs(profile))
        if fill_model is not None:
            venue_exec["fill_model"] = fill_model
        if latency_model is not None:
            venue_exec["latency_model"] = latency_model
        if fee_model is not None:
            venue_exec["fee_model"] = fee_model
    else:
        venue_exec = {
            "fill_model": fill_model,
            "latency_model": latency_model,
            "fee_model": fee_model,
        }

    # 3. Instantiate Engine and Strategy
    engine = BacktestEngine(
        BacktestEngineConfig(
            bypass_logging=True,
            logging=LoggerConfig(stdout_level=LogLevel.WARNING),
        )
    )
    try:
        engine.add_venue(
            ven,
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money(float(initial_balance), curr)],
            default_leverage=Decimal(1),
            **venue_exec,
        )
        engine.add_instrument(instrument)
        engine.add_data(bars)

        source_map = {c.end_ns: c for c in candles}
        strategy = ExpertEnsembleStrategy(cfg, source_candles=source_map, readings=readings)
        engine.add_strategy(strategy)

        # 4. Run Backtest
        engine.run()

        # 5. Extract Economic State & Diagnostics
        account_state = economic_state(engine, ven, curr)

        # Measured execution evidence. When no profile was declared, no
        # execution semantics are claimed: only the facts that do not depend on
        # the model (fill count, fill identity) are reported.
        fill_records, fill_report_type = native_fill_records(engine)
        if profile is not None:
            execution_block = execution_telemetry(
                profile,
                fill_records,
                fill_report_type,
                strategy.opened_positions,
                [{**d, "instrument_id": str(instrument_id)} for d in strategy.decisions],
            )
        else:
            execution_block = {
                "profile": None,
                "evidence_class": "UNSPECIFIED_EXECUTION_SEMANTICS",
                "fills_count": len(fill_records),
                "fills_report_type": fill_report_type,
                "fill_signature": fill_signature(fill_records),
            }
        return {
            "strategy_id": str(strategy.strategy_id),
            "instrument_id": str(instrument_id),
            "total_bars": len(bars),
            "decisions_count": len(strategy.decisions),
            "decisions": strategy.decisions,
            "order_events": strategy.order_events,
            "opened_positions": strategy.opened_positions,
            "closed_positions": strategy.closed_positions,
            "account": account_state,
            "execution": execution_block,
            "opportunity_book": strategy.opportunity_book,
        }
    finally:
        engine.dispose()
