"""MACD-filtered stochastic crossover behavior family (`macd_stoch_trend`).

Hypothesis (mechanism `trend_filtered_oscillator`): a stochastic crossover
aligned with the MACD trend filter is a trend-side momentum entry. The book's
rule is fully mechanical (Ch5.5 p152): "Long entries every time the stochastic
crosses above its signal line with the MACD above its zero line. Short entries
every time the stochastic crosses below its signal line with the MACD below
its zero line."

Setup: stoch_k crosses stoch_d (its signal line) with macd > 0 (long) / macd <
0 (short). The setup anchor is the CROSSING BAR — the first bar of the current
run where the crossing state holds (D-026; `find_setup_anchor` run-start
semantics). No price confirmation is required: the book's rule is an entry
signal, not a trigger-on-confirmation pattern.

stoch_k and stoch_d are window-stationary: a bar's %K/%D depend only on its
own trailing 14 bars, so the local series over the `history` window equals the
state features exactly at the newest bar and the anchor scan cannot disagree
with the gate. MACD is read only as the current-bar trend filter (the EMA
recursion is not window-reproducible, which is fine: it is a state condition,
not an anchor input).

Post-entry thesis: the reason to hold a long is that the MACD trend filter
still agrees with the direction (macd > 0). When the filter flips, the
direction of the trade no longer has a trend premise (D-029) — close. The
book's stop is "just below the previous trough" and its target is a trailing
stop (card variants b); both are level-based / position-management rules
(level stops need the swing lattice; the trailing stop is O-013 position
management), so the family uses the declared 1R:1R:8bar fallback geometry
(deviation recorded in the implementer report).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


def _stoch_k_d(highs, lows, closes, period: int = 14) -> tuple[list, list]:
    """Per-bar fast %K and %D = SMA3(%K) (G-09; identical formula to
    marketstate's stoch_k/stoch_d, which makes the local series equal to the
    features at the newest bar)."""
    ks = []
    for i in range(len(closes)):
        lo = max(0, i - period + 1)
        h14 = max(highs[lo:i + 1])
        l14 = min(lows[lo:i + 1])
        if h14 == l14:
            ks.append(50.0)
        else:
            ks.append((closes[i] - l14) / (h14 - l14) * 100.0)
    ds = []
    for i in range(len(closes)):
        win = ks[max(0, i - 2):i + 1]
        ds.append(sum(win) / len(win))
    return ks, ds


def _run_start(cond, n: int) -> int:
    i = n - 1
    if i < 0 or not cond(i):
        return -1
    while i > 0 and cond(i - 1):
        i -= 1
    return i


class MacdStochTrendExpert(Expert):
    """Stochastic crossover filtered by the MACD zero line."""
    expert_id = 'macd_stoch_trend'
    version = 'v1'
    mechanism_family_id = 'trend_filtered_oscillator'
    behavior_family_id = 'macd_stoch_cross'
    variant_id = 'a'
    variants_evaluated = ('a',)
    search_universe_size = 1
    requires = ('oscillator', 'volatility', 'history')

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.stoch_k', f'{sym}.stoch_d',
                f'{sym}.macd', f'{sym}.macd_signal', f'{sym}.macd_hist',
                f'{sym}.atr', f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        macd = f[f'{sym}.macd'].value
        k_now = f[f'{sym}.stoch_k'].value
        d_now = f[f'{sym}.stoch_d'].value
        hist_value = f[f'{sym}.history'].value
        if (not isinstance(hist_value, (tuple, list)) or not hist_value
                or atr is None or macd is None or k_now is None or d_now is None):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(hist_value)
        if len(hist) < 17:
            # The crossing needs %K/%D seeds inside the window (14+3 bars).
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        closes = [float(b[4]) for b in hist]
        highs = [float(b[2]) for b in hist]
        lows = [float(b[3]) for b in hist]
        ks, ds = _stoch_k_d(highs, lows, closes)
        n = len(ks)
        macd = float(macd)
        k_now, d_now = float(k_now), float(d_now)
        direction = None
        s = -1
        if macd > 0.0 and k_now > d_now and ks[-1] > ds[-1]:
            s = _run_start(lambda i: ks[i] > ds[i], n)
            if s >= 1 and ks[s - 1] <= ds[s - 1]:
                direction = 'LONG'
        elif macd < 0.0 and k_now < d_now and ks[-1] < ds[-1]:
            s = _run_start(lambda i: ks[i] < ds[i], n)
            if s >= 1 and ks[s - 1] >= ds[s - 1]:
                direction = 'SHORT'
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = hist[s][0]
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{direction}:{k_now:.6f}:{d_now:.6f}:{close:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr, 'variant': self.variant_id},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the trend filter agrees with the position": a long is
        held only while MACD is above its zero line, a short only while it is
        below. When the filter flips, the direction no longer has a trend
        premise (D-029). Fails open when MACD is unobservable."""
        sym = draft.instrument
        f = state.features
        macd = f.get(f'{sym}.macd')
        if macd is None or macd.value is None:
            return True
        macd = float(macd.value)
        if draft.direction == 'LONG':
            return macd > 0.0
        return macd < 0.0
