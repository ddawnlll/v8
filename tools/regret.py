"""V8 x Recoverable Regret v0.2 — Phase-0 evaluator.

READ-ONLY against the decision path (same write discipline as
`tools/diagnostics.py`). Consumes a completed `v8.lab.Lab` store directory
plus its `manifest.json`/`report.json`; it NEVER re-runs `Lab.run` and never
creates a second Candidate population. Every semantic implemented here is
frozen in `reports/accp/v8-rr-v02-phase0/source/FCR-V8RR-004.accp.yaml` and
this module must not reinterpret those contracts silently — an amendment
gets a new EVALUATOR_VERSION and a CHANGELOG entry (FCR amendment rule 1).

IMPORTANT — population boundary. This evaluator's Candidate population is
the LEDGER population: canonical `episode_key`, lifecycle-gated,
risk-admitted, one real actual action per executed Candidate. It is NOT
`tools/diagnostics.py`'s population (re-detected drafts, entry = birth+lag,
no lifecycle/gates, non-canonical `candidate_id`). The two are never
interchangeable (FER-V8RR-002 RK001, FCR-V8RR-004 OM003).

Pipeline (v0.2 section 13, post-Candidate half only — the pre-Candidate half
already exists as `v8.lab.Lab` and is read, never rebuilt, by this module):

    store dir -> CandidateSnapshot (join)
              -> ledger reconciliation (Replay(C, a_actual, M) == observed)
              -> LegalActionManifest (generate, per Candidate)
              -> ReplayModel adapter (replay each legal action; abstain on
                 an undefined/censored/inapplicable cell rather than fabricate)
              -> ModelDerivedOutcomeCube  (cube.jsonl)
              -> LegalHindsightGap        (regret.jsonl)

Phase 0 computes NO statistics: no slicing, no multiplicity control, no
attribution, no recoverability estimate. It produces a reconciliation
verdict, a cube, and a per-Candidate gap with explicit tie/abstention
handling — nothing else. Every number is labelled MODEL_DERIVED and carries
no economic authority; a positive `legal_hindsight_gap` is not recoverable
loss and is not an improvement target (FCR FT011, V8_CONSTITUTION rule 12).

Two contract gaps discovered during implementation (recorded, not hidden):
  - `CounterfactualOutcome` (schema.py) does not carry `funding_paid_r` —
    only the stepped `OpenPosition` does. On a store whose manifest declares
    a zero funding rate AND whose tape carries no `funding` channel, funding
    is provably zero and `funding_r`/`gross_utility` are reported exactly;
    otherwise they are reported as `None` with an explicit reason rather
    than silently assuming zero. See `_funding_decomposable`.
  - `Lab.run()` previously discarded its own `LabReport` once returned, so a
    completed store could not recover `risk_gate_hash` without re-running
    the lab. `src/v8/lab.py` now additionally persists `report.json`
    alongside `manifest.json` (additive-only; not part of `ledger_hash`).
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))

from v8 import experts as _experts_module
from v8.lab import _code_hash, _geometry_version
from v8.lifecycle import episode_key, TERMINAL
from v8.schema import CandidateDraft, FeatureValue, MarketState, sha1_hex
from v8.simulator import CanonicalSimulator
from v8.store import AppendOnlyLog

EVALUATOR_VERSION = 'regret-phase0-v1'
RECONCILE_TOLERANCE = 1e-12
RECONCILE_EXACT_FIELDS = ('endpoint', 'label_status', 'horizon_bars', 'ambiguous_bars')
RECONCILE_FLOAT_FIELDS = ('net_r', 'entry_price', 'risk_unit_price', 'mae_r',
                          'mfe_r', 'market_move_r')

# Write guard, mirroring tools/diagnostics.py's discipline: this engine may
# only write its own four artifacts, never a decision-path or store file.
_ALLOWED_OUT = ('cube.jsonl', 'regret.jsonl', 'reconciliation.json', 'summary.json')
_PROTECTED_DIRS = ('src', 'docs', 'site', 'research', 'tests', 'tools')


class RegretWriteError(RuntimeError):
    pass


def _guard_no_write(path: Path) -> None:
    if path.name not in _ALLOWED_OUT:
        raise RegretWriteError(f'regret evaluator is read-only; refused to write {path}')
    repo_root = REPO
    try:
        rel = Path(path).resolve().relative_to(repo_root)
    except ValueError:
        return
    for part in rel.parts:
        if part in _PROTECTED_DIRS and part != 'tools':
            raise RegretWriteError(f'refused to write under {part}/: {path}')


# --- Expert registry (generic, by expert_id — NOT hardcoded to the pilots) --

def _expert_registry() -> dict[str, type]:
    registry: dict[str, type] = {}
    for name in _experts_module.__all__:
        if name == 'Expert':
            continue
        cls = getattr(_experts_module, name)
        registry[cls().expert_id] = cls
    return registry


EXPERT_REGISTRY = _expert_registry()


# --- Store loading (FDR AR005 boundary: reader, never a runner) ------------

@dataclass(frozen=True)
class StoreHandle:
    dir: Path
    manifest: dict
    report: dict | None
    tape_log: AppendOnlyLog
    candidates: list
    evaluations: list
    outcomes: list
    states: list


def load_store(store_dir: Path) -> StoreHandle:
    d = Path(store_dir)
    manifest_path = d / 'manifest.json'
    if not manifest_path.exists():
        raise ValueError(f'{d}: no manifest.json — not a completed Lab store')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    tape_log = AppendOnlyLog(d / 'tape.jsonl')
    live_code = _code_hash()
    if manifest.get('code_hash') and manifest['code_hash'] != live_code:
        raise ValueError(
            f'{d}: manifest code_hash {manifest["code_hash"]} != live {live_code}')
    if manifest.get('data_hash') and manifest['data_hash'] != tape_log.hash:
        raise ValueError(
            f'{d}: manifest data_hash {manifest["data_hash"]} != live tape {tape_log.hash}')
    report_path = d / 'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
    return StoreHandle(
        dir=d, manifest=manifest, report=report, tape_log=tape_log,
        candidates=AppendOnlyLog(d / 'candidates.jsonl').read(),
        evaluations=AppendOnlyLog(d / 'evaluations.jsonl').read(),
        outcomes=AppendOnlyLog(d / 'outcomes.jsonl').read(),
        states=AppendOnlyLog(d / 'states.jsonl').read())


def _build_simulator(store: StoreHandle) -> CanonicalSimulator:
    """CONTRACT FT005(a): M is constructed from the run's persisted manifest,
    never from constants written in this module."""
    m = store.manifest
    tape = store.tape_log.replay_tape()
    funding_schedule = tuple(
        (r.event_time, float(r.payload['funding_rate']))
        for r in sorted((r for r in tape if r.channel == 'funding'),
                        key=lambda r: r.event_time))
    return CanonicalSimulator(
        round_trip_cost_r=m['round_trip_cost_r'],
        funding_rate_r=m['funding_rate_r'],
        funding_hours=m['funding_hours'],
        fill_policy=m['fill_policy'],
        funding_schedule=funding_schedule,
        round_trip_cost_bps=m.get('round_trip_cost_bps'))


def _funding_decomposable(store: StoreHandle) -> bool:
    """True iff funding is PROVABLY zero for every episode in this store, so
    gross_utility = net_utility + cost_r holds exactly without needing the
    (unrecoverable, see module docstring) per-episode funding_paid_r."""
    if float(store.manifest.get('funding_rate_r', 0.0)) != 0.0:
        return False
    return not any(r.channel == 'funding' for r in store.tape_log.replay_tape())


def _deserialize_state(rec: dict) -> MarketState:
    features = {k: FeatureValue(**v) for k, v in rec['features'].items()}
    return MarketState(state_id=rec['state_id'], as_of=rec['as_of'],
                       universe=tuple(rec['universe']), features=features,
                       lineage_hash=rec['lineage_hash'],
                       quality=rec.get('quality', 'COMPLETE'),
                       provenance=rec.get('provenance'))


def _states_by_time(store: StoreHandle) -> dict:
    """CONTRACT (PIT lineage, FCR FT001c): states are READ from states.jsonl,
    never recomputed — a second computation of phi would be a second Replay
    Model in disguise."""
    return {rec['as_of']: _deserialize_state(rec) for rec in store.states}


def _bars_by_time(store: StoreHandle):
    tape = sorted(store.tape_log.replay_tape(), key=lambda r: r.available_time)
    bars = [r for r in tape if r.channel == 'kline' and r.payload.get('closed') is True]
    idx_by_time = {b.available_time: i for i, b in enumerate(bars)}
    return bars, idx_by_time


# --- CandidateSnapshot (FCR FT001) ------------------------------------------

@dataclass(frozen=True)
class CandidateSnapshot:
    candidate_id: str
    expert_id: str
    expert_version: str
    instrument: str
    direction: str
    setup_anchor_event_id: str
    geometry_version: str
    birth_time: int
    birth_state_id: str | None
    risk_geometry: dict
    size: float
    terminal_state: str | None
    terminal_reason_code: str | None
    entry_bar_available_time: int | None
    observed_outcome: dict | None
    binding_status: str        # BOUND | UNBOUND_NO_DRAFT
    raw_draft: dict | None     # full draft dict — avoids the setup_fingerprint
                                # information loss a field-by-field snapshot
                                # would incur when reconstructing CandidateDraft


def build_snapshots(store: StoreHandle) -> list[CandidateSnapshot]:
    """CONTRACT FT001: identity = lifecycle.episode_key alone; the join is a
    RE-DERIVATION of that key (never a stored foreign key, FER CA010) and a
    candidate whose draft cannot be bound is reported UNBOUND_NO_DRAFT, never
    dropped or defaulted."""
    drafts_by_cid: dict[str, dict] = {}
    for rec in store.evaluations:
        d = rec.get('draft')
        if not d:
            continue
        draft = CandidateDraft(**d)
        cid = episode_key(draft.expert_id, draft.expert_version, draft.instrument,
                          draft.direction, draft.setup_anchor_event_id,
                          _geometry_version(draft))
        drafts_by_cid.setdefault(cid, d)

    trans_by_cid: dict[str, list] = {}
    for rec in store.candidates:
        if 'to_state' not in rec:
            continue
        trans_by_cid.setdefault(rec['candidate_id'], []).append(rec)

    outcome_by_cid = {o['candidate_id']: o for o in store.outcomes}

    snapshots: list[CandidateSnapshot] = []
    for cid, trans in sorted(trans_by_cid.items()):
        trans.sort(key=lambda r: r['sequence'])
        detected = next((t for t in trans if t['to_state'] == 'DETECTED'), None)
        executed = next((t for t in trans if t['to_state'] == 'EXECUTED'), None)
        terminal = next((t for t in reversed(trans) if t['to_state'] in TERMINAL), None)
        draft = drafts_by_cid.get(cid)
        entry_time = executed['knowledge_time'] if executed else None

        if draft is None:
            snapshots.append(CandidateSnapshot(
                candidate_id=cid,
                expert_id=(detected or {}).get('expert_id', ''),
                expert_version=(detected or {}).get('expert_version', ''),
                instrument=(detected or {}).get('instrument', ''),
                direction=(detected or {}).get('direction', ''),
                setup_anchor_event_id=(detected or {}).get('setup_anchor_event_id', ''),
                geometry_version=(detected or {}).get('geometry_version', ''),
                birth_time=(detected or {}).get('knowledge_time', 0),
                birth_state_id=(detected or {}).get('state_id'),
                risk_geometry={}, size=1.0,
                terminal_state=terminal['to_state'] if terminal else None,
                terminal_reason_code=(terminal or {}).get('reason_code'),
                entry_bar_available_time=entry_time,
                observed_outcome=outcome_by_cid.get(cid),
                binding_status='UNBOUND_NO_DRAFT', raw_draft=None))
            continue

        snapshots.append(CandidateSnapshot(
            candidate_id=cid, expert_id=draft['expert_id'],
            expert_version=draft['expert_version'], instrument=draft['instrument'],
            direction=draft['direction'],
            setup_anchor_event_id=draft['setup_anchor_event_id'],
            geometry_version=(detected or {}).get('geometry_version', ''),
            birth_time=draft['birth_time'],
            birth_state_id=(detected or {}).get('state_id'),
            risk_geometry=draft['risk_geometry'], size=draft.get('size', 1.0),
            terminal_state=terminal['to_state'] if terminal else None,
            terminal_reason_code=(terminal or {}).get('reason_code'),
            entry_bar_available_time=entry_time,
            observed_outcome=outcome_by_cid.get(cid),
            binding_status='BOUND', raw_draft=draft))
    return snapshots


def assert_pit_lineage(store: StoreHandle, snapshots: list) -> list:
    """CONTRACT (PIT lineage verification, FCR FT001c / RIR GR006). Asserts,
    does not build: every BOUND snapshot's birth_state_id resolves in
    states.jsonl, and no feature's max_input_available_time exceeds that
    state's own as_of. Returns a list of violation strings (empty = clean)
    rather than raising, so a caller can decide severity."""
    states = {s['state_id']: s for s in store.states}
    problems: list[str] = []
    for snap in snapshots:
        if snap.binding_status != 'BOUND':
            continue
        if snap.birth_state_id is None:
            problems.append(f'{snap.candidate_id}: no birth_state_id recorded')
            continue
        st = states.get(snap.birth_state_id)
        if st is None:
            problems.append(
                f'{snap.candidate_id}: birth_state_id {snap.birth_state_id} '
                'not found in states.jsonl')
            continue
        as_of = st['as_of']
        for fname, fv in st['features'].items():
            mia = fv.get('max_input_available_time', 0)
            if mia > as_of:
                problems.append(
                    f'{snap.candidate_id}: feature {fname} max_input_available_time '
                    f'{mia} > decision clock {as_of} — future leakage')
    return problems


# --- Ledger reconciliation (FCR FT010) --------------------------------------

@dataclass(frozen=True)
class ReconciliationResult:
    n_executed: int
    n_reconciled: int
    n_mismatched: int
    n_not_applicable: int
    mismatches: tuple
    max_abs_deviation: dict
    verdict: str   # RECONCILED | RECONCILIATION_FAILED


def reconcile_actual_actions(store: StoreHandle, snapshots: list) -> ReconciliationResult:
    """CONTRACT FT010: Replay(C, a_actual, M) must equal the observed ledger
    outcome exactly on the enumerated fields; excluded fields (admission
    size, equity/heat state, pre-entry gates) per FT010(b). Not applicable to
    candidates that never entered (FT010c)."""
    sim = _build_simulator(store)
    bars, idx_by_time = _bars_by_time(store)
    states_by_time = _states_by_time(store)

    n_exec = n_ok = n_bad = n_na = 0
    mismatches: list = []
    max_dev = {f: 0.0 for f in RECONCILE_FLOAT_FIELDS}

    for snap in snapshots:
        if snap.binding_status != 'BOUND' or snap.entry_bar_available_time is None:
            n_na += 1
            continue
        n_exec += 1
        i = idx_by_time.get(snap.entry_bar_available_time)
        obs = snap.observed_outcome
        if i is None or obs is None:
            n_bad += 1
            mismatches.append((snap.candidate_id, 'entry_bar_or_outcome_missing'))
            continue
        draft = CandidateDraft(**snap.raw_draft)
        owner_cls = EXPERT_REGISTRY.get(snap.expert_id)
        owner = owner_cls() if owner_cls else None
        tail = bars[i:]

        def thesis_ok(t_ns, _payload, _owner=owner, _draft=draft):
            if _owner is None or t_ns is None:
                return True
            st = states_by_time.get(t_ns)
            return _owner.still_valid(st, _draft) if st is not None else True

        replayed = sim.run(draft, [b.payload for b in tail],
                           times=[b.available_time for b in tail],
                           thesis_valid=thesis_ok)

        ok = True
        for f in RECONCILE_EXACT_FIELDS:
            if getattr(replayed, f) != obs.get(f):
                ok = False
        for f in RECONCILE_FLOAT_FIELDS:
            dev = abs(getattr(replayed, f) - float(obs.get(f, 0.0)))
            max_dev[f] = max(max_dev[f], dev)
            if dev > RECONCILE_TOLERANCE:
                ok = False
        if ok:
            n_ok += 1
        else:
            n_bad += 1
            mismatches.append((snap.candidate_id, 'field_mismatch'))

    verdict = 'RECONCILED' if n_bad == 0 else 'RECONCILIATION_FAILED'
    return ReconciliationResult(n_exec, n_ok, n_bad, n_na, tuple(mismatches),
                                max_dev, verdict)


# --- Legal action manifest (FCR FT003) --------------------------------------

# FT003(e): pyramid_add_rules is declared-but-fails-closed in the simulator;
# the generator must never manufacture a variant that adds it. direction is
# excluded structurally — it is never a risk_geometry key, so it is simply
# never touched by this generator.
_EXCLUDED_VARIANT_KEYS = ('pyramid_add_rules',)

# FT003(d): the declared continuous grid. Kept deliberately small — grid
# cardinality is itself search burden (FER RK005) and Phase 0 computes no
# statistics, so a larger grid buys nothing here.
CONTINUOUS_AXIS_GRID = {'target_r': (1.0, 2.0, 3.0), 'expiry_bars': (8, 24, 48)}
GENERATOR_VERSION = 'legal-action-manifest-v1'


@dataclass(frozen=True)
class LegalAction:
    action_id: str
    kind: str            # NO_TRADE | GEOMETRY_VARIANT
    provenance: str       # ACTUAL | DECLARED_VARIANT
    override: dict
    axes_touched: tuple


@dataclass(frozen=True)
class LegalActionManifest:
    manifest_id: str
    actions: tuple
    cardinality: int
    continuous_axes_sampled: dict
    generator_version: str


def _action_id(override: dict) -> str:
    return sha1_hex(sorted(override.items())) if override else 'NO_TRADE'


def generate_legal_actions(actual_geometry: dict) -> LegalActionManifest:
    """A(C) per FCR FT003. Element 0 is always NO_TRADE; element 1 is always
    the ACTUAL action, seeded directly from the frozen draft geometry — so
    a_actual in A_t holds by construction, not by a lucky grid (FER LA005)."""
    actions: list[LegalAction] = [LegalAction('NO_TRADE', 'NO_TRADE',
                                              'DECLARED_VARIANT', {}, ())]
    seen_ids = {'NO_TRADE'}

    actual_override = dict(actual_geometry)
    actual_id = _action_id(actual_override)
    actions.append(LegalAction(actual_id, 'GEOMETRY_VARIANT', 'ACTUAL',
                               actual_override, tuple(sorted(actual_override))))
    seen_ids.add(actual_id)

    if not any(k in actual_geometry for k in _EXCLUDED_VARIANT_KEYS):
        for target_r in CONTINUOUS_AXIS_GRID['target_r']:
            for expiry_bars in CONTINUOUS_AXIS_GRID['expiry_bars']:
                override = dict(actual_geometry)
                override['target_r'] = target_r
                override['expiry_bars'] = expiry_bars
                aid = _action_id(override)
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)
                actions.append(LegalAction(aid, 'GEOMETRY_VARIANT', 'DECLARED_VARIANT',
                                           override, ('target_r', 'expiry_bars')))

    manifest_id = sha1_hex((tuple((a.action_id, tuple(sorted(a.override.items())))
                                  for a in actions), GENERATOR_VERSION))
    return LegalActionManifest(manifest_id=manifest_id, actions=tuple(actions),
                               cardinality=len(actions),
                               continuous_axes_sampled=CONTINUOUS_AXIS_GRID,
                               generator_version=GENERATOR_VERSION)


# --- Cell status / abstention (FCR FT009) -----------------------------------

CELL_OK = 'OK'
CELL_CENSORED = 'CENSORED'
CELL_UNDEFINED_FUTURE = 'UNDEFINED_FUTURE'
CELL_NOT_EVALUABLE_ACTION = 'NOT_EVALUABLE_ACTION'
CELL_NO_ENTRY = 'NO_ENTRY'

# Fewer than this many bars of future after the entry bar -> the simulator
# would return a manufactured EXPIRY value (measured: entry-only tail ->
# EXPIRY/-cost; empty tail -> EXPIRY/0.0), never a real outcome. Refuse
# instead of accepting it (FER RM008).
MIN_FUTURE_BARS = 1


@dataclass(frozen=True)
class OutcomeCubeRow:
    candidate_id: str
    action_id: str
    simulator_hash: str
    data_hash: str
    code_hash: str
    config_hash: str
    risk_gate_hash: str | None
    action_manifest_id: str
    evaluator_version: str
    platform: str
    utility_unit: str
    net_utility: float | None
    gross_utility: float | None
    cost_r: float | None
    cost_form: str
    funding_r: float | None
    slippage: str
    endpoint: str | None
    label_status: str | None
    horizon_bars: int | None
    mae_r: float | None
    mfe_r: float | None
    ambiguous_bars: int | None
    entry_price: float | None
    risk_unit_price: float | None
    market_move_r: float | None
    label_available_time: int | None
    epistemic_class: str
    cell_status: str
    cell_status_reason: str


def replay_action(store: StoreHandle, sim: CanonicalSimulator, snap: CandidateSnapshot,
                  action: LegalAction, bars: list, idx_by_time: dict,
                  states_by_time: dict, manifest_id: str,
                  risk_gate_hash: str | None, funding_ok: bool, *,
                  code_hash: str | None = None) -> OutcomeCubeRow:
    """CONTRACT FT005/FT009: the adapter's ONE new semantic responsibility —
    refuse rather than accept a fabricated number. Every branch either
    returns a MATURE/CENSORED model-derived row or an explicit abstention;
    none falls through to the simulator's degenerate-future behaviour."""
    cost_form = ('flat' if store.manifest.get('round_trip_cost_bps') is None
                else f"bps:{store.manifest['round_trip_cost_bps']}")
    resolved_code_hash = _code_hash() if code_hash is None else code_hash
    prov = dict(simulator_hash=sim.hash(), data_hash=store.tape_log.hash,
               code_hash=resolved_code_hash, config_hash=sha1_hex(store.manifest),
               risk_gate_hash=risk_gate_hash, action_manifest_id=manifest_id,
               evaluator_version=EVALUATOR_VERSION, platform=platform.platform())

    def _row(cell_status: str, cell_status_reason: str, **kw) -> OutcomeCubeRow:
        base = dict(candidate_id=snap.candidate_id, action_id=action.action_id,
                   utility_unit='R', slippage='NOT_APPLICABLE',
                   epistemic_class='MODEL_DERIVED', cost_form=cost_form,
                   net_utility=None, gross_utility=None, cost_r=None, funding_r=None,
                   endpoint=None, label_status=None, horizon_bars=None, mae_r=None,
                   mfe_r=None, ambiguous_bars=None, entry_price=None,
                   risk_unit_price=None, market_move_r=None, label_available_time=None,
                   cell_status=cell_status, cell_status_reason=cell_status_reason)
        base.update(prov)
        base.update(kw)
        return OutcomeCubeRow(**base)

    if snap.entry_bar_available_time is None:
        return _row(CELL_NO_ENTRY, 'candidate has no actual entry bar')

    if action.kind == 'NO_TRADE':
        # FT011(i): NO_TRADE utility is exactly 0.0 R by definition — no
        # simulator call (FER LA001).
        return _row(CELL_OK, '', net_utility=0.0, gross_utility=0.0, cost_r=0.0,
                   funding_r=0.0, endpoint='NO_TRADE', label_status='NOT_EXECUTED',
                   horizon_bars=0)

    i = idx_by_time.get(snap.entry_bar_available_time)
    if i is None:
        return _row(CELL_NOT_EVALUABLE_ACTION, 'entry bar not found in tape')

    tail = bars[i:]
    if len(tail) <= MIN_FUTURE_BARS:
        return _row(CELL_UNDEFINED_FUTURE,
                   f'fewer than {MIN_FUTURE_BARS + 1} bars of future after the entry '
                   'bar — the simulator would return a manufactured EXPIRY value')

    geom = dict(snap.risk_geometry)
    geom.update(action.override)
    try:
        draft = CandidateDraft(**{**snap.raw_draft, 'risk_geometry': geom})
    except Exception as exc:  # noqa: BLE001 — surfaced as an explicit abstention, not a crash
        return _row(CELL_NOT_EVALUABLE_ACTION, f'draft construction failed: {exc!r}')

    owner_cls = EXPERT_REGISTRY.get(snap.expert_id)
    owner = owner_cls() if owner_cls else None

    def thesis_ok(t_ns, _payload, _owner=owner, _draft=draft):
        if _owner is None or t_ns is None:
            return True
        st = states_by_time.get(t_ns)
        return _owner.still_valid(st, _draft) if st is not None else True

    try:
        out = sim.run(draft, [b.payload for b in tail],
                      times=[b.available_time for b in tail], thesis_valid=thesis_ok)
    except Exception as exc:  # noqa: BLE001
        return _row(CELL_NOT_EVALUABLE_ACTION, f'replay raised: {exc!r}')

    if out.label_status == 'NOT_EXECUTED':
        return _row(CELL_NOT_EVALUABLE_ACTION,
                   'action never filled on this tape (e.g. FILL_AT_LIMIT never '
                   'traded through)')

    cost = sim.cost_r(out.entry_price, out.risk_unit_price) if out.entry_price else 0.0
    if funding_ok:
        funding_r = 0.0
        gross = out.net_r + cost
    else:
        # Module-docstring gap: funding_paid_r is not recoverable from a
        # CounterfactualOutcome. Report None honestly rather than assume 0.
        funding_r = None
        gross = None

    status = CELL_OK if out.label_status == 'MATURE' else CELL_CENSORED
    reason = '' if status == CELL_OK else 'replay reached tape end before a terminal endpoint'
    return _row(status, reason, net_utility=out.net_r, gross_utility=gross,
               cost_r=cost, funding_r=funding_r, endpoint=out.endpoint,
               label_status=out.label_status, horizon_bars=out.horizon_bars,
               mae_r=out.mae_r, mfe_r=out.mfe_r, ambiguous_bars=out.ambiguous_bars,
               entry_price=out.entry_price, risk_unit_price=out.risk_unit_price,
               market_move_r=out.market_move_r,
               label_available_time=out.label_available_time)


