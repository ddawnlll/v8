"""MarketState builder with availability gating.

Builds an immutable state for decision clock D from tape rows whose
available_time <= D; a future row must fail, never silently pass
(MARKET_STATE_CONTRACT sections 1 and 6).
"""
from __future__ import annotations

from .schema import TapeRow, MarketState, FeatureValue, sha1_hex, FEATURE_GROUPS, FEATURE_TO_GROUP


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


def build_state(rows: list[TapeRow], as_of: int, universe: tuple[str, ...],
                feature_version: str = 'v1') -> MarketState:
    for r in rows:
        if r.available_time > as_of:
            raise FutureRowError(
                f'row {r.event_id} available at {r.available_time} > decision clock {as_of}')
    features: dict[str, FeatureValue] = {}
    for sym in universe:
        bars = [r for r in rows if r.instrument == sym and r.channel == 'kline']
        # Only closed klines feed OHLC features (FEED_INGESTION_SPEC section 3).
        closed = [b for b in bars if b.payload.get('closed') is True]
        if not closed:
            continue
        closes = [float(b.payload['close']) for b in closed]
        highs = [float(b.payload['high']) for b in closed]
        lows = [float(b.payload['low']) for b in closed]
        avail = closed[-1].available_time

        def add(name: str, value: float | None) -> None:
            features[f'{sym}.{name}'] = FeatureValue(
                f'{sym}.{name}', value, 'float', feature_version,
                avail if value is not None else closed[-1].available_time,
                quality='COMPLETE' if value is not None else 'DEGRADED',
                null_reason=None if value is not None else 'NOT_YET_AVAILABLE',
                group=FEATURE_TO_GROUP.get(name, 'raw'))

        add('close', closes[-1])
        add('prior_high', max(highs[:-1]) if len(highs) > 1 else None)
        add('prior_low', min(lows[:-1]) if len(lows) > 1 else None)
        if len(closes) >= 20:
            fast = _ema(closes, 5)[-1]
            slow = _ema(closes, 20)[-1]
            add('ema_fast', fast)
            add('ema_slow', slow)
            add('atr', sum(h - l for h, l in zip(highs[-14:], lows[-14:])) / 14)
        # D-026 history feature group: last 32 closed bars as a tuple of
        # (event_id, open, high, low, close, ema_fast, ema_slow), oldest first,
        # per-bar EMAs over the full close series. This is the anchor scan the
        # pilots use to find setup_anchor_event_id (CANDIDATE_LIFECYCLE_SPEC 1).
        if closed:
            fast_series = _ema(closes, 5)
            slow_series = _ema(closes, 20)
            window = closed[-32:]
            hist = tuple(
                (b.event_id, float(b.payload['open']), float(b.payload['high']),
                 float(b.payload['low']), float(b.payload['close']),
                 fast_series[i + len(closed) - len(window)],
                 slow_series[i + len(closed) - len(window)])
                for i, b in enumerate(window))
            features[f'{sym}.history'] = FeatureValue(
                f'{sym}.history', hist, 'history', 'v2',
                closed[-1].available_time, quality='COMPLETE', group='history')
    validate_feature_groups(features)
    # State quality is DEGRADED when any emitted feature is (MARKET_STATE_CONTRACT
    # section 4). This is what makes the D-024 DEGRADED data-integrity veto
    # reachable at admission; quality is metadata and does not enter the
    # lineage/state hashes, so it cannot leak into identities.
    quality = 'DEGRADED' if any(v.quality == 'DEGRADED' for v in features.values()) \
        else 'COMPLETE'
    # Lineage binds every feature's value, availability, group tag and version,
    # so a re-tag or re-version changes every dependent hash (MARKET_STATE_CONTRACT 2).
    lineage = sha1_hex({k: [v.value, v.max_input_available_time, v.group,
                            v.feature_version]
                        for k, v in sorted(features.items())})
    return MarketState(
        state_id=sha1_hex((as_of, universe, lineage)),
        as_of=as_of, universe=universe, features=features,
        lineage_hash=lineage, quality=quality)
