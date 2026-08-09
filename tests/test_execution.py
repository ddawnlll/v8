"""EXEC-1..6 tests: position management and fill policies (O-013; EX-01..EX-12).

EXEC-1  breakeven roll + chandelier trail (EX-01/05) — stop_level machinery.
EXEC-2  scale-out / partial exits (EX-02/04) — StepResult.closed_fraction,
        realized_r/remaining accounting, lifecycle PARTIAL_EXIT PositionAction.
EXEC-3  pyramiding (EX-03) — declared `pyramid_add_rules` key, midpoint-stop
        math primitive, OFF by default (requesting it fails closed).
EXEC-4  FILL_AT_LIMIT (EX-11) — barrier entry, fill-only entry-bar inspection,
        never-filling orders never enter.
EXEC-5  TIME_EXIT endpoint (EX-09/12) — distinct from STOP/TARGET/EXPIRY.
EXEC-6  hash discipline — sim.hash() re-versions to canonical-sim-v8 and the
        management keys actually change step() output.

Every threshold below is a DECLARED numeric literal (frozen pre-holdout,
O-017 method) — none is fitted to any data window. The pilots' default
geometry declares none of the management keys, so the existing frozen-geometry
goldens are unaffected (verified separately).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from v8.schema import CandidateDraft, ExpertEvaluation, TapeRow
from v8.simulator import (CanonicalSimulator, OpenPosition, midpoint_stop,
                          risk_unit, SUPPORTED_FILL_POLICIES, _SIMULATOR_SRC_HASH)
from v8.lifecycle import CandidateRegistry
from v8.store import AppendOnlyLog
from v8.lab import Lab
from v8.schema import sha1_hex

HOUR_NS = 3_600_000_000_000
UNIVERSE = ('SOLUSDT',)


def _draft(direction='LONG', entry=100.0, atr=2.0, target_r=2.0, stop_r=1.0,
           expiry=10, **geometry) -> CandidateDraft:
    risk_geometry = {'target_r': target_r, 'stop_r': stop_r,
                     'expiry_bars': expiry, 'atr_ref': atr}
    risk_geometry.update(geometry)
    return CandidateDraft(expert_id='t', expert_version='v1', instrument='SOLUSDT',
                          direction=direction, setup_fingerprint='fp',
                          risk_geometry=risk_geometry, birth_time=0)


def _pos(direction='LONG', entry=100.0, atr=2.0, target_r=2.0, stop_r=1.0,
         expiry=10, **geometry) -> OpenPosition:
    return OpenPosition(candidate_id='c1', draft=_draft(
        direction=direction, atr=atr, target_r=target_r, stop_r=stop_r,
        expiry=expiry, **geometry), entry_price=entry, entry_bar_index=0)


# --- EXEC-1: breakeven roll + trailing -------------------------------------

def test_breakeven_roll_moves_stop_and_endpoint_stays_stop():
    """Once mfe_r crosses breakeven_roll_at_mfe_r the effective stop rolls to
    entry +/- breakeven_margin_r; a later stop-out is still endpoint STOP
    (vocabulary preserved) and costs exactly the margin + the round trip."""
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    pos = _pos(breakeven_roll_at_mfe_r=1.5, breakeven_margin_r=0.07)
    # Bar 1: high 103.5 -> mfe 1.75R crosses the threshold. The low 99.0 sits
    # between the old static stop (98.0) and the new rolled stop (99.86) — the
    # rolled stop applies from the NEXT bar, so no phantom same-bar stop-out.
    r1 = sim.step(pos, {'open': 100.0, 'high': 103.5, 'low': 99.0, 'close': 103.0})
    assert not r1.closed
    assert r1.next_pos.stop_rolled is True
    assert r1.next_pos.stop_level == pytest.approx(100.0 - 0.07 * 2.0)
    # Bar 2: the rolled stop is taken out -> STOP at the rolled barrier.
    r2 = sim.step(r1.next_pos, {'open': 103.0, 'high': 103.2, 'low': 99.5,
                                'close': 100.0})
    assert r2.endpoint == 'STOP'
    assert r2.label_status == 'MATURE'
    assert r2.net_r == pytest.approx(-0.07 - 0.07, abs=1e-12)


def test_breakeven_margin_defaults_to_round_trip_cost():
    sim = CanonicalSimulator(round_trip_cost_r=0.05)
    pos = _pos(breakeven_roll_at_mfe_r=1.5)          # no explicit margin
    r = sim.step(pos, {'open': 100.0, 'high': 103.5, 'low': 99.0, 'close': 103.0})
    assert r.next_pos.stop_level == pytest.approx(100.0 - 0.05 * 2.0)


def test_breakeven_roll_is_one_shot():
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    pos = _pos(target_r=5.0, breakeven_roll_at_mfe_r=1.5,
               breakeven_margin_r=0.07)
    r1 = sim.step(pos, {'open': 100.0, 'high': 103.5, 'low': 99.0, 'close': 103.0})
    # A higher mfe on the next bar must not roll again (margin already applied).
    r2 = sim.step(r1.next_pos, {'open': 103.0, 'high': 107.0, 'low': 102.0,
                                'close': 106.0})
    assert not r2.closed and r2.next_pos.stop_rolled is True
    assert r2.next_pos.stop_level == pytest.approx(100.0 - 0.07 * 2.0)


def test_no_management_key_keeps_static_geometry():
    """Default geometry: stop_level stays None, step output unchanged."""
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    pos = _pos()
    r = sim.step(pos, {'open': 100.0, 'high': 103.5, 'low': 99.0, 'close': 103.0})
    assert not r.closed
    assert r.next_pos.stop_level is None
    assert r.next_pos.stop_rolled is False
    # Same bar, static stop at 98: no exit.
    r2 = sim.step(pos, {'open': 100.0, 'high': 104.0, 'low': 99.0, 'close': 103.0})
    assert r2.endpoint == 'TARGET'                    # 104.0 >= target 104.0


def test_chandelier_trail_ratchets_with_mfe():
    """trail_stop_atr: the stop trails k*ATR behind the extreme and never
    gives back ground (ratchet)."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(target_r=5.0, trail_stop_atr=2.0)      # k=2, unit=2 -> 4.0 back
    r1 = sim.step(pos, {'open': 100.0, 'high': 106.0, 'low': 100.0, 'close': 105.0})
    assert not r1.closed
    assert r1.next_pos.stop_level == pytest.approx(100.0 + (3.0 - 2.0) * 2.0)
    # Bar 2 makes a lower high: the trail must not give back the level.
    r2 = sim.step(r1.next_pos, {'open': 105.0, 'high': 104.0, 'low': 101.0,
                                'close': 102.0})
    assert r2.next_pos.stop_level == pytest.approx(102.0)
    # Bar 3 breaks the trail: endpoint STOP at the trailed barrier.
    r3 = sim.step(r2.next_pos, {'open': 102.0, 'high': 102.0, 'low': 101.5,
                                'close': 102.0})
    assert r3.endpoint == 'STOP'
    assert r3.net_r == pytest.approx(1.0, abs=1e-12)


