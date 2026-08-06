"""Volume-gated breakout behavior family (`volume_confirmed_breakout`).

Hypothesis: a close beyond the windowed prior extreme is a breakout setup
ONLY when volume confirms it. Volume is a positive confirmation gate layered
on the breakout trigger (Dow: "volume should be increasing in the direction
of the trend", Ch2.2 p61; Ch6.1 p174-181) — never a stop or target input and
never a standalone entry signal (volume is secondary to price, Ch6.1 p176).

Four book variants share one breakout trigger — close beyond the 20-bar
windowed prior extreme — and differ only in the volume gate:
  a  Dow volume confirmation: breakout-bar volume above its 20-bar smoothed
     average (expanding volume in the breakout direction).
  b  Low-volume breakout timing: volume near its historical minimum
     (vol_min_proximity < 0.4) yet expanding above the smoothed average
     (Ch6.1 p180: "whenever volume declines close to its lowest historical
     level, a breakout is expected" — the increase on the breakout bar is
     the confirmation).
  c  High-volume continuation-bar confirm: breakout-bar volume >= 1.2x the
     smoothed average.
  d  Volume spike, not climax: a >= 2.0x spike that is NOT a 2-sigma
     overextension (vol_zscore < 2.0) — an overextended climax spike belongs
     to the volume_exhaustion family, not to a continuation confirmation.

evaluate() emits ONE CandidateDraft per bar for the highest-priority variant
whose gate fires (declared priority d > c > b > a: most restrictive first, so
every variant owns a non-empty domain and the single-draft dispatch is
deterministic). All four variants count as one multiplicity unit in the
family-level correction (rule 13; D-044 variants_evaluated) and are
distinguished by the `variant` geometry key so episode attribution is exact.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert


class VolumeConfirmedBreakoutExpert(Expert):
    """Close beyond the 20-bar windowed prior extreme, volume-confirmed."""
    expert_id = 'volume_confirmed_breakout'
    version = 'v1'
    mechanism_family_id = 'volume_confirmation'
    behavior_family_id = 'volume_confirmed_breakout'
    variant_id = 'a'
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 4
    requires = ('location', 'volatility', 'participation', 'history')

    # Declared, LOCKED constants (D-036 pattern: declared, never fitted).
    BREAKOUT_WINDOW = 20        # Donchian window (matches window_high_20)
    LOW_VOL_PROXIMITY_MAX = 0.4
    HIGH_VOL_MULT = 1.2
    SPIKE_MULT = 2.0
    CLIMAX_Z = 2.0
    VARIANTS = ('d', 'c', 'b', 'a')     # single-draft gate priority

    def _prior_high(self, i: int) -> float:
        lo = max(0, i - self.BREAKOUT_WINDOW)
        return max(h for (_e, _o, h, _l, _c, _f, _s) in self._hist[lo:i])

    def _prior_low(self, i: int) -> float:
        lo = max(0, i - self.BREAKOUT_WINDOW)
        return min(l for (_e, _o, _h, l, _c, _f, _s) in self._hist[lo:i])

    def _long_pred(self, i: int, bar: tuple) -> bool:
        """Close above the windowed prior high (bounded at the history edge:
        anchors older than the 32-bar window are unstable — documented bound)."""
        if i == 0:
            return False
        _e, _o, _h, _l, close, _f, _s = bar
        return close > self._prior_high(i)

    def _short_pred(self, i: int, bar: tuple) -> bool:
        if i == 0:
            return False
        _e, _o, _h, _l, close, _f, _s = bar
        return close < self._prior_low(i)

    def _evaluate_variants(self, f: dict, sym: str, sma: float) -> str | None:
        """First variant whose volume gate fires, in declared priority order."""
        volume = float(f[f'{sym}.volume'].value)
        for variant in self.VARIANTS:
            if variant == 'd':
                zs = f.get(f'{sym}.vol_zscore')
                if (sma > 0 and volume >= self.SPIKE_MULT * sma
                        and zs is not None and zs.value is not None
                        and float(zs.value) < self.CLIMAX_Z):
                    return variant
            elif variant == 'c':
                if sma > 0 and volume >= self.HIGH_VOL_MULT * sma:
                    return variant
            elif variant == 'b':
                prox = f.get(f'{sym}.vol_min_proximity')
                if (prox is not None and prox.value is not None
                        and float(prox.value) < self.LOW_VOL_PROXIMITY_MAX
                        and sma > 0 and volume > sma):
                    return variant
            else:  # 'a'
                if sma > 0 and volume > sma:
                    return variant
        return None

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.volume',
                f'{sym}.vol_smooth_ma', f'{sym}.history']
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
        # The breakout levels are the windowed prior extremes of the newest
        # bar (window_high_20 / window_low_20), warmup-gated: a tape without
        # a 20-bar window has no range to break out of.
        wh = f.get(f'{sym}.window_high_20')
        wl = f.get(f'{sym}.window_low_20')
        if wh is None or wh.value is None or wl is None or wl.value is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        long_level = float(wh.value)
        short_level = float(wl.value)
        if not (close > long_level or close < short_level):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        variant = self._evaluate_variants(f, sym,
                                          float(f[f'{sym}.vol_smooth_ma'].value))
        if variant is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        if close > long_level:
            direction, level, ref_key = 'LONG', long_level, 'prior_low_ref'
            pred = self._long_pred
        else:
            direction, level, ref_key = 'SHORT', short_level, 'prior_high_ref'
            pred = self._short_pred
        anchor = self.find_setup_anchor(self._hist, pred)
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
        """The thesis is "the volume-confirmed breakout holds": price must
        stay on the breakout side of the FROZEN broken level. A close back
        through the level says the breakout did not hold, whatever the stop
        distance still says (Ch4.1 p104: "close back inside the range")."""
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
