"""Lifecycle additions for EXEC-2: the PositionAction append-only event.

PARTIAL_EXIT is a NON-TERMINAL lifecycle fact: it records a fraction of an
open (EXECUTED) position being closed while the position continues, without a
state transition. It is distinct from the terminal endpoint vocabulary
(TARGET/STOP/EXPIRY/THESIS_INVALIDATED/TIME_EXIT) and never produces an
outcome — one terminal CounterfactualOutcome per candidate, unchanged.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from v8.lifecycle import CandidateRegistry, IllegalTransitionError
from v8.store import AppendOnlyLog
from v8.schema import sha1_hex


def _registry(tmp_path) -> CandidateRegistry:
    return CandidateRegistry(AppendOnlyLog(Path(tmp_path) / 'candidates.jsonl'))


def _to_executed(reg: CandidateRegistry, cid: str = 'c1') -> None:
    reg.apply(cid, None, 'DETECTED', 'setup_detected', 0)
    reg.apply(cid, 'DETECTED', 'PENDING', 'hypothesis_completed', 0)
    reg.apply(cid, 'PENDING', 'TRIGGERED', 'trigger_observed', 0)
    reg.apply(cid, 'TRIGGERED', 'ACCEPTED', 'risk_accept', 0)
    reg.apply(cid, 'ACCEPTED', 'ORDER_SUBMITTED', 'submit_order', 0)
    reg.apply(cid, 'ORDER_SUBMITTED', 'EXECUTED', 'fill_observed', 0)


def test_position_action_is_append_only_non_transition(tmp_path):
    """A PARTIAL_EXIT does not move the candidate out of EXECUTED — the
    position continues; only the append-only record is written."""
    reg = _registry(tmp_path)
    _to_executed(reg)
    n_before = len(reg.log.read())
    rec = reg.position_action('c1', 'PARTIAL_EXIT', fraction=0.25,
                              price=103.0, knowledge_time=10)
    assert reg.current('c1') == 'EXECUTED'             # state unchanged
    assert rec['kind'] == 'position_action'
    assert rec['action'] == 'PARTIAL_EXIT'
    assert rec['fraction'] == 0.25
    assert rec['price'] == 103.0
    assert rec['knowledge_time'] == 10
    assert len(reg.log.read()) == n_before + 1         # append-only
    # The record joins the ledger hash (like suppressed_duplicate records).
    before = sha1_hex(reg.log.read()[:-1])
    assert sha1_hex(reg.log.read()) != before


def test_position_action_does_not_consume_transition_sequence(tmp_path):
    """PositionAction is not a CandidateTransition: the candidate's transition
    sequence is untouched, so a terminal close after a partial still appends
    at the same sequence the transition log expects."""
    reg = _registry(tmp_path)
    _to_executed(reg)
    reg.position_action('c1', 'PARTIAL_EXIT', fraction=0.5, price=102.0,
                        knowledge_time=5)
    reg.apply('c1', 'EXECUTED', 'CLOSED', 'position_flat', 6)
    assert reg.current('c1') == 'CLOSED'
    transitions = [r for r in reg.log.read() if 'to_state' in r]
    assert transitions[-1]['to_state'] == 'CLOSED'
    assert transitions[-1]['sequence'] == 7            # the next transition seq


def test_position_action_replay_is_stable(tmp_path):
    """A replayed registry sees the same append-only record (no state change
    on replay, and replay does not fail on the non-transition record)."""
    lab_dir = Path(tmp_path) / 'store'
    log = AppendOnlyLog(lab_dir / 'candidates.jsonl')
    reg = CandidateRegistry(log)
    _to_executed(reg)
    reg.position_action('c1', 'PARTIAL_EXIT', fraction=0.25, price=103.0,
                        knowledge_time=10)
    log2 = AppendOnlyLog(lab_dir / 'candidates.jsonl')
    reg2 = CandidateRegistry(log2)
    assert reg2.current('c1') == 'EXECUTED'
    actions = [r for r in log2.read() if r.get('kind') == 'position_action']
    assert len(actions) == 1 and actions[0]['fraction'] == 0.25


def test_position_action_vocabulary_distinct_from_endpoints(tmp_path):
    """PARTIAL_EXIT is a lifecycle action, not an outcome endpoint: no
    outcome can carry it (schema.CounterfactualOutcome.endpoint vocabulary is
    unchanged) and the action's kind is a different record class."""
    reg = _registry(tmp_path)
    _to_executed(reg)
    rec = reg.position_action('c1', 'PARTIAL_EXIT', fraction=0.25, price=103.0,
                              knowledge_time=10)
    assert rec['kind'] == 'position_action'
    assert 'endpoint' not in rec
    assert 'to_state' not in rec


def test_illegal_transition_still_fails_after_position_action(tmp_path):
    """The PositionAction machinery must not loosen transition legality: an
    illegal state move still raises."""
    reg = _registry(tmp_path)
    _to_executed(reg)
    reg.position_action('c1', 'PARTIAL_EXIT', fraction=0.25, price=103.0,
                        knowledge_time=10)
    with pytest.raises(IllegalTransitionError):
        reg.apply('c1', 'EXECUTED', 'ORDER_SUBMITTED', 'submit_order', 11)
