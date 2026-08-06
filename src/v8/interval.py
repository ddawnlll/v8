"""Base-interval kline aggregation into higher declared intervals (D-053).

An Expert declares the intervals it needs; the tape carries ONE base interval.
Every higher interval is an exact aggregation of the base — no new ingestion,
no interpolation. Derivation is up-only: a 1h tape yields 2h/4h/1d, never 15m.

Three invariants make an aggregate usable as point-in-time evidence, and all
three are load-bearing rather than stylistic:

- Buckets are anchored to a FIXED UTC epoch, never to the first row of the
  tape. A tape-relative anchor makes the same calendar hour fall in different
  buckets depending on where the window starts, so the dev window and the
  frozen holdout would disagree about what a "4h bar" is.
- The aggregate's `available_time` is the availability of its LAST constituent
  base bar. A 4h bar spanning 08:00-12:00 does not exist as evidence at 09:00;
  reading it there is lookahead wearing an aggregation costume.
- A partial trailing bucket is never emitted as closed. The final bucket of a
  tape is usually incomplete, and an incomplete bucket's high/low/close are
  still moving.
"""
from __future__ import annotations

from .schema import TapeRow

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS
HOUR_NS = 60 * MINUTE_NS
DAY_NS = 24 * HOUR_NS

# Declarable intervals and their length in nanoseconds. An interval is
# derivable from a base only when it is an exact integer multiple of it.
INTERVAL_NS: dict[str, int] = {
    '1m': MINUTE_NS, '3m': 3 * MINUTE_NS, '5m': 5 * MINUTE_NS,
    '15m': 15 * MINUTE_NS, '30m': 30 * MINUTE_NS,
    '1h': HOUR_NS, '2h': 2 * HOUR_NS, '4h': 4 * HOUR_NS,
    '6h': 6 * HOUR_NS, '8h': 8 * HOUR_NS, '12h': 12 * HOUR_NS,
    '1d': DAY_NS,
}

# The fixed bucket anchor: the UNIX epoch, which is a 00:00 UTC boundary. Every
# interval in the table divides a day evenly, so bucketing by absolute time
# modulo the interval length lands every bucket on a real calendar boundary.
EPOCH_NS = 0


class IntervalError(ValueError):
    """A declared interval cannot be served from the base interval."""


def is_derivable(base: str, target: str) -> bool:
    """True when `target` is an exact integer multiple of `base`. Equal
    intervals are derivable (the identity aggregation)."""
    if base not in INTERVAL_NS:
        raise IntervalError(f'unknown base interval {base!r}')
    if target not in INTERVAL_NS:
        raise IntervalError(f'unknown target interval {target!r}')
    return INTERVAL_NS[target] % INTERVAL_NS[base] == 0


def bars_per(base: str, target: str) -> int:
    """How many base bars make one `target` bar."""
    if not is_derivable(base, target):
        raise IntervalError(
            f'{target} is not an integer multiple of {base}; aggregation is '
            'up-only and exact — a finer interval needs its own ingestion')
    return INTERVAL_NS[target] // INTERVAL_NS[base]


def bucket_start_ns(event_time_ns: int, target: str) -> int:
    """The fixed-epoch bucket boundary `event_time_ns` belongs to.

    `event_time` on a kline is its CLOSE time, so a bar closing exactly on a
    boundary belongs to the bucket that ENDS there, not the one starting there
    — hence the 1ns pull-back before flooring.
    """
    width = INTERVAL_NS[target]
    return ((event_time_ns - EPOCH_NS - 1) // width) * width + EPOCH_NS


def aggregate(rows: list[TapeRow], base: str, target: str) -> list[TapeRow]:
    """Aggregate closed base klines into closed `target` klines.

    Only closed base bars participate: an open base bar's OHLC is still moving,
    so a bucket containing one cannot be closed either. Rows of other channels
    are ignored (funding/OI are not bar-shaped and are served at their own
    cadence). Output is sorted by `available_time`, the order `build_state`
    requires.
    """
    n = bars_per(base, target)
    if n == 1:
        return [r for r in rows
                if r.channel == 'kline' and r.payload.get('closed') is True]

    buckets: dict[tuple[str, int], list[TapeRow]] = {}
    for r in rows:
        if r.channel != 'kline' or r.payload.get('closed') is not True:
            continue
        key = (r.instrument, bucket_start_ns(r.event_time, target))
        buckets.setdefault(key, []).append(r)

    out: list[TapeRow] = []
    for (instrument, start), members in buckets.items():
        # A bucket short of its full complement is incomplete. This drops the
        # trailing partial bucket AND any bucket with a data gap — an aggregate
        # built over missing base bars would silently understate its own range.
        if len(members) != n:
            continue
        members.sort(key=lambda r: r.event_time)
        highs = [float(m.payload['high']) for m in members]
        lows = [float(m.payload['low']) for m in members]
        last = members[-1]
        out.append(TapeRow(
            source=last.source,
            channel='kline',
            instrument=instrument,
            # The aggregate closes when its last constituent closes, and
            # becomes available when that bar becomes available — never
            # earlier, which is what keeps it point-in-time honest.
            event_time=last.event_time,
            available_time=last.available_time,
            ingested_time=max(m.ingested_time for m in members),
            venue_sequence=last.venue_sequence,
            event_id=f'{instrument}:{target}:{start}',
            payload={
                'open': float(members[0].payload['open']),
                'high': max(highs),
                'low': min(lows),
                'close': float(last.payload['close']),
                'volume': sum(float(m.payload.get('volume', 0.0)) for m in members),
                'closed': True,
                'interval': target,
                'base_bars': n,
            }))
    out.sort(key=lambda r: (r.available_time, r.instrument))
    return out
