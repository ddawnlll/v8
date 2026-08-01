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
    candidate, and a transition-fidelity execution trajectory."""
    manifest = _make_pinned_manifest(tmp_path)
    summary = materialize(manifest, tmp_path / 'store')
    assert summary['verdict'] == 'NO_ECONOMIC_CLAIM'
    assert summary['candidate_count'] > 0
    views_dir = Path(summary['views_dir'])
    for view in VIEWS:
        p = views_dir / f'{view}.parquet'
        assert p.exists(), f'{view} missing'
        assert summary['rows'][view] == pq.read_table(p).num_rows
    assert summary['rows']['market_states'] == 60
    assert summary['rows']['candidate_birth'] == summary['candidate_count']
    assert summary['rows']['candidate_outcomes'] == summary['candidate_count']
    assert summary['rows']['execution_trajectories'] >= summary['candidate_count']
    assert (views_dir / 'views_manifest.json').exists()


def test_materialize_fails_closed_on_data_hash_mismatch(tmp_path):
    """A pinned data_hash that no longer matches the tape fails closed: the
    views would be stale and must not be produced."""
    manifest = _make_pinned_manifest(tmp_path)
    data = json.loads(manifest.read_text(encoding='utf-8'))
    data['data_hash'] = 'f' * 40
    manifest.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='data hash mismatch'):
        materialize(manifest, tmp_path / 'store2')
