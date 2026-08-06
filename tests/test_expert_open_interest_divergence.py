"""E-22 open_interest_divergence expert tests (`positioning_divergence` /
`oi_price_divergence` family).

Covers: D-044/D-046 variant accounting, the four directional OI rules on
crafted tapes carrying the open_interest channel, NO_HABITAT self-gating on
tapes without the channel (the DATA_BLOCKED path), no-setup rejection,
risk_geometry values (recent-extreme stop in R), still_valid invalidation +
fail-open, D-026 anchor stability, requires-vs-consumption audit, determinism,
and a lab.run rule-12 smoke test.
"""
from __future__ import annotations

from v8.schema import TapeRow, MarketState, FEATURE_GROUPS, FEATURE_TO_GROUP
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.open_interest_divergence import (
    OpenInterestDivergenceExpert, LOOKBACK_N)

UNIVERSE = ('SOLUSDT',)
VARIANTS = ('a', 'b', 'c', 'd')
# global positioning read for the tape
_SKEW = 1.2


def _row(i, c, vol, skew):
    """Kline row (available at HOUR*i) + open_interest row (available at
    HOUR*i+1) carrying open_interest and long_short_skew (G-42/G-43)."""
    k = TapeRow(
        source='binance-um', channel='kline', instrument='SOLUSDT',
        event_time=HOUR_NS * i, available_time=HOUR_NS * i,
        ingested_time=HOUR_NS * i, venue_sequence=i * 2 + 1,
        event_id=f'SOLUSDT:{i + 1}',
        payload={'open': c, 'high': c + 0.5, 'low': c - 0.5, 'close': c,
                 'volume': vol, 'closed': True})
    o = TapeRow(
        source='binance-um', channel='open_interest', instrument='SOLUSDT',
        event_time=HOUR_NS * i, available_time=HOUR_NS * i + 1,
        ingested_time=HOUR_NS * i + 1, venue_sequence=i * 2 + 2,
        event_id=f'OI:{i + 1}',
        payload={'open_interest': 1000.0 + i, 'long_short_skew': skew})
    return k, o


def _tape(base_closes, tail_closes, tail_vols, skew=_SKEW):
    """>=100 flat bars (for vol_zscore) then a directional tail."""
    rows = []
    for i in range(100):
        rows += _row(i, base_closes, 1.0, skew)
    for j, c in enumerate(tail_closes):
        rows += _row(100 + j, c, tail_vols[j], skew)
    return rows


def _state(rows, kline_idx):
    as_of = rows[kline_idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _eval(expert, rows, idx):
    return expert.evaluate(_state(rows, 2 * idx))


# --- ontology + variants (D-044/D-046) --------------------------------------

def test_ontology_declared():
    e = OpenInterestDivergenceExpert()
    assert e.expert_id == 'open_interest_divergence'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'positioning_divergence'
    assert e.behavior_family_id == 'oi_price_divergence'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == VARIANTS
    assert set(e.requires) == {'positioning', 'participation', 'volatility',
                               'history'}


def test_variants_evaluated_completeness():
    e = OpenInterestDivergenceExpert()
    assert set(e.variants_evaluated) == set(VARIANTS)
    assert e.variant_id in e.variants_evaluated
    # The book card lists a..f; `e`/`f` need an OI series the state contract
    # does not carry (dropped before evaluation; the consumed search is 6).
    assert e.search_universe_size == 6 >= len(e.variants_evaluated)
    for vid in VARIANTS:
        assert OpenInterestDivergenceExpert(vid).variant_id == vid


def test_unknown_variant_fails_closed():
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    try:
        OpenInterestDivergenceExpert('zz').evaluate(_state(rows, 2 * 101))
    except ValueError:
        return
    raise AssertionError('undeclared variant must fail closed (D-044)')


# --- setup detection per variant (Ch6.1 p192-193) ----------------------------

def test_variant_a_all_rising_long():
    """price up + volume up + long-heavy positioning -> buy (variant a)."""
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    ev = _eval(OpenInterestDivergenceExpert('a'), rows, 101)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'a'


def test_variant_b_price_up_volume_short_heavy_short():
    """price up + volume down + short-heavy positioning -> bearish (variant b)."""
    rows = _tape(100.0, [101.0, 102.0], [0.5, 0.5], skew=0.8)
    ev = _eval(OpenInterestDivergenceExpert('b'), rows, 101)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'b'


def test_variant_c_price_down_volume_up_long_heavy_short():
    """declining market + OI/volume rising -> go short (variant c)."""
    rows = _tape(100.0, [99.0, 98.0], [1.5, 1.5])
    ev = _eval(OpenInterestDivergenceExpert('c'), rows, 101)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'c'


def test_variant_d_both_declining_long():
    """price + volume + positioning all down -> cover shorts / long (d)."""
    rows = _tape(100.0, [99.0, 98.0], [0.5, 0.5], skew=0.8)
    ev = _eval(OpenInterestDivergenceExpert('d'), rows, 101)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'd'


# --- no-setup / no-habitat ---------------------------------------------------

def test_no_setup_flat_price():
    """A flat close change (no direction) with no divergence -> NO_SETUP."""
    rows = _tape(100.0, [100.0, 100.0], [1.5, 1.5])
    ev = _eval(OpenInterestDivergenceExpert('a'), rows, 101)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_setup_wrong_variant_combination():
    """price up + volume up + SHORT-heavy does not satisfy variant a."""
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5], skew=0.8)
    ev = _eval(OpenInterestDivergenceExpert('a'), rows, 101)
    assert ev.decision == 'NO_SETUP'


