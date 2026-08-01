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
from .marketstate import build_state
from .lifecycle import CandidateRegistry, episode_key, TERMINAL
from .simulator import CanonicalSimulator, OpenPosition, risk_unit
from .risk import RiskGate, tradability_mask_veto, TRADABILITY_MASK_VETO

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
    base = Path(__file__).resolve().parent
    files = {str(p.relative_to(base)): p.read_bytes().hex()
             for p in sorted(base.rglob('*.py'))}
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
                        ambiguous_bars: int = 0) -> None:
        out = CounterfactualOutcome(candidate_id=candidate_id, horizon_bars=horizon_bars,
                                    endpoint=endpoint, net_r=net_r,
                                    label_status=label_status,
                                    simulator_hash=simulator_hash,
                                    label_available_time=label_available_time,
                                    mae_r=mae_r, mfe_r=mfe_r,
                                    ambiguous_bars=ambiguous_bars)
        self.outcomes.append(record_dict(out, source='simulator'))

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
        gate = risk_gate or RiskGate()
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
        # Only CLOSED klines drive the decision loop; an open (not-yet-closed)
        # kline must never feed entries, stops/targets, or invalidation with its
        # partial OHLC (FEED_INGESTION_SPEC section 3 — marketstate already
        # filters closed bars for features; the decision loop must too).
        bars = [r for r in tape if r.channel == 'kline'
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
        # INCREMENTAL: tape is replay-sorted (available_time non-decreasing), so
        # a moving pointer accumulates rows once — O(N) instead of the O(N^2)
        # per-bar tape rescan that dominated run time at N>1000.
        acc_rows: list = []
        tape_it = iter(tape)
        next_row = next(tape_it, None)
        for bar in bars:
            while next_row is not None \
                    and next_row.available_time <= bar.available_time:
                acc_rows.append(next_row)
                next_row = next(tape_it, None)
            states_by_time[bar.available_time] = build_state(
                acc_rows, bar.available_time, self.universe)

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
                entry = float(bar.payload['close'])
                # D-024 mechanical tradability mask, applied before any risk
                # admission: data-plane integrity veto, kept counterfactual
                # (NOT_EXECUTED) like the other rejections below.
                vetoed, veto_reason = tradability_mask_veto(
                    bar.payload, state.quality, bar.available_time,
                    max_spread_frac=manifest.max_spread_frac,
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
                                         ambiguous_bars=out.ambiguous_bars)
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
                                         ambiguous_bars=out.ambiguous_bars)
                    del pending[cid]
                    continue
                self.registry.apply(cid, 'TRIGGERED', 'ACCEPTED', 'risk_accept', as_of)
                self.registry.apply(cid, 'ACCEPTED', 'ORDER_SUBMITTED', 'submit_order', as_of)
                self.registry.apply(cid, 'ORDER_SUBMITTED', 'EXECUTED', 'fill_observed', as_of)
                open_positions[cid] = OpenPosition(candidate_id=cid, draft=draft,
                                                   entry_price=entry, entry_bar_index=i,
                                                   entry_time_ns=bar.available_time)

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
                if res.closed and res.endpoint and res.net_r is not None:
                    closed_pos = res.next_pos or pos
                    self._record_outcome(cid, res.endpoint, res.net_r,
                                         res.label_status or 'MATURE', sim.hash(),
                                         pos.bars_held + 1,
                                         label_available_time=bar.available_time,
                                         mae_r=closed_pos.mae_r, mfe_r=closed_pos.mfe_r,
                                         ambiguous_bars=closed_pos.ambiguous_bars)
                    reason = {'TARGET': 'position_flat', 'STOP': 'position_flat',
                              'THESIS_INVALIDATED': 'thesis_invalidated'}.get(
                                  res.endpoint, 'expiry_reached')
                    self.registry.apply(cid, 'EXECUTED', 'CLOSED', reason, as_of)
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
                    if entry_bar is not None and (
                            (draft.direction == 'LONG'
                             and float(entry_bar.payload['low']) < info['prior_low'])
                            or (draft.direction == 'SHORT'
                                and float(entry_bar.payload['high'])
                                > info['prior_high'])):
                        self._record_outcome(cid, 'INVALIDATED_BEFORE_TRIGGER', 0.0,
                                             'NOT_EXECUTED', sim.hash(),
                                             label_available_time=entry_bar.available_time)
                    else:
                        out = counterfactual(cid, draft, i + 1)
                        # Empty-tail counterfactual (trigger on the final bar)
                        # has no exit clock (label_available_time=0 sentinel);
                        # its label is knowable at tape end.
                        self._record_outcome(
                            cid, out.endpoint, out.net_r,
                            'NOT_EXECUTED', sim.hash(), out.horizon_bars,
                            label_available_time=out.label_available_time or last_as_of,
                            mae_r=out.mae_r, mfe_r=out.mfe_r,
                            ambiguous_bars=out.ambiguous_bars)
                    del pending[cid]
                    continue
                info['entry_bar'] = i + 1

            # PHASE 3: full self-gating — every cheap expert evaluates the bar.
            # Evaluate in canonical expert_id order: RUNTIME_SCHEDULER_SPEC
            # section 5 requires shuffling the evaluation order of independent
            # experts to produce identical stored events — the evaluation and
            # DETECTED record order is part of the ledger hash.
            for ex in sorted(experts, key=lambda e: e.expert_id):
                ev = ex.evaluate(state)
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
            sign = 1.0 if pos.draft.direction == 'LONG' else -1.0
            final_close = float(bars[-1].payload['close']) if bars else pos.entry_price
            unit = risk_unit(pos.draft, pos.entry_price)     # R, never percent
            net = sign * (final_close - pos.entry_price) / unit \
                - manifest.round_trip_cost_r - pos.funding_paid_r
            self._record_outcome(cid, 'EXPIRY', net, 'RIGHT_CENSORED',
                                 sim.hash(), pos.bars_held,
                                 label_available_time=last_as_of,
                                 mae_r=pos.mae_r, mfe_r=pos.mfe_r,
                                 ambiguous_bars=pos.ambiguous_bars)
            self.registry.apply(cid, 'EXECUTED', 'CLOSED', 'expiry_reached', last_as_of)
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
                                config_hash))
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
                         tooling_hash=_tooling_hash())
