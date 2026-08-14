"""Standard momentum-divergence reversal behavior family
(`divergence_12_setups`, book card E-07, Ch9.9.3 p291-303).

Hypothesis (mechanism `momentum_divergence`): when price prints a new extreme
but the oscillator fails to confirm it, the momentum behind the move has
rolled over and price reverses through the intervening swing extreme.

Implemented subset (CRIT-6 — the book's 12 standard setups x 3 oscillators
{rsi14, macd, cci20} x 3 confirmation barriers = the 162-configuration grid
is DECLARED NOT implemented):
  a  bearish standard divergence: price higher high at peak2 vs peak1 while
     rsi14 makes a lower high; confirmation = a CLOSE below the intervening
     swing low (the support between the two peaks) -> SHORT.
  b  bullish standard divergence: price lower low at trough2 vs trough1 while
     rsi14 makes a higher low; confirmation = a CLOSE above the intervening
     swing high (the resistance between the two troughs) -> LONG.

Confirmation is part of the setup predicate (CRIT-7): the expert keeps NO
pending/unconfirmed signal state (EXPERT_PROTOCOL section 1 bans hidden
mutable state); any confirmation gap belongs to the lifecycle
DETECTED -> PENDING -> TRIGGERED machinery. The setup anchor is the first bar
of the current consecutive run in which BOTH the divergence AND the price
confirmation hold (`Expert.find_setup_anchor` over one predicate).

Swing lattice (G-21 + CRIT-1 / Ch27.2 p858-859): pivots with the significance
range filter (pivot range >= 1.0 * ATR, k LOCKED), computed over the
`history` window with marketstate's exact formula, so the window lattice is a
SUBSET of the global swing_* lattice (conservative miss when the true
most-recent swing sits outside the window; the gate cross-checks the newest
local pivot against the state feature and stands down on disagreement).

PIVOT STRENGTH — DEVIATION from the group note: the note names
`swing_high_10`/`swing_low_10`, but the frozen 32-bar `history` window
(O-020) makes a strength-10 divergence pair structurally unobservable: both
pivots need RSI-seeded (>= bar 14) values, a strength-N pair needs the two
pivots >= N+1 bars apart, and the newer pivot must confirm within the window
(newest bar = 31) — for N=10 that requires pivot1 >= 14, pivot2 <= 21, and
pivot2 - pivot1 >= 11, which is impossible. Strength 5 is the largest degree
that fits (pivot1 in [14, 20], pivot2 in [pivot1+6, 26]). The local lattice
therefore uses strength 5 and cross-checks against the state
`swing_high_5`/`swing_low_5` features; this is the same blocker
CRITIC_GAPS 3.3 flags for the P1 swing-anchored families. rsi14 values at
the pivot bars are recomputed locally over the window (Wilder's recursive
seed cannot be reproduced from a 32-bar window alone; the gate and the
anchor scan use the IDENTICAL local series, so the anchor is reproducible
from the gate). Anchor stability across sliding windows is the documented
O-020 approximation shared by the pilots.

The reverse-divergence-continuation behavior (the book's 6 reverse setups) is
a declared sibling of this mechanism family and is NOT implemented here.

Risk geometry: the book gives no numeric stop/target for divergence
(countertrend stops "positioned slightly beyond the supportive/resistive
confluence zones", Ch9.9.3.2 p296), so the family default 1R:1R:8bar +
atr_ref applies. The confirmation barrier and the setup's own new extreme are
FROZEN at detection (`barrier_ref` / `extremum_ref`, the D-042 prior_*_ref
pattern) and drive still_valid.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, LOCKED constants (D-036 pattern: "declared, never fitted").
# Pivot strength: 5, NOT 10 — see the module docstring (the 32-bar history
# window makes a strength-10 divergence pair structurally unobservable).
SWING_N = 5           # swing pivot strength (G-21; swing_high_5/swing_low_5)
SWING_SIGNIFICANCE_K = 1.0   # CRIT-1 / Ch27.2 p858-859 range filter (k LOCKED)
RSI_PERIOD = 14       # G-08 rsi14 lookback


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    if avg_gain == 0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _rsi_per_bar(closes: list[float], period: int = RSI_PERIOD) -> list:
    """Wilder RSI per bar; None before the seed (a bar needs `period` prior
    deltas). Identical formula to marketstate's rsi14, over the given window
    (the recursive seed is window-dependent; the gate and the anchor scan
    share the same window, so determinism holds)."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out = [None] * period
    out.append(_rsi_value(avg_gain, avg_loss))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out.append(_rsi_value(avg_gain, avg_loss))
    return out


def _lattice(highs: list[float], lows: list[float], n: int, atr: float,
             k: float) -> tuple[list, list]:
    """Confirmed significant pivot highs/lows (G-21 + CRIT-1): index p is a
    pivot when both n-bar flanks are closed and its range passes the
    significance filter (>= k*ATR, Ch27.2 p858-859). Matches marketstate's
    `_significant_pivots` formula exactly (single decision-time ATR)."""
    peaks, troughs = [], []
    for i in range(n, len(highs) - n):
        hi = highs[i]
        if hi > max(highs[i - n:i] + highs[i + 1:i + 1 + n]) \
                and hi - lows[i] >= k * atr:
            peaks.append((i, hi))
        lo = lows[i]
        if lo < min(lows[i - n:i] + lows[i + 1:i + 1 + n]) \
                and highs[i] - lo >= k * atr:
            troughs.append((i, lo))
    return peaks, troughs


