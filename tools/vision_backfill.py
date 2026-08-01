"""Binance Vision monthly klines -> PIT tape (JSONL) with audit.

Phase 1 data plane (FEED_INGESTION_SPEC sections 4-5; ROADMAP Phase 1).
Downloads a Vision monthly klines archive and its `.CHECKSUM`, verifies the
SHA-256, unzips, and converts the CSV to a point-in-time tape in
`<out>/tape.jsonl` with the three distinct clocks (event / available /
ingested) and the canonical payload hash. A second run over the same output
dir is idempotent: the store's (source, event_id) inbox dedups to zero new
rows. `--audit` verifies monotonicity, venue-sequence gaps, row counts and
payload hashes, and exits non-zero on any violation.

OPEN_PIN (RUNLOG step 4): the runbook pins "reuse tools/data.py's row-building
logic (import it; do not fork it)", but `tools/data.py` raises SystemExit at
import time without polars/pandera/pyarrow/duckdb, and O-009 / runbook step 5
forbid adding those dependencies this session. This module therefore mirrors
data.py's *documented* contracts as stdlib code: the kline column order and
ms->ns conversion from `_normalize_kline_archive`, and the checksum file
contract from `_parse_checksum_file`/`_sha256_file`. The mapping below is the
same contract; it is not a new format.

The network path is exercised only with an explicit `--download` flag;
tests never touch the network (offline fixture zip + .CHECKSUM).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

# Allow `python tools/vision_backfill.py` from the repo root and `import v8.*`
# in tests (pytest already puts src/ on sys.path via pyproject pythonpath).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from v8.schema import sha1_hex  # noqa: E402
from v8.store import AppendOnlyLog  # noqa: E402

VISION_BASE = 'https://data.binance.vision/data/futures/um/monthly/klines'
# Futures archives are milliseconds; the tape normalizes to integer
# nanoseconds and records the source unit in schema_version
# (FEED_INGESTION_SPEC section 2).
SCHEMA_VERSION = 'binance-um-v1-ms'
# Usable at close + feed latency + aggregation latency (FEED_INGESTION_SPEC
# section 3); 1s mirrors the synthetic tape's configured latency.
DEFAULT_LATENCY_NS = 1_000_000_000

INTERVAL_MS = {
    '1m': 60_000, '3m': 180_000, '5m': 300_000, '15m': 900_000, '30m': 1_800_000,
    '1h': 3_600_000, '2h': 7_200_000, '4h': 14_400_000, '6h': 21_600_000,
    '8h': 28_800_000, '12h': 43_200_000, '1d': 86_400_000,
}

# Binance kline CSV column order (documented; mirrors tools/data.py's
# KLINE_COLUMNS contract). 12 columns, headerless by default.
KLINE_COLUMNS = ('open_time', 'open', 'high', 'low', 'close', 'volume',
                 'close_time', 'quote_asset_volume', 'number_of_trades',
                 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                 'ignore')


def vision_urls(symbol: str, interval: str, month: str,
                base: str = VISION_BASE) -> tuple[str, str]:
    """(zip_url, checksum_url) for a Vision monthly archive
    (`BTCUSDT-1h-2025-01.zip` + `.CHECKSUM`, FEED_INGESTION_SPEC section 5)."""
    name = f'{symbol}-{interval}-{month}.zip'
    return f'{base}/{symbol}/{interval}/{name}', f'{base}/{symbol}/{interval}/{name}.CHECKSUM'


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    """SHA-256 of a file; mirrors tools/data.py `_sha256_file` (stdlib part of
    its checksum contract — see OPEN_PIN above)."""
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum_file(path: Path, expected_filename: str) -> str:
    """Parse a Vision `.CHECKSUM` (`<sha256> *<name>`); mirrors
    tools/data.py `_parse_checksum_file`. Fails closed on empty, malformed,
    or name-mismatched checksum files."""
    text = path.read_text(encoding='utf-8').strip()
    if not text:
        raise ValueError(f'empty checksum file: {path}')
    parts = text.replace('*', ' ').split()
    if not parts:
        raise ValueError(f'invalid checksum file: {path}')
    digest = parts[0].lower()
    if len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest):
        raise ValueError(f'invalid SHA-256 in {path}: {digest!r}')
    if len(parts) > 1 and Path(parts[-1]).name != expected_filename:
        raise ValueError(
            f'checksum filename mismatch in {path}: expected {expected_filename!r}, '
            f'got {Path(parts[-1]).name!r}')
    return digest


def _ms_to_ns(ms: int) -> int:
    # Futures archives are ms; the guard keeps the parser safe if an archive
    # later follows the spot microsecond convention (data.py `_timestamp_ms_expr`).
    return (ms // 1000 if ms >= 100_000_000_000_000 else ms) * 1_000_000


def kline_csv_to_rows(csv_text: str, symbol: str, interval: str,
                      latency_ns: int = DEFAULT_LATENCY_NS) -> list[dict]:
    """Binance kline CSV -> PIT tape row dicts (FEED_INGESTION_SPEC section 2).

    Mirrors the documented mapping in tools/data.py `_normalize_kline_archive`:
    close_time is the venue event time, the bar is usable at
    close + latency, venue_sequence is the bar's open-time ordinal, and the
    dedup key is the kline open time. Only closed klines are emitted.
    """
    interval_ms = INTERVAL_MS.get(interval)
    if interval_ms is None:
        raise ValueError(f'unsupported interval {interval!r}; choose from {sorted(INTERVAL_MS)}')
    reader = csv.reader(io.StringIO(csv_text))
    first = next(reader, None)
    if first is None:
        raise ValueError('empty kline CSV')
    # Headerless by default; tolerate a header line like data.py `_csv_has_header`.
    header = not first[0].strip().strip('"').isdigit()
    if header:
        first = next(reader, None)
    if first is None:
        raise ValueError('kline CSV has a header but no data rows')

    rows: list[dict] = []
    for line in ([first] + list(reader)):
        if len(line) < 12:
            raise ValueError(f'kline CSV row has {len(line)} columns, expected 12: {line!r}')
        open_ms, close_ms = int(line[0]), int(line[6])
        event_ns = _ms_to_ns(close_ms)
        avail_ns = event_ns + latency_ns
        content = {
            'open': float(line[1]), 'high': float(line[2]), 'low': float(line[3]),
            'close': float(line[4]), 'volume': float(line[5]),
            'open_time_ms': open_ms, 'close_time_ms': close_ms,
            'quote_asset_volume': float(line[7]), 'number_of_trades': int(line[8]),
            'closed': True,
        }
        payload_hash = sha1_hex(content)
        rows.append({
            'source': 'binance-um', 'channel': 'kline', 'instrument': symbol,
            'event_time': event_ns,
            'available_time': avail_ns,
            'ingested_time': avail_ns,      # offline backfill: no live arrival
            'venue_sequence': open_ms // interval_ms,
            'event_id': f'{symbol}:{interval}:{open_ms}',
            'payload': dict(content, payload_hash=payload_hash,
                            schema_version=SCHEMA_VERSION),
        })
    return rows


def build_tape_from_zip(zip_path: Path, symbol: str, interval: str,
                        latency_ns: int = DEFAULT_LATENCY_NS) -> list[dict]:
    """Unzip a Vision monthly archive (exactly one CSV) and map it to tape rows."""
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if len(csv_names) != 1:
            raise ValueError(f'expected exactly one CSV in {zip_path}, got {csv_names}')
        csv_text = zf.read(csv_names[0]).decode('utf-8-sig')
    return kline_csv_to_rows(csv_text, symbol, interval, latency_ns)


def write_tape(out_dir: Path, rows: list[dict]) -> tuple[int, int]:
    """Append rows to `<out>/tape.jsonl` through the store's idempotent inbox.
    A second run over the same dir dedups to zero new rows (FEED_INGESTION_SPEC
    section 5 idempotency). Returns (rows_appended, rows_skipped_duplicates)."""
    log = AppendOnlyLog(out_dir / 'tape.jsonl')
    appended = skipped = 0
    for row in rows:
        if log.append(dict(row)):
            appended += 1
        else:
            skipped += 1
    return appended, skipped


def write_source_meta(out_dir: Path, symbol: str, interval: str, month: str,
                      zip_sha256: str) -> dict:
    """Provenance record for the audit: what the tape was built from and the
    row count / tape hash actually stored (post-dedup)."""
    stored = AppendOnlyLog(out_dir / 'tape.jsonl').read()
    meta = {'symbol': symbol, 'interval': interval, 'month': month,
            'zip_sha256': zip_sha256, 'row_count': len(stored),
            'tape_hash': sha1_hex(stored), 'schema_version': SCHEMA_VERSION}
    (out_dir / 'source.json').write_text(
        json.dumps(meta, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return meta


class TapeAuditError(ValueError):
    pass


def audit_tape(out_dir: Path) -> dict:
    """Monotonicity, gap, row-count and payload-hash checks
    (FEED_INGESTION_SPEC section 4). Raises TapeAuditError on the first
    violation; the CLI exits non-zero."""
    log = AppendOnlyLog(out_dir / 'tape.jsonl')
    rows = log.read()
    problems: list[str] = []
    prev: dict | None = None
    for rec in rows:
        if 'channel' not in rec:
            continue
        payload = rec['payload']
        content = {k: v for k, v in payload.items()
                   if k not in ('payload_hash', 'schema_version')}
        if payload.get('payload_hash') != sha1_hex(content):
            problems.append(f'payload hash mismatch for {rec["event_id"]}')
        if prev is not None:
            for field in ('event_time', 'available_time', 'venue_sequence'):
                if rec[field] < prev[field]:
                    problems.append(
                        f'non-monotonic {field} at {rec["event_id"]}: '
                        f'{rec[field]} < {prev[field]}')
            if rec['venue_sequence'] - prev['venue_sequence'] > 1:
                problems.append(
                    f'venue sequence gap at {rec["event_id"]}: '
                    f'{prev["venue_sequence"]} -> {rec["venue_sequence"]}')
        prev = rec

    meta_path = out_dir / 'source.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if meta['row_count'] != len(rows):
            problems.append(f'row count {len(rows)} != recorded {meta["row_count"]}')
        if meta['tape_hash'] != sha1_hex(rows):
            problems.append('tape hash differs from recorded source.json')
        zip_path = out_dir / f'{meta["symbol"]}-{meta["interval"]}-{meta["month"]}.zip'
        if zip_path.exists() and sha256_file(zip_path) != meta['zip_sha256']:
            problems.append('zip sha256 differs from recorded source.json')
    if problems:
        raise TapeAuditError('; '.join(problems))
    return {'row_count': len(rows), 'payload_hashes_ok': True,
            'monotonic': True, 'venue_gaps': 0}


def _http_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--symbol', required=True, help='e.g. BTCUSDT')
    ap.add_argument('--interval', default='1h', choices=sorted(INTERVAL_MS))
    ap.add_argument('--month', required=True, help='YYYY-MM, e.g. 2025-01')
    ap.add_argument('--out', required=True, type=Path, help='output directory')
    ap.add_argument('--download', action='store_true',
                    help='fetch zip + .CHECKSUM from data.binance.vision '
                         '(offline otherwise: the archive must already be in --out)')
    ap.add_argument('--audit', action='store_true',
                    help='audit <out>/tape.jsonl and exit (non-zero on violation)')
    ap.add_argument('--latency-ns', type=int, default=DEFAULT_LATENCY_NS)
    ap.add_argument('--url-base', default=VISION_BASE)
    args = ap.parse_args(argv)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    if args.audit:
        report = audit_tape(out)
        print(json.dumps(report, sort_keys=True))
        return 0

    zip_path = out / f'{args.symbol}-{args.interval}-{args.month}.zip'
    checksum_path = out / f'{zip_path.name}.CHECKSUM'
    if args.download:
        zip_url, checksum_url = vision_urls(args.symbol, args.interval,
                                            args.month, args.url_base)
        _http_download(checksum_url, checksum_path)
        _http_download(zip_url, zip_path)
    if not zip_path.exists():
        raise SystemExit(
            f'{zip_path} not found; pass --download or place the archive (and its '
            f'.CHECKSUM) in {out}')

    expected = parse_checksum_file(checksum_path, zip_path.name)
    actual = sha256_file(zip_path)
    if actual != expected:
        raise SystemExit(
            f'SHA-256 mismatch for {zip_path}: expected {expected}, got {actual}')

    rows = build_tape_from_zip(zip_path, args.symbol, args.interval,
                               args.latency_ns)
    appended, skipped = write_tape(out, rows)
    meta = write_source_meta(out, args.symbol, args.interval, args.month, actual)
    print(f'wrote {appended} rows (skipped {skipped} duplicates); '
          f'tape_hash={meta["tape_hash"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
