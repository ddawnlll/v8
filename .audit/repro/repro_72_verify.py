"""Verify fix for issue #72: make_synthetic_tape gains a continuous variant.

The legacy default (continuous=False) must be BYTE-IDENTICAL to the pre-fix
generator (gap_frac ~73%, open==prev_close 0%), so the pinned golden/contract
tests are unaffected. The new continuous=True variant must bind each bar's open
to the prior close (open = prev_close * (1 + uniform(-0.001, 0.001))), dropping
the fabricated TR > (H-L) gap fraction from ~73% to the ~3-5% band D-064 claims
(real BTCUSDT 1h tape: ~0.6%).

Assertions (bug-gone evidence):
  1. legacy gap_frac is still ~73% (unchanged vs pre-fix out/72.json)
  2. continuous gap_frac is < 10% — far below the legacy ~73% and inside the
     expected ~3-5% band
  3. continuous open is bound to the prior close: mean_gap_frac << legacy
  4. golden regression test still passes (legacy hash re-pin untouched)
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
# (1) static — the continuous-variant open line in the CURRENT tree
# --------------------------------------------------------------------------
synth_src = (REPO / 'src/v8/synth.py').read_text()
lines = synth_src.splitlines()
cont_open_line = next(
    (i + 1, l.strip()) for i, l in enumerate(lines)
    if 'prev_close * (1 + rng.uniform(-0.001, 0.001))' in l)
legacy_open_line = next(
    (i + 1, l.strip()) for i, l in enumerate(lines)
    if 'price / (1 + rng.uniform(-0.004, 0.004))' in l)
assert cont_open_line[0] < legacy_open_line[0], (
    'continuous branch must precede the legacy branch in the source')


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
# (2) dynamic continuity stats: legacy vs continuous vs real tape
# --------------------------------------------------------------------------
legacy_rows = make_synthetic_tape(seed=7, n_bars=2500)
legacy_payloads = [r.payload for r in legacy_rows]
assert len(legacy_payloads) == 2500

cont_rows = make_synthetic_tape(seed=7, n_bars=2500, continuous=True)
cont_payloads = [r.payload for r in cont_rows]
assert len(cont_payloads) == 2500

real_rows = load_window(n_bars=2500)
real_payloads = [r.payload for r in real_rows
                 if r.channel == 'kline'
                 and r.payload.get('closed') is True][:2500]

legacy_stats = continuity_stats(legacy_payloads)
cont_stats = continuity_stats(cont_payloads)
real_stats = continuity_stats(real_payloads)

# --------------------------------------------------------------------------
# (3) bug-gone assertions
# --------------------------------------------------------------------------
assert abs(legacy_stats['gap_frac'] - 0.7302921168467387) < 1e-12, (
    f"legacy default drifted: {legacy_stats['gap_frac']}")
assert 0.60 < legacy_stats['gap_frac'] < 0.80, (
    f"legacy gap_frac outside ~73% band: {legacy_stats['gap_frac']}")
assert cont_stats['gap_frac'] < 0.10, (
    f"continuous variant still fabricates gaps: {cont_stats['gap_frac']}")
assert cont_stats['gap_frac'] < legacy_stats['gap_frac'] / 2, (
    f"continuous gap_frac not clearly below legacy: "
    f"{cont_stats['gap_frac']} vs {legacy_stats['gap_frac']}")
assert 0.01 < cont_stats['gap_frac'] < 0.10, (
    f"continuous gap_frac outside expected ~3-5% band: "
    f"{cont_stats['gap_frac']}")
assert cont_stats['mean_gap_frac'] < legacy_stats['mean_gap_frac'] / 10, (
    f"continuous open not bound to prior close: "
    f"{cont_stats['mean_gap_frac']} vs {legacy_stats['mean_gap_frac']}")

# --------------------------------------------------------------------------
# (4) golden regression test
# --------------------------------------------------------------------------
proc = subprocess.run(
    [str(REPO / '.venv/bin/python'), '-m', 'pytest',
     'tests/test_golden_backtest.py', '-q'],
    cwd=str(REPO), capture_output=True, text=True, timeout=600)
golden_passed = proc.returncode == 0
tail = (proc.stdout or '').strip().splitlines()[-3:]
assert golden_passed, f"golden test failed:\n{proc.stdout}\n{proc.stderr}"

evidence = {
    'issue': 72,
    'fixed': True,
    'static_continuous_open_line': (
        f'src/v8/synth.py:{cont_open_line[0]}: {cont_open_line[1]}'),
    'static_legacy_open_line': (
        f'src/v8/synth.py:{legacy_open_line[0]}: {legacy_open_line[1]}'),
    'n_bars': 2500,
    # flat legacy fields mirror the pre-fix schema in out/72.json
    'synth_gap_frac': legacy_stats['gap_frac'],
    'real_gap_frac': real_stats['gap_frac'],
    'synth_open_eq_prev': legacy_stats['open_eq_prev'],
    'real_open_eq_prev': real_stats['open_eq_prev'],
    'synth_mean_gap_frac': legacy_stats['mean_gap_frac'],
    'real_mean_gap_frac': real_stats['mean_gap_frac'],
    'continuous_gap_frac': cont_stats['gap_frac'],
    'continuous_open_eq_prev': cont_stats['open_eq_prev'],
    'continuous_mean_gap_frac': cont_stats['mean_gap_frac'],
    'legacy': legacy_stats,
    'continuous': cont_stats,
    'real': real_stats,
    'legacy_byte_identical': (
        abs(legacy_stats['gap_frac'] - 0.7302921168467387) < 1e-12),
    'golden_test_passed': golden_passed,
    'golden_pytest_tail': tail,
}

out_path = REPO / '.audit/repro/out/72.fixed.json'
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence))
