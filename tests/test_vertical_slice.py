"""Vertical-slice tests: prove the contracts run end-to-end, deterministically."""
from __future__ import annotations

import pytest

from v8.schema import ExperimentManifest, TapeRow
from v8.store import AppendOnlyLog
from v8.marketstate import build_state, FutureRowError
from v8.lifecycle import CandidateRegistry, episode_key, IllegalTransitionError, ExposureBook
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.schema import CandidateDraft
from v8.simulator import CanonicalSimulator, OpenPosition, risk_unit
from v8.synth import make_synthetic_tape
from v8.lab import Lab

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
    key = episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'fp', 1_000)
    assert key == episode_key('e', 'v1', 'SOLUSDT', 'LONG', 'fp', 1_000)
    assert key != episode_key('e', 'v1', 'SOLUSDT', 'SHORT', 'fp', 1_000)
    reg = CandidateRegistry(AppendOnlyLog(tmp_path / 'c.jsonl'))
    reg.apply(key, None, 'DETECTED', 'setup_detected', 1_000)
    assert reg.is_duplicate(key, 1_000 + 2 * 3_600_000_000_000) is True
    assert reg.is_duplicate(key, 1_000 + 20 * 3_600_000_000_000) is False


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


def test_trend_expert_thesis_dies_when_trend_dies(tmp_path):
    ex = TrendPullbackExpert()
    lab = _fresh_lab(tmp_path)
    tape = lab.tape_log.replay_tape()
    state = build_state(tape, tape[-1].available_time, UNIVERSE)
    draft = _pos().draft
    f = state.features
    if f'SOLUSDT.ema_fast' in f and f['SOLUSDT.ema_fast'].value is not None:
        expected = float(f['SOLUSDT.ema_fast'].value) > float(f['SOLUSDT.ema_slow'].value)
        assert ex.still_valid(state, draft) is expected