def write_cube(store: StoreHandle, cube_path: Path, snapshots: list
              ) -> tuple[dict, int]:
    """Writes cube.jsonl (FE001: source='regret-cube',
    event_id=f'{candidate_id}:{action_id}'). Returns
    (manifest_by_candidate_id, row_count)."""
    _guard_no_write(cube_path)
    cube_log = AppendOnlyLog(cube_path)
    sim = _build_simulator(store)
    bars, idx_by_time = _bars_by_time(store)
    states_by_time = _states_by_time(store)
    risk_gate_hash = (store.report or {}).get('risk_gate_hash')
    funding_ok = _funding_decomposable(store)
    code_hash = _code_hash()

    manifests: dict[str, LegalActionManifest] = {}
    n_rows = 0
    for snap in snapshots:
        if snap.binding_status != 'BOUND':
            continue
        manifest = generate_legal_actions(snap.risk_geometry)
        manifests[snap.candidate_id] = manifest
        for action in manifest.actions:
            row = replay_action(store, sim, snap, action, bars, idx_by_time,
                                states_by_time, manifest.manifest_id,
                                risk_gate_hash, funding_ok,
                                code_hash=code_hash)
            rec = asdict(row)
            rec['source'] = 'regret-cube'
            rec['event_id'] = f'{snap.candidate_id}:{action.action_id}'
            cube_log.append(rec)
            n_rows += 1
    cube_log.close()
    return manifests, n_rows


