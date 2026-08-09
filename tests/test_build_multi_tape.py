"""Offline tests for the single-process multi-tape grid driver
(tools/build_multi_tape.py).

Network is never required: fixture kline/funding zips + .CHECKSUM files are
written into the out dir and the driver runs offline (`--download` off). The
tests pin the three properties the driver exists to guarantee: complete
provenance written once and atomically, idempotent re-runs (recorded archives
skipped by zip sha256; the store inbox drops already-applied rows), and
self-healing of a corrupt source.json (rebuilt from the on-disk checksums, so
the revision guard is re-armed rather than silently disarmed).
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from tools.build_multi_tape import main as driver_main
from v8.schema import sha1_hex

HOUR_MS = 3_600_000


def _month_start_ms(month: str) -> int:
    y, m = int(month[:4]), int(month[5:7])
    return int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _write_checksum(out: Path, name: str) -> None:
    (out / f'{name}.CHECKSUM').write_text(
        hashlib.sha256((out / name).read_bytes()).hexdigest() + f' *{name}\n',
        encoding='utf-8')


def _write_kline_zip(out: Path, symbol: str, month: str) -> None:
    start_ms = _month_start_ms(month)
    lines = []
    for i in range(6):
        c = 100.0 + i
        lines.append(
            f'{start_ms + i * HOUR_MS},{c},{c + 0.5},{c - 0.5},{c},10,'
            f'{start_ms + (i + 1) * HOUR_MS - 1},1000,5,5,500,0')
    name = f'{symbol}-1h-{month}.zip'
    with zipfile.ZipFile(out / name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{symbol}-1h-{month}.csv', '\n'.join(lines) + '\n')
    _write_checksum(out, name)


def _write_funding_zip(out: Path, symbol: str, month: str) -> None:
    start_ms = _month_start_ms(month)
    rows = [f'{start_ms + i * 8 * HOUR_MS},8,{0.01 + i * 0.001}'
            for i in range(3)]
    name = f'{symbol}-fundingRate-{month}.zip'
    with zipfile.ZipFile(out / name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{symbol}-fundingRate-{month}.csv', '\n'.join(rows) + '\n')
    _write_checksum(out, name)


def _write_grid(out: Path, symbols: tuple[str, ...],
                months: tuple[str, ...]) -> None:
    for sym in symbols:
        for month in months:
            _write_kline_zip(out, sym, month)
            _write_funding_zip(out, sym, month)


ARGS = ['--symbols', 'AAAUSDT,BBBUSDT', '--start', '2025-01', '--end', '2025-03',
        '--channels', 'kline,funding']


def _rows(out: Path) -> list[dict]:
    return [json.loads(l) for l in (out / 'tape.jsonl').read_text().splitlines()]


def test_driver_builds_complete_provenance(tmp_path):
    _write_grid(tmp_path, ('AAAUSDT', 'BBBUSDT'), ('2025-01', '2025-02'))
    assert driver_main(['--out', str(tmp_path)] + ARGS) == 0

    rows = _rows(tmp_path)
    assert len(rows) == 2 * 2 * 6 + 2 * 2 * 3       # 24 kline + 12 funding
    meta = json.loads((tmp_path / 'source.json').read_text())
    assert meta['row_count'] == len(rows)
    assert meta['tape_hash'] == sha1_hex(rows)
    assert meta['symbols'] == ['AAAUSDT', 'BBBUSDT']
    assert len(meta['archives']) == 8
    # every archive carries a symbol + month + sha256 (multi-symbol provenance)
    for a in meta['archives']:
        assert a['symbol'] in ('AAAUSDT', 'BBBUSDT')
        assert a['month'] in ('2025-01', '2025-02')
        assert len(a['zip_sha256']) == 64


def test_driver_rerun_is_idempotent(tmp_path):
    _write_grid(tmp_path, ('AAAUSDT', 'BBBUSDT'), ('2025-01', '2025-02'))
    assert driver_main(['--out', str(tmp_path)] + ARGS) == 0
    tape_before = (tmp_path / 'tape.jsonl').read_text()
    meta_before = (tmp_path / 'source.json').read_text()

    # second run: every archive is already recorded with the same sha -> skipped
    assert driver_main(['--out', str(tmp_path)] + ARGS) == 0
    assert (tmp_path / 'tape.jsonl').read_text() == tape_before
    assert (tmp_path / 'source.json').read_text() == meta_before


def test_driver_rebuilds_corrupt_source(tmp_path):
    _write_grid(tmp_path, ('AAAUSDT', 'BBBUSDT'), ('2025-01', '2025-02'))
    assert driver_main(['--out', str(tmp_path)] + ARGS) == 0
    rows_before = _rows(tmp_path)

    # corrupt provenance (the concurrent-write failure mode) must self-heal:
    # the driver rebuilds source.json from the on-disk zips + checksums.
    (tmp_path / 'source.json').write_text(
        '{not valid json' + '}' * 5 + '\n', encoding='utf-8')
    assert driver_main(['--out', str(tmp_path)] + ARGS) == 0

    meta = json.loads((tmp_path / 'source.json').read_text())
    assert meta['row_count'] == len(rows_before)   # dedup: no rows were re-added
    assert len(meta['archives']) == 8
    # a third run now skips everything (revision guard re-armed from checksums)
    assert driver_main(['--out', str(tmp_path)] + ARGS) == 0
    assert (tmp_path / 'tape.jsonl').read_text().count('\n') == len(rows_before)


def test_driver_refuses_revised_archive(tmp_path):
    _write_grid(tmp_path, ('AAAUSDT',), ('2025-01',))
    assert driver_main(['--out', str(tmp_path), '--symbols', 'AAAUSDT',
                        '--start', '2025-01', '--end', '2025-02',
                        '--channels', 'kline']) == 0
    # a corrected archive (different bytes, same name) must fail closed
    (tmp_path / 'AAAUSDT-1h-2025-01.zip').write_bytes(b'corrected archive')
    _write_checksum(tmp_path, 'AAAUSDT-1h-2025-01.zip')
    with pytest.raises(SystemExit):
        driver_main(['--out', str(tmp_path), '--symbols', 'AAAUSDT',
                     '--start', '2025-01', '--end', '2025-02',
                     '--channels', 'kline'])
