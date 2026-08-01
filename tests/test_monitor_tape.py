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


def test_clean_tape_audit_key_present(tmp_path, capsys):
    """--schema emits the reused audit result; a regression that silently
    drops the audit from the report must fail this test."""
    tape = _tape(tmp_path)
    assert main(['--tape', str(tape), '--schema']) == 0
    report = json.loads(capsys.readouterr().out)
    assert 'audit' in report and report['audit']['monotonic'] is True


def test_empty_tape_fails_closed_schema(tmp_path, capsys):
    """A zero-row tape cannot be evaluated and must reject, not pass
    (OPERATIONS_SPEC section 5)."""
    tape = tmp_path / 'tape.jsonl'
    tape.write_text('', encoding='utf-8')
    assert main(['--tape', str(tape), '--schema']) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['verdict'] == 'VIOLATION'
    assert any('cannot evaluate' in v for v in report['violations'])


def test_empty_tape_fails_closed_staleness_structured(tmp_path, capsys):
    """The empty-tape staleness path alerts with a well-formed JSON report
    (no KeyError traceback) and a non-zero exit."""
    tape = tmp_path / 'tape.jsonl'
    tape.write_text('', encoding='utf-8')
    assert main(['--tape', str(tape), '--staleness', '--now', str(1_770_000_000_000_000_000)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['verdict'] == 'VIOLATION'
    assert report['staleness']['detail'] == 'no bar rows on tape'


def test_missing_tape_structured_error(tmp_path, capsys):
    """A missing tape fails closed with a structured report, not a traceback."""
    assert main(['--tape', str(tmp_path / 'nope.jsonl'), '--schema']) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['verdict'] == 'VIOLATION'
    assert any('tape not found' in v for v in report['violations'])


def test_audit_violation_end_to_end(tmp_path, capsys):
    """A venue-sequence gap in the tape surfaces through main as a violation
    with exit 1 (the TapeAuditError branch)."""
    base = 1_770_000_000_000_000_000
    rows = []
    for i in range(5):
        c = 100.0 + i
        content = {'open': c, 'high': c + 0.5, 'low': c - 0.5, 'close': c,
                   'volume': 1.0, 'closed': True}
        rows.append({
            'source': 'binance-um', 'channel': 'kline', 'instrument': 'BTCUSDT',
            'event_time': base + (i + 1) * HOUR_NS - 1,
            'available_time': base + (i + 1) * HOUR_NS,
            'ingested_time': base + (i + 1) * HOUR_NS,
            'venue_sequence': 1000 + i + (1 if i >= 2 else 0),   # gap at i=2
            'event_id': f'BTCUSDT:1h:{base + i * HOUR_NS}',
            'payload': dict(content, payload_hash=sha1_hex(content),
                            schema_version='binance-um-v1-ms'),
        })
    tape = tmp_path / 'tape.jsonl'
    tape.write_text('\n'.join(json.dumps(r, sort_keys=True) for r in rows) + '\n',
                    encoding='utf-8')
    assert main(['--tape', str(tape), '--schema']) == 1
    report = json.loads(capsys.readouterr().out)
    assert any('venue sequence gap' in v for v in report['violations'])


def test_directory_tape_path(tmp_path, capsys):
    """--tape <outdir> resolves to <outdir>/tape.jsonl (documented form)."""
    _tape(tmp_path)
    assert main(['--tape', str(tmp_path), '--schema']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['tape'].endswith('tape.jsonl')


def test_bool_timestamp_rejected(tmp_path, capsys):
    """Booleans are not valid integer-nanosecond timestamps
    (FEED_INGESTION_SPEC section 2); `true` must not pass the int check."""
    tape = _tape(tmp_path, bad={'event_time': True})
    assert main(['--tape', str(tape), '--schema']) == 1
    report = json.loads(capsys.readouterr().out)
    assert any('event_time is bool' in p for p in report['schema_problems'])


def test_staleness_experiment_id_propagates(tmp_path, capsys):
    """experiment_id reaches the staleness report (OPERATIONS_SPEC section 3)."""
    tape = _tape(tmp_path)
    assert main(['--tape', str(tape), '--staleness', '--now', str(1_770_000_000_000_000_000),
                 '--experiment-id', 'exp-mon']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['staleness']['experiment_id'] == 'exp-mon'
