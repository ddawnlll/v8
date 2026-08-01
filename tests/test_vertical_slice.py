"""Vertical-slice tests: prove the contracts run end-to-end, deterministically."""
from __future__ import annotations

from dataclasses import replace

import pytest

from v8.schema import ExperimentManifest, TapeRow, FeatureValue, FEATURE_GROUPS
from v8.store import AppendOnlyLog
from v8.marketstate import build_state, FutureRowError, validate_feature_groups
from v8.lifecycle import CandidateRegistry, episode_key, IllegalTransitionError, ExposureBook
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.schema import CandidateDraft
from v8.simulator import CanonicalSimulator, OpenPosition, risk_unit
from v8.synth import make_synthetic_tape, HOUR_NS
from v8.lab import Lab
from v8.risk import tradability_mask_veto

UNIVERSE = ('SOLUSDT',)


def _manifest(**kw) -> ExperimentManifest:
    base = dict(experiment_id='exp-vertical-slice', code_hash='', data_hash='',
                universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    return ExperimentManifest(**base)


def _fresh_lab(tmp_path, seed=7, n_bars=140) -> Lab:
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=seed, n_bars=n_bars))
    return lab


def test_future_row_rejected():
    rows = make_synthetic_tape(seed=1, n_bars=3)
    with pytest.raises(FutureRowError):
        build_state(rows, rows[0].available_time, UNIVERSE)


def test_open_kline_excluded_from_features():
    rows = make_synthetic_tape(seed=2, n_bars=25)
    as_of = rows[-1].available_time
    st = build_state(rows, as_of, UNIVERSE)
    before = st.features['SOLUSDT.close'].value
    open_row = TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                       event_time=as_of + 1, available_time=as_of,
                       ingested_time=as_of, venue_sequence=9999,
                       event_id='SOLUSDT:OPEN', payload={'close': 999999.0, 'closed': False})
    st2 = build_state(rows + [open_row], as_of, UNIVERSE)
    assert st2.features['SOLUSDT.close'].value == before


def test_illegal_transition_fails(tmp_path):
    reg = CandidateRegistry(AppendOnlyLog(tmp_path / 'c.jsonl'))
    with pytest.raises(IllegalTransitionError):
        reg.apply('c1', 'PENDING', 'EXECUTED', 'x', 1)
    reg.apply('c2', None, 'DETECTED', 'setup_detected', 1)
    with pytest.raises(IllegalTransitionError):
        reg.apply('c2', 'DETECTED', 'EXECUTED', 'x', 1)


def test_episode_key_deterministic_and_dedup_window(tmp_path):
    """D-026 anchor form: same setup anchor -> same key (determinism); a
    distinct anchor, direction, or geometry -> a distinct key; a repeat is a
    duplicate regardless of time (the window parameter is removed — anchor
    equality subsumes it, CANDIDATE_LIFECYCLE_SPEC 1)."""
    key = episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'anchor-1', 'geo-v1')
    assert key == episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'anchor-1', 'geo-v1')
    assert key != episode_key('e', 'v1', 'SOLUSDT', 'SHORT', 'anchor-1', 'geo-v1')
    assert key != episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'anchor-2', 'geo-v1')
    assert key != episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'anchor-1', 'geo-v2')
    reg = CandidateRegistry(AppendOnlyLog(tmp_path / 'c.jsonl'))
    reg.apply(key, None, 'DETECTED', 'setup_detected', 1_000)
    assert reg.is_duplicate(key) is True            # repeat is a duplicate
    # The registry has no time concept: is_duplicate is pure key membership,
    # so a repeat is a duplicate at ANY later clock — the time-window
    # parameter was removed because anchor equality subsumes it (D-026).
    assert reg.is_duplicate(key) is True
    fresh = episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'anchor-2', 'geo-v1')
    assert reg.is_duplicate(fresh) is False


