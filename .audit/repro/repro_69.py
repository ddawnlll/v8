"""Repro for issue #69 — EXCESS_COST_THRESHOLD_R=0.10 below realistic taker cost.

Claim (issue body): lab.py EXCESS_COST_THRESHOLD_R=0.10 corresponds to ~6.39 bps
on BTCUSDT 1h (1R ~63.9 bps), below every realistic taker round trip (8-10 bps).
So at an honest cost the lab rejects everything; the default 0.07 sits just
under the gate to keep it from firing.

Repro:
  1. ATR(14)/price mean and median over the 2500-bar window (marketstate formula:
     atr = mean of last-14 (high-low) ranges), cross-checked against the shipped
     `BTCUSDT.atr` feature at the last bar -> 1R in bps; then threshold bps
     (0.10 * 1R_bps) and default-cost bps (0.07 * 1R_bps).
  2. run_lab at round_trip_cost_r=0.125 (realistic taker 8bps):
     terminal_distribution, rejection_distribution, n_executed.
  3. run_lab at 0.07: same fields for contrast.

Deterministic: no wall clock, no randomness in the decision path.
"""
import json
import statistics
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (load_window, run_lab, UNIVERSE, INTERVAL,
                       _series_for, TAPE_PATH)  # noqa: E402
from v8.lab import EXCESS_COST_THRESHOLD_R  # noqa: E402
from v8.schema import ExperimentManifest  # noqa: E402
from v8.marketstate import build_multi_state  # noqa: E402
from v8.store import AppendOnlyLog  # noqa: E402

N_BARS = 2500
ATR_PERIOD = 14


def atr_price_series(bars):
    """Per-bar ATR(period)/close, computed exactly like the shipped feature
    (marketstate.py:973: sum of last-14 (high-low) / 14)."""
    fracs = []
    for i in range(len(bars)):
        window = bars[max(0, i - ATR_PERIOD + 1):i + 1]
        if len(window) < ATR_PERIOD:
            continue
        atr = sum(float(b.payload['high']) - float(b.payload['low'])
                  for b in window) / ATR_PERIOD
        close = float(bars[i].payload['close'])
        fracs.append(atr / close)
    return fracs


def shipped_atr_frac_at_last_bar(rows):
    """Cross-check: the state's emitted BTCUSDT.atr feature at the last bar,
    normalized by the last close."""
    rows = sorted(rows, key=lambda r: r.available_time)
    bars = [r for r in rows if r.channel == 'kline'
            and r.payload.get('closed') is True][:N_BARS]
    last_bar = bars[-1]
    acc = [r for r in rows if r.available_time <= last_bar.available_time]
    series = _series_for(acc)
    state = build_multi_state(acc, last_bar.available_time, UNIVERSE,
                              base_interval=INTERVAL, intervals=(),
                              depths={}, series=series)
    f = state.features.get('BTCUSDT.atr')
    atr = float(f.value) if f is not None else None
    close = float(last_bar.payload['close'])
    return (atr / close) if atr else None


def main():
    rows = load_window(n_bars=N_BARS)
    bars = [r for r in rows if r.channel == 'kline'
            and r.payload.get('closed') is True][:N_BARS]
    assert len(bars) == N_BARS, f'expected {N_BARS} bars, got {len(bars)}'

    fracs = atr_price_series(bars)
    mean_frac = statistics.fmean(fracs)
    median_frac = statistics.median(fracs)

    shipped_frac = shipped_atr_frac_at_last_bar(rows)

    # 1R in bps uses the window-mean ATR/price fraction.
    def to_bps(r_fraction):
        return r_fraction * 1e4

    one_r_bps = to_bps(mean_frac)
    threshold_bps = EXCESS_COST_THRESHOLD_R * one_r_bps
    default_cost_bps = 0.07 * one_r_bps
    realistic_cost_bps = 0.125 * one_r_bps  # taker 4bp/side, no slippage

    # (2) run at realistic taker cost 0.125 R (>= 0.10 threshold).
    lab125, report125 = run_lab(rows, round_trip_cost_r=0.125)
    # (3) run at the manifest default 0.07 R (just under the threshold).
    lab07, report07 = run_lab(rows, round_trip_cost_r=0.07)

    evidence = {
        'issue': 69,
        'excess_cost_threshold_r': EXCESS_COST_THRESHOLD_R,
        'manifest_default_cost_r': 0.07,
        'atr_price_frac': {
            'mean': mean_frac,
            'median': median_frac,
            'shipped_feature_at_last_bar': shipped_frac,
        },
        'one_r_bps': one_r_bps,
        'threshold_bps': threshold_bps,
        'default_cost_bps': default_cost_bps,
        'realistic_cost_bps': realistic_cost_bps,
        'run_at_0_125': {
            'round_trip_cost_r': 0.125,
            'terminal_distribution': report125.terminal_distribution,
            'rejection_distribution': report125.rejection_distribution,
            'n_executed': report125.n_executed,
            'candidate_count': report125.candidate_count,
            'verdict': report125.verdict,
            'economic_note': report125.economic_note,
        },
        'run_at_0_07': {
            'round_trip_cost_r': 0.07,
            'terminal_distribution': report07.terminal_distribution,
            'rejection_distribution': report07.rejection_distribution,
            'n_executed': report07.n_executed,
            'candidate_count': report07.candidate_count,
            'verdict': report07.verdict,
            'economic_note': report07.economic_note,
        },
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    out = Path(__file__).resolve().parent / 'out' / '69.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n',
                   encoding='utf-8')


if __name__ == '__main__':
    main()
