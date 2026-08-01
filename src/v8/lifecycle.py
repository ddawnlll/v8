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
    # CANDIDATE_LIFECYCLE_SPEC: "any terminal | retain | ARCHIVED". Previously
    # TERMINAL declared ARCHIVED but LEGAL had no edge to it, so the state was
    # paper-only and any archive attempt raised IllegalTransitionError.
    # ARCHIVED itself is excluded (it is already terminal — a self-archival
    # self-loop must not be a legal transition).
    **{(_t, 'ARCHIVED'): 'retain' for _t in TERMINAL if _t != 'ARCHIVED'},
}


class IllegalTransitionError(ValueError):
    pass


def episode_key(expert_id: str, expert_version: str, instrument: str,
                direction: str, setup_anchor_event_id: str,
                geometry_version: str) -> str:
    """Deterministic candidate identity anchored to the setup event, never the
    decision clock (D-026; CANDIDATE_LIFECYCLE_SPEC section 1). A birth
    timestamp in the key would make a re-detected setup hash differently and
    silently disable deduplication."""
    return sha1_hex((expert_id, expert_version, instrument, direction,
                     setup_anchor_event_id, geometry_version))


class CandidateRegistry:
    """Owns transition legality; projects current state from the log."""

    def __init__(self, log: AppendOnlyLog):
        self.log = log
        self._state: dict[str, str] = {}
        self._seq: dict[str, int] = {}
        self._detected: set[str] = set()
        for rec in self.log.read():
            if 'from_state' in rec:
                # Replay must validate legality like apply(): a corrupt log with
                # an illegal transition (mutation-campaign requirement) must
                # fail loudly, not silently project a state no run could reach.
                if (rec.get('from_state'), rec['to_state']) not in LEGAL:
                    raise IllegalTransitionError(
                        f'{rec.get("candidate_id")}: replay '
                        f'{rec.get("from_state")} -> {rec["to_state"]} not legal')
                self._apply_projection(rec)

    def _apply_projection(self, rec: dict) -> None:
        cid = rec['candidate_id']
        self._seq[cid] = rec['sequence']
        self._state[cid] = rec['to_state']
        if rec['to_state'] == 'DETECTED':
            self._detected.add(cid)

    def current(self, candidate_id: str) -> str | None:
        return self._state.get(candidate_id)

    def apply(self, candidate_id: str, from_state: str | None, to_state: str,
              reason_code: str, knowledge_time: int, source: str = 'lifecycle',
              extra: dict | None = None) -> dict:
        """Record one legal transition. `extra` fields are merged into the
        stored record BEFORE append, so they become part of the immutable
        append-only event (e.g. the birth snapshot on DETECTED,
        CANDIDATE_LIFECYCLE_SPEC section 1) — they can never be added later."""
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
        if extra:
            rec.update(extra)
        self.log.append(rec)
        self._apply_projection(rec)
        return rec

    def is_duplicate(self, key: str) -> bool:
        """True iff the key already produced a DETECTED episode.

        The time window is removed: key stability under D-026 means the same
        setup re-detected on any later decision clock hashes to the same key,
        so anchor equality subsumes the window (keeping both would
        double-suppress).
        """
        return key in self._detected


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