def test_vertical_slice_runs_deterministically(tmp_path):
    lab = _fresh_lab(tmp_path, seed=7, n_bars=160)
    m = _manifest()
    r1 = lab.run(m, [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r1.candidate_count > 0
    assert r1.verdict == 'NO_ECONOMIC_CLAIM'
    # Stepped runtime: positions live across bars, so same-direction overlap
    # is now real and the exposure guard fires naturally.
    assert r1.exposure_conflicts > 0
    # No dangling candidates: every born candidate reaches a terminal state.
    assert sum(r1.terminal_distribution.values()) == r1.candidate_count
    # Rejected candidates keep a NOT_EXECUTED counterfactual outcome.
    assert any(rec.get('label_status') == 'NOT_EXECUTED' for rec in lab.outcomes.read())
    # Every candidate has exactly one outcome record.
    outcomes = [rec['candidate_id'] for rec in lab.outcomes.read()]
    assert len(outcomes) == len(set(outcomes)) == r1.candidate_count
    assert set(r1.terminal_distribution) <= {'CLOSED', 'EXPIRED', 'INVALIDATED', 'REJECTED'}
    # Determinism: an identical run from scratch reproduces every hash.
    lab2 = _fresh_lab(tmp_path / 'run2', seed=7, n_bars=160)
    r2 = lab2.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r2.ledger_hash == r1.ledger_hash
    assert r2.data_hash == r1.data_hash
    assert r2.candidate_count == r1.candidate_count
    assert r2.terminal_distribution == r1.terminal_distribution


def test_exposure_book_one_per_instrument_direction():
    book = ExposureBook()
    assert book.acquire('SOLUSDT', 'LONG') is True
    assert book.acquire('SOLUSDT', 'LONG') is False      # same exposure -> conflict
    assert book.acquire('SOLUSDT', 'SHORT') is True      # opposite direction ok
    assert book.acquire('ETHUSDT', 'LONG') is True       # other instrument ok
    book.release('SOLUSDT', 'LONG')
    assert book.acquire('SOLUSDT', 'LONG') is True


def test_duplicate_keys_never_double_apply(tmp_path):
    lab = _fresh_lab(tmp_path, seed=7, n_bars=160)
    lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    seen: set[tuple[str, str]] = set()
    for rec in lab.candidates.read():
        if 'from_state' in rec:
            key = (rec['candidate_id'], rec['sequence'])
            assert key not in seen, f'duplicate transition {key}'
            seen.add(key)


# --- D-026: setup-anchored episode identity --------------------------------
# Key stability (CANDIDATE_LIFECYCLE_SPEC 5): one unchanged setup on two
# consecutive decision clocks yields the same episode_key; a fresh setup (new
# anchor event) yields a different one; a repeat is SUPPRESSED_DUPLICATE.

def _craft_pullback_tape() -> list[TapeRow]:
    """Deterministic tape engineered for consecutive trend-pullback setups:
    40 flat bars (EMAs converge to 100), 20 bars of +1/bar uptrend (101..120),
    a shallow dip (108, 107) that keeps close < ema_slow while ema_fast >
    ema_slow on consecutive bars (run A), a recovery that ends the run, then a
    second dip (113, 112, 111) that starts a *new* run with a new anchor.
    Numbers verified against build_state's EMA: ema_fast falls below ema_slow
    at bar 62 (close 106) and the recovery keeps close above ema_slow."""
    closes = [100.0] * 40
    closes += [100.0 + (i + 1) for i in range(20)]     # 101..120
    closes += [108.0, 107.0]                           # pullback run A
    closes += [106.0, 115.0, 120.0, 124.0, 126.0]      # exit + recovery
    closes += [113.0, 112.0, 111.0]                    # pullback run B
    rows: list[TapeRow] = []
    for i, c in enumerate(closes):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c * 1.002, 'low': c * 0.998,
                     'close': c, 'volume': 1.0, 'closed': True}))
    return rows


def _draft_at(rows: list[TapeRow], expert, bar_idx: int) -> CandidateDraft:
    as_of = rows[bar_idx].available_time
    st = build_state([r for r in rows if r.available_time <= as_of],
                     as_of, UNIVERSE)
    ev = expert.evaluate(st)
    assert ev.draft is not None, f'no draft at bar {bar_idx}'
    return ev.draft


def test_episode_key_stable_across_consecutive_decision_clocks():
    """The same setup observed on two consecutive decision clocks hashes to
    the same key: the anchor (run start) is unchanged, so dedup can fire."""
    ex = TrendPullbackExpert()
    rows = _craft_pullback_tape()
    d60, d61 = _draft_at(rows, ex, 60), _draft_at(rows, ex, 61)
    assert d60.setup_anchor_event_id == d61.setup_anchor_event_id
    assert d60.setup_anchor_event_id == 'SOLUSDT:61'
    keys = {episode_key(ex.expert_id, ex.version, d.instrument, d.direction,
                        d.setup_anchor_event_id, _geo(d)) for d in (d60, d61)}
    assert len(keys) == 1


def _geo(draft: CandidateDraft) -> str:
    structural = {k: v for k, v in draft.risk_geometry.items() if k != 'atr_ref'}
    from v8.schema import sha1_hex
    return sha1_hex(structural)


def test_fresh_setup_gets_new_anchor_and_key():
    """A new setup (a new anchor event) is a different episode: a distinct
    episode_key, so it is not suppressed by the earlier run."""
    ex = TrendPullbackExpert()
    rows = _craft_pullback_tape()
    run_a = _draft_at(rows, ex, 61)          # inside pullback run A
    run_b = _draft_at(rows, ex, 68)          # inside pullback run B
    assert run_a.setup_anchor_event_id == 'SOLUSDT:61'
    assert run_b.setup_anchor_event_id == 'SOLUSDT:68'
    assert run_a.setup_anchor_event_id != run_b.setup_anchor_event_id
    ka = episode_key(ex.expert_id, ex.version, run_a.instrument, run_a.direction,
                     run_a.setup_anchor_event_id, _geo(run_a))
    kb = episode_key(ex.expert_id, ex.version, run_b.instrument, run_b.direction,
                     run_b.setup_anchor_event_id, _geo(run_b))
    assert ka != kb


