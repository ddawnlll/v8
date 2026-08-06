"""E-07 standard divergence expert tests.

Deterministic crafted tapes (verbatim OHLC) for the exact rule gates plus a
synthetic-tape lab smoke test. Cover: setup detection for both variants
(bearish peak-to-peak, bullish trough-to-trough), no-setup rejection on each
gate (no close confirmation, no price divergence, no oscillator divergence),
no-habitat on a warmup tape, still_valid invalidation + fail-open,
risk-geometry values, D-026 anchor stability across sliding windows, the
CRIT-7 no-pending-state structural constraint, the D-044 variants_evaluated
completeness, and lab dedup (SUPPRESSED_DUPLICATE).

The swing lattice is strength 5 (SWING_N), NOT 10 — see the expert module
docstring: the frozen 32-bar history window (O-020) makes a strength-10
divergence pair structurally unobservable. The crafted tapes place the two
pivots at window indices 19 and 25 (11+ bars inside the window, both past the
14-bar RSI seed, the second confirmed by the newest bar).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from v8.schema import TapeRow, MarketState
from v8.marketstate import build_state
from v8.synth import HOUR_NS
from v8.experts.divergence_12_setups import Divergence12SetupsExpert

UNIVERSE = ('SOLUSDT',)

# Pivot-bar range (2.5) is comfortably above ATR so the CRIT-1 significance
# filter passes; normal bars use range 2.0.
PIVOT_R = 1.25
NORM_R = 1.0


def _tape(bars):
    rows = []
    for i, (o, h, l, c) in enumerate(bars):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': 2.0, 'closed': True}))
    return rows


def _state_at(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of], as_of, UNIVERSE)


def _to_bars(closes, pivots, pivot_r=PIVOT_R, norm_r=NORM_R):
    """Close path -> (open, high, low, close) bars; pivot bars get the wide
    range so they pass the significance filter regardless of ATR."""
    out = []
    for i, cl in enumerate(closes):
        r = pivot_r if i in pivots else norm_r
        out.append((cl, cl + r, cl - r, cl))
    return out


def _bullish_closes():
    """Window 0..31. t1 (lower low) at idx 19 after a decline; rally 20..24;
    t2 at idx 25 (even lower low) after a milder second leg (rsi higher);
    drift 26..30 below the barrier; bar 31 confirms with a close above the
    barrier (max high of the rally = 106.5)."""
    closes = [112.0]
    for i in range(18):
        closes.append(closes[-1] - (0.7 if i % 3 != 2 else -0.15))
    closes.append(99.0)                        # t1 at 19, low 97.75
    for i in range(1, 6):
        closes.append(100.0 + 1.1 * i)         # rally 20..24, barrier 106.5
    closes.append(97.5)                        # t2 at 25, low 96.25 (lower low)
    for i in range(1, 6):
        closes.append(101.5 + 0.5 * i)         # drift 26..30 (below barrier)
    closes.append(107.5)                       # 31 close-through confirmation
    return closes


def _bearish_closes():
    """Window 0..31. Rally 0..18 into p1 at idx 19 (high 113.25); pullback
    20..24; p2 at idx 25 (higher high, high 114.75) with a weaker second leg
    (rsi lower); drift 26..30 above the barrier; bar 31 confirms with a close
    below the barrier (min low of the pullback = 107.0)."""
    closes = []
    c = 100.0
    for i in range(19):
        closes.append(c)
        c += 0.7 if i % 3 != 2 else -0.15
    closes.append(112.0)                       # p1 at 19, high 113.25
    closes.extend([111.0, 109.5, 108.5, 108.0, 108.0])   # pullback 20..24
    closes.append(113.5)                       # p2 at 25, high 114.75
    closes.extend([108.0, 108.5, 108.0, 107.6, 107.4])   # drift 26..30
    closes.append(106.0)                       # 31 close-through confirmation
    return closes


# --- ontology + variants_evaluated (D-044) ----------------------------------

def test_ontology_declared():
    e = Divergence12SetupsExpert()
    assert e.expert_id == 'divergence_12_setups'
    assert e.version == 'v1'
    assert e.mechanism_family_id == 'momentum_divergence'
    assert e.behavior_family_id == 'standard_divergence_reversal'
    assert e.variant_id == 'a'
    assert e.variants_evaluated == ('a', 'b')
    assert set(e.requires) == {'oscillator', 'location', 'volatility', 'history'}


def test_variants_evaluated_completeness():
    e = Divergence12SetupsExpert()
    assert len(e.variants_evaluated) == 2
    assert e.variant_id in e.variants_evaluated
    assert e.search_universe_size >= len(e.variants_evaluated)
    # D-044: a reported variant is a member of the evaluated set; the
    # reverse-divergence-continuation behavior is declared NOT implemented.
    assert Divergence12SetupsExpert('b').variant_id in e.variants_evaluated


def test_unknown_variant_fails_closed():
    with pytest.raises(ValueError):
        Divergence12SetupsExpert('z')


def test_not_a_router_and_no_pending_state():
    """CRIT-7: the confirmation must live inside the setup predicate — no
    expert-internal pending/unconfirmed signal state and no selection-layer
    wiring. Structural guards: no lifecycle/risk/simulator/lab imports, no
    other-expert names, and every detection path goes through
    find_setup_anchor over one predicate."""
    repo = Path(__file__).resolve().parents[1]
    src = (repo / 'src' / 'v8' / 'experts' / 'divergence_12_setups.py').read_text()
    for forbidden in ('from ..lifecycle', 'from ..risk', 'from ..simulator',
                      'from ..lab'):
        assert forbidden not in src
    for other in ('TrendPullback', 'FailedBreakout', 'LiquiditySweepReclaim',
                  'RsiStochReversion', 'VolumeConfirmedBreakout'):
        assert other not in src
    assert 'from ..schema import' in src and 'from .base import' in src
    assert 'find_setup_anchor' in src


# --- setup detection per variant --------------------------------------------

def test_variant_a_bearish_divergence_short():
    """p2 higher high (114.75 > 113.25) with rsi lower (77.9 < 94.0); close
    below the intervening support (107.0) confirms -> SHORT."""
    rows = _tape(_to_bars(_bearish_closes(), (19, 25)))
    st = _state_at(rows, 31)
    f = st.features
    assert float(f['SOLUSDT.swing_high_5'].value) == pytest.approx(114.75)
    ev = Divergence12SetupsExpert('a').evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'SHORT'
    g = d.risk_geometry
    assert g['variant'] == 'a'
    assert g['barrier_ref'] == pytest.approx(107.0)
    assert g['extremum_ref'] == pytest.approx(114.75)
    assert g['prior_high_ref'] == pytest.approx(114.75)
    assert d.setup_anchor_event_id == 'SOLUSDT:32'   # run start = confirm bar


def test_variant_b_bullish_divergence_long():
    """t2 lower low (96.25 < 97.75) with rsi higher (26.3 > 4.5); close above
    the intervening resistance (106.5) confirms -> LONG."""
    rows = _tape(_to_bars(_bullish_closes(), (19, 25)))
    st = _state_at(rows, 31)
    f = st.features
    assert float(f['SOLUSDT.swing_low_5'].value) == pytest.approx(96.25)
    ev = Divergence12SetupsExpert('b').evaluate(st)
    assert ev.decision == 'CANDIDATE'
    d = ev.draft
    assert d.direction == 'LONG'
    g = d.risk_geometry
    assert g['variant'] == 'b'
    assert g['barrier_ref'] == pytest.approx(106.5)
    assert g['extremum_ref'] == pytest.approx(96.25)
    assert g['prior_low_ref'] == pytest.approx(96.25)
    assert d.setup_anchor_event_id == 'SOLUSDT:32'


# --- no-setup rejection (each gate) -----------------------------------------

def test_no_setup_without_close_confirmation():
    """Divergence present but the newest close does NOT cross the barrier:
    CRIT-7's both-conditions predicate rejects the signal — no confirmation,
    no candidate (the lifecycle owns any confirmation gap, not the expert)."""
    closes = _bullish_closes()
    closes[-1] = 104.0                        # below barrier 106.5
    rows = _tape(_to_bars(closes, (19, 25)))
    st = _state_at(rows, 31)
    assert float(st.features['SOLUSDT.swing_low_5'].value) == pytest.approx(96.25)
    ev = Divergence12SetupsExpert('b').evaluate(st)
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_no_setup_without_price_divergence():
    """t2 is NOT a lower low (99.25 > 97.75): no divergence even with a close
    through the barrier -> NO_SETUP."""
    closes = _bullish_closes()
    closes[25] = 100.5                        # t2 low 99.25, above t1 low
    rows = _tape(_to_bars(closes, (19, 25)))
    st = _state_at(rows, 31)
    ev = Divergence12SetupsExpert('b').evaluate(st)
    assert ev.decision == 'NO_SETUP'


def test_no_setup_without_oscillator_divergence():
    """p2 is a higher high but rsi is HIGHER too (a strong second leg): the
    oscillator did not roll over -> NO_SETUP even with a close through the
    barrier. p1 is a small bounce high inside a decline (low rsi), p2 the
    strong rally high."""
    closes = []
    c = 110.0
    for i in range(19):                       # 0..18 decline
        closes.append(c)
        c -= 0.5 if i % 2 == 0 else 0.2
    closes.append(c + 0.8)                    # 19 p1 bounce high
    p1 = closes[-1]
    for i in range(5):
        closes.append(p1 - 1.0 - 0.6 * i)     # 20..24 pullback
    closes.append(p1 + 3.0)                   # 25 p2 strong rally high
    p2 = closes[-1]
    for i in range(1, 6):
        closes.append(p2 - 0.4 - 0.3 * i)     # 26..30 drift
    closes.append(97.5)                       # 31 close below barrier
    rows = _tape(_to_bars(closes, (19, 25), pivot_r=2.5))
    st = _state_at(rows, 31)
    assert float(st.features['SOLUSDT.swing_high_5'].value) > 106.0
    ev = Divergence12SetupsExpert('a').evaluate(st)
    assert ev.decision == 'NO_SETUP'


def test_no_habitat_on_warmup_tape():
    """Swing features need 11 bars and rsi14 needs 15; a 10-bar tape has no
    oscillator/location habitat -> NO_HABITAT."""
    rows = _tape(_to_bars([100.0] * 10, ()))
    for variant in ('a', 'b'):
        ev = Divergence12SetupsExpert(variant).evaluate(_state_at(rows, 9))
        assert ev.decision == 'NO_HABITAT'
        assert ev.draft is None


# --- D-026 anchor stability across sliding windows --------------------------

def test_anchor_stable_across_consecutive_clocks():
    """While the setup persists (close stays through the barrier), the anchor
    stays the confirmation bar across sliding 32-bar windows — the episode key
    does not drift (D-026 key stability)."""
    e = Divergence12SetupsExpert('b')
    base = _to_bars(_bullish_closes(), (19, 25))
    st = _state_at(_tape(base), 31)
    first = e.evaluate(st).draft
    assert first.setup_anchor_event_id == 'SOLUSDT:32'
    for extra in (108.0, 108.5, 108.0, 107.6):
        bars = base + [(extra, extra + 1.0, extra - 1.0, extra)]
        st2 = _state_at(_tape(bars), len(bars) - 1)
        ev2 = e.evaluate(st2)
        assert ev2.decision == 'CANDIDATE'
        assert ev2.draft.setup_anchor_event_id == 'SOLUSDT:32'


# --- still_valid (post-entry thesis) ----------------------------------------

def test_still_valid_invalidated_on_barrier_reclaim():
    """A LONG thesis dies when the close reclaims the frozen barrier (or a new
    low forms below the second trough); a SHORT thesis dies on a close back
    above the frozen barrier (or above the second peak)."""
    eb = Divergence12SetupsExpert('b')
    base_b = _to_bars(_bullish_closes(), (19, 25))
    draft = eb.evaluate(_state_at(_tape(base_b), 31)).draft
    assert eb.still_valid(_state_at(_tape(base_b), 31), draft) is True
    broke = _tape(base_b + [(104.0, 105.0, 103.0, 104.0)])
    assert eb.still_valid(_state_at(broke, 32), draft) is False
    new_low = _tape(base_b + [(94.0, 95.0, 93.0, 94.0)])
    assert eb.still_valid(_state_at(new_low, 32), draft) is False

    ea = Divergence12SetupsExpert('a')
    base_a = _to_bars(_bearish_closes(), (19, 25))
    draft = ea.evaluate(_state_at(_tape(base_a), 31)).draft
    assert ea.still_valid(_state_at(_tape(base_a), 31), draft) is True
    broke = _tape(base_a + [(108.5, 109.5, 107.5, 108.5)])
    assert ea.still_valid(_state_at(broke, 32), draft) is False
    new_high = _tape(base_a + [(116.0, 117.0, 115.0, 116.0)])
    assert ea.still_valid(_state_at(new_high, 32), draft) is False


def test_still_valid_fail_open():
    e = Divergence12SetupsExpert('b')
    base = _to_bars(_bullish_closes(), (19, 25))
    draft = e.evaluate(_state_at(_tape(base), 31)).draft
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE, features={},
                       lineage_hash='h')
    assert e.still_valid(bare, draft) is True


# --- risk geometry ----------------------------------------------------------

def test_risk_geometry_values():
    for variant, closes in (('a', _bearish_closes()), ('b', _bullish_closes())):
        e = Divergence12SetupsExpert(variant)
        rows = _tape(_to_bars(closes, (19, 25)))
        d = e.evaluate(_state_at(rows, 31)).draft
        g = d.risk_geometry
        assert g['entry'] == 'NEXT_BAR_CLOSE'
        assert g['target_r'] == 1.0
        assert g['stop_r'] == 1.0
        assert g['expiry_bars'] == 8
        assert g['atr_ref'] > 0
        assert g['variant'] in e.variants_evaluated
        assert g['barrier_ref'] > 0
        assert g['extremum_ref'] > 0
        # the frozen extremum doubles as the lifecycle pre-entry invalidation
        # level (lab.py consumes prior_low_ref / prior_high_ref)
        if variant == 'a':
            assert g['prior_high_ref'] == g['extremum_ref']
            assert 'prior_low_ref' not in g
        else:
            assert g['prior_low_ref'] == g['extremum_ref']
            assert 'prior_high_ref' not in g


# --- lab integration --------------------------------------------------------

def test_lab_dedup_and_no_claim(tmp_path):
    """The crafted tape re-detects the same setup on consecutive bars; the
    episode key is stable so the repeat is a SUPPRESSED_DUPLICATE, never a
    second candidate (D-026). The verdict stays NO_ECONOMIC_CLAIM."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest

    bars = _to_bars(_bullish_closes(), (19, 25))
    bars += [(108.0, 109.0, 107.0, 108.0), (108.5, 109.5, 107.5, 108.5)]
    lab = Lab(tmp_path)
    lab.ingest(_tape(bars))
    m = ExperimentManifest(experiment_id='exp-e07', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [Divergence12SetupsExpert('b')])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    assert r.candidate_count == 1
    kinds = {rec.get('kind') for rec in lab.candidates.read()}
    assert 'suppressed_duplicate' in kinds
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')


def test_lab_smoke_no_claim_synthetic(tmp_path):
    """Synthetic-tape smoke: the expert never crashes the decision loop and
    the economic verdict stays blocked."""
    from v8.lab import Lab
    from v8.schema import ExperimentManifest
    from v8.synth import make_synthetic_tape

    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=23, n_bars=200))
    m = ExperimentManifest(experiment_id='exp-e07', code_hash='', data_hash='',
                           universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [Divergence12SetupsExpert(), Divergence12SetupsExpert('b')])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    for rec in lab.evaluations.read():
        assert rec.get('decision') in ('NO_HABITAT', 'NO_SETUP', 'CANDIDATE')