# --- Legal hindsight gap (FCR FT011) ----------------------------------------

GAP_COMPUTED = 'COMPUTED'
GAP_ABSTAINED_CENSORED = 'ABSTAINED_CENSORED'
GAP_ABSTAINED_UNDEFINED = 'ABSTAINED_UNDEFINED'
GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION = 'NOT_APPLICABLE_NO_ACTUAL_ACTION'
GAP_OUTSIDE_CANDIDATE_UNIVERSE = 'OUTSIDE_CANDIDATE_UNIVERSE'
GAP_TIE_EPS = 1e-12


@dataclass(frozen=True)
class RegretRecord:
    candidate_id: str
    action_manifest_id: str | None
    actual_action_id: str | None
    actual_utility: float | None
    best_utility: float | None
    best_action_ids: tuple
    tie_cardinality: int
    legal_hindsight_gap: float | None
    gap_status: str
    abstention_reason: str


def compute_gap(candidate_id: str, manifest, cube_rows: list) -> RegretRecord:
    """CONTRACT FT011: g = max_a tilde_U(a) - tilde_U(a_actual). Ties are
    REPORTED, never broken (measured tie_cardinality 3 on 4/12 golden
    candidates — FER LHG002, a common case). Abstains whenever any cell
    that could be the maximum is not cell_status OK, rather than maximizing
    over a mixture of complete and incomplete outcomes (FER OC003)."""
    if manifest is None or not cube_rows:
        return RegretRecord(candidate_id, None, None, None, None, (), 0, None,
                            GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION,
                            'candidate has no actual entry bar')

    actual = next((a for a in manifest.actions if a.provenance == 'ACTUAL'), None)
    by_action = {r['action_id']: r for r in cube_rows}
    if actual is None or actual.action_id not in by_action:
        return RegretRecord(candidate_id, manifest.manifest_id, None, None, None,
                            (), 0, None, GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION,
                            'no ACTUAL action in the generated manifest')

    actual_row = by_action[actual.action_id]
    if actual_row['cell_status'] != CELL_OK:
        return RegretRecord(candidate_id, manifest.manifest_id, actual.action_id,
                            None, None, (), 0, None, GAP_ABSTAINED_UNDEFINED,
                            f"actual action cell is {actual_row['cell_status']}: "
                            f"{actual_row['cell_status_reason']}")
    actual_utility = actual_row['net_utility']

    censored = [r for r in cube_rows if r['cell_status'] == CELL_CENSORED]
    if censored:
        return RegretRecord(candidate_id, manifest.manifest_id, actual.action_id,
                            actual_utility, None, (), 0, None, GAP_ABSTAINED_CENSORED,
                            f'{len(censored)} action(s) reached tape end before a '
                            'terminal endpoint; their eventual outcome could exceed '
                            'the best fully-observed cell')

    ok_rows = [r for r in cube_rows if r['cell_status'] == CELL_OK]
    if not ok_rows:
        return RegretRecord(candidate_id, manifest.manifest_id, actual.action_id,
                            actual_utility, None, (), 0, None, GAP_ABSTAINED_UNDEFINED,
                            'no cell_status OK cell to maximize over')

    best_ok = max(r['net_utility'] for r in ok_rows)
    tie_set = tuple(sorted(r['action_id'] for r in ok_rows
                           if abs(r['net_utility'] - best_ok) < GAP_TIE_EPS))
    gap = best_ok - actual_utility
    return RegretRecord(candidate_id, manifest.manifest_id, actual.action_id,
                        actual_utility, best_ok, tie_set, len(tie_set), gap,
                        GAP_COMPUTED, '')