def test_trail_never_worse_than_static_stop():
    """The ratchet starts at the static stop: an early low mfe cannot lower the
    effective stop below the declared stop_r barrier."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(trail_stop_atr=2.0)
    r = sim.step(pos, {'open': 100.0, 'high': 101.0, 'low': 99.5, 'close': 100.5})
    # trail = 100 + (0.5 - 2.0)*2 = 97.0, which would be WORSE than the static
    # stop 98.0 — the ratchet never gives ground, so it starts at the base stop.
    assert r.next_pos.stop_level == pytest.approx(98.0)


# --- EXEC-2: scale-out / partial exits --------------------------------------

def test_scale_out_is_non_terminal_partial():
    """Crossing scale_out_at_mfe_r closes fraction f = stop_r/(stop_r+target_r)
    at bar close: closed_fraction < 1.0, endpoint None, position continues at
    remaining = 1-f with its stop unchanged."""
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    pos = _pos(target_r=5.0, stop_r=1.0, scale_out_ratio=1.0,
               scale_out_at_mfe_r=2.0)
    r = sim.step(pos, {'open': 100.0, 'high': 104.5, 'low': 99.0, 'close': 103.5})
    assert not r.closed
    assert r.endpoint is None
    assert r.closed_fraction == pytest.approx(1.0 / 6.0)       # 1/(1+5)
    assert r.next_pos.remaining == pytest.approx(5.0 / 6.0)
    assert r.next_pos.scaled_out is True
    assert r.next_pos.realized_r == pytest.approx((1.0 / 6.0) * (103.5 - 100.0) / 2.0)
    assert r.next_pos.stop_level is None                        # stop unchanged


def test_scale_out_terminal_net_r_books_the_partial():
    """After a partial, the terminal net_r = realized_r + remaining*leg - cost:
    the scaled-out leg's profit is not lost when the remainder stops."""
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    pos = _pos(target_r=5.0, stop_r=1.0, scale_out_ratio=1.0,
               scale_out_at_mfe_r=2.0)
    r1 = sim.step(pos, {'open': 100.0, 'high': 104.5, 'low': 99.0, 'close': 103.5})
    assert r1.closed_fraction == pytest.approx(1.0 / 6.0)
    r2 = sim.step(r1.next_pos, {'open': 100.0, 'high': 100.0, 'low': 97.5,
                                'close': 98.0})
    assert r2.endpoint == 'STOP'
    expected = (1.0 / 6.0) * ((103.5 - 100.0) / 2.0) \
        + (5.0 / 6.0) * ((98.0 - 100.0) / 2.0) - 0.07
    assert r2.net_r == pytest.approx(expected, abs=1e-12)


