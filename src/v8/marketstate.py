"""MarketState builder with availability gating.

Builds an immutable state for decision clock D from tape rows whose
available_time <= D; a future row must fail, never silently pass
(MARKET_STATE_CONTRACT sections 1 and 6).

Feature groups FG-1..FG-7 (G-01..G-43, HAND_EXPERTS.md section 0):
  candle_shape, oscillator, volatility (extended), location (extended),
  participation (activated), session, positioning.
All formulas are stdlib-only, deterministic, and derived from the three
integer clocks on tape rows — none reads the wall clock (D-031).

Value semantics that matter (MARKET_STATE_CONTRACT section 4; orchestrator
directive on DEGRADED-vs-no-signal):
  * None is reserved for DATA ABSENCE: warmup (inputs not yet computable) or
    an absent channel. None auto-degrades the FEATURE with
    null_reason='NOT_YET_AVAILABLE' and degrades the STATE (the D-024
    data-integrity veto stays reachable).
  * A "no signal" condition (ATR below its 2-sigma band, a gap not present,
    no significant swing) is a NUMERIC VALUE, never None. Where the book's
    formula is inherently conditional (G-18 atr_filtered_2sigma) it is
    emitted as two always-numeric features: the value and a 0/1 "active" flag
    carrying the filter condition.
  * Price-level sentinels use 0.0 for "no significant level" (swing_high/low):
    every validated tape has strictly positive OHLC, so 0.0 is unambiguous.
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

from .schema import (TapeRow, MarketState, FeatureValue, sha1_hex, FEATURE_GROUPS,
                     FEATURE_TO_GROUP, FEATURE_GRAPH_VERSION)

# Builder code version bound into every state's provenance: a semantic change
# in build_state re-versions every state's provenance even when the emitted
# values round-trip (MARKET_STATE_CONTRACT 2 code_version).
_BUILDER_SRC_HASH = sha1_hex(Path(__file__).read_bytes())

HOUR_NS = 3_600_000_000_000
DAY_NS = 86_400_000_000_000

# D-026/O-020 `history` window. 32 was a global pin, and the 2026-08-06 expert
# inventory measured its cost: `ichimoku_cloud` needs 78 bars for the displaced
# cloud and declares 3 of 4 variants unevaluated, `breakout_retest` drops
# variant d, `donchian_breakout` falls back from a 55-bar to a 50-bar anchor
# scan, and `pattern_measuring_objective` cannot express its patterns at all.
# It is now the DEFAULT rather than the ceiling: an Expert declares the depth
# it needs (D-053) and the run serves max(declared), with each Expert's view
# truncated to its own declaration so a deeper neighbour cannot widen it.
HISTORY_DEPTH_DEFAULT = 32

# --- Declared, LOCKED constants (D-036 pattern: "declared, never fitted"). ---
# FG-3 (G-18): 2-sigma ATR filter band lookback.
ATR_FILTER_BAND_N = 20
# FG-3 (G-19): STARC multiple k (book k in {2, 3}).
STARC_K = 2.0
# FG-3 (G-20): ATR slope lookback for the trend phase.
ATR_SLOPE_N = 10
# FG-3 (G-28): ATR band-stop multiple k (book k in {1, 1.5, 2, 4}).
ATR_BAND_STOP_K = 2.0

# FG-4 (G-21): swing pivot flanks.
SWING_NS = (5, 10, 20)
# FG-4 (G-21, CRIT-1 / Ch27.2 p858-859): swing-significance range filter.
# A pivot bar is "significant" only when its range >= k * ATR (k LOCKED = 1.0).
SWING_SIGNIFICANCE_K = 1.0
# FG-4 (G-22/G-23): window lookbacks (Donchian channel, current bar excluded).
WINDOW_NS = (10, 20, 50)
# FG-4 (G-24): Fibonacci ratios (verbatim from the book).
FIB_RETRACEMENTS = (0.236, 0.382, 0.5, 0.618, 0.786)
FIB_EXTENSIONS = (1.0, 1.272, 1.618, 2.0, 2.618, 3.0, 3.618, 4.0, 4.236, 4.618)
# FG-4 (G-25): pivot-points day length on a 1h tape (session anchor 00:00 UTC).
BARS_PER_DAY = 24
# FG-4 (G-26): consolidation minimum duration and max relative width.
CONSOLIDATION_BARS = 20
CONSOLIDATION_WIDTH_MAX = 0.03
# FG-4 (G-27): gap-zone persistence horizon.
GAP_ZONE_BARS = 50

# FG-2 (G-13): momentum/ROC lookback.
MOM_N = 14
# FG-2 (G-15): rolling oscillator-percentile window.
OBOS_QUANTILE_WINDOW = 100

# FG-5 (G-30/G-31): volume z-score / min-proximity window (book: 100-day).
VOLUME_STAT_N = 100
# FG-5 (G-32): smoothed-volume MA lookback (declared fixed N; cycle tuning is
# a section-3 deferred decision).
VOLUME_SMA_N = 20
# FG-5 (G-35): CMF lookback (declared 20 pre-holdout).
CMF_N = 20
# FG-5 (G-37): bar-class percentile window.
BAR_CLASS_N = 100

# FG-6 (G-39): impulsive window 08:00-17:00 GMT (inclusive).
IMPULSIVE_START_HOUR = 8
IMPULSIVE_END_HOUR = 17


class FutureRowError(ValueError):
    pass


def validate_feature_groups(features: dict[str, FeatureValue]) -> None:
    """Every emitted feature carries a declared group; the group table's
    `requires` are consistent. Fails closed on an undeclared feature name or
    an undeclared required group (MARKET_STATE_CONTRACT section 2)."""
    for name, fv in features.items():
        bare = name.rsplit('.', 1)[-1]
        if fv.group not in FEATURE_GROUPS:
            raise ValueError(f'feature {name} has undeclared group {fv.group!r}')
        if bare in FEATURE_TO_GROUP and FEATURE_TO_GROUP[bare] != fv.group:
            raise ValueError(
                f'feature {name} tagged {fv.group!r}, expected {FEATURE_TO_GROUP[bare]!r}')
    for group, spec in FEATURE_GROUPS.items():
        for req in spec['requires']:
            if req not in FEATURE_GROUPS:
                raise ValueError(f'group {group} requires undeclared group {req!r}')


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sma(values: list[float], period: int) -> float:
    return _mean(values[-period:])


def _std_pop(values: list[float]) -> float:
    m = _mean(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def _typical(highs, lows, closes) -> list[float]:
    return [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]


def _percentile_rank(values: list[float], current: float) -> float:
    """Fraction of trailing values <= current, in [0, 1] (ties included)."""
    return sum(1.0 for v in values if v <= current) / len(values)


# --- FG-2 oscillator helpers (G-08..G-15) -----------------------------------

def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    if avg_gain == 0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _rsi_series(closes: list[float], period: int = 14) -> list[float]:
    """Wilder RSI over the full close series (G-08)."""
    if len(closes) < period + 1:
        return []
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out = [_rsi_value(avg_gain, avg_loss)]
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out.append(_rsi_value(avg_gain, avg_loss))
    return out


def _stoch(highs, lows, closes, period: int = 14) -> tuple[float, float]:
    """Fast stochastic: %K raw = (C-L14)/(H14-L14)*100; %D = SMA3(%K) (G-09).
    A flat 14-bar window has no range -> %K = 50 (neutral, never a zero)."""
    ks = []
    for i in range(len(closes) - 3, len(closes)):
        h14 = max(highs[i - period + 1:i + 1])
        l14 = min(lows[i - period + 1:i + 1])
        if h14 == l14:
            ks.append(50.0)
        else:
            ks.append((closes[i] - l14) / (h14 - l14) * 100.0)
    return ks[-1], sum(ks) / 3.0


def _stochrsi_from(rsis, period: int = 14) -> float:
    """StochRSI %K from an RSI series (G-10). Shared by the uncached path
    (`_stochrsi`) and the cached path (which feeds the precomputed RSI series),
    so both use one formula."""
    window = rsis[-period:]
    lo, hi = min(window), max(window)
    if hi == lo:
        return 0.5
    return (rsis[-1] - lo) / (hi - lo)


def _stochrsi(closes, period: int = 14) -> float:
    """StochRSI %K = (RSI - RSI_L14)/(RSI_H14 - RSI_L14) (G-10)."""
    return _stochrsi_from(_rsi_series(closes, period), period)


def _cci(highs, lows, closes, period: int = 20) -> float:
    """Commodity Channel Index: (TP - SMA(TP,20)) / (0.015 * mean_abs_dev) (G-11)."""
    tp = _typical(highs, lows, closes)
    sma = _sma(tp, period)
    mad = _mean([abs(t - sma) for t in tp[-period:]])
    if mad == 0:
        return 0.0
    return (tp[-1] - sma) / (0.015 * mad)


def _macd(closes, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD = EMA12 - EMA26; signal = EMA9(MACD); histogram = MACD - signal (G-12)."""
    macd = [f - s for f, s in zip(_ema(closes, fast), _ema(closes, slow))]
    sig = _ema(macd, signal)
    return macd[-1], sig[-1], macd[-1] - sig[-1]


