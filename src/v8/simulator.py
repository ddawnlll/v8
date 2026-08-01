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
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .schema import CandidateDraft, CounterfactualOutcome, sha1_hex

HOUR_NS = 3_600_000_000_000


def risk_unit(draft: CandidateDraft, entry_price: float) -> float:
    """Price distance of one R. Explicit and positive; never implied by price level.

    Preference order: the Expert's declared `atr_ref`, else a declared
    `risk_frac` of the entry price. A non-positive unit is a contract breach
    and fails closed rather than silently producing percent-shaped numbers.
    """
    atr = draft.risk_geometry.get('atr_ref')
    unit = float(atr) if atr is not None else \
        entry_price * float(draft.risk_geometry.get('risk_frac', 0.01))
    if not unit > 0:
        raise ValueError(
            f'risk_unit must be > 0 (got {unit!r}); geometry declares neither a '
            f'positive atr_ref nor a positive risk_frac')
    return unit


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


@dataclass(frozen=True)
class StepResult:
    closed: bool
    endpoint: str | None = None      # TARGET | STOP | EXPIRY | THESIS_INVALIDATED
    net_r: float | None = None
    label_status: str | None = None  # MATURE | RIGHT_CENSORED
    next_pos: OpenPosition | None = None
    funding_settled: int = 0         # funding_settled events booked this step


# Only this fill policy is implemented. A manifest-declared policy outside
# this set must fail closed — a hash that claims a fill semantics the stepper
# does not implement is a lie (OPERATIONS_SPEC sections 1, 5: shadow/paper
# share one code path and the fill source is a manifest input, never a silent
# divergence).
SUPPORTED_FILL_POLICIES = ('FILL_AT_BAR_CLOSE',)


