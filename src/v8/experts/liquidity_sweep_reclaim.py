"""Liquidity-sweep-reclaim behavior family (`liquidity_sweep_reclaim`).

Hypothesis: a wick through a prior extreme that reclaims the level by the
close is a stop-hunt reversal setup — LONG after a sweep of the prior low
that closes back above it, SHORT after a sweep of the prior high that closes
back below it. Detected on closed bars only; the direction is decided by
which level the detection bar swept.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class LiquiditySweepReclaimExpert(Expert):
    """Sweep of the windowed prior extreme, reclaimed by the close."""
    expert_id = 'liquidity_sweep_reclaim'
    version = 'v1'
    mechanism_family_id = 'liquidity_sweep_reclaim'
    behavior_family_id = 'sweep_reclaim'
    variant_id = 'a'
    requires = ('location', 'volatility', 'history')

    def _prior_low(self, i: int) -> float:
        return min(l for (_e, _o, _h, l, _c, _f, _s) in self._hist[:i])

    def _prior_high(self, i: int) -> float:
        return max(h for (_e, _o, h, _l, _c, _f, _s) in self._hist[:i])

    def _long_pred(self, i: int, bar: tuple) -> bool:
        """Bar i swept the windowed prior low and reclaimed it by the close."""
        if i == 0:
            return False                       # no prior bar: no prior low
        _e, _o, _h, low, close, _f, _s = bar
        return low < self._prior_low(i) and close > self._prior_low(i)

    def _short_pred(self, i: int, bar: tuple) -> bool:
        """Bar i swept the windowed prior high and reclaimed it by the close."""
        if i == 0:
            return False                       # no prior bar: no prior high
        _e, _o, high, _l, close, _f, _s = bar
        return high > self._prior_high(i) and close < self._prior_high(i)

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
        # ONE swept-level reference for the gate AND the anchor: the windowed
        # prior extreme of the newest bar (excludes the newest bar itself).
        prior_low = self._prior_low(len(self._hist) - 1)
        prior_high = self._prior_high(len(self._hist) - 1)
        newest = self._hist[-1]
        _e, _o, high, low, _c, _f, _s = newest
        direction: str | None = None
        ref: float = 0.0
        ref_key = ''
        if low < prior_low and close > prior_low:
            direction, ref, ref_key = 'LONG', prior_low, 'prior_low_ref'
        elif high > prior_high and close < prior_high:
            direction, ref, ref_key = 'SHORT', prior_high, 'prior_high_ref'
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._long_pred if direction == 'LONG' else self._short_pred
        anchor = self.find_setup_anchor(self._hist, pred)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{close:.6f}:{ref:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr, ref_key: ref},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the sweep was reclaimed": price must stay on the
        reclaimed side of the swept level. The reference is FROZEN at
        detection — a live-recomputed extreme drifts with the adverse move and
        the invalidation would never fire on a re-cross (failed_breakout's
        prior_high_ref pattern)."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True          # unobservable: fail open, price still governs
        if draft.direction == 'LONG':
            ref = draft.risk_geometry.get('prior_low_ref')
            if ref is None:
                return True
            return float(close.value) > float(ref)
        ref = draft.risk_geometry.get('prior_high_ref')
        if ref is None:
            return True
        return float(close.value) < float(ref)
