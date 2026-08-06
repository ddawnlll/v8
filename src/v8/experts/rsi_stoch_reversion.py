"""Overbought/oversold oscillator reversion behavior family
(`rsi_stoch_reversion`).

Hypothesis (mechanism `oscillator_reversion`): after an oscillator extreme,
the bounded oscillator reverts toward its central region; entering on the
first sign of reversion with a price confirmation carries the reversion.

Setup doctrine (book E-05, Ch8.6 p259-262): the oscillator dips below the
oversold level and then rises back above it; the trigger is the HIGH of the
bar associated with the signal, and entry requires a CLOSE beyond that bar's
extreme (never an intraday touch, Ch14.2 doctrine — a close above the signal
bar's high for longs, below its low for shorts). Short = mirror at the
overbought level.

Variants (all frozen; D-044 lists every implemented variant):
  a  RSI-only: rsi14 dips below 30 then rises back above 30 (short: above 70
     then falls back below).
  b  RSI+stoch confluence: BOTH rsi14 and stoch_k dip below oversold (30/20)
     and BOTH rise back above (short mirror at 70/80).
  c  CCI-only: cci20 dips below -100 then rises back above -100 (short: above
     +100 then falls back below).

The book card's variant `c` describes a dual-period CCI (CCI20 AND CCI100);
CCI100 is not an emitted feature, so `c` is implemented single-period CCI20
(deviation recorded in the implementer report).

The setup anchor is the SIGNAL BAR: the first bar of the current run where the
oscillator is back on the reverted side of its extreme (D-026; the run-start
semantics of `find_setup_anchor`). The gate reads the state features for the
current-bar condition and recomputes the oscillator series over the `history`
window for the dip/crossing context (per-bar oscillator values are not carried
in the history tuples). Stoch %K and CCI are window-stationary (a bar's value
depends only on its own trailing window, so the local series equals the
feature exactly at the newest bar); Wilder RSI is not, so the gate requires
BOTH the feature and the local newest value to satisfy the threshold — a
near-threshold disagreement fails the setup conservatively rather than
emitting an anchor the anchor scan cannot reproduce.
"""
from __future__ import annotations

from ..schema import MarketState, CandidateDraft, ExpertEvaluation
from .base import Expert

# Oversold / overbought levels (declared, never fitted; book Ch8.6 p259-262).
RSI_OS = 30.0
RSI_OB = 70.0
STOCH_OS = 20.0
STOCH_OB = 80.0
CCI_OS = -100.0
CCI_OB = 100.0


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    if avg_gain == 0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _rsi_per_bar(closes, period: int = 14) -> list:
    """Wilder RSI per bar over the given close series; None before the seed
    (a bar needs `period` prior deltas). Identical formula to marketstate's
    rsi14 so the local series is the same computation over a shorter window."""
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


def _stoch_k_per_bar(highs, lows, closes, period: int = 14) -> list:
    """Raw fast %K per bar (G-09): (C - L14) / (H14 - L14) * 100. Window-
    stationary: a bar's value depends only on its own trailing 14 bars."""
    ks = []
    for i in range(len(closes)):
        lo = max(0, i - period + 1)
        h14 = max(highs[lo:i + 1])
        l14 = min(lows[lo:i + 1])
        if h14 == l14:
            ks.append(50.0)
        else:
            ks.append((closes[i] - l14) / (h14 - l14) * 100.0)
    return ks


def _sma3(values: list) -> list:
    out = []
    for i in range(len(values)):
        out.append(sum(values[max(0, i - 2):i + 1]) / len(values[max(0, i - 2):i + 1]))
    return out


def _cci_per_bar(highs, lows, closes, period: int = 20) -> list:
    """CCI per bar (G-11): (TP - SMA(TP,n)) / (0.015 * mean_abs_dev); None
    before the seed. Window-stationary (matches marketstate's cci20 formula)."""
    out = []
    for i in range(len(closes)):
        lo = max(0, i - period + 1)
        if i - lo + 1 < period:
            out.append(None)
            continue
        tp = [(highs[j] + lows[j] + closes[j]) / 3.0 for j in range(lo, i + 1)]
        sma = sum(tp) / period
        mad = sum(abs(v - sma) for v in tp) / period
        out.append((tp[-1] - sma) / (0.015 * mad) if mad else 0.0)
    return out


