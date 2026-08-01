"""Offline tests for the session-2 tooling admission (D-037): the pure
planning/checksum helpers of tools/data.py.

Network is never required — plan_archives is deterministic URL construction
and the checksum helpers are local file logic. The heavy deps
(polars/pyarrow/pandera/duckdb) are installed at session-2 step 1 for Phase-1
parquet materialization (DATASET_SPEC section 5); the decision path stays
stdlib-only (O-009). These tests pin the admitted path without touching the
network.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

from tools.data import (
    BASE_URL, DatasetConfig, plan_archives, _parse_checksum_file, _sha256_file,
)


def _config(tmp_path: Path, start: str = '2026-06-01', end: str = '2026-07-01',
            interval: str = '1h') -> DatasetConfig:
    return DatasetConfig(symbols=('BTCUSDT',), start=date.fromisoformat(start),
                         end=date.fromisoformat(end), out_dir=tmp_path / 'out',
                         raw_cache_dir=tmp_path / 'cache', interval=interval,
                         data_types=('klines',))


def test_plan_archives_monthly_vision_url(tmp_path):
    """A whole-month window plans exactly one official Vision monthly archive
    with the documented naming (FEED_INGESTION_SPEC section 5)."""
    specs = plan_archives(_config(tmp_path))
    assert len(specs) == 1
    spec = specs[0]
    assert spec.relative_path == (
        'futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2026-06.zip')
    assert spec.url == f'{BASE_URL}/{spec.relative_path}'
    assert spec.checksum_url == f'{spec.url}.CHECKSUM'
    assert (spec.symbol, spec.interval, spec.data_type) == ('BTCUSDT', '1h', 'klines')


def test_plan_archives_partial_boundary_uses_daily(tmp_path):
    """Partial boundary months plan daily archives (data.py cadence rule),
    which is the documented Vision layout for incomplete months."""
    specs = plan_archives(_config(tmp_path, start='2026-06-15', end='2026-07-02'))
    # [start, end) -> 2026-06-15..06-30 (16 days) + 2026-07-01 (1 day) = 17
    # daily archives, each named by its exact day.
    assert len(specs) == 17, [s.relative_path for s in specs]
    assert all(s.cadence == 'daily' for s in specs)
    expected_days = {f'2026-06-{d:02d}' for d in range(15, 31)} | {'2026-07-01'}
    got = {'-'.join(Path(s.relative_path).stem.split('-')[-3:])
           for s in specs}            # date segment, e.g. 2026-06-15
    assert got == expected_days


def test_parse_checksum_file_contract(tmp_path):
    """Vision CHECKSUM files parse to the digest and fail closed on malformed
    or name-mismatched content (FEED_INGESTION_SPEC section 5)."""
    ck = tmp_path / 'x.CHECKSUM'
    digest = hashlib.sha256(b'x').hexdigest()
    ck.write_text(f'{digest} *BTCUSDT-1h-2026-06.zip\n', encoding='utf-8')
    assert _parse_checksum_file(ck, 'BTCUSDT-1h-2026-06.zip') == digest
    ck.write_text(f'{digest} *other.zip\n', encoding='utf-8')
    with pytest.raises(ValueError):
        _parse_checksum_file(ck, 'BTCUSDT-1h-2026-06.zip')
    ck.write_text('not-a-digest\n', encoding='utf-8')
    with pytest.raises(ValueError):
        _parse_checksum_file(ck, 'x.zip')


def test_sha256_file_matches_hashing(tmp_path):
    p = tmp_path / 'f.bin'
    p.write_bytes(b'hello world')
    assert _sha256_file(p) == hashlib.sha256(b'hello world').hexdigest()
