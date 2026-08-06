"""E-16 volume-climax reversal expert tests.

Deterministic crafted tapes (verbatim OHLC/volume) for the exact rule gates
plus a synthetic-tape lab smoke test. Cover: setup detection for every
variant, no-setup rejection, no-habitat on a warmup tape, still_valid
invalidation + fail-open, risk-geometry values, and the D-044
variants_evaluated completeness.
"""
from __future__ import annotations

import pytest

from v8.schema import TapeRow, MarketState
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.volume_climax_reversal import VolumeClimaxReversalExpert

UNIVERSE = ('SOLUSDT',)


def _tape(closes, volumes, opens=None):
    """Closed 1h bars; opens default to closes (mid-range, zero flow bias)."""
    rows = []
    for i, c in enumerate(closes):
        o = opens[i] if opens is not None else c
        h = max(o, c) * 1.004
        l = min(o, c) * 0.996
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': volumes[i], 'closed': True}))
    return rows


def _state_at(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of], as_of, UNIVERSE)


# --- ontology + variants_evaluated (D-044) ----------------------------------

def test_ontology_declared():
    e = VolumeClimaxReversalExpert()
    assert e.expert_id == 'volume_climax_reversal'
    assert e.version == 'v2'
    assert e.mechanism_family_id == 'volume_exhaustion'
    assert e.behavior_family_id == 'volume_climax_reversal'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == ('a', 'b', 'c', 'd', 'e')
    assert set(e.requires) == {'trend', 'volatility', 'participation', 'history'}


def test_variants_evaluated_completeness():
    e = VolumeClimaxReversalExpert()
    assert len(e.variants_evaluated) == 5
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)


# --- setup detection per variant --------------------------------------------

def test_variant_a_selling_climax_long():
    """A 2-sigma volume overextension in a downtrend is a selling climax ->
    LONG fade (variant a)."""
    closes = [100.0 - 0.1 * i for i in range(100)] + [89.5]
    vols = [1.9, 2.1] * 50 + [2.25]
    rows = _tape(closes, vols)
    st = _state_at(rows, 100)
    ev = VolumeClimaxReversalExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'a'
    assert st.features['SOLUSDT.vol_zscore'].value >= 2.0
    # The climax extreme is frozen as the invalidation level.
    assert d.risk_geometry['prior_low_ref'] == pytest.approx(
        float(st.features['SOLUSDT.close'].value) * 0.996)


def test_variant_b_buying_climax_short():
    """A 2-sigma volume overextension in an uptrend is a buying climax
    (blow-off) -> SHORT fade (variant b)."""
    closes = [100.0 + 0.1 * i for i in range(100)] + [110.5]
    vols = [1.9, 2.1] * 50 + [2.25]
    rows = _tape(closes, vols)
    ev = VolumeClimaxReversalExpert().evaluate(_state_at(rows, 100))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'b'
    assert d.risk_geometry['prior_high_ref'] > 0


def test_variant_c_low_volume_bottom():
    """A low-volume bottom: volume near its historical minimum with price
    below the slow EMA -> LONG (variant c; the distinction from a climax is
    the volume level itself)."""
    closes = [100.0 - 0.2 * i for i in range(60)] + [88.0] * 41
    vols = [5.0] * 60 + [1.0] * 41
    rows = _tape(closes, vols)
    st = _state_at(rows, 100)
    ev = VolumeClimaxReversalExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'c'
    assert st.features['SOLUSDT.vol_min_proximity'].value < 0.4


def test_variant_d_reversal_bar_confirm():
    """A 2-sigma overextension on a High-Vol Reversal bar (bar_class == 1) is
    the bar-shape-confirmed climax -> fade in the bar's own direction
    (variant d)."""
    closes = [100.0 - 0.1 * i for i in range(100)] + [89.5]
    vols = [1.9, 2.1] * 50 + [2.25]
    opens = list(closes)
    opens[100] = 88.0                       # opens low, closes up: bullish
    rows = _tape(closes, vols, opens=opens)
    st = _state_at(rows, 100)
    ev = VolumeClimaxReversalExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'd'
    assert st.features['SOLUSDT.bar_class'].value == 1.0


