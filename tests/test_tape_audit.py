"""Offline tests for tools/vision_backfill.py (FEED_INGESTION_SPEC 4-5).

Network is never required: a tiny fixture zip + .CHECKSUM exercises the
checksum-verify -> unzip -> CSV -> PIT tape (JSONL) path, the audit gates,
and double-run idempotency. The real download path is a manual operator step
and is not covered here (runbook step 4).
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

from tools.vision_backfill import (
    DEFAULT_LATENCY_NS, SCHEMA_VERSION,
    audit_tape, build_tape_from_zip, kline_csv_to_rows, parse_checksum_file,
    sha256_file, write_tape, TapeAuditError, sha1_hex,
)

HOUR_MS = 3_600_000


def _fixture_zip(tmp_path: Path) -> Path:
    """A tiny 6-bar 1h kline CSV in the documented Binance column order plus
    its `.CHECKSUM` (as Vision publishes it: `<sha256> *<name>`)."""
    open_ms = 1_735_689_600_000                       # 2025-01-01 00:00 UTC
    lines = []
    for i in range(6):
        c = 100.0 + i
        lines.append(
            f'{open_ms + i * HOUR_MS},{c},{c + 0.5},{c - 0.5},{c},10,'
            f'{open_ms + (i + 1) * HOUR_MS - 1},1000,5,5,500,0')
    csv_text = '\n'.join(lines) + '\n'
    zip_path = tmp_path / 'BTCUSDT-1h-2025-01.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('BTCUSDT-1h-2025-01.csv', csv_text)
    (tmp_path / f'{zip_path.name}.CHECKSUM').write_text(
        hashlib.sha256(zip_path.read_bytes()).hexdigest() + f' *{zip_path.name}\n',
        encoding='utf-8')
    return zip_path


def test_checksum_verify_and_tape_rows(tmp_path):
    """Checksum parses and matches; every row carries the three distinct
    clocks, ms -> integer ns, a monotonic venue sequence, a payload hash, and
    the source unit in schema_version (FEED_INGESTION_SPEC 2)."""
    zip_path = _fixture_zip(tmp_path)
    expected = parse_checksum_file(tmp_path / f'{zip_path.name}.CHECKSUM',
                                   zip_path.name)
    assert expected == hashlib.sha256(zip_path.read_bytes()).hexdigest()

    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    assert len(rows) == 6
    for r in rows:
        assert r['source'] == 'binance-um' and r['channel'] == 'kline'
        assert r['instrument'] == 'BTCUSDT'
        payload = r['payload']
        assert payload['closed'] is True
        assert payload['schema_version'] == SCHEMA_VERSION
        content = {k: v for k, v in payload.items()
                   if k not in ('payload_hash', 'schema_version')}
        assert payload['payload_hash'] == sha1_hex(content)
        assert r['event_time'] == payload['close_time_ms'] * 1_000_000
        assert r['available_time'] == r['event_time'] + DEFAULT_LATENCY_NS
        assert r['ingested_time'] == r['available_time']
    times = [r['event_time'] for r in rows]
    avail = [r['available_time'] for r in rows]
    seq = [r['venue_sequence'] for r in rows]
    assert times == sorted(times) and avail == sorted(avail)
    assert seq == list(range(seq[0], seq[0] + 6))       # contiguous ordinal


def test_header_tolerated():
    """A header line is detected and skipped (data.py `_csv_has_header`)."""
    header = ('open_time,open,high,low,close,volume,close_time,'
              'quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,'
              'taker_buy_quote_asset_volume,ignore\n')
    csv_text = header + '1735689600000,100,100.5,99.5,100,10,1735693200000,1000,5,5,500,0\n'
    rows = kline_csv_to_rows(csv_text, 'BTCUSDT', '1h')
    assert len(rows) == 1
    assert rows[0]['event_id'] == 'BTCUSDT:1h:1735689600000'


def test_corrupt_checksum_and_zip_fail_closed(tmp_path):
    """Malformed checksum files and zip hash mismatches are rejected, never
    silently accepted (FEED_INGESTION_SPEC 6)."""
    zip_path = _fixture_zip(tmp_path)
    good = parse_checksum_file(tmp_path / f'{zip_path.name}.CHECKSUM', zip_path.name)
    assert sha256_file(zip_path) == good
    # filename mismatch -> fail
    bad = tmp_path / 'bad.CHECKSUM'
    bad.write_text('f' * 64 + ' *some-other.zip\n', encoding='utf-8')
    with pytest.raises(ValueError):
        parse_checksum_file(bad, 'expected.zip')
    # truncated digest -> fail
    bad.write_text('abcd\n', encoding='utf-8')
    with pytest.raises(ValueError):
        parse_checksum_file(bad, 'expected.zip')
    # zip corruption -> hash mismatch
    zip_path.write_bytes(zip_path.read_bytes() + b'corrupt')
    assert sha256_file(zip_path) != good


def test_double_run_is_idempotent(tmp_path):
    """A second backfill over the same output dir must not duplicate rows; the
    tape file is byte-identical (FEED_INGESTION_SPEC 5 idempotency)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path / 'out'
    out.mkdir()
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    appended1, skipped1 = write_tape(out, rows)
    assert (appended1, skipped1) == (6, 0)
    before = (out / 'tape.jsonl').read_bytes()
    appended2, skipped2 = write_tape(out, rows)
    assert (appended2, skipped2) == (0, 6)             # all deduped
    assert (out / 'tape.jsonl').read_bytes() == before


def test_audit_passes_clean_tape(tmp_path):
    """A clean tape audits without violations."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path / 'out'
    out.mkdir()
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    report = audit_tape(out)
    assert report['row_count'] == 6 and report['payload_hashes_ok']


def test_audit_flags_venue_gap(tmp_path):
    """A missing bar (venue-sequence gap) is an audit violation, not a
    curiosity (FEED_INGESTION_SPEC 4)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path / 'out'
    out.mkdir()
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    tape = out / 'tape.jsonl'
    lines = tape.read_text(encoding='utf-8').splitlines()
    del lines[3]                                       # remove the 4th bar
    tape.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(TapeAuditError) as excinfo:
        audit_tape(out)
    assert 'venue sequence gap' in str(excinfo.value)


def test_audit_flags_payload_corruption(tmp_path):
    """A tampered payload (hash mismatch) is an audit violation
    (FEED_INGESTION_SPEC 5 reconciliation)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path / 'out'
    out.mkdir()
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    tape = out / 'tape.jsonl'
    first = tape.read_text(encoding='utf-8').splitlines()[0]
    tape.write_text(first.replace('"close": 100.0', '"close": 999.0') + '\n',
                    encoding='utf-8')
    with pytest.raises(TapeAuditError) as excinfo:
        audit_tape(out)
    assert 'payload hash mismatch' in str(excinfo.value)
