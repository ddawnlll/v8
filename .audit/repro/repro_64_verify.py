"""Verify fix for ISSUE #64 — RR 1:1 and expiry_bars=8 hardcoded.

The landed fix is the RM-11 feasibility note (report-only) plus the D-062
record that RR=1.0 target_r is a DESIGN_INFERENCE until a structural target
exists. The geometry was NOT swept (optimization is explicitly not the fix),
so the static grep counts and the emitted draft geometry are expected to be
UNCHANGED. What must be NEW is report.economic_note carrying the RM-11
'FEASIBILITY: breakeven win rate ... exceeds realized win rate ...' note.

Verified here against the CURRENT (fixed) tree:
  (a) STATIC grep counts of literal target_r=1.0 / expiry_bars=8 — must equal
      the pre-fix baseline (19/27 target_r=1.0, 14/14 rr1-both-literal,
      27/27 expiry=8) because geometry was deliberately not swept.
  (b) DYNAMIC emitted geometry (detect_drafts) — RR=1.0 uniform count 13/23
      emitting experts, expiry=8 uniform 23/23, as in baseline.
  (c) run_lab at default cost 0.07 -> report.economic_note MUST contain
      'FEASIBILITY: breakeven win rate' (the NEW behavior) and w_min vs the
      realized executed win rate (the mismatch the note surfaces).

Deterministic: fixed tape, no wall clock, no RNG.
"""
from __future__ import annotations

import json
import re
import sys
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

# Pre-fix baseline (from .audit/repro/out/64.json, 2026-08-07).
PRE_FIX = {
    'static_n_target_r_eq_1_0': 19,
    'static_n_stop_r_eq_1_0': 14,
    'static_n_expiry_eq_8': 27,
    'static_n_rr1_both_literal': 14,
    'dyn_n_rr1_uniform': 13,
    'dyn_n_rr1_any': 13,
    'dyn_n_expiry8_uniform': 23,
    'dyn_n_expiry8_any': 23,
    'w_min': 0.5280639098900115,
    'realized_win_rate': 0.4686390532544379,
    'n_executed': 845,
    'gap_ppt': 5.9424856635573615,
}

# ---------------------------------------------------------------------------
# (a) STATIC grep — geometry literals must be unchanged (not swept).
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
# (b) DYNAMIC emitted geometry.
# ---------------------------------------------------------------------------
rows = load_window(n_bars=2500)
states, drafts = detect_drafts(rows)

from collections import defaultdict
per_expert_geo: dict[str, set] = defaultdict(set)
for cid, draft, birth_idx in drafts:
    g = draft.risk_geometry
    per_expert_geo[draft.expert_id].add(
        (g.get('target_r'), g.get('stop_r'), g.get('expiry_bars')))

n_dyn_rr1_uniform = 0
n_dyn_rr1_any = 0
n_dyn_eb8_uniform = 0
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

# ---------------------------------------------------------------------------
# (c) Full lab -> economic_note (THE new behavior) + w_min vs realized.
# ---------------------------------------------------------------------------
lab, report = run_lab(rows)
ex_outcomes = executed_outcomes(lab)
ex_net = [o['net_r'] for o in ex_outcomes]
realized = stats(ex_net)
w_min = report.w_min
note = report.economic_note

gap = (w_min - realized['win_rate']) * 100 if w_min is not None else None

static_unchanged = (
    n_static_tr1 == PRE_FIX['static_n_target_r_eq_1_0']
    and n_static_sr1 == PRE_FIX['static_n_stop_r_eq_1_0']
    and n_static_eb8 == PRE_FIX['static_n_expiry_eq_8']
    and n_static_rr1 == PRE_FIX['static_n_rr1_both_literal'])
dyn_unchanged = (
    n_dyn_rr1_uniform == PRE_FIX['dyn_n_rr1_uniform']
    and n_dyn_rr1_any == PRE_FIX['dyn_n_rr1_any']
    and n_dyn_eb8_uniform == PRE_FIX['dyn_n_expiry8_uniform']
    and n_dyn_eb8_any == PRE_FIX['dyn_n_expiry8_any'])
note_present = (note is not None) and (
    'FEASIBILITY: breakeven win rate' in note)

evidence = {
    'issue': 64,
    'fixed': True,
    'geometry_not_swept': {
        'static_unchanged_vs_baseline': static_unchanged,
        'dynamic_unchanged_vs_baseline': dyn_unchanged,
        'static_grep': {
            'n_target_r_eq_1_0': n_static_tr1,
            'n_stop_r_eq_1_0': n_static_sr1,
            'n_expiry_eq_8': n_static_eb8,
            'n_rr1_both_literal': n_static_rr1,
        },
        'dynamic_drafts': {
            'n_emitting_experts': len(per_expert_geo),
            'n_rr1_uniform': n_dyn_rr1_uniform,
            'n_rr1_any': n_dyn_rr1_any,
            'n_expiry8_uniform': n_dyn_eb8_uniform,
            'n_expiry8_any': n_dyn_eb8_any,
        },
    },
    'lab': {
        'cost_r': COST_R,
        'n_executed': len(ex_outcomes),
        'w_min': w_min,
        'realized_win_rate': realized['win_rate'],
        'gap_breakeven_vs_realized_ppt': gap,
        'economic_note': note,
        'economic_note_carries_RM11_feasibility': note_present,
    },
}

assert static_unchanged, 'geometry was swept — #64 fix must NOT sweep geometry'
assert dyn_unchanged, 'emitted draft geometry changed — unexpected'
assert note_present, (
    'report.economic_note missing FEASIBILITY: breakeven win rate note')

print(json.dumps(evidence, indent=2))
out_path = REPO / '.audit/repro/out/64.fixed.json'
out_path.write_text(json.dumps(evidence, indent=2) + '\n')
