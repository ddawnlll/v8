"""Bollinger band-reversion behavior family (`bollinger_reversion`).

Hypothesis (mechanism `volatility_band`, behavior `band_reversion`): price
testing the 2-SD band tends to revert toward the 1-SD band / central value —
Setup 2 fades the 2-SD band back to the 1-SD band with the stop beyond the
3-SD band (Ch12 p481-482); Setup 3 fades the SAME band structure but only in
the direction of the established trend (close above the SMA in an UPTREND ->
long at the upper 2-SD band, target the 1-SD band; Ch12 p482). The opposite
hypothesis — riding the band — is the sibling behavior `band_breakout`
(`bollinger_breakout`) under the SAME `volatility_band` mechanism (rule 13).

Book geometry (verbatim): Setup 2 — short at the upper 2-SD band, stop just
above the 3-SD upper band, profit target at the 1-SD upper band (mirror for
the long leg; the book text's long leg reads "upper two-SD band" but the
"just below the three-SD lower band" stop implies the lower 2-SD band — the
typo is captured verbatim in the extraction). Setup 3 — stop just under/over
the SMA, profit exit at the 1-SD band. The three levels are one band-sigma
apart, so in R terms stop_r = target_r = sigma_ref / atr_ref for Setup 2 and
stop_r = 2 * sigma_ref / atr_ref, target_r = sigma_ref / atr_ref for Setup 3.
A close beyond the 3-SD band invalidates the reversion premise (that is a
trend, not a reversion; Ch12 p471-474).

Setup 3 ships RR = 0.5 (stop_r = 2*sd/atr, target_r = sd/atr): at
round_trip_cost_r = 0.07 the breakeven win rate is 2.07/3.00 = 69.0% — a
high-hit-rate/low-RR geometry, recorded as a PROVISIONAL_DECISION (issue #70;
D-061). Setup 2 and Setup 3 outcomes are aggregated in the outcome ledger
(variant not recorded per outcome today), so Setup 3's standalone
hit-rate-vs-breakeven must be measured before this geometry is relied on.

As in `bollinger_breakout`, the band geometry is FROZEN at the setup anchor
(run start, D-026) so episode_key stays stable across the detection run; the
20 closes ending at a fixed anchor are identical on every decision clock while
the anchor stays inside the 32-bar history window.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, frozen constant (D-036 pattern): the Bollinger base window of the
# marketstate bb_* features (SMA20 +/- 2*sigma); the 1-SD/3-SD levels are
# derived from it, not new features.
BB_BASE_N = 20


def _mean(values):
    return sum(values) / len(values)


def _std_pop(values):
    m = _mean(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def _bb_series(hist):
    """Per-bar (mid, sd) of the trailing 20 closes; None in warmup."""
    closes = [b[4] for b in hist]
    out = []
    for i in range(len(closes)):
        if i >= BB_BASE_N - 1:
            win = closes[i - BB_BASE_N + 1:i + 1]
            out.append((_mean(win), _std_pop(win)))
        else:
            out.append(None)
    return out


def _anchor_refs(hist, anchor_event_id):
    """Frozen band stack + ATR14 at the setup anchor, or None when the anchor's
    20-bar context is not fully inside the history window (the documented
    anchor bound of base.Expert.find_setup_anchor)."""
    pos = next((i for i, b in enumerate(hist) if b[0] == anchor_event_id), None)
    if pos is None or pos < BB_BASE_N - 1 or pos < 13:
        return None
    closes = [b[4] for b in hist]
    win = closes[pos - BB_BASE_N + 1:pos + 1]
    mid = _mean(win)
    sd = _std_pop(win)
    atr = _mean([hist[k][2] - hist[k][3] for k in range(pos - 13, pos + 1)])
    return {'mid_ref': mid, 'sd_ref': sd, 'atr_ref': atr,
            'upper_1sd_ref': mid + sd, 'upper_2sd_ref': mid + 2 * sd,
            'upper_3sd_ref': mid + 3 * sd,
            'lower_1sd_ref': mid - sd, 'lower_2sd_ref': mid - 2 * sd,
            'lower_3sd_ref': mid - 3 * sd}


class BollingerReversionExpert(Expert):
    """Fade the 2-SD band back toward the 1-SD band — Setup 2 (reversion
    within bands) or Setup 3 (trend-aligned reversion)."""
    expert_id = 'bollinger_reversion'
    version = 'v1'
    mechanism_family_id = 'volatility_band'
    behavior_family_id = 'band_reversion'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')
    # D-044: the full evaluated set, losers included. `a` = Setup 2 (fade the
    # 2-SD band, stop beyond 3-SD, target 1-SD); `b` = Setup 3 (trend-aligned
    # reversion: close beyond the SMA in the trend direction).
    variants_evaluated = ('a', 'b')
    search_universe_size = 2

    def __init__(self, variant_id=None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r}; '
                    f'evaluated variants: {self.variants_evaluated}')
            self.variant_id = variant_id

    # --- per-variant per-bar predicates (D-026 anchor scan) ------------------
    def _pred_a_long(self, i, bar):
        """Close in the fade zone below the lower band: between 2-SD and 3-SD
        below the SMA. A degenerate band (sd == 0) is no fade level (with
        upper == lower == mid the inequality holds for every bar), and a close
        beyond 3-SD is a breakdown, not a reversion (Ch12 p471-474)."""
        if i < BB_BASE_N - 1:
            return False
        mid, sd = self._bb[i]
        return sd > 0 and mid - 3 * sd < bar[4] <= mid - 2 * sd

    def _pred_a_short(self, i, bar):
        """Close in the fade zone above the upper band: between 2-SD and 3-SD
        above the SMA (a close beyond 3-SD is a breakout, not a reversion)."""
        if i < BB_BASE_N - 1:
            return False
        mid, sd = self._bb[i]
        return sd > 0 and mid + 2 * sd <= bar[4] < mid + 3 * sd

    def _pred_b_long(self, i, bar):
        """Close above the SMA in an UPTREND (Setup 3, Ch12 p482)."""
        if i < BB_BASE_N - 1:
            return False
        _e, _o, _h, _l, close, ema_fast, ema_slow = bar
        return close > self._bb[i][0] and ema_fast > ema_slow

    def _pred_b_short(self, i, bar):
        """Close below the SMA in a DOWNTREND."""
        if i < BB_BASE_N - 1:
            return False
        _e, _o, _h, _l, close, ema_fast, ema_slow = bar
        return close < self._bb[i][0] and ema_fast < ema_slow

    def _pred(self, direction):
        if self.variant_id == 'a':
            return (self._pred_a_long if direction == 'LONG'
                    else self._pred_a_short)
        return (self._pred_b_long if direction == 'LONG'
                else self._pred_b_short)

    def _direction(self, f, sym, close):
        if self.variant_id == 'a':
            # Fade zone: close between 2-SD and 3-SD (matches _pred_a_*).
            mid = float(f[f'{sym}.bb_mid'].value)
            upper = float(f[f'{sym}.bb_upper'].value)
            lower = float(f[f'{sym}.bb_lower'].value)
            upper_3sd = mid + 1.5 * (upper - mid)
            lower_3sd = mid - 1.5 * (mid - lower)
            if upper <= close < upper_3sd:
                return 'SHORT', 'upper_2sd_ref'
            if lower_3sd < close <= lower:
                return 'LONG', 'lower_2sd_ref'
            return None, ''
        fast = float(f[f'{sym}.ema_fast'].value)
        slow = float(f[f'{sym}.ema_slow'].value)
        mid = float(f[f'{sym}.bb_mid'].value)
        if close > mid and fast > slow:
            return 'LONG', 'mid_ref'
        if close < mid and fast < slow:
            return 'SHORT', 'mid_ref'
        return None, ''

    def _geometry(self, refs, direction):
        sd, atr = refs['sd_ref'], refs['atr_ref']
        geo = {'entry': 'NEXT_BAR_CLOSE', 'expiry_bars': 8, 'atr_ref': atr,
               'variant': self.variant_id}
        if self.variant_id == 'b':
            # Setup 3 (Ch12 p482): entry proxy at the 2-SD band, stop under
            # the SMA (two sigma), profit exit at the 1-SD band (one sigma).
            geo['stop_r'] = 2 * sd / atr
            geo['target_r'] = sd / atr
            geo['mid_ref'] = refs['mid_ref']
            if direction == 'LONG':
                geo['upper_1sd_ref'] = refs['upper_1sd_ref']
                geo['upper_2sd_ref'] = refs['upper_2sd_ref']
            else:
                geo['lower_1sd_ref'] = refs['lower_1sd_ref']
                geo['lower_2sd_ref'] = refs['lower_2sd_ref']
            return geo
        # Setup 2 (Ch12 p481-482): fade the 2-SD band; the 3-SD stop and the
        # 1-SD target are each one band-sigma away.
        r = sd / atr
        geo['stop_r'] = r
        geo['target_r'] = r
        if direction == 'SHORT':
            geo['upper_1sd_ref'] = refs['upper_1sd_ref']
            geo['upper_2sd_ref'] = refs['upper_2sd_ref']
            geo['upper_3sd_ref'] = refs['upper_3sd_ref']
        else:
            geo['lower_1sd_ref'] = refs['lower_1sd_ref']
            geo['lower_2sd_ref'] = refs['lower_2sd_ref']
            geo['lower_3sd_ref'] = refs['lower_3sd_ref']
        return geo

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.bb_mid', f'{sym}.bb_upper',
                f'{sym}.bb_lower', f'{sym}.bb_pct_b', f'{sym}.ema_fast',
                f'{sym}.ema_slow', f'{sym}.history']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        hist_value = f[f'{sym}.history'].value
        if not isinstance(hist_value, (tuple, list)) or not hist_value:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._hist = tuple(hist_value)
        self._bb = _bb_series(self._hist)
        direction, ref_key = self._direction(f, sym, close)
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(self._hist, self._pred(direction))
        refs = _anchor_refs(self._hist, anchor)
        if refs is None or refs['sd_ref'] <= 0 or refs['atr_ref'] <= 0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        geometry = self._geometry(refs, direction)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{close:.6f}:{geometry[ref_key]:.6f}',
            risk_geometry=geometry,
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """Post-entry thesis: the reversion premise. Setup 2 dies when price
        closes beyond the frozen 3-SD band (that is a trend, not a reversion);
        Setup 3 dies when the trend flips. Unobservable inputs fail open.
        """
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        c = float(close.value)
        long = draft.direction == 'LONG'
        geom = draft.risk_geometry
        if geom.get('variant') == 'b':
            fast = f.get(f'{sym}.ema_fast')
            slow = f.get(f'{sym}.ema_slow')
            if fast is None or slow is None or fast.value is None \
                    or slow.value is None:
                return True
            return float(fast.value) > float(slow.value) if long \
                else float(fast.value) < float(slow.value)
        ref = geom.get('upper_3sd_ref' if not long else 'lower_3sd_ref')
        if ref is None:
            return True
        return c < float(ref) if not long else c > float(ref)