def _dx_value(atr, pdi, ndi) -> float:
    """Directional index for a Wilder-smoothed (ATR, +DM, -DM) triple."""
    if atr <= 0:
        return 0.0
    pdi_p = 100.0 * pdi / atr
    ndi_p = 100.0 * ndi / atr
    if pdi_p + ndi_p == 0:
        return 0.0
    return 100.0 * abs(pdi_p - ndi_p) / (pdi_p + ndi_p)


def _adx(highs, lows, closes, period: int = 14) -> float:
    """Wilder DMI ADX (G-14): +DI/-DI from Wilder-smoothed TR/DM, ADX =
    Wilder average of DX over `period`."""
    n = len(closes)
    trs, pdms, ndms = [], [], []
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        pdms.append(up if (up > dn and up > 0) else 0.0)
        ndms.append(dn if (dn > up and dn > 0) else 0.0)
    atr_w = sum(trs[:period])
    pdi_w = sum(pdms[:period])
    ndi_w = sum(ndms[:period])

    dxs = [_dx_value(atr_w, pdi_w, ndi_w)]
    for i in range(period, len(trs)):
        atr_w = atr_w - atr_w / period + trs[i]
        pdi_w = pdi_w - pdi_w / period + pdms[i]
        ndi_w = ndi_w - ndi_w / period + ndms[i]
        dxs.append(_dx_value(atr_w, pdi_w, ndi_w))
    if len(dxs) < period:
        return 0.0
    adx = sum(dxs[:period]) / period
    for i in range(period, len(dxs)):
        adx = (adx * (period - 1) + dxs[i]) / period
    return adx


# --- FG-3 volatility helpers (G-16..G-20, G-28) ------------------------------

def _atr_series(highs, lows, period: int = 14) -> list[float]:
    """Simple-mean ATR over rolling `period`-bar windows (matches the existing
    `atr` feature formula exactly; G-17/G-18/G-19 build on the same series)."""
    out = []
    for i in range(period - 1, len(highs)):
        out.append(sum(h - l for h, l in zip(highs[i - period + 1:i + 1],
                                             lows[i - period + 1:i + 1])) / period)
    return out


# --- FG-4 location helpers (G-21..G-28) --------------------------------------

def _confirmed_swings(highs, lows, n: int):
    """Most recent confirmed strength-n swing high and low (G-21 pivot
    formula, no significance filter). Confirmed pivots are immutable once
    their n-bar flank is closed, so the most recent pair is persistent: once
    both a swing high and a swing low have EVER been confirmed, the pair never
    disappears for later states."""
    hi_piv, lo_piv = None, None
    for i in range(n, len(highs) - n):
        hi = highs[i]
        if hi > max(highs[i - n:i] + highs[i + 1:i + 1 + n]):
            hi_piv = (i, hi)
        lo = lows[i]
        if lo < min(lows[i - n:i] + lows[i + 1:i + 1 + n]):
            lo_piv = (i, lo)
    return hi_piv, lo_piv


def _significant_pivots(highs, lows, n: int, atr_now: float, k: float):
    """Confirmed strength-n pivot bars (G-21) that pass the CRIT-1 significance
    range filter: pivot bar range >= k*ATR (Ch27.2 p858-859; k LOCKED)."""
    hi_pivs, lo_pivs = [], []
    for i in range(n, len(highs) - n):
        hi = highs[i]
        if hi > max(highs[i - n:i] + highs[i + 1:i + 1 + n]) \
                and hi - lows[i] >= k * atr_now:
            hi_pivs.append((i, hi))
        lo = lows[i]
        if lo < min(lows[i - n:i] + lows[i + 1:i + 1 + n]) \
                and highs[i] - lo >= k * atr_now:
            lo_pivs.append((i, lo))
    return hi_pivs, lo_pivs


def _fib_levels(swing_high, swing_low):
    """Fibonacci levels anchored on the last impulse (the two most recent
    confirmed swings, G-24). The CRIT-1 significance filter applies to the
    G-21 swing_* features, not to the fib anchor. "Area of application"
    invariant (Ch10.11 p394): levels are valid only forward of the anchor bar
    — the anchor is always a confirmed past swing, so PIT holds by
    construction.

    Returns a self-describing tuple
    (anchor_price, direction, retracements, extensions) where direction is +1
    for an up-impulse (retracements below the anchor high) and -1 for a
    down-impulse (retracements above the anchor low); None when no anchor pair
    exists (pre-anchor data absence).

    Extension base is the impulse ORIGIN (the older extreme), not the END:
    the book's formula is "Upside extension = Trough + (Range x Ratio)" and
    "Downside extension = Peak - (Range x Ratio)" (Ch10.5.1 p404 / 10.5.2
    p405). Projecting from the END extreme puts every extension level one full
    impulse-range beyond the book's level for the same ratio label (a 1.618
    extension would sit at the book's 2.618)."""
    if swing_high is None or swing_low is None:
        return None
    i_h, h = swing_high
    i_l, l = swing_low
    # The impulse runs from the older extreme to the newer one; the anchor
    # extreme is the END of the impulse (the newer extreme, used for the
    # retracements), and the ORIGIN is the older extreme (the book's extension
    # base). rng = h - l is always positive (a swing high sits above a swing
    # low).
    if i_h > i_l:
        extreme, origin, rng, direction = h, l, h - l, 1.0   # up-impulse low->high
    else:
        extreme, origin, rng, direction = l, h, h - l, -1.0  # down-impulse high->low
    if rng <= 0:
        return None
    retr = tuple((r, extreme - direction * r * rng) for r in FIB_RETRACEMENTS)
    ext = tuple((r, origin + direction * r * rng) for r in FIB_EXTENSIONS)
    return (extreme, direction, retr, ext)


def _consolidation_range(highs, lows, closes, m: int = CONSOLIDATION_BARS,
                         width_max: float = CONSOLIDATION_WIDTH_MAX):
    """G-26: always-computable structured range state. Returns
    (range_high, range_low, width_ratio, is_active) where the bounds cover the
    m bars BEFORE the current bar and is_active=1 when the close is inside the
    range and the range is narrow (width <= width_max)."""
    h_ref = max(highs[-(m + 1):-1])
    l_ref = min(lows[-(m + 1):-1])
    width = h_ref - l_ref
    width_ratio = width / closes[-1] if closes[-1] else 0.0
    inside = 1.0 if l_ref <= closes[-1] <= h_ref else 0.0
    is_active = 1.0 if (inside and width_ratio <= width_max) else 0.0
    return (h_ref, l_ref, width_ratio, is_active)


def _gap_levels(opens, highs, lows, closes, n: int = GAP_ZONE_BARS):
    """G-27: unfilled gap zones from the last n bars, oldest first. Each zone
    is (top, bottom, gap_dir); a gap is filled when a later close enters the
    zone. An empty tuple is a valid value (no gaps / all filled) — never None."""
    start = max(1, len(opens) - n)
    zones = []
    for t in range(start, len(opens)):
        o = opens[t]
        ph, pl = highs[t - 1], lows[t - 1]
        if o > ph:
            top, bottom, d = o, ph, 1.0
        elif o < pl:
            top, bottom, d = pl, o, -1.0
        else:
            continue
        filled = any(bottom <= closes[j] <= top for j in range(t + 1, len(closes)))
        if not filled:
            zones.append((top, bottom, d))
    return tuple(zones)


# --- FG-5 participation helpers (G-29..G-37) ----------------------------------

def _obv(closes, volumes) -> float:
    """G-33: cumulative +vol on a rising close, -vol on a falling close."""
    total = 0.0
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            total += volumes[i]
        elif closes[i] < closes[i - 1]:
            total -= volumes[i]
    return total


def _adl(highs, lows, closes, volumes) -> float:
    """G-34: cumulative money flow; a flat bar (H==L) contributes zero flow."""
    total = 0.0
    for h, l, c, v in zip(highs, lows, closes, volumes):
        rng = h - l
        if rng > 0:
            total += ((c - l) - (h - c)) / rng * v
    return total


def _cmf(highs, lows, closes, volumes, period: int = CMF_N) -> float:
    """G-35: sum(MF)/sum(vol) over the window (Chaikin Money Flow)."""
    mf_sum = 0.0
    vol_sum = 0.0
    for h, l, c, v in zip(highs[-period:], lows[-period:], closes[-period:],
                          volumes[-period:]):
        rng = h - l
        if rng > 0:
            mf_sum += ((c - l) - (h - c)) / rng * v
        vol_sum += v
    if vol_sum == 0:
        return 0.0
    return mf_sum / vol_sum


