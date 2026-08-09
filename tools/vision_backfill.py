"""Binance Vision monthly archives -> PIT tape (JSONL) with audit.

Phase 1 data plane (FEED_INGESTION_SPEC sections 3-5; ROADMAP Phase 1).
Downloads a Vision monthly klines or fundingRate archive and its
`.CHECKSUM`, verifies the SHA-256, unzips, and converts the CSV to a
point-in-time tape in `<out>/tape.jsonl` with the three distinct clocks
(event / available / ingested) and the canonical payload hash. A second run
over the same output dir is idempotent: the store's (source, event_id) inbox
dedups to zero new rows. `--sort` rewrites the tape in canonical replay order
(file order == replay order), and `--audit` verifies monotonicity, venue
sequence gaps, payload hashes and provenance, exiting non-zero on any
violation.

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
import math
import os
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

# Funding channel (D-041; DATASET_SPEC section 6.4). Vision monthly
# fundingRate archives; one TapeRow per settlement boundary with the three
# clocks, funding_time, funding_rate (FEED_INGESTION_SPEC section 3).
FUNDING_BASE = 'https://data.binance.vision/data/futures/um/monthly/fundingRate'
FUNDING_SCHEMA_VERSION = 'binance-um-funding-v1-ms'
HOUR_MS = 3_600_000
HOUR_NS = HOUR_MS * 1_000_000

# Binance public funding archives have changed headers over time; route
# aliases explicitly and fail if the timestamp/rate columns cannot be resolved
# (mirrors tools/data.py `_normalize_funding_archive` + `_validate_funding`).
FUNDING_TIMESTAMP_ALIASES = ('calc_time', 'funding_time', 'fundingtime',
                             'time', 'timestamp')
FUNDING_RATE_ALIASES = ('last_funding_rate', 'funding_rate', 'fundingrate',
                        'rate')
FUNDING_INTERVAL_ALIASES = ('funding_interval_hours', 'funding_interval',
                            'interval_hours')


def vision_urls(symbol: str, interval: str, month: str,
                base: str = VISION_BASE) -> tuple[str, str]:
    """(zip_url, checksum_url) for a Vision monthly archive
    (`BTCUSDT-1h-2025-01.zip` + `.CHECKSUM`, FEED_INGESTION_SPEC section 5)."""
    name = f'{symbol}-{interval}-{month}.zip'
    return f'{base}/{symbol}/{interval}/{name}', f'{base}/{symbol}/{interval}/{name}.CHECKSUM'


def funding_urls(symbol: str, month: str, base: str = FUNDING_BASE) -> tuple[str, str]:
    """(zip_url, checksum_url) for a Vision monthly fundingRate archive
    (`BTCUSDT-fundingRate-2025-01.zip` + `.CHECKSUM`; mirrors
    tools/data.py `_archive_relative_path`)."""
    name = f'{symbol}-fundingRate-{month}.zip'
    return f'{base}/{symbol}/{name}', f'{base}/{symbol}/{name}.CHECKSUM'


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


def _resolve_alias(columns: list[str], aliases: tuple[str, ...], label: str,
                   optional: bool = False) -> int | None:
    """Resolve a funding CSV column INDEX by header alias; mirrors tools/data.py
    `_normalize_column_name` + `_resolve_alias`. Fails closed when the column
    cannot be resolved (a funding row without a timestamp/rate is useless);
    `optional=True` returns None instead of raising."""
    normalized = {c.strip().strip('"').lower().replace(' ', '_').replace('-', '_'): i
                  for i, c in enumerate(columns)}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    if optional:
        return None
    raise ValueError(f'cannot resolve {label}; columns={columns}, aliases={aliases}')


def funding_csv_to_rows(csv_text: str, symbol: str,
                        latency_ns: int = DEFAULT_LATENCY_NS) -> list[dict]:
    """Vision fundingRate CSV -> PIT tape row dicts (FEED_INGESTION_SPEC 3;
    DATASET_SPEC 6.4).

    Mirrors tools/data.py `_normalize_funding_archive`: headerless archives
    use the documented three-column order (calc_time, funding_interval_hours,
    last_funding_rate); headered archives are alias-routed. A non-finite or
    |rate| > 0.10 value fails closed (data.py `_validate_funding`). The
    settlement boundary is the event time; the row is usable at
    boundary + latency. event_id embeds a funding namespace so it can never
    collide with a kline event_id under the (source, event_id) dedup key.
    """
    reader = csv.reader(io.StringIO(csv_text))
    first = next(reader, None)
    if first is None:
        raise ValueError('empty funding CSV')
    header = not first[0].strip().strip('"').isdigit()
    if header:
        timestamp_idx = _resolve_alias(first, FUNDING_TIMESTAMP_ALIASES,
                                       'funding timestamp')
        rate_idx = _resolve_alias(first, FUNDING_RATE_ALIASES, 'funding rate')
        interval_idx = _resolve_alias(first, FUNDING_INTERVAL_ALIASES,
                                      'funding interval', optional=True)
        assert timestamp_idx is not None and rate_idx is not None
        rows_iter = reader
    else:
        timestamp_idx, interval_idx, rate_idx = 0, 1, 2
        rows_iter = iter([first] + list(reader))

    rows: list[dict] = []
    for line in rows_iter:
        funding_ts_ms = int(line[timestamp_idx])
        rate = float(line[rate_idx])
        if not math.isfinite(rate) or abs(rate) > 0.10:
            raise ValueError(
                f'implausible funding rate {rate} at {funding_ts_ms}: '
                'fail closed (data.py `_validate_funding` gate)')
        if interval_idx is not None and line[interval_idx].strip():
            interval_hours = float(line[interval_idx])
        else:
            interval_hours = 8.0
        # calc_time carries a sub-boundary ms jitter (+1ms in some archives,
        # observed 2026-06); the settlement boundary is the hour-aligned floor,
        # which is what the schedule lookup and the venue sequence use.
        boundary_ms = (funding_ts_ms // HOUR_MS) * HOUR_MS
        event_ns = _ms_to_ns(boundary_ms)
        avail_ns = event_ns + latency_ns
        content = {'funding_time_ms': boundary_ms,
                   'funding_rate': rate,
                   'funding_interval_hours': interval_hours}
        payload_hash = sha1_hex(content)
        rows.append({
            'source': 'binance-um', 'channel': 'funding', 'instrument': symbol,
            'event_time': event_ns,
            'available_time': avail_ns,
            'ingested_time': avail_ns,      # offline backfill: no live arrival
            'venue_sequence': boundary_ms // HOUR_MS,
            'event_id': f'{symbol}:funding:{boundary_ms}',
            'payload': dict(content, payload_hash=payload_hash,
                            schema_version=FUNDING_SCHEMA_VERSION),
        })
    return rows


def _zip_name(symbol: str, interval: str, channel: str, month: str) -> str:
    """Vision archive filename for a channel (kline archives carry the bar
    interval; funding archives do not)."""
    if channel == 'funding':
        return f'{symbol}-fundingRate-{month}.zip'
    return f'{symbol}-{interval}-{month}.zip'


def build_tape_from_zip(zip_path: Path, symbol: str, interval: str,
                        latency_ns: int = DEFAULT_LATENCY_NS,
                        channel: str = 'kline') -> list[dict]:
    """Unzip a Vision monthly archive (exactly one CSV) and map it to tape rows."""
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if len(csv_names) != 1:
            raise ValueError(f'expected exactly one CSV in {zip_path}, got {csv_names}')
        csv_text = zf.read(csv_names[0]).decode('utf-8-sig')
    if channel == 'funding':
        return funding_csv_to_rows(csv_text, symbol, latency_ns)
    if channel == 'kline':
        return kline_csv_to_rows(csv_text, symbol, interval, latency_ns)
    raise ValueError(f'unsupported channel {channel!r}')


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


def _replay_key(row: dict) -> tuple[int, int, int]:
    return (row['event_time'], row['available_time'], row['venue_sequence'])


def sort_tape(out_dir: Path) -> dict:
    """Rewrite <out>/tape.jsonl in canonical replay order
    (event_time, available_time, venue_sequence) — the store's replay sort
    (store.py `replay_tape`) — so file order == replay order and the tape hash
    is deterministic (PERSISTENCE_REPLAY_SPEC 4). Atomic via temp file +
    os.replace; rewrites source.json's row_count/tape_hash. Idempotent on an
    already-sorted tape."""
    log = AppendOnlyLog(out_dir / 'tape.jsonl')
    rows = log.read()
    sorted_rows = sorted(rows, key=_replay_key)
    tmp = out_dir / 'tape.jsonl.tmp'
    tmp.write_text(
        ''.join(json.dumps(r, sort_keys=True) + '\n' for r in sorted_rows),
        encoding='utf-8')
    os.replace(tmp, out_dir / 'tape.jsonl')
    meta = _load_provenance(out_dir)
    if meta:
        meta['row_count'] = len(sorted_rows)
        meta['tape_hash'] = sha1_hex(sorted_rows)
        (out_dir / 'source.json').write_text(
            json.dumps(meta, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return meta


def _load_provenance(out_dir: Path) -> dict:
    path = out_dir / 'source.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    return data


def check_archive_revision(out_dir: Path, month: str, zip_sha256: str,
                           channel: str = 'kline', symbol: str = '') -> None:
    """Fail closed if a recorded (symbol, channel, month) is re-run with a
    DIFFERENT zip: a venue-corrected archive has the same event times (same
    event_ids), so the store's dedup would silently keep the superseded rows
    while the provenance records the new checksum — a silent data corruption.
    A revised archive invalidates the existing tape; rebuild in a fresh dir.

    The key includes the SYMBOL. Keying on (channel, month) alone was correct
    only while a tape dir held one instrument: the moment a second symbol is
    ingested, its 2025-01 archive has a different checksum than the first
    symbol's 2025-01 and is misread as a revision of it, so a multi-instrument
    tape could never be built at all.
    """
    prov = _load_provenance(out_dir)
    legacy_symbol = prov.get('symbol', '')
    # An omitted symbol means "the tape's own", which is unambiguous exactly
    # while the tape holds one instrument. Resolving it here keeps the guard
    # armed for single-symbol callers that predate the symbol argument — an
    # unmatched key would silently admit a revised archive.
    symbol = symbol or legacy_symbol
    recorded = {(a.get('symbol', legacy_symbol), a.get('channel', 'kline'),
                 a['month']): a['zip_sha256']
                for a in prov.get('archives', [])}
    # Legacy single-month source.json (top-level month/zip_sha256, written by
    # the pre-per-month fix) must still guard the revision: otherwise a revised
    # archive silently passes and the store keeps superseded bars.
    if not prov.get('archives') and 'month' in prov and 'zip_sha256' in prov:
        recorded[(legacy_symbol, 'kline', prov['month'])] = prov['zip_sha256']
    key = (symbol, channel, month)
    if key in recorded and recorded[key] != zip_sha256:
        raise ValueError(
            f'refusing to ingest revised archive: {symbol} {channel}/{month} '
            f'was recorded with sha256 {recorded[key]}, the current zip is '
            f'{zip_sha256}. A corrected archive invalidates the existing tape '
            '— rebuild it in a fresh out dir.')


def write_source_meta(out_dir: Path, symbol: str, interval: str, month: str,
                      zip_sha256: str, channel: str = 'kline') -> dict:
    """Per-month per-channel provenance: every ingested archive
    (channel + month + zip sha256) is recorded, with the full-tape row count
    and tape hash. Re-running a (channel, month) with the SAME zip is
    idempotent (the entry is kept); a different zip was already rejected by
    check_archive_revision."""
    prov = _load_provenance(out_dir)
    legacy_symbol = prov.get('symbol', symbol)
    archives = {(a.get('symbol', legacy_symbol), a.get('channel', 'kline'),
                 a['month']): {**a, 'symbol': a.get('symbol', legacy_symbol)}
                for a in prov.get('archives', [])}
    archives[(symbol, channel, month)] = {
        'symbol': symbol, 'channel': channel, 'month': month,
        'zip_sha256': zip_sha256}
    stored = AppendOnlyLog(out_dir / 'tape.jsonl').read()
    symbols = sorted({a['symbol'] for a in archives.values()})
    meta = {'symbol': symbols[0] if len(symbols) == 1 else '',
            'symbols': symbols, 'interval': interval,
            'archives': [archives[m] for m in sorted(archives)],
            'row_count': len(stored),
            'tape_hash': sha1_hex(stored), 'schema_version': SCHEMA_VERSION}
    (out_dir / 'source.json').write_text(
        json.dumps(meta, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return meta


class TapeAuditError(ValueError):
    pass


def audit_tape(out_dir: Path, funding_hours: int = 8,
               rows: list[dict] | None = None) -> dict:
    """Monotonicity, gap, payload-hash, duplicate-row and provenance checks
    (FEED_INGESTION_SPEC section 4). Raises TapeAuditError on the first
    violation; the CLI exits non-zero. Fails closed when provenance
    (source.json) is missing or its recorded archives cannot be verified —
    a check that cannot evaluate must reject, not pass (OPERATIONS_SPEC
    section 5). event_time/available_time are globally monotonic across
    channels (funding rows interleave the kline stream); venue_sequence is
    per-channel (kline gap > 1 bar, funding gap > funding_hours). A tape whose
    file order is not the replay order fails closed (run --sort).

    `rows` (optional) supplies the already-parsed records — monitor_tape
    parses the tape once and passes it here so a --schema cycle does not
    re-read and re-json-parse the whole tape a second time."""
    if rows is None:
        log = AppendOnlyLog(out_dir / 'tape.jsonl')
        rows = log.read()
    problems: list[str] = []
    prev: dict | None = None
    prev_by_channel: dict[str, dict] = {}
    seen_ids: set[tuple[str, str]] = set()
    for rec in rows:
        if 'channel' not in rec:
            continue
        key = (rec.get('source', ''), rec.get('event_id', ''))
        if key in seen_ids:
            problems.append(f'duplicate row (source, event_id) = {key}')
        seen_ids.add(key)
        payload = rec['payload']
        content = {k: v for k, v in payload.items()
                   if k not in ('payload_hash', 'schema_version')}
        if payload.get('payload_hash') != sha1_hex(content):
            problems.append(f'payload hash mismatch for {rec["event_id"]}')
        channel = rec['channel']
        if channel == 'kline':
            # Data invariants the payload hash cannot see (a hash is
            # self-consistent by construction): a NaN/±inf close, an
            # OHLC-ordering violation, or negative volume must fail the audit.
            o, h, l, c = (payload.get(f) for f in ('open', 'high', 'low', 'close'))
            if not all(type(x) in (int, float) and math.isfinite(float(x))
                       for x in (o, h, l, c)):
                problems.append(f'non-finite or non-numeric OHLC at {rec["event_id"]}')
            elif min(float(o), float(h), float(l), float(c)) <= 0:
                problems.append(f'non-positive OHLC at {rec["event_id"]}')
            elif float(h) < max(float(o), float(c)) \
                    or float(l) > min(float(o), float(c)) or float(h) < float(l):
                problems.append(f'OHLC invariant violation at {rec["event_id"]}')
            vol = payload.get('volume')
            if vol is not None and (type(vol) not in (int, float)
                                    or not math.isfinite(float(vol))
                                    or float(vol) < 0):
                problems.append(f'negative or non-finite volume at {rec["event_id"]}')
        elif channel == 'funding':
            rate = payload.get('funding_rate')
            if not (type(rate) in (int, float) and math.isfinite(float(rate))):
                problems.append(f'non-finite funding rate at {rec["event_id"]}')
            elif abs(float(rate)) > 0.10:
                problems.append(
                    f'implausible funding rate at {rec["event_id"]}: {rate}')
            if rec['event_time'] % HOUR_NS != 0:
                problems.append(
                    f'funding event not hour-aligned at {rec["event_id"]}')
        else:
            problems.append(f'unknown channel {channel!r} at {rec["event_id"]}')
        # event_time / available_time are globally monotonic; venue_sequence
        # is per-channel with per-channel gap semantics.
        if prev is not None:
            for field in ('event_time', 'available_time'):
                if rec[field] < prev[field]:
                    problems.append(
                        f'non-monotonic {field} at {rec["event_id"]}: '
                        f'{rec[field]} < {prev[field]}')
        prev = rec
        pc = prev_by_channel.get(channel)
        if pc is not None:
            if rec['venue_sequence'] < pc['venue_sequence']:
                problems.append(
                    f'non-monotonic venue_sequence ({channel}) at '
                    f'{rec["event_id"]}: {rec["venue_sequence"]} < '
                    f'{pc["venue_sequence"]}')
            gap = rec['venue_sequence'] - pc['venue_sequence']
            if channel == 'funding':
                # The gap from the PREVIOUS settlement to this one is governed
                # by the interval in effect at the previous settlement (the
                # venue's declared funding_interval_hours on that row). Using
                # the CURRENT row's interval false-positives the settlement
                # right after a schedule change (e.g. a 4h row followed by a
                # 2h row: the 4h gap is the old schedule, not a missing row).
                hours = pc['payload'].get('funding_interval_hours') or funding_hours
                if gap > hours:
                    problems.append(
                        f'funding venue sequence gap at {rec["event_id"]}: '
                        f'{pc["venue_sequence"]} -> {rec["venue_sequence"]} '
                        f'(> {hours}h)')
            elif gap > 1:
                problems.append(
                    f'venue sequence gap at {rec["event_id"]}: '
                    f'{pc["venue_sequence"]} -> {rec["venue_sequence"]}')
        prev_by_channel[channel] = rec

    if sorted(rows, key=_replay_key) != rows:
        problems.append(
            'tape file order != replay order (event_time, available_time, '
            'venue_sequence); run --sort')

    meta_path = out_dir / 'source.json'
    if not meta_path.exists():
        problems.append('source.json missing — provenance cannot be verified')
    else:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if meta.get('row_count') != len(rows):
            problems.append(f'row count {len(rows)} != recorded {meta.get("row_count")}')
        if meta.get('tape_hash') != sha1_hex(rows):
            problems.append('tape hash differs from recorded source.json')
        for archive in meta.get('archives', []):
            # Per-archive symbol: a multi-instrument tape has no single
            # top-level symbol, and reconstructing the zip name from one would
            # look for a file that never existed.
            sym = archive.get('symbol') or meta.get('symbol', '')
            zip_path = out_dir / _zip_name(
                sym, meta.get('interval', '1h'),
                archive.get('channel', 'kline'), archive['month'])
            if not zip_path.exists():
                problems.append(
                    f'recorded archive zip missing: {zip_path.name} — '
                    'provenance cannot be verified')
            elif sha256_file(zip_path) != archive['zip_sha256']:
                problems.append(
                    f'zip sha256 differs from recorded source.json for '
                    f'{sym} {archive.get("channel", "kline")}/'
                    f'{archive["month"]}')
    if problems:
        raise TapeAuditError('; '.join(problems))
    return {'row_count': len(rows), 'payload_hashes_ok': True,
            'monotonic': True, 'venue_gaps': 0, 'duplicate_rows': 0}


def _http_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--symbol', default=None, help='e.g. BTCUSDT (build runs)')
    ap.add_argument('--interval', default='1h', choices=sorted(INTERVAL_MS))
    ap.add_argument('--month', default=None, help='YYYY-MM, e.g. 2025-01 '
                                                  '(build runs only)')
    ap.add_argument('--channel', default='kline', choices=('kline', 'funding'))
    ap.add_argument('--out', required=True, type=Path, help='output directory')
    ap.add_argument('--download', action='store_true',
                    help='fetch zip + .CHECKSUM from data.binance.vision '
                         '(offline otherwise: the archive must already be in --out)')
    ap.add_argument('--audit', action='store_true',
                    help='audit <out>/tape.jsonl and exit (non-zero on violation)')
    ap.add_argument('--sort', action='store_true',
                    help='rewrite <out>/tape.jsonl in replay order and refresh '
                         'source.json (file order == replay order)')
    ap.add_argument('--funding-hours', type=int, default=8,
                    help='funding venue-sequence gap tolerance for --audit')
    ap.add_argument('--latency-ns', type=int, default=DEFAULT_LATENCY_NS)
    ap.add_argument('--url-base', default=None,
                    help='archive base URL (default per channel)')
    args = ap.parse_args(argv)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    if args.sort:
        meta = sort_tape(out)
        print(f'sorted {meta.get("row_count", 0)} rows; '
              f'tape_hash={meta.get("tape_hash")}')
        if not args.audit:
            return 0
    if args.audit:
        report = audit_tape(out, funding_hours=args.funding_hours)
        print(json.dumps(report, sort_keys=True))
        return 0

    if not args.symbol or not args.month:
        raise SystemExit('--symbol and --month are required for a build run')
    channel = args.channel
    base = args.url_base or (FUNDING_BASE if channel == 'funding' else VISION_BASE)
    zip_name = _zip_name(args.symbol, args.interval, channel, args.month)
    zip_path = out / zip_name
    checksum_path = out / f'{zip_name}.CHECKSUM'
    if args.download:
        if channel == 'funding':
            zip_url, checksum_url = funding_urls(args.symbol, args.month, base)
        else:
            zip_url, checksum_url = vision_urls(args.symbol, args.interval,
                                                args.month, base)
        _http_download(checksum_url, checksum_path)
        _http_download(zip_url, zip_path)
    if not zip_path.exists():
        raise SystemExit(
            f'{zip_path} not found; pass --download or place the archive (and its '
            f'.CHECKSUM) in {out}')

    expected = parse_checksum_file(checksum_path, zip_name)
    actual = sha256_file(zip_path)
    if actual != expected:
        raise SystemExit(
            f'SHA-256 mismatch for {zip_path}: expected {expected}, got {actual}')

    rows = build_tape_from_zip(zip_path, args.symbol, args.interval,
                               args.latency_ns, channel)
    check_archive_revision(out, args.month, actual, channel, args.symbol)
    appended, skipped = write_tape(out, rows)
    meta = write_source_meta(out, args.symbol, args.interval, args.month,
                             actual, channel)
    print(f'wrote {appended} rows (skipped {skipped} duplicates); '
          f'tape_hash={meta["tape_hash"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
