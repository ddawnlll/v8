"""Canonical record schemas for the V8 vertical slice.

All times are integer nanoseconds since the Unix epoch. Nothing here may
depend on the wall clock: determinism requires event time, never NOW()
(PERSISTENCE_REPLAY_SPEC section 4).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict


def sha1_hex(obj: object) -> str:
    """Canonical sha1 of any JSON-serializable object (sort_keys, compact)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha1(canonical.encode('utf-8')).hexdigest()


def record_dict(rec: dataclass, source: str) -> dict:
    """Dataclass -> appendable log record with provenance and dedup key."""
    d = asdict(rec)
    d['source'] = source
    d['event_id'] = f"{d.get('candidate_id', d.get('event_id', sha1_hex(d)))}"
    return d


@dataclass(frozen=True)
class TapeRow:
    """One immutable raw market fact with three distinct clocks.

    event_time / available_time / ingested_time are never collapsed
    (FEED_INGESTION_SPEC section 2; MARKET_STATE_CONTRACT section 1).
    """
    source: str
    channel: str
    instrument: str
    event_time: int
    available_time: int
    ingested_time: int
    venue_sequence: int
    event_id: str
    payload: dict = field(default_factory=dict)


# Feature-group ontology (MARKET_STATE_CONTRACT section 2; EXPERT_PROTOCOL
# section 1). The frozen vocabulary is the five Phase-2 ontology groups plus
# the base bar-data layer (`raw`) and the D-026 `history` group. `requires`
# declares which other groups must be present for this group's features to be
# meaningful; it is a frozen declaration, not a per-state guarantee (a short
# tape can emit `history` before the 20-bar EMA warmup has produced `trend`,
# which is allowed).
FEATURE_GROUPS: dict[str, dict] = {
    'raw': {'requires': (), 'features': ('close',)},
    'trend': {'requires': ('raw',), 'features': ('ema_fast', 'ema_slow')},
    'volatility': {'requires': ('raw',), 'features': ('atr',)},
    'location': {'requires': ('raw',), 'features': ('prior_high', 'prior_low')},
    'participation': {'requires': ('raw',), 'features': ()},
    'response': {'requires': ('trend', 'volatility', 'location', 'participation'),
                 'features': ()},
    'history': {'requires': ('trend', 'volatility'), 'features': ('history',)},
}

FEATURE_TO_GROUP: dict[str, str] = {
    name: group for group, spec in FEATURE_GROUPS.items() for name in spec['features']
}


@dataclass(frozen=True)
class FeatureValue:
    name: str
    # `tuple | list` covers structured feature groups (e.g. `{sym}.history`,
    # a tuple of per-bar tuples); JSON-serializable for canonical hashing.
    value: float | str | None | tuple | list
    dtype: str
    feature_version: str
    max_input_available_time: int
    quality: str = 'COMPLETE'
    null_reason: str | None = None
    # Phase-2: the feature-group tag (FEATURE_GROUPS above). Every emitted
    # feature carries it and it joins the lineage hash, so a re-tag or
    # re-version changes every dependent hash (MARKET_STATE_CONTRACT 2).
    group: str = ''


@dataclass(frozen=True)
class MarketState:
    """Immutable context snapshot for a single decision clock D."""
    state_id: str
    as_of: int
    universe: tuple[str, ...]
    features: dict[str, FeatureValue]
    lineage_hash: str
    quality: str = 'COMPLETE'


@dataclass(frozen=True)
class ExpertEvaluation:
    """Stored per-evaluation record; None is not an auditable result."""
    expert_id: str
    version: str
    state_id: str
    applicability: str          # APPLICABLE | NOT_APPLICABLE
    decision: str               # CANDIDATE | NO_SETUP | NO_HABITAT
    knowledge_time: int
    draft: CandidateDraft | None = None


@dataclass(frozen=True)
class CandidateDraft:
    """A conditional trade hypothesis; never an order (EXPERT_PROTOCOL)."""
    expert_id: str
    expert_version: str
    instrument: str
    direction: str              # LONG | SHORT
    setup_fingerprint: str
    risk_geometry: dict
    birth_time: int
    # D-026: the event that created the setup (first closed bar of the current
    # consecutive run where the Expert's predicate holds), never the decision
    # clock. This is the episode-identity primitive (CANDIDATE_LIFECYCLE_SPEC
    # section 1). Empty string only for drafts that never enter the registry.
    setup_anchor_event_id: str = ''


@dataclass(frozen=True)
class CandidateTransition:
    """One legal, append-only state change (CANDIDATE_LIFECYCLE_SPEC section 2)."""
    candidate_id: str
    sequence: int
    from_state: str | None
    to_state: str
    reason_code: str
    knowledge_time: int
    event_hash: str


@dataclass(frozen=True)
class CounterfactualOutcome:
    """Deterministic simulator result; never an observed fill.

    `net_r`, `mae_r` and `mfe_r` are R-multiples (see `simulator.risk_unit`),
    never fractional price returns. Excursions are retained because path
    magnitude was the only quantity V7 measured as materially predictable
    (PROJECT_EVIDENCE_AUDIT); they are the input to O-013.
    """
    candidate_id: str
    horizon_bars: int
    endpoint: str               # TARGET | STOP | EXPIRY | THESIS_INVALIDATED
    #                             | INVALIDATED_BEFORE_TRIGGER
    net_r: float
    label_status: str           # MATURE | RIGHT_CENSORED | NOT_EXECUTED
    simulator_hash: str
    mae_r: float = 0.0          # max adverse excursion, R (>= 0)
    mfe_r: float = 0.0          # max favourable excursion, R (>= 0)
    ambiguous_bars: int = 0     # bars touching both barriers (STOP_FIRST applied)


@dataclass(frozen=True)
class ExperimentManifest:
    """Immutable run definition; binds code, data, universe and costs."""
    experiment_id: str
    code_hash: str
    data_hash: str
    universe: tuple[str, ...]
    start_ns: int
    end_ns: int
    interval: str = '1h'
    round_trip_cost_r: float = 0.07
    fill_policy: str = 'FILL_AT_BAR_CLOSE'
    # Versioned venue inputs (SIMULATION_TRUTH_SPEC 3-5): funding settles at
    # integer-hour UTC boundaries divisible by funding_hours, before any order
    # event of a bar whose decision clock crosses a boundary while a position
    # is held. 0.0 = no funding cost (numbers byte-identical to no-funding).
    funding_rate_r: float = 0.0
    funding_hours: int = 8
    # D-024 mechanical tradability mask (CANDIDATE_LIFECYCLE_SPEC section 6.3).
    # Frozen manifest constants — no fitting, no leakage, no learned component.
    # A candidate is vetoed at admission (TRADABILITY_MASK_VETO, kept
    # counterfactual NOT_EXECUTED) when the entry bar's (high-low)/close
    # exceeds max_spread_frac, when StateQuality == DEGRADED at decision time,
    # or when the entry bar closes within funding_window_bars of a funding
    # boundary.
    max_spread_frac: float = 0.05
    funding_window_bars: int = 1
    authority_receipt: str | None = None


@dataclass(frozen=True)
class LabReport:
    """Hash-bound run report; verdict stays blocked without an authority receipt."""
    experiment_id: str
    code_hash: str
    data_hash: str
    candidate_count: int
    terminal_distribution: dict
    ledger_hash: str
    verdict: str
    exposure_conflicts: int = 0
