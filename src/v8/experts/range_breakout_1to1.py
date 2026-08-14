"""Consolidation / range-breakout behavior family with the book's 1:1
measuring objective (`range_breakout_1to1`, E-03).

Mechanism `consolidation_breakout` / behavior `range_breakout`. Hypothesis
(Ch4.1 p103-104, Ch2.2 p53-54 "Dow lines", Ch13.2 p499-501): a close beyond a
narrow consolidation range is a breakout whose minimum measuring objective is
a price excursion equal to the range height (1:1); a 2:1 projection is the
secondary profit-taking level. The accumulation/distribution LABEL is
retrospective (HAND_EXPERTS §3.6) and is not part of the setup.

Variants (rule 13 — one family, breakout-filter changes; D-044 lists every
implemented variant, losers included):
  a  close beyond the range extreme, no completion filter
  b  close >= 3% beyond the range extreme (Ch4.1 p104)
  c  close >= 5% beyond the range extreme
  d  close >= one ATR beyond the range extreme (ATR-multiple filter, k=1.0
     DECLARED — the book gives no multiple, so the constant is declared
     pre-holdout, never fitted)
  e  close beyond the range extreme WITH breakout-bar volume expansion
     (volume > the 20-bar smoothed volume; Dow volume-confirmation doctrine)
  f  low-volume breakout timing: close beyond the range extreme with volume at
     its 100-bar historical minimum (vol_min_proximity <= 0.25, declared) AND
     volume expansion on the breakout bar (Ch6.1 p180-181)

The consolidation range is the 20-bar Donchian window of the bars BEFORE the
current bar (window_high_20/window_low_20, G-22) with the declared narrowness
precondition: range width <= 3% of price (CONSOLIDATION_WIDTH_MAX, read from
the consolidation_range feature). The setup is by construction a SINGLE-BAR
event: the gate requires the prior bar NOT to have broken out, so the anchor
(D-026) is the breakout bar itself — the market event that created the setup.
The per-bar anchor predicate mirrors the same gate over the history window.

RISK geometry (book exact, Ch13.2 p499-501 + Ch4.1 p104):
  * TARGET = 1:1 range height: target_r = range_height_20 / atr_ref (R is a
    declared price distance, D-028 — the measuring objective expressed in R
    with the declared atr risk unit).
  * STOP behind the consolidation boundary (far side of the range):
    stop_r = range_height_20 / atr_ref (declared interpretation — "just
    inside / opposite side of the range").
  * The 2:1 secondary target is recorded as `target_2x_ref` (a frozen price
    level) for attribution; the simulator exits at the primary 1:1 objective.
  * expiry_bars = 8 (family fallback; the book gives no expiry).

still_valid (D-029): the thesis is "the breakout holds"; a close back inside
the range (below the FROZEN breakout level for a long, above it for a short)
before the 1:1 objective is met is the book's invalidation (Ch4.1) — close at
bar close. Fails open on unobservable inputs.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

VARIANTS_EVALUATED = ('a', 'b', 'c', 'd', 'e', 'f')
# Range lookback (the G-22 20-bar window).
RANGE_N = 20
# Narrow-consolidation width precondition (CONSOLIDATION_WIDTH_MAX, declared).
WIDTH_MAX = 0.03
# Completion filters for variants b/c (book Ch4.1 p104: 3-5%).
FILTER_3PCT = 1.03
FILTER_5PCT = 1.05
# ATR-multiple breakout filter (variant d), declared k (book gives no number).
ATR_K = 1.0
# Low-volume precondition (variant f): volume near its 100-bar historical
# minimum (declared percentile rank bound).
VOL_MIN_PROXIMITY_MAX = 0.25


class RangeBreakout1To1Expert(Expert):
    """Variant a — close beyond the 20-bar range extreme, no completion filter
    (bidirectional)."""
    expert_id = 'range_breakout_1to1'
    version = 'v1'
    mechanism_family_id = 'consolidation_breakout'
    behavior_family_id = 'range_breakout'
    variant_id = 'a'
    variants_evaluated = VARIANTS_EVALUATED
    search_universe_size = 6
    requires = ('location', 'volatility', 'history', 'participation')
    # target_r/stop_r are structural: the 1:1 range-height measuring
    # objective in R (D-028), computed in evaluate().
    target_r = None
    stop_r = None
    # Breakout completion filter as a price multiple (variants b/c) or None.
    filter_mult = 1.0
    # Variants d (ATR-multiple), e/f (volume) toggle extra conditions.
    atr_filter = False
    volume_expansion = False
    low_volume_precond = False

    @staticmethod
    def _c(b): return float(b[4])
    @staticmethod
    def _h(b): return float(b[2])
    @staticmethod
    def _l(b): return float(b[3])

    # --- per-history-bar window references (G-22 formula) --------------------

    def _win_high(self, i: int) -> float | None:
        if i < RANGE_N:
            return None
        return max(self._h(b) for b in self._hist[i - RANGE_N:i])

    def _win_low(self, i: int) -> float | None:
        if i < RANGE_N:
            return None
        return min(self._l(b) for b in self._hist[i - RANGE_N:i])

    def _breakout_level(self, i: int, direction: str) -> float | None:
        """The level a close must exceed (long) / fall below (short) at bar i
        for the variant's completion filter (mirrors the gate exactly)."""
        if direction == 'LONG':
            base = self._win_high(i)
        else:
            base = self._win_low(i)
        if base is None:
            return None
        return base * self.filter_mult if self.filter_mult else base

    def _long_pred(self, i: int, bar: tuple) -> bool:
        """Bar i broke out above the filtered 20-bar window high, and the prior
        bar had NOT broken out (single-bar setup guarantee)."""
        if i < RANGE_N:
            return False
        level = self._win_high(i) * self.filter_mult
        if self.atr_filter:
            level += ATR_K * self._atr_ref
        if not (self._c(bar) > level):
            return False
        prev = self._win_high(i - 1) if i - 1 >= RANGE_N else None
        if prev is None:
            return True
        if self.atr_filter:
            return self._c(self._hist[i - 1]) <= prev + ATR_K * self._atr_ref
        return self._c(self._hist[i - 1]) <= prev * self.filter_mult

    def _short_pred(self, i: int, bar: tuple) -> bool:
        if i < RANGE_N:
            return False
        level = self._win_low(i) * self.filter_mult
        if self.atr_filter:
            level -= ATR_K * self._atr_ref
        if not (self._c(bar) < level):
            return False
        prev = self._win_low(i - 1) if i - 1 >= RANGE_N else None
        if prev is None:
            return True
        if self.atr_filter:
            return self._c(self._hist[i - 1]) >= prev - ATR_K * self._atr_ref
        return self._c(self._hist[i - 1]) >= prev * self.filter_mult

    # --- evaluation -----------------------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: variant {self.variant_id!r} is not in '
                f'variants_evaluated {list(self.variants_evaluated)} (D-044)')
        t = state.as_of
        sym = state.universe[0]
        self._sym = sym
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.window_high_20', f'{sym}.window_low_20',
                f'{sym}.range_height_20', f'{sym}.consolidation_range']
        if self.atr_filter or self.volume_expansion or self.low_volume_precond:
            need.append(f'{sym}.volume')
        if self.volume_expansion or self.low_volume_precond:
            need.append(f'{sym}.vol_smooth_ma')
        if self.low_volume_precond:
            need.append(f'{sym}.vol_min_proximity')
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        wh = float(f[f'{sym}.window_high_20'].value)
        wl = float(f[f'{sym}.window_low_20'].value)
        rng_h = float(f[f'{sym}.range_height_20'].value)
        cons = f[f'{sym}.consolidation_range'].value
        hist_value = f[f'{sym}.history'].value
        if (atr is None or not isinstance(hist_value, (tuple, list))
                or not hist_value or not isinstance(cons, (tuple, list))):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = tuple(hist_value)
        self._atr_ref = atr
        # Narrow-consolidation precondition: the 20-bar range before the bar is
        # a genuine consolidation (declared width bound).
        if float(cons[2]) > WIDTH_MAX:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        if not (wh > wl and rng_h > 0):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        # Volume gates (variants e/f) are evaluated on the breakout bar.
        volume_ok = True
        if self.volume_expansion or self.low_volume_precond:
            vol = float(f[f'{sym}.volume'].value)
            sma = float(f[f'{sym}.vol_smooth_ma'].value)
            volume_ok = vol > sma
        if self.low_volume_precond:
            prox = float(f[f'{sym}.vol_min_proximity'].value)
            volume_ok = volume_ok and prox <= VOL_MIN_PROXIMITY_MAX
        level = wh * self.filter_mult
        if self.atr_filter:
            level += ATR_K * atr
        short_level = wl * self.filter_mult
        if self.atr_filter:
            short_level -= ATR_K * atr
        direction = None
        if close > level and volume_ok:
            direction = 'LONG'
        elif close < short_level and volume_ok:
            direction = 'SHORT'
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        # Single-bar setup guarantee: the prior bar must NOT have broken out.
        n = len(self._hist)
        prev = self._breakout_level(n - 2, direction)
        prior_broke = (prev is not None and (
            (self._c(self._hist[-2]) > prev) if direction == 'LONG'
            else (self._c(self._hist[-2]) < prev)))
        if prior_broke:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._long_pred if direction == 'LONG' else self._short_pred
        anchor = self.find_setup_anchor(self._hist, pred)
        # 1:1 measuring-objective geometry in R (D-028): one range height is
        # the book's minimum target AND the far-side-of-range stop distance.
        rr = rng_h / atr
        geom = self.declared_geometry()
        geom.update({'target_r': rr, 'stop_r': rr, 'atr_ref': atr,
                     'variant': self.variant_id})
        if direction == 'LONG':
            geom['prior_low_ref'] = wl
            geom['breakout_ref'] = wh
        else:
            geom['prior_high_ref'] = wh
            geom['breakout_ref'] = wl
        # Secondary profit-taking level (2:1 of the range height, Ch13.2).
        if direction == 'LONG':
            geom['target_2x_ref'] = wh + 2.0 * rng_h
        else:
            geom['target_2x_ref'] = wl - 2.0 * rng_h
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction}:{close:.6f}:'
                              f'{wh:.6f}:{wl:.6f}',
            risk_geometry=geom, birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the breakout holds": the close must stay beyond the
        FROZEN breakout level (a close back inside the range before the 1:1
        objective is the book's invalidation, Ch4.1). Fails open when the
        inputs are unobservable."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        ref = draft.risk_geometry.get('breakout_ref')
        if ref is None:
            return True
        if draft.direction == 'LONG':
            return float(close.value) > float(ref)
        return float(close.value) < float(ref)


class RangeBreakout1To1B(RangeBreakout1To1Expert):
    """Variant b — completion filter 3% beyond the range extreme."""
    variant_id = 'b'
    filter_mult = FILTER_3PCT


class RangeBreakout1To1C(RangeBreakout1To1Expert):
    """Variant c — completion filter 5% beyond the range extreme."""
    variant_id = 'c'
    filter_mult = FILTER_5PCT


class RangeBreakout1To1D(RangeBreakout1To1Expert):
    """Variant d — one-ATR completion filter beyond the range extreme."""
    variant_id = 'd'
    atr_filter = True


class RangeBreakout1To1E(RangeBreakout1To1Expert):
    """Variant e — range breakout with breakout-bar volume expansion."""
    variant_id = 'e'
    volume_expansion = True


class RangeBreakout1To1F(RangeBreakout1To1Expert):
    """Variant f — low-volume breakout timing: volume at its 100-bar minimum
    precondition plus expansion on the breakout bar."""
    variant_id = 'f'
    volume_expansion = True
    low_volume_precond = True
