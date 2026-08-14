"""Failed-breakout-reentry behavior family (`failed_breakout`).

Hypothesis: a close above the prior high that fails back below it is a
liquidity-vacuum reentry setup. Detected on closed bars only; emits SHORT
CandidateDrafts.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class FailedBreakoutExpert(Expert):
    """Close exceeds prior_high, then closes back below it (failed breakout)."""
    expert_id = 'failed_breakout'
    version = 'v1'
    mechanism_family_id = 'liquidity_vacuum_reentry'
    behavior_family_id = 'failed_breakout_reentry'
    variant_id = 'a'
    requires = ('location', 'volatility', 'history')
    # stop_r is structural: the frozen distance to the level the breakout
    # failed under (D-028), computed in evaluate(); target_r stays the family
    # 1:1 default.
    stop_r = None

    def _last_breakout(self) -> tuple[int, float] | None:
        """(idx, level) of the most recent close-breakout in the window: bar j
        whose CLOSE exceeded the max high of the bars BEFORE it (the pre-move
        high-water mark), and the level that bar broke. The failed-breakout
        thesis needs this first leg — a close that first went above the prior
        high — before a later close back below it can be a "failure"
        (Ch7.3 p228). None when no bar in the window ever closed above its own
        prior high (a plain downtrend is not a failed breakout)."""
        for j in range(len(self._hist) - 1, 0, -1):
            prior = max(h for (_e, _o, h, _l, _c, _ff, _ss) in self._hist[:j])
            if self._hist[j][4] > prior:
                return j, float(prior)
        return None

    def _setup_pred(self, i: int, bar: tuple) -> bool:
        """Per-history-bar predicate (pinned D-026 interpretation): bar i is in
        the failure run — it closed below the FROZEN breakout level AFTER the
        breakout bar (`_breakout_idx`). Bars before the breakout are not
        failure bars, so the anchor cannot slide across the breakout."""
        if i == 0:
            return False
        _e, _o, _h, _l, close, _f, _s = bar
        return i > self._breakout_idx and float(close) < self._level

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        hist_value = f[f'{sym}.history'].value
        if not isinstance(hist_value, (tuple, list)) or not hist_value or atr is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = tuple(hist_value)
        # The two-step hypothesis, not a bare "price below the prior high":
        # a prior bar must first have CLOSED above its own prior high (the
        # breakout leg, Ch7.3 p228), and the newest bar must have closed back
        # below that SAME breakout level (the failure leg). The level is
        # FROZEN at detection (prior_high_ref pattern) — a live reference
        # (recomputed every clock) drifts upward with the adverse move and the
        # documented thesis invalidation ('a close back above the prior high')
        # never fires on a reversal.
        breakout = self._last_breakout()
        if breakout is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        self._breakout_idx, self._ref_prior_high = breakout
        if not (close < self._ref_prior_high):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        self._level = self._ref_prior_high
        # The invalidation reference is FROZEN at detection: a live reference
        # (recomputed every clock) drifts upward with the adverse move and the
        # documented thesis invalidation ('a close back above the prior high')
        # never fires on a reversal.
        anchor = self.find_setup_anchor(self._hist, self._setup_pred)
        # Issue #63: the structural stop IS the frozen breakout level — the
        # stop's place for a failed-breakout SHORT is beyond the prior high
        # it failed under, not a fixed ATR multiple from entry. stop_r is the
        # frozen distance in R (D-028): (prior_high - close) / atr_ref.
        stop_r = (self._ref_prior_high - close) / atr
        geometry = self.declared_geometry()
        geometry.update({'stop_r': stop_r, 'atr_ref': atr,
                         'prior_high_ref': self._ref_prior_high,
                         'stop_ref': self._ref_prior_high})
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='SHORT',
            setup_fingerprint=f'{sym}:{close:.6f}:{self._ref_prior_high:.6f}',
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the breakout failed"; a close back above the prior
        high says it did not fail after all, so the short has no premise.

        The reference is the FROZEN setup prior_high (prior_high_ref), not the
        live state's prior_high: a live max drifts with the adverse move and
        the invalidation never fires on a reversal that re-crosses the
        entry-time breakout level.
        """
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        ref = draft.risk_geometry.get('prior_high_ref')
        if close is None or close.value is None:
            return True          # unobservable: fail open, price still governs
        if ref is None:
            # Backward compatibility: no frozen reference (legacy drafts).
            prior_high = f.get(f'{sym}.prior_high')
            if prior_high is None or prior_high.value is None:
                return True
            ref = float(prior_high.value)
        return float(close.value) < float(ref)


class FailedBreakoutV2Expert(FailedBreakoutExpert):
    """v2 CHALLENGER (D-074, `FCR-V8RR-010`): identical setup, trigger,
    invalidation and geometry to v1 — ONE added pre-entry admission filter,
    nothing else. Never mutates v1 in place (rule 15/D-023); v1 is unchanged
    by this class and stays the champion.

    Origin: the V8 x Recoverable Regret v0.2 Phase-3 recoverability pass
    (`D-073`) independently selected a `bb_pct_b < ~0.73` NO_TRADE gate on 4
    of 6 symbols for `failed_breakout` SHORT, each with a materially positive,
    confirmation-half-validated utility delta. This class tests that pattern
    as ONE preregistered, single-component intervention — a declared, ROUND
    threshold (0.70), not a per-symbol refit of the 4 measured values.

    PROVISIONAL: deliberately NOT exported via `experts/__init__.py` or
    registered in `docs/EXPERTS_REGISTRY.yaml` — this is a challenger under
    test (rule 5), not yet a registry admission. Promotion is a separate,
    later decision contingent on the frozen comparison's result.
    """
    version = 'v2'
    variant_id = 'b'

    # Declared, frozen constant (FCR-V8RR-010 FT002) — the round value used
    # across every symbol, not the 4 separately-fitted Phase-3 thresholds.
    BB_PCT_B_MAX = 0.70

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        ev = super().evaluate(state)
        if ev.draft is None:
            return ev
        sym = state.universe[0]
        bb = state.features.get(f'{sym}.bb_pct_b')
        if bb is None or bb.value is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', state.as_of)
        if not (float(bb.value) < self.BB_PCT_B_MAX):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', state.as_of)
        return ev
