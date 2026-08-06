"""Open-interest / price divergence behavior family (`open_interest_divergence`).

Hypothesis (mechanism `positioning_divergence`): price, participation and
positioning agree or diverge directionally, and the divergence is tradable
(Ch6.1 p192-193, Ch9.9.6.4 p349). The book's four directional rules are
verbatim:
  a  all rising — price, volume and OI rising together -> buy;
  b  rising prices with declining OI and volume -> exit longs / bearish;
  c  declining market with OI and volume both rising -> go short;
  d  OI and volume declining together -> cover shorts.

The open_interest channel is NOT part of the declared tape (the derivatives
tape is a ROADMAP Phase 3 backlog; the registry entry is DATA_BLOCKED). When
`{sym}.open_interest` is absent the expert self-gates to NO_HABITAT; the logic
below is the full evaluation for when a tape carries the channel.

Documented deviations: (1) the state contract exposes the latest open_interest
value only — no OI series (marketstate.py emits the newest admissible OI row),
so the book's OI-DIRECTION term is unobservable. The positioning leg is read
from `long_short_skew` (G-43, carried in the OI channel payload): skew >= 1.0
is long-heavy positioning (the "OI rising" / longs-accumulating proxy) and
skew < 1.0 is short-heavy (the "OI declining" proxy). When the derivatives
tape carries an OI series this leg becomes the literal OI change; the variant
predicates are unchanged. (2) The price-direction leg is the close change over
LOOKBACK_N bars from the `history` window.

Variants (all frozen; D-044 lists every implemented variant):
  a  LONG when price up, volume up, positioning long-heavy ("all rising").
  b  SHORT when price up, volume down, positioning short-heavy (the book's
     "rising prices + declining OI/volume" exit-longs rule).
  c  SHORT when price down, volume up, positioning long-heavy.
  d  LONG when price down, volume down, positioning short-heavy ("cover
     shorts").
The book card's variants `e` (high OI -> faster reversal) and `f` (OI rising
through a consolidation) require an OI series and an OI-through-consolidation
reading; both are unexpressible in the state contract and are dropped before
evaluation (counted in search_universe_size).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, LOCKED constants (D-036 pattern). Price-direction lookback on the
# close series (declared; the book leaves the window unstated).
LOOKBACK_N = 5
# Positioning proxy threshold: long_short_skew >= 1.0 = long-heavy.
SKEW_LONG_HEAVY = 1.0


class OpenInterestDivergenceExpert(Expert):
    """OI/volume/price directional divergence (Ch6.1 p192-193)."""
    expert_id = 'open_interest_divergence'
    version = 'v1'
    mechanism_family_id = 'positioning_divergence'
    behavior_family_id = 'oi_price_divergence'
    variant_id = 'a'
    # D-044: every implemented variant, losers included. The book card lists
    # a..f; `e` and `f` need an OI series the state contract does not carry
    # (dropped before evaluation, counted in search_universe_size).
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 6
    requires = ('positioning', 'participation', 'volatility', 'history')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            self.variant_id = variant_id

    def _detect(self, close, closes, vol_zscore, skew):
        """Returns the direction for the current variant, or None."""
        if len(closes) < LOOKBACK_N + 1:
            return None
        price_up = close > closes[-1 - LOOKBACK_N]
        vol_up = vol_zscore > 0.0
        vol_down = vol_zscore < 0.0
        long_heavy = skew >= SKEW_LONG_HEAVY
        short_heavy = skew < SKEW_LONG_HEAVY
        if self.variant_id == 'a' and price_up and vol_up and long_heavy:
            return 'LONG'
        if self.variant_id == 'b' and price_up and vol_down and short_heavy:
            return 'SHORT'
        if self.variant_id == 'c' and not price_up and vol_up and long_heavy:
            return 'SHORT'
        if self.variant_id == 'd' and not price_up and vol_down and short_heavy:
            return 'LONG'
        return None

    def _anchor_pred(self, direction: str, closes: list):
        """Per-history-bar predicate: the price-direction leg (the run of
        closes agreeing with the direction). The participation/positioning
        legs are state readings (per-bar volume/OI are not in the history
        tuples), so the anchor captures the price run (D-026)."""
        if direction == 'LONG':
            def pred(i, _bar):
                if i < LOOKBACK_N:
                    return False
                return float(closes[i]) > float(closes[i - LOOKBACK_N])
            return pred

        def pred(i, _bar):
            if i < LOOKBACK_N:
                return False
            return float(closes[i]) < float(closes[i - LOOKBACK_N])
        return pred

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: unknown variant {self.variant_id!r} '
                f'(variants_evaluated={list(self.variants_evaluated)})')
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.open_interest', f'{sym}.long_short_skew',
                f'{sym}.vol_zscore']
        if not self._need(state, need):
            # open_interest absent -> DATA_BLOCKED on the declared tape; the
            # self-gate is a NO_HABITAT, never a fabricated positioning read.
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        hist_value = f[f'{sym}.history'].value
        skew = f[f'{sym}.long_short_skew'].value
        vol_zscore = f[f'{sym}.vol_zscore'].value
        if atr is None or atr <= 0 or not isinstance(hist_value, (tuple, list)) \
                or not hist_value or skew is None or vol_zscore is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(hist_value)
        closes = [float(b[4]) for b in hist]
        direction = self._detect(close, closes, float(vol_zscore), float(skew))
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        # Stop behind the recent window extreme (the diverged barrier), frozen
        # at detection (Ch6.1; the divergence family has no book numeric stop).
        # The window INCLUDES the current bar so a fade setup (close beyond
        # the prior extreme — e.g. variant b short at a new high) keeps a
        # non-degenerate stop beyond the current bar's own extreme.
        if direction == 'LONG':
            lows = [float(b[3]) for b in hist]
            low_ref = min(lows[-LOOKBACK_N:])
            stop_r = (close - low_ref) / float(atr)
            prior_low_ref = low_ref
            prior_high_ref = None
        else:
            highs = [float(b[2]) for b in hist]
            high_ref = max(highs[-LOOKBACK_N:])
            stop_r = (high_ref - close) / float(atr)
            prior_low_ref = None
            prior_high_ref = high_ref
        if stop_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._anchor_pred(direction, closes)
        anchor = self.find_setup_anchor(hist, pred)
        geometry = {
            'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0, 'stop_r': stop_r,
            'expiry_bars': 8, 'atr_ref': float(atr), 'variant': self.variant_id,
        }
        if prior_low_ref is not None:
            geometry['prior_low_ref'] = prior_low_ref
        if prior_high_ref is not None:
            geometry['prior_high_ref'] = prior_high_ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction}:{close:.6f}',
            risk_geometry=geometry, birth_time=t,
            setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the divergence persists": a long must hold the
        frozen recent low, a short the frozen recent high. A close through the
        reference says the divergence resolved in price and the setup is dead.
        Fails open when the close is unobservable."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        close = float(close.value)
        if draft.direction == 'LONG':
            ref = draft.risk_geometry.get('prior_low_ref')
            if ref is None:
                return True
            return close > float(ref)
        ref = draft.risk_geometry.get('prior_high_ref')
        if ref is None:
            return True
        return close < float(ref)
