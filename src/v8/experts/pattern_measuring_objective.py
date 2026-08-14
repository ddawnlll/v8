"""Geometric-pattern-breakout behavior family (`pattern_measuring_objective`).

Hypothesis (mechanism `geometric_pattern_breakout`; Ch13.2 p499-501): a
completed geometric pattern whose boundary is broken by a CLOSE is a
breakout, and the book's measuring-objective doctrine fixes the target at the
1:1 projection of the pattern's vertical height — "a completed pattern that
achieves its minimum 1:1 objective avoids future pattern-failure
classification" (Ch13.3 p509). Targets become pattern-derived price
distances expressed in R with the 14-bar ATR unit (D-028).

Variants (D-044; one per pattern, all sharing the measuring-objective
mechanism):
  head_shoulders  - head-and-shoulders: neckline break (top -> SHORT, bottom
                    -> LONG); target = 1:1 head-to-neckline height; stop
                    beyond the head.
  double_top      - double top/bottom: validation-level break (the trough
                    between two peaks for a top, the peak between two troughs
                    for a bottom); target = 1:1 validation-to-extreme height;
                    stop beyond the higher peak / lower trough.
  triangle        - symmetrical triangle: close beyond the consolidation
                    range after a narrow, converging range; target = 1:1 of
                    the 20-bar range height; stop behind the opposite range
                    bound.

The book's flag/pennant, wedge, rounding and triple-top patterns are not
implemented in this family: flags/pennants need pole-parallelogram geometry
that the 32-bar history pin (O-020) cannot express, and the card lists them
under the same mechanism with a shared `variants_evaluated` for a future
revision. Structure pivots use a small declared flank because the global
history window is 32 bars (O-020).

The pattern line (neckline / validation level / range bound) is FROZEN at
detection (the prior_high_ref pattern); `still_valid` keeps the thesis alive
while the close stays beyond it — a close back through says the pattern
failed (Ch13.3: "minimum objective not met before price reverses through the
breakout level").
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class PatternMeasuringObjectiveExpert(Expert):
    """Geometric pattern breakout with a 1:1 measuring-objective target."""
    expert_id = 'pattern_measuring_objective'
    version = 'v1'
    mechanism_family_id = 'geometric_pattern_breakout'
    behavior_family_id = 'geometric_pattern_breakout'
    variant_id = 'head_shoulders'
    # target_r/stop_r are structural: the 1:1 pattern-height measuring
    # objective and the frozen pattern stop in R (D-028), computed in
    # evaluate().
    target_r = None
    stop_r = None
    # D-044: every implemented variant (losers included); the reported
    # variant_id is a member. D-046: every threshold/lookback below is a
    # declared constant frozen pre-window, so the search universe equals the
    # evaluated set.
    variants_evaluated = ('head_shoulders', 'double_top', 'triangle')
    search_universe_size = 3
    requires = ('location', 'volatility', 'history')

    # Declared, LOCKED constants (D-036 pattern: "declared, never fitted").
    PT_FLANK = 3                 # structure-pivot flank on the 32-bar history
    TRIANGLE_WINDOW = 20         # convergence scan window (bars)
    TRIANGLE_WIDTH_MAX = 0.03    # max consolidation width (G-26 verbatim)

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    # --- pivot lattice over the history window -------------------------------

    def _pivot_highs(self):
        out = []
        flank = self.PT_FLANK
        hist = self._hist
        for i in range(flank, len(hist) - flank):
            hi = float(hist[i][2])
            if hi > max(float(hist[j][2]) for j in range(i - flank, i)) \
                    and hi > max(float(hist[j][2])
                                 for j in range(i + 1, i + 1 + flank)):
                out.append((i, hi))
        return out

    def _pivot_lows(self):
        out = []
        flank = self.PT_FLANK
        hist = self._hist
        for i in range(flank, len(hist) - flank):
            lo = float(hist[i][3])
            if lo < min(float(hist[j][3]) for j in range(i - flank, i)) \
                    and lo < min(float(hist[j][3])
                                 for j in range(i + 1, i + 1 + flank)):
                out.append((i, lo))
        return out

    # --- head-and-shoulders structure ----------------------------------------

    def _hs_top(self) -> tuple | None:
        """(head, neckline, right_shoulder_idx) or None."""
        ph = self._pivot_highs()
        pl = self._pivot_lows()
        if len(ph) < 3 or len(pl) < 2:
            return None
        head_i, head = max(ph, key=lambda x: x[1])
        lefts = [(i, h) for i, h in ph if i < head_i]
        rights = [(i, h) for i, h in ph if i > head_i]
        if not lefts or not rights:
            return None
        li, left = max(lefts, key=lambda x: x[1])
        ri, right = max(rights, key=lambda x: x[1])
        if not (left < head and right < head):
            return None
        lt = [v for i, v in pl if li < i < head_i]
        rt = [v for i, v in pl if head_i < i < ri]
        if not lt or not rt:
            return None
        neckline = max(max(lt), max(rt))
        if neckline >= head:
            return None
        return head, neckline, ri

    def _hs_bottom(self) -> tuple | None:
        """(head, neckline, right_shoulder_idx) or None."""
        ph = self._pivot_highs()
        pl = self._pivot_lows()
        if len(ph) < 2 or len(pl) < 3:
            return None
        head_i, head = min(pl, key=lambda x: x[1])
        lefts = [(i, v) for i, v in pl if i < head_i]
        rights = [(i, v) for i, v in pl if i > head_i]
        if not lefts or not rights:
            return None
        li, left = min(lefts, key=lambda x: x[1])
        ri, right = min(rights, key=lambda x: x[1])
        if not (left > head and right > head):
            return None
        lp = [v for i, v in ph if li < i < head_i]
        rp = [v for i, v in ph if head_i < i < ri]
        if not lp or not rp:
            return None
        neckline = min(min(lp), min(rp))
        if neckline <= head:
            return None
        return head, neckline, ri

    # --- variant detection ----------------------------------------------------

    def _head_shoulders(self, n: int) -> tuple | None:
        """Neckline break on the current close (no retest — entry on the
        breakout), target = head-to-neckline height."""
        close = float(self._hist[n - 1][4])
        top = self._hs_top()
        if top is not None:
            head, neckline, ri = top
            if close < neckline:
                pred = lambda j, bar: j >= ri and float(bar[4]) < neckline
                anchor = self.find_setup_anchor(self._hist, pred)
                return 'SHORT', neckline, head, head - neckline, anchor
        bottom = self._hs_bottom()
        if bottom is not None:
            head, neckline, ri = bottom
            if close > neckline:
                pred = lambda j, bar: j >= ri and float(bar[4]) > neckline
                anchor = self.find_setup_anchor(self._hist, pred)
                return 'LONG', neckline, head, neckline - head, anchor
        return None

    def _double(self, n: int) -> tuple | None:
        """Validation-level break on the current close; target = the 1:1
        validation-to-extreme projection."""
        close = float(self._hist[n - 1][4])
        ph = self._pivot_highs()
        if len(ph) >= 2:
            (i2, h2), (i1, h1) = ph[-2], ph[-1]
            level = min(float(self._hist[j][3]) for j in range(i2 + 1, i1))
            if h1 > level and h2 > level and close < level:
                stop = max(h1, h2)
                pred = lambda j, bar: j >= i1 and float(bar[4]) < level
                anchor = self.find_setup_anchor(self._hist, pred)
                return 'SHORT', level, stop, stop - level, anchor
        pl = self._pivot_lows()
        if len(pl) >= 2:
            (i2, v2), (i1, v1) = pl[-2], pl[-1]
            level = max(float(self._hist[j][2]) for j in range(i2 + 1, i1))
            if v1 < level and v2 < level and close > level:
                stop = min(v1, v2)
                pred = lambda j, bar: j >= i1 and float(bar[4]) > level
                anchor = self.find_setup_anchor(self._hist, pred)
                return 'LONG', level, stop, level - stop, anchor
        return None

    def _triangle_structure(self) -> bool:
        """Symmetrical-triangle convergence: at least 2 pivot highs DECLINING
        and 2 pivot lows RISING inside the trailing consolidation window
        (excluding the current bar)."""
        n = len(self._hist)
        lo = max(0, n - 1 - self.TRIANGLE_WINDOW)
        ph = sorted((i, h) for i, h in self._pivot_highs() if lo <= i < n - 1)
        pl = sorted((i, v) for i, v in self._pivot_lows() if lo <= i < n - 1)
        if len(ph) < 2 or len(pl) < 2:
            return False
        return ph[0][1] > ph[-1][1] and pl[0][1] < pl[-1][1]

    def _triangle(self, f: dict, n: int) -> tuple | None:
        """Close beyond the narrow consolidation range (breakout from a
        converging range); target = 1:1 of the range height."""
        sym = self._sym
        cr = f.get(f'{sym}.consolidation_range')
        rh = f.get(f'{sym}.range_height_20')
        if cr is None or cr.value is None or rh is None or rh.value is None:
            return None
        h_ref, l_ref, width_ratio, _active = cr.value
        if width_ratio > self.TRIANGLE_WIDTH_MAX or not self._triangle_structure():
            return None
        prev_close = float(self._hist[n - 2][4]) if n >= 2 else None
        if prev_close is None or not (l_ref <= prev_close <= h_ref):
            return None                       # no consolidation right before
        close = float(f[f'{sym}.close'].value)
        height = float(rh.value)
        if close > h_ref:
            pred = lambda j, bar: float(bar[4]) > h_ref
            anchor = self.find_setup_anchor(self._hist, pred)
            return 'LONG', h_ref, l_ref, height, anchor
        if close < l_ref:
            pred = lambda j, bar: float(bar[4]) < l_ref
            anchor = self.find_setup_anchor(self._hist, pred)
            return 'SHORT', l_ref, h_ref, height, anchor
        return None

    # --- evaluate / still_valid -----------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.window_high_20', f'{sym}.window_low_20',
                f'{sym}.range_height_20', f'{sym}.consolidation_range']
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
        n = len(self._hist)
        if n < 2 * self.PT_FLANK + 1:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        if self.variant_id == 'head_shoulders':
            hit = self._head_shoulders(n)
        elif self.variant_id == 'double_top':
            hit = self._double(n)
        else:
            hit = self._triangle(f, n)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, level, stop_price, height, anchor = hit
        if direction == 'LONG':
            stop_r = (close - stop_price) / atr
        else:
            stop_r = (stop_price - close) / atr
        target_r = height / atr
        if stop_r <= 0 or target_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        geometry = self.declared_geometry()
        geometry.update({'target_r': target_r, 'stop_r': stop_r,
                         'atr_ref': atr, 'variant': self.variant_id,
                         'level_ref': level, 'stop_ref': stop_price})
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
        """The thesis is "the pattern's completion line holds": a close back
        through the FROZEN line says the breakout failed and the 1:1
        objective is not in force."""
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