def _vwap(closed):
    """G-36: session-anchored VWAP = sum(TP*vol)/sum(vol) since the last 00:00
    UTC boundary (declared session anchor for a 24/7 market). Returns
    (value, session_bars) so the caller can attach exact input lineage."""
    latest = closed[-1]
    anchor = latest.event_time - (latest.event_time % DAY_NS)
    session = [b for b in closed if b.event_time >= anchor]
    tp_vol = 0.0
    vol = 0.0
    for b in session:
        p = b.payload
        tp_vol += (float(p['high']) + float(p['low']) + float(p['close'])) / 3.0 \
            * float(p.get('volume', 0.0))
        vol += float(p.get('volume', 0.0))
    if vol == 0:
        return 0.0, session
    return tp_vol / vol, session


def _bar_class(opens, closes, highs, lows, volumes,
               n: int = BAR_CLASS_N, lookback: int = 5) -> float:
    """G-37: bar class from (range percentile, volume percentile) + short-term
    trend. 0=Low-Vol Rest, 1=High-Vol Reversal, 2=Low-Vol Reversal,
    3=High-Vol Continuation. High-Vol = range or volume at/above the 80th
    percentile; Reversal = the close opposes the prior short-term move."""
    range_pct = _percentile_rank([h - l for h, l in zip(highs[-n:], lows[-n:])],
                                 highs[-1] - lows[-1])
    vol_pct = _percentile_rank(volumes[-n:], volumes[-1])
    up_trend = closes[-1] > closes[-1 - lookback]
    reversal = (up_trend and closes[-1] < opens[-1]) or \
        (not up_trend and closes[-1] > opens[-1])
    high_vol = 1.0 if (vol_pct >= 0.8 or range_pct >= 0.8) else 0.0
    if high_vol:
        return 3.0 if not reversal else 1.0
    return 0.0 if not reversal else 2.0


# --- FG-6 session helpers (G-38..G-40) ---------------------------------------

