"""Trend-pullback-continuation behavior family (`trend_pullback`).

Hypothesis: inside an uptrend, a pullback to the slow EMA is a continuation
setup. Detected on closed bars only; emits LONG CandidateDrafts.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class TrendPullbackExpert(Expert):
    """Uptrend (ema_fast > ema_slow) with a pullback (close < ema_slow)."""
    expert_id = 'trend_pullback'
    version = 'v1'
    mechanism_family_id = 'trend_continuation'
    behavior_family_id = 'pullback_in_trend'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')

    @staticmethod
    def _setup_pred(i: int, bar: tuple) -> bool:
        """Per-history-bar predicate (pinned D-026 interpretation): uptrend with
        a pullback to the slow EMA."""
        _event_id, _open, _high, _low, close, ema_fast, ema_slow = bar
        return ema_fast > ema_slow and close < ema_slow

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.ema_fast', f'{sym}.ema_slow', f'{sym}.atr',
                f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        fast = float(f[f'{sym}.ema_fast'].value)
        slow = float(f[f'{sym}.ema_slow'].value)
        atr = f[f'{sym}.atr'].value
        if atr is None or not (fast > slow and close < slow):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        hist_value = f[f'{sym}.history'].value
        if not isinstance(hist_value, (tuple, list)) or not hist_value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        anchor = self.find_setup_anchor(tuple(hist_value), self._setup_pred)
        geometry = self.declared_geometry()
        geometry['atr_ref'] = atr
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='LONG',
            setup_fingerprint=f'{sym}:{close:.6f}:{slow:.6f}',
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "pullback inside an uptrend"; if the uptrend is gone,
        so is the reason to hold, whatever the stop distance still says."""
        sym = draft.instrument
        f = state.features
        fast, slow = f.get(f'{sym}.ema_fast'), f.get(f'{sym}.ema_slow')
        if fast is None or slow is None or fast.value is None or slow.value is None:
            return True          # unobservable: fail open, price still governs
        return float(fast.value) > float(slow.value)
