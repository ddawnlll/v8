"""Volume-climax reversal behavior family (`volume_climax_reversal`).

Hypothesis: a volume overextension marks a likely top or bottom — a selling
climax at a bottom and a buying climax (blow-off) at a top (Ch6.1 p182-185).
The signal is a CANDIDATE, never a labeled top/bottom: "overbought/oversold
in volume terms can only be identified in retrospect", so the trade is a
counter-trend fade entered on the next bar close (Ch9.9.3.12 p320:
"extreme bullishness is potentially bearish"). Price confirmation is the
frozen level: the climax extreme must not be exceeded.

Four book variants, all on the 100-bar 2-sigma volume overextension
(vol_zscore) or the volume-minimum / bar-class predicates:
  a  Selling-climax bottom: vol_zscore >= 2.0 in a downtrend (ema_fast <
     ema_slow) -> LONG fade.
  b  Buying-climax top: vol_zscore >= 2.0 in an uptrend (ema_fast >
     ema_slow) -> SHORT fade.
  c  Low-volume top/bottom: volume near its historical minimum
     (vol_min_proximity < 0.4) at a local extreme -> counter-trend (the
     distinction from a climax is the volume level itself, Ch6.1 p185).
  d  2-sigma overextension confirmed by a High-Vol Reversal bar
     (bar_class == 1, the squat-bar idea: large volume on a reversal bar,
     Ch6.1 p197-199) -> fade in the bar's own direction.
  e  D-055 strict-climax challenger: vol_zscore >= 3.0 in a trend -> fade
     (LONG after a selling climax, SHORT after a buying climax). Declared and
     frozen pre-holdout; competes with a-d in the within-family Reality-Check
     on the frozen OOS (D-044), never selected on the dev window.

evaluate() emits ONE CandidateDraft per bar for the highest-priority variant
whose gate fires (declared priority e > d > c > b > a: most restrictive
first; the strict 3-sigma variant owns every 3-sigma bar). All five variants
count as one multiplicity unit (rule 13; D-044 variants_evaluated) and are
distinguished by the `variant` geometry key.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class VolumeClimaxReversalExpert(Expert):
    """Fade a volume climax / overextension at a local extreme."""
    expert_id = 'volume_climax_reversal'
    version = 'v2'
    mechanism_family_id = 'volume_exhaustion'
    behavior_family_id = 'volume_climax_reversal'
    variant_id = 'a'
    variants_evaluated = ('a', 'b', 'c', 'd', 'e')
    search_universe_size = 5
    requires = ('trend', 'volatility', 'participation', 'history')

    # Declared, LOCKED constants (D-036 pattern: declared, never fitted).
    CLIMAX_Z = 2.0               # 2-sigma volume overextension (book, N=100)
    # D-055 challenger: a STRICT climax at 3-sigma. The dev diagnostic measured
    # the 2-sigma gate as over-broad (8,272 distinct candidates on 8,760 bars ->
    # a 4.6% D-027 execution_share, the family flooding the exposure pool). The
    # 3-sigma variant owns every bar with vol_zscore >= 3.0; it is declared and
    # frozen pre-holdout and competes with a/b/c/d in the within-family
    # Reality-Check on the frozen OOS (D-044) — never selected on the dev window.
    CLIMAX_Z_STRICT = 3.0
    LOW_VOL_PROXIMITY_MAX = 0.4
    HIGH_VOL_REVERSAL_BAR = 1.0  # bar_class value: high-volume reversal bar
    VARIANTS = ('e', 'd', 'c', 'b', 'a')     # single-draft gate priority

    def _evaluate_variants(self, state: MarketState, sym: str,
                           f: dict, close: float) -> tuple[str, str] | None:
        """(variant_id, direction) for the first variant whose gate fires, in
        declared priority order; None = stand down. The setup is the CURRENT
        bar (the climax / overextension bar), so no per-bar anchor predicate is
        needed: the D-026 anchor is the detection bar (see evaluate())."""
        zs = f.get(f'{sym}.vol_zscore')
        z_over = (zs is not None and zs.value is not None
                  and float(zs.value) >= self.CLIMAX_Z)
        z_strict = (zs is not None and zs.value is not None
                    and float(zs.value) >= self.CLIMAX_Z_STRICT)
        for variant in self.VARIANTS:
            if variant == 'e':
                # D-055 strict-climax challenger: a 3-sigma overextension is a
                # stronger climax; fade it in the trend direction (LONG after a
                # 3-sigma selling climax, SHORT after a 3-sigma buying climax).
                # Owns every 3-sigma bar; the 2-sigma a/b/d gates serve the rest.
                if z_strict:
                    fast = f.get(f'{sym}.ema_fast')
                    slow = f.get(f'{sym}.ema_slow')
                    if fast is not None and fast.value is not None \
                            and slow is not None and slow.value is not None:
                        if float(fast.value) < float(slow.value):
                            return ('e', 'LONG')
                        if float(fast.value) > float(slow.value):
                            return ('e', 'SHORT')
            elif variant == 'd':
                bc = f.get(f'{sym}.bar_class')
                if z_over and bc is not None and bc.value is not None \
                        and float(bc.value) == self.HIGH_VOL_REVERSAL_BAR:
                    # The reversal bar's own direction decides the fade.
                    o = self._hist[-1][1]
                    if close > o:
                        return ('d', 'LONG')
                    if close < o:
                        return ('d', 'SHORT')
            elif variant == 'c':
                prox = f.get(f'{sym}.vol_min_proximity')
                if prox is not None and prox.value is not None \
                        and float(prox.value) < self.LOW_VOL_PROXIMITY_MAX:
                    slow = f.get(f'{sym}.ema_slow')
                    if slow is None or slow.value is None:
                        continue
                    slow_v = float(slow.value)
                    if close < slow_v:
                        return ('c', 'LONG')
                    if close > slow_v:
                        return ('c', 'SHORT')
            elif variant == 'b':
                if z_over:
                    fast = f.get(f'{sym}.ema_fast')
                    slow = f.get(f'{sym}.ema_slow')
                    if fast is not None and fast.value is not None \
                            and slow is not None and slow.value is not None \
                            and float(fast.value) > float(slow.value):
                        return ('b', 'SHORT')
            else:  # 'a'
                if z_over:
                    fast = f.get(f'{sym}.ema_fast')
                    slow = f.get(f'{sym}.ema_slow')
                    if fast is not None and fast.value is not None \
                            and slow is not None and slow.value is not None \
                            and float(fast.value) < float(slow.value):
                        return ('a', 'LONG')
        return None

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.ema_fast', f'{sym}.ema_slow',
                f'{sym}.atr', f'{sym}.volume', f'{sym}.history']
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
        # The 100-bar volume-stat features (vol_zscore / vol_min_proximity)
        # are this family's habitat: absent until the window fills, and a tape
        # without either cannot express a volume-climax predicate at all.
        zs = f.get(f'{sym}.vol_zscore')
        prox = f.get(f'{sym}.vol_min_proximity')
        if (zs is None or zs.value is None) and (prox is None or prox.value is None):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hit = self._evaluate_variants(state, sym, f, close)
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        variant, direction = hit
        # The climax extreme is FROZEN at detection: the level below which a
        # selling climax is not exhausted (LONG) / above which a buying climax
        # is not exhausted (SHORT). A live-recomputed extreme drifts with the
        # adverse move and the invalidation would never fire on a re-extreme.
        level = float(self._hist[-1][3]) if direction == 'LONG' \
            else float(self._hist[-1][2])
        ref_key = 'prior_low_ref' if direction == 'LONG' else 'prior_high_ref'
        # The setup is a discrete EVENT — the climax bar itself — and the
        # per-bar volume state is not carried in the history tuples, so the
        # D-026 anchor is the DETECTION bar (the newest closed bar), never the
        # run start of a trend predicate. Anchoring on the trend run would
        # collapse every distinct climax inside one trend into a single episode
        # (episode_key hashes the anchor): a second selling climax in the same
        # downtrend would be suppressed as a duplicate instead of re-entering.
        anchor = self._hist[-1][0]
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{close:.6f}:{level:.6f}:{variant}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr, 'variant': variant,
                           ref_key: level},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the climax was exhaustion": price must NOT exceed
        the frozen climax extreme. A LONG fade is dead on a new low below the
        selling-climax bar (the selling was not exhausted); a SHORT fade is
        dead on a new high above the buying-climax bar."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True          # unobservable: fail open, price still governs
        if draft.direction == 'LONG':
            ref = draft.risk_geometry.get('prior_low_ref')
            if ref is None:
                return True
            return float(close.value) > float(ref)
        ref = draft.risk_geometry.get('prior_high_ref')
        if ref is None:
            return True
        return float(close.value) < float(ref)
