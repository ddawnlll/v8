"""E-17 OBV/ADL regime-gate expert tests.

Deterministic crafted tapes (verbatim OHLC) for the exact rule gates plus a
synthetic-tape lab smoke test. Cover: setup detection for every variant,
self-gating stand-down (disagreement -> NO_SETUP), the no-router structural
constraint (CRIT-7), no-habitat on a warmup tape, still_valid invalidation +
fail-open, risk-geometry values, and the D-044 variants_evaluated
completeness.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from v8.schema import TapeRow, MarketState
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.obv_adl_regime import ObvAdlRegimeExpert

UNIVERSE = ('SOLUSDT',)


def _tape(closes, volumes, style='flat'):
    """Closed 1h bars with a declared money-flow bias (the close's position in
    the range decides the Chaikin money-flow factor per bar):
      'bull'  - close at the high: MF factor +1 (cmf_20 -> +1)
      'bear'  - close at the low:  MF factor -1 (cmf_20 -> -1)
      'mild_bear' - close slightly below the range midpoint: cmf_20 in
                    (-0.15, 0) so the CMF-oversold gate does not pre-empt
      'flat'  - close at the midpoint: MF factor 0
    """
    rows = []
    for i, c in enumerate(closes):
        if style == 'bull':
            o, h, l = c * 0.996, c, c * 0.996
        elif style == 'bear':
            o, h, l = c * 1.004, c * 1.004, c
        elif style == 'mild_bear':
            o, h, l = c, c * 1.004, c * 0.9965
        else:  # 'flat'
            o, h, l = c, c * 1.004, c * 0.996
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
    e = ObvAdlRegimeExpert()
    assert e.expert_id == 'obv_adl_regime'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'volume_oscillator_regime'
    assert e.behavior_family_id == 'volume_oscillator_regime'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == ('a', 'b', 'c', 'd')
    assert set(e.requires) == {'participation', 'trend'}


def test_variants_evaluated_completeness():
    e = ObvAdlRegimeExpert()
    assert len(e.variants_evaluated) == 4
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)


def test_not_a_router():
    """CRIT-7: the regime gate must be a self-gating EXPERT, never a
    selection layer over other experts. Structural guard: the module defines
    no other-expert wiring (no expert imports beyond schema/base, no calls
    into the lifecycle/risk/simulator stack)."""
    # Anchor to the repo, not cwd: a sibling test module may chdir, and
    # inspect.getfile can then resolve to a path relative to the moved cwd.
    repo = Path(__file__).resolve().parents[1]
    src = (repo / 'src' / 'v8' / 'experts' / 'obv_adl_regime.py').read_text()
    # Layering (ARCHITECTURE_SPEC): an expert imports only base + schema; an
    # import into the lifecycle/risk/simulator/lab stack would be a router's
    # wiring, not a self-gating predicate.
    for forbidden in ('from ..lifecycle', 'from ..risk', 'from ..simulator',
                      'from ..lab'):
        assert forbidden not in src
    # A selection layer would NAME the experts it gates; this family must not.
    for other in ('TrendPullback', 'FailedBreakout', 'LiquiditySweepReclaim',
                  'VolumeConfirmedBreakout', 'VolumeClimaxReversal'):
        assert other not in src
    assert 'from ..schema import' in src and 'from .base import' in src


# --- setup detection per variant --------------------------------------------

def test_variant_a_trending_regime_long():
    """OBV slope, cmf_20 and the EMA trend all agree up -> trending LONG."""
    closes = [100.0 + 0.3 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='bull')   # bullish bars: cmf > 0
    st = _state_at(rows, 100)
    ev = ObvAdlRegimeExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'a'
    assert st.features['SOLUSDT.cmf_20'].value > 0


def test_variant_a_trending_regime_short():
    """OBV slope, cmf_20 and the EMA trend all agree down -> trending SHORT.
    Mildly bearish bars keep cmf_20 in (-0.15, 0) so the CMF-oversold gate
    (variant d) does not pre-empt."""
    closes = [100.0 - 0.3 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='mild_bear')
    st = _state_at(rows, 100)
    ev = ObvAdlRegimeExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'a'
    assert -0.15 < st.features['SOLUSDT.cmf_20'].value < 0


def test_disagreement_stands_down():
    """Rising EMA trend with negative money flow (OBV/ADL do NOT agree) is a
    ranging/choppy regime: the expert stands down with NO_SETUP rather than
    emitting a directional candidate (self-gating)."""
    closes = [100.0 + 0.2 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='bear')
    st = _state_at(rows, 100)
    ev = ObvAdlRegimeExpert().evaluate(st)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None
    assert st.features['SOLUSDT.cmf_20'].value < 0


def test_variant_b_unconfirmed_divergence_long():
    """Bullish OBV divergence without price confirmation: price weak (below
    both EMAs), flow already positive and OBV rising -> LONG anticipation."""
    closes = [100.0 - 0.2 * i for i in range(80)]
    up, c = [], closes[-1]
    for _ in range(10):
        c += 0.05
        up.append(c)
    closes = closes + up + [up[-1] - 0.2, up[-1] - 0.4]
    rows = _tape(closes, [2.0] * len(closes), style='bull')
    st = _state_at(rows, len(closes) - 1)
    ev = ObvAdlRegimeExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'b'


def test_variant_c_confirmed_divergence_long():
    """The divergence resolved by price confirmation: price below the slow EMA
    has crossed back above the fast EMA while flow stays positive -> LONG on
    the resolution (variant c)."""
    closes = [100.0 - 0.2 * i for i in range(80)]
    up, c = [], closes[-1]
    for _ in range(12):
        c += 0.04
        up.append(c)
    closes = closes + up
    rows = _tape(closes, [2.0] * len(closes), style='bull')
    st = _state_at(rows, len(closes) - 1)
    ev = ObvAdlRegimeExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'c'
    f = st.features
    assert f['SOLUSDT.close'].value < f['SOLUSDT.ema_slow'].value
    assert f['SOLUSDT.close'].value > f['SOLUSDT.ema_fast'].value


def test_variant_d_cmf_oversold_long():
    """CMF deeply oversold in a downtrend = exhausted distribution -> LONG
    (potential bottom, variant d)."""
    closes = [100.0 - 0.3 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='bear')
    st = _state_at(rows, 100)
    ev = ObvAdlRegimeExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'd'
    assert st.features['SOLUSDT.cmf_20'].value < -0.15


# --- no-habitat rejection ---------------------------------------------------

def test_no_habitat_on_warmup_tape():
    """cmf_20 is warmup-gated: a tape without it has no volume-oscillator
    habitat -> NO_HABITAT."""
    closes = [100.0] * 10
    rows = _tape(closes, [2.0] * 10)
    ev = ObvAdlRegimeExpert().evaluate(_state_at(rows, 9))
    assert ev.decision == 'NO_HABITAT'


# --- still_valid (post-entry thesis) ----------------------------------------

def test_still_valid_invalidated_on_regime_flip():
    """A LONG trending-regime candidate is dead once a close breaks below the
    frozen regime-bar low (the regime flipped or was misread)."""
    e = ObvAdlRegimeExpert()
    closes = [100.0 + 0.3 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='bull')
    draft = e.evaluate(_state_at(rows, 100)).draft
    assert e.still_valid(_state_at(rows, 100), draft) is True
    later = _tape(closes + [90.0], [2.0] * 102, style='bull')
    assert e.still_valid(_state_at(later, 101), draft) is False


def test_still_valid_fail_open():
    e = ObvAdlRegimeExpert()
    closes = [100.0 + 0.3 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='bull')
    draft = e.evaluate(_state_at(rows, 100)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- risk geometry ----------------------------------------------------------

def test_risk_geometry_values():
    e = ObvAdlRegimeExpert()
    closes = [100.0 + 0.3 * i for i in range(101)]
    rows = _tape(closes, [2.0] * 101, style='bull')
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
    lab.ingest(make_synthetic_tape(seed=41, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e17', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [ObvAdlRegimeExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')
