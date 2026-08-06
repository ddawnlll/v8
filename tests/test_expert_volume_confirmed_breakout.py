"""E-15 volume-gated breakout expert tests.

Deterministic crafted tapes (verbatim OHLC) for the exact rule gates plus a
synthetic-tape lab smoke test. Cover: setup detection on a known setup for
every variant, no-setup rejection, no-habitat on a warmup tape, still_valid
invalidation + fail-open, risk-geometry values, D-026 key stability, and the
D-044 variants_evaluated completeness.
"""
from __future__ import annotations

import pytest

from v8.schema import TapeRow, MarketState, sha1_hex
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.volume_confirmed_breakout import VolumeConfirmedBreakoutExpert
from v8.lifecycle import episode_key

UNIVERSE = ('SOLUSDT',)


def _tape(closes, volumes, high_frac=0.002, low_frac=0.002):
    """Closed 1h bars with deterministic OHLC/volume; high above close so a
    20-bar window has a strictly positive range to break out of."""
    rows = []
    for i, c in enumerate(closes):
        h = c * (1 + high_frac)
        l = c * (1 - low_frac)
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': h, 'low': l, 'close': c,
                     'volume': volumes[i], 'closed': True}))
    return rows


def _state_at(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of], as_of, UNIVERSE)


def _geo(draft) -> str:
    """Structural geometry only — mirrors lab._geometry_version (atr_ref and
    the prior_*_ref price levels are data-dependent and excluded from episode
    identity, D-042)."""
    structural = {k: v for k, v in draft.risk_geometry.items()
                  if k not in ('atr_ref', 'prior_high_ref', 'prior_low_ref')}
    return sha1_hex(structural)


# --- ontology + variants_evaluated (D-044) ----------------------------------

def test_ontology_declared():
    e = VolumeConfirmedBreakoutExpert()
    assert e.expert_id == 'volume_confirmed_breakout'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'volume_confirmation'
    assert e.behavior_family_id == 'volume_confirmed_breakout'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == ('a', 'b', 'c', 'd')
    assert set(e.requires) == {'location', 'volatility', 'participation', 'history'}


def test_variants_evaluated_completeness():
    e = VolumeConfirmedBreakoutExpert()
    assert len(e.variants_evaluated) == 4
    assert e.variant_id in e.variants_evaluated
    # D-046: the declared search cannot be smaller than what it retained.
    assert e.search_universe_size >= len(e.variants_evaluated)


# --- setup detection per variant --------------------------------------------

def test_variant_a_dow_confirmation_long():
    """Breakout with modestly expanding volume (above the 20-bar smoothed
    average but below the 1.2x/2.0x gates) -> variant a, LONG."""
    closes = [100.0] * 41 + [101.5]
    vols = [1.0] * 41 + [1.1]
    rows = _tape(closes, vols)
    ev = VolumeConfirmedBreakoutExpert().evaluate(_state_at(rows, 41))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'a'
    # The broken level is the 20-bar windowed high and is FROZEN as the
    # prior_low_ref (the level a LONG must stay above).
    assert d.risk_geometry['prior_low_ref'] == pytest.approx(100.2)


def test_variant_a_short_breakout():
    """A close below the 20-bar windowed low -> SHORT variant a."""
    closes = [100.0] * 41 + [98.5]
    vols = [1.0] * 41 + [1.1]
    rows = _tape(closes, vols)
    ev = VolumeConfirmedBreakoutExpert().evaluate(_state_at(rows, 41))
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    assert d.risk_geometry['variant'] == 'a'
    assert d.risk_geometry['prior_high_ref'] == pytest.approx(99.8)


def test_variant_b_low_volume_timing():
    """Low-volume breakout timing: a 100-bar window with a loud past and a
    quiet phase, then a breakout bar whose volume is near the historical
    minimum (vol_min_proximity < 0.4) yet above the smoothed average. The
    variant-b gate fires (a/c/d gates are below/above it)."""
    closes = [100.0] * 101 + [101.5]
    vols = [5.0] * 70 + [1.0] * 31 + [1.15]
    rows = _tape(closes, vols)
    st = _state_at(rows, 101)
    ev = VolumeConfirmedBreakoutExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    assert ev.draft.risk_geometry['variant'] == 'b'
    assert st.features['SOLUSDT.vol_min_proximity'].value < 0.4


def test_variant_c_high_volume_confirm():
    """High-volume continuation confirm: breakout-bar volume >= 1.2x the
    smoothed average (and < 2.0x, so the spike gate does not pre-empt)."""
    closes = [100.0] * 101 + [101.5]
    vols = [2.0] * 101 + [3.0]
    rows = _tape(closes, vols)
    ev = VolumeConfirmedBreakoutExpert().evaluate(_state_at(rows, 101))
    assert ev.decision == 'CANDIDATE'
    assert ev.draft.risk_geometry['variant'] == 'c'


