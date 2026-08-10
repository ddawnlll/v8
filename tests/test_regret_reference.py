"""Family E — reference parity (v0.2 section 14.2).

`tools/regret_reference.py` is written independently from
`docs/contracts/SIMULATION_TRUTH_SPEC.md`, not from `v8.simulator`. Agreement
on randomized synthetic paths certifies SEMANTIC CONSISTENCY between the two
readings of the same declared rules — it is not evidence about the market
and it does not extend beyond the narrow geometry subset both sides
implement here (no funding, no cost, no management extensions, no
`stop_ref`, FILL_AT_BAR_CLOSE only).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st

from v8.schema import CandidateDraft
from v8.simulator import CanonicalSimulator, risk_unit

from tools.regret_reference import reference_walk

DIRECTIONS = ('LONG', 'SHORT')


def _make_bars(closes):
    """Turn a list of close-like floats into OHLC bars with a little
    intrabar range around each close, deterministic given the input."""
    bars = []
    prev_close = closes[0]
    for c in closes:
        lo, hi = min(prev_close, c), max(prev_close, c)
        pad = max(0.01, (hi - lo) * 0.15)
        bars.append({'open': prev_close, 'high': hi + pad, 'low': lo - pad, 'close': c})
        prev_close = c
    return bars


@given(
    direction=st.sampled_from(DIRECTIONS),
    entry=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    unit=st.floats(min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False),
    stop_r=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
    target_r=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
    expiry_bars=st.integers(min_value=1, max_value=12),
    deltas=st.lists(st.floats(min_value=-3.0, max_value=3.0, allow_nan=False,
                              allow_infinity=False), min_size=1, max_size=20),
)
@settings(max_examples=150, deadline=None)
def test_reference_parity_on_randomized_paths(direction, entry, unit, stop_r,
                                              target_r, expiry_bars, deltas):
    closes = [entry]
    for d in deltas:
        closes.append(max(1.0, closes[-1] + d))
    future_bars = _make_bars(closes)[1:]   # entry bar excluded, matches sim.run's convention

    draft = CandidateDraft(
        expert_id='parity-probe', expert_version='v1', instrument='TESTUSDT',
        direction=direction, setup_fingerprint='x',
        risk_geometry={'stop_r': stop_r, 'target_r': target_r,
                       'expiry_bars': expiry_bars, 'risk_frac': unit / entry},
        birth_time=0, setup_anchor_event_id='anchor')
    # risk_unit derives the unit from risk_frac * entry_price — recompute it
    # the SAME way the canonical simulator will, so both sides use the
    # identical R denominator (a deliberately shared input, not a shared
    # implementation of the WALK itself).
    canonical_unit = risk_unit(draft, entry)

    sim = CanonicalSimulator(round_trip_cost_r=0.0, funding_rate_r=0.0)
    canonical = sim.run(draft, [{'open': entry, 'high': entry, 'low': entry,
                                 'close': entry}] + future_bars,
                        times=None, thesis_valid=None)

    ref = reference_walk(direction, entry, canonical_unit, stop_r, target_r,
                         expiry_bars, future_bars, cost_r=0.0)

    assert canonical.endpoint == ref.endpoint, (direction, entry, unit, stop_r,
                                                target_r, expiry_bars, closes)
    assert canonical.ambiguous_bars == ref.ambiguous_bars
    assert canonical.horizon_bars == ref.horizon_bars
    assert abs(canonical.net_r - ref.net_r) < 1e-9
    assert abs(canonical.mae_r - ref.mae_r) < 1e-9
    assert abs(canonical.mfe_r - ref.mfe_r) < 1e-9


def test_reference_parity_empty_future_matches_declared_convention():
    """Both sides must agree on the boundary case too (not just the happy
    path) — an empty future is EXPIRY/0.0 by the shared never-entered
    convention (cost_r=0 here, so -cost_r == 0.0)."""
    ref = reference_walk('LONG', 100.0, 1.0, 1.0, 1.0, 8, [], cost_r=0.0)
    assert ref.endpoint == 'EXPIRY'
    assert ref.net_r == 0.0
    assert ref.horizon_bars == 0
