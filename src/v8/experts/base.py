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
