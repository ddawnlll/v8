"""Deterministic synthetic tape generator for the vertical slice.

Clearly synthetic: proves the contracts run end-to-end; proves nothing about
economics (V8_CONSTITUTION rule 10, OPEN_DECISIONS O-001).

Issue #72: the LEGACY default tape is also unusable for MECHANICAL diagnostics
— each bar's `open` is generated independently of the previous close, so the
tape fabricates bar-to-bar gaps (TR > (H-L) on ~73% of bars, where the real
continuously-traded BTCUSDT 1h tape shows ~0.6%) and reports a volatility /
stop-slippage / gap regime that does not exist in real perp data. Use
`continuous=True` for any diagnostic that touches gaps, stops or excursions
(and prefer the real tape for anything economic, per the audit convention); the
legacy default is kept byte-identical for the pinned golden/contract tests and
flipping it is a register decision (D-064, CHANGELOG 2026-08-07).
"""
from __future__ import annotations

import random

from .schema import TapeRow

FIXED_EPOCH_NS = 1_750_000_000_000_000_000
HOUR_NS = 3_600_000_000_000


def make_synthetic_tape(seed: int = 7, n_bars: int = 120, symbol: str = 'SOLUSDT',
                        base: float = 76.0, continuous: bool = False) -> list[TapeRow]:
    rng = random.Random(seed)
    price = base
    prev_close = base
    rows: list[TapeRow] = []
    for i in range(n_bars):
        price *= 1 + rng.gauss(0.0002, 0.012)
        if continuous:
            # Issue #72: a continuously-traded perp does not gap bar to bar —
            # the open is the prior close plus a small intra-interval move, so
            # the tape does not fabricate TR > (H-L) gaps that would mislead
            # mechanical diagnostics. The walk's σ=1.2% per bar is the
            # interval move; the open sits within ±0.1% of the prior close.
            o = prev_close * (1 + rng.uniform(-0.001, 0.001))
        else:
            o = price / (1 + rng.uniform(-0.004, 0.004))
        c = price * (1 + rng.uniform(-0.004, 0.004))
        h = max(o, c) * (1 + rng.uniform(0, 0.006))
        l = min(o, c) * (1 - rng.uniform(0, 0.006))
        prev_close = c
        open_time = FIXED_EPOCH_NS + i * HOUR_NS
        close_time = open_time + HOUR_NS - 1_000_000
        available = close_time + 1_000_000_000  # 1s configured feed latency
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument=symbol,
            event_time=close_time, available_time=available,
            ingested_time=available + rng.randint(0, 2_000_000),
            venue_sequence=i + 1, event_id=f'{symbol}:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': rng.uniform(1.0, 5.0), 'closed': True}))
    return rows
