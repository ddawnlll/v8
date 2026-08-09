#!/usr/bin/env python3
"""Drive `vision_backfill` over a symbol x month x channel grid into ONE tape.

Why a multi-instrument tape (D-053 follow-on): the 12-month single-instrument
dev tape starves the evidence in two independent ways that this fixes.

1. Exposure slots. Rule 16 (D-018) permits one active exposure per (instrument,
   direction), so a one-instrument universe offers TWO slots to 27 Experts. The
   measured consequence on the 2026-08-06 dev run was an execution_share of
   0.169 against the O-017 reference of 0.4576: 85.8% of triggered candidates
   died at the portfolio gate, and which Expert survived was decided by arrival
   order rather than by quality. N instruments make 2N slots.
2. Episodes. The preregistered detection bar needs roughly 680 episodes per
   family to see a 0.10 R effect at the slate-wide Bonferroni alpha; most
   families had 30-100.

The tape stays STRICTLY inside the dev window: the frozen holdout opens at
2026-07-01 (prereg section 13) and this builder refuses any month at or past
it, because a dev tape that reaches into the holdout destroys the one piece of
evidence the program has not yet spent.

Single-process fast path: the original driver spawned one subprocess per
archive, and each per-archive provenance write re-read and re-hashed the whole
growing tape — O(N²) in rows, ~80 min of CPU for a 960-archive grid. This
driver imports vision_backfill's functions directly, opens ONE log, dedups
against ONE inbox, and writes provenance ONCE at the end (atomic via
os.replace). Re-runs are idempotent: an archive already recorded with the SAME
zip sha256 is skipped, and the store's (source, event_id) inbox drops any
already-applied row regardless. A corrupt or missing source.json is rebuilt
from the zips on disk + their .CHECKSUM files, which re-arms the revision
guard from the authoritative checksums rather than silently disarming it.

Usage:
  python tools/build_multi_tape.py --out research/tape/multi-1h-4y \\
      --symbols BTCUSDT,ETHUSDT --start 2022-07 --end 2026-07

Add --download to fetch missing zips from data.binance.vision; without it the
builder runs offline and any archive whose zip is not already in --out is
counted as a miss (never a silent coverage gap).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from tools.vision_backfill import (  # noqa: E402
    DEFAULT_LATENCY_NS, FUNDING_BASE, SCHEMA_VERSION, VISION_BASE,
    build_tape_from_zip, funding_urls, parse_checksum_file, sha256_file,
    vision_urls, _http_download, _zip_name,
)
from v8.schema import sha1_hex  # noqa: E402
from v8.store import AppendOnlyLog  # noqa: E402

# The frozen holdout anchor (prereg section 13). A dev tape must end before it.
HOLDOUT_ANCHOR = date(2026, 7, 1)

DEFAULT_SYMBOLS = (
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT',
)
DEFAULT_BUDGET_GB = 10.0


def months(start: date, end: date) -> list[str]:
    """Inclusive-exclusive month labels, `YYYY-MM`."""
    out, y, m = [], start.year, start.month
    while (y, m) < (end.year, end.month):
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _parse_month(s: str) -> date:
    y, m = s.split('-')
    return date(int(y), int(m), 1)


def dir_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())


def _load_provenance(out: Path) -> dict:
    """source.json, or {} when missing/corrupt (a corrupt file is rebuilt from
    the on-disk zips + .CHECKSUM files, which is a rebuild from a trusted
    source, not a disarmed revision guard)."""
    path = out / 'source.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, ValueError):
        return {'_corrupt': True}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--symbols', default=','.join(DEFAULT_SYMBOLS))
    ap.add_argument('--start', default='2022-07', help='YYYY-MM inclusive')
    ap.add_argument('--end', default='2026-07', help='YYYY-MM exclusive')
    ap.add_argument('--interval', default='1h')
    ap.add_argument('--channels', default='kline,funding')
    ap.add_argument('--budget-gb', type=float, default=DEFAULT_BUDGET_GB)
    ap.add_argument('--download', action='store_true',
                    help='fetch missing zips from data.binance.vision (offline '
                         'otherwise: archives must already be in --out)')
    a = ap.parse_args(argv)

    start, end = _parse_month(a.start), _parse_month(a.end)
    if end > HOLDOUT_ANCHOR:
        print(f'REFUSED: --end {a.end} reaches the frozen holdout '
              f'({HOLDOUT_ANCHOR}); a dev tape must stop before it',
              file=sys.stderr)
        return 2
    symbols = [s.strip().upper() for s in a.symbols.split(',') if s.strip()]
    channels = [c.strip() for c in a.channels.split(',') if c.strip()]
    ms = months(start, end)
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    budget = int(a.budget_gb * 1024 ** 3)

    prov = _load_provenance(out)
    if prov.get('_corrupt'):
        print('WARNING: source.json is corrupt (a concurrent write raced); '
              'rebuilding provenance from the zips on disk and their .CHECKSUM '
              'files. The revision guard is re-armed from the checksums.',
              file=sys.stderr)
    recorded: dict[tuple[str, str, str], str] = {}
    for entry in prov.get('archives', []):
        sym = entry.get('symbol')
        ch = entry.get('channel', 'kline')
        if sym:
            recorded[(sym, ch, entry['month'])] = entry['zip_sha256']

    # One append-only log for the whole grid: the dedup inbox is built once,
    # and appended rows are the only file writes (no per-archive full re-read).
    log = AppendOnlyLog(out / 'tape.jsonl')
    total = len(symbols) * len(ms) * len(channels)
    print(f'{len(symbols)} symbols x {len(ms)} months x {len(channels)} '
          f'channels = {total} archives -> {out}', flush=True)

    done = skipped = missing = 0
    misses: dict[str, list[str]] = {}
    for symbol in symbols:
        for month in ms:
            for channel in channels:
                zip_name = _zip_name(symbol, a.interval, channel, month)
                zip_path = out / zip_name
                checksum_path = out / f'{zip_name}.CHECKSUM'
                if not zip_path.exists():
                    if a.download:
                        base = FUNDING_BASE if channel == 'funding' else VISION_BASE
                        if channel == 'funding':
                            zurl, cksurl = funding_urls(symbol, month, base)
                        else:
                            zurl, cksurl = vision_urls(symbol, a.interval,
                                                       month, base)
                        _http_download(cksurl, checksum_path)
                        _http_download(zurl, zip_path)
                    else:
                        missing += 1
                        misses.setdefault(symbol, []).append(f'{month}/{channel}')
                        continue
                expected = parse_checksum_file(checksum_path, zip_name)
                actual = sha256_file(zip_path)
                if actual != expected:
                    raise SystemExit(
                        f'SHA-256 mismatch for {zip_name}: expected {expected}, '
                        f'got {actual}')
                key = (symbol, channel, month)
                if key in recorded:
                    if recorded[key] != actual:
                        raise SystemExit(
                            f'refusing to ingest revised archive {zip_name}: '
                            f'recorded sha {recorded[key]}, current zip {actual}. '
                            'A corrected archive invalidates the existing tape '
                            '— rebuild it in a fresh out dir.')
                    skipped += 1
                    continue
                rows = build_tape_from_zip(zip_path, symbol, a.interval,
                                           DEFAULT_LATENCY_NS, channel)
                appended = 0
                for row in rows:
                    if log.append(dict(row)):
                        appended += 1
                recorded[key] = actual
                done += 1
                if (done + skipped + missing) % 25 == 0:
                    used = dir_bytes(out)
                    print(f'  {done + skipped + missing}/{total}  ok={done} '
                          f'skip={skipped} miss={missing}  '
                          f'{used / 1024 ** 3:.2f} GB', flush=True)
                    if used > budget:
                        print(f'STOP: {used / 1024 ** 3:.2f} GB exceeds the '
                              f'{a.budget_gb} GB budget', file=sys.stderr)
                        return 3

    # Provenance written ONCE, atomically (temp + os.replace), covering every
    # archive recorded in THIS run (the full on-disk set when source.json was
    # missing/corrupt, the recorded set plus any newly ingested otherwise).
    stored = log.read()
    meta = {
        'symbol': symbols[0] if len(symbols) == 1 else '',
        'symbols': sorted({s for (s, _c, _m) in recorded}),
        'interval': a.interval,
        'archives': sorted(
            ({'symbol': s, 'channel': c, 'month': m, 'zip_sha256': h}
             for (s, c, m), h in recorded.items()),
            key=lambda x: (x['symbol'], x['month'], x['channel'])),
        'row_count': len(stored),
        'tape_hash': sha1_hex(stored),
        'schema_version': SCHEMA_VERSION,
    }
    tmp = out / 'source.json.tmp'
    tmp.write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n',
                   encoding='utf-8')
    os.replace(tmp, out / 'source.json')

    used = dir_bytes(out)
    print(f'\narchives ok={done} skipped={skipped} missing={missing}; '
          f'{used / 1024 ** 3:.2f} GB')
    # A missing archive is normal (a symbol listed after `start` has no earlier
    # months) but it must be VISIBLE: silently short coverage for one symbol is
    # the same failure mode as a silently short history window.
    for sym, gaps in sorted(misses.items()):
        print(f'  {sym}: {len(gaps)} missing ({gaps[0]} .. {gaps[-1]})')
    print('\nnext: --sort then --audit via tools/vision_backfill.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