def write_gaps(regret_path: Path, snapshots: list, manifests: dict,
              cube_rows_by_cid: dict) -> int:
    """FE002: one row per Candidate in the store, INCLUDING candidates with
    no actual action — a missing row is always a defect, never a silent
    exclusion."""
    _guard_no_write(regret_path)
    log = AppendOnlyLog(regret_path)
    n = 0
    for snap in snapshots:
        if snap.binding_status != 'BOUND':
            rec_status, reason = GAP_OUTSIDE_CANDIDATE_UNIVERSE, 'draft unbound'
            record = RegretRecord(snap.candidate_id, None, None, None, None, (), 0,
                                  None, rec_status, reason)
        else:
            record = compute_gap(snap.candidate_id, manifests.get(snap.candidate_id),
                                 cube_rows_by_cid.get(snap.candidate_id, []))
        rec = asdict(record)
        rec['source'] = 'regret-gap'
        rec['event_id'] = snap.candidate_id
        log.append(rec)
        n += 1
    log.close()
    return n


# --- Orchestration + CLI ----------------------------------------------------

def run_phase0(store_dir: Path, out_dir: Path, *, reconcile_only: bool = False) -> dict:
    store = load_store(store_dir)
    snapshots = build_snapshots(store)
    lineage_problems = assert_pit_lineage(store, snapshots)
    recon = reconcile_actual_actions(store, snapshots)

    summary = {
        'store_dir': str(store.dir), 'evaluator_version': EVALUATOR_VERSION,
        'n_candidates': len(snapshots),
        'n_unbound': sum(1 for s in snapshots if s.binding_status == 'UNBOUND_NO_DRAFT'),
        'pit_lineage_problems': lineage_problems,
        'reconciliation': asdict(recon),
    }

    if recon.verdict != 'RECONCILED' or lineage_problems:
        summary['halted'] = True
        summary['halt_reason'] = (
            'reconciliation failed — load-bearing invariant broken, refusing to '
            'produce a cube' if recon.verdict != 'RECONCILED' else
            'PIT lineage violation detected — future leakage, refusing to proceed')
        return summary
    summary['halted'] = False

    if reconcile_only:
        return summary

    out = Path(out_dir)
    cube_path, regret_path = out / 'cube.jsonl', out / 'regret.jsonl'
    if cube_path.exists() or regret_path.exists():
        raise ValueError(f'{out}: already contains regret evidence; compile-once — '
                         'use a fresh out dir')
    out.mkdir(parents=True, exist_ok=True)

    manifests, n_cube_rows = write_cube(store, cube_path, snapshots)
    cube_rows_by_cid: dict[str, list] = {}
    for rec in AppendOnlyLog(cube_path).read():
        cube_rows_by_cid.setdefault(rec['candidate_id'], []).append(rec)
    n_gap_rows = write_gaps(regret_path, snapshots, manifests, cube_rows_by_cid)

    summary['n_cube_rows'] = n_cube_rows
    summary['n_gap_rows'] = n_gap_rows
    (out / 'summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, default=list) + '\n',
        encoding='utf-8')
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--store', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reconcile-only', action='store_true')
    args = ap.parse_args(argv)
    summary = run_phase0(args.store, args.out, reconcile_only=args.reconcile_only)
    print(json.dumps(summary, sort_keys=True, indent=2, default=list))
    return 1 if summary.get('halted') else 0


if __name__ == '__main__':
    raise SystemExit(main())
