"""Simulation truth core — the single source of economic truth (RULES §14).

net_R, labels, and outcomes are defined here and nowhere else. This is one
audit unit on purpose: the entire economic contract — trade shape, cost math,
funding tape, gap semantics, and the bar-walk that turns them into a net_R —
reads top to bottom in one pass.

Determinism contract (RULES §14): no wall-clock, no global RNG, no network, no
env reads. Every function is a pure function of its inputs. Same inputs →
byte-identical output on any machine (verified by frozen outcome hashes).

Reference engine only: this scalar loop *defines* truth. Any faster path
(vectorized tape, CUDA) must reproduce it exactly under a parity test and is
never the sole path.

Conventions (fixed decisions):
- The entry bar is never inspected for exits. The walk starts at entry_index+1,
  so an outcome can never use information from the decision bar (no lookahead).
- Barriers use bar extremes: a LONG stops when a bar's low touches the stop and
  targets when its high touches the target (mirror for SHORT).
- If one bar touches BOTH stop and target, the stop wins — the conservative
  assumption, since intrabar order is unknown.
- When a stop or target is hit, the exit fill is the WORSE of the barrier price
  and the bar's open (gap semantics): a LONG stop fills at min(open, stop) —
  you can't exit at the stop price if the market gapped through it.
- If neither barrier is hit within max_holding_bars, exit at the close of bar
  (entry_index + max_holding_bars), reason "time".
- Too few forward bars is an error, not a silent truncation (fail-closed).

Return tiers (three distinct quantities, no unit mixing):
  nominal_return — at the barrier price (stop/target/close) before gap or cost
  execution_return — gap-adjusted exit price, before costs
  net_return — execution_return minus all costs
  net_r — net_return / risk_fraction (the only downstream performance unit)

All returns are fractional (fraction of entry price); all costs are fractional
(fraction of notional). No unit conversion bugs possible because there are no
units to convert.
"""

from __future__ import annotations

import bisect
import hashlib
import math
from dataclasses import dataclass
from typing import Literal, Sequence, cast

Side = Literal["LONG", "SHORT"]
ExitReason = Literal["stop", "target", "time"]

_BPS = 1e-4


# --- contracts ---------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FundingEvent:
    """One funding interval event on the funding tape.

    bar_index : index into the bar arrays where this funding event settles.
                Must be strictly increasing across the tape.
    rate      : funding rate as a fraction (e.g. 0.0001 = 0.01% per interval).
                Must be finite with |rate| < 1.0.
    mark_price: mark price at settlement (quote). Must be finite and > 0.
    """
    bar_index: int
    rate: float
    mark_price: float