def test_repeat_is_suppressed_duplicate_not_dropped(tmp_path):
    """A repeat of an already-detected setup inside the window is logged
    SUPPRESSED_DUPLICATE and never becomes a second candidate."""
    lab = Lab(tmp_path)
    lab.ingest(_craft_pullback_tape())
    lab.run(_manifest(), [TrendPullbackExpert()])
    suppressed = [rec for rec in lab.candidates.read()
                  if rec.get('kind') == 'suppressed_duplicate']
    assert suppressed, 'the consecutive setup must produce a suppressed repeat'
    detected = {rec['candidate_id'] for rec in lab.candidates.read()
                if rec.get('to_state') == 'DETECTED'}
    assert all(s['candidate_id'] in detected for s in suppressed)
    # Every DETECTED key appears at most once as a real candidate.
    detected_seqs = [rec['sequence'] for rec in lab.candidates.read()
                     if rec.get('to_state') == 'DETECTED']
    assert detected_seqs == [1] * len(detected_seqs)


# --- R-unit semantics, excursions, ambiguity, thesis exit -------------------
# Regression guards for the defect where `net_r` was a fractional price return
# while every consumer (geometry, RiskGate heat, spec) treated it as R.

def _pos(direction='LONG', entry=100.0, atr=2.0, target_r=2.0, stop_r=1.0,
         expiry=10):
    draft = CandidateDraft(
        expert_id='t', expert_version='v1', instrument='SOLUSDT',
        direction=direction, setup_fingerprint='fp',
        risk_geometry={'target_r': target_r, 'stop_r': stop_r,
                       'expiry_bars': expiry, 'atr_ref': atr},
        birth_time=0)
    return OpenPosition(candidate_id='c1', draft=draft, entry_price=entry,
                        entry_bar_index=0)


def test_stop_out_is_exactly_minus_one_r():
    """A stop-out must be -1R minus cost, whatever the instrument or stop width."""
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    # entry 100, atr 2.0 -> 1R = 2.0 price; stop at 98.0
    res = sim.step(_pos(), {'open': 99.5, 'high': 99.6, 'low': 97.9, 'close': 98.0})
    assert res.endpoint == 'STOP'
    assert res.net_r == pytest.approx(-1.0 - 0.07, abs=1e-12)


def test_target_hit_is_exactly_target_r():
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    # target_r 2.0 with 1R = 2.0 price -> target at 104.0
    res = sim.step(_pos(), {'open': 101.0, 'high': 104.5, 'low': 100.5, 'close': 104.2})
    assert res.endpoint == 'TARGET'
    assert res.net_r == pytest.approx(2.0 - 0.07, abs=1e-12)


def test_net_r_is_risk_normalised_not_price_normalised():
    """Two positions with the same R geometry but 10x different risk width
    must produce the same net_r; that is what makes heat (D-023) meaningful."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    tight = sim.step(_pos(atr=1.0), {'open': 100.0, 'high': 102.5, 'low': 100.0,
                                     'close': 102.0})
    wide = sim.step(_pos(atr=10.0), {'open': 100.0, 'high': 125.0, 'low': 100.0,
                                     'close': 124.0})
    assert tight.endpoint == wide.endpoint == 'TARGET'
    assert tight.net_r == pytest.approx(wide.net_r, abs=1e-12) == pytest.approx(2.0)


def test_excursions_recorded_in_r():
    """MAE/MFE are the only quantity V7 measured as materially predictable."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    # 1R = 2.0; bar ranges 97.0..103.0 without touching stop(98)? it does touch.
    res = sim.step(_pos(stop_r=3.0, target_r=5.0),
                   {'open': 100.0, 'high': 103.0, 'low': 97.0, 'close': 101.0})
    assert not res.closed                      # stop is 94.0, target 110.0
    assert res.next_pos.mfe_r == pytest.approx(1.5)   # (103-100)/2
    assert res.next_pos.mae_r == pytest.approx(1.5)   # (100-97)/2


def test_ambiguous_bar_counted_and_stop_wins():
    """SIMULATION_TRUTH_SPEC: record ambiguity AND apply STOP_FIRST."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    res = sim.step(_pos(), {'open': 100.0, 'high': 105.0, 'low': 97.0, 'close': 99.0})
    assert res.endpoint == 'STOP'              # conservative
    assert res.next_pos.ambiguous_bars == 1    # and it is no longer silent


def test_risk_unit_fails_closed_on_nonpositive():
    draft = _pos(atr=0.0).draft
    with pytest.raises(ValueError):
        risk_unit(draft, entry_price=0.0)


def test_thesis_invalidation_is_a_distinct_exit():
    """A dead thesis closes the position even while the stop is far away."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    quiet = {'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0}
    assert not sim.step(_pos(), quiet, thesis_valid=True).closed
    dead = sim.step(_pos(), quiet, thesis_valid=False)
    assert dead.endpoint == 'THESIS_INVALIDATED'
    assert dead.label_status == 'MATURE'       # a fact, not a censored label


