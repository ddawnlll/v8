"""DATASET_SPEC section 5 materializations from a pinned ExperimentManifest.

Runs a fresh, deterministic lab execution on the pinned tape and writes the
five materialized parquet views — market_states, candidate_birth,
candidate_trigger, candidate_outcomes, execution_trajectories — with DuckDB
from the JSONL decision ledger (PERSISTENCE_REPLAY_SPEC section 1).

Compile-once discipline: the views are rebuilt only when the feature graph, an
Expert definition, the simulator, or the outcome definition changes — never
per training run. A pinned manifest pins code_hash and data_hash; a live
mismatch fails closed (the views would be stale and must not be read).

Usage:
  python tools/materialize_views.py --manifest <manifest.json> --store <dir>

The manifest is an ExperimentManifest (as JSON) plus two keys consumed here:
  tape_path: path to the JSONL PIT tape the lab store consumes
  views_dir: directory that receives the five <view>.parquet files
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import duckdb

from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.lab import Lab, _code_hash
from v8.schema import ExperimentManifest, sha1_hex
from v8.store import AppendOnlyLog

PILOTS = (TrendPullbackExpert, FailedBreakoutExpert)

# view name -> (jsonl ledger, SELECT body). read_json_auto infers the
# heterogeneous candidate ledger (transitions vs suppressed vs veto rows);
# missing keys are NULL, which is the correct projection semantics.
VIEWS: dict[str, tuple[str, str]] = {
    'market_states': (
        'states.jsonl',
        "SELECT state_id, as_of, universe, lineage_hash, quality, "
        "to_json(features) AS features_json FROM read_json_auto('{src}')"),
    'candidate_birth': (
        'candidates.jsonl',
        "SELECT candidate_id, sequence, knowledge_time, event_hash, "
        "expert_id, expert_version, instrument, direction, "
        "setup_anchor_event_id, geometry_version, state_id "
        "FROM read_json_auto('{src}') WHERE to_state = 'DETECTED'"),
    'candidate_trigger': (
        'candidates.jsonl',
        "SELECT candidate_id, sequence, knowledge_time, event_hash "
        "FROM read_json_auto('{src}') WHERE to_state = 'TRIGGERED'"),
    'candidate_outcomes': (
        'outcomes.jsonl',
        "SELECT candidate_id, horizon_bars, endpoint, net_r, label_status, "
        "simulator_hash, label_available_time, mae_r, mfe_r, ambiguous_bars "
        "FROM read_json_auto('{src}')"),
    'execution_trajectories': (
        'candidates.jsonl',
        "SELECT candidate_id, sequence, from_state, to_state, reason_code, "
        "knowledge_time FROM read_json_auto('{src}') "
        "WHERE from_state IS NOT NULL ORDER BY candidate_id, sequence"),
}


def materialize(manifest_path: Path, store_dir: Path) -> dict:
    """Run the pinned manifest's lab execution and write the parquet views.

    Fails closed on any pinned-hash mismatch or on a verdict other than
    NO_ECONOMIC_CLAIM (no authority receipt — nothing to materialize as
    evidence). Returns {report: {...}, rows: {view: count}, views_dir: ...}.
    """
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    tape_path = Path(data.pop('tape_path'))
    views_dir = Path(data.pop('views_dir'))
    manifest = ExperimentManifest(**data)

    # Compile-once discipline: a store dir that already holds a run would be
    # polluted by a second run (the lab fails closed too, but fail here with
    # a clear message before any work).
    store = Path(store_dir)
    if any((store / f'{name}.jsonl').exists()
           for name in ('states', 'candidates', 'outcomes', 'evaluations')):
        raise ValueError(
            f'store dir {store} already contains run evidence; '
            'materialization is compile-once — use a fresh store dir')

    lab = Lab(store_dir, universe=manifest.universe)
    lab.ingest(AppendOnlyLog(tape_path).replay_tape())
    report = lab.run(manifest, [cls() for cls in PILOTS])

    if _code_hash() != manifest.code_hash:
        raise ValueError(
            f'code hash mismatch: pinned {manifest.code_hash} vs live {_code_hash()}')
    if lab.tape_log.hash != manifest.data_hash:
        raise ValueError(
            f'data hash mismatch: pinned {manifest.data_hash} vs live {lab.tape_log.hash}')
    if report.verdict != 'NO_ECONOMIC_CLAIM':
        raise ValueError(f'verdict {report.verdict!r}: no authority receipt in manifest')

    views_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(':memory:')
    rows: dict[str, int] = {}
    try:
        for view, (jsonl, select) in VIEWS.items():
            sql = (f"COPY ({select.format(src=lab.dir / jsonl)}) "
                   f"TO '{views_dir / f'{view}.parquet'}' (FORMAT PARQUET);")
            con.execute(sql)
            rows[view] = con.execute(
                f"SELECT count(*) FROM read_parquet('{views_dir / f'{view}.parquet'}')"
            ).fetchone()[0]
    finally:
        con.close()

    # The pin must bind what the views actually depend on: the src/v8 code hash
    # alone misses the view SQL in THIS module and the manifest's economic
    # parameters (a recompile with changed economics or view definitions would
    # silently replace the "pinned" views under the same code_hash/data_hash).
    views_pin = sha1_hex((_code_hash(), json.dumps(VIEWS, sort_keys=True),
                          manifest.round_trip_cost_r, manifest.funding_rate_r,
                          manifest.funding_hours, manifest.fill_policy,
                          manifest.max_spread_frac, manifest.funding_window_bars,
                          str(views_dir), report.data_hash, report.ledger_hash))
    manifest_path = views_dir / 'views_manifest.json'
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding='utf-8'))
        if prior.get('views_pin') not in (None, views_pin):
            raise ValueError(
                'views pin mismatch: existing views_manifest.json was built '
                'with different view definitions/economics/code — rebuild in a '
                'fresh views_dir rather than silently replacing the pin')
    summary = {
        'experiment_id': report.experiment_id,
        'code_hash': report.code_hash,
        'data_hash': report.data_hash,
        'ledger_hash': report.ledger_hash,
        'verdict': report.verdict,
        'candidate_count': report.candidate_count,
        'rows': rows,
        'views_dir': str(views_dir),
        'views_pin': views_pin,
    }
    manifest_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True,
                    help='pinned ExperimentManifest JSON (+ tape_path, views_dir)')
    ap.add_argument('--store', type=Path, default=None,
                    help='lab store dir (default: <views_dir>/store)')
    args = ap.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    store = args.store or (Path(manifest['views_dir']) / 'store')
    summary = materialize(args.manifest, store)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
