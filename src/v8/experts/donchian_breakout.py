"""N-bar price-channel breakout behavior family (`donchian_breakout`, E-10).

Hypothesis (mechanism `channel_breakout`): a close beyond the trailing
N-bar price channel (Donchian channel) is a continuation entry — the
book's Turtle framing (Ch12 p485-489). Long when a close exceeds the
N-bar high, short when a close falls below the N-bar low (variant a is
long-only by card). The channel reference is the windowed extreme of the
bars BEFORE the current bar (the G-22 window_high/window_low feature
formula), so a breakout is detectable on the closed bar.

Variants (rule 13 — one family, parameter/geometry changes only):
  a  N=20 unidirectional, long only on upside breakout
  b  N=20 bidirectional (SAR: the opposite N-extreme is a new setup)
  c  N=10
  d  N=55, implemented on the nearest DECLARED 50-bar window
     (window_high_50/window_low_50, G-22): the 32-bar `history` pin
     (O-020) cannot host a 55-bar anchor scan, so the gate reference is
     the 50-bar channel feature and the anchor scan falls back to the
     windowed bound (documented deviation).
  e  N=20 entry with the responsive-band exit (band N=5)
  f  N=20 entry with the 2-3 bar significant-extreme exit (extreme N=3)

STOP_RULE (book, Ch12 p486): "long: stop just below the lower band;
short: stop just above the upper band." The stop distance is the frozen
channel band in R (D-028): stop_r = (close - lower_band) / atr_ref for a
long, (upper_band - close) / atr_ref for a short. The book's
"riskless-re-entry" rule is O-013-adjacent position management and is
NOT implemented.

TARGET_RULE: none in the book ("allow risk-free positions to run" — the
channel exit is the profit-taking mechanism), so the family uses the
declared 1R:1R:8bar fallback geometry with the atr_ref unit; the live
channel acts as the post-entry thesis (still_valid), not the target.

INVALIDATION_RULE: stop, or the opposite-channel flip (a new N-extreme
in the other direction). still_valid holds while the close stays on the
entry side of the LIVE channel (the same window formula); a close back
through the live channel kills the thesis (THESIS_INVALIDATED). The
responsive / significant-extreme variants exit on a shorter live band
instead of the N-bar channel.

The book warns channels "perform very poorly in consolidations"
(Ch12 p485); the range-context guard (G-26) is left to a future variant
— this card implements the base channel family only.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# The family's variant ids (D-044: every variant evaluated, losers
# included). One id per implemented+tested configuration.
CHANNEL_N = ('a', 'b', 'c', 'd', 'e', 'f')
# Exit-band lookback for variant e (book: responsive exit bands N in {2..10}).
RESPONSIVE_EXIT_N = 5
# Exit-extreme lookback for variant f (book: "last 2-3 bar extreme").
SIGNIFICANT_EXTREME_N = 3


class DonchianBreakoutExpert(Expert):
    """N=20 unidirectional (long-only) price-channel breakout (variant a)."""
    expert_id = 'donchian_breakout'
    version = 'v1'
    mechanism_family_id = 'channel_breakout'
    behavior_family_id = 'channel_breakout'
    variant_id = 'a'
    variants_evaluated = CHANNEL_N
    search_universe_size = 6
    requires = ('location', 'volatility', 'history')
    # Variant parameters (book Ch12 p485-489, E-10 card).
    channel_n = 20
    long_only = True
    # 'channel' -> live N-bar channel exit; 'responsive' -> responsive band;
    # 'significant_extreme' -> 2-3 bar significant-extreme exit.
    exit_kind = 'channel'

    # --- per-history-bar channel references (windowed) -----------------------

    def _channel_high(self, i: int) -> float | None:
        start = max(0, i - self.channel_n)
        if i <= start:
            return None
        return max(self._highs[start:i])

    def _channel_low(self, i: int) -> float | None:
        start = max(0, i - self.channel_n)
        if i <= start:
            return None
        return min(self._lows[start:i])

    def _long_pred(self, i: int, bar: tuple) -> bool:
        """Bar i closed above the channel_n high of the bars before it."""
        hi = self._channel_high(i)
        return hi is not None and float(bar[4]) > hi

    def _short_pred(self, i: int, bar: tuple) -> bool:
        """Bar i closed below the channel_n low of the bars before it."""
        lo = self._channel_low(i)
        return lo is not None and float(bar[4]) < lo

    # --- evaluation -----------------------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        # D-044 fail-closed: a reported variant that was never implemented
        # must not evaluate as if it were a member of the family.
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: variant {self.variant_id!r} is not in '
                f'variants_evaluated {self.variants_evaluated!r} (D-044)')
        t = state.as_of
        sym = state.universe[0]
        n = self.channel_n
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.window_high_{n}', f'{sym}.window_low_{n}']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        window_high = float(f[f'{sym}.window_high_{n}'].value)
        window_low = float(f[f'{sym}.window_low_{n}'].value)
        hist_value = f[f'{sym}.history'].value
        if atr is None or not isinstance(hist_value, (tuple, list)) or not hist_value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = tuple(hist_value)
        self._highs = [float(b[2]) for b in self._hist]
        self._lows = [float(b[3]) for b in self._hist]
        # The gate reference IS the state feature (the same G-22 window
        # formula the anchor predicate mirrors), so the frozen risk geometry
        # and the state the test audits cannot drift.
        if self.long_only:
            direction = 'LONG' if close > window_high else None
        elif close > window_high:
            direction = 'LONG'
        elif close < window_low:
            direction = 'SHORT'
        else:
            direction = None
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._long_pred if direction == 'LONG' else self._short_pred
        anchor = self.find_setup_anchor(self._hist, pred)
        # Frozen channel band stop in R (D-028; book Ch12 p486): the stop is
        # the level the breakout left, so the exit geometry is declared at
        # detection and cannot drift with the market.
        if direction == 'LONG':
            stop_r = (close - window_low) / atr
        else:
            stop_r = (window_high - close) / atr
        geom = {'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0, 'expiry_bars': 8,
                'atr_ref': atr, 'prior_high_ref': window_high,
                'prior_low_ref': window_low, 'channel_n': n,
                'variant': self.variant_id, 'stop_r': stop_r}
        if self.exit_kind == 'responsive':
            geom['responsive_exit_n'] = RESPONSIVE_EXIT_N
        elif self.exit_kind == 'significant_extreme':
            geom['significant_extreme_n'] = SIGNIFICANT_EXTREME_N
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{direction}:{close:.6f}:'
                              f'{window_high:.6f}:{window_low:.6f}',
            risk_geometry=geom, birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """Post-entry thesis (D-029): the position holds while the close stays
        on the entry side of the LIVE channel — a close back through it says
        the breakout failed, whatever the stop distance still says. The
        responsive / significant-extreme variants exit on their shorter live
        band instead. Fails open when the channel inputs are unobservable."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        direction = draft.direction
        if self.exit_kind == 'channel':
            n = int(draft.risk_geometry.get('channel_n', self.channel_n))
            if direction == 'LONG':
                lo = f.get(f'{sym}.window_low_{n}')
                if lo is None or lo.value is None:
                    return True
                return float(close.value) > float(lo.value)
            hi = f.get(f'{sym}.window_high_{n}')
            if hi is None or hi.value is None:
                return True
            return float(close.value) < float(hi.value)
        m = (RESPONSIVE_EXIT_N if self.exit_kind == 'responsive'
             else SIGNIFICANT_EXTREME_N)
        hist = f.get(f'{sym}.history')
        if hist is None or not isinstance(hist.value, (tuple, list)) \
                or len(hist.value) < m + 1:
            return True
        prev = hist.value[-(m + 1):-1]
        if direction == 'LONG':
            band = min(float(b[3]) for b in prev)
            return float(close.value) > band
        band = max(float(b[2]) for b in prev)
        return float(close.value) < band