def test_no_habitat_without_oi_channel():
    """The declared tape carries no open_interest: the expert self-gates to
    NO_HABITAT (registry DATA_BLOCKED; never a fabricated positioning read)."""
    from v8.synth import make_synthetic_tape
    rows = make_synthetic_tape(seed=5, n_bars=120)
    as_of = rows[-1].available_time
    st = build_state([r for r in rows if r.available_time <= as_of], as_of,
                     UNIVERSE)
    for vid in VARIANTS:
        ev = OpenInterestDivergenceExpert(vid).evaluate(st)
        assert ev.decision == 'NO_HABITAT'
        assert ev.draft is None


def test_no_habitat_on_warmup():
    """A tape without 100 bars has no vol_zscore -> NO_HABITAT."""
    rows = []
    for i in range(40):
        rows += _row(i, 100.0, 1.0, _SKEW)
    ev = OpenInterestDivergenceExpert('a').evaluate(_state(rows, 2 * 39))
    assert ev.decision == 'NO_HABITAT'


# --- risk geometry -----------------------------------------------------------

def test_risk_geometry_values():
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    d = _eval(OpenInterestDivergenceExpert('a'), rows, 101).draft
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['expiry_bars'] == 8
    assert g['variant'] == 'a'
    assert g['atr_ref'] == 1.0
    # Stop behind the recent 5-bar low (close 102.0 at bar 101; the prior
    # lows are 99.5..100.5, min = 99.5).
    assert g['prior_low_ref'] == 99.5
    assert g['stop_r'] == (102.0 - 99.5) / 1.0


def test_stop_uses_recent_window_not_anchor_bar():
    """The frozen stop is the LOOKBACK window extreme at detection, not the
    anchor bar's low (the D-026 anchor is the price-run start, older)."""
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    d = _eval(OpenInterestDivergenceExpert('a'), rows, 101).draft
    assert d.risk_geometry['prior_low_ref'] == 99.5
    assert LOOKBACK_N == 5


# --- still_valid -------------------------------------------------------------

def test_still_valid_invalidated_through_frozen_low():
    e = OpenInterestDivergenceExpert('a')
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    draft = e.evaluate(_state(rows, 2 * 101)).draft
    # Holds while close stays above the frozen 99.5.
    assert e.still_valid(_state(rows, 2 * 101), draft) is True
    # A later close through the frozen low resolves the divergence -> dead.
    tail = []
    for j, c in enumerate([101.0, 100.0, 99.0]):
        tail += _row(102 + j, c, 1.5, _SKEW)
    later = rows + tail
    assert e.still_valid(_state(later, 2 * 102), draft) is True
    assert e.still_valid(_state(later, 2 * 104), draft) is False


def test_still_valid_fail_open():
    e = OpenInterestDivergenceExpert('a')
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    draft = e.evaluate(_state(rows, 2 * 101)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- D-026 anchor stability --------------------------------------------------

def test_anchor_stable_across_consecutive_clocks():
    """The price-direction run anchor is stable while the up-move persists."""
    e = OpenInterestDivergenceExpert('a')
    rows = _tape(100.0, [101.0, 102.0, 103.0], [1.5, 1.5, 1.5])
    d1 = e.evaluate(_state(rows, 2 * 101)).draft
    d2 = e.evaluate(_state(rows, 2 * 102)).draft
    assert d1.setup_anchor_event_id == d2.setup_anchor_event_id


# --- registry audit + determinism + lab -------------------------------------

def test_requires_audited_against_consumption():
    e = OpenInterestDivergenceExpert()
    assert all(g in FEATURE_GROUPS for g in e.requires)
    consumption = {'close', 'atr', 'history', 'open_interest',
                   'long_short_skew', 'vol_zscore'}
    read_groups = {FEATURE_TO_GROUP[name] for name in consumption}
    assert read_groups <= set(e.requires) | {'raw'}


def test_evaluation_deterministic():
    rows = _tape(100.0, [101.0, 102.0], [1.5, 1.5])
    a = OpenInterestDivergenceExpert('a').evaluate(_state(rows, 2 * 101))
    b = OpenInterestDivergenceExpert('a').evaluate(_state(rows, 2 * 101))
    assert a.draft is not None and b.draft is not None
    assert a.draft.risk_geometry == b.draft.risk_geometry
    assert a.draft.setup_anchor_event_id == b.draft.setup_anchor_event_id


def test_lab_smoke_no_economic_claim(tmp_path):
    """Rule-12 guard: on the synthetic tape (no OI channel) the expert only
    NO_HABITATs; no economic claim is implied."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=41, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e22', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [OpenInterestDivergenceExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    assert r.candidate_count == 0   # no OI channel -> every eval NO_HABITAT
    for rec in lab.evaluations.read():
        assert rec.get('decision') == 'NO_HABITAT'
