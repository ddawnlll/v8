"""Gap-reaction behavior family (`gap_exhaustion`).

Hypothesis (mechanism `gap_reaction`; Ch3.2 p72, Ch5.8 p166-167, Ch13.3
p513): a type-3 gap (open beyond the prior bar's extreme) classified by its
place in the gap sequence carries a directional claim — the first gap out of
a range is a BREAKAWAY (continuation), the second gap in the trend is a
RUNAWAY (continuation), and the THIRD gap is an EXHAUSTION gap that tends to
fill (reversal). Gap zones persist as support/resistance until filled
(Ch5.8).

Variants (D-044):
  a  third-gap exhaustion reversal: the third same-direction gap in the
     window whose bar FAILS to hold the gap direction (up-gap closes down,
     down-gap closes up) -> reversal (SHORT after an up-gap, LONG after a
     down-gap). The thesis is that the exhaustion gap fills.
  b  breakaway-gap breakout: the FIRST gap in the direction that opens beyond
     the 20-bar range (out of a consolidation) -> continuation in the gap
     direction; the thesis is that the gap HOLDS.
  c  runaway/midway gap continuation: the SECOND gap in the direction with a
     close that holds the gap -> continuation.

The card's variant d (gap zone as S/R + gap-fill expectation) is folded into
the geometry of a-c: the gap zone IS the stop/level reference and the thesis
("gap fills" for exhaustion, "gap holds" for continuation) is `still_valid`.
The book gives no stop/target numbers for gaps -> the family default
geometry (1R:1R:8bar, Ch14 doctrine) with the gap zone as the frozen S/R
reference (prior_high_ref/prior_low_ref pattern). Crypto perps gap rarely
(liquidations/maintenance squeezes), so low episode counts are expected and
honest (V8_LOGIC_GAP H07).

The gap direction and zone are FROZEN at detection; the anchor is the first
bar of the current run where the variant's own predicate holds (D-026).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class GapExhaustionExpert(Expert):
    """Gap-sequence reaction expert (exhaustion / breakaway / runaway)."""
    expert_id = 'gap_exhaustion'
    version = 'v1'
    mechanism_family_id = 'gap_reaction'
    behavior_family_id = 'gap_reaction'
    variant_id = 'a'
    # D-044: every implemented variant (losers included); the reported
    # variant_id is a member. D-046: all thresholds are declared constants
    # frozen pre-window, so the search universe equals the evaluated set.
    variants_evaluated = ('a', 'b', 'c')
    search_universe_size = 3
    requires = ('candle_shape', 'location', 'volatility', 'history')

    # Declared, LOCKED (D-036): the same-direction gap-count window.
    GAP_COUNT_WINDOW = 20

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    # --- gap primitives over the history window -------------------------------

    def _gap_of(self, i: int) -> int:
        """Direction of history bar i's type-3 gap (-1, 0, +1)."""
        if i == 0:
            return 0
        o = float(self._hist[i][1])
        ph = float(self._hist[i - 1][2])
        pl = float(self._hist[i - 1][3])
        if o > ph:
            return 1
        if o < pl:
            return -1
        return 0

    def _count_dir(self, i: int, direction: int) -> int:
        """Same-direction gaps within the trailing window ending at bar i."""
        start = max(1, i - self.GAP_COUNT_WINDOW + 1)
        return sum(1 for j in range(start, i + 1)
                   if self._gap_of(j) == direction)

    def _zone(self, i: int, direction: int) -> tuple[float, float]:
        """(top, bottom) of bar i's gap zone (marketstate G-27 semantics)."""
        o = float(self._hist[i][1])
        if direction == 1:
            return o, float(self._hist[i - 1][2])
        return float(self._hist[i - 1][3]), o

    # --- per-bar predicates (D-026 anchor scan) -------------------------------

    def _exhaustion_pred(self, direction: int):
        def pred(i: int, bar: tuple) -> bool:
            if i == 0 or self._gap_of(i) != direction:
                return False
            if self._count_dir(i, direction) < 3:
                return False
            o, c = float(bar[1]), float(bar[4])
            if direction == 1:
                return c < o            # up-gap stall -> reversal
            return c > o
        return pred

    def _breakaway_pred(self, direction: int):
        def pred(i: int, bar: tuple) -> bool:
            if i == 0 or self._gap_of(i) != direction:
                return False
            if self._count_dir(i, direction) != 1:
                return False
            o = float(bar[1])
            lo = max(0, i - 20)
            if direction == 1:
                return o > max(float(self._hist[j][2]) for j in range(lo, i))
            return o < min(float(self._hist[j][3]) for j in range(lo, i))
        return pred

    def _runaway_pred(self, direction: int):
        def pred(i: int, bar: tuple) -> bool:
            if i == 0 or self._gap_of(i) != direction:
                return False
            if self._count_dir(i, direction) != 2:
                return False
            o, c = float(bar[1]), float(bar[4])
            if direction == 1:
                return c > o            # the gap holds
            return c < o
        return pred

    # --- evaluate / still_valid -----------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        common = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                  f'{sym}.gap_dir', f'{sym}.gap_size', f'{sym}.gap_levels']
        need = common + [f'{sym}.window_high_20', f'{sym}.window_low_20'] \
            if self.variant_id == 'b' else common
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
        if n < 2:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        gd = f[f'{sym}.gap_dir']
        direction = int(round(float(gd.value)))
        if direction == 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        o = float(self._hist[n - 1][1])
        c = float(self._hist[n - 1][4])
        top, bottom = self._zone(n - 1, direction)
        # The current gap zone must be present in gap_levels (still unfilled).
        gl = f[f'{sym}.gap_levels']
        if gl is None or gl.value is None or not gl.value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        ztop, zbottom, zd = gl.value[-1]
        if not (int(round(float(zd))) == direction
                and abs(float(ztop) - top) < 1e-9
                and abs(float(zbottom) - bottom) < 1e-9):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        count = self._count_dir(n - 1, direction)
        if self.variant_id == 'a':
            if count < 3:
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            if direction == 1 and not (c < o):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            if direction == -1 and not (c > o):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            pred = self._exhaustion_pred(direction)
            trade_dir = 'SHORT' if direction == 1 else 'LONG'
        elif self.variant_id == 'b':
            wh = f.get(f'{sym}.window_high_20')
            wl = f.get(f'{sym}.window_low_20')
            if direction == 1 and (wh is None or wh.value is None
                                   or not (o > float(wh.value))):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            if direction == -1 and (wl is None or wl.value is None
                                    or not (o < float(wl.value))):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            if count != 1 or (direction == 1 and not (c > top)) \
                    or (direction == -1 and not (c < bottom)):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            pred = self._breakaway_pred(direction)
            trade_dir = 'LONG' if direction == 1 else 'SHORT'
        else:  # 'c' — runaway
            if count != 2 or (direction == 1 and not (c > top)) \
                    or (direction == -1 and not (c < bottom)):
                return ExpertEvaluation(self.expert_id, self.version,
                                        state.state_id, 'NOT_APPLICABLE',
                                        'NO_SETUP', t)
            pred = self._runaway_pred(direction)
            trade_dir = 'LONG' if direction == 1 else 'SHORT'
        # Gap-zone S/R reference, FROZEN at detection: the level is the far
        # side of the gap zone (the gap-fill boundary).
        if trade_dir == 'LONG':
            ref = bottom
            stop_r = (close - bottom) / atr
            prior_low_ref = bottom
        else:
            ref = top
            stop_r = (top - close) / atr
            prior_high_ref = top
        if stop_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(self._hist, pred)
        geometry = {'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                    'stop_r': stop_r, 'expiry_bars': 8, 'atr_ref': atr,
                    'variant': self.variant_id,
                    'level_ref': ref, 'stop_ref': ref,
                    'gap_top_ref': top, 'gap_bottom_ref': bottom}
        if trade_dir == 'LONG':
            geometry['prior_low_ref'] = prior_low_ref
        else:
            geometry['prior_high_ref'] = prior_high_ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=trade_dir,
            setup_fingerprint=(f'{sym}:{self.variant_id}:{trade_dir}:'
                               f'{close:.6f}:{top:.6f}:{bottom:.6f}'),
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is the gap zone: a continuation thesis dies when the gap
        FILLS (close back through the frozen far side); an exhaustion thesis
        dies when the gap does NOT fill (close back through the near side).
        Fails open when the close is unobservable."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True          # unobservable: fail open, price still governs
        top = draft.risk_geometry.get('gap_top_ref')
        bottom = draft.risk_geometry.get('gap_bottom_ref')
        if top is None or bottom is None:
            return True
        if draft.direction == 'LONG':
            return float(close.value) > float(bottom)
        return float(close.value) < float(top)
