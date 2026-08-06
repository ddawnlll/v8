"""Market Profile value-area behavior family (`market_profile_value_area`).

Hypothesis (mechanism `value_area_reversion`): price reacts to the prior
session's value structure — the point of control (POC), the 68% value area
and the TPO-count pressure gauge (Ch17.1 p655-665, Ch17.2 p665-669). Price
that trades outside the value region reverts toward the value center (POC);
price that moves beyond value on heavy TPO pressure is initiative and
continues toward the prior-day range extreme.

The profile is computed INSIDE the expert from the state's `history` OHLC
window (D-026 32-bar pin, O-020: no per-session histogram state exists): each
bar contributes one TPO to every price bucket its [low, high] range touches;
the POC is the bucket with the most TPOs (ties resolve to the bucket nearest
the session mid, lower line wins — Ch17.1 p656-657); the 68% value area
expands from the POC one bucket at a time, adding the larger side until the
target TPO share is reached (Ch17.1 p656-657).

Declared constants (never fitted, D-036 pattern): bucket size = 1.0 * ATR at
detection; value area = 68%; pressure threshold = 55%; VA-exit distance gate
= 0.5 * ATR; minimum prior-session bars = 12.

Documented deviations: (1) the state contract carries no per-bar volume, so
the profile uses TPO (bar) counts — the book's primary definition — rather
than volume weighting (the G-29 volume leg exists only for the current bar);
(2) the 32-bar `history` pin bounds the prior-session window, so the full
prior day is present only while bar_of_session <= 8, degrading to the most
recent prior-session bars afterwards (O-020; CRITIC 3.3); (3) the participant
classification (initiative vs responsive) is behavioral (HAND_EXPERTS 3 #27)
and only names the mechanism.

Variants (all frozen; D-044 lists every implemented variant):
  a  prior-day POC as S/R: a close below the POC reverts up to the POC; a
     close above it reverts down (Ch17.2 responsive activity).
  b  prior-day 68% value area as an S/R zone: a close beyond a VA boundary
     reverts to the POC.
  c  TPO-count pressure gauge: above-POC TPO share >= 55% is buying pressure;
     a close beyond the VA high in that regime is initiative buying that
     continues to the prior-day range high. Mirror below.
  d  value-area 68% reversion with a distance gate: a close beyond a VA
     boundary by >= 0.5 * ATR reverts to the POC.
The book card's variant `e` (six degrees of bullishness/bearishness) requires
the participant classification, which is behavioral — not implemented
(HAND_EXPERTS 3 #27; CRITIC 4.3).
"""
from __future__ import annotations

import math

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# --- Declared, LOCKED constants (D-036 pattern: "declared, never fitted"). ---
PROFILE_BUCKET_ATR_FRAC = 1.0     # price bucket = 1.0 * ATR at detection
VALUE_AREA_FRAC = 0.68            # book: value area = 68% of TPOs (Ch17.1)
SESSION_BARS = 24                 # 1h bars per UTC session (00:00 UTC anchor)
MIN_PRIOR_BARS = 12               # minimum prior-session bars for a profile
PRESSURE_THRESHOLD = 0.55         # TPO-pressure share for variant c
VA_EXIT_DISTANCE_ATR = 0.5        # variant d: outside VA by >= 0.5 * ATR


