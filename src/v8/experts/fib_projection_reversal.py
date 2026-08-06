"""Fibonacci projection reversal behavior family (`fib_projection_reversal`).

Hypothesis (Ch10.15 p400-401, Fig10.51; Ch10.20-10.21): after an intact
impulse, price that extends into a measured Fibonacci extension/projection of
the impulse range and then REJECTS the level by a close is a reversal setup.
The book's worked setup is a short at the 161.8% projection of an up-impulse
(the "initial stop just below the 161.8% projection level" applies to the
mirror long at a down-impulse projection). Detected on closed bars only.

The projection level set is `{sym}.fib_levels`, a self-describing tuple
(anchor_price, direction, retracements, extensions) anchored on the most
recent CONFIRMED swing pair (G-24); extensions continue the impulse beyond
the anchor (Ch10.4-10.7). The area-of-application invariant (Ch10.11 p394)
holds by construction: the anchor is a past confirmed swing, and its flank
window has closed before the extension can be tested, so the level set is
stable while price extends toward it (a NEW confirmed extreme re-anchors the
set — a new setup, D-026 fresh-anchor semantics).

Trigger: a bar whose extreme reaches the variant's extension level (high >=
level for an up-impulse, low <= level for a down-impulse) and whose close
rejects it (close below / above the level) — "price tests a measured
projection level ... then reverse", with the close-based confirmation the
book's trigger doctrine requires (Ch14.2). Entry on the NEXT_BAR_CLOSE.

The projection level is the invalidation reference: a close THROUGH it in the
extension direction means the extension continued, not reversed. It is frozen
into the draft geometry as prior_low_ref / prior_high_ref (the `prior_*_ref`
pattern, D-042), excluded from the episode-key geometry.

Risk geometry deviation (documented): the book's stop/target are PRICE LEVELS
(the projection level and the next retracement cluster); V8's canonical
simulator expresses stops/targets as fixed R-multiples of a declared risk unit
(D-028), and a data-derived stop_r would break episode-key stability (D-026).
The projection level is therefore frozen as the prior_*_ref used by still_valid
and the pre-entry invalidation, while the structural geometry is the family
default 1R:1R:8bar with atr_ref — the registered-pilots pattern.

Rule-13 discipline: extension-ratio and direction changes are VARIANTS of this
one behavior family (which shares mechanism fib_level_reaction with
fib_retracement_continuation); variants_evaluated lists every extension-ratio
variant implemented and tested (D-044). The book's confluence overlay for the
reversal (MACD divergence, channel support) is optional strengthening, not a
hard precondition — the confluence-based variants b/c of the book card are
represented here as the declared extension-ratio grid rather than calibrated
confluence thresholds (in-sample calibration is forbidden, CRITIC 2.3).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class FibProjectionReversalExpert(Expert):
    """Reversal at a measured Fibonacci extension level, rejected by a close."""
    expert_id = 'fib_projection_reversal'
    version = 'v1'
    mechanism_family_id = 'fib_level_reaction'
    behavior_family_id = 'fib_projection_reversal'
    variant_id = 'a'
    requires = ('location', 'volatility', 'history')
    # D-044: every extension-ratio variant implemented and tested in
    # tests/test_expert_fib_projection_reversal.py.
    variants_evaluated = ['a', 'b', 'c']
    # D-046: 3 extension ratios x 2 direction-sign choices, frozen in code.
    search_universe_size = 6
    _RATIO = {'a': 1.618, 'b': 1.272, 'c': 2.618}

    @staticmethod
    def _extension_level(fibs: tuple, ratio: float):
        """The extension level for `ratio` from the self-describing fib tuple
        (anchor, direction, retr, ext); None when absent."""
        if not isinstance(fibs, tuple) or len(fibs) != 4:
            return None
        for r, level in fibs[3]:
            if abs(r - ratio) < 1e-9:
                return float(level)
        return None

    def _short_pred(self, i: int, bar: tuple) -> bool:
        """Bar i tested the upside projection level (high >= level) and
        rejected it by the close (close < level) — reversal of an up-impulse
        extension."""
        if i == 0:
            return False
        _e, _o, high, _l, close, _f, _s = bar
        return high >= self._level and close < self._level

    def _long_pred(self, i: int, bar: tuple) -> bool:
        """Mirror: price tested the downside projection level and closed back
        above it — reversal of a down-impulse extension."""
        if i == 0:
            return False
        _e, _o, _h, low, close, _f, _s = bar
        return low <= self._level and close > self._level

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.fib_levels', f'{sym}.swing_high_10',
                f'{sym}.swing_low_10']
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
        # Swing-lattice consistency guard (same as fib_retracement_continuation).
        swh = f[f'{sym}.swing_high_10'].value
        swl = f[f'{sym}.swing_low_10'].value
        if swh and swl and swh > 0.0 and swl > 0.0 and not (swh > swl):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        anchor_price, direction, _retr, _ext = fibs
        if direction not in (1.0, -1.0) or anchor_price <= 0.0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        level = self._extension_level(fibs, self._RATIO[self.variant_id])
        if level is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        # An up-impulse (direction +1) extension overshoots to the UPSIDE ->
        # short the overextension; a down-impulse (-1) extension overshoots to
        # the DOWNSIDE -> long the overextension. "Trend in effect" is the
        # impulse itself: the measured projection is only meaningful against an
        # intact, confirmed impulse (the anchor direction); the projection
        # level frozen into the geometry is the invalidation reference.
        if direction == 1.0:
            direction_sig = 'SHORT'
            pred = self._short_pred
        else:
            direction_sig = 'LONG'
            pred = self._long_pred
        self._level = level
        hist = tuple(hist)
        if not pred(len(hist) - 1, hist[-1]):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(hist, pred)
        risk_geometry = {'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                         'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr}
        # The invalidation reference is FROZEN at detection: for a LONG reversal
        # a close BELOW the projection level means the downside extension
        # continued (not reversed); for a SHORT, a close above it.
        if direction_sig == 'LONG':
            risk_geometry['prior_low_ref'] = level
        else:
            risk_geometry['prior_high_ref'] = level
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
        """The thesis is "the measured projection was rejected; price reverses
        against the extension". A close THROUGH the frozen projection level in
        the extension direction says the extension continued after all, so the
        reversal has no premise (Ch10.16.3). Unobservable inputs fail open."""
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
