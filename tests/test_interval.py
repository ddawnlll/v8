"""Interval aggregation invariants (D-053).

These are properties, not examples: each one is a rule that must hold for every
input, because each protects a specific way an aggregate can silently become
invalid evidence (wrong bucket boundary, lookahead availability, or a bar built
from an incomplete window).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from v8.interval import (DAY_NS, HOUR_NS, INTERVAL_NS, IntervalError,
                         aggregate, bars_per, bucket_start_ns, is_derivable)
from v8.schema import TapeRow

LATENCY_NS = 1_000_000_000


def _bar(i: int, o: float, h: float, l: float, c: float, vol: float = 1.0,
         *, sym: str = 'BTCUSDT', closed: bool = True,
         start_ns: int = 0) -> TapeRow:
    """One closed 1h kline whose close time is the END of hour `i`."""
    close_time = start_ns + (i + 1) * HOUR_NS - 1
    return TapeRow(
        source='binance-um', channel='kline', instrument=sym,
        event_time=close_time, available_time=close_time + LATENCY_NS,
        ingested_time=close_time + LATENCY_NS, venue_sequence=i + 1,
        event_id=f'{sym}:{i + 1}',
        payload={'open': o, 'high': h, 'low': l, 'close': c,
                 'volume': vol, 'closed': closed})


def _ramp(n: int, **kw) -> list[TapeRow]:
    return [_bar(i, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, **kw)
            for i in range(n)]


# --- derivability ----------------------------------------------------------


def test_aggregation_is_up_only_and_exact():
    assert is_derivable('1h', '4h')
    assert is_derivable('1h', '1d')
    assert is_derivable('1h', '1h')          # identity
    assert is_derivable('1m', '15m')
    assert not is_derivable('1h', '15m')     # finer needs its own ingestion
    assert not is_derivable('4h', '6h')      # 6h is not a multiple of 4h
    with pytest.raises(IntervalError, match='not an integer multiple'):
        bars_per('1h', '15m')
    for bad in ('7h', '', '1w'):
        with pytest.raises(IntervalError, match='unknown'):
            is_derivable('1h', bad)


def test_bars_per_matches_the_interval_table():
    for target, width in INTERVAL_NS.items():
        if is_derivable('1m', target):
            assert bars_per('1m', target) * INTERVAL_NS['1m'] == width


# --- bucket boundaries -----------------------------------------------------


def test_buckets_are_anchored_to_the_utc_epoch_not_the_tape():
    """The same calendar instant must land in the same bucket regardless of
    where the tape starts. A tape-relative anchor would make the dev window and
    the frozen holdout disagree about what a 4h bar is."""
    instant = 37 * DAY_NS + 9 * HOUR_NS       # arbitrary 09:00-ish UTC moment
    b = bucket_start_ns(instant, '4h')
    assert (b % INTERVAL_NS['4h']) == 0       # lands on a real 4h boundary
    # Aggregating the same bars out of two differently-offset tapes yields the
    # same bucket starts.
    early = aggregate(_ramp(24, start_ns=0), '1h', '4h')
    late = aggregate(_ramp(24, start_ns=7 * DAY_NS), '1h', '4h')
    assert [r.event_id.split(':')[-1] for r in early] != []
    for r in early + late:
        assert int(r.event_id.split(':')[-1]) % INTERVAL_NS['4h'] == 0


def test_bar_closing_exactly_on_a_boundary_belongs_to_the_bucket_it_ends():
    """`event_time` is a CLOSE time, so a bar closing at 04:00:00 completes the
    00:00-04:00 bucket rather than opening the next one."""
    assert bucket_start_ns(4 * HOUR_NS, '4h') == 0
    assert bucket_start_ns(4 * HOUR_NS + 1, '4h') == 4 * HOUR_NS


# --- point-in-time availability -------------------------------------------


def test_aggregate_availability_is_its_last_constituent():
    """A 4h bar does not exist as evidence before its final hour is available."""
    rows = _ramp(8)
    out = aggregate(rows, '1h', '4h')
    assert len(out) == 2
    assert out[0].available_time == rows[3].available_time
    assert out[1].available_time == rows[7].available_time
    for agg in out:
        assert agg.available_time >= agg.event_time


def test_partial_trailing_bucket_is_never_emitted():
    """The last bucket of a tape is usually incomplete, and an incomplete
    bucket's high/low/close are still moving."""
    assert len(aggregate(_ramp(4), '1h', '4h')) == 1
    for n in (5, 6, 7):
        assert len(aggregate(_ramp(n), '1h', '4h')) == 1   # the partial is dropped
    assert aggregate(_ramp(3), '1h', '4h') == []


