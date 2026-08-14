"""Ichimoku cloud-trend behavior family (`ichimoku_cloud`, E-18).

Hypothesis (mechanism `cloud_trend`): the Tenkan-Kijun crossover aligned
with the larger trend is a trend-side entry (Ch16.1 p628-632, Ch16.2
p633-643). Tenkan = midrange(9), Kijun = midrange(26), midrange(N) =
(max(high,N) + min(low,N))/2 — computed INSIDE the expert from the
`history` OHLC (G-44); the state does not emit a cloud group.

Variants (rule 13 — one family):
  a  cloud-boundary reversal at thick-cloud zones  -- NOT implemented
  b  thin-cloud breakout entry                    -- NOT implemented
  c  Tenkan-Kijun crossover with larger-trend filter   (implemented)
  d  V/N pattern 1:1 projection                   -- NOT implemented

Variants a/b/d need the FULL displaced cloud (Senkou A/B = midrange(26/52)
plotted 26 bars FORWARD), which requires 78 bars of lookback; the 32-bar
`history` pin (O-020) cannot host it, so they are declared but NOT
evaluated (D-044 honest accounting: variants_evaluated = ('c',), the only
implemented+tested configuration).

Variant c's "larger-trend filter": the book's trend filter is the cloud
itself, which is not computable on the 32-bar pin. The filter is
implemented as close-vs-Kijun alignment (price on the Kijun side of the
entry — a long requires close > Kijun, a short close < Kijun), a
deterministic proxy for the unbuildable cloud (documented deviation).
The setup anchor is the CROSSING BAR — the first bar of the current run
where the crossing state holds (D-026; find_setup_anchor run-start
semantics).

STOP_RULE: the book places the stop "within the cloud, just below Senkou
A / just above Senkou B" (Ch16.2) — cloud levels are unbuildable on the
32-bar pin, so the family uses the declared 1R:1R:8bar fallback geometry
with the atr_ref unit (documented deviation).

TARGET_RULE: none for variant c (the V/N 1:1 measuring objective is
variant d, not evaluated) -> default 1R:1R:8bar.

INVALIDATION_RULE: the thesis is the cross aligned with the trend line —
a close back through the LIVE Kijun says the alignment is gone
(THESIS_INVALIDATED, D-029), even while the stop is a distance away.
Fails open when the Kijun inputs are unobservable.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Ichimoku Tenkan/Kijun lookbacks (G-44, verbatim from the book).
TENKAN_N = 9
KIJUN_N = 26


class IchimokuCloudExpert(Expert):
    """Tenkan-Kijun crossover with the close-vs-Kijun larger-trend filter."""
    expert_id = 'ichimoku_cloud'
    version = 'v1'
    mechanism_family_id = 'cloud_trend'
    behavior_family_id = 'cloud_trend'
    variant_id = 'c'
    variants_evaluated = ('c',)
    search_universe_size = 1
    # Variants a/b/d need the 78-bar displaced cloud (Senkou A/B) the 32-bar
    # history pin cannot host; they are declared in the card but NOT evaluated
    # (D-044: only implemented+tested variants enter variants_evaluated).
    DECLARED_NOT_EVALUATED = ('a', 'b', 'd')
    requires = ('volatility', 'history')

    def _midrange(self, i: int, n: int) -> float:
        start = max(0, i - n + 1)
        return (max(self._highs[start:i + 1]) + min(self._lows[start:i + 1])) / 2.0

    def _bullish_pred(self, i: int, bar: tuple) -> bool:
        """Bar i is a fresh bullish cross aligned with the trend line: Tenkan
        above Kijun with the close above Kijun."""
        if i < 1:
            return False
        return (self._midrange(i, TENKAN_N) > self._midrange(i, KIJUN_N)
                and float(bar[4]) > self._midrange(i, KIJUN_N))

    def _bearish_pred(self, i: int, bar: tuple) -> bool:
        """Bar i is a fresh bearish cross aligned with the trend line."""
        if i < 1:
            return False
        return (self._midrange(i, TENKAN_N) < self._midrange(i, KIJUN_N)
                and float(bar[4]) < self._midrange(i, KIJUN_N))

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
        if atr is None or not isinstance(hist_value, (tuple, list)) or not hist_value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(hist_value)
        # Kijun (26) plus the previous bar's values must be inside the window
        # for a crossover to be confirmable (warmup is absence, never a value).
        if len(hist) < KIJUN_N + 1:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = hist
        self._highs = [float(b[2]) for b in hist]
        self._lows = [float(b[3]) for b in hist]
        n = len(hist)
        tk_now, kj_now = self._midrange(n - 1, TENKAN_N), self._midrange(n - 1, KIJUN_N)
        tk_prev, kj_prev = self._midrange(n - 2, TENKAN_N), self._midrange(n - 2, KIJUN_N)
        direction: str | None = None
        if tk_now > kj_now and tk_prev <= kj_prev and close > kj_now:
            direction = 'LONG'
        elif tk_now < kj_now and tk_prev >= kj_prev and close < kj_now:
            direction = 'SHORT'
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._bullish_pred if direction == 'LONG' else self._bearish_pred
        anchor = self.find_setup_anchor(hist, pred)
        geometry = self.declared_geometry()
        geometry.update({'atr_ref': atr, 'variant': self.variant_id})
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{direction}:{close:.6f}:'
                              f'{tk_now:.6f}:{kj_now:.6f}',
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the cross aligned with the trend line": a long is
        held only while the close stays above the LIVE Kijun, a short only
        while it stays below. A close back through the live Kijun says the
        alignment is gone (D-029). Fails open when the Kijun inputs are
        unobservable."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        hist = f.get(f'{sym}.history')
        if hist is None or not isinstance(hist.value, (tuple, list)) \
                or len(hist.value) < KIJUN_N:
            return True
        bars = hist.value[-KIJUN_N:]
        kijun = (max(float(b[2]) for b in bars) +
                 min(float(b[3]) for b in bars)) / 2.0
        c = float(close.value)
        if draft.direction == 'LONG':
            return c > kijun
        return c < kijun