def test_scale_out_off_by_default():
    """scale_out_ratio default 0 = off: no partial ever fires."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(target_r=5.0, scale_out_at_mfe_r=2.0)  # ratio absent
    r = sim.step(pos, {'open': 100.0, 'high': 106.0, 'low': 99.0, 'close': 105.0})
    assert not r.closed
    assert r.closed_fraction == 1.0
    assert r.next_pos.remaining == 1.0
    assert r.next_pos.scaled_out is False


def test_scale_out_one_shot():
    """The partial fires once; later mfe growth does not scale out again."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(target_r=5.0, stop_r=1.0, scale_out_ratio=1.0,
               scale_out_at_mfe_r=1.5)
    r1 = sim.step(pos, {'open': 100.0, 'high': 104.0, 'low': 99.0, 'close': 103.0})
    assert r1.closed_fraction == pytest.approx(1.0 / 6.0)
    r2 = sim.step(r1.next_pos, {'open': 103.0, 'high': 108.0, 'low': 102.0,
                                'close': 107.0})
    assert not r2.closed and r2.closed_fraction == 1.0
    assert r2.next_pos.remaining == pytest.approx(5.0 / 6.0)


def test_scale_out_breaks_on_same_bar_terminal():
    """A bar that both crosses the scale threshold and hits a barrier exits
    terminally (STOP_FIRST among price events) — no partial, conservative."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(target_r=5.0, stop_r=1.0, scale_out_ratio=1.0,
               scale_out_at_mfe_r=1.5)
    r = sim.step(pos, {'open': 100.0, 'high': 104.0, 'low': 97.0, 'close': 99.0})
    assert r.closed and r.endpoint == 'STOP'
    assert r.closed_fraction == 1.0


# --- EXEC-3: pyramiding plumbing (OFF) --------------------------------------

def test_midpoint_stop_math():
    """EX-03 midpoint-stop primitive: (entry + add_price)/2 — the book's
    'roll both stops to midway between the two entry levels'."""
    assert midpoint_stop(100.0, 110.0) == 105.0
    assert midpoint_stop(100.0, 104.0) == 102.0
    assert midpoint_stop(80.0, 100.0) == 90.0


def test_pyramid_add_rules_fails_closed():
    """Pyramiding is declared (risk_geometry key + midpoint primitive) but P2:
    a draft that requests it fails closed rather than trading a partial
    implementation. Absent (the default) keeps behavior unchanged."""
    sim = CanonicalSimulator()
    pos = _pos(pyramid_add_rules={'add_at_mfe_r': [2.0], 'add_fraction': 0.5})
    with pytest.raises(ValueError, match='pyramid'):
        sim.step(pos, {'open': 100.0, 'high': 103.0, 'low': 99.0, 'close': 102.0})


# --- EXEC-4: FILL_AT_LIMIT ---------------------------------------------------

def _limit_bars():
    """Hand-built bar payloads: closes 100..106 rising, bar 3 dips low (101.0)."""
    payloads = []
    for i in range(7):
        c = 100.0 + i
        lo = 101.0 if i == 3 else c - 0.5
        payloads.append({'open': c, 'high': c + 0.5, 'low': lo,
                         'close': c, 'volume': 1.0})
    return payloads


def _limit_fill_then_target_bars():
    """Bar 0 fills the limit (low 99.0 <= 102.0) and dips below the would-be
    stop (101.0); bar 1 hits the 2R target (104.0) without touching the stop
    (low 101.5 > 101.0), so the outcome is a clean TARGET."""
    return [
        {'open': 100.0, 'high': 100.5, 'low': 99.0, 'close': 100.0},
        {'open': 102.0, 'high': 104.5, 'low': 101.5, 'close': 104.0},
    ]


def test_fill_at_limit_supported_policy():
    assert 'FILL_AT_LIMIT' in SUPPORTED_FILL_POLICIES


def test_run_fill_at_limit_fills_at_the_limit_price():
    """FILL_AT_LIMIT fills at the declared limit_price when a bar's range
    trades through it (fill-only inspection of the entry bar)."""
    sim = CanonicalSimulator(fill_policy='FILL_AT_LIMIT', round_trip_cost_r=0.0)
    draft = _draft(limit_price=102.0, target_r=2.0, stop_r=1.0, atr=1.0)
    out = sim.run(draft, _limit_fill_then_target_bars(),
                  times=[HOUR_NS * i for i in range(2)])
    assert out.endpoint == 'TARGET'
    assert out.entry_price == pytest.approx(102.0)          # filled at the limit
    assert out.net_r == pytest.approx((104.0 - 102.0) / 1.0)  # target 104.0


def test_run_fill_at_limit_entry_bar_not_inspected_for_exits():
    """The entry (fill) bar's low (99.0) is below the would-be stop (101.0): if
    the simulator inspected the entry bar for exits, the outcome would be STOP.
    Fill-only inspection means the position opens at the limit and exits are
    evaluated from the next bar — outcome TARGET proves the invariant."""
    sim = CanonicalSimulator(fill_policy='FILL_AT_LIMIT', round_trip_cost_r=0.0)
    draft = _draft(limit_price=102.0, target_r=2.0, stop_r=1.0, atr=1.0)
    out = sim.run(draft, _limit_fill_then_target_bars(),
                  times=[HOUR_NS * i for i in range(2)])
    assert out.endpoint == 'TARGET'
    assert out.entry_price == pytest.approx(102.0)


def test_run_fill_at_limit_never_filling_never_enters():
    """A limit no bar trades through never enters: never-entered convention
    (EXPIRY / NOT_EXECUTED / 0.0), knowable at the tape end."""
    sim = CanonicalSimulator(fill_policy='FILL_AT_LIMIT', round_trip_cost_r=0.0)
    draft = _draft(limit_price=90.0, target_r=2.0, stop_r=1.0, atr=1.0)
    out = sim.run(draft, _limit_bars(), times=[HOUR_NS * i for i in range(7)])
    assert out.endpoint == 'EXPIRY'
    assert out.label_status == 'NOT_EXECUTED'
    assert out.net_r == 0.0
    assert out.horizon_bars == 0


def test_fill_at_limit_missing_limit_price_fails_closed():
    sim = CanonicalSimulator(fill_policy='FILL_AT_LIMIT')
    with pytest.raises(ValueError, match='limit_price'):
        sim.run(_draft(), _limit_bars())


# --- EXEC-5: TIME_EXIT endpoint ----------------------------------------------

def test_time_exit_is_a_distinct_endpoint():
    """time_exit_bars exits at bar close with the distinct TIME_EXIT endpoint
    (RIGHT_CENSORED label, like EXPIRY) once bars_held reaches the horizon."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(time_exit_bars=3)
    quiet = {'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0}
    r1 = sim.step(pos, quiet)
    assert not r1.closed
    r2 = sim.step(r1.next_pos, quiet)
    assert not r2.closed
    r3 = sim.step(r2.next_pos, quiet)                    # bars_held == 3
    assert r3.endpoint == 'TIME_EXIT'
    assert r3.label_status == 'RIGHT_CENSORED'
    assert r3.net_r == pytest.approx(0.0)                # exit at close = entry


def test_time_exit_fires_before_expiry():
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(expiry=8, time_exit_bars=4)
    quiet = {'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0}
    p = pos
    for _ in range(3):
        p = sim.step(p, quiet).next_pos or p
    r = sim.step(p, quiet)                               # bars_held == 4
    assert r.endpoint == 'TIME_EXIT'


def test_stop_and_target_win_over_time_exit():
    """On the same bar, price events take priority: a time horizon is not an
    excuse to skip a real stop-out."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos(time_exit_bars=2, stop_r=1.0)
    r = sim.step(pos, {'open': 100.0, 'high': 100.5, 'low': 97.5, 'close': 99.0})
    assert r.endpoint == 'STOP'


def test_time_exit_absent_by_default():
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    pos = _pos()
    r = sim.step(pos, {'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0})
    assert not r.closed and r.endpoint is None


# --- EXEC-6: hash discipline -------------------------------------------------

def test_sim_hash_reversions_to_canonical_sim_v8():
    """The endpoint vocabulary and step() semantics changed, so sim.hash() must
    differ from the pre-EXEC tag even though the module source hash also moved
    on its own (both bindings move in the same direction)."""
    h = CanonicalSimulator().hash()
    assert h == sha1_hex(('canonical-sim-v8', 'FILL_AT_BAR_CLOSE', 0.07, 0.0, 8,
                          'flat', _SIMULATOR_SRC_HASH))
    assert h != sha1_hex(('canonical-sim-v7', 'FILL_AT_BAR_CLOSE', 0.07, 0.0, 8,
                          'flat', _SIMULATOR_SRC_HASH))
    # The cost FORM is part of the identity: a bps run must never hash equal
    # to the flat-R run, even when the two price an episode the same.
    assert h != CanonicalSimulator(round_trip_cost_bps=5.0).hash()


def test_managed_geometry_changes_step_output():
    """The management keys are not decorative: the same two bars produce a
    different exit under a trailing geometry than under the static geometry,
    so old and new sim outputs differ exactly when the semantics differ."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    bar1 = {'open': 100.0, 'high': 103.5, 'low': 100.0, 'close': 103.0}
    bar2 = {'open': 103.0, 'high': 103.0, 'low': 99.0, 'close': 100.0}
    r1p = sim.step(_pos(), bar1)                        # static: no stop_level
    r2p = sim.step(r1p.next_pos, bar2)                  # static stop 98: 99.0 > 98
    assert not r2p.closed                               # no exit under static
    r1t = sim.step(_pos(trail_stop_atr=2.0), bar1)      # trail -> stop 99.5
    assert r1t.next_pos.stop_level == pytest.approx(99.5)
    r2t = sim.step(r1t.next_pos, bar2)                  # 99.0 <= 99.5 -> STOP
    assert r2t.endpoint == 'STOP'
    assert r2p.closed != r2t.closed


# --- Lab end-to-end: PARTIAL_EXIT wiring + FILL_AT_LIMIT entry ---------------

class _ManagedExpert:
    """Minimal self-gating expert emitting ONE managed draft (dedup via a fixed
    anchor). Tests the lab's executed-path wiring for management keys."""
    expert_id = 'z_managed'
    version = 'v1'

    def __init__(self, **geometry):
        self.geometry = dict(entry='NEXT_BAR_CLOSE', target_r=2.0, stop_r=1.0,
                             expiry_bars=8, atr_ref=1.0)
        self.geometry.update(geometry)

    def evaluate(self, state):
        pl = state.features.get('SOLUSDT.prior_low')
        if pl is None or pl.value is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'APPLICABLE', 'NO_SETUP', state.as_of, None)
        draft = CandidateDraft(expert_id=self.expert_id, expert_version=self.version,
                               instrument='SOLUSDT', direction='LONG',
                               setup_fingerprint='managed',
                               risk_geometry=dict(self.geometry),
                               setup_anchor_event_id='SOLUSDT:anchor1',
                               birth_time=state.as_of)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', state.as_of, draft)

    def still_valid(self, state, draft):
        return True


def _managed_tape(n=8) -> list[TapeRow]:
    """Rising closes 100..107. prior_low exists from bar 1; entry bar 3
    (close 103); bar 4 high 104.5 crosses mfe 1.5R (scale threshold); bar 5
    hits the 2R target."""
    rows = []
    for i in range(n):
        c = 100.0 + i
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c + 0.5, 'low': c - 0.5,
                     'close': c, 'volume': 1.0, 'closed': True}))
    return rows


