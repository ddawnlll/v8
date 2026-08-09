"""Verify fix for ISSUE #61 — Cost dominates measured edge (FEASIBILITY note).

#61 was a MEASUREMENT record ("düzeltme önermiyor"): no economics were changed
on purpose for it. What landed in the audit-fix pass is the FEASIBILITY
SURFACING — report.economic_note now carries an RM-11 note when the
cost-degraded breakeven win rate (w_min) exceeds the realized win rate (#64,
D-062) and an excess-cost note when the gate fires (#69, D-063), and the
cost/edge mismatch is recorded (O-025).

Verified here against the CURRENT (fixed) tree:
  (a) the cost sweep (ALL-SETUPS, 1R:1R override, lag=2, n=8040) — the
      measurement record. The economics were NOT changed on purpose, so the
      sweep is expected ~unchanged; the shift that IS present (edge at cost 0
      moving from -0.0064 to ~-0.00007) comes from the #63 structural-stop
      correctness fix landing in the same pass, not from any #61 economics
      change.
  (b) the flat-cost-subtraction identity mean(c) - mean(0) = -c — must still
      hold EXACTLY (the mechanism the issue's "difference is exactly cost"
      claim relies on).
  (c) run_lab at round_trip_cost_r=0.07 -> report.economic_note MUST contain
      'FEASIBILITY' (the NEW behavior; the RM-11 variant, since 0.07 <
      EXCESS_COST_THRESHOLD_R=0.10).

Pre-fix baseline embedded below is .audit/repro/out/61.run.log (2026-08-07
16:32, HEAD 8b7ac3a + D-056 working tree; matches BASELINE.md headline rows
exactly). NOTE: out/61.json on disk already held the post-fix numbers (a prior
verify pass re-ran repro_61.py, overwriting it) — the true pre-fix evidence is
61.run.log, which this script embeds.

Deterministic: fixed tape, no wall clock, no RNG.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path('/Users/hootie/src/v8')
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, offline_resim, executed_outcomes,
    stats,
)

N_BARS = 2500
GEOM = {'target_r': 1.0, 'stop_r': 1.0}
LAG = 2
COSTS = [0.0, 0.02, 0.04, 0.07]
SHIPPED = 0.07

# Pre-fix baseline (.audit/repro/out/61.run.log, 2026-08-07 pre-fix tree).
PRE_FIX_SWEEP = {
    '0.0': {'mean_net_r': -0.006407880168243891, 'win_rate': 0.4968905472636816,
            'total_r': -51.51935655268089},
    '0.02': {'mean_net_r': -0.0264078801682439, 'win_rate': 0.4937810945273632,
             'total_r': -212.31935655268094},
    '0.04': {'mean_net_r': -0.04640788016824391, 'win_rate': 0.49129353233830847,
             'total_r': -373.11935655268104},
    '0.07': {'mean_net_r': -0.07640788016824393, 'win_rate': 0.48818407960199006,
             'total_r': -614.3193565526811},
}
PRE_FIX_EDGE = -0.006407880168243891
PRE_FIX_COST_EDGE_RATIO = -10.924049476908964
PRE_FIX_EXECUTED = {
    '0.0': {'n': 895, 'mean_net_r': -0.04549416518553134,
            'win_rate': 0.46368715083798884, 'total_r': -40.71727784105055},
    '0.07': {'n': 895, 'mean_net_r': -0.11549416518553138,
             'win_rate': 0.45251396648044695, 'total_r': -103.36727784105058},
}

rows = load_window(n_bars=N_BARS)
states, drafts = detect_drafts(rows, n_bars=N_BARS)

# ---------------------------------------------------------------------------
# (a) ALL-SETUPS population: cost sweep at fixed 1R:1R geometry, lag=2.
# ---------------------------------------------------------------------------
sweep = {}
for c in COSTS:
    outcomes = offline_resim(rows, drafts, cost_r=c, lag=LAG,
                             geometry_override=GEOM, n_bars=N_BARS)
    net_rs = [o['net_r'] for o in outcomes]
    s = stats(net_rs)
    sweep[str(c)] = {'cost_r': c, 'n': s['n'], 'mean_net_r': s['mean_net_r'],
                     'win_rate': s['win_rate'], 'total_r': s['total_r']}

edge = sweep['0.0']['mean_net_r']
shipped_mean = sweep['0.07']['mean_net_r']
cost_edge_ratio = (SHIPPED / edge) if edge else None

# (b) Structural check: flat-cost subtraction implies mean(c) == mean(0) - c.
mean_drops = {str(c): sweep[str(c)]['mean_net_r'] - edge for c in COSTS}
# "Exactly" means: the drop equals -c to float round-trip precision (the
# residual is ~1e-17). The mechanism is a pure per-trade subtraction.
identity_exact = all(
    abs(mean_drops[str(c)] - (-c)) < 1e-12 for c in COSTS)

# (c) Full lab at shipped cost -> economic_note (THE new behavior).
lab, report = run_lab(rows, round_trip_cost_r=SHIPPED)
ex_outcomes = executed_outcomes(lab)
ex_net = [o['net_r'] for o in ex_outcomes]
ex_stat = stats(ex_net)
note = report.economic_note
feasibility_present = (note is not None) and ('FEASIBILITY' in note)

# Zero-cost executed run for the before/after executed delta.
lab0, report0 = run_lab(rows, round_trip_cost_r=0.0)
ex0 = executed_outcomes(lab0)
ex0_stat = stats([o['net_r'] for o in ex0])

# Sweep delta vs pre-fix: report the shift and the uniform-magnitude check.
sweep_delta = {
    str(c): {
        'before_mean': PRE_FIX_SWEEP[str(c)]['mean_net_r'],
        'after_mean': sweep[str(c)]['mean_net_r'],
        'shift': sweep[str(c)]['mean_net_r'] - PRE_FIX_SWEEP[str(c)]['mean_net_r'],
    } for c in COSTS
}
# The shift should be cost-independent (net_R change from the #63 stop fix is a
# per-draft constant; cost is still applied as a flat subtraction on top).
shifts = [sweep_delta[str(c)]['shift'] for c in COSTS]
shift_uniform = max(abs(s - shifts[0]) for s in shifts) < 1e-9

evidence = {
    'issue': 61,
    'fixed': True,
    'new_behavior': {
        'cost_r': SHIPPED,
        'n_executed': ex_stat['n'],
        'economic_note': note,
        'economic_note_carries_FEASIBILITY': feasibility_present,
        'w_min_breakeven': report.w_min,
        'realized_win_rate': ex_stat['win_rate'],
        'breakeven_exceeds_realized': (
            report.w_min is not None and report.w_min > ex_stat['win_rate']),
    },
    'measurement_unchanged_on_purpose': {
        'flat_cost_subtraction_identity_exact': identity_exact,
        'mean_drops_vs_cost0': mean_drops,
        'n_drafts': len(drafts),
        'n_setups': sweep['0.07']['n'],
    },
    'cost_sweep_after': sweep,
    'cost_sweep_before_after_delta': sweep_delta,
    'cost_sweep_shift_is_cost_independent_uniform': shift_uniform,
    'edge_at_cost0': edge,
    'mean_at_shipped_cost': shipped_mean,
    'cost_edge_ratio': cost_edge_ratio,
    'executed_before_after': {
        '0.07': {
            'before': PRE_FIX_EXECUTED['0.07'],
            'after': {'n': ex_stat['n'], 'mean_net_r': ex_stat['mean_net_r'],
                      'win_rate': ex_stat['win_rate'],
                      'total_r': ex_stat['total_r']},
        },
        '0.0': {
            'before': PRE_FIX_EXECUTED['0.0'],
            'after': {'n': ex0_stat['n'], 'mean_net_r': ex0_stat['mean_net_r'],
                      'win_rate': ex0_stat['win_rate'],
                      'total_r': ex0_stat['total_r']},
        },
    },
}

assert identity_exact, (
    'flat-cost identity mean(c) - mean(0) = -c no longer holds exactly')
assert feasibility_present, (
    'report.economic_note missing FEASIBILITY at shipped cost 0.07')
assert report.w_min is not None and report.w_min > ex_stat['win_rate'], (
    'breakeven win rate does not exceed realized win rate — the RM-11 '
    'mismatch the note surfaces is absent')

print(json.dumps(evidence, indent=2, sort_keys=True))
out_path = REPO / '.audit/repro/out/61.fixed.json'
out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
