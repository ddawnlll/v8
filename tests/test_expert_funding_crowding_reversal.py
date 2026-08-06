"""E-23 funding_crowding_reversal expert tests (`positioning_divergence` /
`funding_crowding_reversal` family).

Covers: D-044/D-046 variant accounting, DECLARED funding thresholds (CRIT-9:
+0.001/-0.001 literals, never a fitted quantile), price-confirmation setup
detection on crafted funding tapes, NO_HABITAT self-gating on tapes without
the funding channel (the DATA_BLOCKED path), risk_geometry values (barrier
stop in R), still_valid invalidation + fail-open, D-026 anchor stability,
requires-vs-consumption audit, determinism, and a lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, MarketState, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.funding_crowding_reversal import (
    FundingCrowdingReversalExpert, FUNDING_EXTREME_POS, FUNDING_EXTREME_NEG,
    CONFIRM_N)

UNIVERSE = ('SOLUSDT',)
VARIANTS = ('a', 'b', 'c', 'd')


def _row(i, c, rate=None, with_oi=False):
    """Kline row at HOUR*i (avail) + optional funding/OI rows at HOUR*i+1."""
    rows = [TapeRow(
        source='binance-um', channel='kline', instrument='SOLUSDT',
        event_time=HOUR_NS * i, available_time=HOUR_NS * i,
        ingested_time=HOUR_NS * i, venue_sequence=i * 3 + 1,
        event_id=f'SOLUSDT:{i + 1}',
        payload={'open': c, 'high': c + 0.5, 'low': c - 0.5, 'close': c,
                 'volume': 1.0, 'closed': True})]
    if rate is not None:
        rows.append(TapeRow(
            source='binance-um', channel='funding', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i + 1,
            ingested_time=HOUR_NS * i + 1, venue_sequence=i * 3 + 2,
            event_id=f'F:{i + 1}', payload={'funding_rate': rate}))
    if with_oi:
        rows.append(TapeRow(
            source='binance-um', channel='open_interest', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i + 2,
            ingested_time=HOUR_NS * i + 2, venue_sequence=i * 3 + 3,
            event_id=f'OI:{i + 1}',
            payload={'open_interest': 1000.0 + i, 'long_short_skew': 1.2}))
    return rows


def _tape(n_flat=30, tail_closes=(), rate=None, from_bar=25, with_oi=False):
    """n_flat flat bars at 100, then tail closes; funding rate from bar
    `from_bar`. Returns (rows, kline_idx_by_bar)."""
    rows = []
    kline_idx = {}
    for i in range(n_flat):
        kline_idx[i] = len(rows)
        rows += _row(i, 100.0, rate if i >= from_bar else None,
                     with_oi=with_oi)
    for j, c in enumerate(tail_closes):
        i = n_flat + j
        kline_idx[i] = len(rows)
        rows += _row(i, c, rate if i >= from_bar else None, with_oi=with_oi)
    return rows, kline_idx


def _state(rows, kline_idx):
    as_of = rows[kline_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _eval(expert, rows, kline_idx, bar):
    return expert.evaluate(_state(rows, kline_idx[bar]))


# --- ontology + variants (D-044/D-046) --------------------------------------

def test_ontology_declared():
    e = FundingCrowdingReversalExpert()
    assert e.expert_id == 'funding_crowding_reversal'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'positioning_divergence'
    assert e.behavior_family_id == 'funding_crowding_reversal'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == VARIANTS
    assert set(e.requires) == {'positioning', 'volatility', 'history'}


def test_variants_evaluated_completeness():
    e = FundingCrowdingReversalExpert()
    assert set(e.variants_evaluated) == set(VARIANTS)
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size == 4 >= len(e.variants_evaluated)
    for vid in VARIANTS:
        assert FundingCrowdingReversalExpert(vid).variant_id == vid


def test_declared_thresholds_not_fitted():
    """CRIT-9: the funding-extreme thresholds are numeric literals, never a
    fitted quantile of the funding distribution."""
    assert FUNDING_EXTREME_POS == 0.001
    assert FUNDING_EXTREME_NEG == -0.001


def test_unknown_variant_fails_closed():
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)
    try:
        FundingCrowdingReversalExpert('zz').evaluate(_state(rows, ki[30]))
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- setup detection per variant --------------------------------------------

def test_variant_a_crowded_long_short():
    """funding >= +0.001 (crowded long) + price confirms by closing below the
    prior 5-bar low -> SHORT."""
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)
    ev = _eval(FundingCrowdingReversalExpert('a'), rows, ki, 30)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'a'
    assert d.risk_geometry['atr_ref'] == 1.0


def test_variant_b_crowded_short_long():
    """funding <= -0.001 (crowded short) + price confirms by closing above the
    prior 5-bar high -> LONG."""
    rows, ki = _tape(tail_closes=[101.0], rate=-0.002)
    ev = _eval(FundingCrowdingReversalExpert('b'), rows, ki, 30)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'b'


def test_variant_c_requires_oi_channel():
    """Variant c needs the open_interest confluence leg: absent OI -> NO_HABITAT
    (a data gate, never a NO_SETUP)."""
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)     # no OI channel
    ev = _eval(FundingCrowdingReversalExpert('c'), rows, ki, 30)
    assert ev.decision == 'NO_HABITAT'
    rows_oi, ki_oi = _tape(tail_closes=[99.0], rate=0.002, with_oi=True)
    ev = _eval(FundingCrowdingReversalExpert('c'), rows_oi, ki_oi, 30)
    assert ev.decision == 'CANDIDATE'
    assert ev.draft.direction == 'SHORT'


def test_variant_d_exhaustion_short():
    """funding >= +0.001 while price makes a new 10-bar high (extension, not
    confirmation) -> exhaustion SHORT."""
    tail = [100.0 + 0.5 * k for k in range(10)]
    tail[-1] = 112.0          # clear new high above the prior highs
    rows, ki = _tape(n_flat=25, tail_closes=tail, rate=0.002, from_bar=24)
    ev = _eval(FundingCrowdingReversalExpert('d'), rows, ki, 34)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'd'
    assert d.risk_geometry['stop_r'] > 1.0    # 1 ATR beyond the extended high


# --- no-setup / no-habitat ---------------------------------------------------

def test_no_setup_funding_not_extreme():
    """Funding below the declared extreme never triggers the reversal."""
    rows, ki = _tape(tail_closes=[99.0], rate=0.0002)
    ev = _eval(FundingCrowdingReversalExpert('a'), rows, ki, 30)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_setup_extreme_without_price_confirmation():
    """Extreme funding with no confirming close (price still flat) is a
    sentiment reading, not a trade (the book's price-confirmation gate)."""
    rows, ki = _tape(rate=0.002)         # all flat
    ev = _eval(FundingCrowdingReversalExpert('a'), rows, ki, 29)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_habitat_without_funding_channel():
    """The declared tape carries no funding channel: self-gate to NO_HABITAT
    (registry DATA_BLOCKED; never a fabricated sentiment read)."""
    from v8.synth import make_synthetic_tape
    rows = make_synthetic_tape(seed=7, n_bars=120)
    as_of = rows[-1].available_time
    st = build_state([r for r in rows if r.available_time <= as_of], as_of,
                     UNIVERSE)
    for vid in VARIANTS:
        ev = FundingCrowdingReversalExpert(vid).evaluate(st)
        assert ev.decision == 'NO_HABITAT'
        assert ev.draft is None


def test_no_habitat_on_warmup():
    """A tape too short for the extension window -> NO_HABITAT."""
    rows, ki = _tape(n_flat=8, tail_closes=[99.0], rate=0.002)
    ev = _eval(FundingCrowdingReversalExpert('a'), rows, ki, 8)
    assert ev.decision == 'NO_HABITAT'


# --- risk geometry -----------------------------------------------------------

def test_risk_geometry_values():
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)
    d = _eval(FundingCrowdingReversalExpert('a'), rows, ki, 30).draft
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['expiry_bars'] == 8
    assert g['variant'] == 'a'
    assert g['atr_ref'] == 1.0
    # Stop beyond the confirmation barrier: the recent 5-bar high (100.5).
    assert g['prior_high_ref'] == 100.5
    assert g['stop_r'] == (100.5 - 99.0) / 1.0