def _hour_utc(event_time_ns: int) -> int:
    return (event_time_ns // HOUR_NS) % 24


def _bar_of_session(event_time_ns: int) -> int:
    """1-indexed bar ordinal within the UTC session (00:00 UTC anchor)."""
    return (event_time_ns % DAY_NS) // HOUR_NS + 1


def _day_index(event_time_ns: int) -> int:
    """UTC day ordinal (Market Profile bucketing index)."""
    return event_time_ns // DAY_NS


# --- Fast path: precomputed per-symbol series (O(N²) -> O(N × window)). ------
#
# build_state recomputes every series (EMA/ATR/RSI/ADX/pivots/... ) from scratch
# for each decision clock, so a backtest over N bars is O(N²). The cached path
# precomputes the same series ONCE per symbol over the full tape, and each state
# reads its values by index. Every series is a function of a prefix-computable
# recurrence or fixed window, so indexing the full-series array at position
# t-1 is byte-identical to recomputing over the prefix (verified by
# tests/test_state_cache_identity.py). The cached path must NEVER produce a
# different value: the identity test asserts full MarketState equality between
# the two paths on every bar.


class Prefix:
    """Read-only prefix view over a full array: `arr[:n]` semantics with O(1)
    reads and O(slice) bounded slices. The feature block reads a growing prefix
    without copying it: the uncached path passes real prefix lists, the cached
    path passes views over precomputed arrays."""

    __slots__ = ('_a', '_n')

    def __init__(self, arr, n):
        self._a, self._n = arr, n

    def __len__(self) -> int:
        return self._n

    def __bool__(self) -> bool:
        return self._n > 0

    def __getitem__(self, i):
        if isinstance(i, slice):
            start, stop, step = i.indices(self._n)
            return self._a[start:stop:step]
        idx = i if i >= 0 else i + self._n
        if not 0 <= idx < self._n:
            raise IndexError('prefix index out of range')
        return self._a[idx]

    def __iter__(self):
        return iter(self._a[:self._n])


def _row_tuple_bytes(row: TapeRow) -> bytes:
    """Canonical bytes of a row's (event_id, payload_hash|payload) tuple, as
    `sha1_hex` serializes it inside a list: the per-row piece of the growing
    lineage lists, precomputed once so the per-state cumulative hash walks
    bytes instead of re-json-dumping dicts."""
    return json.dumps((row.event_id, row.payload.get('payload_hash', row.payload)),
                      sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')


def _cumulative_digest(tuple_bytes: list[bytes], n: int) -> str:
    """sha1_hex of the first n tuples as a JSON list: `[` + comma-joined + `]`.
    Exactly `sha1_hex([(event_id, payload) for ...][:n])` — the same canonical
    string, built from precomputed per-row bytes."""
    h = hashlib.sha1()
    h.update(b'[')
    for i in range(n):
        if i:
            h.update(b',')
        h.update(tuple_bytes[i])
    h.update(b']')
    return h.hexdigest()


def _slice_digest(tuple_bytes: list[bytes], lo: int, hi: int) -> str:
    """sha1_hex of the JSON list `[(event_id, payload) ...]` for rows lo:hi,
    built from the precomputed per-row bytes — byte-identical to the uncached
    `sha1_hex([(b.event_id, payload) for b in rows[lo:hi]])` (JSON arrays keep
    element order, so sort_keys has no effect), without re-json-dumping the
    payload dicts. This is what makes the per-feature input-lineage hashes in
    the cached state path ~10x cheaper."""
    if hi <= lo:
        return ''
    h = hashlib.sha1()
    h.update(b'[')
    for i in range(lo, hi):
        if i != lo:
            h.update(b',')
        h.update(tuple_bytes[i])
    h.update(b']')
    return h.hexdigest()


def _adx_series(highs, lows, closes, period: int = 14) -> list[float]:
    """ADX value at every bar index, replicating `_adx`'s Wilder recurrences so
    `series[t-1] == _adx(highs[:t], lows[:t], closes[:t], period)` exactly."""
    n = len(closes)
    out = [0.0] * n
    if n < 2 * period:
        return out
    trs, pdms, ndms = [], [], []
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        pdms.append(up if (up > dn and up > 0) else 0.0)
        ndms.append(dn if (dn > up and dn > 0) else 0.0)
    atr_w, pdi_w, ndi_w = sum(trs[:period]), sum(pdms[:period]), sum(ndms[:period])
    dxs = [_dx_value(atr_w, pdi_w, ndi_w)]
    for i in range(period, len(trs)):
        atr_w = atr_w - atr_w / period + trs[i]
        pdi_w = pdi_w - pdi_w / period + pdms[i]
        ndi_w = ndi_w - ndi_w / period + ndms[i]
        dxs.append(_dx_value(atr_w, pdi_w, ndi_w))
    adx = sum(dxs[:period]) / period
    out[2 * period - 1] = adx
    for j in range(period, len(dxs)):
        adx = (adx * (period - 1) + dxs[j]) / period
        out[period + j] = adx
    return out


@dataclass
class BarSeries:
    """Per-symbol precomputed series over closed bars in available order.

    Array alignment: most series are indexed by BAR index (j -> bar j), so
    state at t (t closed bars, indices 0..t-1) reads the value for the latest
    bar at [t-1]. `atr` and `rsi` carry the period warmup offset of the
    helpers they mirror (the feature block wraps them in Prefix views with the
    real length). `prior_high`/`prior_low` are indexed by BAR COUNT (t).
    """
    closed: list[TapeRow]
    kline: list[TapeRow]
    funding: list[TapeRow]
    oi: list[TapeRow]
    closes: list
    highs: list
    lows: list
    opens: list
    volumes: list
    tp: list
    ema_fast: list
    ema_slow: list
    atr: list
    rsi: list
    adx: list
    cci: list
    macd: list
    macd_signal: list
    macd_hist: list
    obv: list
    adl: list
    prior_high: list
    prior_low: list
    piv_hi: dict = field(default_factory=dict)
    piv_lo: dict = field(default_factory=dict)
    vwap: list = field(default_factory=list)
    vwap_start: list = field(default_factory=list)
    avail: list = field(default_factory=list)          # closed bars' available_time
    funding_avail: list = field(default_factory=list)
    oi_avail: list = field(default_factory=list)
    kline_avail: list = field(default_factory=list)
    tuple_bytes: list = field(default_factory=list)    # closed-bar lineage pieces
    kline_bytes: list = field(default_factory=list)    # kline-row manifest pieces
    # True when event_time is non-decreasing in available-sorted order: the
    # precomputed vwap session window (a contiguous backward scan) is exact.
    # On a PIT tape with heterogeneous latencies (event_time non-monotonic) the
    # cached path falls back to the exact full-filter `_vwap`.
    event_time_monotonic: bool = True
    # Mutable running lineage state, advanced by the cached state path (lab
    # calls states in increasing bar order, so this is amortized O(1)).
    _last_t: int = -1
    _last_D: str = ''
    _last_prev: str = ''
    _last_m: int = -1
    _last_M: str = ''
    # Persistent incremental hashers (started at b'[' without the closing
    # bracket; the digest is the hasher copy + b']'): a monotonic t/m advance
    # appends the new element instead of re-walking the whole prefix, turning
    # the O(N^2) full-prefix re-hash into O(1) amortized per bar. The hashed
    # BYTES are byte-identical to _cumulative_digest (same concatenation), so
    # every digest is unchanged. Reset to None on a jump (t/m non-consecutive).
    # _dt_n/_md_n count elements already folded in — the JSON-list separator
    # `,` goes BETWEEN elements, never before the first (`[e1,e2]`, not
    # `[,e1,e2]`).
    _dt_hash: hashlib._Hash | None = None
    _md_hash: hashlib._Hash | None = None
    _dt_n: int = 0
    _md_n: int = 0

    def closed_digests(self, t: int) -> tuple[str, str]:
        """(D_{t-1}, D_t): sha1_hex of the closed-bar tuple list up to t-1 / t
        bars. D_{t-1} is the value computed for the previous bar (consecutive
        states) or recomputed on a jump; both are the exact sha1_hex(list)
        semantics the uncached path produces per state. Idempotent on a repeat
        call for the same t."""
        if self._last_t == t:
            return self._last_prev, self._last_D
        if t >= 2:
            if self._last_t == t - 1:
                prev = self._last_D
            else:
                prev = _cumulative_digest(self.tuple_bytes, t - 1)
        else:
            prev = ''
        if self._dt_hash is None or t != self._last_t + 1:
            self._dt_hash = hashlib.sha1()
            self._dt_hash.update(b'[')
            for i in range(t):
                if i:
                    self._dt_hash.update(b',')
                self._dt_hash.update(self.tuple_bytes[i])
            self._dt_n = t
        else:
            if self._dt_n:
                self._dt_hash.update(b',')
            self._dt_hash.update(self.tuple_bytes[t - 1])
            self._dt_n += 1
        h = self._dt_hash.copy()
        h.update(b']')
        dt = h.hexdigest()
        self._last_t, self._last_D, self._last_prev = t, dt, prev
        return prev, dt

    def manifest_digest(self, m: int) -> str:
        """sha1_hex of the kline-row tuple list up to m rows (raw_manifest_hash)."""
        if self._last_m != m:
            if self._md_hash is None or m != self._last_m + 1:
                self._md_hash = hashlib.sha1()
                self._md_hash.update(b'[')
                for i in range(m):
                    if i:
                        self._md_hash.update(b',')
                    self._md_hash.update(self.kline_bytes[i])
                self._md_n = m
            else:
                if self._md_n:
                    self._md_hash.update(b',')
                self._md_hash.update(self.kline_bytes[m - 1])
                self._md_n += 1
            h = self._md_hash.copy()
            h.update(b']')
            self._last_M = h.hexdigest()
            self._last_m = m
        return self._last_M


def _pivot_lists(highs, lows, n: int) -> tuple[list, list]:
    """All confirmed strength-n pivot bars in the FULL series, as
    (idx, value, range). A bar's pivot status is fixed once its right flank
    closes, so at state t the confirmed subset is exactly the pivots with
    idx <= t-1-n; the significance filter (range >= k*ATR) is applied per state
    because ATR moves."""
    hi, lo = [], []
    for i in range(n, len(highs) - n):
        h, l = highs[i], lows[i]
        if h > max(highs[i - n:i] + highs[i + 1:i + 1 + n]):
            hi.append((i, h, h - l))
        if l < min(lows[i - n:i] + lows[i + 1:i + 1 + n]):
            lo.append((i, l, highs[i] - l))
    return hi, lo


def _last_significant_pivot(pivs, t: int, n: int, atr_now: float, k: float):
    """(idx, value) of the most recent confirmed pivot whose range passes the
    CRIT-1 significance filter at the CURRENT atr — exactly `hi_pivs[-1]` from
    `_significant_pivots` (which re-scans every bar with today's atr, so an
    older pivot can become significant as ATR falls). None when no confirmed
    pivot passes."""
    limit = t - 1 - n
    for idx, val, rng in reversed(pivs):
        if idx > limit:
            continue
        if rng >= k * atr_now:
            return (idx, val)
    return None


def _last_confirmed_swing(pivs, t: int, n: int):
    """(idx, value) of the most recent confirmed pivot (no significance
    filter), mirroring `_confirmed_swings`' persistent most-recent pair."""
    limit = t - 1 - n
    for idx, val, _rng in reversed(pivs):
        if idx <= limit:
            return (idx, val)
    return None


def build_bar_series(closed: list[TapeRow], kline_rows: list[TapeRow],
                     funding_rows: list[TapeRow], oi_rows: list[TapeRow]) -> BarSeries:
    """Precompute every series build_state needs over the full closed-bar
    sequence. Each array is computed with the SAME formula the uncached path
    uses at the final bar, so indexing reproduces prefix results exactly."""
    closes = [float(b.payload['close']) for b in closed]
    highs = [float(b.payload['high']) for b in closed]
    lows = [float(b.payload['low']) for b in closed]
    opens = [float(b.payload['open']) for b in closed]
    volumes = [float(b.payload.get('volume', 0.0)) for b in closed]
    # When every kline row is a closed bar (the vision_backfill tapes), the raw
    # manifest list and the closed-bar list are the SAME rows in the SAME
    # order, so the cached state path can reuse the closed-bar lineage digest
    # (D_t) for raw_manifest_hash instead of hashing the kline stream twice.
    if kline_rows and all(b.payload.get('closed') is True for b in kline_rows):
        kline_rows = closed
    n = len(closes)
    tp = _typical(highs, lows, closes)
    ema_fast = _ema(closes, 5)
    ema_slow = _ema(closes, 20)
    atr = _atr_series(highs, lows, 14)
    rsi = _rsi_series(closes, 14)
    adx = _adx_series(highs, lows, closes, 14)

    cci = [0.0] * n
    for j in range(19, n):
        w = tp[j - 19:j + 1]
        sma = sum(w) / 20
        mad = sum(abs(x - sma) for x in w) / 20
        cci[j] = (tp[j] - sma) / (0.015 * mad) if mad else 0.0

    macd = [f - s for f, s in zip(_ema(closes, 12), _ema(closes, 26))]
    macd_signal = _ema(macd, 9)
    macd_hist = [m - s for m, s in zip(macd, macd_signal)]

    obv = [0.0] * n
    acc = 0.0
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            acc += volumes[i]
        elif closes[i] < closes[i - 1]:
            acc -= volumes[i]
        obv[i] = acc
    adl = [0.0] * n
    acc = 0.0
    for i, (h, l, c, v) in enumerate(zip(highs, lows, closes, volumes)):
        rng = h - l
        if rng > 0:
            acc += ((c - l) - (h - c)) / rng * v
        adl[i] = acc

    prior_high = [None, None]
    prior_low = [None, None]
    ph = [highs[0]]
    pl = [lows[0]]
    for j in range(1, n):
        ph.append(ph[-1] if ph[-1] >= highs[j] else highs[j])
        pl.append(pl[-1] if pl[-1] <= lows[j] else lows[j])
    prior_high += ph[:n - 1]
    prior_low += pl[:n - 1]

    piv_hi, piv_lo = {}, {}
    for swn in SWING_NS:
        piv_hi[swn], piv_lo[swn] = _pivot_lists(highs, lows, swn)

    vwap = [0.0] * n
    vwap_start = [0] * n
    for j in range(n):
        ev = closed[j].event_time
        anchor = ev - (ev % DAY_NS)
        lo = j
        while lo > 0 and closed[lo - 1].event_time >= anchor:
            lo -= 1
        vwap_start[j] = lo
        tp_v = vol = 0.0
        for b in closed[lo:j + 1]:
            p = b.payload
            tp_v += (float(p['high']) + float(p['low']) + float(p['close'])) / 3.0 \
                * float(p.get('volume', 0.0))
            vol += float(p.get('volume', 0.0))
        vwap[j] = tp_v / vol if vol else 0.0

    return BarSeries(
        closed=closed, kline=kline_rows, funding=funding_rows, oi=oi_rows,
        closes=closes, highs=highs, lows=lows, opens=opens, volumes=volumes,
        tp=tp, ema_fast=ema_fast, ema_slow=ema_slow, atr=atr, rsi=rsi, adx=adx,
        cci=cci, macd=macd, macd_signal=macd_signal, macd_hist=macd_hist,
        obv=obv, adl=adl, prior_high=prior_high, prior_low=prior_low,
        piv_hi=piv_hi, piv_lo=piv_lo, vwap=vwap, vwap_start=vwap_start,
        event_time_monotonic=all(a.event_time <= b.event_time
                                 for a, b in zip(closed, closed[1:])),
        avail=[b.available_time for b in closed],
        funding_avail=[r.available_time for r in funding_rows],
        oi_avail=[r.available_time for r in oi_rows],
        kline_avail=[r.available_time for r in kline_rows],
        tuple_bytes=[_row_tuple_bytes(b) for b in closed],
        kline_bytes=[_row_tuple_bytes(r) for r in kline_rows])


def build_state(rows: list[TapeRow], as_of: int, universe: tuple[str, ...],
                feature_version: str = 'v1',
                history_depth: int = HISTORY_DEPTH_DEFAULT,
                series: dict[str, BarSeries] | None = None) -> MarketState:
    # The cached path (series provided) reads precomputed per-symbol arrays and
    # skips the O(N) validation scan: a BarSeries is built over already
    # available-sorted, clock-validated rows, and the lab guarantees the batch
    # it feeds a series is admissible at the clock.
    if series is None:
        prev_t = -1
        for r in rows:
            if r.available_time > as_of:
                raise FutureRowError(
                    f'row {r.event_id} available at {r.available_time} > decision clock {as_of}')
            # PIT ordering: closed[-1] is the latest bar ONLY if rows are in
            # chronological order. Unsorted input silently selects the wrong bar
            # (reversed rows changed close and prior_high empirically); fail closed
            # rather than emit wrong features (MARKET_STATE_CONTRACT section 1).
            if r.available_time < prev_t:
                raise ValueError(
                    f'rows must be sorted by available_time (got {r.available_time} '
                    f'after {prev_t} at {r.event_id}); unsorted input silently '
                    'selects the wrong bar')
            prev_t = r.available_time
    features: dict[str, FeatureValue] = {}
    manifest_hash: str | None = None
    for sym in universe:
        if series is None:
            bars = [r for r in rows if r.instrument == sym and r.channel == 'kline']
            # Only closed klines feed OHLC features (FEED_INGESTION_SPEC section 3).
            closed = [b for b in bars if b.payload.get('closed') is True]
            if not closed:
                continue
            closes = [float(b.payload['close']) for b in closed]
            highs = [float(b.payload['high']) for b in closed]
            lows = [float(b.payload['low']) for b in closed]
            opens = [float(b.payload['open']) for b in closed]
            volumes = [float(b.payload.get('volume', 0.0)) for b in closed]
            # Every series the feature block needs, computed over the prefix as
            # the inline helpers always did (the cached path reads the same
            # arrays precomputed over the full tape — byte-identical values,
            # verified by tests/test_state_cache_identity.py).
            fast_series = _ema(closes, 5)
            slow_series = _ema(closes, 20)
            atrs = _atr_series(highs, lows, 14)
            rsis = _rsi_series(closes, 14)
            tp = _typical(highs, lows, closes)
            adx_now = _adx(highs, lows, closes, 14)
            cci_now = _cci(highs, lows, closes, 20)
            macd, macd_signal, macd_hist = _macd(closes, 12, 26, 9)
            obv_now = _obv(closes, volumes)
            adl_now = _adl(highs, lows, closes, volumes)
            prior_high = max(highs[:-1]) if len(highs) > 1 else None
            prior_low = min(lows[:-1]) if len(lows) > 1 else None
            vwap_val, vwap_bars = _vwap(closed)
            funding_rows = [r for r in rows
                            if r.instrument == sym and r.channel == 'funding']
            oi_rows = [r for r in rows
                       if r.instrument == sym and r.channel == 'open_interest']
            # Growing-list lineages are computed per feature from `consumed`
            # (the reference behavior); the cached path supplies them exact.
            D_prev = D_t = manifest_hash = None
            t = 0
        else:
            s = series.get(sym)
            if s is None:
                continue                     # absent symbol -> missing_symbols
            t = bisect_right(s.avail, as_of)
            if t == 0:
                continue
            D_prev, D_t = s.closed_digests(t)
            # When kline == closed (see build_bar_series aliasing), the raw
            # manifest list is the closed-bar list, so D_t IS raw_manifest_hash.
            if s.kline is s.closed:
                manifest_hash = D_t
            else:
                manifest_hash = s.manifest_digest(bisect_right(s.kline_avail, as_of))
            closed = Prefix(s.closed, t)
            closes = Prefix(s.closes, t)
            highs = Prefix(s.highs, t)
            lows = Prefix(s.lows, t)
            opens = Prefix(s.opens, t)
            volumes = Prefix(s.volumes, t)
            fast_series = Prefix(s.ema_fast, t)
            slow_series = Prefix(s.ema_slow, t)
            atrs = Prefix(s.atr, max(0, t - 13))
            rsis = Prefix(s.rsi, max(0, t - 14))
            tp = Prefix(s.tp, t)
            adx_now = s.adx[t - 1]
            cci_now = s.cci[t - 1]
            macd, macd_signal, macd_hist = (s.macd[t - 1], s.macd_signal[t - 1],
                                            s.macd_hist[t - 1])
            obv_now, adl_now = s.obv[t - 1], s.adl[t - 1]
            prior_high, prior_low = s.prior_high[t], s.prior_low[t]
            if s.event_time_monotonic:
                vwap_val = s.vwap[t - 1]
                vwap_bars = s.closed[s.vwap_start[t - 1]:t]
            else:
                # Non-monotonic event_time (a PIT tape with heterogeneous
                # latencies): the contiguous session precompute would silently
                # miss a scattered same-day bar, so fall back to the exact
                # full-filter `_vwap` (O(N) per state, the uncached reference).
                vwap_val, vwap_bars = _vwap(closed)
            m = bisect_right(s.funding_avail, as_of)
            funding_rows = [s.funding[m - 1]] if m > 0 else []
            m = bisect_right(s.oi_avail, as_of)
            oi_rows = [s.oi[m - 1]] if m > 0 else []
            # Fast per-feature lineage: every `consumed` here is a contiguous
            # slice of s.closed (the same row objects), so the feature's input
            # lineage is `_slice_digest` over the precomputed row bytes and its
            # calc clock is the slice's last available_time — no re-json-dump,
            # no max() generator. A row not in s.closed (funding/OI) or a
            # non-contiguous window (the non-monotonic `_vwap` fallback) drops
            # to the exact slow path below. `slice_cache` is per-(state, symbol),
            # so a window shared by several features (e.g. closed[-20:] feeds
            # six bollinger features) is hashed once per bar.
            id_map = {id(b): i for i, b in enumerate(s.closed)}
            slice_cache: dict[tuple[int, int], str] = {}

        def add(name: str, value: float | str | None | tuple | list, consumed: list,
                quality: str = 'COMPLETE', null_reason: str | None = None,
                dtype: str = 'float', lineage: str | None = None) -> None:
            # A None value is absent data, never a zero (MARKET_STATE_CONTRACT
            # section 4: "Null is not zero"). Auto-degrade it with an explicit
            # null reason instead of labelling it COMPLETE — the D-024 DEGRADED
            # veto is what makes a missing feature reachable at admission.
            if value is None and quality == 'COMPLETE':
                quality = 'DEGRADED'
                null_reason = null_reason or 'NOT_YET_AVAILABLE'
            # Per-feature input lineage + calculation clock (MARKET_STATE_
            # CONTRACT 2): the identity of the raw rows that produced this
            # feature and the latest such row's availability. max_input_
            # available_time is the SAME consumed-derived clock (never the
            # newest bar for a feature that does not consume it — prior_high/
            # prior_low exclude the newest bar), so the field never claims an
            # input newer than the feature's own calculation time. A feature
            # that consumed nothing (prior_high on the first bar) has clock 0:
            # it is not computable yet, and borrowing the newest bar would
            # claim an input the feature never used.
            # Bind the raw row identity: payload_hash when the tape computes it
            # (vision_backfill real tapes — compact), else the payload itself
            # (synthetic tapes without payload_hash — small, still detects any
            # raw revision). A value-irrelevant payload change must move the
            # per-feature lineage without fabricating a new state identity.
            #
            # Cached path fast route: `consumed` is a contiguous slice of
            # s.closed (same row objects — verified by the index span check), so
            # the lineage is the slice digest over the precomputed row bytes and
            # the calc clock is the slice's last available_time. Byte-identical
            # to the slow path (the identity tests pin input_lineage_hash and
            # calculation_time on every bar); a non-closed row (funding/OI) or a
            # non-contiguous window (non-monotonic `_vwap`) falls back below.
            inp = lineage
            calc = None
            if inp is None and series is not None and consumed:
                # Fast route: consumed is a contiguous slice of s.closed (the
                # index-span check proves it), so the lineage is the slice
                # digest over the precomputed row bytes and the calc clock is
                # the slice's last available_time. Byte-identical to the slow
                # path (the identity tests pin input_lineage_hash and
                # calculation_time on every bar); a non-closed row (funding/OI)
                # or a non-contiguous window (the non-monotonic `_vwap` fallback)
                # drops below.
                assert s is not None
                lo_i = id_map.get(id(consumed[0]))
                hi_i = id_map.get(id(consumed[-1]))
                if lo_i is not None and hi_i is not None \
                        and hi_i - lo_i + 1 == len(consumed):
                    key = (lo_i, hi_i + 1)
                    inp = slice_cache.get(key)
                    if inp is None:
                        inp = _slice_digest(s.tuple_bytes, lo_i, hi_i + 1)
                        slice_cache[key] = inp
                    calc = s.avail[hi_i]
            if calc is None:
                calc = max((b.available_time for b in consumed), default=0)
                if inp is None:
                    inp = sha1_hex([(b.event_id, b.payload.get('payload_hash',
                                                               b.payload))
                                    for b in consumed]) if consumed else ''
            assert inp is not None
            features[f'{sym}.{name}'] = FeatureValue(
                f'{sym}.{name}', value, dtype, feature_version, calc,
                quality=quality, null_reason=null_reason,
                group=FEATURE_TO_GROUP.get(name, 'raw'),
                input_lineage_hash=inp, calculation_time=calc)

        # --- raw / location / trend / volatility (existing baseline) --------
        add('close', closes[-1], [closed[-1]])
        # prior_high/prior_low are the UNBOUNDED prefix extremes — a fixed
        # window would silently diverge, so the cached path carries the exact
        # running prefix max/min and the full-prefix lineage digest (D_{t-1}).
        if series is None:
            add('prior_high', prior_high, closed[:-1])
            add('prior_low', prior_low, closed[:-1])
        elif t >= 2:
            add('prior_high', prior_high, [closed[-2]], lineage=D_prev)
            add('prior_low', prior_low, [closed[-2]], lineage=D_prev)
        else:
            add('prior_high', None, [], lineage='')
            add('prior_low', None, [], lineage='')
        # fast_series/slow_series are computed in the per-symbol setup (cached:
        # precomputed Prefix views) and shared by the trend features and the
        # per-bar history tuples.
        if len(closes) >= 20:
            if series is None:
                add('ema_fast', fast_series[-1], closed)
                add('ema_slow', slow_series[-1], closed)
            else:
                add('ema_fast', fast_series[-1], [closed[-1]], lineage=D_t)
                add('ema_slow', slow_series[-1], [closed[-1]], lineage=D_t)
            add('atr', sum(h - l for h, l in zip(highs[-14:], lows[-14:])) / 14,
                closed[-14:])

        # --- FG-1 candle_shape (G-01..G-07) ----------------------------------
        o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
        rng = h - l
        body = abs(c - o)
        add('real_body', body, closed[-1:])
        add('body_range_ratio', body / rng if rng > 0 else 0.0, closed[-1:])
        add('upper_shadow', h - max(o, c), closed[-1:])
        add('lower_shadow', min(o, c) - l, closed[-1:])
        add('close_position', (c - l) / rng if rng > 0 else 0.5, closed[-1:])
        if len(closed) >= 2:
            po, ph, pl = opens[-2], highs[-2], lows[-2]
            add('inside_bar', 1.0 if h <= ph and l >= pl else 0.0, closed[-2:])
            add('outside_bar', 1.0 if h >= ph and l <= pl else 0.0, closed[-2:])
            if o > ph:          # type-3 gap up (G-07)
                add('gap_size', o - ph, closed[-2:])
                add('gap_dir', 1.0, closed[-2:])
            elif o < pl:        # type-3 gap down
                add('gap_size', o - pl, closed[-2:])
                add('gap_dir', -1.0, closed[-2:])
            else:
                add('gap_size', 0.0, closed[-2:])   # 0.0 = no gap (a real zero)
                add('gap_dir', 0.0, closed[-2:])
        else:
            # Bar 0: the prior-bar features are data absence (not yet available).
            add('inside_bar', None, [], null_reason='NOT_YET_AVAILABLE')
            add('outside_bar', None, [], null_reason='NOT_YET_AVAILABLE')
            add('gap_size', None, [], null_reason='NOT_YET_AVAILABLE')
            add('gap_dir', None, [], null_reason='NOT_YET_AVAILABLE')

        # --- FG-2 oscillator (G-08..G-15) -----------------------------------
        n_close = len(closes)
        if n_close >= 15:
            add('rsi14', rsis[-1], closed[-15:])
            add('mom_14', closes[-1] - closes[-15], closed[-15:])
            add('roc_14', (closes[-1] - closes[-15]) / closes[-15] * 100.0,
                closed[-15:])
        if n_close >= 16:
            k, d = _stoch(highs, lows, closes, 14)
            add('stoch_k', k, closed[-16:])
            add('stoch_d', d, closed[-16:])
        if n_close >= 28:
            add('stochrsi',
                _stochrsi_from(rsis) if series is not None
                else _stochrsi(closes, 14),
                closed[-28:])
        if n_close >= 20:
            add('cci20', cci_now, closed[-20:])
        if n_close >= 34:
            add('macd', macd, closed[-34:])
            add('macd_signal', macd_signal, closed[-34:])
            add('macd_hist', macd_hist, closed[-34:])
        if n_close >= 28:
            add('adx14', adx_now, closed[-28:])
        if n_close >= 14 + OBOS_QUANTILE_WINDOW:
            add('osc_obos_quantile',
                _percentile_rank(rsis[-OBOS_QUANTILE_WINDOW:], rsis[-1]),
                closed[-(14 + OBOS_QUANTILE_WINDOW):])

        # --- FG-3 volatility extensions (G-16..G-20, G-28) -------------------
        if n_close >= 20:
            mid = _sma(closes, 20)
            sd = _std_pop(closes[-20:])
            upper, lower = mid + 2.0 * sd, mid - 2.0 * sd
            add('bb_mid', mid, closed[-20:])
            add('bb_upper', upper, closed[-20:])
            add('bb_lower', lower, closed[-20:])
            add('bb_pct_b', (closes[-1] - lower) / (upper - lower) if upper > lower else 0.5,
                closed[-20:])
            add('bb_bandwidth', (upper - lower) / mid if mid else 0.0, closed[-20:])
        if n_close >= 5:
            add('atr_locational', sum(h - l for h, l in zip(highs[-5:], lows[-5:])) / 5,
                closed[-5:])
        if n_close >= 20:
            add('atr_filtered_2sigma', atrs[-1], closed[-14:])
        if len(atrs) >= ATR_FILTER_BAND_N:
            band = _sma(atrs, ATR_FILTER_BAND_N) + 2.0 * _std_pop(atrs[-ATR_FILTER_BAND_N:])
            add('atr_2sigma_active', 1.0 if atrs[-1] > band else 0.0,
                closed[-(14 + ATR_FILTER_BAND_N - 1):])
        if len(atrs) >= ATR_SLOPE_N + 1:
            slope = atrs[-1] - atrs[-1 - ATR_SLOPE_N]
            add('atr_trend_phase', 1.0 if slope > 0 else (-1.0 if slope < 0 else 0.0),
                closed[-(14 + ATR_SLOPE_N):])
        if n_close >= 23:
            mid_k = _sma(tp, 10)
            k_atr = _sma(atrs, 10)
            add('keltner_u', mid_k + k_atr, closed[-23:])
            add('keltner_l', mid_k - k_atr, closed[-23:])
        if n_close >= 15:
            mid_s = _sma(tp, 6)
            a15 = sum(h - l for h, l in zip(highs[-15:], lows[-15:])) / 15
            add('starc_u', mid_s + STARC_K * a15, closed[-15:])
            add('starc_l', mid_s - STARC_K * a15, closed[-15:])
        if n_close >= 20:
            add('atr_band_stop', ATR_BAND_STOP_K * atrs[-1], closed[-20:])

        # --- FG-4 location extensions (G-21..G-28) ---------------------------
        # Warmup-gated features are ABSENT until their window is satisfied
        # (the ema_fast/atr pattern): a not-yet-computable feature must not
        # degrade the state, and absent carries no empty input lineage.
        atr_now = atrs[-1] if atrs else None
        for n in SWING_NS:
            if n_close >= 2 * n + 1 and atr_now is not None:
                if series is None:
                    hi_pivs, lo_pivs = _significant_pivots(
                        highs, lows, n, atr_now, SWING_SIGNIFICANCE_K)
                    swing_hi = hi_pivs[-1][1] if hi_pivs else 0.0
                    swing_lo = lo_pivs[-1][1] if lo_pivs else 0.0
                else:
                    # The cached path filters the precomputed pivot list with
                    # today's ATR (the filter is atr-dependent, so it cannot be
                    # hoisted), scanning backward for the most recent pass.
                    p = _last_significant_pivot(s.piv_hi[n], t, n, atr_now,
                                                SWING_SIGNIFICANCE_K)
                    q = _last_significant_pivot(s.piv_lo[n], t, n, atr_now,
                                                SWING_SIGNIFICANCE_K)
                    swing_hi = p[1] if p else 0.0
                    swing_lo = q[1] if q else 0.0
                # 0.0 = "no significant swing" sentinel: OHLC is strictly
                # positive on any validated tape, so 0.0 is never a real level.
                add(f'swing_high_{n}', swing_hi, closed[-(2 * n + 1):])
                add(f'swing_low_{n}', swing_lo, closed[-(2 * n + 1):])
        for n in WINDOW_NS:
            if n_close >= n + 1:
                add(f'window_high_{n}', max(highs[-(n + 1):-1]), closed[-(n + 1):-1])
                add(f'window_low_{n}', min(lows[-(n + 1):-1]), closed[-(n + 1):-1])
                add(f'range_height_{n}',
                    max(highs[-(n + 1):-1]) - min(lows[-(n + 1):-1]),
                    closed[-(n + 1):-1])
        # fib_levels: anchored on the most recent CONFIRMED swing pair (G-24;
        # the CRIT-1 significance filter applies to the G-21 swing_* features,
        # not to the fib anchor). Confirmed pairs are persistent once formed,
        # so the feature is ABSENT only during pre-anchor warmup; the "area of
        # application" invariant holds because the anchor is always a past,
        # confirmed swing.
        if n_close >= 21:
            if series is None:
                hi10, lo10 = _confirmed_swings(highs, lows, 10)
            else:
                hi10 = _last_confirmed_swing(s.piv_hi[10], t, 10)
                lo10 = _last_confirmed_swing(s.piv_lo[10], t, 10)
            fibs = _fib_levels(hi10, lo10)
            if fibs is not None:
                add('fib_levels', fibs, closed[-21:], dtype='fib_levels')
        if n_close >= BARS_PER_DAY + 1:
            ph_p = max(highs[-(BARS_PER_DAY + 1):-1])
            pl_p = min(lows[-(BARS_PER_DAY + 1):-1])
            pc_p = closes[-BARS_PER_DAY - 1]
            pp = (ph_p + pl_p + pc_p) / 3.0
            rng_p = ph_p - pl_p
            add('pivot_points_day',
                (pp, pp + (pp - pl_p), pp + rng_p, pp + (pp - pl_p) + rng_p,
                 pp + rng_p + rng_p,
                 pp - (ph_p - pp), pp - rng_p, pp - (ph_p - pp) - rng_p,
                 pp - rng_p - rng_p),
                closed[-(BARS_PER_DAY + 1):-1], dtype='pivot_points')
        if n_close >= CONSOLIDATION_BARS + 1:
            add('consolidation_range', _consolidation_range(highs, lows, closes),
                closed[-(CONSOLIDATION_BARS + 1):-1], dtype='consolidation')
        add('gap_levels', _gap_levels(opens, highs, lows, closes), closed[-GAP_ZONE_BARS:],
            dtype='gap_levels')

        # --- FG-5 participation activation (G-29..G-37) ----------------------
        add('volume', volumes[-1], closed[-1:])
        if n_close >= VOLUME_STAT_N:
            vol_win = volumes[-VOLUME_STAT_N:]
            vmean = _mean(vol_win)
            vsd = _std_pop(vol_win)
            add('vol_zscore', (volumes[-1] - vmean) / vsd if vsd else 0.0,
                closed[-VOLUME_STAT_N:])
            vmin, vmax = min(vol_win), max(vol_win)
            add('vol_min_proximity',
                (volumes[-1] - vmin) / (vmax - vmin) if vmax > vmin else 0.5,
                closed[-VOLUME_STAT_N:])
        if n_close >= VOLUME_SMA_N:
            add('vol_smooth_ma', _sma(volumes, VOLUME_SMA_N), closed[-VOLUME_SMA_N:])
        if n_close >= 2:
            add('obv', obv_now, closed[-2:])
        if series is None:
            add('adl', adl_now, closed)
        else:
            add('adl', adl_now, [closed[-1]], lineage=D_t)
        if n_close >= CMF_N:
            add('cmf_20', _cmf(highs, lows, closes, volumes, CMF_N), closed[-CMF_N:])
        add('vwap', vwap_val, vwap_bars)
        if n_close >= BAR_CLASS_N and n_close >= 6:
            add('bar_class', _bar_class(opens, closes, highs, lows, volumes),
                closed[-BAR_CLASS_N:])

        # --- FG-6 session (G-38..G-40) --------------------------------------
        ev = closed[-1].event_time
        hour = _hour_utc(ev)
        add('hour_of_day_utc', float(hour), closed[-1:])
        add('impulsive_window',
            1.0 if IMPULSIVE_START_HOUR <= hour <= IMPULSIVE_END_HOUR else 0.0,
            closed[-1:])
        add('bar_of_session', float(_bar_of_session(ev)), closed[-1:])
        add('day_index', float(_day_index(ev)), closed[-1:])

        # --- FG-7 positioning (G-41..G-43) -----------------------------------
        # Data-absent channels are NOT emitted (absent, like ema_fast during
        # warmup): emitting None for an absent channel would degrade every
        # state and make the D-024 veto unreachable-in-practice. When a tape
        # carries the channel, the latest admissible value is emitted.
        if series is None:
            # The cached path already resolved funding_rows/oi_rows to the
            # last admissible row (O(1)); a per-state scan here would be the
            # O(N) the fast path exists to avoid.
            funding_rows = [r for r in rows
                            if r.instrument == sym and r.channel == 'funding']
            oi_rows = [r for r in rows
                       if r.instrument == sym and r.channel == 'open_interest']
        if funding_rows:
            add('funding_rate', float(funding_rows[-1].payload['funding_rate']),
                [funding_rows[-1]])
        if oi_rows:
            add('open_interest', float(oi_rows[-1].payload['open_interest']),
                [oi_rows[-1]])
            if 'long_short_skew' in oi_rows[-1].payload:
                add('long_short_skew', float(oi_rows[-1].payload['long_short_skew']),
                    [oi_rows[-1]])

        # D-026 history feature group: last 32 closed bars as a tuple of
        # (event_id, open, high, low, close, ema_fast, ema_slow), oldest first,
        # per-bar EMAs over the full close series. This is the anchor scan the
        # pilots use to find setup_anchor_event_id (CANDIDATE_LIFECYCLE_SPEC 1).
        if closed:
            window = closed[-history_depth:]
            hist = tuple(
                (b.event_id, float(b.payload['open']), float(b.payload['high']),
                 float(b.payload['low']), float(b.payload['close']),
                 fast_series[i + len(closed) - len(window)],
                 slow_series[i + len(closed) - len(window)])
                for i, b in enumerate(window))
            # The history tuples embed per-bar EMAs computed over the FULL
            # close series, so the input lineage covers all closed bars — a
            # revision anywhere in the series changes the embedded EMA values.
            if series is None:
                hist_lineage = sha1_hex(
                    [(b.event_id, b.payload.get('payload_hash', b.payload))
                     for b in closed])
            else:
                hist_lineage = D_t
            features[f'{sym}.history'] = FeatureValue(
                f'{sym}.history', hist, 'history', 'v2',
                closed[-1].available_time, quality='COMPLETE', group='history',
                input_lineage_hash=hist_lineage,
                calculation_time=closed[-1].available_time)
    validate_feature_groups(features)
    # A universe symbol with no emitted features (zero kline rows or zero CLOSED
    # bars) degrades the state: an entirely absent symbol is a data-integrity
    # failure, and quality=COMPLETE would make the D-024 DEGRADED veto silently
    # unreachable for it (the per-feature None path already degrades).
    emitted_symbols = {k.split('.', 1)[0] for k in features}
    missing_symbols = [s for s in universe if s not in emitted_symbols]
    # State quality is DEGRADED when any emitted feature is, or any universe
    # symbol is absent (MARKET_STATE_CONTRACT section 4). This is what makes the
    # D-024 DEGRADED data-integrity veto reachable at admission; quality is
    # metadata and does not enter the lineage/state hashes, so it cannot leak
    # into identities.
    quality = 'DEGRADED' if missing_symbols \
        or any(v.quality == 'DEGRADED' for v in features.values()) \
        else 'COMPLETE'
    # Lineage binds every feature's value, availability, group tag and version,
    # so a re-tag or re-version changes every dependent hash (MARKET_STATE_CONTRACT 2).
    # Per-feature input_lineage_hash and the state provenance are audit
    # metadata and deliberately do NOT join this identity hash (the identity is
    # a function of the semantic values; a raw revision that does not change a
    # value must not fabricate a new state identity).
    lineage = sha1_hex({k: [v.value, v.max_input_available_time, v.group,
                            v.feature_version]
                        for k, v in sorted(features.items())})
    # raw_manifest_hash covers EVERY kline row admissible at the clock. The
    # cached path derives it from the per-symbol series (single-symbol stores
    # are the only supported run shape); when a symbol was absent or the
    # universe spans multiple symbols, fall back to the batch scan (the
    # uncached behavior) rather than emit a wrong manifest.
    if series is None or len(universe) > 1 or manifest_hash is None:
        raw_manifest_hash = sha1_hex(
            [(r.event_id, r.payload.get('payload_hash', r.payload))
             for r in rows if r.channel == 'kline'])
    else:
        raw_manifest_hash = manifest_hash
    provenance = {
        'raw_manifest_hash': raw_manifest_hash,
        'feature_graph_version': FEATURE_GRAPH_VERSION,
        'code_version': _BUILDER_SRC_HASH,
    }
    return MarketState(
        state_id=sha1_hex((as_of, universe, lineage)),
        as_of=as_of, universe=universe, features=features,
        lineage_hash=lineage, quality=quality, provenance=provenance)


def build_multi_state(rows: list[TapeRow], as_of: int,
                      universe: tuple[str, ...], *, base_interval: str,
                      intervals: tuple[str, ...] = (),
                      depths: dict[str, int] | None = None,
                      feature_version: str = 'v1',
                      series: dict[str, dict[str, BarSeries]] | None = None) -> MarketState:
    """One canonical state per decision clock, carrying every declared interval.

    The base interval is built exactly as before and keeps its unprefixed keys,
    so this is a superset of the pre-D-053 state rather than a replacement.
    Each higher interval is aggregated from the same rows and run through the
    SAME feature builder, then namespaced `{sym}.{tf}.{feature}` — one formula
    of record per feature, never a second implementation that could drift.

    Point-in-time safety is inherited rather than re-argued: an aggregate's
    `available_time` is its last constituent's, so a 4h bar spanning 08:00-12:00
    simply does not exist among the rows at 09:00 and cannot be built into the
    09:00 state.
    """
    from .interval import aggregate, is_derivable

    depths = depths or {}
    base = build_state(rows, as_of, universe, feature_version,
                       depths.get(base_interval, HISTORY_DEPTH_DEFAULT),
                       series=series.get(base_interval) if series else None)
    extra: dict[str, FeatureValue] = {}
    for tf in intervals:
        if tf == base_interval:
            continue
        if not is_derivable(base_interval, tf):
            raise ValueError(
                f'{tf} is not derivable from base interval {base_interval}')
        agg = aggregate(rows, base_interval, tf)
        if not agg:
            continue                      # not enough base bars for one bucket
        sub = build_state(agg, as_of, universe, feature_version,
                          depths.get(tf, HISTORY_DEPTH_DEFAULT),
                          series=series.get(tf) if series else None)
        for key, fv in sub.features.items():
            sym, _, name = key.partition('.')
            nk = f'{sym}.{tf}.{name}'
            extra[nk] = FeatureValue(
                nk, fv.value, fv.dtype, fv.feature_version,
                fv.max_input_available_time, quality=fv.quality,
                null_reason=fv.null_reason, group=fv.group,
                input_lineage_hash=fv.input_lineage_hash)
    if not extra:
        return base

    features = dict(base.features)
    features.update(extra)
    quality = 'DEGRADED' if base.quality == 'DEGRADED' \
        or any(v.quality == 'DEGRADED' for v in extra.values()) else 'COMPLETE'
    lineage = sha1_hex({k: [v.value, v.max_input_available_time, v.group,
                            v.feature_version]
                        for k, v in sorted(features.items())})
    prov = dict(base.provenance or {})
    prov['intervals'] = [base_interval] + [t for t in intervals
                                           if t != base_interval]
    return MarketState(
        state_id=sha1_hex((as_of, universe, lineage)),
        as_of=as_of, universe=universe, features=features,
        lineage_hash=lineage, quality=quality, provenance=prov)


# --- D-053 per-Expert projection -------------------------------------------


def group_closure(groups: tuple[str, ...] | list[str]) -> frozenset[str]:
    """A declared group set plus everything it transitively `requires`.

    An Expert declaring `history` is also declaring the graph beneath it: the
    group table says `history` requires `trend` and `volatility`, which in turn
    require `raw`. Serving the declared groups alone would withhold `close`
    from every Expert in the registry, none of which declares `raw`.
    """
    out: set[str] = set()
    stack = list(groups)
    while stack:
        g = stack.pop()
        if g in out or g not in FEATURE_GROUPS:
            continue
        out.add(g)
        stack.extend(FEATURE_GROUPS[g]['requires'])
    return frozenset(out)


def feature_interval(key: str, base_interval: str,
                     known_intervals: frozenset[str]) -> str:
    """The interval a feature key belongs to.

    Base-interval features stay unprefixed (`BTCUSDT.atr`) so every pre-D-053
    Expert and test reads exactly what it always read; higher intervals carry a
    namespace segment (`BTCUSDT.4h.atr`).
    """
    parts = key.split('.')
    if len(parts) >= 3 and parts[1] in known_intervals:
        return parts[1]
    return base_interval


def projection_allowed_keys(universe, closure, wanted, base_interval: str,
                            known_intervals: frozenset[str]) -> frozenset[str]:
    """Static feature-key universe an Expert's projection can contain: every
    emitted feature name in the group closure, on the base interval and each
    declared higher interval, per universe symbol.

    This is EXACTLY the set the runtime filter (group closure + interval in
    `wanted`) accepts over the keys `build_state` can emit, because the builder
    emits every feature through `FEATURE_TO_GROUP` and the namespace rules are
    the same. Building the projection is then one frozenset membership per key
    instead of a per-key `feature_interval` call — a profiled hot path at tens
    of thousands of projections per run.
    """
    out: set[str] = set()
    for sym in universe:
        for name, group in FEATURE_TO_GROUP.items():
            if group not in closure:
                continue
            out.add(f'{sym}.{name}')
            for tf in wanted:
                if tf != base_interval and tf in known_intervals:
                    out.add(f'{sym}.{tf}.{name}')
    return frozenset(out)


def project_state(state: MarketState, *, groups: tuple[str, ...] | list[str],
                  intervals: tuple[str, ...], base_interval: str,
                  known_intervals: frozenset[str],
                  depths: dict[str, int] | None = None,
                  allowed_keys: frozenset[str] | None = None) -> MarketState:
    """The MarketState one Expert asked for: a VIEW of the canonical state.

    `state_id` and `lineage_hash` are carried through unchanged, deliberately.
    The projection is not a state in its own right — it is the same world at
    the same clock with the undeclared parts withheld, so an `ExpertEvaluation`
    still references the one canonical state every Expert saw. Minting a new id
    here would fork the audit anchor per Expert and destroy the property that
    two Experts' decisions at clock D are comparable.

    Withholding rather than absence: a feature outside the declaration is not
    "missing data" (which would read as NO_HABITAT) — it was never requested.
    An Expert that reads outside its declaration raises KeyError at the access
    site, which is what turns the registry audit from a test-time check into a
    runtime one.
    """
    if allowed_keys is None:
        allowed_keys = projection_allowed_keys(
            state.universe, group_closure(groups),
            frozenset(intervals) | {base_interval},
            base_interval, known_intervals)
    features = {k: v for k, v in state.features.items() if k in allowed_keys}
    # Depth is per-Expert, not per-run: the canonical state holds
    # max(declared) so one deep Expert does not force everyone to recompute,
    # and each view is truncated back to its own declaration so it also cannot
    # WIDEN anyone else's window. A shallower Expert must see exactly the
    # history it asked for, or the depth declaration would be advisory.
    if depths:
        for k, v in list(features.items()):
            if not k.endswith('.history') or not isinstance(v.value, tuple):
                continue
            d = depths.get(feature_interval(k, base_interval, known_intervals))
            if d is None or len(v.value) <= d:
                continue
            features[k] = FeatureValue(
                v.name, v.value[-d:], v.dtype, v.feature_version,
                v.max_input_available_time, quality=v.quality,
                null_reason=v.null_reason, group=v.group,
                input_lineage_hash=v.input_lineage_hash)
    return MarketState(
        state_id=state.state_id, as_of=state.as_of, universe=state.universe,
        features=features, lineage_hash=state.lineage_hash,
        quality=state.quality, provenance=state.provenance)