def test_variant_e_strict_3sigma_climax():
    """D-055 challenger: a 3-sigma overextension (the 8.0 spike gives
    vol_zscore ~10) is the strict climax -> variant e owns the bar, LONG after
    a selling climax in a downtrend, SHORT after a buying climax in an uptrend.
    The 2-sigma a/b/d gates must NOT fire on a 3-sigma bar."""
    # downtrend + 3-sigma spike -> e/LONG (variant a would also want LONG, but
    # the strict variant owns 3-sigma bars by priority)
    closes = [100.0 - 0.1 * i for i in range(100)] + [89.5]
    vols = [2.0] * 100 + [8.0]
    ev = VolumeClimaxReversalExpert().evaluate(_state_at(_tape(closes, vols), 100))
    assert ev.decision == 'CANDIDATE'
    assert ev.draft.direction == 'LONG'
    assert ev.draft.risk_geometry['variant'] == 'e'
    # uptrend + 3-sigma spike -> e/SHORT
    closes_up = [100.0 + 0.1 * i for i in range(100)] + [110.5]
    ev2 = VolumeClimaxReversalExpert().evaluate(_state_at(_tape(closes_up, vols), 100))
    assert ev2.decision == 'CANDIDATE'
    assert ev2.draft.direction == 'SHORT'
    assert ev2.draft.risk_geometry['variant'] == 'e'


# --- no-setup / no-habitat rejection ----------------------------------------

def test_no_setup_on_quiet_tape():
    """No 2-sigma overextension and no near-minimum volume -> no climax setup
    -> NO_SETUP."""
    closes = [100.0 + 0.05 * i for i in range(101)]
    vols = [2.0] * 101
    rows = _tape(closes, vols)
    ev = VolumeClimaxReversalExpert().evaluate(_state_at(rows, 100))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_habitat_on_warmup_tape():
    """The 100-bar volume-stat features are this family's habitat: a tape
    without them cannot express a climax predicate -> NO_HABITAT."""
    closes = [100.0] * 30
    rows = _tape(closes, [2.0] * 30)
    ev = VolumeClimaxReversalExpert().evaluate(_state_at(rows, 29))
    assert ev.decision == 'NO_HABITAT'


# --- still_valid (post-entry thesis) ----------------------------------------

def test_still_valid_invalidated_on_new_extreme():
    """A LONG selling-climax fade is dead once a close exceeds the frozen
    climax bar's low in the adverse direction (a new low says the selling was
    not exhausted)."""
    e = VolumeClimaxReversalExpert()
    closes = [100.0 - 0.1 * i for i in range(100)] + [89.5]
    vols = [2.0] * 100 + [8.0]
    rows = _tape(closes, vols)
    draft = e.evaluate(_state_at(rows, 100)).draft
    assert e.still_valid(_state_at(rows, 100), draft) is True
    later = _tape(closes + [88.0], vols + [2.0])
    assert e.still_valid(_state_at(later, 101), draft) is False


def test_still_valid_fail_open():
    e = VolumeClimaxReversalExpert()
    closes = [100.0 - 0.1 * i for i in range(100)] + [89.5]
    vols = [2.0] * 100 + [8.0]
    rows = _tape(closes, vols)
    draft = e.evaluate(_state_at(rows, 100)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- risk geometry ----------------------------------------------------------

def test_risk_geometry_values():
    e = VolumeClimaxReversalExpert()
    closes = [100.0 - 0.1 * i for i in range(100)] + [89.5]
    vols = [2.0] * 100 + [8.0]
    rows = _tape(closes, vols)
    d = e.evaluate(_state_at(rows, 100)).draft
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['stop_r'] == 1.0
    assert g['expiry_bars'] == 8
    assert g['atr_ref'] > 0
    assert g['variant'] in e.variants_evaluated
    assert 'prior_low_ref' in g and g['prior_low_ref'] > 0


# --- lab integration --------------------------------------------------------

def test_lab_smoke_no_claim(tmp_path):
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=31, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e16', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [VolumeClimaxReversalExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')