@dataclass(frozen=True, slots=True)
class TradeSpec:
    """A single trade to simulate, fully self-contained.

    Prices are quote currency per base unit. Costs are fractional, applied per
    side unless noted. No config registry, no mode object: a trade is described
    entirely by this spec, nothing is read from ambient state.

    side              : "LONG" | "SHORT"
    entry_index       : index into the bar arrays where the position opens
    entry_price       : assumed fill price (quote); the engine takes it as given
    stop_price        : protective stop (quote); on the losing side of entry
    target_price      : profit target (quote); on the winning side of entry
    max_holding_bars  : hard cap on bars held; else exit at that bar's close
    fee_rate          : per-side fee as a fraction of notional (e.g. 0.0004)
    slippage_bps      : per-side slippage in bps of notional (1.0 = 0.01%)
    """

    side: Side
    entry_index: int
    entry_price: float
    stop_price: float
    target_price: float
    max_holding_bars: int
    fee_rate: float = 0.0004
    slippage_bps: float = 1.0


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Round-trip costs as fractions of notional. `funding` is signed (a short
    can receive funding); `total` is subtracted from execution_return."""

    fee: float          # entry_fee + exit_fee
    slippage: float     # entry_slip + exit_slip
    funding: float      # signed: +cost, -credit
    total: float


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    """Result of simulating one TradeSpec. `net_r` is the only performance
    number that matters downstream: net_return / risk_fraction, where
    risk_fraction = |entry - stop| / entry (the 1R distance).

    nominal_return   — at barrier price, before gap adjustment or costs
    execution_return — gap-adjusted exit price, before costs
    net_return       — execution_return minus all costs
    net_r            — net_return / risk_fraction
    outcome_hash     — SHA-256 of canonical fields (cross-machine determinism)
    """

    side: Side
    entry_index: int
    exit_index: int
    exit_reason: ExitReason
    entry_price: float
    exit_price: float       # gap-adjusted fill price
    nominal_return: float   # at barrier price
    risk_fraction: float
    gross_return: float     # = execution_return (legacy name, kept for compat)
    net_return: float
    net_r: float
    mae_r: float            # max adverse excursion, in R (>= 0)
    mfe_r: float            # max favorable excursion, in R (>= 0)
    costs: CostBreakdown
    outcome_hash: str = ""


# --- validation helpers -------------------------------------------------------

def _strict_int(value: object, *, allow_bool: bool = False) -> bool:
    """True if value is an int (not bool unless allow_bool)."""
    if isinstance(value, bool):
        return allow_bool
    return isinstance(value, int)


def _finite_number(value: float) -> bool:
    """True if value is a finite float (not NaN, not inf, not -inf)."""
    if not isinstance(value, (int, float)):
        return False
    if isinstance(value, bool):
        return False
    return math.isfinite(float(value))


def _validate_bar(hi: float, lo: float, op: float, cl: float, idx: int) -> None:
    """Lazy bar validation at event end: finite, positive, and OHLC-consistent.
    Raises ValueError on any invalid bar — fail-closed structural gate."""
    for name, val in [("high", hi), ("low", lo), ("open", op), ("close", cl)]:
        if not _finite_number(val):
            raise ValueError(f"bar[{idx}]: {name}={val} is not finite")
    if lo <= 0.0:
        raise ValueError(f"bar[{idx}]: low={lo} must be > 0")
    if hi < lo:
        raise ValueError(f"bar[{idx}]: high={hi} < low={lo}")
    if cl < lo or cl > hi:
        raise ValueError(f"bar[{idx}]: close={cl} outside [{lo}, {hi}]")
    if op < lo or op > hi:
        raise ValueError(f"bar[{idx}]: open={op} outside [{lo}, {hi}]")


def _validate_all_bars_used(
    highs: Sequence[float],
    lows: Sequence[float],
    opens: Sequence[float],
    closes: Sequence[float],
    entry_index: int,
    exit_index: int,
) -> None:
    """Validate every bar from entry_index+1 through exit_index (the bars the
    engine actually inspected). Prevents silent corruption in unused tail bars
    but also catches garbage in the walk range."""
    for i in range(entry_index + 1, exit_index + 1):
        _validate_bar(highs[i], lows[i], opens[i], closes[i], i)


# --- funding tape -------------------------------------------------------------

def _funding_return(
    events: Sequence[FundingEvent],
    entry_index: int,
    exit_index: int,
    side: Side,
    entry_fill_price: float,
) -> float:
    """Total funding return as a fraction of entry notional.

    Validates that funding events are strictly increasing by bar_index. Future
    events (bar_index > exit_index) are structurally validated but their rate
    and mark_price are never read — the ordering guarantee is enforced so a
    sorter bug can't silently drop past events by burying them after the exit.
    """
    direction = 1.0 if side == "LONG" else -1.0
    total = 0.0
    prev_index: int | None = None

    for k, ev in enumerate(events):
        if not _strict_int(ev.bar_index) or ev.bar_index < 0:
            raise ValueError(
                f"funding[{k}]: bar_index must be an int >= 0, got {ev.bar_index!r}"
            )
        if prev_index is not None and ev.bar_index <= prev_index:
            raise ValueError(
                f"funding[{k}]: bar_index={ev.bar_index} not strictly increasing "
                f"(previous was {prev_index})"
            )
        prev_index = ev.bar_index

        # Future events: validate structure, skip value reads.
        if ev.bar_index > exit_index:
            continue

        if not _finite_number(ev.rate) or abs(ev.rate) >= 1.0:
            raise ValueError(
                f"funding[{k}]: rate={ev.rate!r} must be finite with |rate| < 1.0"
            )
        if not _finite_number(ev.mark_price) or ev.mark_price <= 0.0:
            raise ValueError(
                f"funding[{k}]: mark_price={ev.mark_price!r} must be finite and > 0"
            )

        # Funding settles on bars after entry.
        if ev.bar_index > entry_index:
            total += direction * ev.rate * (ev.mark_price / entry_fill_price)

    return total


class _FundingIndex:
    """Reusable structural index over a funding tape.

    Bar-index ordering is validated once. Rates and marks remain lazily
    validated only when the event is inside the inspected trade interval,
    preserving the scalar engine's future-value semantics and arithmetic order.
    """

    __slots__ = ("events", "bar_indices")

    def __init__(self, events: Sequence[FundingEvent]):
        self.events = events
        indices: list[int] = []
        previous: int | None = None
        for k, event in enumerate(events):
            if not _strict_int(event.bar_index) or event.bar_index < 0:
                raise ValueError(
                    f"funding[{k}]: bar_index must be an int >= 0, "
                    f"got {event.bar_index!r}"
                )
            if previous is not None and event.bar_index <= previous:
                raise ValueError(
                    f"funding[{k}]: bar_index={event.bar_index} not strictly "
                    f"increasing (previous was {previous})"
                )
            previous = event.bar_index
            indices.append(event.bar_index)
        self.bar_indices = indices

    def funding_return(
        self,
        entry_index: int,
        exit_index: int,
        side: Side,
        entry_fill_price: float,
    ) -> float:
        direction = 1.0 if side == "LONG" else -1.0
        left = bisect.bisect_right(self.bar_indices, entry_index)
        right = bisect.bisect_right(self.bar_indices, exit_index)
        total = 0.0
        for k in range(left, right):
            event = self.events[k]
            if not _finite_number(event.rate) or abs(event.rate) >= 1.0:
                raise ValueError(
                    f"funding[{k}]: rate={event.rate!r} must be finite "
                    "with |rate| < 1.0"
                )
            if not _finite_number(event.mark_price) or event.mark_price <= 0.0:
                raise ValueError(
                    f"funding[{k}]: mark_price={event.mark_price!r} must be "
                    "finite and > 0"
                )
            total += direction * event.rate * (
                event.mark_price / entry_fill_price
            )
        return total


FundingSource = Sequence[FundingEvent] | _FundingIndex


def _indexed_funding_return(
    source: FundingSource,
    entry_index: int,
    exit_index: int,
    side: Side,
    entry_fill_price: float,
) -> float:
    if isinstance(source, _FundingIndex):
        return source.funding_return(
            entry_index, exit_index, side, entry_fill_price
        )
    return _funding_return(
        source, entry_index, exit_index, side, entry_fill_price
    )


# --- costs (the only place in the repo that computes money) ------------------

def fee_fraction(fee_rate: float) -> float:
    """Per-side fee as a fraction of notional. Fails closed on bad input."""
    if fee_rate < 0.0:
        raise ValueError(f"fee_rate must be >= 0, got {fee_rate}")
    return fee_rate


def slippage_fraction(slippage_bps: float) -> float:
    """Per-side slippage (bps of notional) as a fraction. Fails closed."""
    if slippage_bps < 0.0:
        raise ValueError(f"slippage_bps must be >= 0, got {slippage_bps}")
    return slippage_bps * _BPS


def round_trip_cost(
    fee_rate: float,
    slippage_bps: float,
    side: Side,
    funding_return: float,
) -> CostBreakdown:
    """Total round-trip cost (entry + exit) as fractions of notional. Fee and
    slippage are charged on both sides (2x); funding is pre-computed from the
    funding tape."""
    fee = 2.0 * fee_fraction(fee_rate)
    slippage = 2.0 * slippage_fraction(slippage_bps)
    total = fee + slippage + funding_return
    return CostBreakdown(fee=fee, slippage=slippage, funding=funding_return,
                         total=total)


# --- outcome hash ------------------------------------------------------------

def _outcome_hash(outcome: TradeOutcome) -> str:
    """Canonical SHA-256 of fields that define the economic outcome.
    Byte-identical on any machine for the same inputs (RULES §14)."""
    payload = (
        f"{outcome.side}|{outcome.entry_index}|{outcome.exit_index}|"
        f"{outcome.exit_reason}|{outcome.entry_price:.16e}|"
        f"{outcome.exit_price:.16e}|{outcome.nominal_return:.16e}|"
        f"{outcome.risk_fraction:.16e}|{outcome.net_return:.16e}|"
        f"{outcome.net_r:.16e}|{outcome.mae_r:.16e}|{outcome.mfe_r:.16e}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# --- reference engine --------------------------------------------------------

def _build_outcome(
    spec: TradeSpec,
    *,
    exit_index: int,
    exit_reason: ExitReason,
    exit_price: float,
    nominal_price: float,
    worst_adverse: float,
    best_favorable: float,
    funding_events: FundingSource,
) -> TradeOutcome:
    """Finalize one outcome using the canonical scalar arithmetic order."""
    entry = spec.entry_price
    sign = 1.0 if spec.side == "LONG" else -1.0
    risk_fraction = abs(entry - spec.stop_price) / entry
    nominal_return = sign * (nominal_price - entry) / entry
    execution_return = sign * (exit_price - entry) / entry
    funding_return = _indexed_funding_return(
        funding_events, spec.entry_index, exit_index, spec.side, entry,
    )
    costs = round_trip_cost(
        fee_rate=spec.fee_rate,
        slippage_bps=spec.slippage_bps,
        side=spec.side,
        funding_return=funding_return,
    )
    net_return = execution_return - costs.total
    mae_r = worst_adverse / risk_fraction
    mfe_r = best_favorable / risk_fraction

    for name, val in (
        ("nominal_return", nominal_return),
        ("execution_return", execution_return),
        ("net_return", net_return),
        ("risk_fraction", risk_fraction),
        ("mae_r", mae_r),
        ("mfe_r", mfe_r),
    ):
        # These are arithmetic outputs over already validated numeric inputs;
        # avoid the public type-dispatch helper on this hottest path.
        if not math.isfinite(val):
            raise ValueError(
                f"non-finite output: {name}={val} — dirty data or overflow"
            )

    outcome = TradeOutcome(
        side=spec.side,
        entry_index=spec.entry_index,
        exit_index=exit_index,
        exit_reason=exit_reason,
        entry_price=entry,
        exit_price=exit_price,
        nominal_return=nominal_return,
        risk_fraction=risk_fraction,
        gross_return=execution_return,
        net_return=net_return,
        net_r=net_return / risk_fraction,
        mae_r=mae_r,
        mfe_r=mfe_r,
        costs=costs,
    )
    object.__setattr__(outcome, "outcome_hash", _outcome_hash(outcome))
    return outcome


def _simulate_unvalidated(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    spec: TradeSpec,
    funding_events: FundingSource,
) -> TradeOutcome:
    """Run one validated spec without repeating shared tape validation."""
    entry = spec.entry_price
    is_long = spec.side == "LONG"

    last_idx = spec.entry_index + spec.max_holding_bars
    exit_index = last_idx
    exit_reason: ExitReason = "time"
    exit_price = closes[last_idx]
    nominal_price = exit_price

    worst_adverse = 0.0
    best_favorable = 0.0

    for i in range(spec.entry_index + 1, last_idx + 1):
        hi, lo, op = highs[i], lows[i], opens[i]

        if is_long:
            adverse = (entry - lo) / entry
            favorable = (hi - entry) / entry
        else:
            adverse = (hi - entry) / entry
            favorable = (entry - lo) / entry
        if adverse > worst_adverse:
            worst_adverse = adverse
        if favorable > best_favorable:
            best_favorable = favorable

        if is_long:
            stop_hit = lo <= spec.stop_price
            target_hit = hi >= spec.target_price
        else:
            stop_hit = hi >= spec.stop_price
            target_hit = lo <= spec.target_price

        if stop_hit:
            nominal_price = spec.stop_price
            exit_price = (
                min(op, spec.stop_price) if is_long
                else max(op, spec.stop_price)
            )
            exit_index, exit_reason = i, "stop"
            break
        if target_hit:
            nominal_price = spec.target_price
            exit_price = (
                max(op, spec.target_price) if is_long
                else min(op, spec.target_price)
            )
            exit_index, exit_reason = i, "target"
            break

    return _build_outcome(
        spec,
        exit_index=exit_index,
        exit_reason=exit_reason,
        exit_price=exit_price,
        nominal_price=nominal_price,
        worst_adverse=worst_adverse,
        best_favorable=best_favorable,
        funding_events=funding_events,
    )


def _batch_group_key(spec: TradeSpec) -> tuple[object, ...]:
    """Specs sharing this key have an identical path until their time horizon."""
    return (
        spec.side,
        spec.entry_index,
        spec.entry_price,
        spec.stop_price,
        spec.target_price,
        spec.fee_rate,
        spec.slippage_bps,
    )


def _simulate_horizon_group(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    indexed_specs: Sequence[tuple[int, TradeSpec]],
    funding_events: FundingSource,
    outputs: list[TradeOutcome | None],
) -> list[tuple[int, int]]:
    """Scan one side/barrier group once for all checkpoint horizons.

    A stop/target path is identical for specs that only differ in
    ``max_holding_bars``. Shorter horizons time-exit before a later hit; all
    remaining horizons share the first hit. This removes repeated OHLC walks
    while retaining the canonical arithmetic and hashes.
    """
    first_spec = indexed_specs[0][1]
    if len(indexed_specs) == 1:
        position, spec = indexed_specs[0]
        outcome = _simulate_unvalidated(
            opens, highs, lows, closes, spec, funding_events
        )
        outputs[position] = outcome
        return [(spec.entry_index + 1, outcome.exit_index)]

    by_horizon: dict[int, list[tuple[int, TradeSpec]]] = {}
    for position, spec in indexed_specs:
        by_horizon.setdefault(spec.max_holding_bars, []).append((position, spec))
    horizons = sorted(by_horizon)
    max_horizon = horizons[-1]
    entry_index = first_spec.entry_index
    entry = first_spec.entry_price
    is_long = first_spec.side == "LONG"
    worst_adverse = 0.0
    best_favorable = 0.0
    next_horizon_index = 0
    intervals: list[tuple[int, int]] = []

    for i in range(entry_index + 1, entry_index + max_horizon + 1):
        hi, lo, op = highs[i], lows[i], opens[i]
        if is_long:
            adverse = (entry - lo) / entry
            favorable = (hi - entry) / entry
            stop_hit = lo <= first_spec.stop_price
            target_hit = hi >= first_spec.target_price
        else:
            adverse = (hi - entry) / entry
            favorable = (entry - lo) / entry
            stop_hit = hi >= first_spec.stop_price
            target_hit = lo <= first_spec.target_price
        if adverse > worst_adverse:
            worst_adverse = adverse
        if favorable > best_favorable:
            best_favorable = favorable

        elapsed = i - entry_index
        if stop_hit or target_hit:
            reason: ExitReason = "stop" if stop_hit else "target"
            nominal_price = (
                first_spec.stop_price if stop_hit else first_spec.target_price
            )
            if stop_hit:
                exit_price = (
                    min(op, first_spec.stop_price) if is_long
                    else max(op, first_spec.stop_price)
                )
            else:
                exit_price = (
                    max(op, first_spec.target_price) if is_long
                    else min(op, first_spec.target_price)
                )
            shared_outcome: TradeOutcome | None = None
            while next_horizon_index < len(horizons):
                horizon = horizons[next_horizon_index]
                if horizon < elapsed:
                    # This horizon was emitted as a time exit below.
                    next_horizon_index += 1
                    continue
                for position, spec in by_horizon[horizon]:
                    # max_holding_bars is not an outcome field. Once the first
                    # barrier is hit, every longer horizon has byte-identical
                    # immutable output, so build/hash it only once.
                    if shared_outcome is None:
                        shared_outcome = _build_outcome(
                            spec,
                            exit_index=i,
                            exit_reason=reason,
                            exit_price=exit_price,
                            nominal_price=nominal_price,
                            worst_adverse=worst_adverse,
                            best_favorable=best_favorable,
                            funding_events=funding_events,
                        )
                    outputs[position] = shared_outcome
                    intervals.append((entry_index + 1, i))
                next_horizon_index += 1
            break

        while (
            next_horizon_index < len(horizons)
            and horizons[next_horizon_index] == elapsed
        ):
            horizon = horizons[next_horizon_index]
            shared_time_outcome: TradeOutcome | None = None
            for position, spec in by_horizon[horizon]:
                if shared_time_outcome is None:
                    shared_time_outcome = _build_outcome(
                        spec,
                        exit_index=i,
                        exit_reason="time",
                        exit_price=closes[i],
                        nominal_price=closes[i],
                        worst_adverse=worst_adverse,
                        best_favorable=best_favorable,
                        funding_events=funding_events,
                    )
                outputs[position] = shared_time_outcome
                intervals.append((entry_index + 1, i))
            next_horizon_index += 1

    if any(outputs[position] is None for position, _ in indexed_specs):
        raise RuntimeError("internal batch simulator failed to emit an outcome")
    return intervals

def simulate(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    spec: TradeSpec,
    funding_events: Sequence[FundingEvent] | None = None,
) -> TradeOutcome:
    """Simulate one trade against OHLC bars and funding tape."""
    n = len(highs)
    if not (len(lows) == n and len(opens) == n and len(closes) == n):
        raise ValueError("opens, highs, lows, closes must have equal length")
    _validate_spec(spec, n)
    if funding_events is None:
        funding_events = ()

    outcome = _simulate_unvalidated(
        opens, highs, lows, closes, spec, funding_events
    )
    _validate_all_bars_used(
        highs, lows, opens, closes, spec.entry_index, outcome.exit_index
    )
    return outcome


def _simulate_batch_core(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    specs: Sequence[TradeSpec],
    funding_events: FundingSource,
    validated_bars: bytearray | None = None,
) -> list[TradeOutcome]:
    n = len(highs)
    if not specs:
        return []

    groups: dict[tuple[object, ...], list[tuple[int, TradeSpec]]] = {}
    for position, spec in enumerate(specs):
        _validate_spec(spec, n)
        groups.setdefault(_batch_group_key(spec), []).append((position, spec))

    outputs: list[TradeOutcome | None] = [None] * len(specs)
    intervals: list[tuple[int, int]] = []
    for indexed_specs in groups.values():
        intervals.extend(
            _simulate_horizon_group(
                opens, highs, lows, closes, indexed_specs,
                funding_events, outputs,
            )
        )

    intervals.sort()
    merged: list[list[int]] = []
    for left, right in intervals:
        if not merged or left > merged[-1][1] + 1:
            merged.append([left, right])
        elif right > merged[-1][1]:
            merged[-1][1] = right
    for left, right in merged:
        for index in range(left, right + 1):
            if validated_bars is not None and validated_bars[index]:
                continue
            _validate_bar(
                highs[index], lows[index], opens[index], closes[index], index
            )
            if validated_bars is not None:
                validated_bars[index] = 1

    if any(outcome is None for outcome in outputs):
        raise RuntimeError("internal batch simulator returned an incomplete result")
    return cast(list[TradeOutcome], outputs)


class SimulationContext:
    """Reusable lazy-validation context for repeated simulations on one tape.

    It preserves ``lab.sim`` economics while caching structural funding checks
    and successful OHLC validation across overlapping event horizons.
    """

    __slots__ = (
        "opens", "highs", "lows", "closes", "n",
        "_validated_bars", "_funding",
    )

    def __init__(
        self,
        opens: Sequence[float],
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
        funding_events: Sequence[FundingEvent] | None = None,
    ) -> None:
        n = len(highs)
        if not (len(lows) == n and len(opens) == n and len(closes) == n):
            raise ValueError("opens, highs, lows, closes must have equal length")
        self.opens = opens
        self.highs = highs
        self.lows = lows
        self.closes = closes
        self.n = n
        self._validated_bars = bytearray(n)
        self._funding = _FundingIndex(
            () if funding_events is None else funding_events
        )

    def simulate_batch(
        self, specs: Sequence[TradeSpec]
    ) -> list[TradeOutcome]:
        return _simulate_batch_core(
            self.opens, self.highs, self.lows, self.closes, specs,
            self._funding, self._validated_bars,
        )


def simulate_batch(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    specs: Sequence[TradeSpec],
    funding_events: Sequence[FundingEvent] | None = None,
) -> list[TradeOutcome]:
    """Reference-compatible grouped batch execution."""
    n = len(highs)
    if not (len(lows) == n and len(opens) == n and len(closes) == n):
        raise ValueError("opens, highs, lows, closes must have equal length")
    return _simulate_batch_core(
        opens, highs, lows, closes, specs,
        () if funding_events is None else funding_events,
    )

def _validate_spec(spec: TradeSpec, n: int) -> None:
    if spec.max_holding_bars < 1:
        raise ValueError(f"max_holding_bars must be >= 1, got {spec.max_holding_bars}")
    if spec.entry_index < 0:
        raise ValueError(f"entry_index must be >= 0, got {spec.entry_index}")
    if spec.entry_index + spec.max_holding_bars > n - 1:
        raise ValueError(
            "not enough forward bars: entry_index + max_holding_bars = "
            f"{spec.entry_index + spec.max_holding_bars} exceeds last index {n - 1}"
        )
    if spec.entry_price <= 0 or spec.stop_price <= 0 or spec.target_price <= 0:
        raise ValueError("entry, stop, and target prices must all be > 0")
    if not _finite_number(spec.entry_price):
        raise ValueError(f"entry_price must be finite, got {spec.entry_price}")
    if not _finite_number(spec.stop_price):
        raise ValueError(f"stop_price must be finite, got {spec.stop_price}")
    if not _finite_number(spec.target_price):
        raise ValueError(f"target_price must be finite, got {spec.target_price}")
    if spec.side == "LONG":
        if not (spec.stop_price < spec.entry_price < spec.target_price):
            raise ValueError("LONG requires stop < entry < target")
    else:
        if not (spec.target_price < spec.entry_price < spec.stop_price):
            raise ValueError("SHORT requires target < entry < stop")