def _tpo_profile(prior_bars, bucket: float, value_area_frac: float):
    """TPO profile of the prior session.

    Each bar contributes one TPO to every bucket its [low, high] range
    touches (Ch17.1). Returns (poc_price, va_low, va_high, total_tpos,
    above_share, below_share); None when no bar contributes. The POC is the
    bucket with the most TPOs; ties resolve to the bucket nearest the session
    mid-price, lower line wins (Ch17.1 p656-657). The 68% value area expands
    from the POC one bucket at a time, adding the larger side until the
    cumulative share reaches the target.
    """
    counts: dict[int, int] = {}
    for b in prior_bars:
        lo = int(float(b[3]) // bucket)
        hi = int(float(b[2]) // bucket)
        for idx in range(lo, hi + 1):
            counts[idx] = counts.get(idx, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return None
    highs = [float(b[2]) for b in prior_bars]
    lows = [float(b[3]) for b in prior_bars]
    mid_idx = int((max(highs) + min(lows)) / 2.0 // bucket)
    # max by (count desc, |dist to mid| asc, lower index wins).
    poc_idx = max(counts,
                  key=lambda i: (counts[i], -abs(i - mid_idx), -i))
    target = math.ceil(value_area_frac * total)
    cum = counts[poc_idx]
    lo_i = hi_i = poc_idx
    while cum < target:
        left = counts.get(lo_i - 1, 0)
        right = counts.get(hi_i + 1, 0)
        if left == 0 and right == 0:
            break
        if right > left:
            hi_i += 1
            cum += counts.get(hi_i, 0)
        else:
            lo_i -= 1
            cum += counts.get(lo_i, 0)
    above = sum(v for k, v in counts.items() if k > poc_idx)
    below = sum(v for k, v in counts.items() if k < poc_idx)
    return (poc_idx * bucket, lo_i * bucket, hi_i * bucket, total,
            above / total, below / total)


class MarketProfileValueAreaExpert(Expert):
    """POC / value-area / TPO-pressure reaction to the prior session."""
    expert_id = 'market_profile_value_area'
    version = 'v1'
    mechanism_family_id = 'value_area_reversion'
    behavior_family_id = 'value_area_reversion'
    variant_id = 'a'
    # D-044: every implemented variant, losers included. The book card lists
    # variants a..e; `e` (six degrees of bullishness/bearishness) needs the
    # behavioral participant classification and is not implemented (dropped
    # before evaluation, counted in search_universe_size).
    variants_evaluated = ('a', 'b', 'c', 'd')
    search_universe_size = 5
    requires = ('session', 'volatility', 'history')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            self.variant_id = variant_id

    def _profile(self, hist, atr, bof):
        """Prior-session TPO profile + range; None when not computable."""
        if bof <= 0 or len(hist) <= int(bof):
            return None
        bucket = atr * PROFILE_BUCKET_ATR_FRAC
        if bucket <= 0:
            return None
        prior_sess = hist[:len(hist) - int(bof)]
        prior_day = prior_sess[-SESSION_BARS:]
        if len(prior_day) < MIN_PRIOR_BARS:
            return None
        prof = _tpo_profile(prior_day, bucket, VALUE_AREA_FRAC)
        if prof is None:
            return None
        poc, va_low, va_high, _total, above, below = prof
        day_high = max(float(b[2]) for b in prior_day)
        day_low = min(float(b[3]) for b in prior_day)
        return (poc, va_low, va_high, above, below, day_high, day_low)

    def _anchor_pred(self, variant_id: str, direction: str,
                     poc: float, va_low: float, va_high: float):
        """Per-history-bar predicate for the setup anchor: the price leg of
        the setup (the run of closes beyond the reference). The profile-level
        conditions (TPO pressure) are state readings, not per-bar, so the
        anchor captures the price run (D-026)."""
        if variant_id in ('a', 'd'):
            return (lambda i, bar: float(bar[4]) < poc) if direction == 'LONG' \
                else (lambda i, bar: float(bar[4]) > poc)
        if variant_id == 'c':
            return (lambda i, bar: float(bar[4]) > va_high) if direction == 'LONG' \
                else (lambda i, bar: float(bar[4]) < va_low)
        return (lambda i, bar: float(bar[4]) < va_low) if direction == 'LONG' \
            else (lambda i, bar: float(bar[4]) > va_high)

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        if self.variant_id not in self.variants_evaluated:
            raise ValueError(
                f'{self.expert_id}: unknown variant {self.variant_id!r} '
                f'(variants_evaluated={list(self.variants_evaluated)})')
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.bar_of_session']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        hist_value = f[f'{sym}.history'].value
        bof = f[f'{sym}.bar_of_session'].value
        if atr is None or atr <= 0 or not isinstance(hist_value, (tuple, list)) \
                or not hist_value or bof is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        hist = tuple(hist_value)
        prof = self._profile(hist, float(atr), float(bof))
        if prof is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        poc, va_low, va_high, above, below, day_high, day_low = prof
        variant = self.variant_id
        # Setup gate per variant (Ch17.2 responsive/initiative doctrine).
        direction = None
        if variant == 'a':
            if close < poc and close > day_low:
                direction = 'LONG'
            elif close > poc and close < day_high:
                direction = 'SHORT'
        elif variant == 'b':
            if close < va_low and close > day_low:
                direction = 'LONG'
            elif close > va_high and close < day_high:
                direction = 'SHORT'
        elif variant == 'c':
            # TPO-pressure gauge: the larger tail (above vs below the POC)
            # dominates at >= 55%. Initiative activity is a close BEYOND the
            # value area but inside the prior-day range (the trend has not yet
            # run its measured course to the range extreme).
            tails = above + below
            if tails == 0:
                pass
            elif above / tails >= PRESSURE_THRESHOLD and close > va_high \
                    and close < day_high:
                direction = 'LONG'
            elif below / tails >= PRESSURE_THRESHOLD and close < va_low \
                    and close > day_low:
                direction = 'SHORT'
        else:  # 'd' — deep deviation below the value center (POC) by the
            # declared distance gate; the VA is the profile context.
            dist = VA_EXIT_DISTANCE_ATR * float(atr)
            if close < poc - dist and close > day_low:
                direction = 'LONG'
            elif close > poc + dist and close < day_high:
                direction = 'SHORT'
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        long = direction == 'LONG'
        # Frozen references (Ch17.2 p669 action-point doctrine): the prior-day
        # range extreme is the stop reference for the reversion variants; the
        # value center (POC) is the hold level for the initiative variant c.
        if variant == 'c':
            stop_ref = va_low if long else va_high
            low_ref = poc if long else None
            high_ref = None if long else poc
        else:
            stop_ref = day_low if long else day_high
            low_ref = day_low if long else None
            high_ref = None if long else day_high
        # Target: reversion variants revert to the value center (POC); the
        # initiative variant c continues to the prior-day range extreme.
        target_ref = poc if variant != 'c' else (day_high if long else day_low)
        if long:
            target_r = (target_ref - close) / float(atr)
            stop_r = (close - stop_ref) / float(atr)
        else:
            target_r = (close - target_ref) / float(atr)
            stop_r = (stop_ref - close) / float(atr)
        if target_r <= 0 or stop_r <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        pred = self._anchor_pred(variant, direction, poc, va_low, va_high)
        anchor = self.find_setup_anchor(hist, pred)
        geometry = {
            'entry': 'NEXT_BAR_CLOSE', 'target_r': target_r, 'stop_r': stop_r,
            'expiry_bars': 8, 'atr_ref': float(atr), 'variant': variant,
            'poc_ref': poc, 'va_low_ref': va_low, 'va_high_ref': va_high,
        }
        if low_ref is not None:
            geometry['prior_low_ref'] = low_ref
        if high_ref is not None:
            geometry['prior_high_ref'] = high_ref
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{variant}:{direction}:{close:.6f}:{poc:.6f}',
            risk_geometry=geometry, birth_time=t,
            setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "price reacts to the prior value structure": a
        reversion long must hold the prior-day low, an initiative long must
        hold the value center (POC), and the short mirrors. A close through
        the frozen reference says the reaction thesis is dead (Ch17.2 value
        shift). Fails open when the close is unobservable."""
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