def _manifest(**kw):
    from v8.schema import ExperimentManifest
    base = dict(experiment_id='exp-exec', code_hash='', data_hash='',
                universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    return ExperimentManifest(**base)


def test_lab_records_partial_exit_and_books_terminal(tmp_path):
    """End to end: a managed scale-out position records a PARTIAL_EXIT
    PositionAction (append-only, non-terminal) and the terminal outcome's
    net_r includes the realized partial leg. One candidate, one outcome."""
    lab = Lab(tmp_path)
    lab.ingest(_managed_tape())
    ex = _ManagedExpert(scale_out_ratio=1.0, scale_out_at_mfe_r=1.5)
    r = lab.run(_manifest(), [ex])
    assert r.candidate_count == 1
    assert r.terminal_distribution == {'CLOSED': 1}
    actions = [rec for rec in lab.candidates.read()
               if rec.get('kind') == 'position_action']
    assert len(actions) == 1
    assert actions[0]['action'] == 'PARTIAL_EXIT'
    assert isinstance(actions[0]['candidate_id'], str) and actions[0]['candidate_id']
    assert actions[0]['fraction'] == pytest.approx(1.0 / 3.0)   # 1/(1+2)
    assert actions[0]['price'] == pytest.approx(104.0)          # bar-4 close
    outs = lab.outcomes.read()
    assert len(outs) == 1
    o = outs[0]
    assert o['endpoint'] == 'TARGET'
    assert o['label_status'] == 'MATURE'
    # realized partial (1/3)*(104-103) + remaining (2/3)*(105-103) - cost
    assert o['net_r'] == pytest.approx((1.0 / 3.0) + (2.0 / 3.0) * 2.0 - 0.07,
                                       abs=1e-12)
    assert o['label_status'] != 'NOT_EXECUTED'


def test_lab_fill_at_limit_executed_path(tmp_path):
    """FILL_AT_LIMIT in a full run: the executed entry fills at the limit on
    the bar whose range trades through it; the entry bar's dip below the
    would-be stop does NOT stop the position (fill-only inspection)."""
    rows = _managed_tape()
    # Bar 3 (entry bar for the bar-1 birth) dips to 101.0 — below the would-be
    # stop 101.5 — to prove the entry bar is inspected for a FILL only.
    rows[3] = rows[3].__class__(
        source='binance-um', channel='kline', instrument='SOLUSDT',
        event_time=HOUR_NS * 3, available_time=HOUR_NS * 3,
        ingested_time=HOUR_NS * 3, venue_sequence=4, event_id='SOLUSDT:4',
        payload={'open': 103.0, 'high': 103.5, 'low': 101.0, 'close': 103.0,
                 'volume': 1.0, 'closed': True})
    lab = Lab(tmp_path)
    lab.ingest(rows)
    ex = _ManagedExpert(limit_price=102.5, target_r=2.0, stop_r=1.0)
    r = lab.run(_manifest(fill_policy='FILL_AT_LIMIT'), [ex])
    assert r.candidate_count == 1
    outs = lab.outcomes.read()
    assert len(outs) == 1
    o = outs[0]
    assert o['endpoint'] == 'TARGET'                # not STOP despite bar-3 dip
    assert o['entry_price'] == pytest.approx(102.5)
    assert o['label_status'] == 'MATURE'


def test_lab_fill_at_limit_never_filling_is_never_entered(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(_managed_tape())
    ex = _ManagedExpert(limit_price=90.0, target_r=2.0, stop_r=1.0)
    r = lab.run(_manifest(fill_policy='FILL_AT_LIMIT'), [ex])
    outs = lab.outcomes.read()
    assert len(outs) == 1
    assert outs[0]['endpoint'] == 'INVALIDATED_BEFORE_TRIGGER'
    assert outs[0]['label_status'] == 'NOT_EXECUTED'
    assert r.n_executed == 0
