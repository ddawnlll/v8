"""MarketState builder with availability gating.

Builds an immutable state for decision clock D from tape rows whose
available_time <= D; a future row must fail, never silently pass
(MARKET_STATE_CONTRACT sections 1 and 6).
"""
from __future__ import annotations

from pathlib import Path

from .schema import (TapeRow, MarketState, FeatureValue, sha1_hex, FEATURE_GROUPS,
                     FEATURE_TO_GROUP, FEATURE_GRAPH_VERSION)

# Builder code version bound into every state's provenance: a semantic change
# in build_state re-versions every state's provenance even when the emitted
# values round-trip (MARKET_STATE_CONTRACT 2 code_version).
_BUILDER_SRC_HASH = sha1_hex(Path(__file__).read_bytes())


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

        def add(name: str, value: float | None, consumed: list,
                quality: str = 'COMPLETE', null_reason: str | None = None) -> None:
            # Per-feature input lineage + calculation clock (MARKET_STATE_
            # CONTRACT 2): the identity of the raw rows that produced this
            # feature and the latest such row's availability.
            calc = max((b.available_time for b in consumed), default=0) or \
                (closed[-1].available_time if closed else 0)
            # Bind the raw row identity: payload_hash when the tape computes it
            # (vision_backfill real tapes — compact), else the payload itself
            # (synthetic tapes without payload_hash — small, still detects any
            # raw revision). A value-irrelevant payload change must move the
            # per-feature lineage without fabricating a new state identity.
            inp = sha1_hex([(b.event_id, b.payload.get('payload_hash', b.payload))
                            for b in consumed]) if consumed else ''
            features[f'{sym}.{name}'] = FeatureValue(
                f'{sym}.{name}', value, 'float', feature_version,
                avail if value is not None else closed[-1].available_time,
                quality=quality, null_reason=null_reason,
                group=FEATURE_TO_GROUP.get(name, 'raw'),
                input_lineage_hash=inp, calculation_time=calc)

        add('close', closes[-1], [closed[-1]])
        add('prior_high', max(highs[:-1]) if len(highs) > 1 else None, closed[:-1])
        add('prior_low', min(lows[:-1]) if len(lows) > 1 else None, closed[:-1])
        # The EMA series are computed ONCE and shared by the trend features and
        # the per-bar history tuples (previously computed twice per state).
        fast_series = _ema(closes, 5)
        slow_series = _ema(closes, 20)
        if len(closes) >= 20:
            add('ema_fast', fast_series[-1], closed)
            add('ema_slow', slow_series[-1], closed)
            add('atr', sum(h - l for h, l in zip(highs[-14:], lows[-14:])) / 14,
                closed[-14:])
        # D-026 history feature group: last 32 closed bars as a tuple of
        # (event_id, open, high, low, close, ema_fast, ema_slow), oldest first,
        # per-bar EMAs over the full close series. This is the anchor scan the
        # pilots use to find setup_anchor_event_id (CANDIDATE_LIFECYCLE_SPEC 1).
        if closed:
            window = closed[-32:]
            hist = tuple(
                (b.event_id, float(b.payload['open']), float(b.payload['high']),
                 float(b.payload['low']), float(b.payload['close']),
                 fast_series[i + len(closed) - len(window)],
                 slow_series[i + len(closed) - len(window)])
                for i, b in enumerate(window))
            features[f'{sym}.history'] = FeatureValue(
                f'{sym}.history', hist, 'history', 'v2',
                closed[-1].available_time, quality='COMPLETE', group='history',
                input_lineage_hash=sha1_hex(
                    [(b.event_id, b.payload.get('payload_hash', b.payload))
                     for b in window]),
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
    provenance = {
        'raw_manifest_hash': sha1_hex(
            [(r.event_id, r.payload.get('payload_hash', r.payload))
             for r in rows if r.channel == 'kline']),
        'feature_graph_version': FEATURE_GRAPH_VERSION,
        'code_version': _BUILDER_SRC_HASH,
    }
    return MarketState(
        state_id=sha1_hex((as_of, universe, lineage)),
        as_of=as_of, universe=universe, features=features,
        lineage_hash=lineage, quality=quality, provenance=provenance)