def _run_start(cond, n: int) -> int:
    """First index of the newest consecutive run where cond(i) holds; -1 if the
    newest bar fails cond (the run-start semantics of Expert.find_setup_anchor,
    returned as an index instead of the event_id)."""
    i = n - 1
    if i < 0 or not cond(i):
        return -1
    while i > 0 and cond(i - 1):
        i -= 1
    return i


class RsiStochReversionExpert(Expert):
    """Oscillator extreme reversion with a close-beyond-signal-bar trigger."""
    expert_id = 'rsi_stoch_reversion'
    version = 'v1'
    mechanism_family_id = 'oscillator_reversion'
    behavior_family_id = 'overbought_oversold_reversion'
    variant_id = 'a'
    # D-044: every implemented variant, losers included; the reported
    # variant_id is a member of this list. D-046: all thresholds/lookbacks are
    # declared constants frozen pre-window, so the search universe equals the
    # evaluated set.
    variants_evaluated = ('a', 'b', 'c')
    search_universe_size = 3
    requires = ('oscillator', 'volatility', 'history')

    def __init__(self, variant_id: str | None = None):
        if variant_id is not None:
            if variant_id not in self.variants_evaluated:
                raise ValueError(
                    f'{self.expert_id}: unknown variant {variant_id!r} '
                    f'(variants_evaluated={list(self.variants_evaluated)})')
            self.variant_id = variant_id

    # --- local recomputations (see module docstring) -----------------------

    def _detect_rsi(self, close, hist, rsi, rsi_now):
        """Variant a: rsi14 dipped below oversold then rose back above; the
        signal bar is the run start of the recovered side. Trigger: close
        beyond the signal bar's extreme."""
        n = len(rsi)
        if rsi_now > RSI_OS and rsi[-1] is not None and rsi[-1] > RSI_OS:
            s = _run_start(lambda i: rsi[i] is not None and rsi[i] > RSI_OS, n)
            if s >= 1 and rsi[s - 1] is not None and rsi[s - 1] <= RSI_OS:
                signal_high = hist[s][2]
                if close > signal_high:
                    return 'LONG', s, signal_high
        if rsi_now < RSI_OB and rsi[-1] is not None and rsi[-1] < RSI_OB:
            s = _run_start(lambda i: rsi[i] is not None and rsi[i] < RSI_OB, n)
            if s >= 1 and rsi[s - 1] is not None and rsi[s - 1] >= RSI_OB:
                signal_low = hist[s][3]
                if close < signal_low:
                    return 'SHORT', s, signal_low
        return None

    def _detect_confluence(self, close, hist, rsi, stoch_k, rsi_now, stoch_k_now):
        """Variant b: BOTH rsi14 and stoch_k dipped below oversold and BOTH
        rose back above; signal bar = run start of the both-recovered state."""
        n = len(stoch_k)
        if rsi_now > RSI_OS and stoch_k_now > STOCH_OS \
                and rsi[-1] is not None and rsi[-1] > RSI_OS \
                and stoch_k[-1] > STOCH_OS:
            cond = lambda i: rsi[i] is not None and rsi[i] > RSI_OS \
                and stoch_k[i] > STOCH_OS
            s = _run_start(cond, n)
            dipped = any(rsi[j] is not None and rsi[j] <= RSI_OS
                         for j in range(n)) \
                and any(stoch_k[j] <= STOCH_OS for j in range(n))
            if s >= 1 and cond(s - 1) is False and dipped:
                signal_high = hist[s][2]
                if close > signal_high:
                    return 'LONG', s, signal_high
        if rsi_now < RSI_OB and stoch_k_now < STOCH_OB \
                and rsi[-1] is not None and rsi[-1] < RSI_OB \
                and stoch_k[-1] < STOCH_OB:
            cond = lambda i: rsi[i] is not None and rsi[i] < RSI_OB \
                and stoch_k[i] < STOCH_OB
            s = _run_start(cond, n)
            spiked = any(rsi[j] is not None and rsi[j] >= RSI_OB
                         for j in range(n)) \
                and any(stoch_k[j] >= STOCH_OB for j in range(n))
            if s >= 1 and cond(s - 1) is False and spiked:
                signal_low = hist[s][3]
                if close < signal_low:
                    return 'SHORT', s, signal_low
        return None

    def _detect_cci(self, close, hist, cci, cci_now):
        """Variant c: cci20 dipped below -100 then rose back above; short
        mirror at +100."""
        n = len(cci)
        if cci_now > CCI_OS and cci[-1] is not None and cci[-1] > CCI_OS:
            s = _run_start(lambda i: cci[i] is not None and cci[i] > CCI_OS, n)
            if s >= 1 and cci[s - 1] is not None and cci[s - 1] <= CCI_OS:
                signal_high = hist[s][2]
                if close > signal_high:
                    return 'LONG', s, signal_high
        if cci_now < CCI_OB and cci[-1] is not None and cci[-1] < CCI_OB:
            s = _run_start(lambda i: cci[i] is not None and cci[i] < CCI_OB, n)
            if s >= 1 and cci[s - 1] is not None and cci[s - 1] >= CCI_OB:
                signal_low = hist[s][3]
                if close < signal_low:
                    return 'SHORT', s, signal_low
        return None

    def evaluate(self, state: MarketState) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        common = [f'{sym}.close', f'{sym}.atr', f'{sym}.history']
        if self.variant_id == 'a':
            need = common + [f'{sym}.rsi14']
        elif self.variant_id == 'b':
            need = common + [f'{sym}.rsi14', f'{sym}.stoch_k', f'{sym}.stoch_d']
        else:
            need = common + [f'{sym}.cci20']
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
        hist = tuple(hist_value)
        # The dip + recovery must be verifiable inside the history window and
        # the crossing needs an RSI seed; reject a too-short window outright.
        if len(hist) < 21:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        closes = [float(b[4]) for b in hist]
        highs = [float(b[2]) for b in hist]
        lows = [float(b[3]) for b in hist]
        if self.variant_id == 'a':
            hit = self._detect_rsi(close, hist, _rsi_per_bar(closes),
                                   float(f[f'{sym}.rsi14'].value))
        elif self.variant_id == 'b':
            hit = self._detect_confluence(
                close, hist, _rsi_per_bar(closes), _stoch_k_per_bar(highs, lows, closes),
                float(f[f'{sym}.rsi14'].value), float(f[f'{sym}.stoch_k'].value))
        else:
            hit = self._detect_cci(close, hist, _cci_per_bar(highs, lows, closes),
                                   float(f[f'{sym}.cci20'].value))
        if hit is None:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        direction, s, ref = hit
        anchor = hist[s][0]
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{sym}:{self.variant_id}:{direction}:{ref:.6f}:{close:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': atr, 'variant': self.variant_id},
            birth_time=t, setup_anchor_event_id=anchor)
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)

    def still_valid(self, state: MarketState, draft: CandidateDraft) -> bool:
        """The thesis is "the extreme reverted": the oscillator must stay on
        the reverted side of its level. A re-entry into the extreme zone says
        the reversion failed — close. Fails open when the oscillator feature
        is unobservable (the price stop still governs)."""
        sym = draft.instrument
        f = state.features
        variant = draft.risk_geometry.get('variant', self.variant_id)
        if variant == 'a':
            rsi = f.get(f'{sym}.rsi14')
            if rsi is None or rsi.value is None:
                return True
            rsi = float(rsi.value)
            if draft.direction == 'LONG':
                return rsi > RSI_OS
            return rsi < RSI_OB
        if variant == 'b':
            rsi = f.get(f'{sym}.rsi14')
            stoch = f.get(f'{sym}.stoch_k')
            if rsi is None or rsi.value is None or stoch is None or stoch.value is None:
                return True
            rsi, stoch = float(rsi.value), float(stoch.value)
            if draft.direction == 'LONG':
                return rsi > RSI_OS and stoch > STOCH_OS
            return rsi < RSI_OB and stoch < STOCH_OB
        cci = f.get(f'{sym}.cci20')
        if cci is None or cci.value is None:
            return True
        cci = float(cci.value)
        if draft.direction == 'LONG':
            return cci > CCI_OS
        return cci < CCI_OB