def test_bucket_with_a_data_gap_is_dropped():
    """A bucket built over missing base bars would understate its own range, so
    an under-full bucket is not a bar at all."""
    rows = [b for i, b in enumerate(_ramp(8)) if i != 2]     # hole in bucket 0
    out = aggregate(rows, '1h', '4h')
    assert len(out) == 1
    assert out[0].available_time == rows[-1].available_time  # only bucket 1 survives


def test_open_base_bars_never_enter_an_aggregate():
    rows = _ramp(3) + [_bar(3, 103.0, 104.0, 102.0, 103.5, closed=False)]
    assert aggregate(rows, '1h', '4h') == []     # bucket 0 is short a closed bar


# --- OHLCV correctness -----------------------------------------------------


def test_ohlcv_is_first_max_min_last_sum():
    rows = [_bar(0, 10.0, 15.0, 9.0, 12.0, vol=2.0),
            _bar(1, 12.0, 20.0, 11.0, 18.0, vol=3.0),
            _bar(2, 18.0, 19.0, 4.0, 6.0, vol=5.0),
            _bar(3, 6.0, 8.0, 5.0, 7.0, vol=7.0)]
    (agg,) = aggregate(rows, '1h', '4h')
    assert agg.payload['open'] == 10.0        # first
    assert agg.payload['high'] == 20.0        # max
    assert agg.payload['low'] == 4.0          # min
    assert agg.payload['close'] == 7.0        # last
    assert agg.payload['volume'] == 17.0      # sum
    assert agg.payload['closed'] is True
    assert agg.payload['interval'] == '4h'
    assert agg.payload['base_bars'] == 4


def test_aggregate_range_contains_every_constituent_range():
    """Property over the whole tape: an aggregate can never be narrower than
    the bars it is made of."""
    rows = _ramp(96)
    for target in ('2h', '4h', '12h', '1d'):
        n = bars_per('1h', target)
        for k, agg in enumerate(aggregate(rows, '1h', target)):
            members = rows[k * n:(k + 1) * n]
            assert agg.payload['high'] == max(m.payload['high'] for m in members)
            assert agg.payload['low'] == min(m.payload['low'] for m in members)
            assert agg.payload['open'] == members[0].payload['open']
            assert agg.payload['close'] == members[-1].payload['close']


# --- shape -----------------------------------------------------------------


def test_identity_aggregation_returns_closed_base_bars():
    rows = _ramp(5) + [_bar(5, 1.0, 1.0, 1.0, 1.0, closed=False)]
    out = aggregate(rows, '1h', '1h')
    assert len(out) == 5
    assert all(r.payload['closed'] is True for r in out)


def test_output_is_available_time_sorted_across_instruments():
    """`build_state` fails closed on unsorted input, so the aggregator must not
    hand it interleaved instruments out of order."""
    rows = _ramp(8) + _ramp(8, sym='ETHUSDT')
    out = aggregate(rows, '1h', '4h')
    assert len(out) == 4
    assert [r.available_time for r in out] == sorted(r.available_time for r in out)


def test_non_kline_channels_are_ignored():
    funding = TapeRow(source='binance-um', channel='funding',
                      instrument='BTCUSDT', event_time=HOUR_NS,
                      available_time=HOUR_NS, ingested_time=HOUR_NS,
                      venue_sequence=1, event_id='f:1',
                      payload={'funding_rate': 0.0001})
    out = aggregate(_ramp(4) + [funding], '1h', '4h')
    assert len(out) == 1
    assert all(r.channel == 'kline' for r in out)
