"""RISK-1..6 tests: size primitive + fixed-fractional sizing (RM-01/02/09/15/16),
equity-curve drawdown controls (RM-06, O-016), trade-unit budget + risk-of-ruin
(RM-07), heat/cluster/conservation + risk-freeing hooks (RM-04/05/12),
min-trades + profit factor (RM-08/17/18), and WCS + spread-adjusted R/r
(RM-10/11).

Every threshold tested here is a DECLARED numeric literal frozen in the modules
(pre-holdout, O-017 method) — none is fitted to any data window. The drawdown
ladder is pure sizing: size*stop_r is invariant, so no admission decision and
no outcome net_r ever changes under it (O-018 caps stay 3.0/2.0).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from v8.equity import (DRAWDOWN_BANDS, RISK_OF_RUIN_N_SIMS, RISK_OF_RUIN_SEED,
                       RiskState, trade_units_for)
from v8.risk import RiskGate
from v8.schema import CandidateDraft, ExperimentManifest
from v8.lab import PROFIT_FACTOR_BAND, Lab
from v8.synth import make_synthetic_tape
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert

UNIVERSE = ('SOLUSDT',)
_PILOTS = [TrendPullbackExpert(), FailedBreakoutExpert()]


def _draft(**kw) -> CandidateDraft:
    base = dict(expert_id='t', expert_version='v1', instrument='SOLUSDT',
                direction='LONG', setup_fingerprint='f',
                risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                               'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 1.0},
                birth_time=0)
    base.update(kw)
    return CandidateDraft(**base)


def _manifest(**kw) -> ExperimentManifest:
    base = dict(experiment_id='exp-risk', code_hash='', data_hash='',
                universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    return ExperimentManifest(**base)


def _run_lab(tmp_path, **manifest_kw):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    return lab, lab.run(_manifest(**manifest_kw), _PILOTS)


def _executed_net_rs(lab: Lab) -> list[float]:
    return [float(o['net_r']) for o in lab.outcomes.read()
            if o['label_status'] != 'NOT_EXECUTED']


# --- RISK-1: size primitive + heat = size * stop_r -------------------------

def test_candidate_draft_size_defaults_to_one():
    assert _draft().size == 1.0
    assert _draft(size=2.0).size == 2.0


def test_heat_is_size_times_stop_r():
    gate = RiskGate(max_heat=5.0, max_cluster_heat=10.0)
    # Two size-2 positions (heat 2 each) fit under the 5.0 total cap; a third
    # (heat 6 > 5) is rejected on total heat.
    assert gate.admit(_draft(instrument='SOLUSDT', size=2.0)).ok
    assert gate.admit(_draft(instrument='ETHUSDT', direction='SHORT',
                             size=2.0)).ok
    v = gate.admit(_draft(instrument='XRPUSDT', size=2.0))
    assert not v.ok
    assert v.reason_code == 'PORTFOLIO_HEAT_EXCEEDED'
    assert v.detail == 'total'


def test_cluster_heat_counts_size_times_stop_r():
    gate = RiskGate(max_heat=10.0, max_cluster_heat=2.0)
    # SOLUSDT and BNBUSDT are both 'major': two size-1 positions fill 2.0.
    assert gate.admit(_draft(instrument='SOLUSDT')).ok
    assert gate.admit(_draft(instrument='BNBUSDT', direction='SHORT')).ok
    v = gate.admit(_draft(instrument='XRPUSDT'))
    assert not v.ok
    assert v.detail == 'cluster:major'


def test_heat_byte_identical_at_size_one():
    """At size=1.0, stop_r=1.0 the heat formula is the pre-size 1R gate
    (heat = number of open positions): three fit the 3.0 cap, the fourth is
    rejected on total heat."""
    gate = RiskGate(max_heat=3.0, max_cluster_heat=3.0)
    assert gate.admit(_draft(instrument='SOLUSDT')).ok
    assert gate.admit(_draft(instrument='ETHUSDT', direction='SHORT')).ok
    assert gate.admit(_draft(instrument='XRPUSDT')).ok
    v = gate.admit(_draft(instrument='FOOUSDT', direction='SHORT'))
    assert not v.ok
    assert v.reason_code == 'PORTFOLIO_HEAT_EXCEEDED'


# --- RISK-2: equity-curve drawdown controls (O-016, RM-06) -----------------

def test_drawdown_bands_are_frozen_declared_literals():
    assert DRAWDOWN_BANDS == ((-0.30, 0.5, 2.0), (-0.50, 0.25, 4.0))


def test_risk_state_equity_is_additive():
    st = RiskState(risk_per_trade=0.01)
    st.on_episode_closed(2.0)                  # +2R at full size -> +2%
    assert st.final_equity() == pytest.approx(1.02)
    st.on_episode_closed(-1.0)
    assert st.final_equity() == pytest.approx(1.01)
    # Drawdown is peak-relative: equity 1.01 vs peak 1.02.
    assert st.max_drawdown() == pytest.approx(1.01 / 1.02 - 1)


def test_drawdown_multipliers_fire_at_bands():
    st = RiskState(risk_per_trade=0.01)
    assert st.size_multiplier() == 1.0
    assert st.stop_multiplier() == 1.0
    for _ in range(40):                        # equity 1.0 -> 0.60 (-40%)
        st.on_episode_closed(-1.0)
    assert st.final_equity() == pytest.approx(0.60)
    assert st.size_multiplier() == 0.5         # below -30%: halve size
    assert st.stop_multiplier() == 2.0         #          double stop
    for _ in range(20):                        # equity 0.60 -> 0.40 (-60%)
        st.on_episode_closed(-1.0)
    assert st.size_multiplier() == 0.25        # below -50%: quarter size
    assert st.stop_multiplier() == 4.0         #          quadruple stop
    # Recovery above the bands restores full sizing (peak-relative).
    for _ in range(35):
        st.on_episode_closed(1.0)
    assert st.final_equity() == pytest.approx(0.75)
    assert st.size_multiplier() == 1.0
    assert st.stop_multiplier() == 1.0


def test_gate_scales_size_and_stop_from_equity_drawdown():
    st = RiskState(risk_per_trade=0.01)
    for _ in range(40):
        st.on_episode_closed(-1.0)             # -40% drawdown
    gate = RiskGate(max_heat=3.0, max_cluster_heat=3.0, equity=st)
    v = gate.admit(_draft(size=1.0))
    assert v.ok
    assert v.size == pytest.approx(0.5)        # f(dd) = 1/2
    assert v.stop_r == pytest.approx(2.0)      # g(dd) = 2


def test_drawdown_scaling_never_changes_admission():
    """size*stop_r is invariant under the ladder, so a gate with a drawn-down
    equity admits/rejects EXACTLY like a plain gate (O-018 caps untouched)."""
    st = RiskState(risk_per_trade=0.01)
    for _ in range(40):
        st.on_episode_closed(-1.0)
    scaled = RiskGate(max_heat=3.0, max_cluster_heat=3.0, equity=st)
    plain = RiskGate(max_heat=3.0, max_cluster_heat=3.0)
    for kw in (dict(instrument='SOLUSDT', size=2.0),
               dict(instrument='ETHUSDT', direction='SHORT', size=2.0),
               dict(instrument='XRPUSDT', size=2.0)):
        vs = scaled.admit(_draft(**kw))
        vp = plain.admit(_draft(**kw))
        assert vs.ok == vp.ok
        assert vs.reason_code == vp.reason_code


# --- RISK-3: trade-unit budget + risk-of-ruin (RM-07) ----------------------

def test_trade_units_budget():
    assert trade_units_for(0.01) == pytest.approx(100.0)   # 1% risk -> 100
    assert trade_units_for(0.20) == pytest.approx(5.0)     # 20% risk -> 5
    with pytest.raises(ValueError):
        trade_units_for(0.0)
    with pytest.raises(ValueError):
        trade_units_for(1.5)


def test_risk_of_ruin_is_seed_explicit_and_deterministic():
    st = RiskState(risk_per_trade=0.01)
    for _ in range(8):
        st.on_episode_closed(-2.0)
    for _ in range(4):
        st.on_episode_closed(1.0)
    r1 = st.risk_of_ruin()
    r2 = st.risk_of_ruin()
    assert r1 == r2                                   # fixed seed -> fixed result
    assert 0.0 <= r1 <= 1.0
    assert st.risk_of_ruin(seed=RISK_OF_RUIN_SEED) == r1
    # Report-only: None with no realized episodes (never a decision input).
    assert RiskState(0.01).risk_of_ruin() is None
    # Explicit constants, not hidden defaults.
    assert RISK_OF_RUIN_N_SIMS == 10_000 and RISK_OF_RUIN_SEED == 7


def test_risk_of_ruin_budget_arithmetic():
    st = RiskState(risk_per_trade=0.05)               # 20 trade units
    st.on_episode_closed(-30.0)                       # one -30R episode
    assert st.risk_of_ruin() == pytest.approx(1.0)    # certain ruin
    st2 = RiskState(risk_per_trade=0.05)
    st2.on_episode_closed(30.0)                       # wins never ruin
    assert st2.risk_of_ruin() == pytest.approx(0.0)


def test_report_carries_equity_and_trade_unit_diagnostics(tmp_path):
    lab, r = _run_lab(tmp_path)
    assert r.trade_units == pytest.approx(100.0)      # risk_per_trade 0.01
    assert r.risk_per_trade == pytest.approx(0.01)
    assert r.final_equity is not None
    assert r.max_drawdown is not None and r.max_drawdown <= 0.0
    assert r.risk_of_ruin is not None
    assert 0.0 <= r.risk_of_ruin <= 1.0
    # The realized sequence was too short to exhaust 100 units.
    assert r.risk_of_ruin == pytest.approx(0.0)


# --- RISK-4: heat/cluster/conservation + risk-freeing hook (RM-04/05/12) ---

def test_caps_remain_three_and_two():
    gate = RiskGate()
    assert gate.max_heat == 3.0
    assert gate.max_cluster_heat == 2.0


def test_risk_free_hook_frees_capital_heat():
    gate = RiskGate(max_heat=10.0, max_cluster_heat=2.0)
    assert gate.admit(_draft(instrument='SOLUSDT')).ok        # major
    assert gate.admit(_draft(instrument='BNBUSDT', direction='SHORT')).ok
    # Cluster heat 2.0 == cap: a third major-cluster position is rejected.
    assert not gate.admit(_draft(instrument='XRPUSDT')).ok
    # Risk-free one position: capital 2 -> 1, opportunity 0 -> 1 (RM-04).
    gate.risk_free('SOLUSDT', 'LONG')
    assert gate.opportunity_heat() == pytest.approx(1.0)
    assert gate.admit(_draft(instrument='XRPUSDT')).ok
    # Release everything: both pools return to zero (release tracks the pool).
    gate.release(_draft(instrument='XRPUSDT'))
    gate.release(_draft(instrument='SOLUSDT'))
    gate.release(_draft(instrument='BNBUSDT', direction='SHORT'))
    assert gate.opportunity_heat() == pytest.approx(0.0)


# --- RISK-5: min-trades + profit factor (RM-08/17/18) ----------------------

def test_min_trades_manifest_default():
    assert _manifest().min_trades == 300


def test_min_trades_annotation_is_a_note_not_a_hard_fail(tmp_path):
    lab, r = _run_lab(tmp_path)
    assert r.n_executed < r.min_trades
    assert r.economic_note is not None
    assert 'min_trades' in r.economic_note
    assert 'RM-07' in r.economic_note           # trade-unit note too
    # With a receipt the D-027 verdict still governs — the annotation is a
    # note, not a hard fail: the verdict equals exactly what the D-027 gates
    # decide and is never forced to NO_ECONOMIC_CLAIM by the note.
    from v8.lab import _d027_verdict
    lab2, r2 = _run_lab(tmp_path / 'receipt', authority_receipt='receipt-1')
    assert r2.economic_note is not None
    assert r2.verdict == _d027_verdict('receipt-1', r2.execution_share,
                                       r2.divergence_ks)
    assert r2.verdict != 'NO_ECONOMIC_CLAIM'


def test_profit_factor_reported(tmp_path):
    assert PROFIT_FACTOR_BAND == (1.5, 2.0)     # the book's external benchmark
    lab, r = _run_lab(tmp_path)
    net_rs = _executed_net_rs(lab)
    if net_rs:
        wins = sum(x for x in net_rs if x > 0.0)
        losses = sum(x for x in net_rs if x < 0.0)
        if losses < 0.0:
            assert r.profit_factor == pytest.approx(wins / -losses)


# --- RISK-6: WCS + spread-adjusted R/r (RM-10/11) --------------------------

def test_worst_case_and_wmin_reported(tmp_path):
    lab, r = _run_lab(tmp_path)
    net_rs = _executed_net_rs(lab)
    assert net_rs
    assert r.worst_case_r == pytest.approx(min(net_rs))     # realized WCS
    assert r.worst_case_portfolio_r == pytest.approx(-3.0)  # -max_heat, all stops
    # Spread-adjusted breakeven win rate (RM-11): w_min = 1/(1 + R/r') with
    # R/r' = (target_r - cost)/(stop_r + cost); geometry 1.0/1.0, cost 0.07.
    cost = 0.07
    expected_w = 1.0 / (1.0 + (1.0 - cost) / (1.0 + cost))
    assert r.w_min == pytest.approx(expected_w)


# --- hash binding + wiring invariants --------------------------------------

def test_open_position_size_and_sim_hash_version():
    from v8.schema import sha1_hex
    from v8.simulator import (CanonicalSimulator, OpenPosition,
                              _SIMULATOR_SRC_HASH)
    pos = OpenPosition(candidate_id='c', draft=_draft(), entry_price=100.0,
                       entry_bar_index=0, size=2.0)
    assert pos.size == 2.0
    # CRIT-3: the size field re-versions sim.hash() REGARDLESS of output
    # byte-identity; EXEC-1..6 land as canonical-sim-v8 (the tag moved on
    # every semantic change since).
    assert CanonicalSimulator().hash() == sha1_hex(
        ('canonical-sim-v8', 'FILL_AT_BAR_CLOSE', 0.07, 0.0, 8,
         _SIMULATOR_SRC_HASH))


def test_equity_config_bound_into_risk_gate_hash(tmp_path):
    lab_a, a = _run_lab(tmp_path)
    lab_b, b = _run_lab(tmp_path / 'b', risk_per_trade=0.05)
    assert a.risk_gate_hash != b.risk_gate_hash
    assert a.ledger_hash != b.ledger_hash       # different sizing policy


def test_drawdown_sizing_never_changes_ledger_outcomes(tmp_path):
    """The O-016 ladder is pure sizing: two runs with different risk_per_trade
    (hence different drawdown paths and effective sizes) admit the SAME
    candidates and produce element-wise identical outcome net_r — the only
    differences are the equity/report diagnostics and the bound risk-config."""
    lab_a, a = _run_lab(tmp_path)
    lab_b, b = _run_lab(tmp_path / 'b', risk_per_trade=0.05)
    assert a.candidate_count == b.candidate_count
    assert a.terminal_distribution == b.terminal_distribution
    net_a = sorted(_executed_net_rs(lab_a))
    net_b = sorted(_executed_net_rs(lab_b))
    assert net_a == pytest.approx(net_b)


def test_risk_diagnostics_deterministic(tmp_path):
    lab_a, a = _run_lab(tmp_path)
    lab_b, b = _run_lab(tmp_path / 'run2')
    for attr in ('trade_units', 'final_equity', 'max_drawdown',
                 'drawdown_sized_episodes', 'risk_of_ruin', 'profit_factor',
                 'w_min', 'worst_case_r', 'economic_note'):
        assert getattr(a, attr) == getattr(b, attr), attr
