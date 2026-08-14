"""Funding-extreme crowding reversal behavior family
(`funding_crowding_reversal`).

Hypothesis (mechanism `positioning_divergence`): extreme funding marks a
crowded positioning, and the contrary doctrine applies — extreme bullishness
is potentially bearish, extreme bearishness potentially bullish (Ch9.9.6.4
p349, Ch23.3 p784-788); a position is only initiated upon PRICE CONFIRMATION
(the book's explicit gate: "participants should only initiate short positions
or exit profitable longs upon price confirmation").

The funding channel is absent on the declared tape (derivatives tape is a
ROADMAP Phase 3 backlog). When `{sym}.funding_rate` is absent the expert
self-gates to NO_HABITAT; the logic below is the full evaluation for when a
tape carries the channel.

The funding-extreme thresholds are DECLARED numeric literals, not fitted:
+0.001 (extreme positive -> crowded long) and -0.001 (extreme negative ->
crowded short) — fixed pre-holdout (CRIT-9: the card's "p95 quantile of the
distribution" was rejected as in-sample calibration; HAND_EXPERTS 2.3).

Variants (all frozen; D-044 lists every implemented variant):
  a  crowded-long reversal: funding >= +0.001 and price confirms by closing
     below the prior CONFIRM_N-bar low -> SHORT (reversion from the top).
  b  crowded-short reversal: funding <= -0.001 and price confirms by closing
     above the prior CONFIRM_N-bar high -> LONG (reversion from the bottom).
  c  funding + OI crowding confluence: variant a/b gated additionally on the
     open_interest channel being present (OI is the crowding witness; G-42).
  d  funding-extreme exhaustion: funding at the extreme while price makes a
     new EXTEND_N-bar extreme in the same direction -> the move is exhausted
     (price extended against the crowd), reversal SHORT / LONG.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, LOCKED thresholds (CRIT-9: numeric literals, never a fitted
# quantile). One pip of the funding rate on perp notional is the crowd line.
FUNDING_EXTREME_POS = 0.001
FUNDING_EXTREME_NEG = -0.001
# Price-confirmation lookbacks (declared): the barrier broken (a/c) and the
# extension window (d).
CONFIRM_N = 5
EXTEND_N = 10


class FundingCrowdingReversalExpert(Expert):
    """Extreme-funding contrary reversal with price confirmation."""
    expert_id = 'funding_crowding_reversal'
    version = 'v1'
    mechanism_family_id = 'positioning_divergence'
    behavior_family_id = 'funding_crowding_reversal'
    variant_id = 'a'
    # stop_r is structural: the distance to the frozen pre-flush extreme in R
    # (D-028), computed in evaluate(); target_r stays the family 1:1 default.
    stop_r = None
    # D-044: every implemented variant, losers included; all four book
    # variants implemented (a..d), so the search universe equals the retained
    # set.
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 4
    requires = ('positioning', 'volatility', 'history')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            self.variant_id = variant_id

    def _leg(self, close, closes, highs, lows, need_oi, oi_present, funding):
        """Directional leg for the current variant; None when the setup does
        not hold. price-confirmation legs match the anchor predicate."""
        n = len(closes)
        if n < EXTEND_N + 1:
            return None
        if need_oi and not oi_present:
            return None
        if funding >= FUNDING_EXTREME_POS:
            if self.variant_id in ('a', 'c') and n >= CONFIRM_N + 1 \
                    and close < min(lows[-1 - CONFIRM_N:-1]):
                return 'SHORT'
            if self.variant_id == 'd' \
                    and close > max(highs[-1 - EXTEND_N:-1]):
                return 'SHORT'
        if funding <= FUNDING_EXTREME_NEG:
            if self.variant_id in ('b', 'c') and n >= CONFIRM_N + 1 \
                    and close > max(highs[-1 - CONFIRM_N:-1]):
                return 'LONG'
            if self.variant_id == 'd' \
                    and close < min(lows[-1 - EXTEND_N:-1]):
                return 'LONG'
        return None

    def _anchor_pred(self, direction, highs, lows):
        """Per-history-bar predicate: the price-confirmation leg of the
        setup. The funding leg is a state reading (per-bar funding is not in
        the history tuples), so the anchor captures the price-confirmation run
        (D-026)."""
        if self.variant_id == 'd':
            if direction == 'SHORT':
                return (lambda i, _b: i >= EXTEND_N
                        and float(highs[i]) > max(highs[i - EXTEND_N:i]))
            return (lambda i, _b: i >= EXTEND_N
                    and float(lows[i]) < min(lows[i - EXTEND_N:i]))
        if direction == 'SHORT':
            return (lambda i, _b: i >= CONFIRM_N
                    and float(lows[i]) < min(lows[i - CONFIRM_N:i]))
        return (lambda i, _b: i >= CONFIRM_N
                and float(highs[i]) > max(highs[i - CONFIRM_N:i]))

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: unknown variant {self.variant_id!r} '
                f'(variants_evaluated={list(self.variants_evaluated)})')
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.funding_rate']
        if self.variant_id == 'c':
            # The OI confluence leg is a data gate: absent open_interest is a
            # DATA absence (NO_HABITAT), never a NO_SETUP.
            need.append(f'{sym}.open_interest')
        if not self._need(state, need):
            # funding_rate absent -> DATA_BLOCKED on the declared tape; the
            # self-gate is a NO_HABITAT, never a fabricated sentiment read.
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        hist_value = f[f'{sym}.history'].value
        funding = f[f'{sym}.funding_rate'].value
        if atr is None or atr <= 0 or not isinstance(hist_value, (tuple, list)) \
                or not hist_value or funding is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        funding = float(funding)
        hist = tuple(hist_value)
        closes = [float(b[4]) for b in hist]
        highs = [float(b[2]) for b in hist]
        lows = [float(b[3]) for b in hist]
        oi_present = f.get(f'{sym}.open_interest') is not None \
            and f[f'{sym}.open_interest'].value is not None
        direction = self._leg(close, closes, highs, lows,
                              self.variant_id == 'c', oi_present, funding)
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        # Stop beyond the confirmation barrier (countertrend stop doctrine,
        # Ch9.9.3.2): the frozen recent extreme for a/b/c; one ATR beyond the
        # extended extreme for d (the extreme is at/above the close, so the
        # bare barrier would be a degenerate zero-distance stop).
        if direction == 'SHORT':
            if self.variant_id == 'd':
                barrier = max(highs[-EXTEND_N:])
                prior_high_ref = barrier
                stop_r = (barrier + float(atr) - close) / float(atr)
            else:
                barrier = max(highs[-1 - CONFIRM_N:-1])
                prior_high_ref = barrier
                stop_r = (barrier - close) / float(atr)
        else:
            if self.variant_id == 'd':
                barrier = min(lows[-EXTEND_N:])
                prior_low_ref = barrier
                stop_r = (close - (barrier - float(atr))) / float(atr)
            else:
                barrier = min(lows[-1 - CONFIRM_N:-1])
                prior_low_ref = barrier
                stop_r = (close - barrier) / float(atr)
        if stop_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._anchor_pred(direction, highs, lows)
        anchor = self.find_setup_anchor(hist, pred)
        geometry = self.declared_geometry()
        geometry.update({'stop_r': stop_r, 'atr_ref': float(atr),
                         'variant': self.variant_id})
        if direction == 'SHORT':
            geometry['prior_high_ref'] = prior_high_ref
        else:
            geometry['prior_low_ref'] = prior_low_ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction}:{close:.6f}',
            risk_geometry=geometry, birth_time=t,
            setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the crowded extreme is reversing": a short must stay
        below the frozen confirmation barrier, a long above it. A close
        through the barrier says the crowd won and the reversal is dead. Fails
        open when the close is unobservable."""
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
