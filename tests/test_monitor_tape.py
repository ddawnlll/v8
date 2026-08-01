"""Offline tests for tools/monitor_tape.py (OPERATIONS_SPEC 2-3, 5).

Schema violations are detected, staleness alerts fire with an injectable
reference time, the audit is reused (not forked), and the tool fails closed
with structured JSON output. No wall clock is ever touched by the tests.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

from tools.monitor_tape import main, read_rows, staleness_report, validate_schema
from v8.schema import sha1_hex

HOUR_NS = 3_600_000_000_000
DAY_NS = 24 * HOUR_NS


def _tape(tmp_path: Path, n: int = 5, base_time: int = 1_770_000_000_000_000_000,
          bad: dict | None = None) -> Path:
    """A contract-compliant 1h kline tape (three clocks, payload_hash) plus an
    optional corrupted row merged in place of the last row."""
    rows = []
    for i in range(n):
        c = 100.0 + i
        content = {'open': c, 'high': c + 0.5, 'low': c - 0.5, 'close': c,
                   'volume': 1.0, 'closed': True}
        rows.append({
            'source': 'binance-um', 'channel': 'kline', 'instrument': 'BTCUSDT',
            'event_time': base_time + (i + 1) * HOUR_NS - 1,
            'available_time': base_time + (i + 1) * HOUR_NS,
            'ingested_time': base_time + (i + 1) * HOUR_NS,
            'venue_sequence': 1000 + i,
            'event_id': f'BTCUSDT:1h:{base_time + i * HOUR_NS}',
            'payload': dict(content, payload_hash=sha1_hex(content),
                            schema_version='binance-um-v1-ms'),
        })
    if bad is not None:
        rows[-1] = {**rows[-1], **bad}
    tape = tmp_path / 'tape.jsonl'
    tape.parent.mkdir(parents=True, exist_ok=True)
    tape.write_text('\n'.join(json.dumps(r, sort_keys=True) for r in rows) + '\n',
                    encoding='utf-8')
    return tape


def test_clean_tape_schema_and_verdict(tmp_path):
    tape = _tape(tmp_path)
    assert validate_schema(read_rows(tape)) == []


def test_clean_tape_structured_json(tmp_path, capsys):
    tape = _tape(tmp_path)
    rc = main(['--tape', str(tape), '--schema', '--experiment-id', 'exp-x'])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report['verdict'] == 'OK' and report['experiment_id'] == 'exp-x'
    assert report['rows'] == 5


def test_schema_violations_detected(tmp_path, capsys):
    tape = _tape(tmp_path, bad={'event_time': 1.5})          # wrong dtype
    rc = main(['--tape', str(tape), '--schema'])
    assert rc == 1
    report = json.loads(capsys.readouterr().out)
    assert report['verdict'] == 'VIOLATION'
    assert any('event_time is float' in p for p in report['schema_problems'])

    tape2 = _tape(tmp_path / 't2', bad={'payload': {'open': 1.0, 'closed': False}})
    rc2 = main(['--tape', str(tape2), '--schema'])
    assert rc2 == 1
    assert 'closed is not True' in json.loads(capsys.readouterr().out)['schema_problems'][0]

    tape3 = _tape(tmp_path / 't3', bad={'event_id': None})
    rc3 = main(['--tape', str(tape3), '--schema'])
    assert rc3 == 1


def test_staleness_injected_now(tmp_path):
    base = 1_770_000_000_000_000_000
    rows = read_rows(_tape(tmp_path, base_time=base))
    newest = max(r['event_time'] for r in rows)
    fresh = staleness_report(rows, now_ns=newest, budget_ns=DAY_NS)
    assert fresh['alert'] is False
    stale = staleness_report(rows, now_ns=newest + DAY_NS + 1, budget_ns=DAY_NS)
    assert stale['alert'] is True


def test_staleness_main_exit_codes(tmp_path, capsys):
    base = 1_770_000_000_000_000_000
    tape = _tape(tmp_path, base_time=base)
    newest = max(r['event_time'] for r in read_rows(tape))
    assert main(['--tape', str(tape), '--staleness', '--now', str(newest),
                 '--budget-ns', str(DAY_NS)]) == 0
    capsys.readouterr()
    assert main(['--tape', str(tape), '--staleness', '--now', str(newest + DAY_NS + 1),
                 '--budget-ns', str(DAY_NS)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['staleness']['alert'] is True