def test_variant_d_spike_not_climax():
    """Volume spike (>= 2.0x smoothed average) that is NOT a 2-sigma
    overextension (high-variance 100-bar window keeps the z-score below 2)
    -> variant d."""
    closes = [100.0] * 101 + [101.5]
    vols = [1.0 if i % 2 == 0 else 9.0 for i in range(101)] + [11.0]
    rows = _tape(closes, vols)
    st = _state_at(rows, 101)
    ev = VolumeConfirmedBreakoutExpert().evaluate(st)
    assert ev.decision == 'CANDIDATE'
    assert ev.draft.risk_geometry['variant'] == 'd'
    assert st.features['SOLUSDT.vol_zscore'].value < 2.0


# --- no-setup / no-habitat rejection ----------------------------------------

def test_no_setup_within_range():
    """No close beyond the windowed extreme (100.1 is inside the 99.8-100.2
    window) -> no breakout -> NO_SETUP."""
    closes = [100.0] * 101 + [100.1]
    vols = [1.0] * 101 + [3.0]
    rows = _tape(closes, vols)
    ev = VolumeConfirmedBreakoutExpert().evaluate(_state_at(rows, 101))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_setup_unconfirmed_volume():
    """A breakout bar whose volume does not expand (== smoothed average, no
    near-min/1.2x/2.0x condition) is an unconfirmed breakout -> NO_SETUP."""
    closes = [100.0] * 101 + [101.5]
    vols = [1.0] * 102
    rows = _tape(closes, vols)
    ev = VolumeConfirmedBreakoutExpert().evaluate(_state_at(rows, 101))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_habitat_on_warmup_tape():
    """A tape too short for the 20-bar window and volume smoothing has no
    breakout habitat -> NO_HABITAT."""
    closes = [100.0] * 10
    rows = _tape(closes, [1.0] * 10)
    ev = VolumeConfirmedBreakoutExpert().evaluate(_state_at(rows, 9))
    assert ev.decision == 'NO_HABITAT'


# --- still_valid (post-entry thesis) ----------------------------------------

def test_still_valid_invalidated_on_retrace():
    """A LONG volume-confirmed breakout is dead once a close retraces back
    below the FROZEN broken level (the volume gate is not a stop input)."""
    e = VolumeConfirmedBreakoutExpert()
    closes = [100.0] * 41 + [101.5]
    rows = _tape(closes, [1.0] * 41 + [1.1])
    draft = e.evaluate(_state_at(rows, 41)).draft
    assert e.still_valid(_state_at(rows, 41), draft) is True
    # A later state closes back below the broken level: thesis dead.
    later = _tape(closes + [100.0], [1.0] * 41 + [1.1, 1.0])
    assert e.still_valid(_state_at(later, 42), draft) is False


def test_still_valid_fail_open():
    """Unobservable inputs fail open: a state without the close feature must
    not kill the thesis."""
    e = VolumeConfirmedBreakoutExpert()
    closes = [100.0] * 41 + [101.5]
    rows = _tape(closes, [1.0] * 41 + [1.1])
    draft = e.evaluate(_state_at(rows, 41)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- risk geometry + episode identity ---------------------------------------

def test_risk_geometry_values():
    e = VolumeConfirmedBreakoutExpert()
    closes = [100.0] * 41 + [101.5]
    rows = _tape(closes, [1.0] * 41 + [1.1])
    d = e.evaluate(_state_at(rows, 41)).draft
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['stop_r'] == 1.0
    assert g['expiry_bars'] == 8
    assert g['atr_ref'] > 0
    assert g['variant'] in e.variants_evaluated
    assert 'prior_low_ref' in g and g['prior_low_ref'] > 0


def test_episode_key_stable_across_consecutive_clocks():
    """The same breakout setup on two consecutive decision clocks hashes to
    the same episode key: the anchor (the first breakout bar of the run) is
    unchanged and the structural geometry is identical (the frozen level and
    atr_ref are excluded), so dedup can fire (D-026)."""
    e = VolumeConfirmedBreakoutExpert()
    closes = [100.0] * 100 + [101.5, 102.5]
    vols = [1.0] * 100 + [1.1, 1.1]
    rows = _tape(closes, vols)
    d1 = e.evaluate(_state_at(rows, 100)).draft
    d2 = e.evaluate(_state_at(rows, 101)).draft
    assert d1.setup_anchor_event_id == d2.setup_anchor_event_id
    keys = {episode_key(e.expert_id, e.version, d.instrument, d.direction,
                        d.setup_anchor_event_id, _geo(d)) for d in (d1, d2)}
    assert len(keys) == 1


# --- lab integration --------------------------------------------------------

def test_lab_smoke_no_claim(tmp_path):
    """The expert runs on the synthetic tape without breaking the lab; no
    economic claim is implied (rule 12)."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=23, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e15', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [VolumeConfirmedBreakoutExpert()])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    # Every evaluation persisted a non-None decision (auditability).
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')
