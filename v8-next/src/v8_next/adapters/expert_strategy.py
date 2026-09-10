"""Native NautilusTrader Strategy adapter for the canonical 28-expert ensemble.

Epistemic & Execution Demarcation (matching V8_NEXT_IMPLEMENTATION_SCOPE.md):
- Python owns opportunity identity, the 28 expert witness stances, and consensus gating.
- NautilusTrader owns generic bar dispatch, order lifecycle, order lists, positions,
  margin accounting, and fee/funding settlement.
- No custom simulator or manual scheduling loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

import polars as pl
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
from v8_next.domain.market import Candle, CausalFrame, build_candle_dataframe, frame_at
from v8_next.domain.positioning import PositioningReading
from v8_next.economics.decisions import (
    Opportunity,
    Stance,
    StanceKind,
    linear_exposure_id,
    opportunity_at,
)
from v8_next.economics.grammar import grammar_opportunity
from v8_next.experts.features import compute_indicator_pipeline
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
    bracket_stop_pct: Decimal | None = None
    bracket_target_pct: Decimal | None = None
    max_concurrent_positions: int = 1
    audit_trace: bool = True


@dataclass
class SignalCache:
    """Shared immutable signal results for repeated deterministic engine runs.

    Funding settlement and sleeve sizing do not alter causal expert observations.
    The portfolio verifier can therefore reuse the exact opportunity/stance tuple
    for the same source candle across P, P+E, funding, and determinism runs.
    """

    _entries: dict[
        tuple[str, int, int, int, str], tuple[Opportunity | None, tuple[Stance, ...]]
    ] = field(default_factory=dict)
    _stance_payloads: dict[tuple[str, int, int, int, str], tuple[dict[str, Any], ...]] = field(
        default_factory=dict
    )
    _indicator_frames: dict[tuple[str, int, str, str], Any] = field(default_factory=dict)

    @staticmethod
    def _key(instrument_id: str, bar_index: int, candle: Candle) -> tuple[str, int, int, int, str]:
        return (instrument_id, bar_index, candle.start_ns, candle.end_ns, candle.source_hash)

    @staticmethod
    def _indicator_key(instrument_id: str, candles: tuple[Candle, ...]) -> tuple[str, int, str, str]:
        return (
            instrument_id,
            len(candles),
            candles[0].source_hash if candles else "",
            candles[-1].source_hash if candles else "",
        )

    def indicator_frame(self, instrument_id: str, candles: tuple[Candle, ...]) -> Any:
        return self._indicator_frames.get(self._indicator_key(instrument_id, candles))

    def store_indicator_frame(
        self, instrument_id: str, candles: tuple[Candle, ...], frame: Any
    ) -> None:
        self._indicator_frames[self._indicator_key(instrument_id, candles)] = frame

    def lookup(
        self,
        instrument_id: str,
        bar_index: int,
        candle: Candle,
    ) -> tuple[Opportunity | None, tuple[Stance, ...]] | None:
        return self._entries.get(self._key(instrument_id, bar_index, candle))

    def stance_payload(
        self,
        instrument_id: str,
        bar_index: int,
        candle: Candle,
    ) -> tuple[dict[str, Any], ...] | None:
        return self._stance_payloads.get(self._key(instrument_id, bar_index, candle))

    def store(
        self,
        instrument_id: str,
        bar_index: int,
        candle: Candle,
        opportunity: Opportunity | None,
        stances: tuple[Stance, ...],
    ) -> None:
        key = self._key(instrument_id, bar_index, candle)
        self._entries[key] = (opportunity, stances)

    def store_stance_payload(
        self,
        instrument_id: str,
        bar_index: int,
        candle: Candle,
        payload: tuple[dict[str, Any], ...],
    ) -> None:
        self._stance_payloads[self._key(instrument_id, bar_index, candle)] = payload


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
        signal_cache: SignalCache | None = None,
    ) -> None:
        super().__init__()
        self.ensemble_config = config or ExpertStrategyConfig()
        self.instrument_id = InstrumentId.from_str(self.ensemble_config.instrument_id)
        self.bar_type = BarType.from_str(self.ensemble_config.bar_type_str)
        self.source_candles = source_candles or {}
        ordered_source = tuple(sorted(self.source_candles.values(), key=lambda c: c.end_ns))
        self._ordered_source = ordered_source
        unsupported_fast_path = (
            not self.ensemble_config.audit_trace
            and self.ensemble_config.grammar_policy == "range-breakout-48-v1"
            and linear_exposure_id(str(self.instrument_id)) is None
        )
        self._source_prefix_df: pl.DataFrame | None = (
            build_candle_dataframe(ordered_source)
            if ordered_source and not unsupported_fast_path
            else None
        )
        if ordered_source and not unsupported_fast_path:
            self._source_indicator_df: pl.DataFrame | None = (
                signal_cache.indicator_frame(str(self.instrument_id), ordered_source)
                if signal_cache is not None
                else None
            )
            if self._source_indicator_df is None:
                source_frame = CausalFrame(
                    str(self.instrument_id),
                    max(c.available_ns or c.end_ns for c in ordered_source),
                    ordered_source,
                )
                self._source_indicator_df = compute_indicator_pipeline(source_frame)
                if signal_cache is not None:
                    signal_cache.store_indicator_frame(
                        str(self.instrument_id), ordered_source, self._source_indicator_df
                    )
        else:
            self._source_indicator_df = None
        self.readings = readings
        self.signal_cache = signal_cache

        # Opportunity book & exposure resolver
        self.opportunity_book = OpportunityBook()
        self.exposure_resolver = ExposureResolver()

        # Internal state & diagnostic ledgers
        self.candles: list[Candle] = []
        self.decisions: list[dict[str, Any]] = []
        self.order_events: list[dict[str, Any]] = []
        self.opened_positions: list[dict[str, Any]] = []
        self.closed_positions: list[dict[str, Any]] = []

    def on_start(self) -> None:
        """Subscribe to configured bar type on strategy start."""
        self.subscribe_bars(self.bar_type)

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
        bar_index = len(self.candles)
        self.candles.append(candle)

        # 2. Advance OpportunityBook with newly closed candle (invalidation & TTL check)
        self.opportunity_book.on_candle(candle)

        # 3. Build CausalFrame
        cached_signal = (
            self.signal_cache.lookup(str(self.instrument_id), bar_index, candle)
            if self.signal_cache is not None
            else None
        )
        if cached_signal is not None:
            opportunity, stances = cached_signal
        else:
            unsupported_fast_path = (
                not self.ensemble_config.audit_trace
                and self.ensemble_config.grammar_policy == "range-breakout-48-v1"
                and linear_exposure_id(str(self.instrument_id)) is None
            )
            if unsupported_fast_path:
                opportunity = None
                stances = ()
            else:
                if use_prefix:
                    prefix_df = self._source_prefix_df
                    if prefix_df is None:
                        raise RuntimeError("trusted prefix requested without prefix cache")
                    frame = CausalFrame.from_trusted_ordered_prefix(
                        str(self.instrument_id),
                        bar.ts_init,
                        tuple(self.candles),
                        prefix_df,
                        self._source_indicator_df,
                    )
                else:
                    frame = frame_at(str(self.instrument_id), bar.ts_init, tuple(self.candles))

                # 4. Detect Opportunity
                if self.ensemble_config.grammar_policy == "range-breakout-48-v1":
                    opportunity = opportunity_at(frame)
                else:
                    opportunity = grammar_opportunity(frame, self.ensemble_config.grammar_policy)

                # 5. Invoke all 28 canonical active witnesses once per source prefix.
                stances = (
                    ()
                    if opportunity is None and not self.ensemble_config.audit_trace
                    else observe_all_28(frame, opportunity, readings=self.readings)
                )
            if self.signal_cache is not None:
                self.signal_cache.store(
                    str(self.instrument_id), bar_index, candle, opportunity, stances
                )

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

        # 6. Consensus uses the cached or freshly computed witness tuple.
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
        if is_supported and opportunity is not None:
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

                        order_list = self.order_factory.bracket(
                            instrument_id=self.instrument_id,
                            order_side=side,
                            quantity=quantity,
                            entry_order_type=OrderType.MARKET,
                            sl_trigger_price=sl_price,
                            tp_price=tp_price,
                        )
                        self.submit_order_list(order_list)
                        if record is not None:
                            self.opportunity_book.update_status(record.opportunity_id, OpportunityStatus.ADMITTED)
                        action = f"SUBMITTED_BRACKET_{side.name}_{qty_str}"
                    else:
                        order = self.order_factory.market(
                            instrument_id=self.instrument_id,
                            order_side=side,
                            quantity=quantity,
                        )
                        self.submit_order(order)
                        if record is not None:
                            self.opportunity_book.update_status(record.opportunity_id, OpportunityStatus.ADMITTED)
                        action = f"SUBMITTED_MARKET_{side.name}_{qty_str}"
            else:
                action = "POSITION_OCCUPIED"

        # 7. Keep the full JSON stance ledger only when audit tracing is enabled.
        decision = {
            "bar_idx": bar_index,
            "decision_ns": bar.ts_init,
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "opportunity": asdict(opportunity) if opportunity else None,
            "support_count": len(supports),
            "contradict_count": len(contradicts),
            "abstain_count": 28 if opportunity is None and not stances else len(abstains),
            "consensus_supported": is_supported,
            "action": action,
        }
        if self.ensemble_config.audit_trace:
            stance_payload = (
                self.signal_cache.stance_payload(str(self.instrument_id), bar_index, candle)
                if self.signal_cache is not None
                else None
            )
            if stance_payload is None:
                stance_payload = tuple(asdict(s) for s in stances)
                if self.signal_cache is not None:
                    self.signal_cache.store_stance_payload(
                        str(self.instrument_id), bar_index, candle, stance_payload
                    )
            decision["stances"] = list(stance_payload)
        self.decisions.append(decision)

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
            fill_model=fill_model,
            latency_model=latency_model,
            fee_model=fee_model,
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
            "opportunity_book": strategy.opportunity_book,
        }
    finally:
        engine.dispose()
