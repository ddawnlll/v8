"""Offline tests for tools/vision_backfill.py (FEED_INGESTION_SPEC 4-5).

Network is never required: a tiny fixture zip + .CHECKSUM exercises the
checksum-verify -> unzip -> CSV -> PIT tape (JSONL) path, the audit gates,
and double-run idempotency. The real download path is a manual operator step
and is not covered here (runbook step 4).
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

from tools.vision_backfill import (
    DEFAULT_LATENCY_NS, SCHEMA_VERSION,
    audit_tape, build_tape_from_zip, check_archive_revision, funding_csv_to_rows,
    kline_csv_to_rows, main as backfill_main, parse_checksum_file, sha256_file,
    write_source_meta, write_tape, TapeAuditError, sha1_hex, _zip_name,
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
    # and the CLI's fail-closed path (main) must reject the corrupt zip, not
    # just SHA-256's different-bytes property.
    out = tmp_path / 'out'
    out.mkdir()
    (out / zip_path.name).write_bytes(zip_path.read_bytes())
    (out / f'{zip_path.name}.CHECKSUM').write_text(
        good + f' *{zip_path.name}\n', encoding='utf-8')
    with pytest.raises(SystemExit, match='SHA-256 mismatch'):
        backfill_main(['--symbol', 'BTCUSDT', '--interval', '1h',
                       '--month', '2025-01', '--out', str(out)])


def test_double_run_is_idempotent(tmp_path):
    """A second backfill over the same output dir must not duplicate rows; the
    tape file and provenance are byte-identical (FEED_INGESTION_SPEC 5
    idempotency)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    appended1, skipped1 = write_tape(out, rows)
    assert (appended1, skipped1) == (6, 0)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01',
                      sha256_file(zip_path))
    before = (out / 'tape.jsonl').read_bytes()
    prov_before = (out / 'source.json').read_bytes()
    check_archive_revision(out, '2025-01', sha256_file(zip_path))   # same zip ok
    appended2, skipped2 = write_tape(out, rows)
    assert (appended2, skipped2) == (0, 6)             # all deduped
    assert (out / 'tape.jsonl').read_bytes() == before
    assert (out / 'source.json').read_bytes() == prov_before
    assert audit_tape(out)['row_count'] == 6


def test_audit_passes_clean_tape(tmp_path):
    """A clean tape with provenance audits without violations."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file(zip_path))
    report = audit_tape(out)
    assert report['row_count'] == 6 and report['payload_hashes_ok']
    assert report['duplicate_rows'] == 0


def test_audit_fails_closed_without_provenance(tmp_path):
    """A tape without source.json cannot be provenance-verified and must
    fail closed, not pass green (OPERATIONS_SPEC section 5)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path
    write_tape(out, build_tape_from_zip(zip_path, 'BTCUSDT', '1h'))
    with pytest.raises(TapeAuditError, match='source.json missing'):
        audit_tape(out)