# --- Funding settlement (SIMULATION_TRUTH_SPEC 3-5, SETTLEMENT_BEFORE_ORDERS) -
# Boundaries are integer-hour UTC divisible by funding_hours (default 8 ->
# 00/08/16 UTC). Open at the start boundary, closed at the end: a hold starting
# exactly on a boundary is not double-settled; a hold ending exactly on one is
# never missed (the V7 terminal-boundary defect).

QUIET_BAR = {'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0}


def _fund_pos(cid='c1', entry_time=2 * HOUR_NS, **kw) -> OpenPosition:
    return OpenPosition(candidate_id=cid, draft=_pos(**kw).draft,
                        entry_price=100.0, entry_bar_index=0,
                        entry_time_ns=entry_time)


def _fund_step(sim, pos, hours):
    """Step `pos` over integer-hour decision clocks; returns (pos, settled)."""
    settled = []
    for h in hours:
        r = sim.step(pos, QUIET_BAR, bar_time=h * HOUR_NS)
        pos = r.next_pos or pos
        if r.funding_settled:
            settled.append(h)
    return pos, settled


def test_funding_spanning_one_boundary_books_one_settlement():
    """A hold spanning exactly one boundary books exactly one funding_settled
    and net_r is reduced by exactly funding_rate_r (LONG pays on a positive
    rate)."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0, funding_rate_r=0.01,
                             funding_hours=8)
    pos = _fund_pos(entry_time=2 * HOUR_NS, expiry=20)
    pos, settled = _fund_step(sim, pos, [3, 4, 5, 6, 7, 8])
    assert settled == [8]                       # booked on the crossing bar
    assert pos.settlements == 1
    assert pos.funding_paid_r == pytest.approx(0.01)
    # Next bar hits the target: net_r = target_r - cost - funding.
    r = sim.step(pos, {'open': 100.0, 'high': 104.5, 'low': 99.5, 'close': 104.0},
                 bar_time=9 * HOUR_NS)
    assert r.endpoint == 'TARGET'
    assert r.net_r == pytest.approx(2.0 - 0.01, abs=1e-12)


def test_funding_boundary_edges_settle_exactly_once():
    """A hold starting exactly on a boundary is not double-settled; a hold
    ending exactly on a boundary settles exactly once (V7 defect: missed
    terminal settlement)."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0, funding_rate_r=0.01,
                             funding_hours=8)
    # (i) starts exactly on boundary hour 8, held to hour 16: one settlement.
    pos = _fund_pos(entry_time=8 * HOUR_NS, expiry=20)
    pos, settled = _fund_step(sim, pos, [9, 10, 11, 12, 13, 14, 15, 16])
    assert settled == [16]                      # not [8, 16] — no double-settle
    assert pos.settlements == 1
    # (ii) ends exactly on boundary hour 16: the terminal settlement is booked.
    pos2 = _fund_pos(cid='c2', entry_time=10 * HOUR_NS, expiry=20)
    pos2, settled2 = _fund_step(sim, pos2, [11, 12, 13, 14, 15, 16])
    assert settled2 == [16]
    assert pos2.settlements == 1
    # SHORT receives on a positive rate: funding_paid_r is negative.
    sim_s = CanonicalSimulator(round_trip_cost_r=0.0, funding_rate_r=0.01,
                               funding_hours=8)
    pos3 = _fund_pos(cid='c3', entry_time=2 * HOUR_NS,
                     direction='SHORT', expiry=20)
    pos3, _ = _fund_step(sim_s, pos3, [3, 4, 5, 6, 7, 8])
    assert pos3.funding_paid_r == pytest.approx(-0.01)


def test_window_replay_matches_full_tape_for_shared_hold():
    """Full-tape and window replay of the same hold book identical settlements
    on the shared prefix; a window ending exactly on a boundary books it once
    (the junction settlement is neither missed nor double-counted)."""
    sim = CanonicalSimulator(round_trip_cost_r=0.0, funding_rate_r=0.001,
                             funding_hours=8)
    draft = _pos(expiry=99).draft
    entry = 2 * HOUR_NS

    def run_over(hours):
        pos = OpenPosition(candidate_id='c', draft=draft, entry_price=100.0,
                           entry_bar_index=0, entry_time_ns=entry)
        for h in hours:
            r = sim.step(pos, QUIET_BAR, bar_time=h * HOUR_NS)
            pos = r.next_pos or pos
        return pos

    full = run_over(list(range(3, 19)))      # crosses boundaries 8 and 16
    window = run_over(list(range(3, 10)))    # crosses boundary 8 only
    terminal = run_over(list(range(3, 9)))   # ends exactly on boundary 8
    assert full.settlements == 2
    assert window.settlements == 1
    assert terminal.settlements == 1             # terminal boundary booked once
    assert window.funding_paid_r == pytest.approx(0.001)
    assert full.funding_paid_r == pytest.approx(0.002)


