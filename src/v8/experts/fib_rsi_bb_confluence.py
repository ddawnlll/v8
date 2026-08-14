"""Fibonacci + RSI + Bollinger confluence behavior family
(`fib_rsi_bb_confluence`).

Hypothesis (mechanism `confluence_reversion_continuation`): when THREE
independent indicator families point the same way at the same bar, the setup
carries more conviction than any single family alone. The three legs are the
registered families' own idioms, verbatim:

- **Bollinger leg** (`volatility_band` / `band_reversion`, Ch12 p481-482):
  a close in the 2-SD..3-SD fade zone — price stretched below the 20-SMA by
  two sigma is a reversion candidate, not a breakdown (a close beyond 3-SD is
  a trend).
- **RSI leg** (`oscillator_reversion` / `overbought_oversold_reversion`,
  Ch8.6 p259-262): the oscillator dipped below oversold (30) and recovered
  above it — the first sign the extreme is reverting. The feature AND the
  local Wilder series must both clear the threshold (the conservative gate
  from `rsi_stoch_reversion`; Wilder RSI over a short window can disagree
  with the full-series feature near the boundary).
- **Fibonacci leg** (`fib_level_reaction` / `fib_retracement_continuation`,
  Ch10.4-10.7): a close that reclaimed a retracement level of the prior
  impulse. The level is the DEEPEST retracement (78.6%) — the deepest
  support of an up-impulse (mirror for shorts). This is a structural choice,
  not a fit: the fade-zone close (below mid - 2*sigma) can only co-occur
  with a retracement level that sits below the 20-SMA's lower band; of the
  standard ratios only 0.786 does so, so a shallow 0.382 reclaim is
  geometrically near-impossible as a three-leg confluence (the co-occurrence
  was computed before the experiment ran, and the level is frozen).

Variants (all frozen; D-044 lists every implemented variant):
  a  STRICT: all three legs vote the same direction, or no signal.
  b  MAJORITY: at least two of the three legs agree, or no signal.

The STRICT variant is the reason the family exists: it answers "does
requiring ALL THREE families to agree beat requiring only TWO?" (the
confluence vs. its own relaxation). Variant b is the same family's
relaxation — one multiplicity unit, one declared search universe.

Risk geometry: the family default 1R:1R:8bar with `atr_ref` (D-028), frozen
at detection. The 78.6% level becomes `prior_low_ref`/`prior_high_ref` (the
D-042 `prior_*_ref` pattern — the pre-entry invalidation AND the post-entry
deep-correction reference), and the frozen 3-SD band becomes
`lower_3sd_ref`/`upper_3sd_ref` (the reversion-premise reference: a close
beyond the 3-SD band is a trend, not a reversion). The `variant` key in the
geometry separates the two variants' episode keys (`lab._geometry_version`
excludes only `atr_ref`/`prior_*_ref`; without it variant-b candidates are
suppressed as duplicates of variant-a).
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Declared, frozen constants, inherited verbatim from the registered
# families (D-036 pattern; never fitted on the dev window).
BB_BASE_N = 20                       # bollinger_reversion.py:43
RSI_OS = 30.0                        # rsi_stoch_reversion.py:45
RSI_OB = 70.0                        # rsi_stoch_reversion.py:46
# The confluence fib leg uses the DEEPEST retracement (the structural
# co-occurrence argument in the module docstring); it doubles as the
# post-entry deep-correction reference, as in fib_retracement_continuation.
FIB_RATIO = 0.786
DEEP_RETRACEMENT = 0.786


def _mean(values):
    return sum(values) / len(values)


def _std_pop(values):
    m = _mean(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def _bb_series(hist):
    """Per-bar (mid, sd) of the trailing 20 closes; None in warmup. Copy of
    bollinger_reversion._bb_series (private there; duplicated with
    attribution so the confluence recomputes the same series locally)."""
    closes = [b[4] for b in hist]
    out = []
    for i in range(len(closes)):
        if i >= BB_BASE_N - 1:
            win = closes[i - BB_BASE_N + 1:i + 1]
            out.append((_mean(win), _std_pop(win)))
        else:
            out.append(None)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    if avg_gain == 0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _rsi_per_bar(closes, period: int = 14) -> list:
    """Wilder RSI per bar; None before the seed. Copy of
    rsi_stoch_reversion._rsi_per_bar (identical formula to marketstate's
    rsi14 over the local window)."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out = [None] * period
    out.append(_rsi_value(avg_gain, avg_loss))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out.append(_rsi_value(avg_gain, avg_loss))
    return out


def _retracement_level(fibs: tuple, ratio: float):
    """The retracement level for `ratio` from the self-describing fib tuple
    (anchor, direction, retr, ext); None when absent (fib_retracement_
    continuation._retracement_level)."""
    if not isinstance(fibs, tuple) or len(fibs) != 4:
        return None
    for r, level in fibs[2]:
        if abs(r - ratio) < 1e-9:
            return float(level)
    return None