class Divergence12SetupsExpert(Expert):
    """rsi14 standard momentum divergence with close-through-barrier
    confirmation (book card E-07, Ch9.9.3)."""
    expert_id = 'divergence_12_setups'
    version = 'v1'
    mechanism_family_id = 'momentum_divergence'
    behavior_family_id = 'standard_divergence_reversal'
    variant_id = 'a'
    # D-044: every implemented variant, losers included; the reported
    # variant_id is a member of this list. D-046: all thresholds/lookbacks
    # are declared constants frozen pre-window, so the search universe equals
    # the evaluated set.
    variants_evaluated = ('a', 'b')
    search_universe_size = 2
    requires = ('oscillator', 'location', 'volatility', 'history')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    # --- the single setup predicate (gate AND anchor share it) --------------

    def _setup_at(self, closes, highs, lows, rsi, peaks, troughs,
                  i) -> tuple | None:
        """The FULL observable setup at bar i — divergence AND close
        confirmation (CRIT-7) — using only pivots confirmed by bar i
        (p + SWING_N <= i). Returns (direction, barrier, extremum_price) or
        None. `peaks`/`troughs` are the lattice over the whole window; a
        pivot is observable at bar i exactly when its right flank has closed.
        Deterministic and window-local, so the gate and the anchor scan
        cannot disagree."""
        n = SWING_N
        if self.variant_id == 'a':
            conf = [(p, hi) for (p, hi) in peaks if p + n <= i]
            if len(conf) < 2:
                return None
            (i1, p1), (i2, p2) = conf[-2], conf[-1]
            if not (p2 > p1):                  # higher high required
                return None
            r1, r2 = rsi[i1], rsi[i2]
            if r1 is None or r2 is None or not (r2 < r1):   # lower high in rsi
                return None
            between = lows[i1 + 1:i2]          # intervening swing support
            if not between:
                return None
            barrier = min(between)
            if closes[i] >= barrier:           # close-through confirmation
                return None
            return 'SHORT', barrier, p2
        conf = [(p, lo) for (p, lo) in troughs if p + n <= i]
        if len(conf) < 2:
            return None
        (i1, t1), (i2, t2) = conf[-2], conf[-1]
        if not (t2 < t1):                      # lower low required
            return None
        r1, r2 = rsi[i1], rsi[i2]
        if r1 is None or r2 is None or not (r2 > r1):   # higher low in rsi
            return None
        between = highs[i1 + 1:i2]             # intervening swing resistance
        if not between:
            return None
        barrier = max(between)
        if closes[i] <= barrier:               # close-through confirmation
            return None
        return 'LONG', barrier, t2

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.rsi14',
                f'{sym}.swing_high_5', f'{sym}.swing_low_5', f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        atr = f[f'{sym}.atr'].value
        hist_value = f[f'{sym}.history'].value
        if atr is None or atr <= 0 \
                or not isinstance(hist_value, (tuple, list)) \
                or len(hist_value) < 2 * SWING_N + 1:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        atr = float(atr)
        hist = tuple(hist_value)
        closes = [float(b[4]) for b in hist]
        highs = [float(b[2]) for b in hist]
        lows = [float(b[3]) for b in hist]
        rsi = _rsi_per_bar(closes)
        peaks, troughs = _lattice(highs, lows, SWING_N, atr,
                                  SWING_SIGNIFICANCE_K)
        n = len(closes)
        hit = self._setup_at(closes, highs, lows, rsi, peaks, troughs, n - 1)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, barrier, extremum = hit
        # Consistency guard: the window lattice must reproduce the state's
        # most-recent significant swing in the setup direction. When the true
        # most-recent swing sits outside the window the local pair is a
        # different structure — stand down rather than emit a mis-anchored
        # setup (0.0 is the "no significant swing" sentinel).
        if direction == 'SHORT':
            sw = float(f[f'{sym}.swing_high_5'].value)
            if sw != 0.0 and abs(extremum - sw) > 1e-9:
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
        else:
            sw = float(f[f'{sym}.swing_low_5'].value)
            if sw != 0.0 and abs(extremum - sw) > 1e-9:
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
        pred = lambda i, bar: self._setup_at(
            closes, highs, lows, rsi, peaks, troughs, i) is not None
        anchor = self.find_setup_anchor(hist, pred)
        # The frozen divergence extremum doubles as the pre-entry invalidation
        # level the lifecycle reads (lab.py consumes prior_low_ref /
        # prior_high_ref): a SHORT is dead if price makes a high above the
        # second peak (the bearish divergence broke); a LONG if price makes a
        # low below the second trough. `barrier_ref` / `extremum_ref` are the
        # frozen post-entry thesis levels.
        geo = self.declared_geometry()
        geo.update({'atr_ref': atr, 'variant': self.variant_id,
                    'barrier_ref': barrier, 'extremum_ref': extremum})
        if direction == 'SHORT':
            geo['prior_high_ref'] = extremum
        else:
            geo['prior_low_ref'] = extremum
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=(f'{sym}:{self.variant_id}:{direction}:'
                               f'{barrier:.6f}:{extremum:.6f}'),
            risk_geometry=geo,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is the divergence reversal: the confirmation must hold.
        SHORT stays valid while price stays below the frozen barrier (the
        broken support) and below the frozen second peak (the exhaustion
        high); LONG while price stays above the frozen barrier and the frozen
        second trough. A close back through either level says the reversal
        failed or never started. Fails open when the close is unobservable
        (the price stop still governs)."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        c = float(close.value)
        g = draft.risk_geometry
        barrier = g.get('barrier_ref')
        extremum = g.get('extremum_ref')
        if draft.direction == 'SHORT':
            if barrier is not None and c >= float(barrier):
                return False
            if extremum is not None and c >= float(extremum):
                return False
        else:
            if barrier is not None and c <= float(barrier):
                return False
            if extremum is not None and c <= float(extremum):
                return False
        return True