class DonchianBreakoutB(DonchianBreakoutExpert):
    """N=20 bidirectional (SAR): a new N-extreme in either direction is a
    setup (the opposite-direction flip is a new episode, never a reopen)."""
    variant_id = 'b'
    long_only = False


class DonchianBreakoutC(DonchianBreakoutExpert):
    """N=10 channel (bidirectional)."""
    variant_id = 'c'
    channel_n = 10
    long_only = False


class DonchianBreakoutD(DonchianBreakoutExpert):
    """N=55 channel, implemented on the nearest DECLARED 50-bar window
    (window_high_50/window_low_50, G-22). The 32-bar `history` pin (O-020)
    cannot host a 55-bar anchor scan; the gate reference is the honest 50-bar
    channel feature and the anchor scan uses the windowed bound."""
    variant_id = 'd'
    channel_n = 50
    long_only = False


class DonchianBreakoutE(DonchianBreakoutExpert):
    """N=20 entry with the responsive-band exit (band lookback 5): the thesis
    dies on a close through the 5-bar extreme, not the 20-bar channel."""
    variant_id = 'e'
    long_only = False
    exit_kind = 'responsive'


class DonchianBreakoutF(DonchianBreakoutExpert):
    """N=20 entry with the 2-3 bar significant-extreme exit (extreme lookback
    3)."""
    variant_id = 'f'
    long_only = False
    exit_kind = 'significant_extreme'
