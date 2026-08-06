"""Candlestick-reversal behavior family (`candlestick_reversal`).

Hypothesis (mechanism `bar_shape_reversal`; Ch14.2 p556-577): a recognized
reversal candlestick that completes at the end of a move marks a
high-probability direction change. Detected on closed bars only; entry is
NEXT_BAR_CLOSE; confirmation is close-based — an intrabar penetration never
confirms (Ch14.2 doctrine; V8_LOGIC_GAP H07).

Variants (one per pattern; D-044 lists every implemented variant — the
book's Ch14.2 enumerations are the frozen search grid):
  hammer                - small body at the top of the range, long lower
                          shadow, no upper shadow, after a down bar -> LONG
  shooting_star         - small body at the bottom of the range, long upper
                          shadow, no lower shadow, after an up bar -> SHORT
  bullish_engulfing     - current body engulfs a prior down bar's body -> LONG
  bearish_engulfing     - current body engulfs a prior up bar's body -> SHORT
  bullish_harami        - small bullish body nested inside a prior down bar's
                          body -> LONG
  bearish_harami        - small bearish body nested inside a prior up bar's
                          body -> SHORT
  three_white_soldiers  - three rising bullish bars after a decline -> LONG
  three_black_crows     - three falling bearish bars after a rally -> SHORT

The book's gap-sequence patterns (morning/evening star, tasuki, island) are
not implemented here: they are gap-reaction signals and belong to the
`gap_reaction` family (E-21), whose card flags perps gaps as rare
(V8_LOGIC_GAP H07). The proportion constraints below are the book's own
Ch14.2 p558/566/570 rules: the real body is at most 1/4-1/3 of the range and
the long shadow is at least twice the body.

Stop: the book gives the pattern extreme exactly (Ch14.2 stop rules) — the
stop sits beyond the pattern, expressed in R with the 14-bar ATR unit
(D-028). Target: the book gives no measuring objective for single/double/
triple candle patterns (Ch14 gives none) -> family default 1R:1R:8bar.

The trigger is the book's close-confirmation level for each pattern
(Ch14.2 p556: "entry only on a CLOSE beyond the trigger") and is FROZEN at
detection. `still_valid` keeps the thesis alive while price stays beyond the
frozen trigger — a close back through it says the follow-through failed and
the reason to hold is gone (D-029).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, LOCKED constants (book Ch14.2 p558/566/570; D-036 pattern:
# "declared, never fitted").
BODY_RATIO_MAX = 1.0 / 3.0     # real body <= 1/3 of the range (book: 1/4-1/3)
SHADOW_MIN_MULT = 2.0          # long shadow >= 2x the body


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _upper_shadow(o: float, h: float, c: float) -> float:
    return h - max(o, c)


def _lower_shadow(o: float, l: float, c: float) -> float:
    return min(o, c) - l


def _body_ratio(o: float, h: float, l: float, c: float) -> float:
    rng = h - l
    return _body(o, c) / rng if rng > 0 else 0.0


class CandlestickReversalExpert(Expert):
    """One bar-shape reversal pattern per variant; direction is fixed by the
    pattern (hammer/bullish set -> LONG, bearish set -> SHORT)."""
    expert_id = 'candlestick_reversal'
    version = 'v1'
    mechanism_family_id = 'bar_shape_reversal'
    behavior_family_id = 'candlestick_reversal'
    variant_id = 'hammer'
    # D-044: every implemented variant (losers included); the reported
    # variant_id is a member. D-046: every threshold/lookback below is a
    # declared constant frozen pre-window, so the search universe equals the
    # evaluated set.
    variants_evaluated = ('hammer', 'shooting_star', 'bullish_engulfing',
                          'bearish_engulfing', 'bullish_harami',
                          'bearish_harami', 'three_white_soldiers',
                          'three_black_crows')
    search_universe_size = 8
    requires = ('candle_shape', 'volatility', 'history')

    _DIRECTION = {
        'hammer': 'LONG', 'shooting_star': 'SHORT',
        'bullish_engulfing': 'LONG', 'bearish_engulfing': 'SHORT',
        'bullish_harami': 'LONG', 'bearish_harami': 'SHORT',
        'three_white_soldiers': 'LONG', 'three_black_crows': 'SHORT',
    }

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    # --- per-bar pattern predicates (D-026 anchor scan) ----------------------

    def _hammer(self, i: int, bar: tuple) -> bool:
        if i < 1:
            return False
        _e, o, h, l, c, _f, _s = bar
        _pe, po, _ph, _pl, pc, _pf, _ps = self._hist[i - 1]
        body = _body(o, c)
        if body <= 0 or not (c > o):
            return False
        if _body_ratio(o, h, l, c) > BODY_RATIO_MAX:
            return False
        if _lower_shadow(o, l, c) < SHADOW_MIN_MULT * body:
            return False
        if _upper_shadow(o, h, c) > body:
            return False
        return pc < po                      # after a down bar (decline context)

    def _shooting_star(self, i: int, bar: tuple) -> bool:
        if i < 1:
            return False
        _e, o, h, l, c, _f, _s = bar
        _pe, po, _ph, _pl, pc, _pf, _ps = self._hist[i - 1]
        body = _body(o, c)
        if body <= 0 or not (c < o):
            return False
        if _body_ratio(o, h, l, c) > BODY_RATIO_MAX:
            return False
        if _upper_shadow(o, h, c) < SHADOW_MIN_MULT * body:
            return False
        if _lower_shadow(o, l, c) > body:
            return False
        return pc > po                      # after an up bar (rally context)

    def _bullish_engulfing(self, i: int, bar: tuple) -> bool:
        if i < 1:
            return False
        _e, o, _h, _l, c, _f, _s = bar
        _pe, po, _ph, _pl, pc, _pf, _ps = self._hist[i - 1]
        return pc < po and c > o and o <= pc and c >= po

    def _bearish_engulfing(self, i: int, bar: tuple) -> bool:
        if i < 1:
            return False
        _e, o, _h, _l, c, _f, _s = bar
        _pe, po, _ph, _pl, pc, _pf, _ps = self._hist[i - 1]
        return pc > po and c < o and o >= pc and c <= po

    def _harami(self, i: int, bar: tuple) -> bool:
        if i < 1:
            return False
        _e, o, _h, _l, c, _f, _s = bar
        pe, po, ph, pl, pc, _pf, _ps = self._hist[i - 1]
        body = _body(o, c)
        rng_prev = ph - pl
        if body <= 0 or rng_prev <= 0:
            return False
        # Second body no larger than 1/4-1/3 of the first bar's range
        # (Ch14.2 p570) and fully nested inside the first body.
        if body > BODY_RATIO_MAX * rng_prev:
            return False
        lo_prev, hi_prev = min(po, pc), max(po, pc)
        if not (lo_prev < o and c < hi_prev):
            return False
        if self.variant_id == 'bullish_harami':
            return pc < po and c > o
        return pc > po and c < o

    def _three_soldiers(self, i: int, bar: tuple) -> bool:
        if i < 3:
            return False
        for j in (i - 2, i - 1, i):
            _e, o, h, _l, c, _f, _s = self._hist[j]
            if not (c > o):
                return False
            body = _body(o, c)
            if body <= 0 or _upper_shadow(o, h, c) > body:
                return False
        c2 = float(self._hist[i - 2][4])
        c1 = float(self._hist[i - 1][4])
        c0 = float(self._hist[i][4])
        if not (c2 < c1 < c0):
            return False
        # Trigger: the third candle must close above the SECOND candle's high
        # (Ch14.2 p556).
        if not (c0 > float(self._hist[i - 1][2])):
            return False
        pe, po, _ph, _pl, pc, _pf, _ps = self._hist[i - 3]
        return pc < po                      # after a decline

    def _three_crows(self, i: int, bar: tuple) -> bool:
        if i < 3:
            return False
        for j in (i - 2, i - 1, i):
            _e, o, _h, l, c, _f, _s = self._hist[j]
            if not (c < o):
                return False
            body = _body(o, c)
            if body <= 0 or _lower_shadow(o, l, c) > body:
                return False
        c2 = float(self._hist[i - 2][4])
        c1 = float(self._hist[i - 1][4])
        c0 = float(self._hist[i][4])
        if not (c2 > c1 > c0):
            return False
        if not (c0 < float(self._hist[i - 1][3])):
            return False
        pe, po, _ph, _pl, pc, _pf, _ps = self._hist[i - 3]
        return pc > po                      # after a rally

    def _pred(self, i: int, bar: tuple) -> bool:
        """The configured variant's per-bar predicate (anchor scan)."""
        return {
            'hammer': self._hammer,
            'shooting_star': self._shooting_star,
            'bullish_engulfing': self._bullish_engulfing,
            'bearish_engulfing': self._bearish_engulfing,
            'bullish_harami': self._harami,
            'bearish_harami': self._harami,
            'three_white_soldiers': self._three_soldiers,
            'three_black_crows': self._three_crows,
        }[self.variant_id](i, bar)

    def _stop_trigger(self, i: int) -> tuple[float, float]:
        """(stop_price, trigger_price) for the pattern completing on bar i.
        The stop is the book's pattern extreme; the trigger is the book's
        close-confirmation level (Ch14.2 p556)."""
        h = self._hist
        return {
            'hammer': (float(h[i][3]), float(h[i][2])),
            'shooting_star': (float(h[i][2]), float(h[i - 1][3])),
            'bullish_engulfing': (float(h[i][3]), float(h[i][2])),
            'bearish_engulfing': (float(h[i][2]), float(h[i][3])),
            'bullish_harami': (float(h[i - 1][3]), float(h[i - 1][2])),
            'bearish_harami': (float(h[i - 1][2]), float(h[i - 1][3])),
            'three_white_soldiers': (float(h[i - 2][3]), float(h[i - 1][2])),
            'three_black_crows': (float(h[i - 2][2]), float(h[i - 1][3])),
        }[self.variant_id]

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.real_body', f'{sym}.body_range_ratio',
                f'{sym}.upper_shadow', f'{sym}.lower_shadow',
                f'{sym}.close_position']
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
        n = len(self._hist)
        if not self._pred(n - 1, self._hist[n - 1]):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        stop_price, trigger_price = self._stop_trigger(n - 1)
        direction = self._DIRECTION[self.variant_id]
        if direction == 'LONG':
            stop_r = (close - stop_price) / atr
            prior_low_ref = stop_price
        else:
            stop_r = (stop_price - close) / atr
            prior_high_ref = stop_price
        if stop_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(self._hist, self._pred)
        geometry = {'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                    'stop_r': stop_r, 'expiry_bars': 8, 'atr_ref': atr,
                    'variant': self.variant_id,
                    'stop_ref': stop_price, 'trigger_ref': trigger_price}
        if direction == 'LONG':
            geometry['prior_low_ref'] = prior_low_ref
        else:
            geometry['prior_high_ref'] = prior_high_ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=(f'{sym}:{self.variant_id}:{close:.6f}:'
                               f'{stop_price:.6f}:{trigger_price:.6f}'),
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the reversal's close confirmation holds": a close
        back through the frozen trigger says the follow-through failed. The
        trigger is FROZEN at detection (the prior_high_ref pattern) — a live
        extreme drifts and the thesis never dies on a re-cross."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True          # unobservable: fail open, price still governs
        ref = draft.risk_geometry.get('trigger_ref')
        if ref is None:
            return True
        if draft.direction == 'LONG':
            return float(close.value) > float(ref)
        return float(close.value) < float(ref)
