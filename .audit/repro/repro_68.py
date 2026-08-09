"""Repro for ISSUE #68 — ExposureBook adverse selection.

Claim: the executed subset is much worse than the average setup, and which
candidate wins a contended (instrument, direction) slot is decided by
alphabetical expert_id order (PHASE 3 sorts experts by expert_id; the pending
dict preserves insertion order; ExposureBook allows one active exposure per
(instrument, direction)).

Deterministic: no RNG, no wall clock. Prints a single JSON evidence object.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_probe import (  # noqa: E402
    ALL_EXPERT_CLASSES, load_window, detect_drafts, run_lab,
    executed_outcomes, offline_resim, stats, SYMBOL,
)

COST_R = 0.07
LAG = 2
N_BARS = 2500


def main() -> None:
    rows = load_window(n_bars=N_BARS)

    # (1) Executed population through the lab's ExposureBook + risk gate.
    lab, report = run_lab(rows, round_trip_cost_r=COST_R)
    ex_outcomes = executed_outcomes(lab)
    executed_stats = stats([o['net_r'] for o in ex_outcomes])

    # (2) All-setups population (no contention), own geometry, lag=2, cost 0.07.
    _, drafts = detect_drafts(rows, n_bars=N_BARS)
    resim = offline_resim(rows, drafts, cost_r=COST_R, lag=LAG, n_bars=N_BARS)
    all_setups_stats = stats([r['net_r'] for r in resim])
    # Issue #68's original table used a 1R:1R geometry override on the old
    # tree; report that variant too so the current-tree ratio is comparable.
    resim_1r1r = offline_resim(
        rows, drafts, cost_r=COST_R, lag=LAG, n_bars=N_BARS,
        geometry_override={'target_r': 1.0, 'stop_r': 1.0})
    all_setups_1r1r_stats = stats([r['net_r'] for r in resim_1r1r])

    exec_mean = executed_stats['mean_net_r']
    all_mean = all_setups_stats['mean_net_r']
    adverse_ratio = (exec_mean / all_mean) if all_mean else None

    # (3) Per-expert tables. Map candidate_id -> expert_id via the DETECTED
    # birth record in the candidates ledger (carries expert_id in its extra).
    cid_to_expert: dict[str, str] = {}
    birth_meta: dict[str, dict] = {}
    transitions: list[dict] = []
    for rec in lab.candidates.read():
        if 'to_state' in rec:
            transitions.append(rec)
        if 'expert_id' in rec and rec.get('candidate_id'):
            cid_to_expert[rec['candidate_id']] = rec['expert_id']
            birth_meta[rec['candidate_id']] = {
                'expert_id': rec['expert_id'],
                'instrument': rec.get('instrument'),
                'direction': rec.get('direction'),
                'birth_time': rec.get('knowledge_time'),
            }
    # Executed count per expert: join executed outcomes by candidate_id.
    exec_by_expert: dict[str, int] = {}
    for o in ex_outcomes:
        ex = cid_to_expert.get(o['candidate_id'])
        exec_by_expert[ex] = exec_by_expert.get(ex, 0) + 1
    # Detected drafts per expert from detect_drafts (all unique setups).
    detected_by_expert: dict[str, int] = {}
    for cid, d, _bi in drafts:
        detected_by_expert[d.expert_id] = detected_by_expert.get(d.expert_id, 0) + 1

    expert_rows = []
    for cls in ALL_EXPERT_CLASSES:
        eid = cls.expert_id
        det = detected_by_expert.get(eid, 0)
        exe = exec_by_expert.get(eid, 0)
        expert_rows.append({
            'expert_id': eid,
            'detected': det,
            'executed': exe,
            'signal_rate': det / N_BARS,
            'exec_rate': exe / N_BARS,
            'exec_per_signal': (exe / det) if det else None,
        })
    expert_rows.sort(key=lambda r: (r['executed'], r['expert_id']), reverse=True)

    n_exec_total = executed_stats['n']
    alpha_order = {cls.expert_id: i for i, cls in
                   enumerate(sorted(ALL_EXPERT_CLASSES,
                                    key=lambda c: c.expert_id), 1)}
    top2 = [r for r in expert_rows
            if alpha_order[r['expert_id']] in (1, 2)]
    top2_share = (sum(r['executed'] for r in top2) / n_exec_total) \
        if n_exec_total else None

    # (4) Alphabetical-race structural evidence: same-bar, same-direction slot
    # contention. Candidates attempt to enter at PHASE 1a on their entry bar
    # (knowledge_time == bar available_time). Pending insertion order == PHASE 3
    # alphabetical evaluation order, so within a birth bar the DETECTED records
    # are in alphabetical order. Count contended slots and whether the
    # slot-winner (the one that reached EXECUTED) was alphabetically first.
    entry_attempt: dict[str, dict] = {}
    for rec in transitions:
        cid = rec.get('candidate_id')
        if rec.get('to_state') == 'EXECUTED':
            entry_attempt[cid] = {
                'time': rec.get('knowledge_time'), 'state': 'EXECUTED',
                'meta': birth_meta.get(cid, {})}
        elif (rec.get('to_state') == 'REJECTED'
              and rec.get('reason_code') == 'EXISTING_EXPOSURE_CONFLICT'):
            entry_attempt[cid] = {
                'time': rec.get('knowledge_time'), 'state': 'CONFLICT',
                'meta': birth_meta.get(cid, {})}
    groups: dict[tuple, list[str]] = {}
    for cid, info in entry_attempt.items():
        if info['meta']:
            groups.setdefault(
                (info['meta'].get('instrument'), info['meta'].get('direction'),
                 info['time']), []).append(cid)
    contended = {k: v for k, v in groups.items() if len(v) >= 2}
    n_contended = 0
    n_alpha_first = 0
    for key, cids in contended.items():
        winner = next((c for c in cids
                       if entry_attempt[c]['state'] == 'EXECUTED'), None)
        losers = [c for c in cids if entry_attempt[c]['state'] != 'EXECUTED']
        if winner is None or not losers:
            continue
        n_contended += 1
        w_ex = entry_attempt[winner]['meta'].get('expert_id')
        if all(alpha_order[w_ex] < alpha_order[entry_attempt[l]['meta'].get('expert_id')]
               for l in losers):
            n_alpha_first += 1

    # Report-level D-027 attribution numbers (secondary evidence).
    report_key = {}
    for k in ('execution_share', 'divergence_ks', 'n_executed',
              'n_portfolio_rejected'):
        if hasattr(report, k):
            report_key[k] = getattr(report, k)

    evidence = {
        'issue': 68,
        'n_bars': N_BARS,
        'cost_r': COST_R,
        'lag': LAG,
        'executed_stats': executed_stats,
        'all_setups_stats': all_setups_stats,
        'all_setups_1r1r_stats': all_setups_1r1r_stats,
        'adverse_selection_ratio': adverse_ratio,
        'adverse_selection_ratio_1r1r': (
            exec_mean / all_setups_1r1r_stats['mean_net_r'])
        if all_setups_1r1r_stats['mean_net_r'] else None,
        'executed_worse_factor': abs(exec_mean / all_mean) if all_mean else None,
        'n_detected_setups': len(drafts),
        'top2': [r['expert_id'] for r in top2],
        'top2_share': top2_share,
        'per_expert_rates': expert_rows[:6],
        'per_expert_all': expert_rows,
        'contended_slots_same_bar': n_contended,
        'alphabetical_first_wins': n_alpha_first,
        'alpha_share_of_contended': (n_alpha_first / n_contended)
        if n_contended else None,
        'report_key': report_key,
    }
    out = json.dumps(evidence, indent=2, default=str)
    print(out)
    out_path = Path(__file__).resolve().parent / 'out' / '68.json'
    out_path.write_text(out + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
