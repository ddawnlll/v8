"""NautilusTrader adapter for one pre-registered swing policy.

The decision plane (`economics/swing_baseline.py`) replays a policy on bars and decides an
entry, a stop, a target and an expiry. This adapter hands exactly those decisions to the
engine so the two execution models can be reconciled: the engine owns order lifecycle,
fills, partial fills and position accounting; the replay owns the decision.

Two execution models are being compared, and their differences are *findings*, not noise:
the engine fills on the bar after the decision at the engine's execution price with the
venue's order semantics, while the replay enters at the decision's own reference price with
its declared bracket rule. The reconciliation tool reports every divergence class instead of
tuning either model until they agree.

Nothing here is an economic claim: it is an execution-parity instrument.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    Price,
    Quantity,
    Symbol,
    TriggerType,
    Venue,
)
from nautilus_trader.trading import Strategy

from v8_next.adapters.execution_models import ExecutionProfile, resolve_profile, venue_kwargs
from v8_next.domain.market import Candle, CausalFrame, frame_at
from v8_next.economics.swing_baseline import (
    SHARED_CONTRACT,
    SwingPolicySpec,
    policy_spec,
    swing_signal,
)

HOUR_NS = 3_600 * 10**9

#: Bounded decision window for the per-bar fast path (see SwingEngineStrategy).
#:
#: Conservative documented bound, not an empirically universal guarantee: it is
#: proven only for the exact ``plain_swing`` combination
#: (``range-breakout-48-v1`` + ``squeeze:baseline:v2``), which needs 49 bars
#: (grammar) and 69 bars (squeeze baseline warmup; 73 for m2/m3 worst case)
#: plus a 14-bar span. Every indicator read for THIS combination is confined
#: to the last 73 bars; 128 is the next power of two above that, leaving margin
#: for rolling-window edge effects. Any other grammar/protection combination
#: (e.g. ``causal_trend``) must use the exact ``frame_at`` path, because its
#: dependencies were not proven bounded here. If policy dependencies change,
#: the bound, the policy guard below and the parity tests must be revisited
#: together. Parity for the proven combination is pinned by regression tests on
#: real tape; any deviation (gap, irregular duration, cross-instrument,
#: unavailable/late, duplicate/overlap) falls back to exact ``frame_at``.
SWING_FRAME_WINDOW_BARS = 128

#: Exact grammar+protection combination proven bounded for the fast path.
#: Anything else uses the unchanged exact path.
_FAST_PATH_POLICY_ID = "plain_swing"
_FAST_PATH_GRAMMAR = "range-breakout-48-v1"
_FAST_PATH_PROTECTION = "squeeze:baseline:v2"

#: Declared execution semantics of the engine lane, published with every result.
ENGINE_LANE_SEMANTICS = {
    "entry": "MARKET on the bar following the decision (engine fill model)",
    "bracket": "STOP_MARKET at the decision's stop plus LIMIT at its target; the sibling is cancelled on fill",
    "timeout_only": "no bracket; the position is closed at market when the decision's expiry passes",
    "sizing": (
        "risk_notional / |entry_reference - stop_price|, floored to the instrument's size "
        "increment; a decision without a live protection has no risk distance, so the declared "
        "notional is divided by the entry reference instead and the basis is recorded per campaign"
    ),
    "bracketless_decision": (
        "the engine decides bracketing per decision: stop_price equal to entry_reference means no "
        "protection formed, so the position is held unprotected to its declared expiry"
    ),
    "class": "ENGINE_SIMULATION_NOT_A_VENUE_SETTLEMENT",
}


@dataclass
class SwingEngineConfig:
    policy_id: str = "plain_swing"
    instrument_id: str = "BTCUSDT-PERP.BINANCE"
    bar_type_str: str = "BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"
    venue: str = "BINANCE"
    currency: str = "USDT"
    base_currency: str = "BTC"
    initial_balance: Decimal = Decimal(SHARED_CONTRACT["initial_balance_usdt"])
    risk_per_trade_fraction: Decimal = Decimal(SHARED_CONTRACT["risk_per_trade_fraction"])
    maker_fee: Decimal = Decimal(SHARED_CONTRACT["maker_fee"])
    taker_fee: Decimal = Decimal(SHARED_CONTRACT["taker_fee"])
    price_precision: int = 2
    size_precision: int = 3
    execution_profile: str | None = None
    open_position_lookback_bars: int = 0

    @property
    def spec(self) -> SwingPolicySpec:
        return policy_spec(self.policy_id)

    @property
    def has_bracket(self) -> bool:
        return self.spec.protection_policy not in (None, "timeout-only-v1")


@dataclass
class SwingEngineEvents:
    """Everything the reconciliation needs, recorded from the engine's own callbacks."""

    decisions: list[dict[str, Any]] = field(default_factory=list)
    order_events: list[dict[str, Any]] = field(default_factory=list)
    fills: list[dict[str, Any]] = field(default_factory=list)
    positions_opened: list[dict[str, Any]] = field(default_factory=list)
    positions_closed: list[dict[str, Any]] = field(default_factory=list)


