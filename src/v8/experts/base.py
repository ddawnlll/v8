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
    # D-053 — the MarketState this Expert asks for, alongside `requires`:
    #
    # `intervals`: bar intervals beyond the run's base interval. Empty means
    #   "base interval only" (every pre-D-053 Expert). A declared interval must
    #   be an exact integer multiple of the base or the run fails closed at the
    #   feasibility gate — aggregation is up-only, so a 1h tape can never serve
    #   a 15m declaration.
    # `depth`: bars of `history` this Expert needs, per interval. An int
    #   applies to every declared interval; a dict names them individually.
    #   This is a REQUEST, not a guarantee: the gate refuses a depth the tape
    #   cannot cover rather than quietly serving a short window, because a
    #   silently-truncated history is what turned three families into
    #   documented-deviation proxies (O-020).
    #
    # Interval is part of the hypothesis, never a search axis: an Expert
    # evaluated on three intervals is three multiplicity units, which is why
    # the declaration is frozen per variant rather than chosen per run.
    intervals: tuple[str, ...] = ()
    depth: int | dict[str, int] = 32
    # Declared risk geometry (EXPERT_PROTOCOL section 1: risk geometry is
    # "Predeclared entry, stop, target, timeout and sizing inputs";
    # SIMULATION_TRUTH_SPEC D-028: R is a declared price distance). A FIXED
    # value is declared here and never re-literalized inside evaluate(). A
    # family whose target/stop is structural (measured move / channel height /
    # pivot level) declares None and computes the value in evaluate(),
    # overriding the key after `declared_geometry()` — the None marks the
    # value as structural rather than a fixed family constant.
    target_r: float | None = 1.0
    stop_r: float | None = 1.0
    expiry_bars: int = 8

    def declared_depth(self, interval: str) -> int:
        """Bars of history this Expert asks for on `interval`."""
        if isinstance(self.depth, dict):
            return int(self.depth.get(interval, 32))
        return int(self.depth)

    def declared_intervals(self, base_interval: str) -> tuple[str, ...]:
        """Every interval this Expert reads, base included, deduplicated and
        base-first so the serving order is deterministic."""
        out = [base_interval]
        for tf in self.intervals:
            if tf not in out:
                out.append(tf)
        return tuple(out)

    def declared_geometry(self) -> dict:
        """The frozen risk-geometry slice every CandidateDraft of this Expert
        carries: entry mode, fixed R values, and the expiry bound. Values come
        from the class declarations, so a family never embeds them as literals
        inside evaluate(); structural families override the None keys with the
        value computed from the measured setup."""
        return {'entry': 'NEXT_BAR_CLOSE', 'target_r': self.target_r,
                'stop_r': self.stop_r, 'expiry_bars': self.expiry_bars}

    def registry_entry(self) -> dict:
        """The code-side registry projection. docs/EXPERTS_REGISTRY.yaml must
        match it exactly; tests/test_expert_registry.py enforces that, so the
        ontology cannot drift from the registry.

        `intervals`/`depth` appear only when they differ from the defaults, so
        a base-interval Expert projects exactly as it did before D-053 and the
        registry needs no migration for families that never left 1h.
        """
        entry = {'expert_id': self.expert_id, 'expert_version': self.version,
                 'mechanism_family_id': self.mechanism_family_id,
                 'behavior_family_id': self.behavior_family_id,
                 'variant_id': self.variant_id, 'requires': list(self.requires),
                 'status': 'FORMALIZED'}
        if self.intervals:
            entry['intervals'] = list(self.intervals)
        if self.depth != 32:
            entry['depth'] = self.depth
        return entry

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