def test_zero_funding_rate_leaves_numbers_identical(tmp_path):
    """funding_rate_r=0.0 keeps today's numbers byte-identical, and the
    simulator hash bumps to canonical-sim-v4 regardless (policy changed)."""
    lab = _fresh_lab(tmp_path, seed=7, n_bars=160)
    experts = [TrendPullbackExpert(), FailedBreakoutExpert()]
    r_default = lab.run(_manifest(), experts)
    lab2 = _fresh_lab(tmp_path / 'zero', seed=7, n_bars=160)
    r_zero = lab2.run(_manifest(funding_rate_r=0.0), experts)
    assert r_zero.ledger_hash == r_default.ledger_hash
    assert r_zero.data_hash == r_default.data_hash
    assert r_zero.candidate_count == r_default.candidate_count
    assert r_zero.terminal_distribution == r_default.terminal_distribution
    assert r_zero.verdict == r_default.verdict == 'NO_ECONOMIC_CLAIM'
    from v8.schema import sha1_hex as _sh
    from v8.simulator import _SIMULATOR_SRC_HASH
    # Hash-canary contract: the simulator hash binds the module source, so a
    # step()/run() semantics change moves every outcome's simulator_hash.
    assert CanonicalSimulator().hash() == _sh(
        ('canonical-sim-v4', 'FILL_AT_BAR_CLOSE', 0.07, 0.0, 8,
         _SIMULATOR_SRC_HASH))
    assert CanonicalSimulator().hash() != _sh(
        ('canonical-sim-v3', 'FILL_AT_BAR_CLOSE', 0.07))


def test_trend_expert_thesis_dies_when_trend_dies():
    """The thesis ('pullback inside an uptrend') dies when the uptrend dies:
    inside run A still_valid is True; after the recovery kills ema_fast >
    ema_slow it is False. Pinned against the crafted tape (not re-derived
    from the implementation's own formula)."""
    ex = TrendPullbackExpert()
    rows = _craft_pullback_tape()
    draft = _draft_at(rows, ex, 61)                    # inside pullback run A
    alive = build_state([r for r in rows if r.available_time <= rows[61].available_time],
                        rows[61].available_time, UNIVERSE)
    # Bar 62 (close 106) is where ema_fast falls below ema_slow (verified in
    # the crafted-tape comments): the uptrend is dead there, whatever the
    # later recovery bars do.
    dead = build_state([r for r in rows if r.available_time <= rows[62].available_time],
                       rows[62].available_time, UNIVERSE)
    assert ex.still_valid(alive, draft) is True
    assert ex.still_valid(dead, draft) is False


def _funding_cross_tape() -> list[TapeRow]:
    """A tape engineered so failed_breakout enters at bar 32 (32h, exactly on
    an 8h boundary — NOT mask-vetoed by the open-interval rule) and is held
    quietly to expiry at bar 40, whose decision clock crosses the 40h
    boundary. Bars 0-29 rise 100..129 (no setup); bar 30 drops to 100 (close
    < prior_high 129.5 -> setup, anchor 30); bars 31-45 are quiet at 100."""
    closes = [100.0 + i for i in range(30)]            # 100..129 rising
    closes += [100.0] * 16                              # drop + quiet hold
    rows: list[TapeRow] = []
    for i, c in enumerate(closes):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c + 0.5, 'low': c - 0.5,
                     'close': c, 'volume': 1.0, 'closed': True}))
    return rows


def test_funding_integration_through_lab_run(tmp_path):
    """Funding settlement actually reaches lab.run outcomes end-to-end: a SHORT
    held across the 40h boundary books exactly one settlement and its net_r is
    +0.01 higher (receives on a positive rate) than the zero-rate run
    (bugfix: this path was previously untested; only simulator goldens)."""
    rows = _funding_cross_tape()
    lab0 = Lab(tmp_path / 'f0')
    lab0.ingest(rows)
    r0 = lab0.run(_manifest(funding_rate_r=0.0), [FailedBreakoutExpert()])
    lab1 = Lab(tmp_path / 'f1')
    lab1.ingest(rows)
    r1 = lab1.run(_manifest(funding_rate_r=0.01), [FailedBreakoutExpert()])
    assert r0.candidate_count == r1.candidate_count == 1
    assert r0.ledger_hash != r1.ledger_hash           # funding changed the ledger
    outs0 = {o['candidate_id']: o for o in lab0.outcomes.read()}
    outs1 = {o['candidate_id']: o for o in lab1.outcomes.read()}
    differing = [cid for cid in outs0
                 if outs0[cid].get('net_r') != outs1[cid].get('net_r')]
    assert differing, 'the held SHORT must book funding across the 40h boundary'
    # One settlement at +0.01 (SHORT receives on a positive rate).
    for cid in differing:
        assert outs1[cid]['net_r'] - outs0[cid]['net_r'] == pytest.approx(0.01)


