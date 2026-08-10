"""V8 x Recoverable Regret v0.2 — Phase 1: Candidate-local opportunity
accounting, DESCRIPTIVE ONLY.

Reads the certified Phase-0 evaluator's output (cube.jsonl + regret.jsonl)
from one or more store directories and joins them into ONE frozen dataset,
tagged with which symbol/store each row came from. It computes ONLY
descriptive summaries over dimensions that are already decision-time-defined
(Expert, direction, endpoint, terminal lifecycle state) — it does NOT slice
by context/habitat (Phase 0 carries no such axis), does NOT test
significance, does NOT call anything a systematic finding, and does NOT sum
Candidate-local gaps into a claimed portfolio value. Every population-style
number in this module's output is labelled
MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED.

This module NEVER re-runs Lab or the Phase-0 evaluator; it is a pure reader
of already-certified cube.jsonl/regret.jsonl files (FCR-V8RR-004 OM002,
restated for Phase 1).
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO))

from v8.store import AppendOnlyLog

LABEL = 'MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED'


@dataclass(frozen=True)
class JoinedCandidateRow:
    """One row of the frozen Phase-1 dataset: a regret.jsonl gap record
    joined with its ACTUAL action's cube row and tagged with the symbol its
    store was built for."""
    symbol: str
    candidate_id: str
    expert_id: str
    direction: str
    birth_time: int
    gap_status: str
    legal_hindsight_gap: float | None
    actual_utility: float | None
    best_utility: float | None
    tie_cardinality: int
    endpoint: str | None
    label_status: str | None
    horizon_bars: int | None
    cost_r: float | None
    funding_r: float | None
    mae_r: float | None
    mfe_r: float | None
    ambiguous_bars: int | None
    epistemic_class: str


def _load_store_snapshots(store_dir: Path) -> dict:
    """expert_id/direction/birth_time lookup per candidate_id, from the
    store's own candidates.jsonl DETECTED snapshot — never recomputed, read
    once. birth_time is the DETECTED transition's own knowledge_time, the
    only decision-time-defined clock a Candidate carries before any action
    is taken (FCR-V8RR-004 FT002)."""
    trans = AppendOnlyLog(store_dir / 'candidates.jsonl').read()
    out = {}
    for rec in trans:
        if rec.get('to_state') == 'DETECTED':
            out[rec['candidate_id']] = (rec.get('expert_id', ''), rec.get('direction', ''),
                                        rec.get('knowledge_time', 0))
    return out


def join_dataset(regret_out_dirs: dict) -> list[JoinedCandidateRow]:
    """regret_out_dirs: {symbol: (store_dir, out_dir)}. Returns the frozen,
    joined Phase-1 dataset — one row per Candidate across every symbol."""
    rows: list[JoinedCandidateRow] = []
    for symbol, (store_dir, out_dir) in sorted(regret_out_dirs.items()):
        snapshots = _load_store_snapshots(Path(store_dir))
        gaps = AppendOnlyLog(Path(out_dir) / 'regret.jsonl').read()
        cube_by_key = {}
        for rec in AppendOnlyLog(Path(out_dir) / 'cube.jsonl').read():
            cube_by_key[(rec['candidate_id'], rec['action_id'])] = rec

        for g in gaps:
            expert_id, direction, birth_time = snapshots.get(g['candidate_id'], ('', '', 0))
            actual_cube = cube_by_key.get((g['candidate_id'], g.get('actual_action_id')))
            rows.append(JoinedCandidateRow(
                symbol=symbol, candidate_id=g['candidate_id'], expert_id=expert_id,
                direction=direction, birth_time=birth_time, gap_status=g['gap_status'],
                legal_hindsight_gap=g.get('legal_hindsight_gap'),
                actual_utility=g.get('actual_utility'), best_utility=g.get('best_utility'),
                tie_cardinality=g.get('tie_cardinality', 0),
                endpoint=(actual_cube or {}).get('endpoint'),
                label_status=(actual_cube or {}).get('label_status'),
                horizon_bars=(actual_cube or {}).get('horizon_bars'),
                cost_r=(actual_cube or {}).get('cost_r'),
                funding_r=(actual_cube or {}).get('funding_r'),
                mae_r=(actual_cube or {}).get('mae_r'), mfe_r=(actual_cube or {}).get('mfe_r'),
                ambiguous_bars=(actual_cube or {}).get('ambiguous_bars'),
                epistemic_class='MODEL_DERIVED'))
    return rows


def _mean(xs: list) -> float | None:
    return sum(xs) / len(xs) if xs else None


def descriptive_breakdown(rows: list, group_fn, group_name: str) -> dict:
    """ONE pre-declared descriptive breakdown (not adaptive search — Phase 1
    performs no selection). Returns {label, group_name, groups: {key: stats}}."""
    groups: dict = {}
    for r in rows:
        key = group_fn(r)
        groups.setdefault(key, []).append(r)
    out = {}
    for key, grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        computed = [r for r in grp if r.gap_status == 'COMPUTED']
        gaps = [r.legal_hindsight_gap for r in computed]
        utils = [r.actual_utility for r in computed]
        out[str(key)] = {
            'n_total': len(grp), 'n_computed': len(computed),
            'gap_status_distribution': {
                s: sum(1 for r in grp if r.gap_status == s)
                for s in sorted({r.gap_status for r in grp})},
            'mean_legal_hindsight_gap': _mean(gaps),
            'mean_actual_utility': _mean(utils),
        }
    return {'label': LABEL, 'group_name': group_name, 'groups': out}


def build_phase1_dataset(regret_out_dirs: dict, out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = join_dataset(regret_out_dirs)

    dataset_path = out / 'phase1_dataset.jsonl'
    with dataset_path.open('w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r), sort_keys=True) + '\n')

    query_log = []
    breakdowns = {}
    for name, fn in (
        ('by_expert', lambda r: r.expert_id),
        ('by_expert_symbol', lambda r: (r.expert_id, r.symbol)),
        ('by_expert_direction', lambda r: (r.expert_id, r.direction)),
        ('by_endpoint', lambda r: r.endpoint),
        ('by_symbol', lambda r: r.symbol),
    ):
        breakdowns[name] = descriptive_breakdown(rows, fn, name)
        query_log.append({'query_id': f'phase1-predeclared-{name}', 'kind': 'descriptive_breakdown',
                          'group_name': name, 'label': LABEL,
                          'adaptive': False, 'phase': 'Phase 1'})

    summary = {
        'label': LABEL,
        'n_symbols': len(regret_out_dirs), 'symbols': sorted(regret_out_dirs),
        'n_candidates_total': len(rows),
        'gap_status_distribution': {
            s: sum(1 for r in rows if r.gap_status == s)
            for s in sorted({r.gap_status for r in rows})},
        'n_computed': sum(1 for r in rows if r.gap_status == 'COMPUTED'),
        'zero_negative_gap_invariant_check': {
            'n_computed': sum(1 for r in rows if r.gap_status == 'COMPUTED'),
            'n_negative': sum(1 for r in rows if r.gap_status == 'COMPUTED'
                              and r.legal_hindsight_gap is not None
                              and r.legal_hindsight_gap < -1e-9)},
        'breakdowns': breakdowns,
        'query_log': query_log,
        'not_computed': ['systematicity', 'recoverability', 'attribution', 'portfolio_aggregation'],
    }
    (out / 'phase1_summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, default=list) + '\n', encoding='utf-8')
    (out / 'phase1_query_log.jsonl').write_text(
        '\n'.join(json.dumps(q, sort_keys=True) for q in query_log) + '\n', encoding='utf-8')
    return summary
