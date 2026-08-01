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

from dataclasses import replace
from pathlib import Path

from .schema import (TapeRow, ExperimentManifest, LabReport,
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


def _code_hash() -> str:
    base = Path(__file__).resolve().parent
    files = {str(p.relative_to(base)): p.read_bytes().hex()
             for p in sorted(base.rglob('*.py'))}
    return sha1_hex(files)


def _geometry_version(draft) -> str:
    """Structural risk geometry only: `atr_ref` is data-dependent (it moves with
    the market) and must not be part of episode identity — a stable setup would
    otherwise change key across decision clocks and disable deduplication."""
    structural = {k: v for k, v in draft.risk_geometry.items() if k != 'atr_ref'}
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
        for r in rows:
            self.tape_log.append(record_dict(r, source=r.source))

    def _record_outcome(self, candidate_id: str, endpoint: str, net_r: float,
                        label_status: str, simulator_hash: str,
                        horizon_bars: int = 0, mae_r: float = 0.0,
                        mfe_r: float = 0.0, ambiguous_bars: int = 0) -> None:
        out = CounterfactualOutcome(candidate_id=candidate_id, horizon_bars=horizon_bars,
                                    endpoint=endpoint, net_r=net_r,
                                    label_status=label_status,
                                    simulator_hash=simulator_hash,
                                    mae_r=mae_r, mfe_r=mfe_r,
                                    ambiguous_bars=ambiguous_bars)
        self.outcomes.append(record_dict(out, source='simulator'))

    def run(self, manifest: ExperimentManifest, experts: list,
            risk_gate: RiskGate | None = None) -> LabReport:
        sim = CanonicalSimulator(round_trip_cost_r=manifest.round_trip_cost_r,
                                 funding_rate_r=manifest.funding_rate_r,
                                 funding_hours=manifest.funding_hours)
        gate = risk_gate or RiskGate()
        by_expert = {ex.expert_id: ex for ex in experts}
        tape = self.tape_log.replay_tape()
        bars = [r for r in tape if r.channel == 'kline']
        pending: dict[str, dict] = {}            # cid -> draft/birth/entry info
        open_positions: dict[str, OpenPosition] = {}
        conflicts = 0

        def counterfactual(cid: str, draft, from_idx: int) -> CounterfactualOutcome:
            tail = bars[from_idx:]
            out = sim.run(draft, [b.payload for b in tail],
                          times=[b.available_time for b in tail])
            return replace(out, candidate_id=cid)

        for i, bar in enumerate(bars):
            as_of = bar.available_time
            state = build_state(
                [r for r in tape if r.available_time <= as_of], as_of, self.universe)
            state_rec = record_dict(state, source='marketstate')
            state_rec['event_id'] = state.state_id
            self.states.append(state_rec)

            # PHASE 1a: enter candidates whose entry bar is this bar (fill at close).
            for cid, info in list(pending.items()):
                if info.get('entry_bar') != i:
                    continue
                draft = info['draft']
                entry = float(bar.payload['close'])
                # D-024 mechanical tradability mask, applied before any risk
                # admission: data-plane integrity veto, kept counterfactual
                # (NOT_EXECUTED) like the other rejections below.
                vetoed, veto_reason = tradability_mask_veto(
                    bar.payload, state.quality, bar.event_time,
                    max_spread_frac=manifest.max_spread_frac,
                    funding_window_bars=manifest.funding_window_bars,
                    funding_hours=manifest.funding_hours,
                    interval_ns=_INTERVAL_NS.get(manifest.interval, 3_600_000_000_000))
                if vetoed:
                    self.registry.apply(cid, 'TRIGGERED', 'REJECTED',
                                        TRADABILITY_MASK_VETO, as_of)
                    self.candidates.append({'kind': 'tradability_veto',
                                            'candidate_id': cid, 'detail': veto_reason,
                                            'source': 'risk',
                                            'event_id': f'{cid}:veto:{as_of}'})
                    out = counterfactual(cid, draft, i + 1)
                    self._record_outcome(cid, out.endpoint, out.net_r,
                                         'NOT_EXECUTED', sim.hash(), out.horizon_bars,
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
                    out = counterfactual(cid, draft, i + 1)
                    self._record_outcome(cid, out.endpoint, out.net_r,
                                         'NOT_EXECUTED', sim.hash(), out.horizon_bars,
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
                                         'MATURE', sim.hash())
                    del pending[cid]
                    continue
                self.registry.apply(cid, 'PENDING', 'TRIGGERED', 'trigger_observed', as_of)
                if manifest.round_trip_cost_r >= 0.10:
                    self.registry.apply(cid, 'TRIGGERED', 'REJECTED', 'excess_cost', as_of)
                    out = counterfactual(cid, draft, i + 1)
                    self._record_outcome(cid, out.endpoint, out.net_r,
                                         'NOT_EXECUTED', sim.hash(), out.horizon_bars,
                                         mae_r=out.mae_r, mfe_r=out.mfe_r,
                                         ambiguous_bars=out.ambiguous_bars)
                    del pending[cid]
                    continue
                info['entry_bar'] = i + 1

            # PHASE 3: full self-gating — every cheap expert evaluates the bar.
            for ex in experts:
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
                pending[cid] = {'draft': ev.draft, 'birth_idx': i, 'entry_bar': None,
                                'prior_low': float(pl.value) if pl and pl.value is not None else 0.0,
                                'prior_high': float(ph.value) if ph and ph.value is not None else float('inf')}

        # Epilogue: close whatever the tape end leaves dangling, deterministically.
        last_as_of = bars[-1].available_time if bars else 0
        for cid, pos in list(open_positions.items()):
            sign = 1.0 if pos.draft.direction == 'LONG' else -1.0
            final_close = float(bars[-1].payload['close']) if bars else pos.entry_price
            unit = risk_unit(pos.draft, pos.entry_price)     # R, never percent
            net = sign * (final_close - pos.entry_price) / unit \
                - manifest.round_trip_cost_r - pos.funding_paid_r
            self._record_outcome(cid, 'EXPIRY', net, 'RIGHT_CENSORED',
                                 sim.hash(), pos.bars_held, mae_r=pos.mae_r,
                                 mfe_r=pos.mfe_r, ambiguous_bars=pos.ambiguous_bars)
            self.registry.apply(cid, 'EXECUTED', 'CLOSED', 'expiry_reached', last_as_of)
            gate.release(pos.draft)
        for cid, info in list(pending.items()):
            if self.registry.current(cid) == 'TRIGGERED':
                self.registry.apply(cid, 'TRIGGERED', 'INVALIDATED',
                                    'no_entry_before_tape_end', last_as_of)
                out = counterfactual(cid, info['draft'], len(bars))
                self._record_outcome(cid, out.endpoint, out.net_r,
                                     'RIGHT_CENSORED', sim.hash(), out.horizon_bars,
                                     mae_r=out.mae_r, mfe_r=out.mfe_r,
                                     ambiguous_bars=out.ambiguous_bars)
            elif self.registry.current(cid) == 'PENDING':
                self.registry.apply(cid, 'PENDING', 'EXPIRED', 'expiry_reached', last_as_of)
                self._record_outcome(cid, 'EXPIRY', 0.0, 'RIGHT_CENSORED', sim.hash())

        dist: dict[str, int] = {}
        candidate_ids: set[str] = set()
        for rec in self.candidates.read():
            if 'to_state' not in rec:
                continue
            candidate_ids.add(rec['candidate_id'])
            if rec['to_state'] in TERMINAL:
                dist[rec['to_state']] = dist.get(rec['to_state'], 0) + 1
        # The decision ledger (DATASET_SPEC section 1) binds candidates,
        # evaluations, outcomes AND the persisted MarketState ledger.
        ledger_hash = sha1_hex((self.candidates.hash, self.evaluations.hash,
                                self.outcomes.hash, self.states.hash))
        data_hash = self.tape_log.hash
        verdict = 'NO_ECONOMIC_CLAIM' if manifest.authority_receipt is None else 'CERTIFIED_AVAILABLE'
        return LabReport(experiment_id=manifest.experiment_id,
                         code_hash=manifest.code_hash or _code_hash(),
                         data_hash=manifest.data_hash or data_hash,
                         candidate_count=len(candidate_ids),
                         terminal_distribution=dist, ledger_hash=ledger_hash,
                         verdict=verdict, exposure_conflicts=conflicts)
