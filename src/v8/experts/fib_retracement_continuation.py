"""Fibonacci retracement continuation behavior family (`fib_retracement_continuation`).

Hypothesis (Ch10.4-10.7, Ch10.14): inside an intact impulse, a pullback that
reaches a Fibonacci retracement level of the prior impulse range and is then
reclaimed by a close is a continuation setup. Detected on closed bars only;
the direction follows the impulse (LONG after an up-impulse retracement
reclaim, SHORT after a down-impulse retracement reclaim).

The retracement level set is `{sym}.fib_levels`, a self-describing tuple
(anchor_price, direction, retracements, extensions) anchored on the most
recent CONFIRMED swing pair (G-24). The area-of-application invariant
(Ch10.11 p394: levels are valid only after the anchor bar) holds by
construction: the anchor is always a past confirmed swing, so the levels are
only ever applied forward of it.

The deepest retracement (78.6%) is the invalidation reference: a close beyond
it is a deep correction — "the deeper the correction, the lower the
probability of trend resumption" (Ch10.14) — and the level set no longer
applies. It is frozen into the draft geometry as prior_low_ref / prior_high_ref
(the `prior_*_ref` pattern, D-042), excluded from the episode-key geometry.

Risk geometry deviation (documented): the book's stop ("just below the 78.6%
level") and target ("1:1 projection of the impulse range") are PRICE LEVELS.
V8's canonical simulator expresses stops/targets as fixed R-multiples of a
declared risk unit (D-028), and a data-derived stop_r would break episode-key
stability (D-026) by hashing differently across decision clocks. The levels
are therefore frozen as the prior_*_ref used by still_valid and the pre-entry
invalidation, while the structural geometry is the family default 1R:1R:8bar
with atr_ref — exactly how the registered pilots carry their book level rules
(failed_breakout's prior_high_ref).

Rule-13 discipline: retracement-ratio and direction changes are VARIANTS of
this one behavior family, never separate Experts; variants_evaluated lists
every ratio variant implemented and tested (D-044).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Retracement ratios of the prior impulse range (G-24, verbatim from the book).
FIB_RETRACEMENTS = (0.236, 0.382, 0.5, 0.618, 0.786)
# The deepest retracement: the invalidation / stop reference level.
DEEP_RETRACEMENT = 0.786


class FibRetracementContinuationExpert(Expert):
    """Pullback to a retracement level reclaimed by a close, in the direction
    of the intact impulse."""
    expert_id = 'fib_retracement_continuation'
    version = 'v1'
    mechanism_family_id = 'fib_level_reaction'
    behavior_family_id = 'fib_retracement_continuation'
    variant_id = 'a'
    requires = ('location', 'volatility', 'history')
    # D-044: every retracement-ratio variant implemented and tested in
    # tests/test_expert_fib_retracement_continuation.py.
    variants_evaluated = ['a', 'b', 'c', 'd', 'e']
    # D-046: the search consumed 5 retracement ratios x 2 direction-sign
    # choices. Every threshold was frozen in code against crafted tapes before
    # any real window existed; nothing was tuned on data.
    search_universe_size = 10
    _RATIO = {'a': 0.382, 'b': 0.5, 'c': 0.618, 'd': 0.236, 'e': 0.786}

    @staticmethod
    def _retracement_level(fibs: tuple, ratio: float):
        """The retracement level for `ratio` from the self-describing fib
        tuple (anchor, direction, retr, ext); None when absent."""
        if not isinstance(fibs, tuple) or len(fibs) != 4:
            return None
        for r, level in fibs[2]:
            if abs(r - ratio) < 1e-9:
                return float(level)
        return None

    def _long_pred(self, i: int, bar: tuple) -> bool:
        """Bar i reached the retracement level (low <= level) and reclaimed it
        by the close (close > level) — the pullback-reclaim of an up-impulse."""
        if i == 0:
            return False
        _e, _o, _h, low, close, _f, _s = bar
        return close > self._level and low <= self._level

    def _short_pred(self, i: int, bar: tuple) -> bool:
        """Mirror: price rose to the retracement level and closed back below it."""
        if i == 0:
            return False
        _e, _o, high, _l, close, _f, _s = bar
        return close < self._level and high >= self._level

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.fib_levels']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        fibs = f[f'{sym}.fib_levels'].value
        hist = f[f'{sym}.history'].value
        if atr is None or not isinstance(fibs, tuple) or len(fibs) != 4 \
                or not isinstance(hist, (tuple, list)) or not hist:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        # The fib anchor's own consistency is the guard: `_fib_levels` returns
        # None when the confirmed swing pair is degenerate, and the level set
        # is checked below. The significance-filtered swing_high_10/
        # swing_low_10 features are a DIFFERENT pair (CRIT-1 range filter) than
        # the unfiltered confirmed swings the anchor uses — gating on them
        # vetoed states with a valid anchor and NO_HABITAT'd states where the
        # filtered pair was absent entirely.
        anchor_price, direction, _retr, _ext = fibs
        if direction not in (1.0, -1.0) or anchor_price <= 0.0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        level = self._retracement_level(fibs, self._RATIO[self.variant_id])
        deep = self._retracement_level(fibs, DEEP_RETRACEMENT)
        if level is None or deep is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        # LONG on an up-impulse (direction +1), SHORT on a down-impulse (-1).
        # "Trend in effect" is the intact IMPULSE itself: the anchor direction
        # is the trend, and the 78.6% depth gate below (frozen as the
        # prior_*_ref) is the "impulse still intact" check — a short/long EMA
        # cross would fight the family's own structure (a deep pullback
        # naturally puts EMA5 below EMA20 while the impulse is fine).
        if direction == 1.0:
            direction_sig = 'LONG'
            pred = self._long_pred
        else:
            direction_sig = 'SHORT'
            pred = self._short_pred
        self._level = level
        hist = tuple(hist)
        if not pred(len(hist) - 1, hist[-1]):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(hist, pred)
        risk_geometry = self.declared_geometry()
        risk_geometry['atr_ref'] = atr
        # The invalidation reference is FROZEN at detection (the `prior_*_ref`
        # pattern, D-042): a live-recomputed deep level would drift with the
        # adverse move and the dead-thesis close would never fire.
        if direction_sig == 'LONG':
            risk_geometry['prior_low_ref'] = deep
        else:
            risk_geometry['prior_high_ref'] = deep
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction_sig,
            setup_fingerprint=f'{sym}:{self._RATIO[self.variant_id]:.3f}:'
                              f'{level:.6f}:{direction_sig}',
            risk_geometry=risk_geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the pullback reclaimed its retracement level and the
        impulse continues". A close beyond the deepest retracement (78.6%) is a
        deep correction — the impulse is no longer intact, so the reason to hold
        is gone whatever the stop distance still says (Ch10.14; E-12
        INVALIDATION). Uses the FROZEN detection-time level, not the live one.
        Unobservable inputs fail open (an unreadable thesis is not a dead one)."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        if draft.direction == 'LONG':
            ref = draft.risk_geometry.get('prior_low_ref')
            if ref is None:
                return True
            return float(close.value) > float(ref)
        ref = draft.risk_geometry.get('prior_high_ref')
        if ref is None:
            return True
        return float(close.value) < float(ref)
