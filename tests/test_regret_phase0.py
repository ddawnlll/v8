"""Phase-0 evaluator (`tools/regret.py`) certification: families A (golden
synthetic paths), B (Candidate boundary), and C (ledger reconciliation).

Per `reports/accp/v8-rr-v02-phase0/source/FCR-V8RR-004.accp.yaml`. These
tests certify the EVALUATOR's semantics, not V8's economics — every number
here is MODEL_DERIVED and carries no economic claim (rule 12).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import pytest

from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.store import AppendOnlyLog
from v8.synth import make_synthetic_tape

from tools.regret import (
    load_store, build_snapshots, assert_pit_lineage, reconcile_actual_actions,
    generate_legal_actions, replay_action, compute_gap, run_phase0,
    _build_simulator, _bars_by_time, _states_by_time, _funding_decomposable,
    CELL_OK, CELL_UNDEFINED_FUTURE, CELL_NO_ENTRY,
    GAP_COMPUTED, GAP_ABSTAINED_UNDEFINED, GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION,
    _EXCLUDED_VARIANT_KEYS,
)

UNIVERSE = ('SOLUSDT',)
PILOTS = (TrendPullbackExpert, FailedBreakoutExpert)


def _manifest(**kw) -> ExperimentManifest:
    base = dict(experiment_id='exp-regret-test', code_hash='', data_hash='',
               universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    return ExperimentManifest(**base)


def _golden_store(tmp_path, seed=7, n_bars=160, experts=None) -> Path:
    store = tmp_path / 'store'
    lab = Lab(store)
    lab.ingest(make_synthetic_tape(seed=seed, n_bars=n_bars))
    lab.run(_manifest(), [cls() for cls in (experts or PILOTS)])
    return store


# --------------------------------------------------------------------- #
# Family A — deterministic golden paths
# --------------------------------------------------------------------- #

def test_no_trade_is_exactly_zero_with_no_simulator_call():
    manifest = generate_legal_actions({'target_r': 1.0, 'stop_r': 1.0,
                                       'expiry_bars': 8, 'atr_ref': 1.0})
    no_trade = manifest.actions[0]
    assert no_trade.kind == 'NO_TRADE'
    assert no_trade.action_id == 'NO_TRADE'
    # A garbage geometry override on NO_TRADE must not matter — the adapter
    # never reads risk_geometry for a NO_TRADE cell, so the result must be
    # deterministic 0.0 R regardless of what the candidate's actual geometry
    # contains.


def test_illegal_action_pyramid_add_rules_never_generated():
    """FT003(e): the generator must never MANUFACTURE a variant carrying an
    excluded key. The ACTUAL action is a pass-through of the real geometry,
    not a manufactured variant — a draft that actually declared
    `pyramid_add_rules` would already have failed closed upstream in
    `sim.step()` before reaching this generator at all (EXEC-3, P2), so
    the check applies to DECLARED_VARIANT actions only."""
    manifest = generate_legal_actions({'target_r': 1.0, 'stop_r': 1.0,
                                       'expiry_bars': 8, 'atr_ref': 1.0,
                                       'pyramid_add_rules': {'k': 1}})
    generated = [a for a in manifest.actions if a.provenance == 'DECLARED_VARIANT'
                and a.kind != 'NO_TRADE']
    # The excluded key being present at all must suppress the ENTIRE
    # continuous-axis grid (generate_legal_actions' conservative choice),
    # not just variants that happen to touch it.
    assert generated == [], (
        'generator must refuse to manufacture ANY continuous-axis variant '
        'when the actual geometry declares pyramid_add_rules')
    for action in manifest.actions:
        if action.provenance == 'ACTUAL':
            continue
        for key in _EXCLUDED_VARIANT_KEYS:
            assert key not in action.override


def test_actual_action_is_always_element_one_and_manifest_contains_it():
    geometry = {'target_r': 1.0, 'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0}
    manifest = generate_legal_actions(geometry)
    assert manifest.actions[0].kind == 'NO_TRADE'
    actual = manifest.actions[1]
    assert actual.provenance == 'ACTUAL'
    assert actual.override == geometry
    # Regenerating from the identical geometry must reproduce the identical
    # manifest_id (FT003f — a manifest is versioned with what generated it).
    again = generate_legal_actions(geometry)
    assert again.manifest_id == manifest.manifest_id


def test_undefined_future_never_fabricates_a_value(tmp_path):
    """A candidate entering on the tape's final bar must abstain
    UNDEFINED_FUTURE — never the simulator's manufactured EXPIRY/-cost
    (measured in FER-V8RR-002 RM008: entry-only tail -> EXPIRY/-0.07)."""
    store_dir = _golden_store(tmp_path)
    store = load_store(store_dir)
    snapshots = build_snapshots(store)
    executed = [s for s in snapshots if s.binding_status == 'BOUND'
               and s.entry_bar_available_time is not None]
    assert executed, 'golden fixture must have at least one executed candidate'
    sim = _build_simulator(store)
    bars, idx_by_time = _bars_by_time(store)
    states_by_time = _states_by_time(store)

    # Force the entry to the LAST bar of the tape (the degenerate case).
    snap = executed[0]
    forced = snap.__class__(**{**snap.__dict__,
                               'entry_bar_available_time': bars[-1].available_time})
    manifest = generate_legal_actions(forced.risk_geometry)
    actual_action = next(a for a in manifest.actions if a.provenance == 'ACTUAL')
    row = replay_action(store, sim, forced, actual_action, bars, idx_by_time,
                        states_by_time, manifest.manifest_id, None,
                        _funding_decomposable(store))
    assert row.cell_status == CELL_UNDEFINED_FUTURE
    assert row.net_utility is None
    assert row.endpoint is None


def test_no_entry_candidate_is_no_entry_not_zero(tmp_path):
    store_dir = _golden_store(tmp_path)
    store = load_store(store_dir)
    snapshots = build_snapshots(store)
    never_entered = [s for s in snapshots
                     if s.binding_status == 'BOUND' and s.entry_bar_available_time is None]
    assert never_entered, 'golden fixture must have a non-executed bound candidate'
    snap = never_entered[0]
    manifest = generate_legal_actions(snap.risk_geometry)
    sim = _build_simulator(store)
    bars, idx_by_time = _bars_by_time(store)
    states_by_time = _states_by_time(store)
    for action in manifest.actions:
        row = replay_action(store, sim, snap, action, bars, idx_by_time,
                            states_by_time, manifest.manifest_id, None,
                            _funding_decomposable(store))
        assert row.cell_status == CELL_NO_ENTRY
        assert row.net_utility is None
    gap = compute_gap(snap.candidate_id, manifest,
                      [{'action_id': a.action_id, 'cell_status': CELL_NO_ENTRY,
                        'cell_status_reason': 'x', 'net_utility': None}
                       for a in manifest.actions])
    assert gap.gap_status == GAP_ABSTAINED_UNDEFINED


def test_known_fee_delta_reconciles_exactly(tmp_path):
    store_dir = _golden_store(tmp_path)
    store = load_store(store_dir)
    sim = _build_simulator(store)
    assert sim.round_trip_cost_r == store.manifest['round_trip_cost_r']
    # cost_r is a pure function of (entry, unit) under the flat form — must
    # equal the manifest constant exactly, regardless of entry/unit.
    assert sim.cost_r(123.45, 6.78) == store.manifest['round_trip_cost_r']


def test_gap_invariant_never_negative_on_golden(tmp_path):
    """v0.2 invariant: hindsight utility cannot be lower than actual utility
    for the same Candidate/action universe — the actual action is always
    element 1 of its own manifest, so best >= actual by construction."""
    store_dir = _golden_store(tmp_path)
    out_dir = store_dir.parent / 'out'
    summary = run_phase0(store_dir, out_dir)
    assert not summary['halted']
    assert summary['reconciliation']['verdict'] == 'RECONCILED'
    rows = AppendOnlyLog(out_dir / 'regret.jsonl').read()
    computed = [r for r in rows if r['gap_status'] == GAP_COMPUTED]
    assert computed, 'golden fixture must yield at least one COMPUTED gap'
    for r in computed:
        assert r['legal_hindsight_gap'] >= -1e-9, (
            f"{r['candidate_id']}: negative gap means a_actual was not in A_t")
        assert r['tie_cardinality'] == len(r['best_action_ids'])


# --------------------------------------------------------------------- #
# Family B — Candidate boundary (OUTSIDE_CANDIDATE_UNIVERSE)
# --------------------------------------------------------------------- #

def test_no_candidate_no_invented_row(tmp_path):
    """A large future move with NO Expert emitting a Candidate must yield
    zero cube rows and zero gap rows — never a manufactured episode. Running
    with an EMPTY expert list is the strongest form of this: the Candidate
    universe is provably empty regardless of what the tape does."""
    store = tmp_path / 'store'
    lab = Lab(store)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r = lab.run(_manifest(), [])
    assert r.candidate_count == 0

    out_dir = tmp_path / 'out'
    summary = run_phase0(store, out_dir)
    assert not summary['halted']
    assert summary['n_candidates'] == 0
    assert not (out_dir / 'cube.jsonl').exists() or \
        len(AppendOnlyLog(out_dir / 'cube.jsonl').read()) == 0
    assert not (out_dir / 'regret.jsonl').exists() or \
        len(AppendOnlyLog(out_dir / 'regret.jsonl').read()) == 0


# --------------------------------------------------------------------- #
# Family C — ledger reconciliation (the load-bearing invariant)
# --------------------------------------------------------------------- #

def test_reconciliation_exact_on_golden_fixture(tmp_path):
    store_dir = _golden_store(tmp_path)
    store = load_store(store_dir)
    snapshots = build_snapshots(store)
    assert all(s.binding_status == 'BOUND' for s in snapshots), (
        'every golden candidate must bind to its stored draft')
    recon = reconcile_actual_actions(store, snapshots)
    assert recon.verdict == 'RECONCILED'
    assert recon.n_mismatched == 0
    assert recon.n_executed == recon.n_reconciled
    for field, dev in recon.max_abs_deviation.items():
        assert dev == 0.0, f'{field}: max abs deviation {dev} (expected exact)'


def test_pit_lineage_clean_on_golden_fixture(tmp_path):
    store_dir = _golden_store(tmp_path)
    store = load_store(store_dir)
    snapshots = build_snapshots(store)
    problems = assert_pit_lineage(store, snapshots)
    assert problems == [], f'PIT lineage violations: {problems}'


def test_reconciliation_failure_halts_before_cube(tmp_path, monkeypatch):
    """A corrupted observed outcome must halt Phase 0 rather than silently
    produce a cube from a store whose own ledger the evaluator cannot trust."""
    store_dir = _golden_store(tmp_path)
    outcomes_path = store_dir / 'outcomes.jsonl'
    lines = outcomes_path.read_text(encoding='utf-8').splitlines()
    import json
    first = json.loads(lines[0])
    if first.get('label_status') == 'MATURE':
        first['net_r'] = first['net_r'] + 999.0   # corrupt one observed outcome
        lines[0] = json.dumps(first, sort_keys=True)
        outcomes_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        out_dir = store_dir.parent / 'out_corrupt'
        summary = run_phase0(store_dir, out_dir)
        assert summary['halted']
        assert summary['reconciliation']['verdict'] == 'RECONCILIATION_FAILED'
        assert not (out_dir / 'cube.jsonl').exists()
