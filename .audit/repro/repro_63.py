"""Repro for ISSUE #63 — Stop placed at ATR multiple from entry, not the
structural level.

Claim: src/v8/simulator.py step() computes base_stop = entry - sign*stop_r*unit
(ATR multiple from entry) even when the expert froze a structural stop price
(risk_geometry['stop_ref']). The structural level is ignored as a stop.

Deterministic. Prints one JSON evidence object to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path('/Users/hootie/src/v8')
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, executed_outcomes,
)
from v8.simulator import risk_unit  # noqa: E402

SIM_SRC = (REPO / 'src/v8/simulator.py').read_text()


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


# --- (1) STATIC CHECK -------------------------------------------------------
step_has_atr_based_stop = 'base_stop = entry - sign * stop_r * unit' in SIM_SRC
step_reads_stop_ref = ('stop_ref' in SIM_SRC
                       and 'pos.draft.risk_geometry.get(\'stop_ref\')'
                       not in SIM_SRC
                       and 'geom[\'stop_ref\']' not in SIM_SRC
                       and 'geom.get(\'stop_ref\')' not in SIM_SRC)
risk_unit_prefers_atr_ref = "atr = draft.risk_geometry.get('atr_ref')" in SIM_SRC

static = {
    'step_computes_atr_based_stop': step_has_atr_based_stop,
    'step_never_reads_stop_ref': not step_reads_stop_ref,
    'risk_unit_prefers_atr_ref': risk_unit_prefers_atr_ref,
    # the exact step() lines the issue cites
    'cites_lines_present':
        'target = entry + sign * target_r * unit' in SIM_SRC
        and 'base_stop = entry - sign * stop_r * unit' in SIM_SRC,
}

# --- (2) DYNAMIC: candlestick_reversal drafts (they carry stop_ref) ---------
rows = load_window()
states, drafts = detect_drafts(rows)          # every unique draft, 27 experts
pit = sorted(rows, key=lambda r: r.available_time)
bars = [r for r in pit if r.channel == 'kline'
        and r.payload.get('closed') is True][:2500]

cand = [(cid, d, i) for (cid, d, i) in drafts
        if d.expert_id == 'candlestick_reversal']

n_drafts = 0
n_stop_ref_differs = 0
abs_dev_R = []
for cid, d, birth_idx in cand:
    entry_idx = birth_idx + 1                  # lab entry: NEXT_BAR_CLOSE
    if entry_idx >= len(bars):
        continue
    entry = float(bars[entry_idx].payload['close'])
    geom = d.risk_geometry
    unit = risk_unit(d, entry)                 # -> atr_ref for these drafts
    sign = 1.0 if d.direction == 'LONG' else -1.0
    stop_r = float(geom['stop_r'])
    atr_stop = entry - sign * stop_r * unit    # the stop step() would use
    stop_ref = float(geom['stop_ref'])         # the frozen structural level
    dev_price = abs(atr_stop - stop_ref)
    abs_dev_R.append(dev_price / unit)
    n_drafts += 1
    tol = 1e-6 * max(1.0, abs(stop_ref))
    if dev_price > tol:
        n_stop_ref_differs += 1

dynamic = {
    'n_drafts': n_drafts,
    'n_stop_ref_differs': n_stop_ref_differs,
    'mean_abs_deviation_R': round(_mean(abs_dev_R), 4) if abs_dev_R else None,
}

# --- (3) EXECUTED POPULATION: MAE/MFE stats ---------------------------------
lab, report = run_lab(rows)
ex = executed_outcomes(lab)
mae_rs = [float(o['mae_r']) for o in ex]
mfe_rs = [float(o['mfe_r']) for o in ex]
n_mae_gt_1r = sum(1 for m in mae_rs if m > 1.0)

executed = {
    'n_executed': len(ex),
    'mae_r_mean': round(_mean(mae_rs), 4) if mae_rs else None,
    'mae_r_median': round(_median(mae_rs), 4) if mae_rs else None,
    'mfe_r_mean': round(_mean(mfe_rs), 4) if mfe_rs else None,
    'mfe_r_median': round(_median(mfe_rs), 4) if mfe_rs else None,
    'n_mae_gt_1R': n_mae_gt_1r,
    'frac_mae_gt_1R': round(n_mae_gt_1r / len(mae_rs), 4) if mae_rs else None,
}

evidence = {
    'issue': 63,
    'static': static,
    'dynamic': dynamic,
    'executed': executed,
}

out = json.dumps(evidence, indent=2)
print(out)

out_path = REPO / '.audit/repro/out/63.json'
out_path.write_text(out)
