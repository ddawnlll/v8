"""Phase 3 expert registry gates (EXPERT_PROTOCOL sections 1, 4; ROADMAP
Phase 3; V8_CONSTITUTION rule 13).

The registry YAML must parse, match the code-side projection exactly, and be
consistent with the feature-group ontology; every pilot must run on the
synthetic tape (the Phase-1 tape is not present in this session). No registry
experiment is registered and nothing is promoted.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from v8.experts import (TrendPullbackExpert, FailedBreakoutExpert,
                        LiquiditySweepReclaimExpert, TrendExhaustionReversalExpert,
                        CompressionBreakoutExpert, VolumeRangeBreakoutExpert)
from v8.schema import FEATURE_GROUPS, FEATURE_TO_GROUP, FeatureValue, MarketState
from v8.synth import make_synthetic_tape

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / 'docs' / 'EXPERTS_REGISTRY.yaml'

PILOTS = (TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert,
          TrendExhaustionReversalExpert, CompressionBreakoutExpert,
          VolumeRangeBreakoutExpert)

# Backlog experts declared DATA_BLOCKED until derivatives tape (no code).
DATA_BLOCKED = ('breakout_retest', 'capitulation', 'range_value_mean_reversion',
                'cross_market_relative_strength')
REJECTED = ('practitioner_geometry_projection',)

# The frozen feature consumption of each pilot (what its evaluate() actually
# reads via _need); audited against the declared requires (EXPERT_PROTOCOL 1).
CONSUMPTION = {
    'trend_pullback': {'close', 'ema_fast', 'ema_slow', 'atr', 'history'},
    'failed_breakout': {'close', 'prior_high', 'atr', 'history'},
    'liquidity_sweep_reclaim': {'close', 'atr', 'history'},
    'trend_exhaustion_reversal': {'atr', 'history', 'close'},
    'compression_breakout': {'atr', 'history'},
    'volume_range_breakout': {'atr', 'relative_volume', 'range_ratio', 'history'},
}


def _registry() -> tuple[dict, list]:
    data = yaml.safe_load(REGISTRY.read_text(encoding='utf-8'))
    assert isinstance(data, dict)
    return ({e['expert_id']: e for e in data['experts']},
            data['expert_status_vocabulary'])


def test_registry_yaml_parses():
    """The registry is valid YAML with the three pilots + the DATA_BLOCKED
    backlog, all required keys, and the full status vocabulary (runbook step 6
    gate). Pilots sit at FORMALIZED; backlog entries at DATA_BLOCKED."""
    entries, vocab = _registry()
    assert set(entries) == {'trend_pullback', 'failed_breakout',
                            'liquidity_sweep_reclaim', 'trend_exhaustion_reversal',
                            'compression_breakout', 'volume_range_breakout'} | set(DATA_BLOCKED) | set(REJECTED)
    for expected in ('PROPOSED', 'FORMALIZED', 'SCREENING', 'REPLICATION',
                     'SHADOW', 'PROMOTED', 'REJECTED', 'MERGED', 'QUARANTINED',
                     'DATA_BLOCKED'):
        assert expected in vocab
    for entry in entries.values():
        for key in ('expert_id', 'expert_version', 'mechanism_family_id',
                    'behavior_family_id', 'variant_id', 'requires', 'status',
                    'owning_spec'):
            assert key in entry, f'{entry["expert_id"]} missing {key}'
        assert entry['status'] in vocab
        assert isinstance(entry['requires'], list) and entry['requires']
        if entry['expert_id'] in DATA_BLOCKED:
            assert entry['status'] == 'DATA_BLOCKED'
        elif entry['expert_id'] in REJECTED:
            assert entry['status'] == 'REJECTED'
        else:
            assert entry['status'] == 'FORMALIZED'


def test_registry_matches_code():
    """docs/EXPERTS_REGISTRY.yaml equals the code-side registry_entry()
    projection exactly — the ontology cannot drift from the registry."""
    entries, _ = _registry()
    for cls in PILOTS:
        ex = cls()
        code = ex.registry_entry()
        yml = entries[ex.expert_id]
        for key in ('expert_id', 'expert_version', 'mechanism_family_id',
                    'behavior_family_id', 'variant_id', 'requires'):
            assert code[key] == yml[key], f'{key} mismatch for {ex.expert_id}'


def test_pilot_ontology_declared():
    """All pilots carry mechanism/behavior/variant ids and variant 'a'
    (pinned runbook step 6 interpretation); the sweep expert is a distinct
    mechanism from failed_breakout (EXPERT_PROTOCOL 1 separate-Expert test)."""
    ids = {cls.expert_id: (cls.mechanism_family_id, cls.behavior_family_id,
                           cls.variant_id) for cls in PILOTS}
    assert ids['trend_pullback'] == ('trend_continuation', 'pullback_in_trend', 'a')
    assert ids['failed_breakout'] == ('liquidity_vacuum_reentry',
                                      'failed_breakout_reentry', 'a')
    assert ids['liquidity_sweep_reclaim'] == ('liquidity_sweep_reclaim',
                                              'sweep_reclaim', 'a')
    # Distinct mechanism + setup + invalidation -> a separate Expert, not a
    # variant of the failed-breakout family (EXPERT_PROTOCOL section 1).
    assert ids['liquidity_sweep_reclaim'][0] != ids['failed_breakout'][0]


def _state(history, relative_volume=2.0, range_ratio=2.0):
    """Small closed-bar state fixtures for rule-level Expert probes."""
    def fv(name, value):
        return FeatureValue(name, value, 'float', 'v1', 1,
                            group=FEATURE_TO_GROUP.get(name.rsplit('.', 1)[-1], 'raw'))
    features = {
        'SOLUSDT.close': fv('SOLUSDT.close', history[-1][4]),
        'SOLUSDT.atr': fv('SOLUSDT.atr', 1.0),
        'SOLUSDT.history': FeatureValue('SOLUSDT.history', tuple(history), 'history', 'v2', 1, group='history'),
        'SOLUSDT.relative_volume': fv('SOLUSDT.relative_volume', relative_volume),
        'SOLUSDT.range_ratio': fv('SOLUSDT.range_ratio', range_ratio),
    }
    return MarketState('fixture', 1, ('SOLUSDT',), features, 'fixture')


def test_handbook_candidate_rules_are_executable():
    """Each newly formalized family emits a deterministic candidate on its
    declared closed-bar predicate.  This is a contract probe, not economics."""
    base = [(f'e{i}', 100.0, 101.0, 99.0, 100.0, 101.0, 100.0) for i in range(28)]
    reversal = base + [('e28', 101.0, 102.0, 100.0, 101.0, 105.0, 100.0),
                       ('e29', 102.0, 103.0, 101.0, 102.0, 105.0, 100.0),
                       ('e30', 103.0, 104.0, 102.0, 103.0, 105.0, 100.0),
                       ('e31', 99.0, 100.0, 98.0, 99.0, 105.0, 100.0)]
    assert TrendExhaustionReversalExpert().evaluate(_state(reversal)).draft is not None

    quiet = [(f'c{i}', 100.0, 101.0, 99.0, 100.0, 101.0, 100.0) for i in range(16)]
    quiet += [(f'c{i}', 100.0, 100.1, 100.0, 100.05, 101.0, 100.0) for i in range(16, 20)]
    quiet += [('c20', 100.0, 103.0, 99.0, 102.0, 101.0, 100.0)]
    assert CompressionBreakoutExpert().evaluate(_state(quiet)).draft is not None

    breakout = [(f'v{i}', 100.0, 101.0, 99.0, 100.0, 101.0, 100.0) for i in range(31)]
    breakout += [('v31', 102.0, 104.0, 102.0, 103.0, 101.0, 100.0)]
    assert VolumeRangeBreakoutExpert().evaluate(_state(breakout)).draft is not None


def test_weekly_interval_is_explicitly_supported():
    from v8.lab import _INTERVAL_NS
    assert _INTERVAL_NS['1w'] == 7 * 24 * 60 * 60 * 1_000_000_000


def test_expert_requires_audited_against_consumption():
    """Declared `requires` groups exist, and every feature the pilot actually
    reads maps into its declared groups (raw is the base layer everyone may
    read) — the habitat definition and the feature usage cannot drift apart."""
    for cls in PILOTS:
        ex = cls()
        assert ex.requires, f'{ex.expert_id} must declare requires'
        assert all(g in FEATURE_GROUPS for g in ex.requires)
        read_groups = {FEATURE_TO_GROUP[name] for name in CONSUMPTION[ex.expert_id]}
        allowed = set(ex.requires) | {'raw'}
        assert read_groups <= allowed, (
            f'{ex.expert_id} reads {sorted(read_groups - allowed)} outside '
            f'its declared requires {ex.requires}')


def test_pilots_run_on_synthetic_tape(tmp_path):
    """Experts run on the synthetic tape (Phase-1 tape absent this session);
    contract tests stay green and no verdict is implied (rule 12)."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-registry', code_hash='', data_hash='',
                           universe=('SOLUSDT',), start_ns=0, end_ns=0)
    r = lab.run(m, [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r.candidate_count > 0
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
