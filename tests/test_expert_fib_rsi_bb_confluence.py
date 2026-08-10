"""Fib+RSI+Bollinger confluence expert tests (D-076).

Covers: STRICT all-three-agree detection on a crafted deep-pullback reclaim
and its down-impulse mirror; MAJORITY two-of-three firing when the fib leg
abstains (and STRICT refusing the same tape); the confluence vote rule
(STRICT needs three equal votes, MAJORITY needs a two-vote majority — one
each is a no-trade); warmup NO_HABITAT; the post-setup NO_SETUP; episode-key
separation between variants and the anchor-as-run-start property (D-026);
still_valid composed of the three dead-thesis conditions + fail-open;
variants_evaluated completeness (D-044) and the requires audit; and a lab.run
smoke that never implies an economic claim (rule 12).

The crafted geometry (why the numbers are what they are): the confluence's
fade-zone close (below mid - 2*sigma of the 20-bar SMA) can only co-occur
with a fib reclaim when the retracement level sits BELOW the lower band —
that needs most of the last 20 closes near the high with only the impulse
low and the reclaim close as outliers. The up-impulse tape is a plateau at
~98.8-99.0 (35 bars), a V-drop to 90.0 (swing low 88.5), a recovery to 99.8
(swing high 100.8), a 9-bar plateau that confirms both swings, then a
reclaim bar whose close (93.2) sits in the fade zone (91.4, 93.4] and whose
low (90.7) dips below the frozen 0.786 level (91.13). The down-impulse
mirror is the same tape reflected around 200 (swing high 111.5, swing low
99.2, 0.786 level 108.87, rally-reclaim close 106.8).
"""
from __future__ import annotations

import pytest

from v8.schema import (TapeRow, MarketState, CandidateDraft, ExperimentManifest,
                       FEATURE_TO_GROUP, sha1_hex)
from v8.marketstate import build_state
from v8.lifecycle import episode_key
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.lab import Lab
from v8.experts.fib_rsi_bb_confluence import (
    FibRsiBbConfluenceExpert, FIB_RATIO)

UNIVERSE = ('SOLUSDT',)

# The up-impulse tape's confirmed swing pair: swing low 88.5 (bar 35),
# swing high 100.8 (bar 37), range 12.3 -> the frozen 0.786 level is
# 100.8 - 0.786*12.3 = 91.132. The down-impulse mirror: swing high 111.5
# (bar 35), swing low 99.2 (bar 37) -> 99.2 + 0.786*12.3 = 108.868.


def _tape(closes, rng_by_idx):
    rows = []
    for i, c in enumerate(closes):
        r = rng_by_idx(i)
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c + r, 'low': c - r, 'close': c,
                     'volume': 1.0, 'closed': True}))
    return rows


def _state(rows, idx: int) -> MarketState:
    return build_state(rows[:idx + 1], rows[idx].available_time, UNIVERSE)


def _long_tape(reclaim_rng: float = 2.5, cont: tuple = ()) -> list[TapeRow]:
    """Up-impulse plateau-V tape. Bar 47 is the reclaim bar: close 93.2 in
    the fade zone, low 90.7 dipping below the frozen 0.786 level (91.13).
    `reclaim_rng` controls how deep the low dips; at 2.0 the low (91.2) does
    NOT reach the level, so the fib leg abstains (the MAJORITY-only tape).
    `cont` appends continuation closes (used for still_valid / NO_SETUP)."""
    closes = [98.8 + 0.1 * (i % 3) for i in range(35)]
    closes += [90.0, 99.05, 99.8]            # 35 swing low, 36 recovery, 37 high
    closes += [99.05] * 9                     # 38-46 confirm both swings
    closes.append(93.2)                       # 47 reclaim
    closes += list(cont)

    def rng(i):
        if i == 35:
            return 1.5                        # low 88.5
        if i == 47:
            return reclaim_rng                # low dips to 93.2 - reclaim_rng
        return 1.0
    return _tape(closes, rng)


def _short_tape(reclaim_rng: float = 2.5) -> list[TapeRow]:
    """Down-impulse mirror of `_long_tape` (reflected around 200): swing
    high 111.5 at bar 35, swing low 99.2 at bar 37, rally-reclaim close
    106.8 at bar 47 in the upper fade zone, high dipping above the frozen
    0.786 level (108.87)."""
    closes = [101.2 - 0.1 * (i % 3) for i in range(35)]
    closes += [110.0, 100.95, 100.2]          # 35 swing high, 36 drop, 37 low
    closes += [100.95] * 9                     # 38-46 confirm both swings
    closes.append(106.8)                       # 47 rally-reclaim

    def rng(i):
        if i == 35:
            return 1.5                        # high 111.5
        if i == 47:
            return reclaim_rng                # high reaches 106.8 + reclaim_rng
        return 1.0
    return _tape(closes, rng)


def _draft(rows, idx: int, expert) -> CandidateDraft:
    ev = expert.evaluate(_state(rows, idx))
    assert ev.draft is not None, f'no draft at bar {idx} ({ev.decision})'
    return ev.draft


