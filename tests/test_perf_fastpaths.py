"""Pins for the 2026-08-07 perf fast paths: byte-identity of every
optimization that touched hashing or serialization.

Each test compares the fast path against the reference semantics it replaced:
- the store `hash` property must equal `sha1_hex(read())` on fresh and
  pre-existing logs (a rejected incremental-hash design made `[,r1,r2]`
  instead of `[r1,r2]`, silently moving every log hash — the semantic is
  pinned here so a future incremental hash cannot regress it);
- the running lineage digests (`closed_digests`/`manifest_digest`) must equal
  `_cumulative_digest` for consecutive t/m AND jumps (the same comma-before-
  first bug cost real run hashes before it was caught);
- `_asdict_fast` must equal `dataclasses.asdict` on every record the lab
  appends (the golden backtest catches a break only through a full re-pin,
  which is exactly what these tests are meant to avoid).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from dataclasses import asdict

from v8.marketstate import (build_bar_series, build_state,
                            _cumulative_digest)
from v8.schema import (CandidateDraft, CounterfactualOutcome,
                       TapeRow, ExpertEvaluation, CandidateTransition,
                       ExperimentManifest, _asdict_fast, record_dict, sha1_hex)
from v8.store import AppendOnlyLog
from v8.synth import make_synthetic_tape


def _rows() -> list[TapeRow]:
    return make_synthetic_tape(seed=7, n_bars=40)


def test_store_incremental_hash_equals_read_hash_fresh(tmp_path):
    log = AppendOnlyLog(tmp_path / 'log.jsonl')
    for r in _rows():
        log.append(record_dict(r, source=r.source))
    assert log.hash == sha1_hex(log.read())
    # and the hash is stable across repeat access + after a duplicate append
    assert log.hash == log.hash
    assert log.append(record_dict(_rows()[0], source='binance-um')) is False
    assert log.hash == sha1_hex(log.read())


def test_store_incremental_hash_equals_read_hash_preexisting(tmp_path):
    """__init__ on a non-empty file must seed the hasher identically."""
    path = tmp_path / 'log.jsonl'
    log = AppendOnlyLog(path)
    for r in _rows():
        log.append(record_dict(r, source=r.source))
    expect = log.hash
    replay = AppendOnlyLog(path)
    assert replay.hash == expect == sha1_hex(replay.read())
    # a second append-only session continues the same hash
    replay.append(record_dict(_rows()[0], source='binance-um'))
    assert replay.hash == sha1_hex(replay.read())


def test_closed_digests_incremental_matches_reference():
    rows = make_synthetic_tape(seed=7, n_bars=250)
    pit = sorted(rows, key=lambda r: r.available_time)
    closed = [r for r in pit if r.channel == 'kline'
              and r.payload.get('closed') is True]
    s = build_bar_series(closed, closed, [], [])
    n = len(closed)
    # consecutive advance 0..n, then BACKWARD jumps (a jump re-seeds the
    # incremental hasher from scratch, which is where the comma-before-first
    # bug lived) — all within the bar count, since a digest beyond n is
    # invalid in the reference too.
    for t in list(range(0, n + 1)) + [n - 7, n - 2, 3, 5]:
        prev, dt = s.closed_digests(t)
        assert dt == _cumulative_digest(s.tuple_bytes, t)
        assert prev == (_cumulative_digest(s.tuple_bytes, t - 1) if t >= 2 else '')
        assert s.manifest_digest(t) == _cumulative_digest(s.kline_bytes, t)
    # idempotent repeat
    assert s.closed_digests(n) == s.closed_digests(n)


@pytest.mark.parametrize('make', [
    lambda: _rows()[0],
    lambda: _rows()[-1],
])
def test_asdict_fast_tape_row(make):
    assert _asdict_fast(make()) == asdict(make())


def test_asdict_fast_market_state():
    rows = _rows()
    pit = sorted(rows, key=lambda r: r.available_time)
    asof = [b.available_time for b in pit if b.channel == 'kline'
            and b.payload.get('closed') is True][20]
    st = build_state([r for r in pit if r.available_time <= asof], asof,
                     ('SOLUSDT',))
    assert _asdict_fast(st) == asdict(st)


def test_asdict_fast_all_record_types():
    draft = CandidateDraft(
        expert_id='x', expert_version='v1', instrument='SOLUSDT',
        direction='LONG', setup_fingerprint='f', risk_geometry={
            'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0, 'stop_r': 1.0,
            'expiry_bars': 8, 'atr_ref': 1.23, 'trigger_ref': 77.0},
        birth_time=1, setup_anchor_event_id='e', size=1.0)
    ev = ExpertEvaluation(expert_id='x', version='v1', state_id='s',
                          applicability='APPLICABLE', decision='CANDIDATE',
                          knowledge_time=5, draft=draft)
    out = CounterfactualOutcome(candidate_id='c', horizon_bars=3, endpoint='STOP',
                                net_r=-1.07, label_status='MATURE',
                                simulator_hash='h', label_available_time=9,
                                mae_r=1.0, mfe_r=2.0, ambiguous_bars=0,
                                entry_price=77.0, risk_unit_price=1.0,
                                market_move_r=0.5)
    tr = CandidateTransition(candidate_id='c', sequence=2, from_state='DETECTED',
                             to_state='PENDING', reason_code='hypothesis_completed',
                             knowledge_time=5, event_hash='e')
    man = ExperimentManifest(experiment_id='e', code_hash='c', data_hash='d',
                             universe=('SOLUSDT',), start_ns=0, end_ns=1)
    for rec in (ev, out, tr, man):
        assert _asdict_fast(rec) == asdict(rec), type(rec).__name__
    # record_dict stays byte-identical through the JSON round-trip (the slow
    # reference is the pre-fast-path record_dict semantics: asdict + source +
    # the auto dedup key, which sha1_hex sorts identically to the fast path).
    for rec in (ev, out, tr, man):
        fast = record_dict(rec, source='t')
        slow = dict(asdict(rec))
        slow['source'] = 't'
        slow['event_id'] = f"{slow.get('candidate_id', slow.get('event_id', sha1_hex(slow)))}"
        assert json_dumps(fast) == json_dumps(slow), type(rec).__name__


def json_dumps(obj):
    import json
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))
