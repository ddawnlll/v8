"""Offline tests for the D-041 funding channel in tools/vision_backfill.py
(DATASET_SPEC 6.4; FEED_INGESTION_SPEC 3).

No network: a tiny fundingRate fixture zip exercises the funding CSV -> PIT
tape mapping, the channel-aware audit (interleaved kline+funding tape), the
--sort replay-order finalize, and the (source, event_id) dedup namespaces.
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

from tools.vision_backfill import (
    FUNDING_SCHEMA_VERSION,
    audit_tape, build_tape_from_zip, check_archive_revision, funding_csv_to_rows,
    kline_csv_to_rows, main as backfill_main, sort_tape, write_source_meta,
    write_tape, TapeAuditError, sha1_hex,
)

HOUR_MS = 3_600_000
DAY0 = 1_735_689_600_000          # 2025-01-01 00:00 UTC
FUNDING_TIMES_MS = (DAY0, DAY0 + 8 * HOUR_MS, DAY0 + 16 * HOUR_MS)
FUNDING_RATES = (0.0001, 0.00005, -0.0001)
FUNDING_HOURS = 8


def _funding_zip(tmp_path: Path, rates: tuple[float, ...] = FUNDING_RATES,
                 headerless: bool = True) -> Path:
    rows = ('' if headerless else
            'calc_time,funding_interval_hours,last_funding_rate\n')
    rows += '\n'.join(
        f'{t},{FUNDING_HOURS},{r}' for t, r in zip(FUNDING_TIMES_MS, rates))
    zip_path = tmp_path / 'BTCUSDT-fundingRate-2025-01.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('BTCUSDT-fundingRate-2025-01.csv', rows + '\n')
    (tmp_path / f'{zip_path.name}.CHECKSUM').write_text(
        hashlib.sha256(zip_path.read_bytes()).hexdigest() + f' *{zip_path.name}\n',
        encoding='utf-8')
    return zip_path


def _kline_zip(tmp_path: Path, bars: int = 24) -> Path:
    lines = []
    for i in range(bars):
        c = 100.0 + i
        open_ms = DAY0 + i * HOUR_MS
        lines.append(
            f'{open_ms},{c},{c + 0.5},{c - 0.5},{c},10,'
            f'{open_ms + HOUR_MS - 1},1000,5,5,500,0')
    csv_text = '\n'.join(lines) + '\n'
    zip_path = tmp_path / 'BTCUSDT-1h-2025-01.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('BTCUSDT-1h-2025-01.csv', csv_text)
    (tmp_path / f'{zip_path.name}.CHECKSUM').write_text(
        hashlib.sha256(zip_path.read_bytes()).hexdigest() + f' *{zip_path.name}\n',
        encoding='utf-8')
    return zip_path


def _mixed_tape(out: Path, funding_rates: tuple[float, ...] = FUNDING_RATES,
                kline_bars: int = 24) -> None:
    """Write klines THEN funding (deliberately not replay-sorted) into <out>,
    with per-channel provenance — the shape a per-month append loop produces."""
    kzip = _kline_zip(out, kline_bars)
    fzip = _funding_zip(out, funding_rates)
    write_tape(out, build_tape_from_zip(kzip, 'BTCUSDT', '1h'))
    write_tape(out, build_tape_from_zip(fzip, 'BTCUSDT', '1h', channel='funding'))
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01',
                      sha256_file_of(kzip))
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01',
                      sha256_file_of(fzip), channel='funding')


def sha256_file_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- funding CSV -> PIT tape mapping ---------------------------------------

def test_funding_rows_mapping():
    csv_text = ('calc_time,funding_interval_hours,last_funding_rate\n'
                '1735689600000,8,0.0001\n'
                '1735718400000,8,0.00005\n')
    rows = funding_csv_to_rows(csv_text, 'BTCUSDT')
    assert len(rows) == 2
    for r in rows:
        assert r['source'] == 'binance-um' and r['channel'] == 'funding'
        assert r['instrument'] == 'BTCUSDT'
        payload = r['payload']
        assert payload['schema_version'] == FUNDING_SCHEMA_VERSION
        content = {k: v for k, v in payload.items()
                   if k not in ('payload_hash', 'schema_version')}
        assert payload['payload_hash'] == sha1_hex(content)
        assert r['event_time'] == payload['funding_time_ms'] * 1_000_000
        assert r['available_time'] == r['event_time'] + 1_000_000_000
        assert r['ingested_time'] == r['available_time']
    assert rows[0]['event_id'] == 'BTCUSDT:funding:1735689600000'
    assert rows[0]['venue_sequence'] == 1735689600000 // HOUR_MS


def test_funding_calc_time_ms_jitter_floors_to_boundary():
    """calc_time can carry a +1ms sub-boundary jitter (observed in the real
    2026-06 archive); the settlement boundary must stay hour-aligned so the
    schedule lookup and the hour-alignment audit check can both match."""
    csv_text = 'calc_time,funding_interval_hours,last_funding_rate\n'
    csv_text += '1780272000001,8,0.00005703\n'       # 00:00 + 1ms
    csv_text += '1780329600000,8,0.00010000\n'       # 16:00 exactly
    rows = funding_csv_to_rows(csv_text, 'BTCUSDT')
    assert [r['event_time'] % 3_600_000_000_000 for r in rows] == [0, 0]
    assert [r['payload']['funding_time_ms'] for r in rows] == [1780272000000, 1780329600000]
    assert [r['event_id'] for r in rows] == ['BTCUSDT:funding:1780272000000',
                                             'BTCUSDT:funding:1780329600000']


def test_funding_headerless_three_column():
    csv_text = '1735689600000,8,0.0001\n1735718400000,8,0.00005\n'
    rows = funding_csv_to_rows(csv_text, 'BTCUSDT')
    assert [r['payload']['funding_rate'] for r in rows] == [0.0001, 0.00005]
    assert [r['payload']['funding_interval_hours'] for r in rows] == [8.0, 8.0]


def test_funding_implausible_rate_fails_closed():
    with pytest.raises(ValueError, match='implausible funding rate'):
        funding_csv_to_rows('1735689600000,8,0.5\n', 'BTCUSDT')


def test_funding_unresolvable_header_fails_closed():
    with pytest.raises(ValueError, match='cannot resolve funding timestamp'):
        funding_csv_to_rows('when,what,why\n1,2,3\n', 'BTCUSDT')


def test_funding_event_id_namespace_distinct_from_kline():
    """The funding event_id namespace (symbol:funding:ts) can never collide
    with a kline event_id (symbol:interval:open_ms) under the store's
    (source, event_id) dedup key, even at the same wall-clock hour."""
    krows = kline_csv_to_rows(
        '1735689600000,100,100.5,99.5,100,10,1735693200000,1000,5,5,500,0\n',
        'BTCUSDT', '1h')
    frows = funding_csv_to_rows('1735689600000,8,0.0001\n', 'BTCUSDT')
    assert krows[0]['event_id'] == 'BTCUSDT:1h:1735689600000'
    assert frows[0]['event_id'] == 'BTCUSDT:funding:1735689600000'
    assert krows[0]['event_id'] != frows[0]['event_id']


# --- channel-aware audit + --sort -----------------------------------------

def test_audit_passes_sorted_mixed_tape(tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    _mixed_tape(out)
    # The append order (klines then funding) is NOT replay order: funding rows
    # at 00:00/08:00/16:00 must interleave the kline stream chronologically.
    with pytest.raises(TapeAuditError, match='replay order'):
        audit_tape(out)
    meta = sort_tape(out)
    assert meta['row_count'] == 24 + 3
    report = audit_tape(out)
    assert report['row_count'] == 27
    assert sort_tape(out)['row_count'] == 27     # idempotent


def test_audit_flags_funding_gap_beyond_funding_hours(tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    # Funding rows 24h apart: the venue-sequence gap (24) exceeds funding_hours.
    kzip = _kline_zip(out, 4)
    fzip = _funding_zip(out, (0.0001, 0.0002, 0.0003))
    f_rows = build_tape_from_zip(fzip, 'BTCUSDT', '1h', channel='funding')
    # Shift the second funding event 24h later and keep the payload hash
    # consistent so the audit reaches the venue-gap check.
    p = dict(f_rows[1]['payload'])
    p['funding_time_ms'] += 24 * HOUR_MS
    p['payload_hash'] = sha1_hex(
        {k: v for k, v in p.items() if k not in ('payload_hash', 'schema_version')})
    f_rows[1]['payload'] = p
    f_rows[1]['event_time'] = p['funding_time_ms'] * 1_000_000
    f_rows[1]['available_time'] = f_rows[1]['event_time'] + 1_000_000_000
    f_rows[1]['ingested_time'] = f_rows[1]['available_time']
    f_rows[1]['venue_sequence'] = p['funding_time_ms'] // HOUR_MS
    f_rows[1]['event_id'] = f"BTCUSDT:funding:{p['funding_time_ms']}"
    write_tape(out, build_tape_from_zip(kzip, 'BTCUSDT', '1h') + f_rows)
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file_of(kzip))
    write_source_meta(out, 'BTCUSDT', '1h', '2025-01', sha256_file_of(fzip),
                      channel='funding')
    with pytest.raises(TapeAuditError, match='funding venue sequence gap'):
        audit_tape(out)


def test_funding_build_via_cli(tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    fzip = _funding_zip(out)
    # Move the zip + checksum where the CLI expects them (the fixture already
    # writes them into <out>).
    assert backfill_main(['--symbol', 'BTCUSDT', '--interval', '1h',
                          '--channel', 'funding', '--month', '2025-01',
                          '--out', str(out)]) == 0
    # Same zip re-run is idempotent (dedup) and passes the revision check.
    check_archive_revision(out, '2025-01', sha256_file_of(fzip),
                           channel='funding')


def test_funding_revision_fails_closed(tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    fzip = _funding_zip(out)
    backfill_main(['--symbol', 'BTCUSDT', '--interval', '1h',
                   '--channel', 'funding', '--month', '2025-01',
                   '--out', str(out)])
    # A different funding zip for the same (channel, month) is refused.
    other = tmp_path / 'other.zip'
    other.write_bytes(fzip.read_bytes() + b'x')
    with pytest.raises(ValueError, match='refusing to ingest revised archive'):
        check_archive_revision(out, '2025-01', sha256_file_of(other),
                               channel='funding')
