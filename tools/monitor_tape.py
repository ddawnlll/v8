"""Data-quality monitoring for the JSONL PIT tape (OPERATIONS_SPEC 2-3, 5).

- Schema validation against the FEED_INGESTION_SPEC section 2 row contract
  (three clocks + venue identity present and correctly typed; kline rows are
  closed with numeric OHLC).
- Integrity audit: payload hashes, monotonicity, venue-sequence gaps,
  row counts vs source checksums — reused from tools/vision_backfill.py
  (audit_tape); do not fork it.
- Staleness alerting: age of the newest bar's event_time against a budget,
  with an injectable reference time (`--now`; tests never depend on the wall
  clock).
- Structured JSON output carrying `experiment_id` (OPERATIONS_SPEC section 3).
- Fail closed (OPERATIONS_SPEC section 5): any violation exits non-zero.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'src'))
sys.path.insert(0, str(_ROOT))                      # `tools.` package for CLI runs

from tools.vision_backfill import audit_tape, TapeAuditError  # noqa: E402

# FEED_INGESTION_SPEC section 2: the three clocks and the venue identity are
# mandatory on every row; a missing or wrong-typed field is a schema breach.
REQUIRED_FIELDS = ('source', 'channel', 'instrument', 'event_time',
                   'available_time', 'ingested_time', 'venue_sequence',
                   'event_id', 'payload')
INT_FIELDS = ('event_time', 'available_time', 'ingested_time', 'venue_sequence')
OHLC_FIELDS = ('open', 'high', 'low', 'close')


def read_rows(tape: Path) -> list[dict]:
    if not tape.exists():
        raise FileNotFoundError(f'tape not found: {tape}')
    return [json.loads(line) for line in
            tape.read_text(encoding='utf-8').splitlines() if line.strip()]


def validate_schema(rows: list[dict]) -> list[str]:
    """Schema contract per ingest (OPERATIONS_SPEC section 2). Returns the
    list of problems; empty means the schema holds."""
    problems: list[str] = []
    for i, r in enumerate(rows):
        if 'channel' not in r:
            continue                        # non-tape rows are not monitored here
        for f in REQUIRED_FIELDS:
            if f not in r or r[f] is None:
                problems.append(f'row {i}: missing or null {f}')
        for f in INT_FIELDS:
            if f in r and r[f] is not None and not isinstance(r[f], int):
                problems.append(f'row {i}: {f} is {type(r[f]).__name__}, expected int')
        for f in ('source', 'channel', 'instrument', 'event_id'):
            if f in r and not isinstance(r.get(f), str):
                problems.append(f'row {i}: {f} is {type(r.get(f)).__name__}, expected str')
        payload = r.get('payload')
        if not isinstance(payload, dict):
            problems.append(f'row {i}: payload is not a dict')
            continue
        if r.get('channel') == 'kline':
            if payload.get('closed') is not True:
                problems.append(f'row {i}: kline payload.closed is not True '
                                '(open klines must never reach the tape)')
            for f in OHLC_FIELDS:
                if not isinstance(payload.get(f), (int, float)):
                    problems.append(f'row {i}: payload.{f} missing or not numeric')
    return problems


def staleness_report(rows: list[dict], now_ns: int, budget_ns: int,
                     experiment_id: str = '') -> dict:
    """Age of the newest bar vs the budget; alert when it exceeds it."""
    times = [r['event_time'] for r in rows if isinstance(r.get('event_time'), int)]
    if not times:
        return {'alert': True, 'detail': 'no bar rows on tape', 'rows': len(rows)}
    newest = max(times)
    age_ns = now_ns - newest
    return {'alert': age_ns > budget_ns, 'newest_event_time': newest,
            'age_ns': age_ns, 'budget_ns': budget_ns,
            'experiment_id': experiment_id}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tape', type=Path, required=True,
                    help='tape.jsonl (or the out dir containing tape.jsonl)')
    ap.add_argument('--experiment-id', default='')
    ap.add_argument('--schema', action='store_true',
                    help='run schema + integrity audit checks')
    ap.add_argument('--staleness', action='store_true',
                    help='alert if the newest bar is older than the budget')
    ap.add_argument('--now', type=int, default=None,
                    help='reference time in ns (default: wall clock; '
                         'injectable so tests never touch the clock)')
    ap.add_argument('--budget-ns', type=int,
                    default=3 * 24 * 3_600_000_000_000,      # 72h default
                    help='staleness budget in ns')
    args = ap.parse_args(argv)

    tape = args.tape if args.tape.suffix == '.jsonl' else args.tape / 'tape.jsonl'
    rows = read_rows(tape)
    report: dict = {'tape': str(tape), 'experiment_id': args.experiment_id,
                    'rows': len(rows), 'violations': []}

    if args.schema:
        report['schema_problems'] = validate_schema(rows)
        report['violations'].extend(report['schema_problems'])
        try:
            report['audit'] = audit_tape(tape.parent)
        except TapeAuditError as exc:
            report['audit'] = {'violation': str(exc)}
            report['violations'].append(str(exc))

    if args.staleness:
        now = args.now if args.now is not None else \
            time.time_ns()                                    # ops tool, not src/v8/
        st = staleness_report(rows, now, args.budget_ns, args.experiment_id)
        report['staleness'] = st
        if st['alert']:
            report['violations'].append(
                f'staleness: newest bar age {st["age_ns"]}ns > budget {st["budget_ns"]}ns')

    report['verdict'] = 'OK' if not report['violations'] else 'VIOLATION'
    print(json.dumps(report, sort_keys=True))
    return 0 if report['verdict'] == 'OK' else 1


if __name__ == '__main__':
    raise SystemExit(main())
