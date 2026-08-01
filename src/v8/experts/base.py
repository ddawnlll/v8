"""Expert base contract (EXPERT_PROTOCOL sections 2-3).

An Expert is one falsifiable executable hypothesis about one behavior
family. It consumes a point-in-time MarketState and emits
CandidateDraft | None. It never submits an order and never allocates
capital. Concrete behavior families live one file per family in this
package.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation


class Expert:
    expert_id = 'base'
    version = 'v1'
    # Phase 3 ontology (EXPERT_PROTOCOL sections 1, 4; ROADMAP Phase 3). A
    # hypothesis family is identified by mechanism + behavior + variant;
    # parameter/threshold/geometry changes are VARIANTS of one family, never
    # separate Experts, and all variants count as one multiplicity unit in the
    # family-level multiple-testing correction (V8_CONSTITUTION rule 13).
    mechanism_family_id = ''
    behavior_family_id = ''
    variant_id = ''
    # Feature groups this Expert consumes (EXPERT_PROTOCOL section 1). The
    # declared set is part of the frozen specification and is audited against
    # actual consumption (tests/test_expert_registry.py).
    requires: tuple[str, ...] = ()

    def registry_entry(self) -> dict:
        """The code-side registry projection. docs/EXPERTS_REGISTRY.yaml must
        match it exactly; tests/test_expert_registry.py enforces that, so the
        ontology cannot drift from the registry."""
        return {'expert_id': self.expert_id, 'expert_version': self.version,
                'mechanism_family_id': self.mechanism_family_id,
                'behavior_family_id': self.behavior_family_id,
                'variant_id': self.variant_id, 'requires': list(self.requires),
                'status': 'FORMALIZED'}

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        raise NotImplementedError

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """Post-entry thesis check, evaluated on closed bars like any other rule.

        A price stop and a dead thesis are different exits. The stop says the
        market moved against the position; this says the reason for holding it
        no longer exists — the trader's "I'm out, the setup is gone" while the
        stop is still a distance away. Deterministic and part of the Expert's
        frozen specification, so it adds no learned component (Constitution 14).

        Default is True: an Expert that declares no post-entry thesis behaves
        exactly as before, and the exit is decided by price alone.
        """
        return True

    def _need(self, state: MarketState, keys: list[str]) -> bool:
        return all(k in state.features for k in keys)

    @staticmethod
    def find_setup_anchor(history: tuple, predicate) -> str:
        """event_id of the first closed bar of the current consecutive run in
        which `predicate(i, bar)` holds (D-026; CANDIDATE_LIFECYCLE_SPEC 1).

        Scans newest -> oldest for the newest bar where the predicate is false;
        the anchor is the next (newer) bar after it — the run start. If no
        false bar exists in the window, the anchor is the oldest bar in the
        window (documented bound: anchors older than the window are unstable).
        If the predicate is false on the newest bar there is no active run; the
        newest bar is returned as a bounded fallback (a caller that emits a
        draft under the state predicate should not reach this branch).
        """
        if not history:
            raise ValueError('setup anchor requires non-empty history')
        newest_false = -1
        for i in range(len(history) - 1, -1, -1):
            if not predicate(i, history[i]):
                newest_false = i
                break
        start = newest_false + 1
        if start == len(history):
            start = len(history) - 1
        return history[start][0]
