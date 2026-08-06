"""Floor-trader daily-pivot S/R reaction behavior family (`floor_trader_pivot`).

Hypothesis (mechanism `pivot_level_reaction`; Ch8.7 p263-265, Ch10.13): the
daily pivot level set (PP/S1..S4/R1..R4 from the prior period's OHLC) is a
time-static support/resistance ladder, and a close-confirmed reaction at a
level is a directional entry. Detected on closed bars only; entry is
NEXT_BAR_CLOSE; confirmation is close-based (Ch14.2).

Variants (D-044; the card's variant e — pivot levels as TARGETS — is folded
into the target ladder of a-d, not a separate entry):
  a  PP drift rule (Ch8.7 p264): open above PP and close up -> LONG drift
     (target R1); open below PP and close down -> SHORT (target S1).
  b  S1/R1 range-day reaction: a pullback to S1 that closes back above it
     (LONG, target PP) / a rally to R1 that closes back below it (SHORT).
  c  S2/R2 violation = strong trend (Ch8.7 p264): a close beyond the second
     support/resistance is continuation -> SHORT below S2 (target S3) /
     LONG above R2 (target R3).
  d  S3/R3 extreme reversion: a close beyond the third level that reclaims
     it is an extreme overbought/oversold fade -> LONG reclaim above S3
     (target S2) / SHORT reclaim below R3 (target R2).

Stop: beyond the level being traded (behind the pivot line, Ch8.7 doctrine).
Target: the next level on the ladder (the level set IS the target ladder,
Ch8.7 p263-265). Targets/stops are price distances expressed in R with the
14-bar ATR unit (D-028).

The level set is FROZEN at detection and the anchor is restricted to the
current session: the pivot set is recomputed daily and a reaction in a later
day is a different setup (D-026: a new anchor event). `still_valid` keeps the
thesis alive while the close stays on the traded side of the frozen level.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class FloorTraderPivotExpert(Expert):
    """Daily-pivot level reaction expert."""
    expert_id = 'floor_trader_pivot'
    version = 'v1'
    mechanism_family_id = 'pivot_level_reaction'
    behavior_family_id = 'pivot_level_reaction'
    variant_id = 'a'
    # D-044: every implemented variant (losers included); the reported
    # variant_id is a member. D-046: all thresholds are declared constants
    # frozen pre-window, so the search universe equals the evaluated set.
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 4
    requires = ('location', 'volatility', 'history', 'session')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    def _detect(self, f: dict, n: int) -> tuple | None:
        """(direction, level_ref, stop_price, target_price, anchor_pred) for
        the configured variant on the current bar; None = no reaction."""
        ppv = f[f'{self._sym}.pivot_points_day'].value
        PP, R1, R2, R3, _R4, S1, S2, S3, _S4 = (float(v) for v in ppv)
        o = float(self._hist[n - 1][1])
        h = float(self._hist[n - 1][2])
        l = float(self._hist[n - 1][3])
        c = float(self._hist[n - 1][4])
        # The anchor is restricted to the current session: the level set is
        # recomputed every day, so a reaction in a later day is a new setup
        # (D-026 anchor = the market event that created the setup).
        day_start = n - int(self._bar_of_session)
        v = self.variant_id
        if v == 'a':
            if o > PP and c > o:
                pred = lambda j, bar: j >= day_start \
                    and float(bar[1]) > PP and float(bar[4]) > float(bar[1])
                return 'LONG', PP, PP, R1, pred
            if o < PP and c < o:
                pred = lambda j, bar: j >= day_start \
                    and float(bar[1]) < PP and float(bar[4]) < float(bar[1])
                return 'SHORT', PP, PP, S1, pred
        elif v == 'b':
            if l <= S1 and c > S1:
                pred = lambda j, bar: j >= day_start \
                    and float(bar[3]) <= S1 and float(bar[4]) > S1
                return 'LONG', S1, S1, PP, pred
            if h >= R1 and c < R1:
                pred = lambda j, bar: j >= day_start \
                    and float(bar[2]) >= R1 and float(bar[4]) < R1
                return 'SHORT', R1, R1, PP, pred
        elif v == 'c':
            if c > R2:
                pred = lambda j, bar: j >= day_start and float(bar[4]) > R2
                return 'LONG', R2, R2, R3, pred
            if c < S2:
                pred = lambda j, bar: j >= day_start and float(bar[4]) < S2
                return 'SHORT', S2, S2, S3, pred
        else:  # 'd' — S3/R3 extreme reversion
            if l <= S3 and c > S3:
                pred = lambda j, bar: j >= day_start \
                    and float(bar[3]) <= S3 and float(bar[4]) > S3
                return 'LONG', S3, S3, S2, pred
            if h >= R3 and c < R3:
                pred = lambda j, bar: j >= day_start \
                    and float(bar[2]) >= R3 and float(bar[4]) < R3
                return 'SHORT', R3, R3, R2, pred
        return None

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.pivot_points_day', f'{sym}.bar_of_session']
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
        self._sym = sym
        self._bar_of_session = float(f[f'{sym}.bar_of_session'].value)
        n = len(self._hist)
        if n < 2:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hit = self._detect(f, n)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, level, stop_price, target_price, pred = hit
        if direction == 'LONG':
            stop_r = (close - stop_price) / atr
            target_r = (target_price - close) / atr
        else:
            stop_r = (stop_price - close) / atr
            target_r = (close - target_price) / atr
        if stop_r <= 0 or target_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(self._hist, pred)
        geometry = {'entry': 'NEXT_BAR_CLOSE', 'target_r': target_r,
                    'stop_r': stop_r, 'expiry_bars': 8, 'atr_ref': atr,
                    'variant': self.variant_id,
                    'level_ref': level, 'stop_ref': stop_price}
        if direction == 'LONG':
            geometry['prior_low_ref'] = stop_price
        else:
            geometry['prior_high_ref'] = stop_price
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=(f'{sym}:{self.variant_id}:{direction}:'
                               f'{close:.6f}:{level:.6f}:{stop_price:.6f}'),
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the reaction holds on the traded side of the level":
        a close back through the FROZEN level says the reaction failed (role
        reversal applies, Ch8.7)."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True          # unobservable: fail open, price still governs
        ref = draft.risk_geometry.get('level_ref')
        if ref is None:
            return True
        if draft.direction == 'LONG':
            return float(close.value) > float(ref)
        return float(close.value) < float(ref)
