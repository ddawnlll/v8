"""Verify the #69 fix: the excess-cost gate firing is surfaced as a FEASIBILITY
note in the report, with the threshold<->bps mapping recorded (D-063).

The fix is report-only annotation on top of an unchanged gate
(EXCESS_COST_THRESHOLD_R stays 0.10; the ATR/bps math is untouched). So this
script asserts the NEW surfacing behavior while confirming the economic
headline is unchanged from the baseline (0 executed at cost 0.125, >0 at 0.07).

Assertions (issue acceptance criteria + verify contract):
  1. ATR/bps math is unchanged: threshold_bps in [4.5, 5.1] (baseline 4.78),
     one_r_bps ~ 47.75.
  2. At round_trip_cost_r=0.125: report.economic_note contains 'excess_cost'
     AND n_executed == 0.
  3. At round_trip_cost_r=0.07: n_executed > 0 AND the note does NOT contain
     'excess_cost' (the gate must not fire below the threshold).
"""
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import load_window, run_lab, UNIVERSE, INTERVAL, _series_for  # noqa: E402
from v8.lab import EXCESS_COST_THRESHOLD_R  # noqa: E402
from v8.marketstate import build_multi_state  # noqa: E402

N_BARS = 2500
ATR_PERIOD = 14


def atr_price_series(bars):
    fracs = []
    for i in range(len(bars)):
        window = bars[max(0, i - ATR_PERIOD + 1):i + 1]
        if len(window) < ATR_PERIOD:
            continue
        atr = sum(float(b.payload['high']) - float(b.payload['low'])
                  for b in window) / ATR_PERIOD
        fracs.append(atr / float(bars[i].payload['close']))
    return fracs


def main():
    rows = load_window(n_bars=N_BARS)
    bars = [r for r in rows if r.channel == 'kline'
            and r.payload.get('closed') is True][:N_BARS]
    assert len(bars) == N_BARS, f'expected {N_BARS} bars, got {len(bars)}'

    mean_frac = statistics.fmean(atr_price_series(bars))
    one_r_bps = mean_frac * 1e4
    threshold_bps = EXCESS_COST_THRESHOLD_R * one_r_bps

    # (1) math unchanged vs baseline (4.7753808218136875 * 0.10).
    assert EXCESS_COST_THRESHOLD_R == 0.10, 'gate constant must stay 0.10'
    assert abs(one_r_bps - 47.753808218136875) < 1e-6, f'one_r_bps drifted: {one_r_bps}'
    assert 4.5 <= threshold_bps <= 5.1, f'threshold_bps out of range: {threshold_bps}'
    print(f'[1] math unchanged: one_r_bps={one_r_bps:.4f} '
          f'threshold_bps={threshold_bps:.4f} (gate {EXCESS_COST_THRESHOLD_R})')

    # (2) at realistic taker cost 0.125 (>= 0.10 gate) -> note + zero trades.
    _, r125 = run_lab(rows, round_trip_cost_r=0.125)
    note125 = r125.economic_note or ''
    assert 'excess_cost' in note125, '0.125 note must surface excess_cost'
    assert r125.n_executed == 0, f'0.125 should execute 0, got {r125.n_executed}'
    assert r125.verdict == 'NO_ECONOMIC_CLAIM'
    print(f'[2] 0.125: n_executed=0, note contains excess_cost -> '
          f'{note125}')

    # (3) at default 0.07 (< 0.10 gate) -> executes, no excess_cost note.
    _, r07 = run_lab(rows, round_trip_cost_r=0.07)
    note07 = r07.economic_note or ''
    assert r07.n_executed > 0, f'0.07 should execute >0, got {r07.n_executed}'
    assert 'excess_cost' not in note07, \
        '0.07 note must NOT contain excess_cost (gate must not fire)'
    print(f'[3] 0.07: n_executed={r07.n_executed}, no excess_cost in note -> '
          f'{note07}')

    print('OK: #69 fix verified — gate value unchanged, surfacing present.')


if __name__ == '__main__':
    main()