# --- D-024 mechanical tradability mask (CANDIDATE_LIFECYCLE_SPEC 6.3) -------
# Deterministic data-integrity vetoes at admission, applied before any risk
# admission: entry-bar spread beyond max_spread_frac, StateQuality == DEGRADED,
# entry bar closing within funding_window_bars of a funding boundary. A vetoed
# candidate is REJECTED with reason TRADABILITY_MASK_VETO and keeps a
# NOT_EXECUTED counterfactual outcome.
#
# Tape geometry: on the epoch-0 crafted tape (event_time = i*HOUR_NS) the run-A
# pullback is detected at bar 60 (anchor 'SOLUSDT:61') and enters at bar 62.
# Prepending k flat bars shifts every bar index by k without changing the
# predicate truth table (EMAs depend only on the close sequence), so the entry
# bar index moves to 62+k — used below to park the entry exactly 1h before a
# funding boundary (index ≡ 7 mod 8).

def _pullback_tape_with_offset(offset_bars: int = 0) -> list[TapeRow]:
    """_craft_pullback_tape with `offset_bars` leading flat bars; identical
    close sequence, so every run/EMA fact is simply index-shifted."""
    closes = [100.0] * (40 + offset_bars)
    closes += [100.0 + (i + 1) for i in range(20)]     # 101..120
    closes += [108.0, 107.0]                           # pullback run A
    closes += [106.0, 115.0, 120.0, 124.0, 126.0]      # exit + recovery
    closes += [113.0, 112.0, 111.0]                    # pullback run B
    rows: list[TapeRow] = []
    for i, c in enumerate(closes):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c * 1.002, 'low': c * 0.998,
                     'close': c, 'volume': 1.0, 'closed': True}))
    return rows


def _inflate_bar_high(rows: list[TapeRow], idx: int, mult: float = 1.10) -> list[TapeRow]:
    out = list(rows)
    p = dict(out[idx].payload)
    p['high'] = float(p['close']) * mult
    out[idx] = replace(out[idx], payload=p)
    return out


def test_mask_vetoes_spread_tail_bar(tmp_path):
    """Entry bar with (high-low)/close > max_spread_frac -> TRADABILITY_MASK_VETO
    (detail SPREAD), never executed, counterfactual NOT_EXECUTED preserved."""
    rows = _inflate_bar_high(_pullback_tape_with_offset(0), 62)   # entry bar
    lab = Lab(tmp_path)
    lab.ingest(rows)
    lab.run(_manifest(), [TrendPullbackExpert()])
    vetoed = [rec for rec in lab.candidates.read()
              if rec.get('to_state') == 'REJECTED'
              and rec.get('reason_code') == 'TRADABILITY_MASK_VETO']
    assert vetoed, 'a spread-tail entry must be mask-vetoed'
    cid = vetoed[0]['candidate_id']
    detail = [rec for rec in lab.candidates.read()
              if rec.get('kind') == 'tradability_veto' and rec['candidate_id'] == cid]
    assert detail and detail[0]['detail'] == 'SPREAD'
    outs = [rec for rec in lab.outcomes.read() if rec['candidate_id'] == cid]
    assert len(outs) == 1 and outs[0]['label_status'] == 'NOT_EXECUTED'


def test_mask_vetoes_in_funding_window(tmp_path):
    """Entry bar closing within funding_window_bars of a boundary -> veto
    (detail FUNDING_WINDOW). One leading flat bar shifts run A's entry (62) to
    bar 63 = 7 mod 8, i.e. exactly 1h before the 64h boundary."""
    rows = _pullback_tape_with_offset(1)
    entry = rows[63]
    period, window = 8 * HOUR_NS, 1 * HOUR_NS
    assert 0 < entry.event_time % period and entry.event_time % period >= period - window
    lab = Lab(tmp_path)
    lab.ingest(rows)
    lab.run(_manifest(), [TrendPullbackExpert()])
    vetoed = [rec for rec in lab.candidates.read()
              if rec.get('to_state') == 'REJECTED'
              and rec.get('reason_code') == 'TRADABILITY_MASK_VETO']
    assert vetoed, 'an entry 1h before a boundary must be mask-vetoed'
    cid = vetoed[0]['candidate_id']
    detail = [rec for rec in lab.candidates.read()
              if rec.get('kind') == 'tradability_veto' and rec['candidate_id'] == cid]
    assert detail and detail[0]['detail'] == 'FUNDING_WINDOW'
    outs = [rec for rec in lab.outcomes.read() if rec['candidate_id'] == cid]
    assert len(outs) == 1 and outs[0]['label_status'] == 'NOT_EXECUTED'


