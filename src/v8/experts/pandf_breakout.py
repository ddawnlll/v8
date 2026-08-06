"""Point-and-Figure boxed-price breakout behavior family (`pandf_breakout`).

Hypothesis (mechanism `boxed_price_breakout`): a boxed-price representation of
the close series (columns of X rising / O falling, Ch15.1 p599) makes double
and triple top/bottom breakouts mechanically detectable — a new X above the
prior column's top is a buy signal, a new O below the prior column's bottom is
a sell signal (Ch15.2 p600-617). Targets use the book's vertical count:
`lowestBoxPrice + (breakoutColBoxes * boxSize * reversalSize)` (Ch15.3
p620-623). Stops sit below the lowest X in the breakout column (bullish) /
above the highest O in the breakout column (bearish) (Ch15.2 p617).

The box filter is DECLARED and LOCKED (orchestrator directive): box = 1.0 *
ATR at detection, reversal = 3 boxes. The P&F transform is computed INSIDE the
expert from the state's `history` close window (no marketstate box/reversal
representation exists — V8_LOGIC_GAP H07).

Documented deviations: (1) the catapult signal requires a two-stage partial
entry (position scaling), which is O-013-gated — not implemented (CRITIC 4.2);
(2) the ascending/descending/spread-triple signals are angle classifications
of the column ladder with no numeric book spec — not implemented; (3) box-grid
alignment is anchored to the column structure rather than an absolute price
grid (a volatility-based box has no natural absolute grid).

Variants (all frozen; D-044 lists every implemented variant):
  a  double-top box breakout (LONG): the current X column's top exceeds the
     prior X column's top.
  b  double-bottom box breakout (SHORT): the current O column's bottom is
     below the prior O column's bottom.
  c  triple-top box breakout (LONG): the current X column's top exceeds both
     prior X column tops.
  d  triple-bottom box breakout (SHORT): the current O column's bottom is
     below both prior O column bottoms.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, LOCKED box filter (orchestrator directive): box = 1.0 * ATR at
# detection, reversal = 3 boxes.
BOX_ATR_K = 1.0
REVERSAL_BOXES = 3
# Minimum history for a meaningful column structure.
MIN_HISTORY_BARS = 20


def _columns(closes: list, box: float, reversal: int):
    """Deterministic close-based P&F columns.

    Returns a list of (direction, start_idx, levels):
      direction: +1 = X column (rising), -1 = O column (falling)
      start_idx: index of the first close that contributed to the column
      levels: box prices in the column, ordered from the column's origin to
      its extreme (rising for X, falling for O).
    A bar that stays inside the current column's box range is absorbed
    (contributes nothing); a move of >= `reversal` boxes in the opposite
    direction starts a new column one box beyond the extreme.
    """
    cols: list[tuple[int, int, list]] = []
    cur = None
    for i, c in enumerate(closes):
        if cur is None:
            cur = (1, i, [c])
            continue
        d, start, levels = cur
        if d > 0:
            top = levels[-1]
            if c >= top + box:
                add = int((c - top) // box)
                for k in range(1, add + 1):
                    levels.append(top + box * k)
                continue
            if c <= top - reversal * box:
                new_levels = [top - box]
                add = int((top - box - c) // box)
                for k in range(1, add + 1):
                    new_levels.append(top - box - box * k)
                cols.append((d, start, levels))
                cur = (-1, i, new_levels)
                continue
        else:
            bottom = levels[-1]
            if c <= bottom - box:
                add = int((bottom - c) // box)
                for k in range(1, add + 1):
                    levels.append(bottom - box * k)
                continue
            if c >= bottom + reversal * box:
                new_levels = [bottom + box]
                add = int((c - bottom - box) // box)
                for k in range(1, add + 1):
                    new_levels.append(bottom + box + box * k)
                cols.append((d, start, levels))
                cur = (1, i, new_levels)
                continue
    if cur is not None:
        cols.append((cur[0], cur[1], cur[2]))
    return cols


class PandfBreakoutExpert(Expert):
    """Double/triple top-bottom boxed-price breakout."""
    expert_id = 'pandf_breakout'
    version = 'v1'
    mechanism_family_id = 'boxed_price_breakout'
    behavior_family_id = 'boxed_price_breakout'
    variant_id = 'a'
    # D-044: every implemented variant, losers included. The book card's
    # signal grid enumerates 8 signals (double/triple top/bottom, ascending/
    # descending/spread triple, catapult); the 4 implemented variants plus the
    # 4 dropped (angle-classification triples and the O-013 catapult) are the
    # consumed search universe.
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 8
    requires = ('volatility', 'history')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            self.variant_id = variant_id

    @staticmethod
    def _signal(cols, variant_id):
        """(direction, anchor_idx, col_bottom, col_top, col_boxes) for the
        signal, or None. A double/triple top requires the current column to be
        an X column whose top exceeds the prior X column top(s); bottoms
        mirror on O columns."""
        if not cols:
            return None
        d_last, start_last, levels_last = cols[-1]
        xs = [c for c in cols if c[0] > 0]
        os_ = [c for c in cols if c[0] < 0]
        if variant_id == 'a':
            if d_last > 0 and len(xs) >= 2 \
                    and levels_last[-1] > xs[-2][2][-1]:
                return ('LONG', start_last, levels_last[0], levels_last[-1],
                        len(levels_last) - 1)
            return None
        if variant_id == 'b':
            if d_last < 0 and len(os_) >= 2 \
                    and levels_last[-1] < os_[-2][2][-1]:
                return ('SHORT', start_last, levels_last[-1], levels_last[0],
                        len(levels_last) - 1)
            return None
        if variant_id == 'c':
            if d_last > 0 and len(xs) >= 3 \
                    and levels_last[-1] > max(xs[-2][2][-1], xs[-3][2][-1]):
                return ('LONG', start_last, levels_last[0], levels_last[-1],
                        len(levels_last) - 1)
            return None
        if d_last < 0 and len(os_) >= 3 \
                and levels_last[-1] < min(os_[-2][2][-1], os_[-3][2][-1]):
            return ('SHORT', start_last, levels_last[-1], levels_last[0],
                    len(levels_last) - 1)
        return None

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: unknown variant {self.variant_id!r} '
                f'(variants_evaluated={list(self.variants_evaluated)})')
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
        if atr is None or atr <= 0 or not isinstance(hist_value, (tuple, list)) \
                or not hist_value or len(hist_value) < MIN_HISTORY_BARS:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(hist_value)
        box = float(atr) * BOX_ATR_K
        if box <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        closes = [float(b[4]) for b in hist]
        hit = self._signal(_columns(closes, box, REVERSAL_BOXES),
                           self.variant_id)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, anchor_idx, col_bottom, col_top, col_boxes = hit
        anchor = hist[anchor_idx][0]
        if direction == 'LONG':
            # Stop below the lowest X in the breakout column; target = the
            # vertical count (Ch15.3): lowest box + boxes * box * reversal.
            stop_price = col_bottom
            target_price = col_bottom + col_boxes * box * REVERSAL_BOXES
            prior_low_ref = col_bottom
            prior_high_ref = None
        else:
            stop_price = col_top
            target_price = col_top - col_boxes * box * REVERSAL_BOXES
            prior_high_ref = col_top
            prior_low_ref = None
        stop_r = (close - stop_price) / float(atr) if direction == 'LONG' \
            else (stop_price - close) / float(atr)
        target_r = (target_price - close) / float(atr) if direction == 'LONG' \
            else (close - target_price) / float(atr)
        if stop_r <= 0 or target_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        geometry = {
            'entry': 'NEXT_BAR_CLOSE', 'target_r': target_r, 'stop_r': stop_r,
            'expiry_bars': 8, 'atr_ref': float(atr), 'variant': self.variant_id,
            'reversal': REVERSAL_BOXES,
        }
        if prior_low_ref is not None:
            geometry['prior_low_ref'] = prior_low_ref
        if prior_high_ref is not None:
            geometry['prior_high_ref'] = prior_high_ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction}:{close:.6f}',
            risk_geometry=geometry, birth_time=t,
            setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the boxed breakout is in force": a long must stay
        above the frozen breakout reference (the lowest X in the breakout
        column — the level a close below would retrace the whole column), a
        short below the highest O. A close through the reference says the
        breakout failed. Fails open when the close is unobservable."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        close = float(close.value)
        if draft.direction == 'LONG':
            ref = draft.risk_geometry.get('prior_low_ref')
            if ref is None:
                return True
            return close > float(ref)
        ref = draft.risk_geometry.get('prior_high_ref')
        if ref is None:
            return True
        return close < float(ref)
