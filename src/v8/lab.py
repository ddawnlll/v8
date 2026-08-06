"""Preregistered hypothesis-lab runner (HYPOTHESIS_LAB_PROTOCOL).

Replays the tape, builds MarketStates, evaluates self-gating experts, drives
the candidate lifecycle and the STEPPED execution ledger, computes
counterfactual outcomes for every candidate, and emits a hash-bound report.
An absent authority receipt blocks the economic verdict.

Per CANDIDATE_LIFECYCLE_SPEC section 6, attribution and execution are
separate paths: rejected candidates keep a batch counterfactual outcome
(label NOT_EXECUTED); accepted candidates live as OpenPositions across
decision clocks and are closed bar by bar through the canonical simulator.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, replace
from pathlib import Path

from .schema import (TapeRow, ExperimentManifest, LabReport, MarketState,
                     CounterfactualOutcome, record_dict, sha1_hex)
from .store import AppendOnlyLog
from .marketstate import build_state, build_multi_state, project_state
from .lifecycle import CandidateRegistry, episode_key, TERMINAL
from .simulator import CanonicalSimulator, OpenPosition, risk_unit
from .risk import RiskGate, tradability_mask_veto, TRADABILITY_MASK_VETO
from .equity import RiskState, trade_units_for

# D-024 funding-window veto measures bars from the entry bar's close time to
# the next boundary; the canonical slice tape is 1h bars (synth.py), so
# funding_hours (in hours) times this interval is the boundary period.
_INTERVAL_NS = {'1m': 60_000_000_000, '1h': 3_600_000_000_000,
                '4h': 14_400_000_000_000, '1d': 86_400_000_000_000}

# Named source for the Phase-2 excess-cost gate (was an undocumented 0.10
# literal): a manifest cost at/above this rejects every triggered candidate as
# NOT_EXECUTED. This is the hypothesis-lab protocol's cost gate, not a
# per-candidate economic rule; kept here so the constant is auditable.
EXCESS_COST_THRESHOLD_R = 0.10

# D-027 attribution-validity thresholds (prereg §15): ratified pre-holdout
# (O-017, 2026-08-01) and fixed forever — never re-set after a verdict.
# execution_share floor 0.25; population-divergence two-sample KS <= 0.20.
EXECUTION_SHARE_FLOOR = 0.25
POPULATION_DIVERGENCE_KS_MAX = 0.20

# RM-17: the book's profit-factor band for an effective system, recorded as an
# external benchmark in the report. Report diagnostic only — the verdict stays
# the prereg §11 R-based gates (PF ignores per-outcome cost by construction).
PROFIT_FACTOR_BAND = (1.5, 2.0)

# Sizing scheme name reported in LabReport (RM-15: fixed-fractional of the
# initial account, never compounding; the O-016 drawdown ladder is layered on
# top via equity.RiskState).
SIZE_SCHEME = 'fixed_fractional'


def _d027_verdict(authority_receipt: str | None,
                  execution_share: float | None,
                  divergence_ks: float | None) -> str:
    """D-027 verdict: authority blocks first (HYPOTHESIS_LAB_PROTOCOL);
    with a receipt the ratified attribution-validity gates decide (prereg
    §15; thresholds O-017, never re-set after a verdict)."""
    if authority_receipt is None:
        return 'NO_ECONOMIC_CLAIM'
    if execution_share is not None and execution_share < EXECUTION_SHARE_FLOOR:
        return 'ATTRIBUTION_UNSAFE_LOW_COVERAGE'
    if divergence_ks is not None and divergence_ks > POPULATION_DIVERGENCE_KS_MAX:
        return 'ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE'
    return 'CERTIFIED_AVAILABLE'


def _two_sample_ks(xs: list[float], ys: list[float]) -> float:
    """Two-sample Kolmogorov-Smirnov D = max_x |F1(x) - F2(x)| (stdlib-pure;
    scipy/numpy are banned in the decision path, D-031). The O-017 calibration
    used numpy; this implementation must reproduce those numbers within
    tolerance — verified against the prereg §15 12-month diagnostics
    (execution_share 0.4576, KS 0.1044). An empty sample returns 1.0
    (maximal divergence — a population with no evidence cannot pass)."""
    if not xs or not ys:
        return 1.0
    xs, ys = sorted(xs), sorted(ys)
    nx, ny = len(xs), len(ys)
    i = j = 0
    d = 0.0
    for v in sorted(set(xs + ys)):
        while i < nx and xs[i] <= v:
            i += 1
        while j < ny and ys[j] <= v:
            j += 1
        d = max(d, abs(i / nx - j / ny))
    return d


def _code_hash() -> str:
    # The decision path is src/v8/ MINUS simtruth/ (vendored V7, engineering
    # only — nothing imports it, so its bytes can never change decision-path
    # output; binding them would invalidate every pinned manifest on a
    # vendored edit for a byte-identical decision path).
    base = Path(__file__).resolve().parent
    files = {str(p.relative_to(base)): p.read_bytes().hex()
             for p in sorted(base.rglob('*.py'))
             if 'simtruth' not in p.parts}
    return sha1_hex(files)


def _tooling_hash() -> str:
    """Hash of the tape-building/audit tooling (tools/*.py), which sits OUTSIDE
    the decision-path code hash. Surfaced in the LabReport so a semantic change
    in the tape builder is visible even when the tape content is unchanged."""
    tools = Path(__file__).resolve().parents[2] / 'tools'
    files = {str(p.relative_to(tools)): p.read_bytes().hex()
             for p in sorted(tools.rglob('*.py'))}
    return sha1_hex(files)


def _validate_tape_rows(rows) -> None:
    """Fail closed on a tape the decision path cannot trust.

    The monitoring tools (monitor_tape/audit_tape) audit the tape, but a
    corrupted tape reaching the lab directly must not silently change results:
    a NaN close flows into every EMA/ATR/state hash and quality stays COMPLETE
    (mutation-campaign requirement). OHLC invariant violations currently fail
    downstream with a misleading risk_unit error; this gives the real reason.
    """
    for r in rows:
        if r.channel == 'kline':
            p = r.payload
            try:
                o, h, l, c = (float(p[f]) for f in ('open', 'high', 'low', 'close'))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f'kline {r.event_id}: missing or non-numeric OHLC') from exc
            if not all(math.isfinite(x) for x in (o, h, l, c)):
                raise ValueError(f'kline {r.event_id}: non-finite OHLC')
            if min(o, h, l, c) <= 0:
                raise ValueError(f'kline {r.event_id}: non-positive OHLC '
                                 f'({o}, {h}, {l}, {c})')
            if h < max(o, c) or l > min(o, c) or h < l:
                raise ValueError(f'kline {r.event_id}: OHLC invariant violation '
                                 f'(high={h} low={l} open={o} close={c})')
            vol = p.get('volume')
            if vol is not None:
                v = float(vol)
                if not math.isfinite(v) or v < 0:
                    raise ValueError(f'kline {r.event_id}: negative or non-finite volume')
        elif r.channel == 'funding':
            p = r.payload
            try:
                rate = float(p['funding_rate'])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f'funding {r.event_id}: missing or non-numeric rate') from exc
            if not math.isfinite(rate):
                raise ValueError(f'funding {r.event_id}: non-finite rate')
            if abs(rate) > 0.10:
                raise ValueError(f'funding {r.event_id}: implausible rate {rate}')


def _geometry_version(draft) -> str:
    """Structural risk geometry only: `atr_ref` and `prior_high_ref` are
    data-dependent (they move with the market) and must not be part of episode
    identity — a stable setup would otherwise change key across decision clocks
    and disable deduplication."""
    structural = {k: v for k, v in draft.risk_geometry.items()
                  if k not in ('atr_ref', 'prior_high_ref', 'prior_low_ref')}
    return sha1_hex(structural)


def _view_for(expert, state, base_interval: str,
              known_intervals: frozenset[str]):
    """The MarketState `expert` declared, projected from the canonical state.

    An Expert that declares no feature groups (the base contract, and the
    synthetic Experts in the test fixtures) receives the state untouched, so
    D-053 adds nothing to a run whose Experts made no declaration.
    """
    groups = getattr(expert, 'requires', ())
    if not groups:
        return state
    intervals = expert.declared_intervals(base_interval)
    return project_state(state, groups=groups, intervals=intervals,
                         base_interval=base_interval,
                         known_intervals=known_intervals,
                         depths={tf: expert.declared_depth(tf)
                                 for tf in intervals})


class Lab:
    """One store directory = one immutable run's evidence."""

    def __init__(self, store_dir: str | Path, universe: tuple[str, ...] = ('SOLUSDT',)):
        self.dir = Path(store_dir)
        self.tape_log = AppendOnlyLog(self.dir / 'tape.jsonl')
        self.candidates = AppendOnlyLog(self.dir / 'candidates.jsonl')
        self.evaluations = AppendOnlyLog(self.dir / 'evaluations.jsonl')
        self.outcomes = AppendOnlyLog(self.dir / 'outcomes.jsonl')
        # Decision ledger: every MarketState built at a decision clock, one
        # record per bar (DATASET_SPEC section 1 layer 2; the input to the
        # DATASET_SPEC section 5 market_states materialization).
        self.states = AppendOnlyLog(self.dir / 'states.jsonl')
        self.universe = universe
        self.registry = CandidateRegistry(self.candidates)

    def ingest(self, rows: list[TapeRow]) -> None:
        _validate_tape_rows(rows)
        for r in rows:
            self.tape_log.append(record_dict(r, source=r.source))

    def _record_outcome(self, candidate_id: str, endpoint: str, net_r: float,
                        label_status: str, simulator_hash: str,
                        horizon_bars: int = 0, label_available_time: int = 0,
                        mae_r: float = 0.0, mfe_r: float = 0.0,
                        ambiguous_bars: int = 0, entry_price: float = 0.0,
                        risk_unit_price: float = 0.0,
                        market_move_r: float = 0.0) -> None:
        """The one place an outcome record is written.

        D-045: the executed path does NOT go through `simulator.run` — it
        steps positions bar by bar and closes them here — so the detrending
        inputs have to be supplied at each entered call site. They stay 0.0
        for candidates that never entered, which is what
        `passive_benchmark_r` fails closed on rather than centering a
        position that was never held.
        """
        out = CounterfactualOutcome(candidate_id=candidate_id, horizon_bars=horizon_bars,
                                    endpoint=endpoint, net_r=net_r,
                                    label_status=label_status,
                                    simulator_hash=simulator_hash,
                                    label_available_time=label_available_time,
                                    mae_r=mae_r, mfe_r=mfe_r,
                                    ambiguous_bars=ambiguous_bars,
                                    entry_price=entry_price,
                                    risk_unit_price=risk_unit_price,
                                    market_move_r=market_move_r)
        self.outcomes.append(record_dict(out, source='simulator'))

    @staticmethod
    def feasibility(expert, base_interval: str, n_base_bars: int) -> tuple[str, str]:
        """Can this tape serve what this Expert declared? (D-053)

        Returns ('EVALUABLE', '') or ('NOT_EVALUABLE', reason). The gate exists
        because an unservable Expert and a signal-less one are otherwise
        indistinguishable in the report: `donchian_breakout` produced 384
        triggers and 0 executions, and read as "no edge" when the truth was
        "never measured". A refused declaration must say so in words.
        """
        from .interval import bars_per, is_derivable

        for tf in expert.declared_intervals(base_interval):
            try:
                if not is_derivable(base_interval, tf):
                    return ('NOT_EVALUABLE',
                            f'{tf} is not an integer multiple of the base '
                            f'interval {base_interval}; aggregation is up-only')
            except ValueError as exc:
                return ('NOT_EVALUABLE', str(exc))
            need = expert.declared_depth(tf) * bars_per(base_interval, tf)
            if need > n_base_bars:
                return ('NOT_EVALUABLE',
                        f'depth {expert.declared_depth(tf)} on {tf} needs '
                        f'{need} base bars, tape has {n_base_bars}')
        return ('EVALUABLE', '')

    def run(self, manifest: ExperimentManifest, experts: list,
            risk_gate: RiskGate | None = None) -> LabReport:
        # One store directory = one immutable run's evidence. A second run on
        # the same store is NOT idempotent: the registry replays the prior
        # run's DETECTED keys, so every first detection becomes a NEW
        # suppressed_duplicate row and the ledger hash silently changes for
        # identical (tape, manifest, code). Fail closed instead of polluting
        # the evidence.
        if self.states.read() or self.candidates.read() \
                or self.outcomes.read() or self.evaluations.read():
            raise ValueError(
                'store already contains a run; one store directory = one '
                "immutable run's evidence (use a fresh store dir)")
        # O-016 equity wiring (RM-06): the composition root builds the
        # deterministic RiskState from the frozen manifest risk_per_trade and
        # attaches it to the gate. The lab feeds it realized net_r in episode
        # order at every position close; RiskGate.admit reads its drawdown
        # multipliers for sizing (heat is invariant, so admission is
        # byte-identical either way). A caller-provided gate without equity
        # gets the same state — there is one equity path per run.
        equity = RiskState(risk_per_trade=manifest.risk_per_trade)
        gate = risk_gate or RiskGate(equity=equity)
        if gate.equity is None:
            gate.equity = equity
        # Risk admission is a run-configuration input, not a code constant: a
        # custom gate (heat caps, clusters, equity ladder) must be bound into
        # the ledger and surfaced, or two runs with different admission/sizing
        # policies would be byte-identical in every hash whenever no cap is
        # actually breached.
        _equity = getattr(gate, 'equity', None)
        equity_config = None if _equity is None else (
            type(_equity).__name__,
            getattr(_equity, 'risk_per_trade', None),
            tuple(getattr(_equity, 'bands', ()) or ()),
            getattr(_equity, 'initial_equity', None),
        )
        risk_config = (type(gate).__module__, type(gate).__name__,
                       getattr(gate, 'max_heat', None),
                       getattr(gate, 'max_cluster_heat', None),
                       tuple(sorted((getattr(gate, 'clusters', {}) or {}).items())),
                       equity_config)
        risk_config_hash = sha1_hex(risk_config)
        by_expert = {ex.expert_id: ex for ex in experts}
        tape = self.tape_log.replay_tape()
        # Tape-driven funding schedule (D-041): every funding TapeRow is a
        # (boundary_time_ns, rate) pair, sorted by boundary time. Non-empty
        # when the tape carries the funding channel; the manifest scalar stays
        # as the no-funding-tape fallback.
        funding_schedule = tuple(
            (r.event_time, float(r.payload['funding_rate']))
            for r in sorted((r for r in tape if r.channel == 'funding'),
                            key=lambda r: r.event_time))
        sim = CanonicalSimulator(round_trip_cost_r=manifest.round_trip_cost_r,
                                 funding_rate_r=manifest.funding_rate_r,
                                 funding_hours=manifest.funding_hours,
                                 fill_policy=manifest.fill_policy,
                                 funding_schedule=funding_schedule)
        # Validate at the run boundary too: a tape written directly to the
        # store (bypassing ingest) must still fail closed on bad OHLC/volume.
        _validate_tape_rows(tape)
        # PIT consumption order: replay_tape's canonical order is
        # (event_time, available_time, venue_sequence), which is NOT guaranteed
        # available-monotonic when latencies are heterogeneous (a row with a
        # later event can become available earlier). Consuming in event order
        # would either silently SKIP a row that IS admissible at the decision
        # clock or feed build_state an unsorted batch (a wrong-state or a
        # misleading crash). Sort a stable copy by available_time for the bar
        # loop and the state accumulator; this is identical to replay order
        # whenever the two agree, and build_state validates that the batch it
        # receives is available-sorted.
        pit = sorted(tape, key=lambda r: r.available_time)
        # Only CLOSED klines drive the decision loop; an open (not-yet-closed)
        # kline must never feed entries, stops/targets, or invalidation with its
        # partial OHLC (FEED_INGESTION_SPEC section 3 — marketstate already
        # filters closed bars for features; the decision loop must too).
        bars = [r for r in pit if r.channel == 'kline'
                and r.payload.get('closed') is True]
        # The bar-driven loop indexes a single per-clock bar sequence and steps
        # positions on the current bar; a multi-instrument tape would silently
        # step a position on another instrument's OHLC. Fail closed until the
        # O-011 universe-extension gate is passed (state building handles
        # multi-symbol; the execution loop does not).
        instruments = {r.instrument for r in bars}
        if len(instruments) > 1:
            raise ValueError(
                'bar-driven loop does not yet support multi-instrument tapes '
                f'({sorted(instruments)}); run one symbol per store until the '
                'O-011 universe-extension gate is passed')
        # One decision clock per bar: two kline rows sharing available_time
        # would silently truncate the state/evaluation ledger via the store's
        # (source, event_id) dedup (DATASET_SPEC section 1: one state per clock).
        avail_clocks = [b.available_time for b in bars]
        if len(avail_clocks) != len(set(avail_clocks)):
            raise ValueError('duplicate decision clocks (available_time) in tape')
        # Last tape clock, needed by in-loop label_available_time fallbacks for
        # tape-end candidates (a candidate whose entry never happened).
        last_as_of = bars[-1].available_time if bars else 0
        pending: dict[str, dict] = {}            # cid -> draft/birth/entry info
        open_positions: dict[str, OpenPosition] = {}
        # available_time -> MarketState for this run, so the batch counterfactual
        # can evaluate the owning Expert's still_valid at each stepped clock.
        states_by_time: dict[int, MarketState] = {}
        conflicts = 0
        # RISK diagnostics (report-only): episodes admitted under a drawdown
        # band (O-016 firing count) and the executed geometry for the
        # spread-adjusted breakeven win rate (RM-11).
        drawdown_sized_episodes = 0
        executed_geometry: list[tuple[float, float]] = []   # (target_r, stop_r)

        def counterfactual(cid: str, draft, from_idx: int) -> CounterfactualOutcome:
            tail = bars[from_idx:]
            owner = by_expert.get(draft.expert_id)

            def thesis_ok(t_ns: int | None, _payload: dict) -> bool:
                # The counterfactual applies the owning Expert's post-entry
                # thesis exactly like the executed path (PHASE 1b): a thesis
                # that dies before price does closes at that bar's close
                # (THESIS_INVALIDATED), never held by price alone. This keeps
                # the executed and NOT_EXECUTED populations under one exit
                # policy for the O-014/D-027 attribution comparison.
                if owner is None or t_ns is None:
                    return True
                st = states_by_time.get(t_ns)
                return owner.still_valid(st, draft) if st is not None else True

            out = sim.run(draft, [b.payload for b in tail],
                          times=[b.available_time for b in tail],
                          thesis_valid=thesis_ok)
            return replace(out, candidate_id=cid)

        if manifest.interval not in _INTERVAL_NS:
            raise ValueError(
                f'unsupported interval {manifest.interval!r}; supported: '
                f'{sorted(_INTERVAL_NS)}')
        interval_ns = _INTERVAL_NS[manifest.interval]

        # Pre-build EVERY bar's decision state once. build_state is a pure
        # function of (rows, as_of, universe), so pre-building is deterministic
        # and identical to incremental building — but it lets the batch
        # counterfactual evaluate the owning Expert's still_valid on FUTURE bars
        # too (an inline build only has states up to the current bar, which made
        # thesis_ok silently return True for every future clock).
        # INCREMENTAL: consume rows in the SAME available_time order as `bars`
        # (pit), so the moving pointer accumulates every admissible row once —
        # O(N) instead of the O(N^2) per-bar tape rescan that dominated run
        # time at N>1000. Consuming in event-sorted replay order here would
        # silently skip a row that is admissible at the current clock.
        # D-053: the canonical state carries the UNION of every active Expert's
        # declared intervals, so one state per clock still serves all of them.
        # Experts declaring nothing leave the union at {base} and the state is
        # byte-identical to the pre-D-053 one.
        from .interval import INTERVAL_NS

        declared_union: list[str] = []
        # Depth union: the canonical state holds max(declared) per interval so
        # one deep Expert does not make everyone recompute, and each Expert's
        # view is truncated back to its own declaration in `_view_for`.
        depth_union: dict[str, int] = {}
        for ex in experts:
            if not hasattr(ex, 'declared_intervals'):
                continue
            for tf in ex.declared_intervals(manifest.interval):
                if tf != manifest.interval and tf not in declared_union:
                    declared_union.append(tf)
                depth_union[tf] = max(depth_union.get(tf, 0),
                                      ex.declared_depth(tf))
        declared_union.sort(key=lambda t: INTERVAL_NS.get(t, 0))
        known_intervals = frozenset(INTERVAL_NS)

        acc_rows: list = []
        pit_it = iter(pit)
        next_row = next(pit_it, None)
        for bar in bars:
            while next_row is not None \
                    and next_row.available_time <= bar.available_time:
                acc_rows.append(next_row)
                next_row = next(pit_it, None)
            states_by_time[bar.available_time] = build_multi_state(
                acc_rows, bar.available_time, self.universe,
                base_interval=manifest.interval,
                intervals=tuple(declared_union), depths=depth_union)

        for i, bar in enumerate(bars):
            as_of = bar.available_time
            state = states_by_time[as_of]
            state_rec = record_dict(state, source='marketstate')
            state_rec['event_id'] = state.state_id
            self.states.append(state_rec)

            # PHASE 1a: enter candidates whose entry bar is this bar (fill at close).
            for cid, info in list(pending.items()):
                if info.get('entry_bar') != i:
                    continue
                draft = info['draft']
                # Pre-entry invalidation, re-checked on the entry bar itself
                # (CANDIDATE_LIFECYCLE_SPEC: a PENDING/TRIGGERED candidate ends on
                # invalidation_observed). Phase 2 evaluated the trigger bar only;
                # if the trigger condition breaks again on the entry bar, the
                # candidate must NOT execute (it would silently pollute the
                # executed population).
                if (draft.direction == 'LONG'
                        and float(bar.payload['low']) < info['prior_low']) \
                        or (draft.direction == 'SHORT'
                            and float(bar.payload['high']) > info['prior_high']):
                    self.registry.apply(cid, 'TRIGGERED', 'INVALIDATED',
                                        'invalidation_observed', as_of)
                    self._record_outcome(cid, 'INVALIDATED_BEFORE_TRIGGER', 0.0,
                                         'NOT_EXECUTED', sim.hash(),
                                         label_available_time=as_of)
                    del pending[cid]
                    continue
                # EXEC-4 (EX-11): FILL_AT_LIMIT entry. The order rests at the
                # declared limit_price; this bar is inspected for a FILL only
                # (never for exits — the invariant holds because the position
                # opens with entry_bar_index == i and the step loop skips the
                # entry bar). An unfilled bar leaves the order resting (entry
                # bar slides one bar); a never-filling order stays TRIGGERED
                # and the epilogue records the never-entered convention.
                if sim.fill_policy == 'FILL_AT_LIMIT':
                    if 'limit_price' not in draft.risk_geometry:
                        raise ValueError(
                            'FILL_AT_LIMIT requires risk_geometry[limit_price]; '
                            f'{draft.expert_id} {cid} declares none — fail closed')
                    limit = float(draft.risk_geometry['limit_price'])
                    filled = (draft.direction == 'LONG'
                              and float(bar.payload['low']) <= limit) \
                        or (draft.direction == 'SHORT'
                            and float(bar.payload['high']) >= limit)
                    if not filled:
                        info['entry_bar'] = i + 1   # rest: try the next bar
                        continue
                    entry = limit
                else:
                    entry = float(bar.payload['close'])
                # D-024 mechanical tradability mask, applied before any risk
                # admission: data-plane integrity veto, kept counterfactual
                # (NOT_EXECUTED) like the other rejections below.
                vetoed, veto_reason = tradability_mask_veto(
                    bar.payload, state.quality, bar.available_time,
                    max_bar_range_frac=manifest.max_bar_range_frac,
                    funding_window_bars=manifest.funding_window_bars,
                    funding_hours=manifest.funding_hours,
                    interval_ns=interval_ns)
                if vetoed:
                    self.registry.apply(cid, 'TRIGGERED', 'REJECTED',
                                        TRADABILITY_MASK_VETO, as_of)
                    self.candidates.append({'kind': 'tradability_veto',
                                            'candidate_id': cid, 'detail': veto_reason,
                                            'source': 'risk',
                                            'event_id': f'{cid}:veto:{as_of}'})
                    # The would-be fill is at this bar's close (Phase 1a); the
                    # counterfactual enters at bars[i] and inspects bars[i+1:],
                    # exactly mirroring the executed path. Entering one bar
                    # later (i+1) would simulate a DIFFERENT trade for every
                    # rejected candidate and bias the D-027/O-014 population.
                    out = counterfactual(cid, draft, i)
                    self._record_outcome(cid, out.endpoint, out.net_r,
                                         'NOT_EXECUTED', sim.hash(), out.horizon_bars,
                                         label_available_time=out.label_available_time,
                                         mae_r=out.mae_r, mfe_r=out.mfe_r,
                                         ambiguous_bars=out.ambiguous_bars,
                                         entry_price=out.entry_price,
                                         risk_unit_price=out.risk_unit_price,
                                         market_move_r=out.market_move_r)
                    del pending[cid]
                    continue
                verdict = gate.admit(draft)
                if not verdict.ok:
                    if verdict.reason_code == 'EXISTING_EXPOSURE_CONFLICT':
                        conflicts += 1
                    self.registry.apply(cid, 'TRIGGERED', 'REJECTED',
                                        verdict.reason_code or 'risk_rejected', as_of)
                    out = counterfactual(cid, draft, i)
                    self._record_outcome(cid, out.endpoint, out.net_r,
                                         'NOT_EXECUTED', sim.hash(), out.horizon_bars,
                                         label_available_time=out.label_available_time,
                                         mae_r=out.mae_r, mfe_r=out.mfe_r,
                                         ambiguous_bars=out.ambiguous_bars,
                                         entry_price=out.entry_price,
                                         risk_unit_price=out.risk_unit_price,
                                         market_move_r=out.market_move_r)
                    del pending[cid]
                    continue
                self.registry.apply(cid, 'TRIGGERED', 'ACCEPTED', 'risk_accept', as_of)
                self.registry.apply(cid, 'ACCEPTED', 'ORDER_SUBMITTED', 'submit_order', as_of)
                self.registry.apply(cid, 'ORDER_SUBMITTED', 'EXECUTED', 'fill_observed', as_of)
                # The executed position is sized at the gate's EFFECTIVE size
                # (draft.size after the O-016 drawdown ladder). R-multiples
                # are size-independent, so the outcome ledger is unchanged;
                # the size feeds the equity curve (RM-06) and the report.
                if verdict.size < draft.size:
                    drawdown_sized_episodes += 1
                executed_geometry.append(
                    (float(draft.risk_geometry.get('target_r', 1.0)),
                     float(draft.risk_geometry.get('stop_r', 1.0))))
                open_positions[cid] = OpenPosition(candidate_id=cid, draft=draft,
                                                   entry_price=entry, entry_bar_index=i,
                                                   entry_time_ns=bar.available_time,
                                                   size=verdict.size)

            # PHASE 1b: step open positions on this bar (never on the entry bar).
            # The owning Expert re-checks its thesis first: a dead thesis is a
            # distinct exit from a price stop (EXPERT_PROTOCOL, still_valid).
            for cid, pos in list(open_positions.items()):
                if pos.entry_bar_index == i:
                    continue
                owner = by_expert.get(pos.draft.expert_id)
                thesis_ok = owner.still_valid(state, pos.draft) if owner else True
                res = sim.step(pos, bar.payload, thesis_valid=thesis_ok,
                               bar_time=bar.available_time)
                if res.closed_fraction < 1.0 and res.next_pos is not None:
                    # EXEC-2: NON-TERMINAL partial exit. The closed fraction is
                    # booked at this bar's close and the position continues at
                    # size*(1-f). Recorded as a lifecycle PositionAction — never
                    # an outcome (one terminal outcome per candidate) and never
                    # an endpoint (the endpoint vocabulary is unchanged). The
                    # closed leg's R is accumulated on the position
                    # (realized_r) and realized at the terminal close.
                    self.registry.position_action(
                        cid, 'PARTIAL_EXIT', fraction=res.closed_fraction,
                        price=float(bar.payload['close']), knowledge_time=as_of)
                    open_positions[cid] = res.next_pos
                    continue
                if res.closed and res.endpoint and res.net_r is not None:
                    closed_pos = res.next_pos or pos
                    unit = risk_unit(pos.draft, pos.entry_price)
                    self._record_outcome(cid, res.endpoint, res.net_r,
                                         res.label_status or 'MATURE', sim.hash(),
                                         pos.bars_held + 1,
                                         label_available_time=bar.available_time,
                                         mae_r=closed_pos.mae_r, mfe_r=closed_pos.mfe_r,
                                         ambiguous_bars=closed_pos.ambiguous_bars,
                                         entry_price=pos.entry_price,
                                         risk_unit_price=unit,
                                         market_move_r=(float(bar.payload['close'])
                                                        - pos.entry_price) / unit)
                    reason = {'TARGET': 'position_flat', 'STOP': 'position_flat',
                              'THESIS_INVALIDATED': 'thesis_invalidated',
                              'TIME_EXIT': 'expiry_reached'}.get(
                                  res.endpoint, 'expiry_reached')
                    self.registry.apply(cid, 'EXECUTED', 'CLOSED', reason, as_of)
                    # O-016 equity feed: episode net_r is fraction-weighted
                    # (realized_r + remaining*leg) and size-independent, so it
                    # is booked against the admission size (pos.size), which
                    # scale-outs never reduce. Deterministic — never wall clock.
                    gate.equity.on_episode_closed(res.net_r, pos.size)
                    gate.release(pos.draft)
                    del open_positions[cid]
                elif res.next_pos is not None:
                    open_positions[cid] = res.next_pos

            # PHASE 2: trigger candidates born at the previous bar (entry next bar).
            for cid, info in list(pending.items()):
                if info['birth_idx'] != i - 1 or info.get('entry_bar') is not None:
                    continue
                draft = info['draft']
                long = draft.direction == 'LONG'
                low, high = float(bar.payload['low']), float(bar.payload['high'])
                if (long and low < info['prior_low']) or (not long and high > info['prior_high']):
                    self.registry.apply(cid, 'PENDING', 'INVALIDATED',
                                        'invalidation_observed', as_of)
                    self._record_outcome(cid, 'INVALIDATED_BEFORE_TRIGGER', 0.0,
                                         'NOT_EXECUTED', sim.hash(),
                                         label_available_time=as_of)
                    del pending[cid]
                    continue
                self.registry.apply(cid, 'PENDING', 'TRIGGERED', 'trigger_observed', as_of)
                if manifest.round_trip_cost_r >= EXCESS_COST_THRESHOLD_R:
                    self.registry.apply(cid, 'TRIGGERED', 'REJECTED', 'excess_cost', as_of)
                    # Mirror the executed path's pre-entry invalidation (H3):
                    # if the would-be entry bar breaks the trigger predicate,
                    # the candidate would never have entered — record
                    # INVALIDATED_BEFORE_TRIGGER, not a trading counterfactual
                    # (a silent population inconsistency otherwise).
                    entry_bar = bars[i + 1] if i + 1 < len(bars) else None
                    if entry_bar is None:
                        # Triggered on the final bar: no entry bar before tape
                        # end — the candidate never entered. Record the
                        # never-entered convention (INVALIDATED_BEFORE_TRIGGER,
                        # NOT_EXECUTED, label knowable at tape end), exactly
                        # like the epilogue does below the cost gate; a
                        # fabricated empty-tail counterfactual (sim.run([])
                        # -> EXPIRY/0.0/RIGHT_CENSORED) would merge a
                        # non-trade into the outcomes ledger with a fake
                        # simulator hash and give the same fact two different
                        # endpoints (ledger-consistency defect).
                        self._record_outcome(cid, 'INVALIDATED_BEFORE_TRIGGER', 0.0,
                                             'NOT_EXECUTED', sim.hash(),
                                             label_available_time=last_as_of)
                    elif (draft.direction == 'LONG'
                          and float(entry_bar.payload['low']) < info['prior_low']) \
                            or (draft.direction == 'SHORT'
                                and float(entry_bar.payload['high'])
                                > info['prior_high']):
                        self._record_outcome(cid, 'INVALIDATED_BEFORE_TRIGGER', 0.0,
                                             'NOT_EXECUTED', sim.hash(),
                                             label_available_time=entry_bar.available_time)
                    else:
                        out = counterfactual(cid, draft, i + 1)
                        self._record_outcome(
                            cid, out.endpoint, out.net_r,
                            'NOT_EXECUTED', sim.hash(), out.horizon_bars,
                            label_available_time=out.label_available_time or last_as_of,
                            mae_r=out.mae_r, mfe_r=out.mfe_r,
                            ambiguous_bars=out.ambiguous_bars,
                            entry_price=out.entry_price,
                            risk_unit_price=out.risk_unit_price,
                            market_move_r=out.market_move_r)
                    del pending[cid]
                    continue
                info['entry_bar'] = i + 1

            # PHASE 3: full self-gating — every cheap expert evaluates the bar.
            # Evaluate in canonical expert_id order: RUNTIME_SCHEDULER_SPEC
            # section 5 requires shuffling the evaluation order of independent
            # experts to produce identical stored events — the evaluation and
            # DETECTED record order is part of the ledger hash.
            for ex in sorted(experts, key=lambda e: e.expert_id):
                # D-053: each Expert evaluates the MarketState it declared — a
                # projection of the one canonical state, not a state of its own
                # (state_id is carried through, so the ledger still shows every
                # Expert deciding against the same world at this clock).
                ev = ex.evaluate(_view_for(ex, state, manifest.interval,
                                           known_intervals))
                self.evaluations.append(record_dict(ev, source='expert'))
                if ev.draft is None:
                    continue
                sym = ev.draft.instrument
                cid = episode_key(ex.expert_id, ex.version, sym,
                                  ev.draft.direction,
                                  ev.draft.setup_anchor_event_id,
                                  _geometry_version(ev.draft))
                if self.registry.is_duplicate(cid):
                    self.candidates.append({'kind': 'suppressed_duplicate',
                                            'candidate_id': cid, 'birth_time': as_of,
                                            'expert_id': ex.expert_id,
                                            'source': 'expert',
                                            'event_id': f'{cid}:suppressed:{as_of}'})
                    continue
                # Immutable birth snapshot on the DETECTED transition
                # (CANDIDATE_LIFECYCLE_SPEC section 1): expert identity, setup
                # evidence, geometry version and the birth state. It is part
                # of the append-only event and can never be rewritten.
                self.registry.apply(cid, None, 'DETECTED', 'setup_detected', as_of,
                                    extra={'expert_id': ev.draft.expert_id,
                                           'expert_version': ev.draft.expert_version,
                                           'instrument': ev.draft.instrument,
                                           'direction': ev.draft.direction,
                                           'setup_anchor_event_id':
                                               ev.draft.setup_anchor_event_id,
                                           'geometry_version':
                                               _geometry_version(ev.draft),
                                           'state_id': state.state_id})
                self.registry.apply(cid, 'DETECTED', 'PENDING', 'hypothesis_completed', as_of)
                pl = state.features.get(f'{sym}.prior_low')
                ph = state.features.get(f'{sym}.prior_high')
                # The pre-entry invalidation level must match the expert's
                # thesis reference. failed_breakout / liquidity_sweep freeze a
                # WINDOWED prior extreme in the draft geometry (prior_high_ref
                # / prior_low_ref) and their gate/anchor/still_valid all use
                # it; the all-bars state feature diverges from it (an old spike
                # outside the 32-bar window pins it), so an invalidation tested
                # against the state feature would let a dead-thesis candidate
                # trigger and enter, polluting the executed population. Use the
                # frozen draft ref when present; the all-bars state feature is
                # the fallback for experts without a prior-level thesis
                # (trend_pullback). Defaulting to 0.0/inf would make the check
                # silently permissive — fail closed instead.
                geom = ev.draft.risk_geometry
                prior_low = (float(geom['prior_low_ref'])
                             if 'prior_low_ref' in geom else None)
                prior_high = (float(geom['prior_high_ref'])
                              if 'prior_high_ref' in geom else None)
                if prior_low is None:
                    if pl is None or pl.value is None:
                        raise ValueError(
                            f'{sym} prior_low unavailable at birth {as_of}: '
                            f'Expert {ev.draft.expert_id} emitted a draft '
                            'without trigger geometry — refuse, never default '
                            'to 0/inf')
                    prior_low = float(pl.value)
                if prior_high is None:
                    if ph is None or ph.value is None:
                        raise ValueError(
                            f'{sym} prior_high unavailable at birth {as_of}: '
                            f'Expert {ev.draft.expert_id} emitted a draft '
                            'without trigger geometry — refuse, never default '
                            'to 0/inf')
                    prior_high = float(ph.value)
                pending[cid] = {'draft': ev.draft, 'birth_idx': i, 'entry_bar': None,
                                'prior_low': prior_low, 'prior_high': prior_high}

        # Epilogue: close whatever the tape end leaves dangling, deterministically.
        for cid, pos in list(open_positions.items()):
            final_close = float(bars[-1].payload['close']) if bars else pos.entry_price
            # The tape-end close formula belongs to the simulator alone
            # (simulator.close_out); re-deriving it here would silently diverge
            # the moment the cost/funding policy changes.
            net = sim.close_out(pos, final_close)
            unit = risk_unit(pos.draft, pos.entry_price)
            self._record_outcome(cid, 'EXPIRY', net, 'RIGHT_CENSORED',
                                 sim.hash(), pos.bars_held,
                                 label_available_time=last_as_of,
                                 mae_r=pos.mae_r, mfe_r=pos.mfe_r,
                                 ambiguous_bars=pos.ambiguous_bars,
                                 entry_price=pos.entry_price,
                                 risk_unit_price=unit,
                                 market_move_r=(final_close
                                                - pos.entry_price) / unit)
            self.registry.apply(cid, 'EXECUTED', 'CLOSED', 'expiry_reached', last_as_of)
            # O-016 equity feed for tape-end realizations (same as in-loop):
            # fraction-weighted, size-independent net_r against the admission
            # size (pos.size), which scale-outs never reduce.
            gate.equity.on_episode_closed(net, pos.size)
            gate.release(pos.draft)
        for cid, info in list(pending.items()):
            if self.registry.current(cid) == 'TRIGGERED':
                self.registry.apply(cid, 'TRIGGERED', 'INVALIDATED',
                                    'no_entry_before_tape_end', last_as_of)
                # The candidate NEVER entered (no entry bar before tape end):
                # a fabricated empty-tail counterfactual (sim.run([]) returns
                # EXPIRY/0.0/RIGHT_CENSORED) would merge a non-trade into the
                # censored population with a fake simulator hash. Record the
                # never-entered convention instead — NOT_EXECUTED, endpoint
                # consistent with the INVALIDATED terminal (B5), label knowable
                # at tape end.
                self._record_outcome(cid, 'INVALIDATED_BEFORE_TRIGGER', 0.0,
                                     'NOT_EXECUTED', sim.hash(),
                                     label_available_time=last_as_of)
            elif self.registry.current(cid) == 'PENDING':
                self.registry.apply(cid, 'PENDING', 'EXPIRED', 'expiry_reached', last_as_of)
                # Never entered: a PENDING candidate that expires before trigger
                # is a non-trade, NOT a censored executed position — merging it
                # into RIGHT_CENSORED pollutes the executed-and-censored
                # population (same class as the INVALIDATED_BEFORE_TRIGGER fix).
                self._record_outcome(cid, 'EXPIRY', 0.0, 'NOT_EXECUTED', sim.hash(),
                                     label_available_time=last_as_of)

        # terminal_distribution counts each candidate's FINAL terminal state
        # (a candidate that goes CLOSED -> ARCHIVED must appear once, in
        # ARCHIVED, not in both buckets) and breaks REJECTED down by reason.
        dist: dict[str, int] = {}
        rejection_dist: dict[str, int] = {}
        final_terminal: dict[str, str] = {}
        candidate_ids: set[str] = set()
        for rec in self.candidates.read():
            if 'to_state' not in rec:
                continue
            candidate_ids.add(rec['candidate_id'])
            if rec['to_state'] in TERMINAL:
                final_terminal[rec['candidate_id']] = rec['to_state']
                if rec['to_state'] == 'REJECTED':
                    rc = rec.get('reason_code', 'unknown')
                    rejection_dist[rc] = rejection_dist.get(rc, 0) + 1
        for terminal_state in final_terminal.values():
            dist[terminal_state] = dist.get(terminal_state, 0) + 1
        # D-027 attribution-validity populations (prereg §15): executed =
        # outcome label_status != NOT_EXECUTED; portfolio-rejected = the
        # NOT_EXECUTED counterfactual of a candidate REJECTED for a
        # portfolio-state reason (EXISTING_EXPOSURE_CONFLICT /
        # PORTFOLIO_HEAT_EXCEEDED). Cost gates, invalidation, expiry and the
        # D-024 mask veto express the strategy itself (D-027 principle) and
        # are excluded from the denominator. Both statistics are computed and
        # reported even without a receipt; they gate only when one exists.
        outcomes_all = self.outcomes.read()
        outcome_by_cid = {o['candidate_id']: o for o in outcomes_all}
        executed_net_r = [o['net_r'] for o in outcomes_all
                          if o['label_status'] != 'NOT_EXECUTED']
        portfolio_rejected_net_r: list[float] = []
        for rec in self.candidates.read():
            if rec.get('to_state') == 'REJECTED' and rec.get('reason_code') in (
                    'EXISTING_EXPOSURE_CONFLICT', 'PORTFOLIO_HEAT_EXCEEDED'):
                o = outcome_by_cid.get(rec['candidate_id'])
                if o is not None and o['label_status'] == 'NOT_EXECUTED':
                    portfolio_rejected_net_r.append(o['net_r'])
        n_executed = len(executed_net_r)
        n_portfolio_rejected = len(portfolio_rejected_net_r)
        if n_executed + n_portfolio_rejected > 0:
            execution_share = n_executed / (n_executed + n_portfolio_rejected)
            divergence_ks = _two_sample_ks(executed_net_r,
                                           portfolio_rejected_net_r) \
                if portfolio_rejected_net_r else 0.0
        else:
            execution_share = None
            divergence_ks = None
        # Persist the run definition alongside the ledgers: a store directory
        # must be self-describing (a zero-candidate run would otherwise be
        # byte-identical across DIFFERENT manifests — SIMULATION_TRUTH_SPEC
        # requires the configuration hash).
        (self.dir / 'manifest.json').write_text(
            json.dumps(record_dict(manifest, source='manifest'),
                       sort_keys=True, indent=2) + '\n', encoding='utf-8')
        # The decision ledger (DATASET_SPEC section 1) binds candidates,
        # evaluations, outcomes, the persisted MarketState ledger AND the run
        # configuration (economics + the authority receipt: a receipt added
        # later must move the ledger hash, never silently re-label a report).
        config_hash = sha1_hex(asdict(manifest))
        ledger_hash = sha1_hex((self.candidates.hash, self.evaluations.hash,
                                self.outcomes.hash, self.states.hash,
                                config_hash, risk_config_hash))
        data_hash = self.tape_log.hash
        # The report must bind what actually ran: a non-empty manifest pin that
        # does not match the live code/tape is a stale or forged identity.
        # Fail closed at the composition root — a direct Lab.run caller must
        # never get a report claiming code/data that did not run (materialize_
        # views re-checks, but Lab.run is the authority).
        live_code_hash = _code_hash()
        if manifest.code_hash and manifest.code_hash != live_code_hash:
            raise ValueError(
                f'manifest code_hash {manifest.code_hash} != live {live_code_hash}')
        if manifest.data_hash and manifest.data_hash != data_hash:
            raise ValueError(
                f'manifest data_hash {manifest.data_hash} != live tape {data_hash}')
        # --- Risk/sizing diagnostics (RM-01..19; O-016). Report-only --------
        # Computed from the executed-outcome ledger and the equity feed; never
        # bound into ledger_hash (all inputs are already inside it).
        trade_units = trade_units_for(manifest.risk_per_trade)
        final_equity = equity.final_equity()
        max_drawdown = equity.max_drawdown()
        risk_of_ruin = equity.risk_of_ruin()
        # RM-17 profit factor: gross win / gross |loss| over executed net_R
        # (after cost). None when no episode or nothing to divide (no losses).
        gross_win = sum(r for r in executed_net_r if r > 0.0)
        gross_loss = sum(r for r in executed_net_r if r < 0.0)
        if gross_loss < 0.0:
            profit_factor = gross_win / -gross_loss
        elif executed_net_r:
            profit_factor = None          # no losing episode: unbounded PF
        else:
            profit_factor = None
        # RM-11 spread-adjusted breakeven win rate: w_min = 1/(1 + R/r') with
        # R/r' = (target_r - cost)/(stop_r + cost) — the cost-degraded reward
        # to risk (Ch3.3). Mean over the executed geometry (uniform for the
        # pilots). None when no position executed.
        w_vals = []
        for target_r, stop_r in executed_geometry:
            reward = target_r - manifest.round_trip_cost_r
            risk = stop_r + manifest.round_trip_cost_r
            if reward > 0.0 and risk > 0.0:
                w_vals.append(1.0 / (1.0 + reward / risk))
        w_min = (sum(w_vals) / len(w_vals)) if w_vals else None
        # RM-10 worst case: realized worst single-episode net_R and the
        # theoretical portfolio worst case (every heat slot stopped at once).
        worst_case_r = min(executed_net_r) if executed_net_r else None
        worst_case_portfolio_r = -float(gate.max_heat)
        # RM-07/RM-08 annotations: below the trade-unit budget or the
        # min_trades bar, the run carries a NO_ECONOMIC_CLAIM note — a
        # report annotation, never a hard fail and never a change to the
        # D-027 verdict string (a dev window that cannot field enough
        # episodes cannot support a positive economic reading).
        notes: list[str] = []
        if n_executed < trade_units:
            notes.append(
                f'NO_ECONOMIC_CLAIM: executed episodes {n_executed} < '
                f'trade-unit need {trade_units:.0f} (RM-07 budget)')
        if n_executed < manifest.min_trades:
            notes.append(
                f'NO_ECONOMIC_CLAIM: executed episodes {n_executed} < '
                f'min_trades {manifest.min_trades} (RM-08 adequacy bar)')
        economic_note = '; '.join(notes) if notes else None
        verdict = _d027_verdict(manifest.authority_receipt,
                                execution_share, divergence_ks)
        # Zero-trade provenance: surface WHY (evaluations never found a setup,
        # all candidates invalidated, the tape degenerate) instead of letting
        # candidate_count=0 collapse every cause.
        eval_dist: dict[str, int] = {}
        for rec in self.evaluations.read():
            decision = rec.get('decision', '?')
            eval_dist[decision] = eval_dist.get(decision, 0) + 1
        states_all = self.states.read()
        data_invalid = (not states_all) or all(
            s.get('quality') == 'DEGRADED' for s in states_all)
        return LabReport(experiment_id=manifest.experiment_id,
                         code_hash=manifest.code_hash or _code_hash(),
                         data_hash=manifest.data_hash or data_hash,
                         candidate_count=len(candidate_ids),
                         terminal_distribution=dist, ledger_hash=ledger_hash,
                         verdict=verdict, exposure_conflicts=conflicts,
                         evaluation_distribution=eval_dist,
                         data_invalid=data_invalid,
                         rejection_distribution=rejection_dist,
                         n_executed=n_executed,
                         n_portfolio_rejected=n_portfolio_rejected,
                         execution_share=execution_share,
                         divergence_ks=divergence_ks,
                         tooling_hash=_tooling_hash(),
                         risk_gate_hash=risk_config_hash,
                         size_scheme=SIZE_SCHEME,
                         risk_per_trade=manifest.risk_per_trade,
                         min_trades=manifest.min_trades,
                         trade_units=trade_units,
                         final_equity=final_equity,
                         max_drawdown=max_drawdown,
                         drawdown_sized_episodes=drawdown_sized_episodes,
                         risk_of_ruin=risk_of_ruin,
                         profit_factor=profit_factor,
                         w_min=w_min,
                         worst_case_r=worst_case_r,
                         worst_case_portfolio_r=worst_case_portfolio_r,
                         economic_note=economic_note)