class SwingEngineStrategy(Strategy):
    """One pre-registered swing policy, executed by the engine."""

    def __new__(cls, *args: object, **kwargs: object) -> SwingEngineStrategy:
        return super().__new__(cls)

    def __init__(
        self,
        config: SwingEngineConfig,
        source_candles: dict[int, Candle],
        warmup_bars: int = 0,
    ) -> None:
        super().__init__()
        self.swing_config = config
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type_str)
        self.source_candles = source_candles
        self.warmup_bars = warmup_bars
        self.events = SwingEngineEvents()
        self.seen: list[Candle] = []
        self.plan: dict[str, Any] | None = None  # the live campaign
        self.active_position_id: str | None = None
        self.bars_seen = 0
        # Conservative positional guards for the bounded fast path. Once any of
        # these latches, the full history is known irregular, so later bounded
        # tails must not silently become regular again. In particular the
        # single-instrument/availability checks must be global, not tail-only:
        # a foreign, unavailable or late-arriving candle older than the window
        # is filtered by full ``frame_at`` (creating a gap or a different
        # admissible set) while a naive tail would hide it.
        self._history_continuous = True
        self._prev_end_ns: int | None = None
        self._duration_ns: int | None = None
        self._duration_regular = True
        self._history_has_foreign = False
        self._history_has_late_or_missing = False
        self._history_has_duplicate = False
        self._seen_starts: set[int] = set()

    # --- lifecycle -----------------------------------------------------------------

    def on_start(self) -> None:
        self.subscribe_bars(self.bar_type)

    def _instrument(self) -> CryptoPerpetual:
        return self.cache.instrument(self.instrument_id)

    def _position_id(self) -> Any | None:
        """The open position this strategy's exits must reduce, if one is known."""
        if self.active_position_id is None:
            return None
        from nautilus_trader.model import PositionId

        return PositionId.from_str(self.active_position_id)

    def on_bar(self, bar: Bar) -> None:
        candle = self.source_candles.get(bar.ts_event)
        if candle is None:
            return
        # Maintain O(1) conservative guards before any decision work. All latch
        # permanently: a single irregular candle anywhere in history forces
        # exact fallback for this and every later decision.
        cfg_instrument = str(self.swing_config.instrument_id)
        if candle.instrument_id != cfg_instrument:
            self._history_has_foreign = True
        if candle.available_ns is None or candle.available_ns > candle.end_ns:
            # Missing or late-arriving (not immediately admissible at its own
            # close). Full frame_at filters such bars per decision_ns, which can
            # create gaps the tail would hide; fall back exactly henceforth.
            self._history_has_late_or_missing = True
        if candle.start_ns in self._seen_starts:
            self._history_has_duplicate = True
        else:
            self._seen_starts.add(candle.start_ns)
        if self._prev_end_ns is not None and candle.start_ns != self._prev_end_ns:
            self._history_continuous = False
        self._prev_end_ns = candle.end_ns
        duration = candle.end_ns - candle.start_ns
        if self._duration_ns is None:
            self._duration_ns = duration
        elif duration != self._duration_ns:
            self._duration_regular = False
        self.seen.append(candle)
        self.bars_seen += 1
        if self.bars_seen <= self.warmup_bars:
            return
        if self.plan is None:
            self._try_open(candle)
        else:
            self._maybe_timeout(candle)

    def _fast_path_eligible(self) -> bool:
        """Exact proven combination only; all others use unchanged exact path."""
        spec = self.swing_config.spec
        return (
            spec.policy_id == _FAST_PATH_POLICY_ID
            and spec.grammar_policy == _FAST_PATH_GRAMMAR
            and spec.protection_policy == _FAST_PATH_PROTECTION
        )

    def _decision_frame(self, candle: Candle) -> CausalFrame:
        """Bounded causal frame with exact fallback (see module constant).

        The fast path is restricted to the exact proven grammar+protection
        combination and to histories that are globally clean (continuous,
        regular duration, single instrument, immediately available, no
        duplicate starts). Anything else — other policies, gaps, irregular
        durations, foreign/late/duplicate history, short histories, or a
        currently inadmissible candle — uses the unchanged exact ``frame_at``
        path, preserving errors and admissible-frame behavior. In particular a
        bad old candle outside the tail still forces fallback via the latched
        global flags, so filtering-induced gaps can never be hidden.
        """
        instrument = str(self.swing_config.instrument_id)
        if not self._fast_path_eligible():
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if not self._history_continuous:
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if not self._duration_regular:
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if self._history_has_foreign:
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if self._history_has_late_or_missing:
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if self._history_has_duplicate:
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if len(self.seen) <= SWING_FRAME_WINDOW_BARS:
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        if (
            candle.instrument_id != instrument
            or candle.available_ns is None
            or candle.available_ns > candle.end_ns
        ):
            return frame_at(instrument, candle.end_ns, tuple(self.seen))
        window = self.seen[-SWING_FRAME_WINDOW_BARS:]
        return CausalFrame(
            instrument, candle.end_ns, tuple(window), _trusted_order=True
        )

    # --- decision → order ----------------------------------------------------------

    def _try_open(self, candle: Candle) -> None:
        spec = self.swing_config.spec
        frame = self._decision_frame(candle)
        decision = swing_signal(frame, spec, bar_ns=HOUR_NS)
        if decision is None:
            return
        stop_distance = abs(Decimal(decision.entry_reference) - Decimal(decision.stop_price))
        # whether a campaign is bracketed is a property of THIS decision, not of the policy's
        # name: a decision whose protection did not form carries stop == entry_reference and is
        # therefore unprotected. The engine inserts it unprotected and holds it to its expiry.
        has_bracket = self.swing_config.has_bracket and stop_distance > 0
        if not has_bracket and stop_distance <= 0:
            self.events.decisions.append(
                {
                    "status": "BRACKETLESS_DECISION_INSERTED_UNPROTECTED",
                    "decision": decision.as_dict(),
                    "note": (
                        "stop_price equals entry_reference: no protection formed, so the engine "
                        "holds to the declared expiry instead of stopping out at its own entry"
                    ),
                }
            )
        if has_bracket and stop_distance <= 0:  # pragma: no cover - defensive
            self.plan = None
            return
        risk_notional = self.swing_config.initial_balance * self.swing_config.risk_per_trade_fraction
        # risk distance is the stop when a bracket exists; an unprotected decision has no risk
        # distance, so the declared notional is used instead and the choice is recorded
        sizing_basis = "STOP_DISTANCE" if has_bracket else "DECLARED_NOTIONAL_AT_ENTRY_REFERENCE"
        denominator = stop_distance if has_bracket else Decimal(decision.entry_reference)
        raw_quantity = risk_notional / denominator
        increment = Decimal(1).scaleb(-self.swing_config.size_precision)
        quantity = (raw_quantity // increment) * increment
        if quantity <= 0:
            self.events.decisions.append(
                {
                    "status": "REJECTED_QUANTITY_FLOORED_TO_ZERO",
                    "decision": decision.as_dict(),
                    "note": "no live campaign; the next bar may decide again",
                }
            )
            self.plan = None
            return

        side = OrderSide.BUY if decision.direction == "LONG" else OrderSide.SELL
        entry = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=side,
            quantity=Quantity(float(quantity), self.swing_config.size_precision),
        )
        # the protection's own declared TTL governs the bracket timeout; only a
        # timeout-only policy falls back to the opportunity expiry
        declared_expiry_bars = decision.open_trade_expiry_bars
        timeout_rule = "PROTECTION_OPEN_TRADE_EXPIRY_BARS"
        timeout_ns = (
            int(decision.decision_ns) + declared_expiry_bars * HOUR_NS
            if declared_expiry_bars is not None
            else int(decision.expires_ns)
        )
        if declared_expiry_bars is None:
            timeout_rule = "OPPORTUNITY_EXPIRY_NS"
        self.plan = {
            "status": "ENTRY_SUBMITTED",
            "timeout_rule": timeout_rule,
            "timeout_ns": timeout_ns,
            "decision": decision.as_dict(),
            "direction": decision.direction,
            "quantity": float(quantity),
            "entry_client_order_id": str(entry.client_order_id),
            "entry_bar_ns": candle.end_ns,
            "expires_ns": int(decision.expires_ns),
            "has_bracket": has_bracket,
            "sizing_basis": sizing_basis,
            "stop_price": str(decision.stop_price),
            "target_price": str(decision.target_price),
        }
        # the live record, not a snapshot: the bracket leg ids are stamped on it after the
        # entry fills, and an auditor must be able to see which leg protected the campaign
        self.events.decisions.append(dict(self.plan))
        self.submit_order(entry)

    def _submit_bracket(self) -> None:
        instrument = self._instrument()
        plan = self.plan or {}
        exit_side = OrderSide.SELL if plan["direction"] == "LONG" else OrderSide.BUY
        quantity = Quantity(float(plan["quantity"]), self.swing_config.size_precision)
        stop = self.order_factory.stop_market(
            instrument_id=self.instrument_id,
            order_side=exit_side,
            quantity=quantity,
            trigger_price=Price(float(Decimal(plan["stop_price"])), instrument.price_precision),
            trigger_type=TriggerType.LAST_PRICE,
        )
        target = self.order_factory.limit(
            instrument_id=self.instrument_id,
            order_side=exit_side,
            quantity=quantity,
            price=Price(float(Decimal(plan["target_price"])), instrument.price_precision),
        )
        plan["stop_client_order_id"] = str(stop.client_order_id)
        plan["target_client_order_id"] = str(target.client_order_id)
        self.events.decisions.append({"bracket_submitted": dict(plan)})
        # both legs rest together; the first to fill closes the position and the sibling is
        # cancelled from on_order_filled, which is the OCO behaviour the replay assumes
        # submitted against the open position so the legs can only reduce it: without this a
        # second leg filling after the first opens an opposite position nobody is tracking
        self.submit_order(stop, position_id=self._position_id())
        self.submit_order(target, position_id=self._position_id())

    def _maybe_timeout(self, candle: Candle) -> None:
        plan = self.plan or {}
        if plan.get("status") not in ("POSITION_OPEN",):
            return
        timeout_ns = plan.get("timeout_ns")
        if timeout_ns is None or candle.end_ns < timeout_ns:
            return
        self._close_at_market("TIMEOUT_EXPIRED")

    def _close_at_market(self, reason: str) -> None:
        plan = self.plan or {}
        if plan.get("status") != "POSITION_OPEN":
            return
        # retire the resting bracket first: an orphaned stop or target left on the book
        # would fill later and open a position this adapter is no longer tracking
        for order in list(self.cache.orders_open(instrument_id=self.instrument_id)):
            self.cancel_order(order)
        exit_side = OrderSide.SELL if plan["direction"] == "LONG" else OrderSide.BUY
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=exit_side,
            quantity=Quantity(float(plan["quantity"]), self.swing_config.size_precision),
        )
        plan["status"] = f"CLOSING_{reason}"
        plan["close_client_order_id"] = str(order.client_order_id)
        plan["close_position_id"] = self.active_position_id
        self.events.decisions.append(dict(plan))
        self.submit_order(order, position_id=self._position_id())

    # --- engine callbacks ----------------------------------------------------------

    def on_order_event(self, event: Any) -> None:
        self.events.order_events.append(
            {
                "event_type": type(event).__name__,
                "client_order_id": str(getattr(event, "client_order_id", "")),
                "ts_event": getattr(event, "ts_event", 0),
            }
        )

    def on_order_filled(self, event: Any) -> None:
        plan = self.plan
        if plan is None:
            return
        self.events.fills.append(
            {
                "client_order_id": str(getattr(event, "client_order_id", "")),
                "side": str(getattr(event, "order_side", "")),
                "last_qty": str(getattr(event, "last_qty", "")),
                "last_px": str(getattr(event, "last_px", "")),
                "ts_event": getattr(event, "ts_event", 0),
                "commission": str(getattr(event, "commission", "")),
            }
        )
        filled_id = str(getattr(event, "client_order_id", ""))
        if plan.get("status") == "ENTRY_SUBMITTED":
            plan["status"] = "POSITION_OPEN"
            plan["entry_fill_ns"] = getattr(event, "ts_event", 0)
            plan["entry_fill_px"] = str(getattr(event, "last_px", ""))
            self.events.decisions.append(dict(plan))
            if plan["has_bracket"]:
                self._submit_bracket()
            return
        # a bracket leg filled: retire its sibling so only one protection remains live
        if plan.get("status") == "POSITION_OPEN" and filled_id in (
            plan.get("stop_client_order_id"),
            plan.get("target_client_order_id"),
        ):
            sibling_id = (
                plan.get("target_client_order_id")
                if filled_id == plan.get("stop_client_order_id")
                else plan.get("stop_client_order_id")
            )
            plan["status"] = "CLOSING_BRACKET"
            plan["bracket_leg_filled"] = filled_id
            for order in self.cache.orders_open(instrument_id=self.instrument_id):
                if str(order.client_order_id) == sibling_id:
                    self.cancel_order(order)

    def on_position_opened(self, event: Any) -> None:
        self.active_position_id = str(getattr(event, "position_id", "")) or None
        self.events.positions_opened.append(
            {
                "position_id": str(getattr(event, "position_id", "")),
                "side": str(getattr(event, "side", "")),
                "quantity": str(getattr(event, "quantity", "")),
                "avg_px_open": str(getattr(event, "avg_px_open", "")),
                "ts_event": getattr(event, "ts_event", 0),
            }
        )

    def on_order_denied(self, event: Any) -> None:
        """A denied order is a finding: it is recorded and named, never swallowed."""
        self.events.order_events.append(
            {
                "event_type": "OrderDenied",
                "client_order_id": str(getattr(event, "client_order_id", "")),
                "reason": str(getattr(event, "reason", "")),
                "ts_event": getattr(event, "ts_event", 0),
            }
        )

    def on_order_rejected(self, event: Any) -> None:
        self.events.order_events.append(
            {
                "event_type": "OrderRejected",
                "client_order_id": str(getattr(event, "client_order_id", "")),
                "reason": str(getattr(event, "reason", "")),
                "ts_event": getattr(event, "ts_event", 0),
            }
        )

    def on_position_closed(self, event: Any) -> None:
        self.active_position_id = None
        record = {
            "position_id": str(getattr(event, "position_id", "")),
            "quantity": str(getattr(event, "quantity", "")),
            "avg_px_open": str(getattr(event, "avg_px_open", "")),
            "avg_px_close": str(getattr(event, "avg_px_close", "") or ""),
            "realized_pnl": str(getattr(event, "realized_pnl", "")),
            "realized_return": str(getattr(event, "realized_return", "")),
            "ts_event": getattr(event, "ts_event", 0),
        }
        self.events.positions_closed.append(record)
        if self.plan is not None and self.plan.get("status", "").startswith(("POSITION_OPEN", "CLOSING")):
            self.plan["status"] = "CLOSED"
            self.plan["exit_fill_ns"] = record["ts_event"]
            self.plan["exit_fill_px"] = record["avg_px_close"]
            self.plan["realized_pnl"] = record["realized_pnl"]
            self.events.decisions.append({"campaign_closed": dict(self.plan)})
            self.plan = None


