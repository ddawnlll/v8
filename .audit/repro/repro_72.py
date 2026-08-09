"""Repro for issue #72: synth.py generates unrealistic bar-to-bar gaps.

Claim: make_synthetic_tape generates each bar's open independently of the
previous close (o = price/(1+uniform)), so the synthetic tape has gap-like
continuity breaks that real continuously-traded perps do not have.

Repro:
  (1) static: quote the open-generation line from src/v8/synth.py
  (2) dynamic continuity stats on make_synthetic_tape(seed=7, n_bars=2500)
      vs the real BTCUSDT 1h tape window:
        - fraction of bars where TR > (H-L)            (a gap)
        - fraction where open == prev close
        - mean |open - prev_close| / prev_close
  (3) golden regression test result (tests/test_golden_backtest.py -q)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path('/Users/hootie/src/v8')
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import load_window  # noqa: E402
from v8.synth import make_synthetic_tape  # noqa: E402

# --------------------------------------------------------------------------
# (1) static — the open-generation line in the CURRENT tree
# --------------------------------------------------------------------------
synth_src = (REPO / 'src/v8/synth.py').read_text()
lines = synth_src.splitlines()
OPEN_LINE_NO = 23
open_line = lines[OPEN_LINE_NO - 1].strip()
# The full per-bar block for context:
block = '\n'.join(lines[20:26])


def continuity_stats(payloads):
    """Return gap/equality stats over consecutive bars (i >= 1)."""
    n = len(payloads)
    gap = 0
    open_eq = 0
    sum_gap_frac = 0.0
    for i in range(1, n):
        o = payloads[i]['open']
        h = payloads[i]['high']
        l = payloads[i]['low']
        c = payloads[i]['close']
        pc = payloads[i - 1]['close']
        hl = h - l
        tr = max(hl, abs(h - pc), abs(l - pc))
        if tr > hl:
            gap += 1
        if o == pc:
            open_eq += 1
        sum_gap_frac += abs(o - pc) / pc
    denom = n - 1
    return {
        'gap_frac': gap / denom,
        'open_eq_prev': open_eq / denom,
        'mean_gap_frac': sum_gap_frac / denom,
    }


# --------------------------------------------------------------------------
# (2) dynamic continuity stats
# --------------------------------------------------------------------------
synth_rows = make_synthetic_tape(seed=7, n_bars=2500)
synth_payloads = [r.payload for r in synth_rows]
assert len(synth_payloads) == 2500

real_rows = load_window(n_bars=2500)
real_payloads = [r.payload for r in real_rows
                 if r.channel == 'kline'
                 and r.payload.get('closed') is True][:2500]

synth_stats = continuity_stats(synth_payloads)
real_stats = continuity_stats(real_payloads)

# --------------------------------------------------------------------------
# (3) golden regression test
# --------------------------------------------------------------------------
proc = subprocess.run(
    [str(REPO / '.venv/bin/python'), '-m', 'pytest',
     'tests/test_golden_backtest.py', '-q'],
    cwd=str(REPO), capture_output=True, text=True, timeout=600)
golden_passed = proc.returncode == 0
tail = (proc.stdout or '').strip().splitlines()[-3:]

evidence = {
    'issue': 72,
    'static_open_line': f'src/v8/synth.py:{OPEN_LINE_NO}: {open_line}',
    'static_block': block,
    'synth_gap_frac': synth_stats['gap_frac'],
    'real_gap_frac': real_stats['gap_frac'],
    'synth_open_eq_prev': synth_stats['open_eq_prev'],
    'real_open_eq_prev': real_stats['open_eq_prev'],
    'synth_mean_gap_frac': synth_stats['mean_gap_frac'],
    'real_mean_gap_frac': real_stats['mean_gap_frac'],
    'n_bars': 2500,
    'golden_test_passed': golden_passed,
    'golden_pytest_tail': tail,
}

out_path = REPO / '.audit/repro/out/72.json'
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence))
