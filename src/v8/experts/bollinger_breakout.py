"""Bollinger band-breakout behavior family (`bollinger_breakout`).

Hypothesis (mechanism `volatility_band`, behavior `band_breakout`): a close
that establishes price on the strong side of the 20-bar SMA band stack is a
momentum-continuation setup — Setup 1 (close beyond the SMA, enter toward the
1-SD band, target the 2-SD band; Ch12 p480-481) and the closing band violation
(close beyond the 2-SD band; Ch12 p471-473), optionally gated by a bandwidth
squeeze (a fresh lookback low in bandwidth precedes the expansion). The
opposite hypothesis — fading the bands — is the sibling behavior
`band_reversion` (`bollinger_reversion`) under the SAME `volatility_band`
mechanism (rule 13).

Book geometry (verbatim): stops go just under/over the SMA — the book's
explicit caveat is that Bollinger stops use the central value, never the band
(Ch12 p473-474: "stops just beyond the bands work well for most bands except
Bollinger Bands, because Bollinger bands diverge during high volatility").
Setup-1 target is the 2-SD band (Ch12 p480-481). V8 expresses the level
geometry as R-multiples: with the entry proxy at the 1-SD band, the SMA stop
is one band-sigma below and the 2-SD target one band-sigma above, so
stop_r = target_r = sigma_ref / atr_ref. A closing band violation reaches the
2-SD band before entry, so its SMA stop is two sigma away and the unstated
target falls back to the family 1:1 rule (stop_r = target_r =
2 * sigma_ref / atr_ref).

The band geometry is FROZEN at the setup anchor (the run-start bar, D-026),
not at the detection bar: episode_key hashes the structural geometry, and a
detection-bar-frozen level would drift across the detection run and silently
disable deduplication (the D-026 timestamp-in-key defect in another shape).
The 20 closes ending at a fixed anchor are identical on every decision clock
while the anchor stays inside the 32-bar history window, so the frozen
geometry is key-stable by construction; anchors pushed past the window edge
fall back to the documented anchor bound (base.Expert.find_setup_anchor).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, frozen constants (D-036 pattern: "declared, never fitted").
# FG-3 G-16: the marketstate bb_* features are SMA20 +/- 2*sigma; the book's
# 1-SD/3-SD levels are derived from them (no new feature, same base window).
BB_BASE_N = 20
# E-08 variant c: squeeze lookback for "bandwidth at an extended low" before
# the closing band violation (book Ch12 bandwidth/squeeze doctrine, H04).
SQUEEZE_LOOKBACK = 10


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


def _bw_series(bb):
    """Per-bar bandwidth (upper-lower)/mid = 4*sd/mid (matches the marketstate
    bb_bandwidth formula exactly); None where the bb pair is not computable."""
    out = []
    for ms in bb:
        if ms is None:
            out.append(None)
        else:
            mid, sd = ms
            out.append(4.0 * sd / mid if mid else 0.0)
    return out


def _anchor_refs(hist, anchor_event_id):
    """Frozen band stack + ATR14 at the setup anchor, or None when the anchor's
    20-bar context is not fully inside the history window (a setup run longer
    than ~13 bars pushes the anchor to the window edge — the documented anchor
    bound of base.Expert.find_setup_anchor)."""
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


class BollingerBreakoutExpert(Expert):
    """Close beyond the SMA (Setup 1) or beyond the 2-SD band (closing band
    violation, optionally after a bandwidth squeeze) -> momentum LONG/SHORT."""
    expert_id = 'bollinger_breakout'
    version = 'v1'
    mechanism_family_id = 'volatility_band'
    behavior_family_id = 'band_breakout'
    variant_id = 'a'
    requires = ('volatility', 'history')
    # target_r/stop_r are structural: band-sigma distances from the frozen
    # anchor refs in R (D-028), computed per variant in _geometry().
    target_r = None
    stop_r = None
    # D-044: the full evaluated set, losers included. `a` = Setup 1 (close
    # beyond the SMA, target the 2-SD band), `b` = closing band violation,
    # `c` = bandwidth-squeeze precondition + closing band violation.
    variants_evaluated = ('a', 'b', 'c')
    search_universe_size = 3

    def __init__(self, variant_id=None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r}; '
                    f'evaluated variants: {self.variants_evaluated}')
            self.variant_id = variant_id

    # --- per-variant per-bar predicates (D-026 anchor scan) ------------------
    def _pred_a_long(self, i, bar):
        if i < BB_BASE_N - 1:
            return False
        return bar[4] > self._bb[i][0]

    def _pred_a_short(self, i, bar):
        if i < BB_BASE_N - 1:
            return False
        return bar[4] < self._bb[i][0]

    def _pred_b_long(self, i, bar):
        if i < BB_BASE_N - 1:
            return False
        mid, sd = self._bb[i]
        return bar[4] > mid + 2 * sd

    def _pred_b_short(self, i, bar):
        if i < BB_BASE_N - 1:
            return False
        mid, sd = self._bb[i]
        return bar[4] < mid - 2 * sd

    def _pred_c_long(self, i, bar):
        if i < BB_BASE_N - 1 + SQUEEZE_LOOKBACK + 1:
            return False
        mid, sd = self._bb[i]
        if not bar[4] > mid + 2 * sd:
            return False
        bw = self._bw
        # The PRIOR bar was at a fresh bandwidth low (the squeeze); this bar
        # closes beyond the band (the expansion/breakout).
        return bw[i - 1] < min(bw[i - 1 - SQUEEZE_LOOKBACK:i - 1])

    def _pred_c_short(self, i, bar):
        if i < BB_BASE_N - 1 + SQUEEZE_LOOKBACK + 1:
            return False
        mid, sd = self._bb[i]
        if not bar[4] < mid - 2 * sd:
            return False
        bw = self._bw
        return bw[i - 1] < min(bw[i - 1 - SQUEEZE_LOOKBACK:i - 1])

    def _pred(self, direction):
        if self.variant_id == 'a':
            return (self._pred_a_long if direction == 'LONG'
                    else self._pred_a_short)
        if self.variant_id == 'b':
            return (self._pred_b_long if direction == 'LONG'
                    else self._pred_b_short)
        return (self._pred_c_long if direction == 'LONG'
                else self._pred_c_short)

    def _direction(self, f, sym, close):
        """Direction decided by the newest bar, on the SAME condition the
        anchor predicate evaluates per history bar (a gate that slides the
        reference would make the anchor inconsistent with the gate)."""
        if self.variant_id == 'a':
            mid = float(f[f'{sym}.bb_mid'].value)
            if close > mid:
                return 'LONG', 'mid_ref'
            if close < mid:
                return 'SHORT', 'mid_ref'
            return None, ''
        pct = float(f[f'{sym}.bb_pct_b'].value)
        if self.variant_id == 'b':
            if pct > 1.0:
                return 'LONG', 'upper_2sd_ref'
            if pct < 0.0:
                return 'SHORT', 'lower_2sd_ref'
            return None, ''
        # variant c: closing violation WITH the squeeze precondition.
        bw = self._bw
        p = len(self._hist) - 1
        squeeze = (p >= BB_BASE_N - 1 + SQUEEZE_LOOKBACK + 1
                   and bw[p - 1] is not None
                   and bw[p - 1] < min(bw[p - 1 - SQUEEZE_LOOKBACK:p - 1]))
        if pct > 1.0 and squeeze:
            return 'LONG', 'upper_2sd_ref'
        if pct < 0.0 and squeeze:
            return 'SHORT', 'lower_2sd_ref'
        return None, ''

    def _geometry(self, refs, direction):
        sd, atr = refs['sd_ref'], refs['atr_ref']
        geo = self.declared_geometry()
        geo.update({'atr_ref': atr, 'variant': self.variant_id,
                    'mid_ref': refs['mid_ref']})
        if self.variant_id == 'a':
            # Setup 1: entry proxy at the 1-SD band; the SMA stop and the 2-SD
            # target are each one band-sigma away (Ch12 p480-481).
            r = sd / atr
            geo['target_r'] = r
            geo['stop_r'] = r
            if direction == 'LONG':
                geo['upper_1sd_ref'] = refs['upper_1sd_ref']
                geo['upper_2sd_ref'] = refs['upper_2sd_ref']
            else:
                geo['lower_1sd_ref'] = refs['lower_1sd_ref']
                geo['lower_2sd_ref'] = refs['lower_2sd_ref']
            return geo
        # Variants b/c: the 2-SD band is already violated at entry; the stop
        # is the central value (book caveat, two sigma away) and the target is
        # the family 1:1 default.
        r = 2 * sd / atr
        geo['target_r'] = r
        geo['stop_r'] = r
        if direction == 'LONG':
            geo['upper_2sd_ref'] = refs['upper_2sd_ref']
        else:
            geo['lower_2sd_ref'] = refs['lower_2sd_ref']
        return geo

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.bb_mid', f'{sym}.bb_upper',
                f'{sym}.bb_lower', f'{sym}.bb_pct_b', f'{sym}.bb_bandwidth',
                f'{sym}.history']
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
        self._bw = _bw_series(self._bb)
        direction, ref_key = self._direction(f, sym, close)
        if direction is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(self._hist, self._pred(direction))
        refs = _anchor_refs(self._hist, anchor)
        # A degenerate band (flat closes: sd == 0) or a non-positive risk unit
        # is no habitat: the geometry would be a zero-distance stop/target.
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
        """Post-entry thesis: the strong-side placement that justified the
        trade is still on the strong side of the frozen reference. Setup 1's
        premise is the SMA (the frozen stop level too — the book's Bollinger
        stop doctrine); the band-violation variants' premise is the broken
        2-SD band itself. Unobservable inputs fail open (price still governs).
        """
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        if close is None or close.value is None:
            return True
        c = float(close.value)
        long = draft.direction == 'LONG'
        geom = draft.risk_geometry
        if 'upper_1sd_ref' in geom or 'lower_1sd_ref' in geom:
            ref = geom.get('mid_ref')
            if ref is None:
                return True
            return c > float(ref) if long else c < float(ref)
        ref = geom.get('upper_2sd_ref' if long else 'lower_2sd_ref')
        if ref is None:
            return True
        return c > float(ref) if long else c < float(ref)
