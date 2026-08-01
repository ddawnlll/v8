"""Feature extraction authority (ROADMAP Phase 6).

Pure: no I/O, no network, no wall-clock. Computes causal feature vectors
from bar data at decision timestamps. Features are directional: momentum
returns are sign-flipped for SHORT events so the model can learn alignment
between event direction and recent trend.

Contract locked in specs/feature_candidate_v0.json — names, order, lookbacks.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .events import CandidateEvent
from .indicators import compute_atr
from .market import Bar

# ═══════════════════════════════════════════════════════════════════════════════
# feature contract
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_NAMES = (
    "return_5m",
    "return_15m",
    "return_1h",
    "atr_pct",
)

FEATURE_DIM = len(FEATURE_NAMES)
ATR_PERIOD = 14


# ═══════════════════════════════════════════════════════════════════════════════
# raw feature precomputation — O(n) one-pass per symbol
# ═══════════════════════════════════════════════════════════════════════════════

def precompute_features(
    bars: list[Bar],
    decision_tss: Sequence[int],
) -> dict[int, np.ndarray]:
    """Precompute causal raw feature vectors with batched timestamp lookup."""
    if not bars:
        raise ValueError("bars must not be empty")
    decisions = np.asarray(decision_tss, dtype=np.int64)
    if decisions.size == 0:
        return {}

    n = len(bars)
    closes = np.fromiter((b.close for b in bars), dtype=np.float64, count=n)
    highs = np.fromiter((b.high for b in bars), dtype=np.float64, count=n)
    lows = np.fromiter((b.low for b in bars), dtype=np.float64, count=n)
    bar_ts = np.fromiter((b.open_ts for b in bars), dtype=np.int64, count=n)
    ordered = not (n >= 2 and np.any(bar_ts[1:] <= bar_ts[:-1]))

    atr_arr = np.asarray(
        compute_atr(highs, lows, closes, period=ATR_PERIOD),
        dtype=np.float64,
    )
    requested_bar_ts = decisions - 300_000
    if ordered:
        indices = np.searchsorted(bar_ts, requested_bar_ts, side="left")
        in_range = indices < n
        exact = np.zeros(len(indices), dtype=np.bool_)
        exact[in_range] = bar_ts[indices[in_range]] == requested_bar_ts[in_range]
    else:
        # Compatibility path for callers that append overlapping fixture bars:
        # the historical implementation used a dict and therefore selected
        # the last duplicate timestamp.
        ts_to_idx = {int(timestamp): index for index, timestamp in enumerate(bar_ts)}
        indices = np.fromiter(
            (ts_to_idx.get(int(timestamp), -1) for timestamp in requested_bar_ts),
            dtype=np.int64,
            count=len(requested_bar_ts),
        )
        exact = indices >= 0
    if not np.all(exact):
        bad = int(np.flatnonzero(~exact)[0])
        raise KeyError(
            f"decision_ts={int(decisions[bad])}: bar at "
            f"{int(requested_bar_ts[bad])} not found in bars"
        )
    if np.any(indices < ATR_PERIOD):
        bad = int(np.flatnonzero(indices < ATR_PERIOD)[0])
        raise ValueError(
            f"decision_ts={int(decisions[bad])}: insufficient history "
            f"(idx={int(indices[bad])}, need >={ATR_PERIOD})"
        )

    references = np.column_stack((indices - 1, indices - 3, indices - 12))
    reference_closes = closes[references]
    zero_positions = np.argwhere(reference_closes == 0.0)
    if zero_positions.size:
        row, column = map(int, zero_positions[0])
        lookback = (1, 3, 12)[column]
        raise ValueError(
            f"decision_ts={int(decisions[row])}: zero close at lookback={lookback}"
        )
    current = closes[indices]
    returns = (current[:, None] - reference_closes) / reference_closes
    atr_values = atr_arr[indices]
    invalid_atr = (~np.isfinite(atr_values)) | (atr_values <= 0.0)
    if np.any(invalid_atr):
        bad = int(np.flatnonzero(invalid_atr)[0])
        raise ValueError(
            f"decision_ts={int(decisions[bad])}: non-finite or non-positive "
            f"ATR={float(atr_values[bad])}"
        )
    atr_pct = atr_values / current
    matrix = np.column_stack((returns, atr_pct))
    invalid = ~np.all(np.isfinite(matrix), axis=1)
    if np.any(invalid):
        bad = int(np.flatnonzero(invalid)[0])
        raise ValueError(
            f"decision_ts={int(decisions[bad])}: non-finite feature values"
        )
    return {
        int(timestamp): matrix[index].copy()
        for index, timestamp in enumerate(decisions)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# directional event features
# ═══════════════════════════════════════════════════════════════════════════════

def build_event_features(
    events: Sequence[CandidateEvent],
    bars_by_symbol: dict[str, list[Bar]],
) -> dict[str, np.ndarray]:
    """Build directional feature vectors for candidate events.

    Returns ``{event_id: feature_vector}``. Momentum returns are multiplied
    by ``side_sign`` (+1 for LONG, -1 for SHORT) so the model can learn
    directional alignment. ATR is unsigned (always positive).

    Same-timestamp LONG and SHORT events receive mirrored return features.
    """
    # Collect unique (symbol, decision_ts) pairs
    symbol_tss: dict[str, set[int]] = {}
    for e in events:
        symbol_tss.setdefault(e.symbol, set()).add(e.decision_ts)

    # Precompute raw features per symbol
    raw_features: dict[str, dict[int, np.ndarray]] = {}
    for sym, tss in symbol_tss.items():
        bars = bars_by_symbol.get(sym)
        if bars is None:
            raise KeyError(f"no bars for symbol {sym}")
        raw_features[sym] = precompute_features(bars, sorted(tss))

    # Apply directional mirror
    result: dict[str, np.ndarray] = {}
    for e in events:
        raw = raw_features[e.symbol][e.decision_ts].copy()
        side_sign = 1.0 if e.side == "LONG" else -1.0
        # Only momentum features are directional; ATR stays unsigned
        raw[0] *= side_sign  # return_5m
        raw[1] *= side_sign  # return_15m
        raw[2] *= side_sign  # return_1h
        # raw[3] is atr_pct — unsigned, stays as-is
        result[e.event_id] = raw

    return result
