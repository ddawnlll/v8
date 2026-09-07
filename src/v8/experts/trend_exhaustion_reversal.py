"""Trend-exhaustion-reversal behavior family (`trend_exhaustion_reversal`).

The executable hypothesis is intentionally narrower than a discretionary
"reversal" reading: a three-bar directional run must break the preceding
three-bar extreme while the EMA trend still points in the old direction.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class TrendExhaustionReversalExpert(Expert):
    expert_id = 'trend_exhaustion_reversal'
    version = 'v1'
    mechanism_family_id = 'trend_exhaustion'
    behavior_family_id = 'run_break_reversal'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t, sym, f = state.as_of, state.universe[0], state.features
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        atr, raw = f[f'{sym}.atr'].value, f[f'{sym}.history'].value
        if atr is None or not isinstance(raw, (tuple, list)) or len(raw) < 7:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(raw)
        closes = [float(bar[4]) for bar in hist]
        fast, slow = float(hist[-1][5]), float(hist[-1][6])
        direction = None
        # A completed up-run broken downward is a SHORT hypothesis; symmetric
        # for a down-run broken upward.  All values are closed-bar observations.
        if fast > slow and closes[-4] < closes[-3] < closes[-2] and closes[-1] < min(closes[-4:-1]):
            direction = 'SHORT'
        elif fast < slow and closes[-4] > closes[-3] > closes[-2] and closes[-1] > max(closes[-4:-1]):
            direction = 'LONG'
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = hist[-4][0]
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version, instrument=sym,
            direction=direction, setup_fingerprint=f'{sym}:{direction}:{closes[-1]:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        sym = draft.instrument
        close = state.features.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        anchor = float(draft.setup_fingerprint.rsplit(':', 1)[-1])
        return float(close.value) < anchor if draft.direction == 'SHORT' else float(close.value) > anchor