def test_confirm_n_declared():
    assert CONFIRM_N == 5


# --- still_valid -------------------------------------------------------------

def test_still_valid_invalidated_through_barrier():
    e = FundingCrowdingReversalExpert('a')
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)
    draft = e.evaluate(_state(rows, ki[30])).draft
    assert e.still_valid(_state(rows, ki[30]), draft) is True
    # A later close back through the frozen barrier (100.5) kills the reversal.
    tail = []
    for j, c in enumerate([99.5, 100.0, 101.0]):
        tail += _row(31 + j, c, 0.002)
    later = rows + tail
    # bars 0..24 = 25 rows, bars 25..33 = 2 rows each -> kline of bar 31 is
    # at 25 + 2*(31-25) = 37; bar 33 at 25 + 2*(33-25) = 41.
    assert e.still_valid(_state(later, 37), draft) is True
    assert e.still_valid(_state(later, 41), draft) is False


def test_still_valid_fail_open():
    e = FundingCrowdingReversalExpert('a')
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)
    draft = e.evaluate(_state(rows, ki[30])).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- D-026 anchor stability --------------------------------------------------

def test_anchor_stable_across_consecutive_clocks():
    """The price-confirmation run anchor is stable while the confirm bars
    persist (the funding leg is a state reading, not per-bar)."""
    e = FundingCrowdingReversalExpert('a')
    rows, ki = _tape(tail_closes=[99.0, 98.0], rate=0.002)
    d1 = e.evaluate(_state(rows, ki[30])).draft
    d2 = e.evaluate(_state(rows, ki[31])).draft
    assert d1 is not None and d2 is not None
    assert d1.setup_anchor_event_id == d2.setup_anchor_event_id


# --- registry audit + determinism + lab -------------------------------------

def test_requires_audited_against_consumption():
    e = FundingCrowdingReversalExpert()
    assert all(g in FEATURE_GROUPS for g in e.requires)
    consumption = {'close', 'atr', 'history', 'funding_rate'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows, ki = _tape(tail_closes=[99.0], rate=0.002)
    a = FundingCrowdingReversalExpert('a').evaluate(_state(rows, ki[30]))
    b = FundingCrowdingReversalExpert('a').evaluate(_state(rows, ki[30]))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    """Rule-12 guard: on the synthetic tape (no funding channel) the expert
    only NO_HABITATs; no economic claim is implied."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=17, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e23', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [FundingCrowdingReversalExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    assert r.candidate_count == 0   # no funding channel -> every eval NO_HABITAT
    for rec in lab.evaluations.read():
        assert rec.get('decision') == 'NO_HABITAT'