def _geo(draft: CandidateDraft) -> str:
    # Mirrors lab._geometry_version: data-dependent refs (atr, prior_*,
    # the frozen 3-SD band) are excluded from episode identity.
    structural = {k: v for k, v in draft.risk_geometry.items()
                  if k not in ('atr_ref', 'prior_low_ref', 'prior_high_ref',
                               'lower_3sd_ref', 'upper_3sd_ref')}
    return sha1_hex(structural)


def _deep_level(rows, idx: int) -> float:
    fibs = _state(rows, idx).features['SOLUSDT.fib_levels'].value
    return next(lv for r, lv in fibs[2] if abs(r - FIB_RATIO) < 1e-9)


# --- setup detection ---------------------------------------------------------

def test_strict_long_all_three_agree():
    ex = FibRsiBbConfluenceExpert()                    # variant a: STRICT
    rows = _long_tape()
    d = _draft(rows, 47, ex)
    assert d.direction == 'LONG'
    assert d.setup_anchor_event_id == 'SOLUSDT:48'     # run start = reclaim bar
    g = d.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['target_r'] == 1.0
    assert g['stop_r'] == 1.0
    assert g['expiry_bars'] == 8
    assert g['variant'] == 'a'
    atr = _state(rows, 47).features['SOLUSDT.atr'].value
    assert g['atr_ref'] == pytest.approx(atr)
    assert g['atr_ref'] > 0.0
    # The frozen invalidation refs: the 0.786 level and the 3-SD band, both
    # below the entry close (93.2) — the reversion premise references.
    assert g['prior_low_ref'] == pytest.approx(_deep_level(rows, 47))
    assert g['prior_low_ref'] == pytest.approx(91.132, abs=1e-3)
    assert g['lower_3sd_ref'] == pytest.approx(91.405, abs=1e-3)


def test_strict_short_mirror():
    ex = FibRsiBbConfluenceExpert()
    rows = _short_tape()
    d = _draft(rows, 47, ex)
    assert d.direction == 'SHORT'
    assert d.setup_anchor_event_id == 'SOLUSDT:48'
    g = d.risk_geometry
    assert g['prior_high_ref'] == pytest.approx(_deep_level(rows, 47))
    assert g['prior_high_ref'] == pytest.approx(108.868, abs=1e-3)
    assert g['upper_3sd_ref'] == pytest.approx(108.595, abs=1e-3)
    assert g['target_r'] == 1.0 and g['stop_r'] == 1.0


def test_majority_fires_when_fib_abstains_but_strict_does_not():
    """The same tape with a shallower reclaim dip: the low (91.2) does not
    reach the frozen level (91.13), so the fib leg abstains. MAJORITY (b)
    fires on the bb+rsi pair; STRICT (a) refuses — it needs all three."""
    rows = _long_tape(reclaim_rng=2.0)
    strict = FibRsiBbConfluenceExpert()                # a
    majority = FibRsiBbConfluenceExpert(variant_id='b')
    assert strict.evaluate(_state(rows, 47)).decision == 'NO_SETUP'
    d = _draft(rows, 47, majority)
    assert d.direction == 'LONG'
    assert d.risk_geometry['variant'] == 'b'


# --- confluence vote rule (pure function) -------------------------------------

def test_confluence_vote_rule():
    """STRICT needs three non-None equal votes; MAJORITY needs a two-vote
    majority (a LONG+SHORT split is a no-trade, not a coin flip)."""
    a = FibRsiBbConfluenceExpert()
    b = FibRsiBbConfluenceExpert(variant_id='b')
    assert a._confluence_vote(['LONG', 'LONG', 'LONG']) == 'LONG'
    assert a._confluence_vote(['SHORT', 'SHORT', 'SHORT']) == 'SHORT'
    # An abstaining leg voids STRICT even when the other two agree.
    assert a._confluence_vote(['LONG', 'LONG', None]) is None
    # A conflict voids STRICT.
    assert a._confluence_vote(['LONG', 'SHORT', 'LONG']) is None
    assert b._confluence_vote(['LONG', 'LONG', None]) == 'LONG'
    assert b._confluence_vote(['SHORT', 'SHORT', 'LONG']) == 'SHORT'
    # One each: no majority, no signal.
    assert b._confluence_vote(['LONG', 'SHORT', None]) is None
    assert b._confluence_vote(['LONG', None, None]) is None
    assert b._confluence_vote([None, None, None]) is None


# --- rejection paths -----------------------------------------------------------

def test_no_habitat_during_warmup():
    ex = FibRsiBbConfluenceExpert()
    rows = _long_tape()
    # The fib anchor needs a confirmed swing pair (n_close >= 21 AND both
    # swings flank-confirmed); before bar 47 the pair is not yet confirmed.
    for idx in (20, 30, 40):
        assert ex.evaluate(_state(rows, idx)).decision == 'NO_HABITAT'


def test_no_setup_after_the_reclaim_run():
    ex = FibRsiBbConfluenceExpert()
    rows = _long_tape(cont=(93.1,))                   # bar 48: no fade-zone close
    assert ex.evaluate(_state(rows, 48)).decision == 'NO_SETUP'