def test_mask_degraded_state_vetoes():
    """StateQuality == DEGRADED at decision time vetoes, whatever the bar."""
    ok_bar = {'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0}
    assert tradability_mask_veto(ok_bar, 'DEGRADED', 3 * HOUR_NS,
                                 max_spread_frac=0.05, funding_window_bars=1,
                                 funding_hours=8, interval_ns=HOUR_NS) == (True, 'DEGRADED')
    assert tradability_mask_veto(ok_bar, 'COMPLETE', 3 * HOUR_NS,
                                 max_spread_frac=0.05, funding_window_bars=1,
                                 funding_hours=8, interval_ns=HOUR_NS) == (False, None)
    # A bar ending EXACTLY on a boundary enters after that settlement
    # (open-interval start) and is NOT vetoed — the documented non-veto must
    # be pinned, not just the veto side.
    boundary = 8 * HOUR_NS
    assert tradability_mask_veto(ok_bar, 'COMPLETE', boundary,
                                 max_spread_frac=0.05, funding_window_bars=1,
                                 funding_hours=8, interval_ns=HOUR_NS) == (False, None)
    # One bar before the boundary is vetoed (imminent settlement).
    assert tradability_mask_veto(ok_bar, 'COMPLETE', boundary - HOUR_NS,
                                 max_spread_frac=0.05, funding_window_bars=1,
                                 funding_hours=8, interval_ns=HOUR_NS) == (True, 'FUNDING_WINDOW')


def test_mask_defaults_do_not_veto_spread_or_quality_on_baseline(tmp_path):
    """Thresholds at defaults never veto the synthetic baseline via spread or
    state quality (no SPREAD/DEGRADED vetoes on seed-7). Funding-window vetoes
    may still occur — with 1h bars some bar is always within 1h of an 8h
    boundary; that is a schedule property of the synthetic epoch, not a
    threshold overreach."""
    lab = _fresh_lab(tmp_path, seed=7, n_bars=160)
    r = lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r.candidate_count > 0
    details = [rec.get('detail') for rec in lab.candidates.read()
               if rec.get('kind') == 'tradability_veto']
    assert not any(d in ('SPREAD', 'DEGRADED') for d in details), details


# --- Phase 2: feature groups + lineage (MARKET_STATE_CONTRACT 2, 5) ---------
# Every emitted feature carries feature_version and a declared group tag; the
# lineage hash binds value + availability + group + version so a re-tag or
# re-version changes every dependent hash. PIT tests (synthetic tape; the
# Phase-1 tape is not present in this session): future rejection and
# bar-not-closed are covered above; revision replay is added here.

def test_feature_groups_declared_and_tagged():
    """Every emitted feature carries a declared group; the group table is
    consistent; two builds reproduce the identical state hash."""
    rows = make_synthetic_tape(seed=5, n_bars=40)
    as_of = rows[-1].available_time
    st = build_state(rows, as_of, UNIVERSE)
    groups = {v.group for v in st.features.values()}
    assert groups <= set(FEATURE_GROUPS), groups
    assert st.features['SOLUSDT.close'].group == 'raw'
    assert st.features['SOLUSDT.ema_fast'].group == 'trend'
    assert st.features['SOLUSDT.atr'].group == 'volatility'
    assert st.features['SOLUSDT.prior_high'].group == 'location'
    assert st.features['SOLUSDT.history'].group == 'history'
    assert all(v.feature_version for v in st.features.values())
    # Reproducibility: identical inputs -> identical state hash.
    st2 = build_state(rows, as_of, UNIVERSE)
    assert st2.state_id == st.state_id and st2.lineage_hash == st.lineage_hash


def test_lineage_hash_binds_feature_version():
    """Two states with identical values but different feature versions must
    hash differently: the lineage binds version, so a re-version invalidates
    every dependent hash instead of silently persisting."""
    rows = make_synthetic_tape(seed=5, n_bars=40)
    as_of = rows[-1].available_time
    v1 = build_state(rows, as_of, UNIVERSE, feature_version='v1')
    v2 = build_state(rows, as_of, UNIVERSE, feature_version='v2')
    assert v1.lineage_hash != v2.lineage_hash
    assert v1.state_id != v2.state_id
    assert [f.value for f in v1.features.values()] == [f.value for f in v2.features.values()]


def test_validate_feature_groups_fails_closed():
    """An undeclared group tag is a contract breach, not a silent state."""
    with pytest.raises(ValueError):
        validate_feature_groups({'SOLUSDT.close': FeatureValue(
            'SOLUSDT.close', 100.0, 'float', 'v1', 0, group='bogus')})


def test_revision_replay_reproduces_prior_state_hash():
    """A late revision available only after D must be excluded from an as-of
    rebuild at D (prior hash reproduced); a later rebuild may differ
    (MARKET_STATE_CONTRACT 6 revision replay)."""
    rows = make_synthetic_tape(seed=3, n_bars=30)
    D = rows[-1].available_time
    st1 = build_state([r for r in rows if r.available_time <= D], D, UNIVERSE)
    last = rows[-1]
    revised = TapeRow(source=last.source, channel=last.channel,
                      instrument=last.instrument, event_time=last.event_time,
                      available_time=D + 1, ingested_time=D + 1,
                      venue_sequence=last.venue_sequence, event_id=last.event_id,
                      payload=dict(last.payload, close=float(last.payload['close']) + 50.0))
    # As-of rebuild at D: the revision is not yet available -> same hash.
    st2 = build_state([r for r in rows + [revised] if r.available_time <= D],
                      D, UNIVERSE)
    assert st2.state_id == st1.state_id
    assert st2.lineage_hash == st1.lineage_hash
    # Rebuild at D' (revision available): the state must differ.
    D2 = revised.available_time
    st3 = build_state([r for r in rows + [revised] if r.available_time <= D2],
                      D2, UNIVERSE)
    assert st3.state_id != st1.state_id


# --- Session 2: decision ledger + birth snapshot (DATASET_SPEC 1;            ---
# CANDIDATE_LIFECYCLE_SPEC 1) — the inputs to the section-5 materializations.

def test_lab_persists_decision_ledger_states(tmp_path):
    """The decision ledger persists every MarketState built at a decision
    clock; two fresh runs reproduce identical state hashes."""
    lab = _fresh_lab(tmp_path, seed=7, n_bars=80)
    lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    states = lab.states.read()
    assert len(states) == 80                       # one state per bar
    assert all(s['source'] == 'marketstate' and s['event_id'] == s['state_id']
               for s in states)
    lab2 = _fresh_lab(tmp_path / 'run2', seed=7, n_bars=80)
    lab2.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert lab2.states.hash == lab.states.hash


def test_birth_snapshot_recorded_on_detected(tmp_path):
    """The DETECTED transition carries the immutable birth snapshot
    (CANDIDATE_LIFECYCLE_SPEC section 1): expert identity, setup evidence,
    geometry version and the birth state_id."""
    lab = _fresh_lab(tmp_path, seed=7, n_bars=160)
    lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    births = [r for r in lab.candidates.read() if r.get('to_state') == 'DETECTED']
    assert births
    for b in births:
        for key in ('expert_id', 'expert_version', 'instrument', 'direction',
                    'setup_anchor_event_id', 'geometry_version', 'state_id'):
            assert key in b, f'birth snapshot missing {key}'
        assert b['instrument'] in UNIVERSE
        assert b['setup_anchor_event_id']
        assert b['direction'] in ('LONG', 'SHORT')


# --- Session 3: fill_policy is a manifest input, enforced fail-closed --------
# OPERATIONS_SPEC section 1: shadow and paper share one code path; the fill
# source is a manifest input. A declared policy the stepper does not
# implement must fail closed — a hash claiming a fill semantics the code does
# not execute is a lie.

def test_unsupported_fill_policy_fails_closed(tmp_path):
    from v8.simulator import CanonicalSimulator, SUPPORTED_FILL_POLICIES
    with pytest.raises(ValueError, match='unsupported fill_policy'):
        CanonicalSimulator(fill_policy='FILL_AT_BAR_OPEN')
    lab = _fresh_lab(tmp_path, seed=7, n_bars=60)
    with pytest.raises(ValueError, match='unsupported fill_policy'):
        lab.run(_manifest(fill_policy='FILL_AT_BAR_OPEN'),
                [TrendPullbackExpert(), FailedBreakoutExpert()])
    # The implemented policy is exactly the locked baseline.
    assert SUPPORTED_FILL_POLICIES == ('FILL_AT_BAR_CLOSE',)
    assert CanonicalSimulator().fill_policy == 'FILL_AT_BAR_CLOSE'


def test_double_run_on_same_store_fails_closed(tmp_path):
    """One store = one immutable run: a second lab.run() on the same store
    must fail closed. It is not idempotent — the registry replays the prior
    run's DETECTED keys and would append NEW suppressed_duplicate rows,
    silently changing the ledger hash for identical inputs (bugfix)."""
    lab = _fresh_lab(tmp_path, seed=7, n_bars=160)
    experts = [TrendPullbackExpert(), FailedBreakoutExpert()]
    r1 = lab.run(_manifest(), experts)
    with pytest.raises(ValueError, match='already contains a run'):
        lab.run(_manifest(), experts)
    # The evidence is untouched by the refused run.
    assert r1.ledger_hash == _fresh_lab(tmp_path / 'fresh', seed=7, n_bars=160).run(
        _manifest(), experts).ledger_hash
