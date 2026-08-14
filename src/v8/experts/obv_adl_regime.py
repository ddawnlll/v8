"""OBV/ADL regime-gate behavior family (`obv_adl_regime`).

Hypothesis: when the volume oscillators agree with price, the market is
predisposed to trending and a directional continuation candidate is the
testable claim; when they disagree the regime is ranging and the expert
stands down (Ch6.2 p203-206; Ch9.9.6.5 p350: "directional traders use this
to avoid choppy action and only participate when the market is predisposed to
trending").

This is a self-gating EXPERT, not a router and not a selection layer over
other experts (CRIT-7): it never switches another Expert's behavior — it only
decides its own evaluate() verdict. OBV and ADL are cumulative levels whose
per-bar increments (direction-signed volume / money flow) are not recoverable
from the 32-bar price history, so their trend direction is read from the
features that DO express it: the 20-bar Chaikin money flow (cmf_20) carries
the ADL slope over its window, and the up-bar count of the last
OBV_WINDOW bars carries the OBV slope sign (OBV rises when closes rise).

Four variants share the volume-oscillator-regime mechanism:
  a  OBV-ADL agreement = trending regime: OBV slope, cmf_20 and the EMA
     trend all point the same way -> directional candidate; any disagreement
     -> NO_SETUP (ranging regime, stand down).
  b  OBV bullish/bearish divergence: price weak (below the slow EMA, no
     confirmation) while flow is positive -> the divergence precedes an
     upside rebound (LONG); mirror for a decline (SHORT).
  c  Divergence resolved by price confirmation: price below the slow EMA
     turns back above the fast EMA while flow is positive -> the wait-for-
     price-confirmation variant emits the candidate on the resolution.
  d  CMF oversold = potential bottom: cmf_20 below the oversold level in a
     downtrend -> exhausted distribution, LONG.

evaluate() emits ONE CandidateDraft per bar for the highest-priority variant
whose gate fires (declared priority d > c > b > a). All four variants count
as one multiplicity unit (rule 13; D-044 variants_evaluated) and are
distinguished by the `variant` geometry key.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class ObvAdlRegimeExpert(Expert):
    """Self-gating volume-oscillator regime expert."""
    expert_id = 'obv_adl_regime'
    version = 'v1'
    mechanism_family_id = 'volume_oscillator_regime'
    behavior_family_id = 'volume_oscillator_regime'
    variant_id = 'a'
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 4
    requires = ('participation', 'trend')

    # Declared, LOCKED constants (D-036 pattern: declared, never fitted).
    OBV_WINDOW = 10            # up-bar-count window for the OBV slope sign
    OBV_MAJORITY = 3           # net up-bars >= +3 -> OBV rising (of OBV_WINDOW)
    CMF_OVERSOLD = -0.15       # CMF oversold level (variant d)
    VARIANTS = ('d', 'c', 'b', 'a')     # single-draft gate priority

    def _obv_dir(self) -> float:
        """Sign of the OBV slope proxy: OBV rises on up closes, falls on down
        closes (per-bar volume only scales the increment), so the net up-bar
        count over OBV_WINDOW bars is the direction. Volume magnitude is not
        recoverable from the price history, so this is a signed proxy."""
        net = 0
        start = max(1, len(self._hist) - self.OBV_WINDOW)
        for i in range(start, len(self._hist)):
            _e, _o, _h, _l, c, _f, _s = self._hist[i]
            _pe, _po, _ph, _pl, pc, _pf, _ps = self._hist[i - 1]
            net += 1 if c > pc else (-1 if c < pc else 0)
        if net >= self.OBV_MAJORITY:
            return 1.0
        if net <= -self.OBV_MAJORITY:
            return -1.0
        return 0.0

    def _uptrend_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, _c, ema_fast, ema_slow = bar
        return ema_fast > ema_slow

    def _downtrend_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, _c, ema_fast, ema_slow = bar
        return ema_fast < ema_slow

    def _weak_unconfirmed_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, close, ema_fast, ema_slow = bar
        return close < ema_slow and close <= ema_fast

    def _strong_unconfirmed_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, close, ema_fast, ema_slow = bar
        return close > ema_slow and close >= ema_fast

    def _weak_confirmed_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, close, ema_fast, ema_slow = bar
        return close < ema_slow and close > ema_fast

    def _strong_confirmed_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, close, ema_fast, ema_slow = bar
        return close > ema_slow and close < ema_fast

    def _below_slow_pred(self, i: int, bar: tuple) -> bool:
        _e, _o, _h, _l, close, _f, ema_slow = bar
        return close < ema_slow

    def _evaluate_variants(self, state: MarketState, sym: str,
                           f: dict, close: float) -> tuple[str, str, tuple] | None:
        """(variant_id, direction, anchor_predicate) for the first variant
        whose gate fires; None = stand down (ranging / no confirmation)."""
        obv_dir = self._obv_dir()
        cmf = f.get(f'{sym}.cmf_20')
        cmf_v = float(cmf.value) if (cmf is not None and cmf.value is not None) \
            else 0.0
        fast = f.get(f'{sym}.ema_fast')
        slow = f.get(f'{sym}.ema_slow')
        if fast is None or fast.value is None or slow is None or slow.value is None:
            return None
        fast_v, slow_v = float(fast.value), float(slow.value)
        for variant in self.VARIANTS:
            if variant == 'd':
                if cmf_v < self.CMF_OVERSOLD and close < slow_v:
                    return ('d', 'LONG', self._below_slow_pred)
            elif variant == 'c':
                if close < slow_v and close > fast_v and cmf_v > 0:
                    return ('c', 'LONG', self._weak_confirmed_pred)
                if close > slow_v and close < fast_v and cmf_v < 0:
                    return ('c', 'SHORT', self._strong_confirmed_pred)
            elif variant == 'b':
                if close < slow_v and close <= fast_v and obv_dir > 0 and cmf_v > 0:
                    return ('b', 'LONG', self._weak_unconfirmed_pred)
                if close > slow_v and close >= fast_v and obv_dir < 0 and cmf_v < 0:
                    return ('b', 'SHORT', self._strong_unconfirmed_pred)
            else:  # 'a' — OBV/ADL agreement with the EMA trend
                if obv_dir > 0 and cmf_v > 0 and fast_v > slow_v:
                    return ('a', 'LONG', self._uptrend_pred)
                if obv_dir < 0 and cmf_v < 0 and fast_v < slow_v:
                    return ('a', 'SHORT', self._downtrend_pred)
        return None

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.ema_fast', f'{sym}.ema_slow',
                f'{sym}.atr', f'{sym}.cmf_20', f'{sym}.history']
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
        hit = self._evaluate_variants(state, sym, f, close)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        variant, direction, pred = hit
        # Freeze the regime bar's extreme at detection: a LONG regime is dead
        # below the detection bar's low, a SHORT regime above its high.
        level = float(self._hist[-1][3]) if direction == 'LONG' \
            else float(self._hist[-1][2])
        ref_key = 'prior_low_ref' if direction == 'LONG' else 'prior_high_ref'
        anchor = self.find_setup_anchor(self._hist, pred)
        geometry = self.declared_geometry()
        geometry.update({'atr_ref': atr, 'variant': variant, ref_key: level})
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{close:.6f}:{level:.6f}:{variant}',
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the volume-oscillator regime is trending in the
        trade's direction": a close beyond the frozen regime-bar extreme says
        the regime flipped (or was misread) and the reason to hold is gone."""
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
