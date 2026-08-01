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

    def _setup_pred(self, i: int, bar: tuple) -> bool:
        """Per-history-bar predicate (pinned D-026 interpretation): a close
        below the prior high within the window (per-bar prior high)."""
        if i == 0:
            return False                       # no prior bar: no prior high
        event_id, _open, high, _low, close, _f, _s = bar
        prior = max(h for (_e, _o, h, _l, _c, _ff, _ss) in self._hist[:i])
        return close < prior

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.prior_high', f'{sym}.atr',
                f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        prior_high = f[f'{sym}.prior_high'].value
        atr = f[f'{sym}.atr'].value
        if prior_high is None or atr is None or not (close < prior_high):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        hist_value = f[f'{sym}.history'].value
        if not isinstance(hist_value, (tuple, list)) or not hist_value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = tuple(hist_value)
        anchor = self.find_setup_anchor(self._hist, self._setup_pred)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='SHORT',
            setup_fingerprint=f'{sym}:{close:.6f}:{prior_high:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the breakout failed"; a close back above the prior
        high says it did not fail after all, so the short has no premise."""
        sym = draft.instrument
        f = state.features
        close, prior_high = f.get(f'{sym}.close'), f.get(f'{sym}.prior_high')
        if close is None or prior_high is None \
                or close.value is None or prior_high.value is None:
            return True          # unobservable: fail open, price still governs
        return float(close.value) < float(prior_high.value)
