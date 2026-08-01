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

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.prior_high', f'{sym}.atr']
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
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='SHORT',
            setup_fingerprint=f'{sym}:{close:.6f}:{prior_high:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr},
            birth_time=t)
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
