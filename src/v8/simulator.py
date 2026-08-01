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


@dataclass(frozen=True)
class StepResult:
    closed: bool
    endpoint: str | None = None      # TARGET | STOP | EXPIRY | THESIS_INVALIDATED
    net_r: float | None = None
    label_status: str | None = None  # MATURE | RIGHT_CENSORED
    next_pos: OpenPosition | None = None


class CanonicalSimulator:
    fill_policy = 'FILL_AT_BAR_CLOSE'

    def __init__(self, round_trip_cost_r: float = 0.07):
        self.round_trip_cost_r = round_trip_cost_r

    def step(self, pos: OpenPosition, bar: dict,
             thesis_valid: bool = True) -> StepResult:
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
            return StepResult(False, next_pos=next_pos)

        if endpoint in ('EXPIRY', 'THESIS_INVALIDATED'):
            exit_price = float(bar['close'])
        elif endpoint == 'TARGET':
            exit_price = target                       # limit semantics
        else:  # STOP, gap semantics: worse of barrier and bar open
            open_ = float(bar['open'])
            exit_price = min(stop, open_) if long else max(stop, open_)

        net_r = sign * (exit_price - entry) / unit - self.round_trip_cost_r
        label = 'MATURE' if endpoint in ('TARGET', 'STOP', 'THESIS_INVALIDATED') \
            else 'RIGHT_CENSORED'
        return StepResult(True, endpoint, net_r, label, next_pos)

    def run(self, draft: CandidateDraft, bars: list[dict]) -> CounterfactualOutcome:
        """Batch counterfactual: entry at first bar close, entry bar not inspected.

        The caller re-binds `candidate_id`; this path never sees the real id.
        """
        placeholder = f'cf:{draft.birth_time}'
        if not bars:
            return CounterfactualOutcome(placeholder, 0, 'EXPIRY', 0.0,
                                         'RIGHT_CENSORED', self.hash())
        entry = float(bars[0]['close'])
        pos = OpenPosition(candidate_id=placeholder, draft=draft,
                           entry_price=entry, entry_bar_index=0)
        horizon = 0
        for b in bars[1:]:
            horizon += 1
            res = self.step(pos, b)
            if res.closed and res.endpoint and res.net_r is not None:
                return CounterfactualOutcome(
                    placeholder, horizon, res.endpoint, res.net_r,
                    res.label_status or 'MATURE', self.hash(),
                    mae_r=res.next_pos.mae_r if res.next_pos else 0.0,
                    mfe_r=res.next_pos.mfe_r if res.next_pos else 0.0,
                    ambiguous_bars=res.next_pos.ambiguous_bars if res.next_pos else 0)
            if res.next_pos is None:
                break
            pos = res.next_pos
        # Never closed within the tape: expire at the final close, in R.
        sign = 1.0 if draft.direction == 'LONG' else -1.0
        unit = risk_unit(draft, entry)
        net = sign * (float(bars[-1]['close']) - entry) / unit - self.round_trip_cost_r
        return CounterfactualOutcome(placeholder, horizon, 'EXPIRY', net,
                                     'RIGHT_CENSORED', self.hash(),
                                     mae_r=pos.mae_r, mfe_r=pos.mfe_r,
                                     ambiguous_bars=pos.ambiguous_bars)

    def hash(self) -> str:
        # v3: R-unit semantics + excursions + ambiguity counting. The version
        # tag is part of the hash so pre-fix ledgers can never compare equal
        # to post-fix ones (SIMULATION_TRUTH_SPEC: outputs bind simulator hash).
        return sha1_hex(('canonical-sim-v3', self.fill_policy, self.round_trip_cost_r))
