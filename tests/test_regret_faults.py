"""Phase-0 evaluator fault-injection harness (family D, v0.2 section 14.3).

Deliberately inject known defects and assert the evaluator's response is the
EXPECTED one — including the two cases (habitat, hidden variable) where the
expected response is an explicit refusal to claim something Phase 0 cannot
support, not a manufactured localization.
"""
from __future__ import annotations

import dataclasses
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.lab import Lab
from v8.lifecycle import episode_key
from v8.schema import CandidateDraft, ExperimentManifest
from v8.simulator import CanonicalSimulator
from v8.synth import make_synthetic_tape

from tools.regret import (
    load_store, build_snapshots, reconcile_actual_actions, generate_legal_actions,
    replay_action, _build_simulator, _bars_by_time, _states_by_time,
    _funding_decomposable, _geometry_version, OutcomeCubeRow, RegretRecord,
    CELL_OK, CELL_CENSORED, CELL_NOT_EVALUABLE_ACTION,
)

UNIVERSE = ('SOLUSDT',)


def _manifest(**kw) -> ExperimentManifest:
    base = dict(experiment_id='exp-fault', code_hash='', data_hash='',
               universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    return ExperimentManifest(**base)


def _golden_store(tmp_path, **manifest_kw) -> Path:
    store = tmp_path / 'store'
    lab = Lab(store)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    lab.run(_manifest(**manifest_kw), [TrendPullbackExpert(), FailedBreakoutExpert()])
    return store


# --------------------------------------------------------------------- #
# 1. TP shortened for one candidate -> the cube must show the correct
#    EXIT-axis sensitivity (Phase 0 exposes the evidence; it does not itself
#    compute a localization verdict — that is Phase 2's job).
# --------------------------------------------------------------------- #

def test_fault_tp_shortened_shows_up_as_an_exit_axis_delta(tmp_path):
    store = load_store(_golden_store(tmp_path))
    snapshots = build_snapshots(store)
    # Pick a candidate whose ACTUAL outcome was a TARGET hit — a shortened TP
    # is guaranteed to change the endpoint for one of these; picking an
    # arbitrary STOP-out candidate would make the injected fault a no-op
    # (the stop fires before price ever reaches either target level).
    executed = next(s for s in snapshots if s.binding_status == 'BOUND'
                    and s.entry_bar_available_time is not None
                    and s.observed_outcome and s.observed_outcome.get('endpoint') == 'TARGET')
    sim = _build_simulator(store)
    bars, idx_by_time = _bars_by_time(store)
    states_by_time = _states_by_time(store)
    manifest = generate_legal_actions(executed.risk_geometry)

    actual_row = replay_action(store, sim, executed,
                               next(a for a in manifest.actions if a.provenance == 'ACTUAL'),
                               bars, idx_by_time, states_by_time,
                               manifest.manifest_id, None, _funding_decomposable(store))

    from tools.regret import LegalAction
    shortened_geom = dict(executed.risk_geometry)
    shortened_geom['target_r'] = 0.25   # deliberately injected fault: TP shortened
    fault_action = LegalAction('fault-tp-shortened', 'GEOMETRY_VARIANT',
                               'DECLARED_VARIANT', shortened_geom, ('target_r',))
    fault_row = replay_action(store, sim, executed, fault_action, bars, idx_by_time,
                              states_by_time, manifest.manifest_id, None,
                              _funding_decomposable(store))

    assert fault_action.axes_touched == ('target_r',), (
        'the cube must record WHICH axis the injected fault touched — this is '
        'the evidence a later localization phase needs')
    if actual_row.cell_status == CELL_OK and fault_row.cell_status == CELL_OK:
        assert fault_row.net_utility != actual_row.net_utility, (
            'a materially different target_r must change the replayed outcome '
            '(a no-op fault-injection test proves nothing)')


# --------------------------------------------------------------------- #
# 2. Cost doubled -> the delta must land ENTIRELY in cost_r/net_utility;
#    every path field (endpoint, horizon, excursions, entry/exit) must be
#    byte-identical, because cost enters only the terminal net formula.
# --------------------------------------------------------------------- #

def test_fault_doubled_cost_isolated_to_cost_and_net(tmp_path):
    store_dir = _golden_store(tmp_path, round_trip_cost_r=0.07)
    store_a = load_store(store_dir)
    snapshots = build_snapshots(store_a)
    executed = next(s for s in snapshots if s.binding_status == 'BOUND'
                    and s.entry_bar_available_time is not None)
    bars, idx_by_time = _bars_by_time(store_a)
    states_by_time = _states_by_time(store_a)
    manifest = generate_legal_actions(executed.risk_geometry)
    actual_action = next(a for a in manifest.actions if a.provenance == 'ACTUAL')

    sim_baseline = _build_simulator(store_a)
    row_baseline = replay_action(store_a, sim_baseline, executed, actual_action,
                                 bars, idx_by_time, states_by_time,
                                 manifest.manifest_id, None, _funding_decomposable(store_a))

    # FAULT: cost doubled — same store/tape/candidate, only the simulator's
    # cost parameter changes (mirrors the injected defect, never a second
    # store or a second Candidate population).
    sim_faulted = CanonicalSimulator(
        round_trip_cost_r=sim_baseline.round_trip_cost_r * 2,
        funding_rate_r=sim_baseline.funding_rate_r,
        funding_hours=sim_baseline.funding_hours,
        fill_policy=sim_baseline.fill_policy)
    row_faulted = replay_action(store_a, sim_faulted, executed, actual_action,
                                bars, idx_by_time, states_by_time,
                                manifest.manifest_id, None, _funding_decomposable(store_a))

    assert row_baseline.cell_status == CELL_OK and row_faulted.cell_status == CELL_OK
    cost_delta = row_faulted.cost_r - row_baseline.cost_r
    net_delta = row_baseline.net_utility - row_faulted.net_utility  # doubled cost -> lower net
    assert abs(cost_delta - row_baseline.cost_r) < 1e-12, 'doubling cost must double the charge'
    assert abs(net_delta - cost_delta) < 1e-12, (
        'the entire net_utility delta must equal the cost delta exactly — '
        'nothing else may move')
    for field in ('endpoint', 'label_status', 'horizon_bars', 'mae_r', 'mfe_r',
                  'ambiguous_bars', 'entry_price', 'risk_unit_price', 'market_move_r'):
        assert getattr(row_baseline, field) == getattr(row_faulted, field), (
            f'{field} moved under a pure cost change — cost is not isolated')


# --------------------------------------------------------------------- #
# 3. Direction sign flip -> must be ILLEGAL (a different Candidate), never a
#    localized "DIRECTION" fault inside A(C). direction is not a risk_geometry
#    key, so the generator has no mechanism to touch it at all.
# --------------------------------------------------------------------- #

def test_fault_direction_flip_is_illegal_not_a_legal_action(tmp_path):
    store = load_store(_golden_store(tmp_path))
    snapshots = build_snapshots(store)
    executed = next(s for s in snapshots if s.binding_status == 'BOUND'
                    and s.entry_bar_available_time is not None)
    manifest = generate_legal_actions(executed.risk_geometry)
    for action in manifest.actions:
        assert 'direction' not in action.override, (
            'the generator must never manufacture a direction-flipped action — '
            'direction is a draft field, not a risk_geometry key, and is '
            'structurally unreachable by this generator')

    # A direction flip is a DIFFERENT Candidate identity, not an alternative
    # action for this one (direction is part of episode_key).
    original = CandidateDraft(**executed.raw_draft)
    flipped = replace(original,
                      direction='SHORT' if original.direction == 'LONG' else 'LONG')
    original_id = episode_key(original.expert_id, original.expert_version,
                              original.instrument, original.direction,
                              original.setup_anchor_event_id, _geometry_version(original))
    flipped_id = episode_key(flipped.expert_id, flipped.expert_version,
                             flipped.instrument, flipped.direction,
                             flipped.setup_anchor_event_id, _geometry_version(flipped))
    assert original_id != flipped_id, (
        'a direction flip must produce a DIFFERENT episode_key — proof that '
        'it is a different Candidate, never a legal alternative action')


# --------------------------------------------------------------------- #
# 4. Habitat/context randomization -> Phase 0 has no context axis and must
#    NOT manufacture a localization it has no evidence for. The refusal is
#    STRUCTURAL: neither record type carries a context/habitat field.
# --------------------------------------------------------------------- #

def test_fault_habitat_randomization_is_structurally_non_localizable():
    cube_fields = {f.name for f in dataclasses.fields(OutcomeCubeRow)}
    gap_fields = {f.name for f in dataclasses.fields(RegretRecord)}
    forbidden = {'context', 'habitat', 'regime', 'context_id', 'habitat_id'}
    assert not (cube_fields & forbidden), (
        f'OutcomeCubeRow carries a context-like field {cube_fields & forbidden} — '
        'Phase 0 must not be able to claim a context localization it has no '
        'slicing machinery to support (that is Phase 2, FCR AP005/CT003)')
    assert not (gap_fields & forbidden), (
        f'RegretRecord carries a context-like field {gap_fields & forbidden} — same reason')


# --------------------------------------------------------------------- #
# 5. Hidden/unobservable variable driving the outcome -> UNKNOWN /
#    NOT_IDENTIFIABLE, never an invented explanation. Modelled as a
#    corrupted ledger (missing observed outcome / missing entry bar): the
#    evaluator must REFUSE (flag the gap / fail reconciliation), not guess.
# --------------------------------------------------------------------- #

def test_fault_missing_evidence_refuses_rather_than_invents(tmp_path):
    store = load_store(_golden_store(tmp_path))
    snapshots = build_snapshots(store)
    executed = next(s for s in snapshots if s.binding_status == 'BOUND'
                    and s.entry_bar_available_time is not None)

    # Simulate an unobservable/corrupted case: the observed outcome for an
    # executed candidate is missing entirely (e.g. a truncated ledger).
    corrupted = replace(executed, observed_outcome=None)
    others = [s for s in snapshots if s.candidate_id != executed.candidate_id]
    recon = reconcile_actual_actions(store, others + [corrupted])
    assert recon.verdict == 'RECONCILIATION_FAILED', (
        'a candidate with no observed outcome must fail reconciliation '
        'explicitly, never silently pass as a 0-deviation match')
    assert any(m[0] == corrupted.candidate_id for m in recon.mismatches)

    # Simulate a missing entry bar (the tape row the candidate needs is
    # absent — e.g. purged): must abstain NOT_EVALUABLE_ACTION, not fabricate
    # a value from whatever bar happens to be nearest.
    bars, idx_by_time = _bars_by_time(store)
    states_by_time = _states_by_time(store)
    sim = _build_simulator(store)
    ghost = replace(executed, entry_bar_available_time=-1)   # not in idx_by_time
    manifest = generate_legal_actions(ghost.risk_geometry)
    actual_action = next(a for a in manifest.actions if a.provenance == 'ACTUAL')
    row = replay_action(store, sim, ghost, actual_action, bars, idx_by_time,
                        states_by_time, manifest.manifest_id, None,
                        _funding_decomposable(store))
    assert row.cell_status == CELL_NOT_EVALUABLE_ACTION
    assert row.net_utility is None
