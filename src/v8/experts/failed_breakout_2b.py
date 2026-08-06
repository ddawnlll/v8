"""Failed-breakout reentry behavior family, book 2B / Hikkake / Oops / failed
cloud / failed S/R variants (`failed_breakout_2b`, E-01).

Mechanism `liquidity_vacuum_reentry` / behavior `failed_breakout_reentry` —
the same family as the registered pilot `failed_breakout`, which owns variant
`a` (a close above the prior high that fails back below it, SHORT; CRIT-4).
This module implements the book's remaining false-breakout entry geometries as
variants b..g ONLY — variant `a` is not reused.

Hypothesis (shared, Ch7.3 p228 / Ch4.2 p106): a false test of a prior level is
a liquidity-vacuum reentry — the failed move fills resting stops, and the
close-based reclaim of the level is the reentry trigger. All variants enter on
a CLOSE-based reclaim (Ch14.2 doctrine: intraday penetration never confirms).

Variants (rule 13 — one family, entry-geometry changes; D-044 lists every
implemented variant, losers included):
  b  2B non-failure swing (Sperandeo, Ch7.3 p228): LONG — the prior bar closes
      below the significant swing low (swing_low_10, 0.0 = no significant
      swing), the current bar closes back above it.
  c  Hikkake bullish (Ch7.4 p230): an inside bar, a false close below its low,
      then a close back above its HIGH within HIKKAKE_WINDOW_BARS of the failed
      move.
  d  Hikkake bearish (Ch7.4 p230): mirror — an inside bar, a false close above
      its high, then a close back below its LOW within the window.
  e  William's Oops (Ch7.4 p231): a bar opens beyond the prior bar's range
      (type-3 gap) and closes back through the prior extreme — buy-stop at the
      prior low (bullish), sell-stop at the prior high (bearish).
  f  Ichimoku failed cloud breakout (Ch16.2 p642): SHORT — a close above the
      cloud-proxy top then a close back below it (cloud proxied by the Kijun
      midrange(CLOUD_N); see module notes).
  g  Failed S/R close-through (Ch5.5 p150 role reversal): a close through the
      20-bar window S/R level then a close back through it — LONG at the window
      low, SHORT at the window high.

Setup anchors (D-026): every variant is a single-bar completion event — the
setup predicate holds on the reclaim/break bar and cannot hold on two
consecutive bars, so `find_setup_anchor`'s run-start semantics resolve to the
completion bar itself (the market event that created the setup).

RISK geometry: the book gives level stops (just beyond the false-move extreme)
but no measuring target (Ch7.3 p228-231: none stated), so the family uses the
declared 1R:1R:8bar fallback geometry with the atr_ref unit (D-028). The frozen
level is bound as `prior_low_ref` (longs) / `prior_high_ref` (shorts) — the
D-042 pattern: data-dependent refs are excluded from episode geometry so the
episode key stays stable. It drives both the lab's pre-entry invalidation and
the post-entry thesis.

still_valid (D-029): the thesis is "the false move failed"; a close back
through the frozen level says the reentry premise is gone — close at bar close.
Fails open on unobservable inputs (an unreadable thesis is not a dead thesis).

Feature notes:
  * candle_shape (G-06 inside_bar/outside_bar, G-07 gap_dir/gap_size) — the
    Hikkake variants cross-check the newest bar's inside/outside status against
    the state features (feature and local series must agree, conservative);
    the Oops variants read gap_dir/gap_size directly.
  * Variant f's "cloud" is a declared proxy: the book's Ichimoku cloud needs
    the 26-bar forward-displaced Senkou spans (G-44 / V8_LOGIC_GAP H08), which
    the feature graph does not emit. The cloud top is approximated by the
    Kijun-style midrange(26) of the bars BEFORE the breakout bar, computed from
    the 32-bar history. Documented deviation.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Variant ids implemented here (D-044: the full evaluated set; variant `a` is
# the registered pilot's and is deliberately not re-evaluated here — CRIT-4).
VARIANTS_EVALUATED = ('b', 'c', 'd', 'e', 'f', 'g')
# Hikkake reclaim window (book verbatim, Ch7.4 p230: "within 3 bars").
HIKKAKE_WINDOW_BARS = 3
# Ichimoku Kijun-style cloud-proxy lookback (book: Kijun = midrange(26)).
CLOUD_N = 26
# Minimum history length per variant: the false move + reference bar + reclaim
# must all fit inside the 32-bar history window (D-034/O-020 bound).
MIN_HISTORY = {'b': 2, 'c': 4, 'd': 4, 'e': 2, 'f': CLOUD_N + 2, 'g': 22}


class FailedBreakout2BExpert(Expert):
    """Variant b — 2B non-failure swing (Sperandeo): LONG on a close-based
    reclaim of the significant swing low after a failed breakdown."""
    expert_id = 'failed_breakout_2b'
    version = 'v1'
    mechanism_family_id = 'liquidity_vacuum_reentry'
    behavior_family_id = 'failed_breakout_reentry'
    variant_id = 'b'
    variants_evaluated = VARIANTS_EVALUATED
    search_universe_size = 6
    requires = ('location', 'volatility', 'history', 'candle_shape')

    # --- per-history-bar helpers -------------------------------------------

    @staticmethod
    def _o(b): return float(b[1])
    @staticmethod
    def _h(b): return float(b[2])
    @staticmethod
    def _l(b): return float(b[3])
    @staticmethod
    def _c(b): return float(b[4])

    def _inside(self, i: int) -> bool:
        """Bar i is an inside bar of bar i-1 (marketstate G-06 formula)."""
        return (self._h(self._hist[i]) <= self._h(self._hist[i - 1])
                and self._l(self._hist[i]) >= self._l(self._hist[i - 1]))

    def _cloud_top(self, i: int) -> float | None:
        """Kijun-style cloud-proxy top at bar i: midrange of the CLOUD_N bars
        before it (G-44 proxy; None when the window is not computable)."""
        if i < CLOUD_N:
            return None
        win = self._hist[i - CLOUD_N:i]
        if not win:
            return None
        hi = max(self._h(b) for b in win)
        lo = min(self._l(b) for b in win)
        return (hi + lo) / 2.0

    def _candle_features_agree(self, state: MarketState, sym: str) -> bool:
        """Cross-check the newest bar's inside/outside status against the state
        candle_shape features (feature and local computation must agree; a
        drift fails the setup conservatively rather than emitting an anchor the
        features cannot reproduce)."""
        if len(self._hist) < 2:
            return False
        f = state.features
        inside = f.get(f'{sym}.inside_bar')
        outside = f.get(f'{sym}.outside_bar')
        if inside is None or outside is None:
            return False
        in_feat = float(inside.value)
        out_feat = float(outside.value)
        in_loc = 1.0 if self._inside(len(self._hist) - 1) else 0.0
        out_loc = 1.0 if (self._h(self._hist[-1]) >= self._h(self._hist[-2])
                          and self._l(self._hist[-1]) <= self._l(self._hist[-2])) else 0.0
        return (in_loc == in_feat) and (out_loc == out_feat)

    # --- per-variant detection predicates -----------------------------------

    def _detect_b(self, state, f, close, atr) -> tuple | None:
        """2B non-failure swing: LONG reclaim of the significant swing low."""
        sym = self._sym
        sw_low = f.get(f'{sym}.swing_low_10')
        if sw_low is None or sw_low.value is None or float(sw_low.value) <= 0:
            return None
        ref = float(sw_low.value)
        if len(self._hist) < 2:
            return None
        if not (self._c(self._hist[-2]) < ref and close > ref):
            return None
        pred = lambda i, bar: (i >= 1
                               and self._c(self._hist[i - 1]) < ref
                               and self._c(bar) > ref)
        anchor = self.find_setup_anchor(self._hist, pred)
        return 'LONG', anchor, ref

    def _hikkake(self, state, f, close, bullish: bool) -> tuple | None:
        """Shared Hikkake sequence (Ch7.4 p230). bullish=True -> variant c,
        False -> variant d. Scans newest -> oldest for the most recent inside
        bar whose range was falsely broken and then reclaimed at the newest
        bar within HIKKAKE_WINDOW_BARS of the failed move."""
        if not self._candle_features_agree(state, self._sym):
            return None
        n = len(self._hist)
        if n < 4:
            return None
        for j in range(n - 3, 0, -1):          # inside bar index (newest first)
            if not self._inside(j):
                continue
            inside_high = self._h(self._hist[j])
            inside_low = self._l(self._hist[j])
            if inside_high <= inside_low:
                continue
            fb = j + 1                         # the false-break bar
            if fb >= n - 1:
                continue                       # no reclaim bar yet
            if bullish:
                broke = self._c(self._hist[fb]) < inside_low
                reclaim = close > inside_high
            else:
                broke = self._c(self._hist[fb]) > inside_high
                reclaim = close < inside_low
            if not broke or not reclaim:
                continue
            if (n - 1) - fb > HIKKAKE_WINDOW_BARS:
                continue                       # reclaim too late
            ref = inside_low if bullish else inside_high
            pred = (lambda i, bar, jj=j, ii_low=inside_low, ii_high=inside_high:
                    i >= 2 and self._hikkake_completes(i, jj, ii_low, ii_high,
                                                       bullish))
            anchor = self.find_setup_anchor(self._hist, pred)
            return ('LONG' if bullish else 'SHORT'), anchor, ref
        return None

    def _hikkake_completes(self, i: int, j: int, inside_low: float,
                           inside_high: float, bullish: bool) -> bool:
        """True when bar i completes the Hikkake that began at inside bar j
        (j and its false-break bar fixed) — used by the anchor scan so the
        gate and the anchor cannot drift."""
        if i < j + 2:
            return False
        fb = j + 1
        if i - fb > HIKKAKE_WINDOW_BARS:
            return False
        if bullish:
            return (self._c(self._hist[fb]) < inside_low
                    and self._c(self._hist[i]) > inside_high)
        return (self._c(self._hist[fb]) > inside_high
                and self._c(self._hist[i]) < inside_low)

    def _detect_e(self, state, f, close, atr) -> tuple | None:
        """William's Oops (Ch7.4 p231): an open beyond the prior bar's range
        (type-3 gap) reclaimed by a close back through the prior extreme."""
        sym = self._sym
        gap_dir = f.get(f'{sym}.gap_dir')
        if gap_dir is None or gap_dir.value is None:
            return None
        gdir = float(gap_dir.value)
        n = len(self._hist)
        if n < 2:
            return None
        prior_high = self._h(self._hist[-2])
        prior_low = self._l(self._hist[-2])
        if gdir < 0 and close > prior_low:
            ref = prior_low
            pred = (lambda i, bar: i >= 1
                    and self._o(bar) < self._l(self._hist[i - 1])
                    and self._c(bar) > self._l(self._hist[i - 1]))
            anchor = self.find_setup_anchor(self._hist, pred)
            return 'LONG', anchor, ref
        if gdir > 0 and close < prior_high:
            ref = prior_high
            pred = (lambda i, bar: i >= 1
                    and self._o(bar) > self._h(self._hist[i - 1])
                    and self._c(bar) < self._h(self._hist[i - 1]))
            anchor = self.find_setup_anchor(self._hist, pred)
            return 'SHORT', anchor, ref
        return None

    def _detect_f(self, state, f, close, atr) -> tuple | None:
        """Ichimoku failed cloud breakout (Ch16.2 p642): SHORT on a close back
        below the cloud-proxy top after a close above it."""
        n = len(self._hist)
        if n < CLOUD_N + 1:
            return None
        top = self._cloud_top(n - 2)          # cloud top at the prior bar
        if top is None:
            return None
        if not (self._c(self._hist[-2]) > top and close < top):
            return None
        pred = (lambda i, bar: i >= CLOUD_N + 1
                and self._cloud_top(i - 1) is not None
                and self._c(self._hist[i - 1]) > self._cloud_top(i - 1)
                and self._c(bar) < self._cloud_top(i - 1))
        anchor = self.find_setup_anchor(self._hist, pred)
        return 'SHORT', anchor, top

    def _detect_g(self, state, f, close, atr) -> tuple | None:
        """Failed S/R close-through (role reversal, Ch5.5 p150): the prior bar
        closed THROUGH the 20-bar window S/R level (as of the PRIOR bar — the
        level excludes the false-move bar itself, so a genuine close-through is
        measurable), and the current bar closes back through it. LONG at the
        window low, SHORT at the window high."""
        n = len(self._hist)
        if n < 22:
            return None
        # The S/R level as of the PRIOR bar (G-22 window of the 20 bars before
        # it): the false-move bar's own low/high cannot set the level it broke.
        w_high = max(self._h(b) for b in self._hist[n - 22:n - 2])
        w_low = min(self._l(b) for b in self._hist[n - 22:n - 2])
        if not (w_high > w_low):
            return None
        if self._c(self._hist[-2]) < w_low and close > w_low:
            pred = (lambda i, bar: i >= 21
                    and self._c(self._hist[i - 1])
                    < min(self._l(b) for b in self._hist[i - 21:i - 1])
                    and self._c(bar)
                    > min(self._l(b) for b in self._hist[i - 21:i - 1]))
            anchor = self.find_setup_anchor(self._hist, pred)
            return 'LONG', anchor, w_low
        if self._c(self._hist[-2]) > w_high and close < w_high:
            pred = (lambda i, bar: i >= 21
                    and self._c(self._hist[i - 1])
                    > max(self._h(b) for b in self._hist[i - 21:i - 1])
                    and self._c(bar)
                    < max(self._h(b) for b in self._hist[i - 21:i - 1]))
            anchor = self.find_setup_anchor(self._hist, pred)
            return 'SHORT', anchor, w_high
        return None

    # --- evaluation ---------------------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: variant {self.variant_id!r} is not in '
                f'variants_evaluated {list(self.variants_evaluated)} (D-044)')
        t = state.as_of
        sym = state.universe[0]
        self._sym = sym
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
        self._hist = tuple(hist_value)
        v = self.variant_id
        # Per-variant habitat: each setup needs a minimum history length (the
        # false move, its reference bar, and the reclaim bar must all fit) —
        # a too-short window is NO_HABITAT, never a zero signal.
        if len(self._hist) < MIN_HISTORY[self.variant_id]:
            return ExpertEvaluation(self.expert_id, self.version,
                                    state.state_id, 'NOT_APPLICABLE',
                                    'NO_HABITAT', t)
        # Per-variant habitat: candle_shape features are warmup-gated and ABSENT
        # until their window fills (inside/outside need 2 bars, gaps need 2
        # bars) — absent features are NO_HABITAT, never a zero signal.
        if v in ('c', 'd'):
            if not self._need(state, [f'{sym}.inside_bar', f'{sym}.outside_bar']):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_HABITAT', t)
        elif v == 'e':
            if not self._need(state, [f'{sym}.gap_dir', f'{sym}.gap_size']):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_HABITAT', t)
        hit = None
        if v == 'b':
            hit = self._detect_b(state, f, close, atr)
        elif v == 'c':
            hit = self._hikkake(state, f, close, bullish=True)
        elif v == 'd':
            hit = self._hikkake(state, f, close, bullish=False)
        elif v == 'e':
            hit = self._detect_e(state, f, close, atr)
        elif v == 'f':
            hit = self._detect_f(state, f, close, atr)
        else:
            hit = self._detect_g(state, f, close, atr)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, anchor, ref = hit
        geom = {'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0, 'stop_r': 1.0,
                'expiry_bars': 8, 'atr_ref': atr, 'variant': self.variant_id}
        if direction == 'LONG':
            geom['prior_low_ref'] = ref
        else:
            geom['prior_high_ref'] = ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction}:{ref:.6f}:{close:.6f}',
            risk_geometry=geom, birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the false move failed": the position is held while the
        close stays on the reentry side of the FROZEN level. A close back
        through it says the reclaim did not hold — the reentry premise is gone
        (D-029). Fails open on unobservable inputs."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        if draft.direction == 'LONG':
            ref = draft.risk_geometry.get('prior_low_ref')
            return ref is None or float(close.value) > float(ref)
        ref = draft.risk_geometry.get('prior_high_ref')
        return ref is None or float(close.value) < float(ref)


class FailedBreakout2BC(FailedBreakout2BExpert):
    """Variant c — Hikkake bullish: LONG on a close back above the inside bar's
    high after a false close below its low."""
    variant_id = 'c'


class FailedBreakout2BD(FailedBreakout2BExpert):
    """Variant d — Hikkake bearish: SHORT on a close back below the inside
    bar's low after a false close above its high."""
    variant_id = 'd'


class FailedBreakout2BE(FailedBreakout2BExpert):
    """Variant e — William's Oops (both directions)."""
    variant_id = 'e'


class FailedBreakout2BF(FailedBreakout2BExpert):
    """Variant f — Ichimoku failed cloud breakout (SHORT)."""
    variant_id = 'f'


class FailedBreakout2BG(FailedBreakout2BExpert):
    """Variant g — failed S/R close-through (both directions)."""
    variant_id = 'g'
