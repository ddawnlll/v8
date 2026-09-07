"""Participation-conditioned breakout family (`volume_range_breakout`).

It uses venue-reported bar volume and realized bar range only.  It does not
claim to observe order flow, liquidity, or aggressor-side participation.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class VolumeRangeBreakoutExpert(Expert):
    expert_id = 'volume_range_breakout'
    version = 'v1'
    mechanism_family_id = 'participation_confirmation'
    behavior_family_id = 'volume_range_breakout'
    variant_id = 'a'
    requires = ('location', 'volatility', 'participation', 'history')

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t, sym, f = state.as_of, state.universe[0], state.features
        need = [f'{sym}.atr', f'{sym}.relative_volume', f'{sym}.range_ratio',
                f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        atr = f[f'{sym}.atr'].value
        rel_vol, range_ratio = f[f'{sym}.relative_volume'].value, f[f'{sym}.range_ratio'].value
        raw = f[f'{sym}.history'].value
        if atr is None or rel_vol is None or range_ratio is None or not isinstance(raw, (tuple, list)) or len(raw) < 6:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(raw)
        if float(rel_vol) < 1.5 or float(range_ratio) < 1.2:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        close, prior = float(hist[-1][4]), hist[-6:-1]
        high, low = max(bar[2] for bar in prior), min(bar[3] for bar in prior)
        direction = 'LONG' if close > high else 'SHORT' if close < low else None
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version, instrument=sym,
            direction=direction,
            setup_fingerprint=f'{sym}:{direction}:{rel_vol:.4f}:{range_ratio:.4f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr,
                           'relative_volume': rel_vol, 'range_ratio': range_ratio},
            birth_time=t, setup_anchor_event_id=hist[-1][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)
