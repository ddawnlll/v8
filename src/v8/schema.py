"""Canonical record schemas for the V8 vertical slice.

All times are integer nanoseconds since the Unix epoch. Nothing here may
depend on the wall clock: determinism requires event time, never NOW()
(PERSISTENCE_REPLAY_SPEC section 4).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


def sha1_hex(obj: object) -> str:
    """Canonical sha1 of any JSON-serializable object (sort_keys, compact)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha1(canonical.encode('utf-8')).hexdigest()


_ASDICT_FIELD_CACHE: dict[type, tuple[str, ...]] = {}


def _asdict_fast(obj: object) -> object:
    """A `dataclasses.asdict` equivalent for the v8 record dataclasses, without
    the per-call `fields()` introspection and deepcopy machinery.

    The stored JSON is produced with `sort_keys=True`, and `sha1_hex` sorts
    too, so the conversion must agree with asdict on VALUES only (key order is
    irrelevant). Every field type in these records is an immutable scalar,
    a dict, a tuple, a list, or a nested record — all handled here. A dataclass
    instance not yet seen caches its field list once (module-level, keyed by
    type). Returns asdict-identical values for every record type the lab
    appends (pinned by tests/test_record_dict_fast.py).
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _asdict_fast(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        # CPython 3.14 dataclasses.asdict recurses INTO tuples but keeps them
        # tuples (it stopped converting tuples to lists); mirror that exactly
        # so `_asdict_fast(rec) == asdict(rec)` holds field-for-field.
        return tuple(_asdict_fast(v) for v in obj)
    if isinstance(obj, list):
        return [_asdict_fast(v) for v in obj]
    typ = type(obj)
    fs = _ASDICT_FIELD_CACHE.get(typ)
    if fs is None:
        dfields = getattr(typ, '__dataclass_fields__', None)
        if dfields is None:
            return obj                     # not a v8 record — pass through
        fs = tuple(dfields)
        _ASDICT_FIELD_CACHE[typ] = fs
    return {name: _asdict_fast(getattr(obj, name)) for name in fs}


def record_dict(rec: dataclass, source: str,
                event_id: str | None = None) -> dict:
    """Dataclass -> appendable log record with provenance and dedup key.

    `event_id` overrides the auto key. For records whose identity is derived
    elsewhere (a MarketState is keyed by its own `state_id`), passing it here
    skips the `sha1_hex(d)` of the full record that the caller would otherwise
    discard — a full json.dumps of a ~70-feature state per bar (profiled as a
    large share of `sha1_hex` total time).
    """
    d = _asdict_fast(rec)
    assert isinstance(d, dict)
    d['source'] = source
    if event_id is not None:
        d['event_id'] = event_id
    else:
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
    'volatility': {'requires': ('raw',), 'features': (
        'atr', 'bb_mid', 'bb_upper', 'bb_lower', 'bb_pct_b', 'bb_bandwidth',
        'atr_locational', 'atr_filtered_2sigma', 'atr_2sigma_active',
        'keltner_u', 'keltner_l', 'starc_u', 'starc_l', 'atr_trend_phase')},
    'location': {'requires': ('raw',), 'features': (
        'prior_high', 'prior_low',
        'swing_high_5', 'swing_high_10', 'swing_high_20',
        'swing_low_5', 'swing_low_10', 'swing_low_20',
        'window_high_10', 'window_low_10', 'window_high_20', 'window_low_20',
        'window_high_50', 'window_low_50',
        'range_height_10', 'range_height_20', 'range_height_50',
        'fib_levels', 'pivot_points_day', 'consolidation_range', 'gap_levels',
        'atr_band_stop')},
    'candle_shape': {'requires': ('raw',), 'features': (
        'real_body', 'body_range_ratio', 'upper_shadow', 'lower_shadow',
        'close_position', 'inside_bar', 'outside_bar', 'gap_size', 'gap_dir')},
    'oscillator': {'requires': ('raw',), 'features': (
        'rsi14', 'stoch_k', 'stoch_d', 'stochrsi', 'cci20', 'macd',
        'macd_signal', 'macd_hist', 'mom_14', 'roc_14', 'adx14',
        'osc_obos_quantile')},
    'participation': {'requires': ('raw',), 'features': (
        'volume', 'vol_zscore', 'vol_min_proximity', 'vol_smooth_ma', 'obv',
        'adl', 'cmf_20', 'vwap', 'bar_class')},
    'session': {'requires': ('raw',), 'features': (
        'hour_of_day_utc', 'impulsive_window', 'bar_of_session', 'day_index')},
    'positioning': {'requires': ('raw',), 'features': (
        'funding_rate', 'open_interest', 'long_short_skew')},
    'response': {'requires': ('trend', 'volatility', 'location', 'participation'),
                 'features': ()},
    'history': {'requires': ('trend', 'volatility'), 'features': ('history',)},
}

FEATURE_TO_GROUP: dict[str, str] = {
    name: group for group, spec in FEATURE_GROUPS.items() for name in spec['features']
}

# The feature graph is itself a versioned artifact: any change to the group
# table, a group's `requires`, or the feature membership re-versions the
# graph. It is surfaced in every MarketState.provenance so a consumer can
# verify the exact graph that produced a state (MARKET_STATE_CONTRACT 2;
# DATASET_SPEC 1).
FEATURE_GRAPH_VERSION = sha1_hex(FEATURE_GROUPS)


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
    # Per-feature input lineage (MARKET_STATE_CONTRACT 2): a hash of the
    # (event_id, payload_hash) identities of the raw rows that produced this
    # feature. A revised raw row changes it even when the emitted value
    # round-trips, so per-feature provenance is auditable independently of the
    # state-level lineage_hash (which binds semantic values). Metadata only —
    # it does not join the lineage/state identity hashes.
    input_lineage_hash: str = ''
    # The clock at which this feature became computable (the latest consumed
    # input row's available_time; MARKET_STATE_CONTRACT 2).
    calculation_time: int = 0


@dataclass(frozen=True)
class MarketState:
    """Immutable context snapshot for a single decision clock D."""
    state_id: str
    as_of: int
    universe: tuple[str, ...]
    features: dict[str, FeatureValue]
    lineage_hash: str
    quality: str = 'COMPLETE'
    # Provenance (MARKET_STATE_CONTRACT 2; DATASET_SPEC 1): the raw-input
    # manifest the state was built from, the feature-graph version that
    # produced it, and the builder code version. Audit metadata — not part of
    # the lineage/state identity hashes.
    provenance: dict | None = None


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
    # RM-01 size primitive: position size in units of one standard position.
    # Heat (D-023) is `size * stop_r`, so at size=1.0, stop_r=1.0 the heat
    # formula is byte-identical to the pre-size 1R gate. `size` is a declared
    # geometry policy (fixed-fractional; RM-15 — never compounding); the
    # RiskGate drawdown ladder (O-016, equity.RiskState) scales the EFFECTIVE
    # size at admission, which is what the executed OpenPosition records.
    # `risk_geometry` may additionally carry `risk_frac` (fraction of the
    # entry price that is one R — the D-028 risk-unit fallback) and
    # `risk_per_trade` (fraction of account equity risked per 1R at size 1.0);
    # the account-level risk_per_trade lives on ExperimentManifest and wins.
    #
    # EXEC-1..6 (O-013) declared management keys — all optional; the default
    # geometry is unchanged. They are pure functions of excursion + frozen
    # keys, never fitted:
    # - `breakeven_roll_at_mfe_r` (+ `breakeven_margin_r`, default
    #   round_trip_cost_r): one-shot roll of the effective stop to entry +/-
    #   margin once mfe_r reaches the threshold (EX-01). Endpoint stays STOP.
    # - `trail_stop_atr`: chandelier trail — the effective stop ratchets to
    #   k*ATR behind the extreme every bar (EX-05). Endpoint stays STOP.
    # - `scale_out_ratio` (>0 enables) + `scale_out_at_mfe_r`: one-shot partial
    #   close of fraction f = stop_r/(stop_r+target_r) at bar close; the
    #   remainder continues. NON-TERMINAL — a PARTIAL_EXIT PositionAction, never
    #   an endpoint and never an outcome (EX-02/04).
    # - `time_exit_bars`: distinct endpoint TIME_EXIT at bar close (EX-09/12).
    # - `pyramid_add_rules`: declared but P2 — pyramiding is OFF; declaring it
    #   fails closed (EX-03; `simulator.midpoint_stop` is the tested primitive).
    # - `limit_price`: the barrier for FILL_AT_LIMIT (EXEC-4, EX-11).
    #
    # ENTRY TRIGGER CONTRACT (issue #62, #67): the entry is a distinct event
    # from the setup. An expert that declares `trigger_ref` (an absolute price,
    # frozen at detection) enters only when the book's close-confirmation is
    # observed: `trigger_side` = 'CLOSE_ABOVE' -> a LONG on a CLOSE above the
    # trigger, 'CLOSE_BELOW' -> a SHORT on a CLOSE below it. The lab's PHASE 2
    # evaluates this predicate before PENDING -> TRIGGERED; a candidate whose
    # trigger has not fired stays PENDING until it fires, invalidates, or the
    # epilogue expires it. `trigger_side` is optional — absent, it is derived
    # from direction. An expert with no trigger level declares
    # 'entry': 'NEXT_BAR_CLOSE' and keeps the unconditional next-bar-close
    # entry (no trigger_ref -> no predicate to wait on). Related: `stop_ref`
    # (an absolute structural stop price; the simulator uses it as the static
    # stop when declared, issue #63).
    size: float = 1.0


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
    #                             | TIME_EXIT | INVALIDATED_BEFORE_TRIGGER
    #                             (PARTIAL_EXIT is NOT an endpoint — it is a
    #                             non-terminal lifecycle PositionAction, EX-02)
    net_r: float
    label_status: str           # MATURE | RIGHT_CENSORED | NOT_EXECUTED
    simulator_hash: str
    # DATASET_SPEC section 4.5: the decision clock at which this outcome became
    # knowable (exit bar's available_time; the last tape bar for RIGHT_CENSORED;
    # the invalidation clock for INVALIDATED_BEFORE_TRIGGER). Training must
    # refuse a label whose label_available_time overlaps its validation window;
    # a consumer reading the materialized view without this field cannot detect
    # dev/OOS overlap. 0 = time-less path (no venue clock).
    label_available_time: int = 0
    mae_r: float = 0.0          # max adverse excursion, R (>= 0)
    mfe_r: float = 0.0          # max favourable excursion, R (>= 0)
    ambiguous_bars: int = 0     # bars touching both barriers (STOP_FIRST applied)
    # D-045 (detrended null): `net_r` alone cannot be re-centered on a
    # same-exposure passive benchmark, because the R denominator is not
    # recoverable downstream — `simulator.risk_unit` falls back to
    # `entry_price * risk_frac` when a draft declares no `atr_ref`, so the
    # unit depends on the fill. Recomputing either outside the simulator
    # would be the second copy of the formula the run() docstring forbids.
    # These are recorded by the simulator at the fill it actually used.
    entry_price: float = 0.0        # executed entry fill; 0.0 = never entered
    risk_unit_price: float = 0.0    # price distance of one R at that fill
    # Passive entry->exit close move in R, direction-FREE (unsigned by
    # `direction`): what the instrument did over the holding window, with no
    # barrier path and no cost. Signing it is the caller's job, which is what
    # lets a permutation test re-pair positions with moves (METH-3 / EV G-03
    # prerequisite: "net-R alone is insufficient"). Recorded now so that test
    # does not force a second simulator hash bump.
    market_move_r: float = 0.0


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
    # Optional bps-of-notional cost. When set it REPLACES round_trip_cost_r in
    # the simulator: cost_R = (bps/1e4) * entry_price / risk_unit. The flat-R
    # form is invariant to the R unit, so an R-widening experiment cannot move
    # it; the bps form is what a venue actually charges. None = flat-R
    # (byte-identical to every pre-existing run).
    round_trip_cost_bps: float | None = None
    # Fill policy (SIMULATION_TRUTH_SPEC): FILL_AT_BAR_CLOSE is the locked
    # baseline (entry at next-bar close). FILL_AT_LIMIT (EXEC-4, EX-11) is a
    # barrier entry: the order rests at the draft's declared
    # risk_geometry['limit_price'] and fills when a bar's range trades through
    # it (fill = the limit exactly); the entry bar is inspected for a FILL only,
    # never for exits; an order that never fills never enters (NOT_EXECUTED).
    # Anything outside SUPPORTED_FILL_POLICIES fails closed.
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
    # exceeds max_bar_range_frac, when StateQuality == DEGRADED at decision
    # time, or when the entry bar closes within funding_window_bars of a
    # funding boundary.
    #
    # Named for what it measures: (high-low)/close is the entry bar's INTRABAR
    # RANGE, not a bid-ask spread. It was called max_spread_frac until
    # 2026-08-04; a real spread needs depth data the tape does not carry, so
    # this is a volatility/illiquidity proxy and must not be read as execution
    # cost. The 0.05 default is declared, not fitted (D-036) — but it is also
    # not derived, and its firing rate on the declared dev window has never
    # been measured, so whether the veto does anything is unknown (O-019).
    max_bar_range_frac: float = 0.05
    funding_window_bars: int = 1
    authority_receipt: str | None = None
    # RM-02: fraction of account equity risked per 1R position at size 1.0
    # (1R = risk_per_trade x initial equity). Makes R interpretable as % of
    # account and drives the trade-unit budget (RM-07: trade_units =
    # 100/risk_per_trade) and the O-016 equity curve (equity.py). Frozen
    # manifest constant, declared pre-holdout — never fitted.
    risk_per_trade: float = 0.01
    # RM-08: minimum executed-episode adequacy bar for a positive verdict
    # annotation. The book's 300-500 trade floor, declared pre-holdout; the
    # prereg §12 n_f >= 30 stays the statistical gate — this is an
    # annotation (NO_ECONOMIC_CLAIM note below the bar), never a hard fail.
    min_trades: int = 300


@dataclass(frozen=True)
class LabReport:
    """Hash-bound run report; the economic verdict stays blocked without an
    authority receipt (NO_ECONOMIC_CLAIM), and D-027 attribution-validity
    failures surface as ATTRIBUTION_UNSAFE_* verdicts when a receipt is
    present."""
    experiment_id: str
    code_hash: str
    data_hash: str
    candidate_count: int
    terminal_distribution: dict
    ledger_hash: str
    verdict: str
    exposure_conflicts: int = 0
    # Zero-trade provenance: candidate_count=0 collapses NO_SETUP vs
    # NO_TRIGGER vs ALL_INVALIDATED vs ALL_REJECTED vs DEGENERATE tape.
    # These fields surface the causes so a consumer never misreads 'no trades'
    # as 'no setups' (or vice versa). Not part of any hash (report-only).
    evaluation_distribution: dict | None = None  # decision -> count (NO_SETUP/...)
    data_invalid: bool = False                   # True when no usable bar drove a state
    # Rejection provenance: terminal_distribution collapses every rejection
    # into one REJECTED bucket; this breaks it down by reason code
    # (TRADABILITY_MASK_VETO vs PORTFOLIO_HEAT_EXCEEDED vs excess_cost ...).
    rejection_distribution: dict | None = None
    # D-027 attribution-validity gating (prereg §15; thresholds ratified
    # pre-holdout O-017, fixed forever): the executed population vs the
    # portfolio-state-rejected (EXISTING_EXPOSURE_CONFLICT /
    # PORTFOLIO_HEAT_EXCEEDED) counterfactual population. Both statistics are
    # computed and reported even when the verdict is NO_ECONOMIC_CLAIM (no
    # authority receipt — authority blocks first); they gate the economic
    # verdict only when a receipt is present. execution_share/divergence_ks
    # are None when no candidate exists; divergence_ks is 0.0 when the
    # rejected sample is empty (no divergence evidence). Not part of any hash
    # (report-only, derived from ledgers already inside ledger_hash).
    n_executed: int = 0
    n_portfolio_rejected: int = 0
    execution_share: float | None = None
    divergence_ks: float | None = None
    # Tooling identity: the tape-building/audit code (tools/*.py) is outside
    # the decision-path code hash; its source hash is surfaced here so a
    # semantic change in the tape builder is at least visible in the report.
    tooling_hash: str = ''
    # D-018/D-023 risk-admission identity: the effective RiskGate
    # configuration (type + heat caps + clusters) that actually admitted /
    # rejected candidates. A custom gate must be distinguishable from the
    # ratified default — two runs with different admission policies must never
    # be byte-identical in every hash. The same value is bound into
    # ledger_hash (risk_config_hash); this field is the report-side copy, so a
    # consumer can see which gate ran without re-deriving it from the ledger.
    risk_gate_hash: str = ''
    # --- Risk/sizing diagnostics (RM-01..19; O-016) -------------------------
    # All report-only, derived deterministically from the executed-outcome
    # ledger and the equity feed (lab.py + equity.py). Never bound into any
    # hash. `economic_note` carries the NO_ECONOMIC_CLAIM annotations for the
    # RM-07 trade-unit budget and the RM-08 min_trades bar when the executed
    # episode count is below them — a note, not a hard fail, and never a
    # change to the D-027 `verdict` string.
    size_scheme: str = 'fixed_fractional'      # sizing policy that ran (RM-15)
    risk_per_trade: float | None = None        # manifest: fraction of equity risked per 1R
    min_trades: int | None = None              # manifest: RM-08 adequacy bar (default 300)
    trade_units: float | None = None           # 100/risk_per_trade (RM-07 budget)
    final_equity: float | None = None          # normalized equity after the last episode
    max_drawdown: float | None = None          # deepest peak-to-trough on the equity curve (<= 0)
    drawdown_sized_episodes: int = 0           # episodes admitted under a drawdown band
    risk_of_ruin: float | None = None          # MC P(ruin) over the realized sequence
    profit_factor: float | None = None         # gross win / gross |loss| over executed net_r
    # RM-11 executed geometry: (target_r, stop_r) per executed episode, in
    # declaration order. Report-only; surfaces what w_min actually averaged
    # over, so a consumer can recompute the breakeven win rate without
    # re-deriving geometry (structural stops make it non-uniform, D-058).
    executed_geometry: list = field(default_factory=list)
    w_min: float | None = None                 # spread-adjusted breakeven win rate 1/(1+R/r')
    worst_case_r: float | None = None          # worst realized single-episode net_r (RM-10)
    worst_case_portfolio_r: float | None = None  # theoretical: -max_heat (all stops at once)
    economic_note: str | None = None           # NO_ECONOMIC_CLAIM annotation when below bars