class CanonicalSimulator:
    def __init__(self, round_trip_cost_r: float = 0.07,
                 funding_rate_r: float = 0.0, funding_hours: int = 8,
                 fill_policy: str = 'FILL_AT_BAR_CLOSE'):
        if fill_policy not in SUPPORTED_FILL_POLICIES:
            raise ValueError(
                f'unsupported fill_policy {fill_policy!r}; implemented: '
                f'{SUPPORTED_FILL_POLICIES}')
        self.round_trip_cost_r = round_trip_cost_r
        self.funding_rate_r = funding_rate_r
        self.funding_hours = funding_hours
        self.fill_policy = fill_policy

    def _boundaries_crossed(self, entry_ns: int, t_ns: int) -> int:
        """Funding boundaries B with entry_ns < B <= t_ns.

        Open at the start boundary (a hold starting exactly on a boundary is
        not double-settled) and closed at the end (a hold ending exactly on a
        boundary settles exactly once) — the V7 terminal-boundary defect was a
        missed settlement at exactly the end boundary.
        """
        if t_ns <= entry_ns or self.funding_hours <= 0:
            return 0
        n = 0
        for hour in range(entry_ns // HOUR_NS + 1, t_ns // HOUR_NS + 1):
            if hour % self.funding_hours == 0:
                n += 1
        return n

    def _apply_funding(self, pos: OpenPosition, t_ns: int
                       ) -> tuple[OpenPosition, int]:
        """Settle every boundary crossed since the position was last stepped;
        returns (position, number of funding_settled events this step)."""
        if pos.entry_time_ns is None:
            return pos, 0
        total = self._boundaries_crossed(pos.entry_time_ns, t_ns)
        new = total - pos.settlements
        if new <= 0:
            return pos, 0
        sign = 1.0 if pos.draft.direction == 'LONG' else -1.0
        cost = sign * self.funding_rate_r * new      # LONG pays when rate > 0
        return replace(pos, settlements=total,
                       funding_paid_r=pos.funding_paid_r + cost), new

    def step(self, pos: OpenPosition, bar: dict,
             thesis_valid: bool = True, bar_time: int | None = None) -> StepResult:
        # Funding settles BEFORE any order/exit event of a bar whose decision
        # clock crosses a boundary while the position is held (event order 5,
        # SETTLEMENT_BEFORE_ORDERS). bar_time None = no venue time -> no funding
        # (backward-compatible with time-less callers).
        if bar_time is not None:
            pos, new_settlements = self._apply_funding(pos, bar_time)
        else:
            new_settlements = 0

        geom = pos.draft.risk_geometry
        long = pos.draft.direction == 'LONG'
        target_r = float(geom['target_r'])
        stop_r = float(geom['stop_r'])
        expiry = int(geom['expiry_bars'])
        entry = pos.entry_price
        unit = risk_unit(pos.draft, entry)
        sign = 1.0 if long else -1.0
        target = entry + sign * target_r * unit
        stop = entry - sign * stop_r * unit
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
        elif bars_held >= expiry:
            endpoint = 'EXPIRY'

        next_pos = replace(pos, bars_held=bars_held, mae_r=mae_r, mfe_r=mfe_r,
                           ambiguous_bars=ambiguous_bars)
        if endpoint is None:
            return StepResult(False, next_pos=next_pos,
                              funding_settled=new_settlements)

        if endpoint in ('EXPIRY', 'THESIS_INVALIDATED'):
            exit_price = float(bar['close'])
        elif endpoint == 'TARGET':
            exit_price = target                       # limit semantics
        else:  # STOP, gap semantics: worse of barrier and bar open
            open_ = float(bar['open'])
            exit_price = min(stop, open_) if long else max(stop, open_)

        net_r = sign * (exit_price - entry) / unit - self.round_trip_cost_r \
            - pos.funding_paid_r
        label = 'MATURE' if endpoint in ('TARGET', 'STOP', 'THESIS_INVALIDATED') \
            else 'RIGHT_CENSORED'
        return StepResult(True, endpoint, net_r, label, next_pos,
                          funding_settled=new_settlements)

    def run(self, draft: CandidateDraft, bars: list[dict],
            times: list[int] | None = None,
            thesis_valid=None) -> CounterfactualOutcome:
        """Batch counterfactual: entry at first bar close, entry bar not inspected.

        The caller re-binds `candidate_id`; this path never sees the real id.
        `times` are the bars' decision clocks (parallel to `bars`) and drive
        funding settlement; None = no venue time -> no funding.

        `thesis_valid(bar_time, bar_payload) -> bool` mirrors the owning Expert's
        post-entry thesis check on the executed path: a thesis that dies before
        price does closes at that bar's close (THESIS_INVALIDATED) instead of
        being held to STOP/TARGET/EXPIRY. Without it the counterfactual and
        executed populations are computed under different exit policies (the
        O-014/D-027 attribution bias). Default None = thesis always valid, which
        keeps time-less/time-free callers byte-identical to prior behavior.
        """
        placeholder = f'cf:{draft.birth_time}'
        if not bars:
            return CounterfactualOutcome(placeholder, 0, 'EXPIRY', 0.0,
                                         'RIGHT_CENSORED', self.hash())
        entry = float(bars[0]['close'])
        entry_time = times[0] if times else None
        pos = OpenPosition(candidate_id=placeholder, draft=draft,
                           entry_price=entry, entry_bar_index=0,
                           entry_time_ns=entry_time)
        horizon = 0
        for i, b in enumerate(bars[1:], start=1):
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
                    ambiguous_bars=res.next_pos.ambiguous_bars if res.next_pos else 0)
            if res.next_pos is None:
                break
            pos = res.next_pos
        # Never closed within the tape: expire at the final close, in R.
        sign = 1.0 if draft.direction == 'LONG' else -1.0
        unit = risk_unit(draft, entry)
        net = sign * (float(bars[-1]['close']) - entry) / unit \
            - self.round_trip_cost_r - pos.funding_paid_r
        return CounterfactualOutcome(placeholder, horizon, 'EXPIRY', net,
                                     'RIGHT_CENSORED', self.hash(),
                                     label_available_time=times[-1] if times else 0,
                                     mae_r=pos.mae_r, mfe_r=pos.mfe_r,
                                     ambiguous_bars=pos.ambiguous_bars)

    def hash(self) -> str:
        # v4: R-unit semantics + excursions + ambiguity counting + funding
        # settlement policy. The version tag is part of the hash so pre-fix
        # ledgers can never compare equal to post-fix ones; funding parameters
        # bind the schedule into the hash (SIMULATION_TRUTH_SPEC: outputs bind
        # simulator hash). v4 bumps regardless of funding_rate_r=0.0 because
        # the policy changed.
        return sha1_hex(('canonical-sim-v4', self.fill_policy,
                         self.round_trip_cost_r, self.funding_rate_r,
                         self.funding_hours))
