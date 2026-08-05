"""Admission under exposure contention (D-018/D-043; RUNTIME_SCHEDULER_SPEC 5).

`RUNTIME_SCHEDULER_SPEC` section 5 test 3 claims that shuffling the evaluation
order of independent Experts produces identical stored events, and
`test_bugfix_pass.py::test_s2_expert_order_shuffle_identical` checks it with the
two pilots. Those two almost never emit on the same bar, so that test exercises
the claim with **no contention at all** — the case the claim is actually about
is untested.

D-043 removed the 3-Expert cap, so contention stops being hypothetical: many
Experts on one instrument compete for a single `(instrument, direction)`
exposure slot (rule 16 / D-018). These tests pin what the runtime does when they
do collide.

Two distinct properties, deliberately separated:

1. The ledger is order-independent even under full contention, because
   `lab.run` sorts Experts by `expert_id` before evaluating (`lab.py`). This is
   a real invariant and must not regress.
2. The surviving tie-break is therefore `expert_id` **lexicographic order**:
   deterministic, but an arbitrary allocation policy. At three Experts it is
   noise; at the unbounded count D-043 now permits it is a silent, name-based
   priority system. Test 2 pins that this is what is happening, so that
   introducing a principled tie-break (a ranker) fails here and forces the
   rule 6 / D-008 registry decision (O-006 / O-012) instead of landing
   silently.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from v8.experts.base import Expert
from v8.lab import Lab
from v8.schema import (CandidateDraft, ExpertEvaluation, ExperimentManifest,
                       LabReport)
from v8.synth import make_synthetic_tape


class _Contender(Expert):
    """Emits a LONG on every bar with a usable state.

    Deliberately unconditional: the point is maximum contention for one
    exposure slot, not a plausible hypothesis. Subclasses differ only in
    identity, so any asymmetry in outcomes comes from identity alone.
    """
    version = 'v1'
    mechanism_family_id = 'test_contention'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')

    def evaluate(self, state) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        if not self._need(state, [f'{sym}.close', f'{sym}.atr', f'{sym}.history']):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        atr = f[f'{sym}.atr'].value
        hist = f[f'{sym}.history'].value
        if atr is None or not isinstance(hist, (tuple, list)) or not hist:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        close = float(f[f'{sym}.close'].value)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='LONG',
            setup_fingerprint=f'{self.expert_id}:{sym}:{close:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr},
            birth_time=t, setup_anchor_event_id=hist[-1][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)


def _contender(expert_id: str) -> Expert:
    """A contender whose ONLY distinguishing property is its expert_id."""
    cls = type(f'_C_{expert_id}', (_Contender,),
               {'expert_id': expert_id, 'behavior_family_id': f'bf_{expert_id}'})
    return cls()


def _manifest() -> ExperimentManifest:
    return ExperimentManifest(experiment_id='exp-contention', code_hash='',
                              data_hash='', universe=('SOLUSDT',),
                              start_ns=0, end_ns=0)


def _run(experts: list) -> tuple[Lab, LabReport]:
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=60))
    report = lab.run(_manifest(), experts)
    return lab, report


def _hashes(lab: Lab) -> tuple:
    return (lab.candidates.hash, lab.evaluations.hash,
            lab.outcomes.hash, lab.states.hash)


def _conflicts_by_expert(lab: Lab) -> dict[str, int]:
    """Exposure-conflict rejections attributed to the emitting Expert.

    The REJECTED transition carries only the candidate_id; expert identity is
    on the immutable DETECTED birth snapshot, so the two are joined here.
    """
    records = lab.candidates.read()
    owner: dict[str, str] = {}
    for rec in records:
        cid, eid = rec.get('candidate_id'), rec.get('expert_id')
        if cid and eid:
            owner.setdefault(cid, eid)
    out: dict[str, int] = {}
    for rec in records:
        if rec.get('reason_code') == 'EXISTING_EXPOSURE_CONFLICT':
            eid = owner.get(rec.get('candidate_id', ''), '?')
            out[eid] = out.get(eid, 0) + 1
    return out


def test_contended_admission_is_order_independent():
    """Full contention, three Experts: caller list order must not move a hash.

    `lab.run` sorts by expert_id, so the caller's ordering is discarded. This
    is the invariant RUNTIME_SCHEDULER_SPEC 5 asserts, exercised for the first
    time with candidates that actually collide on one exposure slot.
    """
    names = ['alpha_c', 'mid_c', 'omega_c']
    lab_fwd, rep_fwd = _run([_contender(n) for n in names])
    lab_rev, rep_rev = _run([_contender(n) for n in reversed(names)])

    # Guard against a vacuous pass: without real contention this proves nothing.
    assert rep_fwd.n_portfolio_rejected > 0, \
        'no exposure contention occurred; the test would be vacuous'
    assert _hashes(lab_fwd) == _hashes(lab_rev), \
        'caller Expert order must not change any ledger hash'
    assert rep_fwd.n_executed == rep_rev.n_executed


def test_contested_slot_priority_follows_expert_id_not_behavior():
    """The surviving tie-break is the Expert's NAME (D-043 follow-up).

    Two behaviorally identical contenders differ only in expert_id. The one
    sorting first wins strictly more contested slots, and the advantage moves
    when the names move — so admission priority under contention is decided by
    lexicographic identity, not by anything about the hypothesis.

    This is deterministic and currently harmless at three Experts. It is pinned
    because D-043 lifted the cap: a principled tie-break is a ranker, and a
    ranker is gated by rule 6 / D-008 (O-006 / O-012). If one is ever added,
    this test fails and forces that decision to be registered.
    """
    lab_a, rep_a = _run([_contender('aaa_first'), _contender('zzz_last')])
    assert rep_a.n_portfolio_rejected > 0, 'no contention; test would be vacuous'
    conflicts_a = _conflicts_by_expert(lab_a)
    assert conflicts_a['zzz_last'] > conflicts_a['aaa_first'], (
        'the lexicographically first Expert should win more contested slots; '
        f'got {conflicts_a}')

    # Same two behaviors, names swapped: the disadvantage must follow the name.
    lab_b, _ = _run([_contender('aaa_last'), _contender('zzz_first')])
    conflicts_b = _conflicts_by_expert(lab_b)
    assert conflicts_b['zzz_first'] > conflicts_b['aaa_last'], (
        'priority must track expert_id, not class identity; '
        f'got {conflicts_b}')
