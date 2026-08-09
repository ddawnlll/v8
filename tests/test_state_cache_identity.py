"""Bit-identity: the cached (precomputed-series) build_state path must produce
byte-identical MarketStates to the uncached path on every decision clock.

The fast path hoists per-state series recomputation into once-per-symbol arrays
(marketstate.build_bar_series). Any divergence — a value, a calc clock, an
input_lineage_hash, a provenance field, a state_id — is a silent semantic break
that the golden backtest would catch only by accident. This test pins the
equivalence on a synthetic tape (every bar, including the full warmup ladder)
and on the real dev tape (sampled bars), so a regression in the index mapping
or the running lineage digests fails here, not in an experiment.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v8.marketstate import (BarSeries, MarketState, build_bar_series, build_state,
                            build_multi_state)
from v8.schema import TapeRow
from v8.store import AppendOnlyLog
from v8.synth import make_synthetic_tape

def _universe(rows: list[TapeRow]) -> tuple[str, ...]:
    """The tape's own kline instruments (synthetic tapes use SOLUSDT)."""
    return tuple(sorted({r.instrument for r in rows if r.channel == 'kline'}))


def _rows_for(rows: list[TapeRow], as_of: int) -> list[TapeRow]:
    """The available-sorted prefix the uncached path expects for a clock."""
    return [r for r in rows if r.available_time <= as_of]


def _series_for(rows: list[TapeRow]) -> dict[str, BarSeries]:
    pit = sorted(rows, key=lambda r: r.available_time)
    series: dict[str, BarSeries] = {}
    syms = {r.instrument for r in rows if r.channel == 'kline'}
    for sym in syms:
        kline = [r for r in pit if r.instrument == sym and r.channel == 'kline']
        closed = [b for b in kline if b.payload.get('closed') is True]
        if closed:
            series[sym] = build_bar_series(
                closed, kline,
                [r for r in pit if r.instrument == sym and r.channel == 'funding'],
                [r for r in pit if r.instrument == sym and r.channel == 'open_interest'])
    return series


def _assert_identical(a: MarketState, b: MarketState, ctx: str) -> None:
    assert a.state_id == b.state_id, f'{ctx}: state_id'
    assert a.lineage_hash == b.lineage_hash, f'{ctx}: lineage_hash'
    assert a.quality == b.quality, f'{ctx}: quality'
    assert a.as_of == b.as_of, f'{ctx}: as_of'
    assert a.universe == b.universe, f'{ctx}: universe'
    assert a.provenance == b.provenance, f'{ctx}: provenance'
    assert set(a.features) == set(b.features), (
        f'{ctx}: feature keys differ '
        f'{sorted(set(a.features) ^ set(b.features))}')
    for key in a.features:
        fa, fb = a.features[key], b.features[key]
        for attr in ('value', 'dtype', 'feature_version', 'max_input_available_time',
                     'quality', 'null_reason', 'group', 'input_lineage_hash',
                     'calculation_time'):
            va, vb = getattr(fa, attr), getattr(fb, attr)
            assert va == vb, f'{ctx}: {key}.{attr}: {va!r} != {vb!r}'


def _check_tape(rows: list[TapeRow], step: int = 1) -> int:
    pit = sorted(rows, key=lambda r: r.available_time)
    universe = _universe(pit)
    series = _series_for(pit)
    bars = [r for r in pit if r.channel == 'kline'
            and r.payload.get('closed') is True]
    n = 0
    for j, bar in enumerate(bars):
        if j % step:
            continue
        as_of = bar.available_time
        a = build_state(_rows_for(pit, as_of), as_of, universe)
        b = build_state(_rows_for(pit, as_of), as_of, universe, series=series)
        _assert_identical(a, b, f'bar {j} as_of {as_of}')
        n += 1
    return n


def test_synthetic_every_bar():
    rows = make_synthetic_tape(seed=7, n_bars=160)
    n = _check_tape(rows, step=1)
    assert n == 160


def test_real_tape_sampled():
    tape = Path(__file__).resolve().parents[1] / 'research/tape/btcusdt-1h-12m/tape.jsonl'
    if not tape.exists():
        import pytest
        pytest.skip('dev tape not present')
    rows = AppendOnlyLog(tape).replay_tape()
    n = _check_tape(rows, step=25)
    assert n >= 300


def test_multi_state_identity():
    rows = make_synthetic_tape(seed=11, n_bars=200)
    pit = sorted(rows, key=lambda r: r.available_time)
    universe = _universe(pit)
    series = _series_for(pit)
    bars = [r for r in pit if r.channel == 'kline'
            and r.payload.get('closed') is True]
    for j, bar in enumerate(bars[::10]):
        as_of = bar.available_time
        prefix = _rows_for(pit, as_of)
        a = build_multi_state(prefix, as_of, universe, base_interval='1h')
        b = build_multi_state(prefix, as_of, universe, base_interval='1h',
                              series={'1h': series})
        _assert_identical(a, b, f'multi bar {j} as_of {as_of}')


def test_non_monotonic_event_time_identity():
    """A PIT tape with heterogeneous latencies has event_time non-monotonic in
    available order; the cached vwap falls back to the exact full-filter
    `_vwap`. Both paths must still agree on every bar."""
    from dataclasses import replace
    rows = make_synthetic_tape(seed=7, n_bars=160)
    pit = sorted(rows, key=lambda r: r.available_time)
    a, b = pit[5], pit[6]
    pit[5] = replace(a, event_time=b.event_time)
    pit[6] = replace(b, event_time=a.event_time)
    n = _check_tape(pit, step=1)
    assert n == 160


def test_closed_digests_same_t_is_idempotent():
    """The running lineage digest must return the SAME (D_{t-1}, D_t) on a
    repeat call for the same t (a warm re-build at the same clock must not
    silently rewrite prior_high/prior_low lineage to D_t)."""
    from v8.schema import sha1_hex
    rows = make_synthetic_tape(seed=7, n_bars=160)
    pit = sorted(rows, key=lambda r: r.available_time)
    s = _series_for(pit)[_universe(pit)[0]]
    p1, d1 = s.closed_digests(10)
    p2, d2 = s.closed_digests(10)
    assert (p1, d1) == (p2, d2)
    assert p1 != d1
    expected = sha1_hex([(b.event_id, b.payload.get('payload_hash', b.payload))
                         for b in s.closed[:9]])
    assert p1 == expected
