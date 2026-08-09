"""Canonical Level-1 bar simulator (SIMULATION_TRUTH_SPEC).

Deterministic, costed, fill-at-bar-close policy. It is an attribution
control, not evidence that alpha and execution are independent.

Two execution modes, per CANDIDATE_LIFECYCLE_SPEC section 6:
- step(): the execution-ledger path — one bar at a time; positions live
  across decision clocks so exposure, heat, and management are measurable.
- run():  the counterfactual path — batch attribution of candidates that
  never entered the ledger (rejected/expired).

Both share one barrier/gap/cost policy. The entry bar is never inspected for
exits (no lookahead); on a same-bar stop+target touch the stop wins
(conservative); a stop fill uses the WORSE of the barrier and the bar open
(gap semantics); a target fill is exactly the barrier price.

UNITS. `stop_r`/`target_r`/`net_r`/`round_trip_cost_r` are R-multiples, never
fractional price returns. One R is an explicit price distance (`risk_unit`)
declared by the Expert's geometry — not the entry price level. A stop-out is
therefore exactly -1R minus cost regardless of instrument or stop width, which
is what makes portfolio heat (D-023) risk-normalised and what makes outcomes
from different geometries comparable at all.

EXCURSIONS. Every position carries running `mae_r`/`mfe_r` (max adverse /
favourable excursion in R). V7's audit found excursion far more predictable
than direction (ICs +0.124/+0.152 vs +0.015 signed-return), and the vendored
V7 simulator records both; dropping them would discard the only evidence that
can decide whether post-entry management is worth adding (O-013).

POSITION MANAGEMENT (EXEC-1..6, O-013). All declared, optional risk_geometry
keys; the default geometry (the pilots' frozen geometry) keeps step()/run()
byte-identical on every field that existed before this change set. Declared
management is a pure function of excursion + frozen keys:
- `breakeven_roll_at_mfe_r` (+ `breakeven_margin_r`, default = round_trip_cost_r):
  one-shot roll of the effective stop to entry +/- margin once mfe_r reaches
  the threshold (EX-01). Endpoint stays STOP.
- `trail_stop_atr`: chandelier trail — the effective stop ratchets to k*ATR
  behind the extreme (entry +/- mfe_r*unit) every bar (EX-05). Endpoint STOP.
- `scale_out_ratio` (> 0 enables) + `scale_out_at_mfe_r`: one-shot partial
  close of fraction f = stop_r/(stop_r+target_r) at bar close; the remainder
  continues. NON-TERMINAL: StepResult.closed_fraction < 1.0 and the lab records
  a PARTIAL_EXIT PositionAction (lifecycle), never an outcome and never an
  endpoint (EX-02/04).
- `time_exit_bars`: distinct endpoint TIME_EXIT at bar close once
  bars_held >= time_exit_bars and price has not reached stop/target (EX-09/12).
- `pyramid_add_rules`: DECLARED but P2 — pyramiding stays OFF; a draft that
  declares it fails closed (EX-03). The `midpoint_stop` primitive is implemented
  and tested.
Management updates apply from the bar AFTER the one that triggered them (a
bar-atomic OHLC cannot order intrabar events; a stop raised by this bar's
excursion never fires on the same bar).

FILL POLICIES (EXEC-4). SUPPORTED_FILL_POLICIES = FILL_AT_BAR_CLOSE (locked
baseline) | FILL_AT_LIMIT (barrier entry: fills at the declared
risk_geometry['limit_price'] when a bar's range trades through it; the entry
bar is inspected for a FILL only, never for exits; never-filling orders never
enter).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .schema import CandidateDraft, CounterfactualOutcome, sha1_hex

HOUR_NS = 3_600_000_000_000

# Hash-canary binding: sim.hash() must change when the simulator's SEMANTICS
# change, not only when the version tag is bumped by hand. Binding the module
# source makes any step/run/funding edit move every outcome's simulator_hash
# (the version tag still names the policy era for human readers).
_SIMULATOR_SRC_HASH = sha1_hex(Path(__file__).read_bytes())


def risk_unit(draft: CandidateDraft, entry_price: float) -> float:
    """Price distance of one R. Explicit and positive; never implied by price level.

    Preference order: the Expert's declared `atr_ref`, else a declared
    `risk_frac` of the entry price. A non-positive unit is a contract breach
    and fails closed rather than silently producing percent-shaped numbers.
    """
    atr = draft.risk_geometry.get('atr_ref')
    if atr is not None:
        unit = float(atr)
    elif 'risk_frac' in draft.risk_geometry:
        unit = entry_price * float(draft.risk_geometry['risk_frac'])
    else:
        # No default: a silently assumed 1% risk unit would make every trade
        # with missing geometry look risk-normalised (wrong-but-plausible).
        raise ValueError(
            f'risk_unit: geometry declares neither atr_ref nor risk_frac '
            f'({draft.risk_geometry!r})')
    if not unit > 0:
        raise ValueError(
            f'risk_unit must be > 0 (got {unit!r}); geometry declares neither a '
            f'positive atr_ref nor a positive risk_frac')
    return unit


def validate_geometry(draft: CandidateDraft) -> None:
    """Fail closed on risk_geometry that cannot produce a meaningful outcome
    (issue #70). A non-positive `target_r` puts the target on the LOSING side
    and the simulator would book the loss as a TARGET endpoint (a win in any
    downstream hit-rate / profit-factor statistic); a non-positive `stop_r` is
    not a position; an `expiry_bars` below 1 is not a horizon.

    Defense in depth, not a replacement: the experts that compute their
    geometry guard themselves (floor_trader_pivot & co), but the simulator is
    the last line — a new expert or a new variant that forgets its guard must
    fail loudly at step()/run() entry, never silently pollute the outcome
    ledger. Called at the top of both; the duplicate check on the same draft is
    a few dict reads, so the hot path cost is not a concern.
    """
    geom = draft.risk_geometry
    target_r = geom.get('target_r')
    stop_r = geom.get('stop_r')
    expiry = geom.get('expiry_bars')
    if target_r is not None and float(target_r) <= 0:
        raise ValueError(
            f'risk_geometry target_r must be > 0 (got {target_r!r}, '
            f'{draft.expert_id}): a non-positive target is on the losing side '
            'and would book losses as TARGET endpoints — fail closed')
    if stop_r is not None and float(stop_r) <= 0:
        raise ValueError(
            f'risk_geometry stop_r must be > 0 (got {stop_r!r}, '
            f'{draft.expert_id}): a zero-distance stop is not a position — '
            'fail closed')
    if expiry is not None and int(expiry) < 1:
        raise ValueError(
            f'risk_geometry expiry_bars must be >= 1 (got {expiry!r}, '
            f'{draft.expert_id}): a horizon below one bar is not a position — '
            'fail closed')
    # `atr_ref` / `risk_frac` positivity is enforced by risk_unit at entry.


@dataclass(frozen=True)
class OpenPosition:
    candidate_id: str
    draft: CandidateDraft
    entry_price: float
    entry_bar_index: int
    bars_held: int = 0
    mae_r: float = 0.0           # running max adverse excursion, R (>= 0)
    mfe_r: float = 0.0           # running max favourable excursion, R (>= 0)
    ambiguous_bars: int = 0      # bars that touched both barriers (STOP_FIRST applied)
    # Funding (SIMULATION_TRUTH_SPEC 3-5): entry decision clock, count of
    # settled funding boundaries, and cumulative funding cost in R (positive
    # reduces net_r; a LONG pays when the rate is positive, sign-adjusted).
    entry_time_ns: int | None = None
    settlements: int = 0
    funding_paid_r: float = 0.0
    # RM-01: the EFFECTIVE size this position was admitted at (draft.size
    # scaled by the O-016 drawdown ladder, equity.RiskState). R-multiples are
    # size-independent, so step()/run() never read it; the lab records it for
    # the equity feed and the sizing evidence (size x stop_r heat invariant,
    # D-023). A semantic field addition per CRIT-3: sim.hash() re-versions to
    # canonical-sim-v7 REGARDLESS of output byte-identity.
    size: float = 1.0
    # EXEC-1/2/3 position management (O-013). `stop_level` is the EFFECTIVE
    # dynamic stop once management has moved it (breakeven roll, chandelier
    # trail); None = the static geometry stop still applies. `stop_rolled` is
    # the one-shot breakeven-roll latch; `scaled_out` the one-shot scale-out
    # latch. `remaining` is the fraction of the position still held after
    # scale-outs (1.0 = no partial yet) and `realized_r` the R accumulated on
    # closed fractions (EXEC-2): total episode net_r at the terminal close is
    # `realized_r + remaining * leg_r - cost - funding`, so a scaled-out leg's
    # profit is not lost when the remainder later stops. `remaining` is a
    # MANAGEMENT fraction — `size` (the admission size, drawdown-scaled) never
    # enters the net_r formula, which keeps R-multiples size-independent
    # (D-028: a stop-out is -1R-cost whatever the effective size).
    stop_level: float | None = None
    stop_rolled: bool = False
    scaled_out: bool = False
    realized_r: float = 0.0
    remaining: float = 1.0


@dataclass(frozen=True)
class StepResult:
    closed: bool
    endpoint: str | None = None      # TARGET | STOP | EXPIRY | THESIS_INVALIDATED
    #                                  | TIME_EXIT (non-terminal: None)
    net_r: float | None = None
    label_status: str | None = None  # MATURE | RIGHT_CENSORED
    next_pos: OpenPosition | None = None
    funding_settled: int = 0         # funding_settled events booked this step
    # EXEC-2: fraction of the position closed this step. 1.0 = terminal (the
    # whole position exited); <1.0 = a non-terminal PARTIAL_EXIT — the
    # position continues at remaining*(1-f) with its stop unchanged. The
    # endpoint vocabulary is untouched by a partial (it is not an endpoint;
    # the lab records it as a lifecycle PositionAction).
    closed_fraction: float = 1.0


# The implemented fill policies. A manifest-declared policy outside this set
# must fail closed — a hash that claims a fill semantics the stepper does not
# implement is a lie (OPERATIONS_SPEC sections 1, 5: shadow/paper share one
# code path and the fill source is a manifest input, never a silent
# divergence).
#
# EXEC-4 (EX-11): FILL_AT_LIMIT is a barrier entry — the order rests at the
# declared risk_geometry['limit_price'] and fills on the first bar whose range
# trades through it (fill price = the limit exactly, conservative limit
# semantics). The entry bar is inspected for a FILL only, never for exits: the
# exit loop starts on the bar AFTER the fill bar, so the "entry bar is never
# inspected for exits" invariant (SIMULATION_TRUTH_SPEC) holds by construction.
# A limit that never trades through never enters (NOT_EXECUTED).
SUPPORTED_FILL_POLICIES = ('FILL_AT_BAR_CLOSE', 'FILL_AT_LIMIT')


def midpoint_stop(entry_price: float, add_price: float) -> float:
    """EXEC-3 (EX-03) primitive: midway stop between the original entry and a
    pyramiding add (`midpoint = (entry + add_price)/2`, the book's
    "roll both stops to midway between the two entry levels"). A pyramid add
    on the same (instrument, direction) is the SAME exposure with larger size
    (D-018 is per instrument-direction), so this is the correct stop for an
    add — if price reverses and takes out the midway stop, the second lot's
    profit neutralizes the first lot's loss. Pyramiding itself is P2 and stays
    OFF (a draft declaring `pyramid_add_rules` fails closed in step()); this
    function is the verified math primitive the P2 work builds on.
    """
    return (float(entry_price) + float(add_price)) / 2.0


class CanonicalSimulator:
    def __init__(self, round_trip_cost_r: float = 0.07,
                 funding_rate_r: float = 0.0, funding_hours: int = 8,
                 fill_policy: str = 'FILL_AT_BAR_CLOSE',
                 funding_schedule: tuple[tuple[int, float], ...] = (),
                 round_trip_cost_bps: float | None = None):
        if fill_policy not in SUPPORTED_FILL_POLICIES:
            raise ValueError(
                f'unsupported fill_policy {fill_policy!r}; implemented: '
                f'{SUPPORTED_FILL_POLICIES}')
        self.round_trip_cost_r = round_trip_cost_r
        # Cost in BASIS POINTS OF NOTIONAL. When set it REPLACES the flat R
        # charge:  cost_R = (bps / 1e4) * entry_price / risk_unit.
        #
        # Why this has to exist: `round_trip_cost_r` is already denominated in
        # R, so it is invariant to the R unit. Widening the risk unit rescales
        # the stop and the target but leaves the cost untouched — the "cost per
        # R falls as R widens" reasoning, which is true of a real venue fee, is
        # silently false in the flat-R model. A venue charges a fraction of
        # notional; only the bps form makes the R unit and the cost move
        # together, which is the whole point of an R-widening experiment.
        #
        # None keeps the flat-R path byte-identical, so existing ledgers and
        # golden tests reproduce exactly.
        if round_trip_cost_bps is not None and round_trip_cost_bps < 0:
            raise ValueError(
                f'round_trip_cost_bps must be >= 0 (got '
                f'{round_trip_cost_bps!r})')
        self.round_trip_cost_bps = round_trip_cost_bps
        self.funding_rate_r = funding_rate_r
        self.funding_hours = funding_hours
        self.fill_policy = fill_policy
        # Tape-driven funding (D-041): (boundary_time_ns, rate) pairs. When
        # non-empty it REPLACES the scalar funding_rate_r at each crossed
        # boundary (entry_price * rate / risk_unit, DATASET_SPEC 6.4); the
        # scalar stays as the no-funding-tape fallback. Schedule VALUES are
        # tape data bound by data_hash, never by sim.hash().
        self.funding_schedule = tuple(funding_schedule)
        self._schedule_map = dict(self.funding_schedule)

    def cost_r(self, entry_price: float, unit: float) -> float:
        """Round-trip cost of one episode, in R.

        THE single resolution point — every net_r site calls this rather than
        reading `round_trip_cost_r` directly, so the flat-R and bps forms can
        never drift apart (parallel-truth rule). Flat-R returns the constant
        unchanged, so the default path is byte-identical.
        """
        if self.round_trip_cost_bps is None:
            return self.round_trip_cost_r
        if not unit > 0:
            raise ValueError(
                f'cost_r: risk unit must be > 0 (got {unit!r}); a bps cost is '
                'undefined without a positive R denominator')
        return (self.round_trip_cost_bps / 10_000.0) * entry_price / unit

    def _boundaries_crossed(self, entry_ns: int, t_ns: int) -> int:
        """Funding boundaries B with entry_ns < B <= t_ns.

        Open at the start boundary (a hold starting exactly on a boundary is
        not double-settled) and closed at the end (a hold ending exactly on a
        boundary settles exactly once) — the V7 terminal-boundary defect was a
        missed settlement at exactly the end boundary.

        O(1) closed form: boundaries are integer hours divisible by
        funding_hours, counted in (entry_hour, t_hour]; the per-hour loop was
        O(period) per step (~195us for a 1-year hold).
        """
        if t_ns <= entry_ns or self.funding_hours <= 0:
            return 0
        a = entry_ns // HOUR_NS
        b = t_ns // HOUR_NS
        return b // self.funding_hours - a // self.funding_hours

    def _crossed_boundary_times(self, entry_ns: int, t_ns: int) -> list[int]:
        """Boundary TIMES B with entry_ns < B <= t_ns (the schedule path)."""
        if t_ns <= entry_ns or self.funding_hours <= 0:
            return []
        a = entry_ns // HOUR_NS
        b = t_ns // HOUR_NS
        first = (a // self.funding_hours + 1) * self.funding_hours
        last = (b // self.funding_hours) * self.funding_hours
        return [hour * HOUR_NS
                for hour in range(first, last + 1, self.funding_hours)]

    def _apply_funding(self, pos: OpenPosition, t_ns: int, unit: float
                       ) -> tuple[OpenPosition, int]:
        """Settle every boundary crossed since the position was last stepped;
        returns (position, number of funding_settled events this step).

        Scalar path (empty schedule): the pre-D-041 R-flat semantics,
        sign * funding_rate_r per boundary. Schedule path (non-empty): each
        crossed boundary settles sign * entry_price * rate / risk_unit
        (DATASET_SPEC 6.4); a boundary missing from the schedule fails closed
        (the tape funding coverage horizon must span every possible hold).
        """
        if pos.entry_time_ns is None:
            return pos, 0
        total = self._boundaries_crossed(pos.entry_time_ns, t_ns)
        new = total - pos.settlements
        if new <= 0:
            return pos, 0
        sign = 1.0 if pos.draft.direction == 'LONG' else -1.0
        if self.funding_schedule:
            crossed = self._crossed_boundary_times(pos.entry_time_ns, t_ns)
            cost = 0.0
            for boundary in crossed[pos.settlements:]:
                rate = self._schedule_map.get(boundary)
                if rate is None:
                    raise ValueError(
                        f'funding schedule missing boundary {boundary}: the '
                        'tape coverage horizon must span every crossed '
                        'boundary (D-041); fail closed')
                cost += sign * pos.entry_price * rate / unit
        else:
            cost = sign * self.funding_rate_r * new   # LONG pays when rate > 0
        return replace(pos, settlements=total,
                       funding_paid_r=pos.funding_paid_r + cost), new

    def step(self, pos: OpenPosition, bar: dict,
             thesis_valid: bool = True, bar_time: int | None = None) -> StepResult:
        validate_geometry(pos.draft)
        # Funding settles BEFORE any order/exit event of a bar whose decision
        # clock crosses a boundary while the position is held (event order 5,
        # SETTLEMENT_BEFORE_ORDERS). bar_time None = no venue time -> no funding
        # (backward-compatible with time-less callers). entry/unit are needed
        # by the schedule-driven funding path (entry_price * rate / risk_unit).
        entry = pos.entry_price
        unit = risk_unit(pos.draft, entry)
        if bar_time is not None:
            pos, new_settlements = self._apply_funding(pos, bar_time, unit)
        else:
            new_settlements = 0

        geom = pos.draft.risk_geometry
        long = pos.draft.direction == 'LONG'
        target_r = float(geom['target_r'])
        stop_r = float(geom['stop_r'])
        expiry = int(geom['expiry_bars'])
        sign = 1.0 if long else -1.0
        target = entry + sign * target_r * unit
        # Issue #63: a frozen STRUCTURAL stop (risk_geometry['stop_ref'], an
        # absolute price) is the static stop when declared — the stop's place
        # is the swept extreme / pattern level, not an ATR multiple of the
        # CURRENT entry. `stop_r * unit` is the fallback for experts without a
        # structural level. stop_r keeps its declared meaning (R-multiple; the
        # structural experts derive it from the frozen distance at detection),
        # so heat (size * stop_r, D-023) and the ledger's R units are
        # unchanged by the swap. A stop-out at the structural level is
        # sign*(stop_ref - entry)/unit R, which is the honest distance.
        stop_ref = geom.get('stop_ref')
        if stop_ref is not None:
            base_stop = float(stop_ref)
        else:
            base_stop = entry - sign * stop_r * unit
        # EXEC-1: the effective stop is the dynamic stop_level once management
        # has moved it (breakeven roll / chandelier trail), else the static
        # geometry stop. Management updates below apply from the NEXT bar — a
        # stop raised by this bar's excursion never fires on the same bar that
        # made the excursion (bar-atomic OHLC cannot order intrabar events, so
        # the conservative reading is that the new barrier did not exist while
        # this bar was trading).
        stop = pos.stop_level if pos.stop_level is not None else base_stop
        bars_held = pos.bars_held + 1
        high, low = float(bar['high']), float(bar['low'])

        # Excursions in R, before any exit decision: the best and worst the
        # position was ever worth, not the value it exited at.
        fav, adv = (high, low) if long else (low, high)
        mfe_r = max(pos.mfe_r, sign * (fav - entry) / unit, 0.0)
        mae_r = max(pos.mae_r, sign * (entry - adv) / unit, 0.0)

        hit_target = high >= target if long else low <= target
        hit_stop = low <= stop if long else high >= stop
        ambiguous = hit_target and hit_stop
        ambiguous_bars = pos.ambiguous_bars + (1 if ambiguous else 0)

        endpoint: str | None = None
        if hit_stop:                    # conservative: STOP_FIRST on ambiguity
            endpoint = 'STOP'
        elif hit_target:
            endpoint = 'TARGET'
        elif not thesis_valid:          # thesis died before price did
            endpoint = 'THESIS_INVALIDATED'
        # EXEC-5 (EX-09/10/12): a declared time-line exit — the position exits
        # at bar close once bars_held reaches time_exit_bars, as long as price
        # did not reach stop/target first. Distinct endpoint from EXPIRY (a
        # time exit is a declared management horizon, not the tape-end expiry).
        elif 'time_exit_bars' in geom and bars_held >= int(geom['time_exit_bars']):
            endpoint = 'TIME_EXIT'
        elif bars_held >= expiry:
            endpoint = 'EXPIRY'

        next_pos = replace(pos, bars_held=bars_held, mae_r=mae_r, mfe_r=mfe_r,
                           ambiguous_bars=ambiguous_bars)
        if endpoint is None:
            # --- EXEC-1/2/3 position management (all bar-close, non-terminal) --
            # Runs only when no terminal exit fires this bar; a bar that stops
            # or targets out is closed, never managed.
            #
            # Pyramiding (EXEC-3): the geometry key is DECLARED and documented
            # (the midpoint-stop math primitive is `midpoint_stop`), but full
            # pyramiding with midway stops is P2 and stays OFF — a draft that
            # requests it fails closed rather than silently trading a partial
            # implementation.
            if 'pyramid_add_rules' in geom:
                raise ValueError(
                    'pyramid_add_rules is declared but pyramiding is P2 and '
                    'not implemented (EXEC-3); a draft that requests it fails '
                    'closed — the declared key must be absent')
            stop_level = pos.stop_level
            stop_rolled = pos.stop_rolled
            # EXEC-1 breakeven roll (EX-01): once mfe_r reaches the declared
            # threshold, roll the stop to entry +/- breakeven_margin_r ("roll
            # slightly farther out to account for slippage and trading costs",
            # Ch28); the margin defaults to the round-trip cost. One-shot.
            if 'breakeven_roll_at_mfe_r' in geom and not stop_rolled \
                    and mfe_r >= float(geom['breakeven_roll_at_mfe_r']):
                margin = float(geom.get('breakeven_margin_r',
                                        self.cost_r(entry, unit)))
                stop_level = entry - sign * margin * unit
                stop_rolled = True
            # EXEC-1 trailing (EX-05, chandelier): trail the stop k*R behind
            # the extreme (entry +/- mfe_r*unit), ratcheting every bar — the
            # stop only moves toward profit. `trail_stop_atr` is k; the R unit
            # is the geometry's declared ATR-based risk unit, so the chandelier
            # is k x ATR as the book defines it.
            if 'trail_stop_atr' in geom:
                k = float(geom['trail_stop_atr'])
                trail = entry + sign * (mfe_r - k) * unit
                if stop_level is None:
                    stop_level = max(base_stop, trail) if long \
                        else min(base_stop, trail)
                else:
                    stop_level = max(stop_level, trail) if long \
                        else min(stop_level, trail)
            next_pos = replace(next_pos, stop_level=stop_level,
                               stop_rolled=stop_rolled)
            # EXEC-2 scale-out / partial exit (EX-02): on the bar whose mfe_r
            # crosses scale_out_at_mfe_r, close the fraction
            # f = stop_r/(stop_r+target_r) (the book's exact formula,
            # Ch28: Stopsize/(Stopsize+Reward)) at this bar's close; the
            # remainder continues at size*(1-f) with the stop unchanged. This
            # is a NON-TERMINAL event: closed_fraction < 1.0, endpoint stays
            # None, and the lab records a lifecycle PositionAction. Scale-out
            # is enabled only when scale_out_ratio > 0 (default 0 = off).
            if geom.get('scale_out_ratio', 0.0) > 0.0 and not pos.scaled_out \
                    and mfe_r >= float(geom['scale_out_at_mfe_r']):
                f = stop_r / (stop_r + target_r)
                leg_r = sign * (float(bar['close']) - entry) / unit
                next_pos = replace(next_pos,
                                   remaining=pos.remaining * (1 - f),
                                   # R realized on the closed fraction of the
                                   # ORIGINAL position = remaining * f * leg_r.
                                   realized_r=pos.realized_r
                                   + pos.remaining * f * leg_r,
                                   scaled_out=True)
                return StepResult(False, None, None, None, next_pos,
                                  funding_settled=new_settlements,
                                  closed_fraction=f)
            return StepResult(False, next_pos=next_pos,
                              funding_settled=new_settlements)

        if endpoint in ('EXPIRY', 'THESIS_INVALIDATED', 'TIME_EXIT'):
            exit_price = float(bar['close'])
        elif endpoint == 'TARGET':
            exit_price = target                       # limit semantics
        else:  # STOP, gap semantics: worse of barrier and bar open
            open_ = float(bar['open'])
            exit_price = min(stop, open_) if long else max(stop, open_)

        # EXEC-2 accounting: total episode net_r = the R realized on closed
        # fractions (realized_r) + the remaining fraction's final leg, minus
        # one round-trip cost and the funding paid. At remaining=1.0 with no
        # partial, realized_r == 0 and this is byte-identical to the pre-EXEC
        # formula (sign*(exit-entry)/unit - cost - funding). The admission
        # `size` never enters: R-multiples stay size-independent (D-028).
        net_r = pos.realized_r \
            + pos.remaining * (sign * (exit_price - entry) / unit) \
            - self.cost_r(entry, unit) - pos.funding_paid_r
        label = 'MATURE' if endpoint in ('TARGET', 'STOP', 'THESIS_INVALIDATED') \
            else 'RIGHT_CENSORED'
        return StepResult(True, endpoint, net_r, label, next_pos,
                          funding_settled=new_settlements)

    def close_out(self, pos: OpenPosition, final_close: float) -> float:
        """Net R of closing an open position at `final_close` (tape-end close).

        The single authority for the net formula: the lab's tape-end epilogue
        and any future force-close must call this instead of re-deriving it — a
        second copy of the formula in another module would silently diverge the
        moment the cost, funding or partial-exit accounting changes
        (parallel-truth rule). Same formula as step()'s terminal branch:
        `realized_r + size*(sign*(final-entry)/unit) - cost - funding_paid`.
        """
        sign = 1.0 if pos.draft.direction == 'LONG' else -1.0
        unit = risk_unit(pos.draft, pos.entry_price)
        return pos.realized_r \
            + pos.remaining * (sign * (final_close - pos.entry_price) / unit) \
            - self.cost_r(pos.entry_price, unit) - pos.funding_paid_r

    def _exit_loop(self, pos: OpenPosition, bars: list[dict],
                   times: list[int] | None, from_idx: int,
                   thesis_valid, placeholder: str, entry: float,
                   unit: float, horizon: int = 0) -> CounterfactualOutcome:
        """Step an open position to a terminal close or the tape end.

        Shared by both fill policies — the EXIT policy is identical; only the
        entry differs, so one copy of the loop (parallel-truth rule). `from_idx`
        is the first bar AFTER the entry/fill bar, preserving the invariant
        that the entry bar is never inspected for exits. `horizon` counts
        stepped bars so the two entry paths report consistent holding times.
        """
        for i, b in enumerate(bars[from_idx:], start=from_idx):
            horizon += 1
            tv = True
            if thesis_valid is not None and times is not None:
                tv = bool(thesis_valid(times[i], b))
            res = self.step(pos, b, thesis_valid=tv,
                            bar_time=times[i] if times else None)
            if res.closed and res.endpoint and res.net_r is not None:
                return CounterfactualOutcome(
                    placeholder, horizon, res.endpoint, res.net_r,
                    res.label_status or 'MATURE', self.hash(),
                    label_available_time=times[i] if times else 0,
                    mae_r=res.next_pos.mae_r if res.next_pos else 0.0,
                    mfe_r=res.next_pos.mfe_r if res.next_pos else 0.0,
                    ambiguous_bars=res.next_pos.ambiguous_bars if res.next_pos else 0,
                    entry_price=entry, risk_unit_price=unit,
                    # Passive move over the SAME window: entry to the exit
                    # bar's close, ignoring the barrier the position actually
                    # took. Unsigned by direction on purpose (D-045).
                    market_move_r=(float(b['close']) - entry) / unit)
            if res.next_pos is None:
                break
            pos = res.next_pos
        # Never closed within the tape: expire at the final close, in R.
        sign = 1.0 if pos.draft.direction == 'LONG' else -1.0
        net = pos.realized_r \
            + pos.remaining * (sign * (float(bars[-1]['close']) - entry) / unit) \
            - self.cost_r(entry, unit) - pos.funding_paid_r
        return CounterfactualOutcome(placeholder, horizon, 'EXPIRY', net,
                                     'RIGHT_CENSORED', self.hash(),
                                     label_available_time=times[-1] if times else 0,
                                     mae_r=pos.mae_r, mfe_r=pos.mfe_r,
                                     ambiguous_bars=pos.ambiguous_bars,
                                     entry_price=entry, risk_unit_price=unit,
                                     market_move_r=(float(bars[-1]['close'])
                                                    - entry) / unit)

    def _limit_entry(self, draft: CandidateDraft, bars: list[dict]
                     ) -> tuple[int, float] | None:
        """EXEC-4 (EX-11) fill-only inspection: the first bar whose range
        trades through the declared limit, and the limit price.

        LONG fills when low <= limit; SHORT fills when high >= limit. Fill
        price is the limit exactly (conservative limit semantics — a buy whose
        bar gaps below the limit still pays the limit). Returns None when no
        bar in the window trades through: the order never fills.
        """
        if 'limit_price' not in draft.risk_geometry:
            raise ValueError(
                'FILL_AT_LIMIT requires risk_geometry[limit_price] (a declared '
                'barrier); none declared — fail closed')
        limit = float(draft.risk_geometry['limit_price'])
        long = draft.direction == 'LONG'
        for i, b in enumerate(bars):
            hi, lo = float(b['high']), float(b['low'])
            if (long and lo <= limit) or (not long and hi >= limit):
                return i, limit
        return None

    def run(self, draft: CandidateDraft, bars: list[dict],
            times: list[int] | None = None,
            thesis_valid=None) -> CounterfactualOutcome:
        """Batch counterfactual: entry per the fill policy, entry bar never
        inspected for exits.

        The caller re-binds `candidate_id`; this path never sees the real id.
        `times` are the bars' decision clocks (parallel to `bars`) and drive
        funding settlement; None = no venue time -> no funding.

        Entry: FILL_AT_BAR_CLOSE fills at the first bar's close (the locked
        baseline); FILL_AT_LIMIT rests at the declared limit and fills when a
        bar's range trades through it (EXEC-4), or never enters (EXPIRY /
        NOT_EXECUTED) if no bar does. Both then step the position through the
        shared exit loop from the bar AFTER the fill, so the entry bar is
        inspected for a FILL only, never for exits (SIMULATION_TRUTH_SPEC).

        `thesis_valid(bar_time, bar_payload) -> bool` mirrors the owning Expert's
        post-entry thesis check on the executed path: a thesis that dies before
        price does closes at that bar's close (THESIS_INVALIDATED) instead of
        being held to STOP/TARGET/EXPIRY/TIME_EXIT. Without it the counterfactual
        and executed populations are computed under different exit policies (the
        O-014/D-027 attribution bias). Default None = thesis always valid, which
        keeps time-less/time-free callers byte-identical to prior behavior.
        """
        validate_geometry(draft)
        placeholder = f'cf:{draft.birth_time}'
        if not bars:
            return CounterfactualOutcome(placeholder, 0, 'EXPIRY', 0.0,
                                         'RIGHT_CENSORED', self.hash())
        if self.fill_policy == 'FILL_AT_LIMIT':
            found = self._limit_entry(draft, bars)
            if found is None:
                # The limit never traded through within the tape: the candidate
                # never entered. Never-entered convention: EXPIRY / 0.0 /
                # NOT_EXECUTED, knowable at the tape end.
                return CounterfactualOutcome(
                    placeholder, 0, 'EXPIRY', 0.0, 'NOT_EXECUTED', self.hash(),
                    label_available_time=times[-1] if times else 0)
            fill_idx, entry = found
            unit = risk_unit(draft, entry)
            entry_time = times[fill_idx] if times else None
            pos = OpenPosition(candidate_id=placeholder, draft=draft,
                               entry_price=entry, entry_bar_index=fill_idx,
                               entry_time_ns=entry_time)
            return self._exit_loop(pos, bars, times, fill_idx + 1,
                                   thesis_valid, placeholder, entry, unit)

        entry = float(bars[0]['close'])
        # One R in price at the fill actually used (D-045): recorded on every
        # outcome so the detrended null can be re-centered downstream without
        # re-deriving the denominator (which depends on the fill whenever the
        # draft declares risk_frac rather than atr_ref).
        unit = risk_unit(draft, entry)
        entry_time = times[0] if times else None
        pos = OpenPosition(candidate_id=placeholder, draft=draft,
                           entry_price=entry, entry_bar_index=0,
                           entry_time_ns=entry_time)
        return self._exit_loop(pos, bars, times, 1, thesis_valid,
                               placeholder, entry, unit)

    def hash(self) -> str:
        # v8: EXEC-1..6 (O-013 position management, this change set).
        # OpenPosition gained stop_level/stop_rolled/scaled_out/realized_r/
        # initial_size; step() gained the breakeven roll, the chandelier trail,
        # the scale-out partial exit and the TIME_EXIT endpoint; the endpoint
        # vocabulary gained TIME_EXIT; SUPPORTED_FILL_POLICIES gained
        # FILL_AT_LIMIT (EXEC-4). Even at fully-default geometry every step()
        # semantics changed, so every outcome re-versions REGARDLESS of output
        # byte-identity at the defaults. (The task brief said "bump to
        # canonical-sim-v6"; v6 and v7 were already taken by D-045 and the
        # CRIT-3 size field, so EXEC lands as v8 — one bump per semantic
        # change, the tag names the policy era.)
        #
        # v7: OpenPosition gained `size` (RM-01, CRIT-3). This re-versions
        # every outcome REGARDLESS of output byte-identity — the R-multiple
        # ledger is byte-identical at size=1.0, but the RECORD (and the
        # simulator's semantic vocabulary) changed, so a v6 ledger must never
        # compare equal to a v7 one. (_SIMULATOR_SRC_HASH already moved; the
        # tag names the policy era. The CRIT-3 instruction said "bump to v6";
        # v6 was already taken by the D-045 record change, so the size field
        # lands as v7 — the principle is a bump per semantic change.)
        #
        # v6: CounterfactualOutcome records entry_price / risk_unit_price /
        # market_move_r (D-045, the detrended null's inputs). No net_r, no
        # endpoint and no excursion changes value — every prior outcome is
        # byte-identical on its old fields — but the RECORD changed, so the
        # ledger re-versions rather than silently comparing equal to a v5 one.
        #
        # v5: tape-driven funding schedule (D-041). The version tag is part of
        # the hash so pre-change ledgers can never compare equal to post-change
        # ones; funding PARAMETERS bind into the hash but the schedule VALUES
        # are tape data bound by data_hash (SIMULATION_TRUTH_SPEC: outputs bind
        # simulator hash). v5 bumps regardless of funding_rate_r=0.0 because
        # the settlement policy changed.
        # The cost FORM binds too: a flat-R and a bps run that happen to price
        # one episode identically are still different policies, and their
        # ledgers must never compare equal.
        return sha1_hex(('canonical-sim-v8', self.fill_policy,
                         self.round_trip_cost_r, self.funding_rate_r,
                         self.funding_hours,
                         'flat' if self.round_trip_cost_bps is None
                         else f'bps:{self.round_trip_cost_bps}',
                         _SIMULATOR_SRC_HASH))
