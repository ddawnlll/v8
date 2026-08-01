"""Candidate lifecycle state machine (CANDIDATE_LIFECYCLE_SPEC section 2).

All transitions are append-only and legal-transition-checked; current state is
a projection of the log; reactivation after a terminal state is forbidden.
"""
from __future__ import annotations

from .schema import CandidateTransition, sha1_hex, record_dict
from .store import AppendOnlyLog

TERMINAL = frozenset({'REJECTED', 'EXPIRED', 'INVALIDATED', 'CANCELLED', 'CLOSED', 'ARCHIVED'})

LEGAL: dict[tuple[str | None, str], str] = {
    (None, 'DETECTED'): 'setup_detected',
    ('DETECTED', 'PENDING'): 'hypothesis_completed',
    ('DETECTED', 'REJECTED'): 'reject',
    ('PENDING', 'TRIGGERED'): 'trigger_observed',
    ('PENDING', 'EXPIRED'): 'expiry_reached',
    ('PENDING', 'INVALIDATED'): 'invalidation_observed',
    ('PENDING', 'REJECTED'): 'reject',
    ('TRIGGERED', 'ACCEPTED'): 'risk_accept',
    ('TRIGGERED', 'INVALIDATED'): 'invalidation_observed',
    ('TRIGGERED', 'REJECTED'): 'reject',
    ('ACCEPTED', 'ORDER_SUBMITTED'): 'submit_order',
    ('ACCEPTED', 'REJECTED'): 'reject',
    ('ORDER_SUBMITTED', 'EXECUTED'): 'fill_observed',
    ('ORDER_SUBMITTED', 'CANCELLED'): 'cancel_confirmed',
    ('EXECUTED', 'CLOSED'): 'position_flat',
}


class IllegalTransitionError(ValueError):
    pass


def episode_key(expert_id: str, expert_version: str, instrument: str,
                direction: str, setup_fingerprint: str, birth_time: int) -> str:
    """Deterministic candidate identity (CANDIDATE_LIFECYCLE_SPEC section 1)."""
    return sha1_hex((expert_id, expert_version, instrument, direction,
                     setup_fingerprint, birth_time))


class CandidateRegistry:
    """Owns transition legality; projects current state from the log."""

    def __init__(self, log: AppendOnlyLog, dedup_window_bars: int = 6):
        self.log = log
        self.dedup_window_bars = dedup_window_bars
        self._state: dict[str, str] = {}
        self._seq: dict[str, int] = {}
        self._birth_time: dict[str, int] = {}
        for rec in self.log.read():
            if 'from_state' in rec:
                self._apply_projection(rec)

    def _apply_projection(self, rec: dict) -> None:
        cid = rec['candidate_id']
        self._seq[cid] = rec['sequence']
        self._state[cid] = rec['to_state']
        if rec['to_state'] == 'DETECTED':
            self._birth_time[cid] = rec['knowledge_time']

    def current(self, candidate_id: str) -> str | None:
        return self._state.get(candidate_id)

    def apply(self, candidate_id: str, from_state: str | None, to_state: str,
              reason_code: str, knowledge_time: int, source: str = 'lifecycle') -> dict:
        cur = self._state.get(candidate_id)
        if cur != from_state:
            raise IllegalTransitionError(
                f'{candidate_id}: expected {from_state}, current is {cur}')
        if (from_state, to_state) not in LEGAL:
            raise IllegalTransitionError(f'{candidate_id}: {from_state} -> {to_state} not legal')
        seq = self._seq.get(candidate_id, 0) + 1
        ev = CandidateTransition(candidate_id=candidate_id, sequence=seq,
                                 from_state=from_state, to_state=to_state,
                                 reason_code=reason_code, knowledge_time=knowledge_time,
                                 event_hash=sha1_hex((candidate_id, seq, from_state,
                                                      to_state, reason_code,
                                                      knowledge_time)))
        rec = record_dict(ev, source=source)
        rec['event_id'] = f'{candidate_id}:{seq}'
        self.log.append(rec)
        self._apply_projection(rec)
        return rec

    def is_duplicate(self, key: str, birth_time: int) -> bool:
        prev = self._birth_time.get(key)
        if prev is None:
            return False
        # Time-windowed suppression window; a distinct new setup gets a new key.
        return birth_time - prev < self.dedup_window_bars * 3_600_000_000_000


class ExposureBook:
    """One active exposure per (instrument, direction) (LIFECYCLE_SPEC section 6)."""

    def __init__(self) -> None:
        self._active: set[tuple[str, str]] = set()

    def acquire(self, instrument: str, direction: str) -> bool:
        key = (instrument, direction)
        if key in self._active:
            return False
        self._active.add(key)
        return True

    def release(self, instrument: str, direction: str) -> None:
        self._active.discard((instrument, direction))
