"""Independent reference Replay Model, for semantic-parity certification only
(v0.2 section 14.2 — "Maintain a slow, transparent reference evaluator and a
fast optimized evaluator... Optimization is accepted only if semantic parity
holds").

Written from `docs/contracts/SIMULATION_TRUTH_SPEC.md` directly, NOT from
`v8.simulator` — it must not import it, and it deliberately does not share a
line of implementation. Agreement between the two is evidence of SEMANTIC
CONSISTENCY only; it certifies that two independent readings of the same
declared rules produce the same numbers, and it is not evidence about the
market (v0.2 section 14, "agreement between implementations certifies
semantic consistency only; it cannot by itself validate a shared Replay
Model against the real market").

Implements a deliberately NARROW subset of `CanonicalSimulator`: a single
FILL_AT_BAR_CLOSE entry, a static R-multiple stop/target (no `stop_ref`
structural stop), zero cost, zero funding, and none of the EXEC-1..6
position-management extensions. This is the geometry every one of the 28
registered Experts declares by default; the parity test in
`tests/test_regret_reference.py` is scoped to exactly this subset and must
not be read as certifying the extensions this file does not implement.
"""
from __future__ import annotations

from dataclasses import dataclass

REFERENCE_VERSION = 'regret-reference-v1'


@dataclass(frozen=True)
class ReferenceOutcome:
    endpoint: str          # TARGET | STOP | EXPIRY
    net_r: float
    horizon_bars: int
    mae_r: float
    mfe_r: float
    ambiguous_bars: int


def reference_walk(direction: str, entry_price: float, unit: float,
                   stop_r: float, target_r: float, expiry_bars: int,
                   future_bars: list, cost_r: float = 0.0) -> ReferenceOutcome:
    """One independently-derived FILL_AT_BAR_CLOSE walk.

    SIMULATION_TRUTH_SPEC rules this implements, read directly off the
    contract text (section "Canonical Level-1 event order" and "Units,
    excursions, and ambiguity"):
      - the entry bar is never inspected for exits: `future_bars` must
        already exclude it (the caller passes bars[1:], entry = bars[0].close);
      - for a bar touching both barriers, record the ambiguity and resolve
        STOP_FIRST (conservative);
      - a gap-through stop exits at the WORSE of the barrier and the bar's
        open; a target exits exactly at the barrier (limit semantics);
      - mae_r/mfe_r are the running best/worst excursion, recorded BEFORE
        any exit decision on that bar;
      - a stop-out is exactly -1R minus cost, independent of instrument or
        stop width, because R is the Expert's own declared price distance.
    """
    if not future_bars:
        return ReferenceOutcome('EXPIRY', -cost_r, 0, 0.0, 0.0, 0)

    sign = 1.0 if direction == 'LONG' else -1.0
    target = entry_price + sign * target_r * unit
    stop = entry_price - sign * stop_r * unit
    mae_r = mfe_r = 0.0
    ambiguous_bars = 0

    for i, bar in enumerate(future_bars, start=1):
        high, low, open_, close = bar['high'], bar['low'], bar['open'], bar['close']
        favorable, adverse = (high, low) if direction == 'LONG' else (low, high)
        mfe_r = max(mfe_r, sign * (favorable - entry_price) / unit, 0.0)
        mae_r = max(mae_r, sign * (entry_price - adverse) / unit, 0.0)

        hit_target = high >= target if direction == 'LONG' else low <= target
        hit_stop = low <= stop if direction == 'LONG' else high >= stop
        if hit_target and hit_stop:
            ambiguous_bars += 1

        if hit_stop:
            exit_price = min(stop, open_) if direction == 'LONG' else max(stop, open_)
            net_r = sign * (exit_price - entry_price) / unit - cost_r
            return ReferenceOutcome('STOP', net_r, i, mae_r, mfe_r, ambiguous_bars)
        if hit_target:
            net_r = sign * (target - entry_price) / unit - cost_r
            return ReferenceOutcome('TARGET', net_r, i, mae_r, mfe_r, ambiguous_bars)
        if i >= expiry_bars:
            net_r = sign * (close - entry_price) / unit - cost_r
            return ReferenceOutcome('EXPIRY', net_r, i, mae_r, mfe_r, ambiguous_bars)

    close = future_bars[-1]['close']
    net_r = sign * (close - entry_price) / unit - cost_r
    return ReferenceOutcome('EXPIRY', net_r, len(future_bars), mae_r, mfe_r, ambiguous_bars)
