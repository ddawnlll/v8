"""Repro for ISSUE #64 — RR 1:1 and expiry_bars=8 hardcoded across the expert slate.

Claims:
  1. A large fraction of the expert slate ships target_r=1.0, stop_r=1.0
     (RR=1.0) in their risk_geometry dicts, and ALL ship expiry_bars=8.
  2. At RR=1 with round_trip_cost_r=0.07 the RM-11 breakeven win rate
     (w_min) sits above the realized win rate of the executed population.

Structure verified here (current tree, 27 experts):
  (a) STATIC grep of literal risk_geometry assignments per expert file.
  (b) DYNAMIC: geometry actually emitted in drafts (detect_drafts) per expert.
  (c) run_lab at default cost 0.07 -> report.w_min vs executed win rate.

Deterministic: fixed seeds not needed (no wall clock, no RNG); the tape is a
fixed file and all passes are pure.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path('/Users/hootie/src/v8')
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, executed_outcomes, stats,
    ALL_EXPERT_CLASSES,
)

EXPERT_DIR = REPO / 'src/v8/experts'
COST_R = 0.07
N_EXPERTS = len(ALL_EXPERT_CLASSES)

# ---------------------------------------------------------------------------
# (a) STATIC grep of literal risk_geometry assignments in each expert file.
# ---------------------------------------------------------------------------
static_rows = []
for f in sorted(EXPERT_DIR.glob('*.py')):
    if f.name in ('__init__.py', 'base.py'):
        continue
    src = f.read_text()
    tr_lit = re.findall(r"'target_r':\s*([0-9.]+)", src)
    sr_lit = re.findall(r"'stop_r':\s*([0-9.]+)", src)
    eb_lit = re.findall(r"'expiry_bars':\s*([0-9]+)", src)
    static_rows.append({
        'file': f.name,
        'literal_target_r': [float(x) for x in tr_lit],
        'literal_stop_r': [float(x) for x in sr_lit],
        'literal_expiry_bars': [int(x) for x in eb_lit],
    })

n_static_tr1 = sum(any(v == 1.0 for v in r['literal_target_r'])
                   for r in static_rows)
n_static_sr1 = sum(any(v == 1.0 for v in r['literal_stop_r'])
                   for r in static_rows)
n_static_eb8 = sum(any(v == 8 for v in r['literal_expiry_bars'])
                   for r in static_rows)
n_static_rr1 = sum(
    any(t == 1.0 for t in r['literal_target_r'])
    and any(s == 1.0 for s in r['literal_stop_r'])
    for r in static_rows)

# ---------------------------------------------------------------------------
# (b) DYNAMIC: geometry actually emitted in drafts per expert.
# ---------------------------------------------------------------------------
rows = load_window(n_bars=2500)
states, drafts = detect_drafts(rows)

per_expert_geo: dict[str, set] = defaultdict(set)
per_expert_ndrafts = defaultdict(int)
for cid, draft, birth_idx in drafts:
    g = draft.risk_geometry
    per_expert_geo[draft.expert_id].add(
        (g.get('target_r'), g.get('stop_r'), g.get('expiry_bars')))
    per_expert_ndrafts[draft.expert_id] += 1

n_dyn_rr1_uniform = 0   # every emitted geometry is (1.0, 1.0, _)
n_dyn_rr1_any = 0       # at least one emitted geometry has target=stop=1.0
n_dyn_eb8_uniform = 0   # every emitted geometry has expiry_bars == 8
n_dyn_eb8_any = 0
for expert_id, geos in per_expert_geo.items():
    rr1 = [(t, s) for (t, s, _) in geos if t == 1.0 and s == 1.0]
    if rr1:
        n_dyn_rr1_any += 1
        if len(rr1) == len(geos):
            n_dyn_rr1_uniform += 1
    eb8 = [e for (_, _, e) in geos if e == 8]
    if eb8:
        n_dyn_eb8_any += 1
        if len(eb8) == len(geos):
            n_dyn_eb8_uniform += 1

# experts that emitted zero drafts
zero_draft_experts = sorted(set(ex.expert_id for ex in ALL_EXPERT_CLASSES)
                            - set(per_expert_geo.keys()))
n_emitting = len(per_expert_geo)

# ---------------------------------------------------------------------------
# (c) run_lab at default cost 0.07; RM-11 w_min vs realized win rate.
# ---------------------------------------------------------------------------
lab, report = run_lab(rows)
ex_outcomes = executed_outcomes(lab)
ex_net = [o['net_r'] for o in ex_outcomes]
realized = stats(ex_net)
w_min = report.w_min

# Independent RM-11 check over the EXECUTED geometry: 1/(1 + (t-c)/(s+c)).
# Report only carries w_min; recompute from executed outcome geometry if the
# ledger records it (outcome records carry risk_geometry).
be_from_executed = None
geos_executed = []
for o in ex_outcomes:
    g = o.get('risk_geometry') or {}
    geos_executed.append((g.get('target_r', 1.0), g.get('stop_r', 1.0)))
if geos_executed:
    vals = []
    for t, s in geos_executed:
        reward = t - COST_R
        risk = s + COST_R
        if reward > 0 and risk > 0:
            vals.append(1.0 / (1.0 + reward / risk))
    if vals:
        be_from_executed = sum(vals) / len(vals)

gap = (w_min - realized['win_rate']) * 100 if w_min is not None else None

evidence = {
    'issue': 64,
    'n_experts_total': N_EXPERTS,
    'static_grep': {
        'n_files': len(static_rows),
        'n_target_r_eq_1_0': n_static_tr1,
        'n_stop_r_eq_1_0': n_static_sr1,
        'n_expiry_eq_8': n_static_eb8,
        'n_rr1_both_literal': n_static_rr1,
        'per_file': static_rows,
    },
    'dynamic_drafts': {
        'n_emitting_experts': n_emitting,
        'zero_draft_experts': zero_draft_experts,
        'n_rr1_uniform': n_dyn_rr1_uniform,
        'n_rr1_any': n_dyn_rr1_any,
        'n_expiry8_uniform': n_dyn_eb8_uniform,
        'n_expiry8_any': n_dyn_eb8_any,
        'per_expert': {k: sorted(v) for k, v in sorted(per_expert_geo.items())},
        'per_expert_ndrafts': dict(sorted(per_expert_ndrafts.items())),
    },
    'lab': {
        'cost_r': COST_R,
        'w_min': w_min,
        'breakeven_from_executed_geo': be_from_executed,
        'realized': realized,
        'n_executed': len(ex_outcomes),
        'gap_breakeven_vs_realized_ppt': gap,
    },
}

out = {
    'count_RR1': n_dyn_rr1_uniform,
    'count_expiry8': n_dyn_eb8_uniform,
    'w_min': w_min,
    'realized_win_rate': realized['win_rate'],
    'gap_breakeven_vs_realized': gap,
}

print(json.dumps(evidence, indent=2))
out_path = REPO / '.audit/repro/out/64.json'
out_path.write_text(json.dumps(evidence, indent=2) + '\n')
key_path = REPO / '.audit/repro/out/64_key.json'
key_path.write_text(json.dumps(out, indent=2) + '\n')
