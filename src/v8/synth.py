"""Deterministic synthetic tape generator for the vertical slice.

Clearly synthetic: proves the contracts run end-to-end; proves nothing about
economics (V8_CONSTITUTION rule 10, OPEN_DECISIONS O-001).
"""
from __future__ import annotations

import random

from .schema import TapeRow

FIXED_EPOCH_NS = 1_750_000_000_000_000_000
HOUR_NS = 3_600_000_000_000


def make_synthetic_tape(seed: int = 7, n_bars: int = 120, symbol: str = 'SOLUSDT',
                        base: float = 76.0) -> list[TapeRow]:
    rng = random.Random(seed)
    price = base
    rows: list[TapeRow] = []
    for i in range(n_bars):
        price *= 1 + rng.gauss(0.0002, 0.012)
        o = price / (1 + rng.uniform(-0.004, 0.004))
        c = price * (1 + rng.uniform(-0.004, 0.004))
        h = max(o, c) * (1 + rng.uniform(0, 0.006))
        l = min(o, c) * (1 - rng.uniform(0, 0.006))
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
