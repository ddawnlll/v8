"""Pullback-in-trend depth-gated behavior family (`trend_pullback_depth`, E-02).

Mechanism `trend_continuation` / behavior `pullback_in_trend` — the same
family as the registered pilot `trend_pullback` (close pulled back to the slow
EMA in an uptrend). This module adds the book's depth/health gates (Ch10.14
p400, Ch2.2 p51-52, Ch11 p433/455) as variants a..g.

Hypothesis: inside an established uptrend, a dip whose depth relative to the
prior impulse swing stays within a declared retracement band is a continuation
setup; the entry is a CLOSE-based signal (Ch14.2 doctrine), never an intraday
touch. All variants emit LONG candidates (the card is a buy-dips doctrine).

Variants (rule 13 — one family, depth-gate changes; D-044 lists every
implemented variant, losers included):
  a  depth <= 38.2% of the impulse swing (swing_low_10 -> swing_high_10)
  b  depth <= 50%  (the book's psychologically most important level, Ch10.14)
  c  depth <= 61.8%
  d  MA-rebound: the fast EMA (short MA) closes back ABOVE the slow EMA after
     dipping below it (Ch11 — the short MA rebounds off the long MA)
  e  double-MA-fan filter: the fan stays aligned (fast > slow), price held
     above the slow EMA, and the dip pulled back to the fast-EMA zone and
     reclaimed it; the 50/200 golden-cross state is approximated by the
     fast/slow EMA fan (the 50/200 SMAs are not emitted features — documented
     deviation)
  f  close-reclaim of the dip low: the prior bar closed at the recent dip low
     and the current bar closes back above it
  g  Dow secondary-reaction: depth in [1/3, 2/3] of the primary move (Ch2.2 —
     a normal secondary reaction; > 2/3 on high volume would be a new primary
     trend and is NOT a setup)

The impulse for the depth variants is the most recent significant strength-10
swing pair (swing_high_10 / swing_low_10, G-21); depth = (swing_high_10 -
close) / (swing_high_10 - swing_low_10). The book's fib retracement levels
(G-24) are not consumed — the depth fraction is computed directly from the
swing range (the levels and the fraction carry the same information for the
depth gate). The EMA/dip variants (d/e/f) do not consume the swing pair; their
pullback is defined by the MA cross / fan / dip structure.

Setup anchors (D-026): the depth variants (a/b/c/g) hold across the dip, so
`find_setup_anchor` returns the first bar of the current consecutive run inside
the depth band with the trend aligned; the completion variants (d/e/f) are
single-bar events. The frozen reference (prior_low_ref) is excluded from
episode geometry (D-042), so the key stays stable across a run.

RISK geometry: the book gives a level stop (below the pullback low / below the
61.8-78.6% retracement) but no target (ride the trend), so the family uses the
declared 1R:1R:8bar fallback geometry with the atr_ref unit (D-028). The
structural level frozen in `prior_low_ref` is the impulse swing low (depth
variants) or the recent dip low (MA/dip variants); the pre-entry invalidation
and still_valid both treat a close below it as the pullback structure breaking.
Documented deviation: the book's pullback-low stop is expressed through the 1R
unit; the still-moving pullback low is not a stable frozen reference.

still_valid (D-029): the thesis is "pullback inside an intact uptrend". It
dies when the trend alignment flips (fast <= slow) or the close breaks the
frozen structural low — close at bar close. Fails open on unobservable inputs.

HISTORY-WINDOW LIMITATION (O-020): the depth-gate reference comes from the
swing_high_10/swing_low_10 state features (computed over the full closed
series), so the gate itself is not history-bound. The D-026 anchor scan runs
over the 32-bar history window only; a setup whose run start predates the
window anchors to the window edge (the documented D-034/O-020 bound).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

VARIANTS_EVALUATED = ('a', 'b', 'c', 'd', 'e', 'f', 'g')
# Declared depth gates (book verbatim: 38.2/50/61.8% and Dow 1/3-2/3).
DEPTH_382 = 0.382
DEPTH_50 = 0.50
DEPTH_618 = 0.618
DOW_LOW = 1.0 / 3.0
DOW_HIGH = 2.0 / 3.0
# Recent-dip lookback for variants e/f (declared).
DIP_LOW_N = 5


class TrendPullbackDepthExpert(Expert):
    """Variant a — depth <= 38.2% of the impulse swing."""
    expert_id = 'trend_pullback_depth'
    version = 'v1'
    mechanism_family_id = 'trend_continuation'
    behavior_family_id = 'pullback_in_trend'
    variant_id = 'a'
    variants_evaluated = VARIANTS_EVALUATED
    search_universe_size = 7
    requires = ('trend', 'location', 'volatility', 'history')
    depth_gate = DEPTH_382

    @staticmethod
    def _c(b): return float(b[4])
    @staticmethod
    def _l(b): return float(b[3])
    @staticmethod
    def _fast(b): return float(b[5])
    @staticmethod
    def _slow(b): return float(b[6])

    def _impulse(self, f):
        """(swing_high_10, swing_low_10, range) from the state features, or
        None when the swing pair is not computable (0.0 = no significant
        swing)."""
        sym = self._sym
        sh = f.get(f'{sym}.swing_high_10')
        sl = f.get(f'{sym}.swing_low_10')
        if sh is None or sl is None or sh.value is None or sl.value is None:
            return None
        high, low = float(sh.value), float(sl.value)
        if not (high > low > 0):
            return None
        return high, low, high - low

    def _recent_dip_low(self) -> float:
        """The recent dip low (min low of the DIP_LOW_N bars before the newest)
        — the frozen structural reference for the EMA/dip variants."""
        return min(self._l(b) for b in self._hist[-(DIP_LOW_N + 1):-1])

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: variant {self.variant_id!r} is not in '
                f'variants_evaluated {list(self.variants_evaluated)} (D-044)')
        t = state.as_of
        sym = state.universe[0]
        self._sym = sym
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.ema_fast', f'{sym}.ema_slow']
        if self.variant_id in ('a', 'b', 'c', 'g'):
            need += [f'{sym}.swing_high_10', f'{sym}.swing_low_10']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        fast = float(f[f'{sym}.ema_fast'].value)
        slow = float(f[f'{sym}.ema_slow'].value)
        hist_value = f[f'{sym}.history'].value
        if atr is None or not isinstance(hist_value, (tuple, list)) or not hist_value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = tuple(hist_value)
        if not (fast > slow):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        v = self.variant_id
        if v in ('a', 'b', 'c'):
            imp = self._impulse(f)
            if imp is None:
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_HABITAT', t)
            high, low, rng = imp
            depth = (high - close) / rng
            if not (0.0 <= depth <= self.depth_gate and close < high):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            lower = high - self.depth_gate * rng
            # Gate and anchor share ONE reference (the frozen impulse levels):
            # the anchor scan is the first bar of the current run whose close
            # sits inside the same depth band with the trend aligned.
            pred = (lambda i, bar: self._fast(bar) > self._slow(bar)
                    and lower <= self._c(bar) < high)
            anchor = self.find_setup_anchor(self._hist, pred)
            return self._draft(state, t, sym, close, atr, anchor, low)
        if v == 'g':
            imp = self._impulse(f)
            if imp is None:
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_HABITAT', t)
            high, low, rng = imp
            depth = (high - close) / rng
            if not (DOW_LOW <= depth <= DOW_HIGH):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            lower = high - DOW_HIGH * rng
            upper = high - DOW_LOW * rng
            pred = (lambda i, bar: self._fast(bar) > self._slow(bar)
                    and lower <= self._c(bar) <= upper)
            anchor = self.find_setup_anchor(self._hist, pred)
            return self._draft(state, t, sym, close, atr, anchor, low)
        ref = self._recent_dip_low()
        if len(self._hist) < 2:
            return ExpertEvaluation(self.expert_id, self.version,
                                    state.state_id, 'NOT_APPLICABLE',
                                    'NO_HABITAT', t)
        if v == 'd':
            # MA-rebound: the fast EMA crosses back above the slow EMA (the
            # short MA rebounds off the long MA) with the close above the slow
            # EMA.
            fast_prev = self._fast(self._hist[-2])
            slow_prev = self._slow(self._hist[-2])
            if not (fast_prev <= slow_prev and close > slow):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            pred = (lambda i, bar: i >= 1
                    and self._fast(bar) > self._slow(bar)
                    and self._fast(self._hist[i - 1]) <= self._slow(self._hist[i - 1])
                    and self._c(bar) > self._slow(bar))
            anchor = self.find_setup_anchor(self._hist, pred)
            return self._draft(state, t, sym, close, atr, anchor, ref)
        if v == 'e':
            # Double-MA-fan: fan aligned, close held above the slow EMA, and
            # the dip pulled back to the fast-EMA zone (min low of the last
            # bars <= fast) and reclaimed above it.
            if len(self._hist) < DIP_LOW_N:
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_HABITAT', t)
            dip_zone = min(self._l(b) for b in self._hist[-DIP_LOW_N:-1])
            if not (close > slow and close > fast and dip_zone <= fast):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            pred = (lambda i, bar: i >= DIP_LOW_N
                    and self._fast(bar) > self._slow(bar)
                    and self._c(bar) > self._slow(bar)
                    and self._c(bar) > self._fast(bar)
                    and min(self._l(b)
                            for b in self._hist[i - DIP_LOW_N:i - 1]) <= self._fast(bar))
            anchor = self.find_setup_anchor(self._hist, pred)
            return self._draft(state, t, sym, close, atr, anchor, ref)
        # variant f — close-reclaim of the recent dip low: a fresh dip low
        # (within the last DIP_LOW_N bars) is reclaimed by a close back above
        # it. The current bar must not extend the dip (its low is above the
        # dip low — the reclaim is a close-based event, Ch14.2 doctrine).
        if len(self._hist) < DIP_LOW_N + 1:
            return ExpertEvaluation(self.expert_id, self.version,
                                    state.state_id, 'NOT_APPLICABLE',
                                    'NO_HABITAT', t)
        win = [self._l(b) for b in self._hist[-DIP_LOW_N:]]
        dip = min(win)
        if not (close > dip and self._l(self._hist[-1]) > dip):
            return ExpertEvaluation(self.expert_id, self.version,
                                    state.state_id, 'NOT_APPLICABLE',
                                    'NO_SETUP', t)
        dip_of = (lambda i: min(self._l(b) for b in self._hist[i - DIP_LOW_N + 1:i + 1]))
        pred = (lambda i, bar: i >= DIP_LOW_N - 1
                and self._fast(bar) > self._slow(bar)
                and self._c(bar) > dip_of(i)
                and self._l(bar) > dip_of(i))
        anchor = self.find_setup_anchor(self._hist, pred)
        return self._draft(state, t, sym, close, atr, anchor, ref)

    def _draft(self, state, t, sym, close, atr, anchor, ref) -> ExpertEvaluation:
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='LONG',
            setup_fingerprint=f'{sym}:{self.variant_id}:LONG:{close:.6f}:{ref:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr,
                           'prior_low_ref': ref, 'variant': self.variant_id},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "pullback inside an intact uptrend". It dies when the
        trend alignment flips (fast <= slow) or the close breaks the frozen
        structural low (prior_low_ref) — the pullback no longer has a trend
        premise (D-029). Fails open on unobservable inputs."""
        sym = draft.instrument
        f = state.features
        fast = f.get(f'{sym}.ema_fast')
        slow = f.get(f'{sym}.ema_slow')
        close = f.get(f'{sym}.close')
        if (fast is None or slow is None or close is None
                or fast.value is None or slow.value is None or close.value is None):
            return True
        ref = draft.risk_geometry.get('prior_low_ref')
        if ref is None:
            return True
        return (float(fast.value) > float(slow.value)
                and float(close.value) > float(ref))


class TrendPullbackDepthB(TrendPullbackDepthExpert):
    """Variant b — depth <= 50% of the impulse swing."""
    variant_id = 'b'
    depth_gate = DEPTH_50


class TrendPullbackDepthC(TrendPullbackDepthExpert):
    """Variant c — depth <= 61.8% of the impulse swing."""
    variant_id = 'c'
    depth_gate = DEPTH_618


class TrendPullbackDepthD(TrendPullbackDepthExpert):
    """Variant d — MA-rebound: the fast EMA crosses back above the slow EMA."""
    variant_id = 'd'


class TrendPullbackDepthE(TrendPullbackDepthExpert):
    """Variant e — double-MA-fan filter: shallow dip reclaiming the fast EMA
    while the fan stays aligned."""
    variant_id = 'e'


class TrendPullbackDepthF(TrendPullbackDepthExpert):
    """Variant f — close-reclaim of the recent dip low."""
    variant_id = 'f'


class TrendPullbackDepthG(TrendPullbackDepthExpert):
    """Variant g — Dow secondary-reaction band [1/3, 2/3]."""
    variant_id = 'g'