# --- episode identity (D-026) ---------------------------------------------------

def test_episode_keys_and_anchor():
    """The anchor is the confluence run start (the reclaim bar), so the same
    setup on consecutive clocks hashes to the same key; and the `variant`
    geometry key separates a/b episodes (lab._geometry_version excludes only
    atr/prior refs — without it variant-b candidates would be suppressed as
    duplicates of variant-a)."""
    rows = _long_tape()
    a = FibRsiBbConfluenceExpert()
    b = FibRsiBbConfluenceExpert(variant_id='b')
    da, db = _draft(rows, 47, a), _draft(rows, 47, b)
    assert da.setup_anchor_event_id == db.setup_anchor_event_id == 'SOLUSDT:48'
    ka = episode_key(a.expert_id, a.version, da.instrument, da.direction,
                     da.setup_anchor_event_id, _geo(da))
    kb = episode_key(b.expert_id, b.version, db.instrument, db.direction,
                     db.setup_anchor_event_id, _geo(db))
    assert ka != kb                                   # variant-separated
    # The structural geometry (minus data-dependent refs) differs only in the
    # variant key — the two keys are identical otherwise.
    geo_a = {k: v for k, v in da.risk_geometry.items()
             if k not in ('atr_ref', 'prior_low_ref', 'prior_high_ref')}
    geo_b = {k: v for k, v in db.risk_geometry.items()
             if k not in ('atr_ref', 'prior_low_ref', 'prior_high_ref')}
    assert geo_a == {**geo_b, 'variant': 'a'} == {**geo_a, 'variant': 'a'}


# --- still_valid ----------------------------------------------------------------

def test_still_valid_composition_and_fail_open():
    ex = FibRsiBbConfluenceExpert()
    rows = _long_tape()
    draft = _draft(rows, 47, ex)
    # Above both frozen refs, oscillator recovered: thesis alive.
    assert ex.still_valid(_state(_long_tape(cont=(93.0,)), 48), draft) is True
    # RSI-only death: close 92.2 sits above both frozen refs (91.132, 91.405)
    # but the oscillator re-entered oversold (rsi14 29.4 <= 30).
    assert ex.still_valid(_state(_long_tape(cont=(92.2,)), 48), draft) is False
    # Bollinger death: close 91.35 is at/beyond the frozen 3-SD band (91.405).
    assert ex.still_valid(_state(_long_tape(cont=(91.35,)), 48), draft) is False
    # Fib death: close 90.0 is below the frozen 0.786 level (deep correction).
    assert ex.still_valid(_state(_long_tape(cont=(90.0,)), 48), draft) is False
    # Unobservable close/oscillator: fail open (an unreadable thesis is not a
    # dead one).
    bare = MarketState(state_id='x', as_of=0, universe=UNIVERSE,
                       features={}, lineage_hash='')
    assert ex.still_valid(bare, draft) is True


# --- variants (D-044 / rule 13) -------------------------------------------------

def test_variants_evaluated_complete_and_unknown_raises():
    ex = FibRsiBbConfluenceExpert()
    assert ex.variant_id == 'a'
    assert ex.variants_evaluated == ('a', 'b')
    assert ex.variant_id in ex.variants_evaluated
    assert ex.search_universe_size >= len(ex.variants_evaluated)
    with pytest.raises(ValueError, match='unknown variant'):
        FibRsiBbConfluenceExpert(variant_id='x')


# --- requires / consumption audit -----------------------------------------------

def test_requires_audited_against_consumption():
    ex = FibRsiBbConfluenceExpert()
    assert ex.requires, 'requires must be non-empty'
    consumed = {'close', 'atr', 'history', 'bb_mid', 'bb_upper', 'bb_lower',
                'rsi14', 'fib_levels'}
    read_groups = {FEATURE_TO_GROUP[n] for n in consumed}
    allowed = set(ex.requires) | {'raw'}
    assert read_groups <= allowed


# --- lab smoke ---------------------------------------------------------------------

def test_lab_run_smoke_verdict_stays_no_economic_claim(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    m = ExperimentManifest(experiment_id='exp-confluence-1', code_hash='',
                           data_hash='', universe=UNIVERSE, start_ns=0, end_ns=0)
    r = lab.run(m, [FibRsiBbConfluenceExpert(),
                    FibRsiBbConfluenceExpert(variant_id='b')])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'            # rule 12
    assert sum(r.terminal_distribution.values()) == r.candidate_count
    # The crafted tape drives a candidate through the full lifecycle.
    lab2 = Lab(tmp_path / 'crafted')
    lab2.ingest(_long_tape())
    m2 = ExperimentManifest(experiment_id='exp-confluence-2', code_hash='',
                            data_hash='', universe=UNIVERSE, start_ns=0, end_ns=0)
    r2 = lab2.run(m2, [FibRsiBbConfluenceExpert()])
    assert r2.candidate_count > 0
    assert r2.verdict == 'NO_ECONOMIC_CLAIM'
