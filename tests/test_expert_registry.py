"""Phase 3 expert registry gates (EXPERT_PROTOCOL sections 1, 4; ROADMAP
Phase 3; V8_CONSTITUTION rule 13; `variants_evaluated` gate D-044).

The registry YAML must parse, match the code-side projection exactly, and be
consistent with the feature-group ontology; every pilot must run on the
synthetic tape (the Phase-1 tape is not present in this session). No registry
experiment is registered and nothing is promoted.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from v8.experts import (TrendPullbackExpert, FailedBreakoutExpert,
                        LiquiditySweepReclaimExpert,
                        FailedBreakout2BExpert, TrendPullbackDepthExpert,
                        RangeBreakout1To1Expert, CandlestickReversalExpert,
                        RsiStochReversionExpert, MacdStochTrendExpert,
                        Divergence12SetupsExpert, BollingerBreakoutExpert,
                        BollingerReversionExpert, DonchianBreakoutExpert,
                        BreakoutRetestExpert, FibRetracementContinuationExpert,
                        FibProjectionReversalExpert, PatternMeasuringObjectiveExpert,
                        VolumeConfirmedBreakoutExpert, VolumeClimaxReversalExpert,
                        ObvAdlRegimeExpert, IchimokuCloudExpert,
                        FloorTraderPivotExpert, MarketProfileValueAreaExpert,
                        GapExhaustionExpert, OpenInterestDivergenceExpert,
                        FundingCrowdingReversalExpert, PandfBreakoutExpert)
from v8.schema import FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.synth import make_synthetic_tape

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / 'docs' / 'EXPERTS_REGISTRY.yaml'

PILOTS = (TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert)

# Every implemented expert family (code-side projection source for the registry).
ALL_EXPERTS = [
    TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert,
    FailedBreakout2BExpert, TrendPullbackDepthExpert, RangeBreakout1To1Expert,
    CandlestickReversalExpert, RsiStochReversionExpert, MacdStochTrendExpert,
    Divergence12SetupsExpert, BollingerBreakoutExpert, BollingerReversionExpert,
    DonchianBreakoutExpert, BreakoutRetestExpert, FibRetracementContinuationExpert,
    FibProjectionReversalExpert, PatternMeasuringObjectiveExpert,
    VolumeConfirmedBreakoutExpert, VolumeClimaxReversalExpert, ObvAdlRegimeExpert,
    IchimokuCloudExpert, FloorTraderPivotExpert, MarketProfileValueAreaExpert,
    GapExhaustionExpert, OpenInterestDivergenceExpert, FundingCrowdingReversalExpert,
    PandfBreakoutExpert,
]

# Backlog: no code OR data-absent on the current tape (self-gating experts).
DATA_BLOCKED = ('capitulation', 'open_interest_divergence')

# The frozen feature consumption of each pilot (what its evaluate() actually
# reads via _need); audited against the declared requires (EXPERT_PROTOCOL 1).
CONSUMPTION = {
    'trend_pullback': {'close', 'ema_fast', 'ema_slow', 'atr', 'history'},
    'failed_breakout': {'close', 'prior_high', 'atr', 'history'},
    'liquidity_sweep_reclaim': {'close', 'atr', 'history'},
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
    expected = {cls().expert_id for cls in ALL_EXPERTS} | set(DATA_BLOCKED)
    assert set(entries) == expected, \
        f'registry expert set {set(entries)} != code+backlog {expected}'
    for expected in ('PROPOSED', 'FORMALIZED', 'SCREENING', 'REPLICATION',
                     'SHADOW', 'PROMOTED', 'REJECTED', 'MERGED', 'QUARANTINED',
                     'DATA_BLOCKED'):
        assert expected in vocab
    for entry in entries.values():
        for key in ('expert_id', 'expert_version', 'mechanism_family_id',
                    'behavior_family_id', 'variant_id', 'variants_evaluated',
                    'search_universe_size', 'requires', 'status', 'owning_spec'):
            assert key in entry, f'{entry["expert_id"]} missing {key}'
        assert entry['status'] in vocab
        assert isinstance(entry['requires'], list) and entry['requires']
        # D-044: variants_evaluated is the full evaluated set (losers
        # included); the reported variant_id must be a member of it, never
        # outside it — that would mean a variant was reported without having
        # been counted in the family's multiplicity accounting.
        assert isinstance(entry['variants_evaluated'], list) and entry['variants_evaluated']
        assert entry['variant_id'] in entry['variants_evaluated'], (
            f"{entry['expert_id']}: variant_id {entry['variant_id']!r} not in "
            f"variants_evaluated {entry['variants_evaluated']!r}")
        # D-046: the retained variants are a SUBSET of the configurations the
        # search consumed, so the declared universe can never be smaller than
        # them. A family that declares fewer has under-reported its search and
        # its Reality-Check p-value is optimistic (Aronson Ch8 p390-391).
        size = entry['search_universe_size']
        assert isinstance(size, int) and not isinstance(size, bool), (
            f"{entry['expert_id']}: search_universe_size must be an int "
            f"(got {size!r})")
        assert size >= len(entry['variants_evaluated']), (
            f"{entry['expert_id']}: search_universe_size {size} < "
            f"{len(entry['variants_evaluated'])} evaluated variants — the "
            'declared search cannot be smaller than what it retained')
        if entry['expert_id'] in DATA_BLOCKED:
            assert entry['status'] == 'DATA_BLOCKED'
        else:
            assert entry['status'] == 'FORMALIZED'


def test_registry_matches_code():
    """docs/EXPERTS_REGISTRY.yaml equals the code-side registry_entry()
    projection exactly — the ontology cannot drift from the registry."""
    entries, _ = _registry()
    for cls in ALL_EXPERTS:
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
