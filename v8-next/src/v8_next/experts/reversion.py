"""Active v1/a Bollinger fade and RSI recovery expert observations."""

from decimal import Decimal

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, Stance, numeric
from v8_next.experts.common import context_reason, directional_stance
from v8_next.experts.features import close_series, wilder_rsi


def bollinger_direction(close: float, mid: float, sd: float) -> str | None:
    # The outer 3-sigma boundary is open; the inner 2-sigma boundary is closed.
    if sd <= 0:
        return None
    if mid + 2 * sd <= close < mid + 3 * sd:
        return "SHORT"
    if mid - 3 * sd < close <= mid - 2 * sd:
        return "LONG"
    return None


def observe_bollinger_reversion(frame: CausalFrame, opportunity: Opportunity | None) -> Stance:
    reason = context_reason(frame, opportunity, 20)
    direction = None
    if reason is None:
        closes = close_series(frame).tail(20)
        mid, sd = numeric(closes.mean()), numeric(closes.std(ddof=0))
        direction = bollinger_direction(float(closes[-1]), mid, sd)
        reason = "DEGENERATE_FEATURE" if sd <= 0 else "BAND_FADE" if direction else "NO_FADE_ZONE"
    return directional_stance(
        frame,
        opportunity,
        family="bollinger-reversion",
        dependency="ohlcv-band-20-v1",
        mechanism="band-mean-reversion-hypothesis",
        direction=direction,
        reason=reason,
    )


def observe_rsi_reversion(frame: CausalFrame, opportunity: Opportunity | None) -> Stance:
    reason = context_reason(frame, opportunity, 21)
    direction = None
    if reason is None:
        rsi = wilder_rsi(close_series(frame))
        reason = "NO_RECOVERY_TRIGGER"
        # LONG takes precedence as in the active Rust v1/a hypothesis.
        for side, threshold in (("LONG", 30), ("SHORT", 70)):

            def recovered(
                value: float | None, threshold: int = threshold, side: str = side
            ) -> bool:
                return value is not None and (
                    value > threshold if side == "LONG" else value < threshold
                )

            if not recovered(rsi[-1]):
                continue
            start = len(rsi) - 1
            while start > 0 and recovered(rsi[start - 1]):
                start -= 1
            if start == 0 or rsi[start - 1] is None:
                continue
            signal, latest = frame.candles[start], frame.candles[-1]
            if latest.close > signal.high if side == "LONG" else latest.close < signal.low:
                direction, reason = side, "RSI_RECOVERY_EXTREME_BREAK"
                break
    return directional_stance(
        frame,
        opportunity,
        family="rsi-stoch-reversion",
        dependency="ohlcv-rsi-14-v1",
        mechanism="oscillator-recovery-hypothesis",
        direction=direction,
        reason=reason,
    )


def bollinger_fade_distance(frame: CausalFrame) -> Decimal | None:
    """Freeze clamped sigma/range geometry at the current fade run's first bar."""
    if len(frame.candles) < 20 or not frame.continuous:
        return None
    closes = close_series(frame)
    means = closes.rolling_mean(20)
    deviations = closes.rolling_std(20, ddof=0)
    directions = [
        bollinger_direction(float(closes[i]), numeric(means[i]), numeric(deviations[i]))
        if i >= 19
        else None
        for i in range(len(closes))
    ]
    side = directions[-1]
    if side is None:
        return None
    anchor = len(closes) - 1
    while anchor > 19 and directions[anchor - 1] == side:
        anchor -= 1
    span = sum((c.high - c.low for c in frame.candles[anchor - 13 : anchor + 1]), Decimal(0)) / 14
    sigma = Decimal(str(numeric(deviations[anchor])))
    if span <= 0 or sigma <= 0:
        return None
    return min(Decimal(2) * span, max(Decimal(".8") * span, sigma))
