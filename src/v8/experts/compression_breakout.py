"""Volatility-compression-breakout behavior family (`compression_breakout`)."""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class CompressionBreakoutExpert(Expert):
    expert_id = 'compression_breakout'
    version = 'v1'
    mechanism_family_id = 'volatility_regime_transition'
    behavior_family_id = 'compression_breakout'
    variant_id = 'a'
    requires = ('volatility', 'location', 'history')

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t, sym, f = state.as_of, state.universe[0], state.features
        need = [f'{sym}.atr', f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        atr, raw = f[f'{sym}.atr'].value, f[f'{sym}.history'].value
        if atr is None or not isinstance(raw, (tuple, list)) or len(raw) < 21:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(raw)
        ranges = [float(bar[2]) - float(bar[3]) for bar in hist]
        baseline = sum(ranges[-21:-5]) / 16
        compressed = sum(ranges[-5:-1]) / 4
        if baseline <= 0 or compressed / baseline > 0.65:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        newest, previous = hist[-1], hist[-5:-1]
        close = float(newest[4])
        prior_high, prior_low = max(bar[2] for bar in previous), min(bar[3] for bar in previous)
        direction = 'LONG' if close > prior_high else 'SHORT' if close < prior_low else None
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version, instrument=sym,
            direction=direction,
            setup_fingerprint=f'{sym}:{direction}:{prior_high:.6f}:{prior_low:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr,
                           'compression_ratio': compressed / baseline},
            birth_time=t, setup_anchor_event_id=hist[-5][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)
