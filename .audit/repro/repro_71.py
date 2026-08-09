"""Repro for issue #71 — gap asymmetry: adverse gap fully paid, favorable gap
clipped at the barrier.

Structure verified against the CURRENT tree's src/v8/simulator.py:403-409:

    if endpoint in ('EXPIRY', 'THESIS_INVALIDATED', 'TIME_EXIT'):
        exit_price = float(bar['close'])
    elif endpoint == 'TARGET':
        exit_price = target                       # limit semantics
    else:  # STOP, gap semantics: worse of barrier and bar open
        open_ = float(bar['open'])
        exit_price = min(stop, open_) if long else max(stop, open_)

Part (1): dynamic, direct simulator — a LONG position entry=100, atr_ref=10,
stop_r=target_r=1.0 (stop 90 / target 110), fed a bar gapped 20 units through
each barrier, then the other. Part (2): real-tape gap rate over the first 2500
closed bars (fraction of bar transitions where TR > (H-L), and where open ==
prev_close). Deterministic; no wall clock; fixed cost 0.07R.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', 'src')))

from lab_probe import TAPE_PATH, load_window  # noqa: E402
from v8.schema import CandidateDraft  # noqa: E402
from v8.simulator import CanonicalSimulator, OpenPosition  # noqa: E402

COST_R = 0.07
ENTRY = 100.0
UNIT = 10.0          # atr_ref
STOP = ENTRY - UNIT  # 90
TARGET = ENTRY + UNIT  # 110


def make_draft() -> CandidateDraft:
    return CandidateDraft(
        expert_id='audit-issue71',
        expert_version='0',
        instrument='BTCUSDT',
        direction='LONG',
        setup_fingerprint='issue71-gap-asymmetry',
        risk_geometry={'atr_ref': UNIT, 'target_r': 1.0, 'stop_r': 1.0,
                       'expiry_bars': 8},
        birth_time=0,
        setup_anchor_event_id='issue71-anchor',
    )


def outcome_for(bar_open: float) -> dict:
    """Step a fresh LONG position at ENTRY through a single gap bar."""
    sim = CanonicalSimulator(round_trip_cost_r=COST_R)
    pos = OpenPosition(candidate_id=f'issue71-{bar_open}', draft=make_draft(),
                       entry_price=ENTRY, entry_bar_index=0)
    bar = {'open': bar_open, 'high': bar_open, 'low': bar_open,
           'close': bar_open}
    res = sim.step(pos, bar)
    # exit_price reconstructed from the sim's own net_r (unique given
    # remaining=1.0, no funding): sign*(exit-entry)/unit - cost = net_r
    exit_price = ENTRY + (res.net_r + COST_R) * UNIT
    return {'endpoint': res.endpoint, 'net_r': res.net_r,
            'exit_price': round(exit_price, 4), 'bar_open': bar_open,
            'gap_units': bar_open - ENTRY}


def main() -> None:
    adverse = outcome_for(70.0)    # gaps 20 units through the stop
    favorable = outcome_for(130.0)  # gaps 20 units through the target

    # Counterfactual: what the favorable leg would have netted had the model
    # paid the favorable gap (fill at open instead of clipped at target).
    favorable_gap_paid_net_r = (130.0 - ENTRY) / UNIT - COST_R  # +2.93
    asymmetry_R = abs(adverse['net_r']) / favorable['net_r']

    # Part (2): real-tape gap rate over the first 2500 closed bars.
    rows = load_window(tape_path=TAPE_PATH, n_bars=2500)
    bars = [r for r in rows if r.channel == 'kline'
            and r.payload.get('closed') is True][:2500]
    transitions = 0
    n_gap = 0
    n_open_eq_prev = 0
    prev_close = None
    for b in bars:
        p = b.payload
        h, l, o, c = p['high'], p['low'], p['open'], p['close']
        if prev_close is not None:
            transitions += 1
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
            if tr > (h - l):
                n_gap += 1
            if o == prev_close:
                n_open_eq_prev += 1
        prev_close = c

    evidence = {
        'issue': 71,
        'title': ('Gap asymmetry: adverse gap fully paid, favorable gap '
                  'clipped at barrier'),
        'reproduced': True,
        'claim': ('simulator step() STOP fills use the worse of barrier and '
                  'bar open (gap semantics) while TARGET fills use exactly the '
                  'barrier; equal-magnitude opposing gaps yield asymmetric R'),
        'adverse_gap_outcome': adverse,
        'favorable_gap_outcome': favorable,
        'asymmetry_R': round(asymmetry_R, 4),
        'favorable_gap_paid_if_open_net_r': round(favorable_gap_paid_net_r, 4),
        'favorable_clip_r': round(favorable_gap_paid_net_r - favorable['net_r'], 4),
        'geometry': {'entry': ENTRY, 'stop': STOP, 'target': TARGET,
                     'atr_ref': UNIT, 'cost_r': COST_R},
        'tape_gap_frac': round(n_gap / transitions, 6),
        'tape_open_eq_prevclose_frac': round(n_open_eq_prev / transitions, 6),
        'tape_stats': {'bars': len(bars), 'transitions': transitions,
                       'n_gap_bars': n_gap,
                       'n_open_eq_prevclose_bars': n_open_eq_prev},
    }
    out = json.dumps(evidence, indent=2, sort_keys=True)
    print(out)
    out_dir = os.path.join(_HERE, 'out')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, '71.json'), 'w') as fh:
        fh.write(out + '\n')


if __name__ == '__main__':
    main()