def build_instrument(config: SwingEngineConfig, currency: Currency) -> CryptoPerpetual:
    """The same instrument contract the ensemble adapter uses, so results are comparable."""
    increment = Decimal(1).scaleb(-config.size_precision)
    tick = Decimal(1).scaleb(-config.price_precision)
    return CryptoPerpetual(
        instrument_id=InstrumentId.from_str(config.instrument_id),
        raw_symbol=Symbol(config.instrument_id.split(".")[0].replace("-PERP", "")),
        base_currency=Currency.from_str(config.base_currency),
        quote_currency=currency,
        settlement_currency=currency,
        is_inverse=False,
        price_precision=config.price_precision,
        size_precision=config.size_precision,
        price_increment=Price(float(tick), config.price_precision),
        size_increment=Quantity(float(increment), config.size_precision),
        min_quantity=Quantity(float(increment), config.size_precision),
        max_quantity=Quantity(100.0, config.size_precision),
        min_notional=Money(1, currency),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal(SHARED_CONTRACT_MARGIN_INIT),
        margin_maint=Decimal(SHARED_CONTRACT_MARGIN_MAINT),
        maker_fee=config.maker_fee,
        taker_fee=config.taker_fee,
    )


#: declared on the shared contract side of the engine lane
SHARED_CONTRACT_MARGIN_INIT = "1"
SHARED_CONTRACT_MARGIN_MAINT = "0.05"


