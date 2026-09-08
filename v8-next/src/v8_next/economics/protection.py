"""Frozen exit geometry: economic policy only, never simulated fill logic."""

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, StanceKind
from v8_next.experts.bollinger import band_setup
from v8_next.experts.breakouts import (
    last_close_breakout,
    observe_failed_breakout,
    observe_volume_breakout,
)
from v8_next.experts.candlestick import VARIANTS as CANDLE_VARIANTS
from v8_next.experts.candlestick import candle_pattern
from v8_next.experts.gaps import gap_setup
from v8_next.experts.measuring import VARIANTS, measuring_setup
from v8_next.experts.pandf import pandf_setup
from v8_next.experts.reversion import observe_rsi_reversion
from v8_next.experts.trend import observe_trend_depth, observe_trend_pullback

PROTECTION_POLICIES = frozenset(
    {
        "timeout-only-v1",
        "donchian:a:v2",
        "trend-pullback:a:v2",
        "trend-depth:a:v2",
        "rsi-reversion:a:v2",
        "volume-breakout:active:v2",
        "failed-breakout:a:v2",
        *(f"gap:{v}:v2" for v in "abc"),
        *(f"candlestick:{v}:v2" for v in CANDLE_VARIANTS),
        *(f"pandf:{v}:v2" for v in "abcd"),
        *(f"bollinger:{v}:v2" for v in "abc"),
        *(f"measuring:{v}:v2" for v in VARIANTS),
    }
)


@dataclass(frozen=True)
class CampaignProtection:
    policy: str
    opportunity_id: str
    instrument_id: str
    direction: str
    observed_ns: int
    expires_ns: int
    stop_price: Decimal
    target_price: Decimal

    def __post_init__(self) -> None:
        if self.policy not in PROTECTION_POLICIES or self.policy == "timeout-only-v1":
            raise ValueError("unknown protected campaign policy")
        if self.direction not in {"LONG", "SHORT"} or self.expires_ns <= self.observed_ns:
            raise ValueError("invalid protection direction or clocks")
        if any(not p.is_finite() or p <= 0 for p in (self.stop_price, self.target_price)):
            raise ValueError("invalid protection prices")
        if (self.target_price - self.stop_price) * (1 if self.direction == "LONG" else -1) <= 0:
            raise ValueError("inverted protection")


def protection_at(
    frame: CausalFrame, opportunity: Opportunity, policy: str, tick: Decimal
) -> CampaignProtection | None:
    if policy not in PROTECTION_POLICIES:
        raise ValueError("unknown campaign policy")
    if policy == "timeout-only-v1":
        return None
    if not tick.is_finite() or tick <= 0:
        raise ValueError("positive venue tick required")
    if (
        opportunity.instrument_id != frame.instrument_id
        or opportunity.anchor_ns > frame.decision_ns
    ):
        raise ValueError("protection outside opportunity domain")
    if not frame.continuous or not frame.candles or opportunity.direction not in {"LONG", "SHORT"}:
        return None
    family, variant, _ = policy.split(":")
    sign = 1 if opportunity.direction == "LONG" else -1
    close = frame.candles[-1].close
    unit_geometry_observers = {
        "trend-pullback": observe_trend_pullback,
        "trend-depth": observe_trend_depth,
        "rsi-reversion": observe_rsi_reversion,
        "volume-breakout": observe_volume_breakout,
    }
    if family in unit_geometry_observers:
        observer = unit_geometry_observers[family]
        if observer(frame, opportunity).kind != StanceKind.SUPPORT:
            return None
        span = sum((c.high - c.low for c in frame.candles[-14:]), Decimal(0)) / 14
        if span <= 0:
            return None
        # Active Rust v1 declares one range unit each way, not its alternate
        # v2 structural stop. Execution remains V8-next frozen absolute geometry.
        stop, target = close - sign * span, close + sign * span
    elif family == "failed-breakout":
        if (
            len(frame.candles) < 14
            or observe_failed_breakout(frame, opportunity).kind != StanceKind.SUPPORT
        ):
            return None
        breakout = last_close_breakout(frame)
        assert breakout is not None
        stop = breakout[1]
        span = sum((c.high - c.low for c in frame.candles[-14:]), Decimal(0)) / 14
        if span <= 0:
            return None
        target = close - span
    elif family in {"donchian", "gap", "candlestick"}:
        if len(frame.candles) < 14:
            return None
        span = sum((c.high - c.low for c in frame.candles[-14:]), Decimal(0)) / 14
        if span <= 0:
            return None
        if family == "donchian":
            if sign != 1 or len(frame.candles) < 21:
                return None
            prior = frame.candles[-21:-1]
            if close <= max(c.high for c in prior):
                return None
            stop = min(c.low for c in prior)
        elif family == "gap":
            gap = gap_setup(frame, variant)
            if gap is None or gap.direction != opportunity.direction:
                return None
            stop = gap.stop_reference
        else:
            candle = candle_pattern(frame, variant)
            if candle is None or candle.direction != opportunity.direction:
                return None
            raw_distance = (close - candle.stop_reference) * sign
            if raw_distance <= 0:
                return None
            distance = min(Decimal(2) * span, max(Decimal(".8") * span, raw_distance))
            stop = close - sign * distance
        target = close + sign * span
    elif family == "pandf":
        pf = pandf_setup(frame, variant)
        if pf is None or pf.direction != opportunity.direction:
            return None
        stop, target = pf.stop, pf.target
    elif family == "measuring":
        measured = measuring_setup(frame, variant)
        if measured is None or measured.direction != opportunity.direction:
            return None
        stop, target = measured.stop_reference, close + sign * measured.target_distance
    else:
        band = band_setup(frame, variant)
        if band is None or band.direction != opportunity.direction:
            return None
        span = Decimal(str(band.mean_range_reference))
        stop = close - sign * Decimal(str(band.stop_r)) * span
        target = close + sign * Decimal(str(band.target_r)) * span
    # Tighten stop and round target toward entry, never silently enlarge price risk.
    stop = (stop / tick).to_integral_value(
        rounding=ROUND_CEILING if sign == 1 else ROUND_FLOOR
    ) * tick
    target = (target / tick).to_integral_value(
        rounding=ROUND_FLOOR if sign == 1 else ROUND_CEILING
    ) * tick
    if stop <= 0 or target <= 0 or (close - stop) * sign <= 0 or (target - close) * sign <= 0:
        return None
    duration = frame.candles[-1].end_ns - frame.candles[-1].start_ns
    if any(c.end_ns - c.start_ns != duration for c in frame.candles):
        raise ValueError("protection requires regular bars")
    expires = min(opportunity.expires_ns, frame.candles[-1].end_ns + 8 * duration)
    if expires <= frame.decision_ns:
        return None
    return CampaignProtection(
        policy,
        opportunity.opportunity_id,
        frame.instrument_id,
        opportunity.direction,
        frame.decision_ns,
        expires,
        stop,
        target,
    )
