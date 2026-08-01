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

    def _setup_pred(self, i: int, bar: tuple) -> bool:
        """Per-history-bar predicate (pinned D-026 interpretation): a close
        below the per-bar prior high (max high of the bars before it in the
        window). The detection gate in evaluate() uses the SAME reference (the
        windowed prior of the newest bar), so the anchor cannot slide."""
        if i == 0:
            return False                       # no prior bar: no prior high
        event_id, _open, high, _low, close, _f, _s = bar
        prior = max(h for (_e, _o, h, _l, _c, _ff, _ss) in self._hist[:i])
        return close < prior

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
        # ONE prior-high reference for the gate AND the anchor: the max high
        # over the history window, excluding the newest bar. The state feature
        # prior_high is the ALL-BARS max, which an old spike outside the window
        # would pin forever — a gate on that diverges from the windowed anchor,
        # fires on every bar and defeats episode-key dedup.
        self._ref_prior_high = float(max(
            h for (_e, _o, h, _l, _c, _ff, _ss) in self._hist[:-1]))
        if not (close < self._ref_prior_high):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        # The invalidation reference is FROZEN at detection: a live reference
        # (recomputed every clock) drifts upward with the adverse move and the
        # documented thesis invalidation ('a close back above the prior high')
        # never fires on a reversal.
        anchor = self.find_setup_anchor(self._hist, self._setup_pred)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='SHORT',
            setup_fingerprint=f'{sym}:{close:.6f}:{self._ref_prior_high:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr, 'prior_high_ref': self._ref_prior_high},
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
