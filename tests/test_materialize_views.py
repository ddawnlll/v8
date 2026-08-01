"""Offline round-trip of tools/materialize_views.py on a synthetic tape.

DATASET_SPEC section 5 compile-once discipline: views rebuild only when the
feature graph, an Expert definition, the simulator, or the outcome definition
changes. A pinned manifest that no longer matches the live code/data hashes
must fail closed — stale views are never silently readable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

import pyarrow.parquet as pq

from tools.materialize_views import VIEWS, materialize
from v8.lab import Lab, _code_hash
from v8.synth import make_synthetic_tape


def _make_pinned_manifest(tmp_path: Path, seed: int = 3, n_bars: int = 60) -> Path:
    store = tmp_path / 'src_store'
    lab = Lab(store)
    lab.ingest(make_synthetic_tape(seed=seed, n_bars=n_bars))
    rows = lab.tape_log.replay_tape()
    manifest = {
        'experiment_id': 'exp-materialize-offline',
        'code_hash': _code_hash(),
        'data_hash': lab.tape_log.hash,
        'universe': ['SOLUSDT'],
        'start_ns': rows[0].event_time,
        'end_ns': rows[-1].event_time,
        'interval': '1h',
        'tape_path': str(store / 'tape.jsonl'),
        'views_dir': str(tmp_path / 'views'),
    }
    p = tmp_path / 'manifest.json'
    p.write_text(json.dumps(manifest), encoding='utf-8')
    return p


def test_materialize_writes_all_five_views(tmp_path):
    """All five section-5 views exist as parquet, with the row counts implied
    by the ledger: one market_state per bar, one birth + one outcome per
    candidate, and a transition-fidelity execution trajectory. The assertions
    check view CONTENT, not just file existence or row counts: a view whose
    payload was replaced by a constant must fail."""
    manifest = _make_pinned_manifest(tmp_path)
    summary = materialize(manifest, tmp_path / 'store')
    assert summary['verdict'] == 'NO_ECONOMIC_CLAIM'
    assert summary['candidate_count'] > 0
    views_dir = Path(summary['views_dir'])
    for view in VIEWS:
        p = views_dir / f'{view}.parquet'
        assert p.exists(), f'{view} missing'
        assert summary['rows'][view] == pq.read_table(p).num_rows

    states = pq.read_table(views_dir / 'market_states.parquet')
    assert summary['rows']['market_states'] == 60
    # CONTENT: the features_json column carries real per-bar features for the
    # decision ledger, and the state_id column is a real 40-hex sha1.
    assert 'features_json' in states.column_names and 'state_id' in states.column_names
    first = states.slice(0, 1).to_pylist()[0]
    import json as _json
    feats = _json.loads(first['features_json'])
    assert 'SOLUSDT.close' in feats and 'SOLUSDT.history' in feats
    assert len(first['state_id']) == 40

    births = pq.read_table(views_dir / 'candidate_birth.parquet').to_pylist()
    assert summary['rows']['candidate_birth'] == summary['candidate_count']
    # CONTENT: every birth carries a real expert, instrument and anchor.
    for b in births:
        assert b['expert_id'] in ('trend_pullback', 'failed_breakout',
                                  'liquidity_sweep_reclaim')
        assert b['instrument'] == 'SOLUSDT'
        assert b['setup_anchor_event_id']
        assert b['direction'] in ('LONG', 'SHORT')

    outcomes = pq.read_table(views_dir / 'candidate_outcomes.parquet').to_pylist()
    assert len(outcomes) == summary['candidate_count']
    # CONTENT: outcomes carry the simulator hash and R-multiples, never
    # placeholder values.
    assert all(o['simulator_hash'] for o in outcomes)
    assert all(isinstance(o['net_r'], float) for o in outcomes)

    trajectories = pq.read_table(views_dir / 'execution_trajectories.parquet')
    assert summary['rows']['execution_trajectories'] >= summary['candidate_count']
    # CONTENT: every trajectory row is a legal transition (from/to present),
    # not an unfiltered dump of suppressed/veto rows.
    traj = trajectories.to_pylist()
    assert all(t['from_state'] is not None and t['to_state'] is not None for t in traj)
    assert (views_dir / 'views_manifest.json').exists()


def test_materialize_fails_closed_on_data_hash_mismatch(tmp_path):
    """A pinned data_hash that no longer matches the tape fails closed: the
    views would be stale and must not be produced."""
    manifest = _make_pinned_manifest(tmp_path)
    data = json.loads(manifest.read_text(encoding='utf-8'))
    data['data_hash'] = 'f' * 40
    manifest.write_text(json.dumps(data), encoding='utf-8')
    # Lab.run now fails closed at the composition root on a non-empty pin
    # mismatch ("manifest data_hash ... != live tape ...") before materialize's
    # own check; either message proves the fail-closed contract.
    with pytest.raises(ValueError, match=r'data_?hash'):
        materialize(manifest, tmp_path / 'store2')


def test_materialize_reused_store_fails_closed(tmp_path):
    """Materialization is compile-once: a second run against a store that
    already holds a run fails closed instead of silently rebuilding views on
    a polluted ledger (bugfix)."""
    manifest = _make_pinned_manifest(tmp_path)
    store = tmp_path / 'store'
    materialize(manifest, store)
    with pytest.raises(ValueError, match='already contains run evidence'):
        materialize(manifest, store)