def run_swing_engine(
    candles: tuple[Candle, ...],
    config: SwingEngineConfig | None = None,
    *,
    warmup_bars: int = 0,
) -> dict[str, Any]:
    """Feed the tape to the engine and return its own event record."""
    cfg = config or SwingEngineConfig()
    currency = Currency.from_str(cfg.currency)
    venue = Venue(cfg.venue)
    instrument = build_instrument(cfg, currency)
    bar_type = BarType.from_str(cfg.bar_type_str)

    bars = [
        Bar(
            bar_type,
            Price(float(candle.open), cfg.price_precision),
            Price(float(candle.high), cfg.price_precision),
            Price(float(candle.low), cfg.price_precision),
            Price(float(candle.close), cfg.price_precision),
            Quantity(float(candle.volume), cfg.size_precision),
            candle.end_ns,
            candle.end_ns,
        )
        for candle in candles
    ]

    profile: ExecutionProfile | None = (
        resolve_profile(cfg.execution_profile) if cfg.execution_profile is not None else None
    )
    venue_exec: dict[str, Any] = dict(venue_kwargs(profile)) if profile is not None else {}

    engine = BacktestEngine(
        BacktestEngineConfig(bypass_logging=True, logging=LoggerConfig(stdout_level=LogLevel.ERROR))
    )
    engine.add_venue(
        venue,
        OmsType.NETTING,
        AccountType.MARGIN,
        [Money(float(cfg.initial_balance), currency)],
        default_leverage=Decimal(1),
        **venue_exec,
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)
    source_map = {candle.end_ns: candle for candle in candles}
    strategy = SwingEngineStrategy(cfg, source_map, warmup_bars=warmup_bars)
    engine.add_strategy(strategy)

    engine.run()
    return {
        "policy_id": cfg.policy_id,
        "instrument_id": cfg.instrument_id,
        "bars": len(candles),
        "warmup_bars": warmup_bars,
        "semantics": ENGINE_LANE_SEMANTICS,
        "execution_profile": None if profile is None else profile.name,
        "events": {
            "decisions": strategy.events.decisions,
            "order_events": strategy.events.order_events,
            "fills": strategy.events.fills,
            "positions_opened": strategy.events.positions_opened,
            "positions_closed": strategy.events.positions_closed,
        },
        "open_position_at_end": None if strategy.plan is None else strategy.plan.get("status"),
        # an order left resting on the book after the run would fill later and open a position
        # the adapter is no longer tracking, so it is published rather than assumed absent
        "orders_open_at_end": [
            str(order.client_order_id)
            for order in strategy.cache.orders_open(instrument_id=strategy.instrument_id)
        ],
    }