class FibRsiBbConfluenceExpert(Expert):
    """Three indicator families must agree (variant a) or a two-of-three
    majority must agree (variant b), or there is no setup."""
    expert_id = 'fib_rsi_bb_confluence'
    version = 'v1'
    mechanism_family_id = 'confluence_reversion_continuation'
    behavior_family_id = 'fib_rsi_bb_confluence'
    variant_id = 'a'
    requires = ('oscillator', 'location', 'volatility', 'history')
    # D-044: both confluence rules evaluated on the dev window, losers
    # included. D-046: every threshold is inherited from a registered family,
    # frozen pre-window — the search consumed exactly the two rules.
    variants_evaluated = ('a', 'b')
    search_universe_size = 2

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    # --- per-leg votes -----------------------------------------------------
    # Each leg votes 'LONG' | 'SHORT' | None for a given bar, computed from
    # the local per-bar series (the anchor scan) or the state features (the
    # current bar). A leg that cannot form an opinion abstains (None).

    def _bb_vote_at(self, i: int, bar: tuple) -> str | None:
        """Fade-zone vote: close between 2-SD and 3-SD of the 20-bar SMA
        (bollinger_reversion Setup 2). A degenerate band (sd == 0) is no
        level; a close beyond 3-SD is a trend, not a reversion."""
        if i < BB_BASE_N - 1 or self._bb[i] is None:
            return None
        mid, sd = self._bb[i]
        if sd <= 0:
            return None
        close = bar[4]
        if mid - 3 * sd < close <= mid - 2 * sd:
            return 'LONG'
        if mid + 2 * sd <= close < mid + 3 * sd:
            return 'SHORT'
        return None

    def _rsi_vote_at(self, i: int) -> str | None:
        """Oscillator-reversion vote (rsi_stoch_reversion variant a): the
        newest run sits on the reverted side of its extreme AND the prior bar
        (the run start's predecessor) is on the extreme side — the dip that
        made the recovery meaningful. The close-beyond-signal-bar price
        confirmation of the pure oscillator strategy is subsumed here by the
        other legs' close conditions, so this leg carries no extra close
        constraint (documented deviation)."""
        if i >= len(self._rsi) or self._rsi[i] is None:
            return None
        # LONG checked first, mirroring rsi_stoch_reversion._detect_rsi's
        # return-early order; a mid-range bar that recovered from both sides
        # in the window resolves the same way as the source family.
        if self._rsi[i] > RSI_OS:
            s = i
            while s > 0 and self._rsi[s - 1] is not None \
                    and self._rsi[s - 1] > RSI_OS:
                s -= 1
            if s > 0 and self._rsi[s - 1] is not None \
                    and self._rsi[s - 1] <= RSI_OS:
                return 'LONG'
            # No oversold dip: fall through to the overbought side rather
            # than abstaining — a mid-range bar can be recovered from the
            # overbought extreme (mirrors rsi_stoch_reversion._detect_rsi,
            # whose LONG branch returns only on a dip and otherwise falls
            # through to the SHORT check).
        if self._rsi[i] < RSI_OB:
            s = i
            while s > 0 and self._rsi[s - 1] is not None \
                    and self._rsi[s - 1] < RSI_OB:
                s -= 1
            if s > 0 and self._rsi[s - 1] is not None \
                    and self._rsi[s - 1] >= RSI_OB:
                return 'SHORT'
        return None

    def _fib_vote_at(self, i: int, bar: tuple) -> str | None:
        """Deep-retracement reclaim vote (fib_retracement_continuation at
        0.786): a close that reclaimed the deepest retracement of the intact
        impulse. `_fib_level`/`_fib_direction` are frozen from the state's
        fib_levels at detection, so the anchor scan uses the same level."""
        if self._fib_direction is None or self._fib_level is None:
            return None
        _e, _o, high, low, close, _f, _s = bar
        if self._fib_direction == 1.0:
            return 'LONG' if (close > self._fib_level
                              and low <= self._fib_level) else None
        return 'SHORT' if (close < self._fib_level
                           and high >= self._fib_level) else None

    def _confluence_vote(self, votes: list) -> str | None:
        """The confluence rule for this variant over the three leg votes.
        variant a (STRICT): all three vote the same direction. variant b
        (MAJORITY): at least two of the three agree."""
        if self.variant_id == 'a':
            if all(v is not None for v in votes) \
                    and votes[0] == votes[1] == votes[2]:
                return votes[0]
            return None
        longs = sum(1 for v in votes if v == 'LONG')
        shorts = sum(1 for v in votes if v == 'SHORT')
        if longs >= 2:
            return 'LONG'
        if shorts >= 2:
            return 'SHORT'
        return None

    def _confluence_at(self, i: int, bar: tuple) -> str | None:
        """The per-bar confluence predicate for the anchor scan (D-026):
        the same variant rule over the three local-series votes."""
        return self._confluence_vote([self._bb_vote_at(i, bar),
                                      self._rsi_vote_at(i),
                                      self._fib_vote_at(i, bar)])

    # --- evaluate ----------------------------------------------------------

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        need = [f'{sym}.close', f'{sym}.atr', f'{sym}.history',
                f'{sym}.bb_mid', f'{sym}.bb_upper', f'{sym}.bb_lower',
                f'{sym}.rsi14', f'{sym}.fib_levels']
        if not self._need(state, need):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        hist_value = f[f'{sym}.history'].value
        fibs = f[f'{sym}.fib_levels'].value
        if atr is None or not isinstance(hist_value, (tuple, list)) \
                or not hist_value or not isinstance(fibs, tuple) \
                or len(fibs) != 4:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        # Fib warmup needs a confirmed swing pair (n_close >= 21 in
        # marketstate); BB needs 20, RSI a seed. A shorter window cannot host
        # the confluence, so it is habitat-unavailable, not signal-less.
        if len(hist_value) < 21:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        anchor_price, direction, _retr, _ext = fibs
        if direction not in (1.0, -1.0) or anchor_price <= 0.0:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._fib_level = _retracement_level(fibs, FIB_RATIO)
        if self._fib_level is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        self._fib_direction = direction
        self._hist = tuple(hist_value)
        self._bb = _bb_series(self._hist)
        self._rsi = _rsi_per_bar([b[4] for b in self._hist])

        # Current-bar votes. The RSI leg additionally requires the STATE
        # feature to clear the threshold (the full-series Wilder value can
        # disagree with the local window near the boundary; the conservative
        # gate from rsi_stoch_reversion).
        bb_v = self._bb_vote_at(len(self._hist) - 1, self._hist[-1])
        rsi_v = self._rsi_vote_at(len(self._hist) - 1)
        rsi_feat = float(f[f'{sym}.rsi14'].value)
        if rsi_v == 'LONG' and not rsi_feat > RSI_OS:
            rsi_v = None
        if rsi_v == 'SHORT' and not rsi_feat < RSI_OB:
            rsi_v = None
        fib_v = self._fib_vote_at(len(self._hist) - 1, self._hist[-1])
        direction_sig = self._confluence_vote([bb_v, rsi_v, fib_v])
        if direction_sig is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        anchor = self.find_setup_anchor(self._hist, self._confluence_at)

        # Geometry, frozen at detection (D-042 prior_*_ref pattern). The
        # 78.6% level doubles as the pre-entry invalidation and the
        # post-entry deep-correction reference; the frozen 3-SD band is the
        # reversion-premise reference. `variant` separates the episode keys.
        mid = float(f[f'{sym}.bb_mid'].value)
        upper = float(f[f'{sym}.bb_upper'].value)
        lower = float(f[f'{sym}.bb_lower'].value)
        geometry = self.declared_geometry()
        geometry.update({'atr_ref': atr, 'variant': self.variant_id})
        if direction_sig == 'LONG':
            geometry['prior_low_ref'] = self._fib_level
            geometry['lower_3sd_ref'] = mid - 1.5 * (mid - lower)
        else:
            geometry['prior_high_ref'] = self._fib_level
            geometry['upper_3sd_ref'] = mid + 1.5 * (upper - mid)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction_sig,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction_sig}:'
                              f'{self._fib_level:.6f}:{close:.6f}',
            risk_geometry=geometry, birth_time=t,
            setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    # --- still_valid ---------------------------------------------------------

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The confluence thesis is "the reversion-reversal holds at the deep
        support". It dies when ANY of the three premises breaks: a close
        beyond the frozen 78.6% level (deep correction — the impulse is
        gone), a close beyond the frozen 3-SD band (a trend, not a
        reversion), or the oscillator re-entering its extreme zone (the
        reversion failed). Unobservable inputs fail open — an unreadable
        thesis is not a dead one."""
        sym = draft.instrument
        f = state.features
        close = f.get(f'{sym}.close')
        c = float(close.value) if (close is not None
                                   and close.value is not None) else None
        long = draft.direction == 'LONG'
        if c is not None:
            ref = draft.risk_geometry.get(
                'prior_low_ref' if long else 'prior_high_ref')
            if ref is not None:
                if (long and c < float(ref)) or (not long and c > float(ref)):
                    return False
            ref3 = draft.risk_geometry.get(
                'lower_3sd_ref' if long else 'upper_3sd_ref')
            if ref3 is not None:
                if (long and c <= float(ref3)) or (not long and c >= float(ref3)):
                    return False
        rsi = f.get(f'{sym}.rsi14')
        if rsi is not None and rsi.value is not None:
            v = float(rsi.value)
            if (long and v <= RSI_OS) or (not long and v >= RSI_OB):
                return False
        return True
