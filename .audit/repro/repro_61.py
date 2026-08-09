"""Repro for audit issue #61 — Cost dominates measured edge.

Structure under test: the raw signal edge (mean net_R at round_trip_cost_r=0.0
over the ALL-SETUPS population, 1R:1R geometry, lag=2) is small and positive;
the shipped round_trip_cost_r=0.07 exceeds it by a large factor, so cost is the
dominant driver of the negative economics. Because cost is applied as a flat
per-trade subtraction in CanonicalSimulator (it never changes entry/exit
decisions), mean_net_r(c) = mean_net_r(0) - c should hold exactly — the
"difference is exactly cost" mechanism.

Current-tree numbers are reported (D-053/D-054/D-055 landed after the issue was
filed), so absolute digits may shift from the issue's +0.0123 / -0.0577.
"""
import json
import sys
from pathlib import Path

REPO = Path('/Users/hootie/src/v8')
sys.path.insert(0, str(REPO / '.audit/repro'))

from lab_probe import (load_window, detect_drafts, run_lab, offline_resim,
                       executed_outcomes, stats)

N_BARS = 2500
GEOM = {'target_r': 1.0, 'stop_r': 1.0}
LAG = 2
COSTS = [0.0, 0.02, 0.04, 0.07]
SHIPPED = 0.07

rows = load_window(n_bars=N_BARS)
states, drafts = detect_drafts(rows, n_bars=N_BARS)

# ---- ALL-SETUPS population: cost sweep at fixed 1R:1R geometry, lag=2 ----
sweep = {}
for c in COSTS:
    outcomes = offline_resim(rows, drafts, cost_r=c, lag=LAG,
                             geometry_override=GEOM, n_bars=N_BARS)
    net_rs = [o['net_r'] for o in outcomes]
    s = stats(net_rs)
    sweep[str(c)] = {'cost_r': c, 'n': s['n'], 'mean_net_r': s['mean_net_r'],
                     'win_rate': s['win_rate'], 'total_r': s['total_r']}

edge = sweep['0.0']['mean_net_r']          # raw signal edge per trade (1R:1R)
shipped_mean = sweep['0.07']['mean_net_r']
cost_edge_ratio = (SHIPPED / edge) if edge else None

# Structural check: flat-cost subtraction implies mean(c) == mean(0) - c.
mean_drops = {str(c): sweep[str(c)]['mean_net_r'] - edge for c in COSTS}

# ---- EXECUTED population: full Lab.run() at shipped cost and at zero cost --
exec_pop = {}
for c in (SHIPPED, 0.0):
    lab, report = run_lab(rows, round_trip_cost_r=c)
    outs = executed_outcomes(lab)
    s = stats([o['net_r'] for o in outs])
    exec_pop[str(c)] = {'cost_r': c, 'n': s['n'], 'mean_net_r': s['mean_net_r'],
                        'win_rate': s['win_rate'], 'total_r': s['total_r'],
                        'n_executed': report.n_executed,
                        'verdict': report.verdict}

evidence = {
    'issue': 61,
    'n_bars': N_BARS,
    'geometry': GEOM,
    'lag': LAG,
    'n_drafts': len(drafts),
    'cost_sweep': sweep,
    'edge_at_cost0': edge,
    'mean_at_shipped_cost': shipped_mean,
    'cost_edge_ratio': cost_edge_ratio,
    'mean_drops_vs_cost0': mean_drops,
    'executed_before_after': exec_pop,
}

out = json.dumps(evidence, indent=2, sort_keys=True)
print(out)
out_dir = REPO / '.audit/repro/out'
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / '61.json').write_text(out + '\n', encoding='utf-8')