def test_archive_revision_fails_closed(tmp_path):
    """A corrected archive (same open times, revised close, different zip
    sha256) must be REFUSED — the store dedup would silently keep the
    superseded bars otherwise (bugfix, critical)."""
    out = tmp_path / 'out'
    out.mkdir()
    zip_a = _fixture_zip(tmp_path)                     # close[3] = 103.0
    rows_a = build_tape_from_zip(zip_a, 'BTCUSDT', '1h')
    write_tape(out, rows_a)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file(zip_a))
    # A revised archive with the same open times but a different close:
    import zipfile
    revised_rows = list(rows_a)
    p = dict(revised_rows[3]['payload'])
    p['close'] = 203.0
    content = {k: v for k, v in p.items() if k not in ('payload_hash', 'schema_version')}
    p['payload_hash'] = sha1_hex(content)
    revised_rows[3]['payload'] = p
    zip_b = tmp_path / 'BTCUSDT-1h-2025-01-revised.zip'
    csv = '\n'.join(
        f"{r['payload']['open_time_ms']},{r['payload']['open']},{r['payload']['high']},"
        f"{r['payload']['low']},{r['payload']['close']},{r['payload']['volume']},"
        f"{r['payload']['close_time_ms']},1000,5,5,500,0"
        for r in revised_rows) + '\n'
    with zipfile.ZipFile(zip_b, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('BTCUSDT-1h-2025-01.csv', csv)
    # The revision check must refuse before any write.
    with pytest.raises(ValueError, match='refusing to ingest revised archive'):
        check_archive_revision(out, '2025-01', sha256_file(zip_b))
    # And through the CLI (main) the same month with a different zip fails.
    (out / 'BTCUSDT-1h-2025-01.zip').write_bytes(zip_b.read_bytes())
    (out / 'BTCUSDT-1h-2025-01.zip.CHECKSUM').write_text(
        sha256_file(zip_b) + ' *BTCUSDT-1h-2025-01.zip\n', encoding='utf-8')
    with pytest.raises((SystemExit, ValueError), match='refusing to ingest revised archive'):
        backfill_main(['--symbol', 'BTCUSDT', '--interval', '1h',
                       '--month', '2025-01', '--out', str(out)])


def test_provenance_is_keyed_by_symbol_not_just_month(tmp_path):
    """A second instrument's archive for the SAME month is not a revision of
    the first's. Keying provenance on (channel, month) alone was correct only
    while a tape dir held one symbol: the moment a second one arrives its
    2025-01 zip has a different checksum and was refused as a 'revised
    archive', so a multi-instrument tape could not be built at all."""
    out = tmp_path / 'out'
    out.mkdir()
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', 'sha-btc')
    # Same month, different symbol, different checksum -> admitted.
    check_archive_revision(out, '2025-01', 'sha-eth', 'kline', 'ETHUSDT')
    write_source_meta(out, 'ETHUSDT', '1h', '2025-01', 'sha-eth')

    meta = json.loads((out / 'source.json').read_text(encoding='utf-8'))
    assert meta['symbols'] == ['BTCUSDT', 'ETHUSDT']
    assert {(a['symbol'], a['month']) for a in meta['archives']} == {
        ('BTCUSDT', '2025-01'), ('ETHUSDT', '2025-01')}
    # No single top-level symbol once the tape is multi-instrument, or the
    # audit would rebuild a zip name that never existed.
    assert meta['symbol'] == ''

    # The revision guard still bites WITHIN a symbol.
    with pytest.raises(ValueError, match='refusing to ingest revised archive'):
        check_archive_revision(out, '2025-01', 'sha-btc-revised', 'kline',
                               'BTCUSDT')


def test_revision_guard_stays_armed_when_symbol_is_omitted(tmp_path):
    """Callers predating the symbol argument pass none; an unmatched key would
    silently ADMIT a revised archive, so the omission must resolve to the
    tape's own single symbol rather than to an empty one."""
    out = tmp_path / 'out'
    out.mkdir()
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', 'sha-btc')
    with pytest.raises(ValueError, match='refusing to ingest revised archive'):
        check_archive_revision(out, '2025-01', 'sha-different')


def test_audit_flags_duplicate_rows(tmp_path):
    """A hand-edited tape with a duplicated (source, event_id) row is an audit
    violation (bugfix)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file(zip_path))
    tape = out / 'tape.jsonl'
    lines = tape.read_text(encoding='utf-8').splitlines()
    tape.write_text('\n'.join(lines + [lines[0]]) + '\n', encoding='utf-8')
    with pytest.raises(TapeAuditError) as excinfo:
        audit_tape(out)
    assert 'duplicate row' in str(excinfo.value)


def test_audit_flags_venue_gap(tmp_path):
    """A missing bar (venue-sequence gap) is an audit violation, not a
    curiosity (FEED_INGESTION_SPEC 4)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file(zip_path))
    tape = out / 'tape.jsonl'
    lines = tape.read_text(encoding='utf-8').splitlines()
    del lines[3]                                       # remove the 4th bar
    tape.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(TapeAuditError) as excinfo:
        audit_tape(out)
    assert 'venue sequence gap' in str(excinfo.value)


def _funding_tape(tmp_path, csv_text: str) -> Path:
    """A funding tape with provenance: rows from `csv_text` + a funding zip
    whose sha the source.json records (so the audit can verify it)."""
    rows = funding_csv_to_rows(csv_text, 'SOLUSDT')
    out = tmp_path
    write_tape(out, rows)
    name = _zip_name('SOLUSDT', '1h', 'funding', '2025-01')
    with zipfile.ZipFile(out / name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name.replace('.zip', '.csv'), csv_text)
    write_source_meta(out, 'SOLUSDT', '1h', '2025-01', sha256_file(out / name),
                      channel='funding')
    return out


def test_audit_accepts_funding_interval_transition(tmp_path):
    """A settlement straddling a venue schedule change (4h -> 2h) is not a
    gap: the gap is governed by the PREVIOUS row's declared interval. The
    real SOLUSDT 2022-11 tape hit exactly this (the audit used the current
    row's 2h interval and false-flagged a 4h transition gap)."""
    csv_text = ('1668038400000,4,0.01\n'   # 00:00 UTC, 4h schedule
                '1668052800000,2,0.01\n'   # 04:00, schedule now 2h
                '1668060000000,2,0.01\n'
                '1668067200000,2,0.01\n')
    out = _funding_tape(tmp_path, csv_text)
    report = audit_tape(out)
    assert report['venue_gaps'] == 0


def test_audit_flags_missing_funding_row(tmp_path):
    """A genuinely missing settlement (a 4h gap under a steady 2h schedule)
    still flags after the interval-transition fix."""
    csv_text = ('1668038400000,2,0.01\n'   # 00:00, 2h schedule
                '1668052800000,2,0.01\n'   # 04:00  <- 02:00 settlement missing
                '1668060000000,2,0.01\n')
    out = _funding_tape(tmp_path, csv_text)
    with pytest.raises(TapeAuditError) as excinfo:
        audit_tape(out)
    assert 'venue sequence gap' in str(excinfo.value)


def test_audit_flags_payload_corruption(tmp_path):
    """A tampered payload (hash mismatch) is an audit violation
    (FEED_INGESTION_SPEC 5 reconciliation)."""
    zip_path = _fixture_zip(tmp_path)
    out = tmp_path
    rows = build_tape_from_zip(zip_path, 'BTCUSDT', '1h')
    write_tape(out, rows)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file(zip_path))
    tape = out / 'tape.jsonl'
    first = tape.read_text(encoding='utf-8').splitlines()[0]
    tape.write_text(first.replace('"close": 100.0', '"close": 999.0') + '\n',
                    encoding='utf-8')
    with pytest.raises(TapeAuditError) as excinfo:
        audit_tape(out)
    assert 'payload hash mismatch' in str(excinfo.value)
