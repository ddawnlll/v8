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

Rows are appended through the store's (source, event_id) inbox, and event_id
carries the symbol and interval, so runs are idempotent and resumable: a second
pass over the same out dir adds zero rows.

Usage:
  python tools/build_multi_tape.py --out research/tape/multi-1h-4y \\
      --symbols BTCUSDT,ETHUSDT --start 2022-07 --end 2026-07
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKFILL = ROOT / 'tools' / 'vision_backfill.py'

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


def build_one(symbol: str, month: str, channel: str, interval: str,
              out: Path) -> tuple[bool, str]:
    cmd = [sys.executable, str(BACKFILL), '--symbol', symbol,
           '--interval', interval, '--month', month, '--channel', channel,
           '--out', str(out), '--download']
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout).strip().splitlines()
        return False, (tail[-1] if tail else f'exit {p.returncode}')
    return True, (p.stdout.strip().splitlines() or [''])[-1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--symbols', default=','.join(DEFAULT_SYMBOLS))
    ap.add_argument('--start', default='2022-07', help='YYYY-MM inclusive')
    ap.add_argument('--end', default='2026-07', help='YYYY-MM exclusive')
    ap.add_argument('--interval', default='1h')
    ap.add_argument('--channels', default='kline,funding')
    ap.add_argument('--budget-gb', type=float, default=DEFAULT_BUDGET_GB)
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

    total = len(symbols) * len(ms) * len(channels)
    print(f'{len(symbols)} symbols x {len(ms)} months x {len(channels)} '
          f'channels = {total} archives -> {out}', flush=True)

    done = failed = 0
    misses: dict[str, list[str]] = {}
    for symbol in symbols:
        for month in ms:
            for channel in channels:
                ok, msg = build_one(symbol, month, channel, a.interval, out)
                if ok:
                    done += 1
                else:
                    failed += 1
                    misses.setdefault(symbol, []).append(f'{month}/{channel}')
                if (done + failed) % 25 == 0:
                    used = dir_bytes(out)
                    print(f'  {done + failed}/{total}  ok={done} miss={failed}  '
                          f'{used / 1024 ** 3:.2f} GB', flush=True)
                    if used > budget:
                        print(f'STOP: {used / 1024 ** 3:.2f} GB exceeds the '
                              f'{a.budget_gb} GB budget', file=sys.stderr)
                        return 3

    used = dir_bytes(out)
    print(f'\narchives ok={done} missing={failed}; {used / 1024 ** 3:.2f} GB')
    # A missing archive is normal (a symbol listed after `start` has no earlier
    # months) but it must be VISIBLE: silently short coverage for one symbol is
    # the same failure mode as a silently short history window.
    for sym, gaps in sorted(misses.items()):
        print(f'  {sym}: {len(gaps)} missing ({gaps[0]} .. {gaps[-1]})')
    print('\nnext: --sort then --audit via tools/vision_backfill.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
