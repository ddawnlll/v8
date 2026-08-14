"""Breakout-retest role-reversal behavior family (`breakout_retest`).

Registered family (D-042; book Ch5.5 p150 Fig5.34-5.36, Ch13.3 p509).
Hypothesis: after a valid breakout the breached level flips role —
resistance becomes support, support becomes resistance — and a retest of the
flipped level that holds by the close is a continuation entry. Close-confirmed
(Ch14.2): the retest must hold by the close, never by an intrabar touch.

Variants (rule 13; D-044 lists every implemented variant):
  a  role-reversal retest on a significant swing level (swing_high_10 /
     swing_low_10): LONG when a broken resistance retests and holds above it;
     SHORT mirror on a broken support.
  b  validation-level retest for a double-top / double-bottom structure: the
     validation level is the trough between two peaks (short) or the peak
     between two troughs (long); target = 1:1 projection of the pattern
     height (Ch13.3: "pattern immune to failure once the minimum objective
     is met").
  c  neckline retest for a head-and-shoulders: neckline break, then a retest
     of the neckline; target = 1:1 head-to-neckline height (Ch13.3 p509).

The book's variant d (Ichimoku cloud retest, Ch16.2 p642) is NOT implemented:
the displaced Senkou cloud needs ~78 bars (52-bar Span B midrange + 26-bar
forward displacement), which the global 32-bar history pin (O-020) cannot
carry, and no cloud feature is emitted (CRIT-3.3 flags the same O-020 block
for the whole cloud family). It stays out of `variants_evaluated` rather than
being claimed unevaluated (D-044).

The reference level is FROZEN at detection (the prior_high_ref pattern): a
live-recomputed level drifts with the move and the retest/hold test never
fires stably. `still_valid` uses the frozen level.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class BreakoutRetestExpert(Expert):
    """Role-reversal retest entries on a breached significant level."""
    expert_id = 'breakout_retest'
    version = 'v1'
    mechanism_family_id = 'breakout_retest'
    behavior_family_id = 'breakout_retest'
    variant_id = 'a'
    # target_r/stop_r are structural: measured levels in R (D-028) computed
    # in evaluate() (target_r = 1:1 pattern-height projection for variants
    # b/c, the family 1R default for variant a).
    target_r = None
    stop_r = None
    # D-044: every implemented variant (losers included); the reported
    # variant_id is a member. D-046: all thresholds/lookbacks are declared
    # constants frozen pre-window, so the search universe equals the set.
    variants_evaluated = ('a', 'b', 'c')
    search_universe_size = 3
    requires = ('location', 'volatility', 'history')

    # Declared, LOCKED (D-036): pattern-pivot flank for the double/H&S
    # structure scans on the 32-bar history (a small flank because the global
    # history pin is 32 bars, O-020).
    PT_FLANK = 3

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

    # --- retest-hold predicates (frozen level; D-026 anchor scan) ------------

    def _retest_long_pred(self, level: float):
        def pred(i: int, bar: tuple) -> bool:
            if i == 0:
                return False
            _e, _o, _h, low, close, _f, _s = bar
            if not (low <= level and close > level):
                return False
            # the retest must FOLLOW a valid breakout (a prior close beyond
            # the level).
            return any(self._hist[j][4] > level for j in range(i))
        return pred

    def _retest_short_pred(self, level: float):
        def pred(i: int, bar: tuple) -> bool:
            if i == 0:
                return False
            _e, _o, high, _l, close, _f, _s = bar
            if not (high >= level and close < level):
                return False
            return any(self._hist[j][4] < level for j in range(i))
        return pred

    # --- variant detection ----------------------------------------------------

    def _variant_a(self, f: dict, n: int) -> tuple | None:
        """Role-reversal retest on the significant swing level. No pattern, so
        the height is None and the family default target applies."""
        sym = self._sym
        newest = self._hist[n - 1]
        hi = f.get(f'{sym}.swing_high_10')
        if hi is not None and hi.value is not None and float(hi.value) > 0:
            level = float(hi.value)
            if self._retest_long_pred(level)(n - 1, newest):
                return 'LONG', level, level, None
        lo = f.get(f'{sym}.swing_low_10')
        if lo is not None and lo.value is not None and float(lo.value) > 0:
            level = float(lo.value)
            if self._retest_short_pred(level)(n - 1, newest):
                return 'SHORT', level, level, None
        return None

    def _variant_b(self, n: int) -> tuple | None:
        """Validation-level retest for a double-top / double-bottom. The
        validation level is the trough between the two most recent pivot
        peaks (short) or the peak between the two most recent pivot troughs
        (long) — the Ch13.3 "validation level". It is read from the structure
        itself, not from the state swing feature: after a breakdown makes new
        lows the old trough is no longer the most recent significant swing,
        and a live feature would silently drop the setup's own level.
        The pattern height is the validation-to-extreme distance (1:1)."""
        newest = self._hist[n - 1]
        ph = self._pivot_highs()
        if len(ph) >= 2:
            (i2, h2), (i1, h1) = ph[-2], ph[-1]
            # validation level = the trough strictly between the two peaks
            level = min(float(self._hist[j][3]) for j in range(i2 + 1, i1))
            if h1 > level and h2 > level:            # double top
                if any(self._hist[j][4] < level for j in range(i1, n - 1)) \
                        and self._retest_short_pred(level)(n - 1, newest):
                    return 'SHORT', level, max(h1, h2), max(h1, h2) - level
        pl = self._pivot_lows()
        if len(pl) >= 2:
            (i2, v2), (i1, v1) = pl[-2], pl[-1]
            # validation level = the peak strictly between the two troughs
            level = max(float(self._hist[j][2]) for j in range(i2 + 1, i1))
            if v1 < level and v2 < level:            # double bottom
                if any(self._hist[j][4] > level for j in range(i1, n - 1)) \
                        and self._retest_long_pred(level)(n - 1, newest):
                    return 'LONG', level, min(v1, v2), level - min(v1, v2)
        return None

    def _hs_top(self) -> tuple | None:
        """(head, right_shoulder_price, neckline, right_shoulder_idx) for an
        H&S top on the history; None when no structure exists."""
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
        neckline = max(max(lt), max(rt))        # flat neckline: higher trough
        if neckline >= head:
            return None
        return head, right, neckline, ri

    def _hs_bottom(self) -> tuple | None:
        """(head, left_shoulder_price, neckline, right_shoulder_idx) for an
        H&S bottom; None when no structure exists."""
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
        neckline = min(min(lp), min(rp))        # flat neckline: lower peak
        if neckline <= head:
            return None
        return head, left, neckline, ri

    def _variant_c(self, n: int) -> tuple | None:
        """Neckline retest for a head-and-shoulders (top or bottom). The
        pattern height is the head-to-neckline distance (1:1 objective)."""
        newest = self._hist[n - 1]
        top = self._hs_top()
        if top is not None:
            head, right, neckline, ri = top
            if any(self._hist[j][4] < neckline for j in range(ri, n - 1)):
                if self._retest_short_pred(neckline)(n - 1, newest):
                    return 'SHORT', neckline, right, head - neckline
        bottom = self._hs_bottom()
        if bottom is not None:
            head, left, neckline, ri = bottom
            if any(self._hist[j][4] > neckline for j in range(ri, n - 1)):
                if self._retest_long_pred(neckline)(n - 1, newest):
                    return 'LONG', neckline, left, neckline - head
        return None

    # --- evaluate / still_valid -----------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.swing_high_10', f'{sym}.swing_low_10']
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
        if self.variant_id == 'a':
            hit = self._variant_a(f, n)
        elif self.variant_id == 'b':
            hit = self._variant_b(n)
        else:
            hit = self._variant_c(n)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, level, stop_price, height = hit
        if direction == 'LONG':
            stop_r = (close - stop_price) / atr
        else:
            stop_r = (stop_price - close) / atr
        # 1:1 measuring objective (Ch13.2 p499-501): for variant a there is no
        # underlying pattern, so the target is the family default (1R); for
        # b/c the target is the 1:1 projection of the pattern height,
        # expressed in R with the atr unit (D-028: R is a price distance).
        if self.variant_id == 'a':
            target_r = 1.0
        else:
            target_r = height / atr
        if stop_r <= 0 or target_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._retest_long_pred(level) if direction == 'LONG' \
            else self._retest_short_pred(level)
        anchor = self.find_setup_anchor(self._hist, pred)
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
        """The thesis is "the retest holds": price must stay on the flipped
        side of the FROZEN retested level. A close back through it says the
        retest failed and the reason to hold is gone."""
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
