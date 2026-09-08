"""Economic campaign value; no native engine import."""

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from v8_next.domain.market import CausalFrame


@dataclass(frozen=True)
class PaperCampaign:
    campaign_id: str
    opportunity_id: str
    instrument_id: str
    direction: str
    quantity: Decimal
    decision_ns: int
    expires_ns: int
    stop_price: Decimal | None = None
    target_price: Decimal | None = None
    close_invalidation_price: Decimal | None = None
    live_channel_bars: int | None = None
    validity_indicator: str | None = None

    def __post_init__(self) -> None:
        if self.direction not in {"LONG", "SHORT"}:
            raise ValueError("invalid campaign direction")
        if not self.quantity.is_finite() or self.quantity <= 0:
            raise ValueError("invalid campaign quantity")
        if self.expires_ns <= self.decision_ns:
            raise ValueError("invalid campaign expiry")

        if self.validity_indicator is not None and (
            self.validity_indicator not in {"kijun26", "ema5-above-ema20", "macd-zero"}
            or self.live_channel_bars is not None
            or (
                self.close_invalidation_price is not None
                and self.validity_indicator != "ema5-above-ema20"
            )
        ):
            raise ValueError("unknown or ambiguous indicator validity")
        if self.live_channel_bars is not None and (
            type(self.live_channel_bars) is not int
            or self.live_channel_bars <= 0
            or self.close_invalidation_price is not None
        ):
            raise ValueError("invalid or ambiguous live channel validity")
        if self.close_invalidation_price is not None and (
            not self.close_invalidation_price.is_finite() or self.close_invalidation_price <= 0
        ):
            raise ValueError("invalid close invalidation reference")
        if (self.stop_price is None) != (self.target_price is None):
            raise ValueError("campaign needs both stop and target or neither")
        if self.stop_price is not None and self.target_price is not None:
            if any(not p.is_finite() or p <= 0 for p in (self.stop_price, self.target_price)):
                raise ValueError("invalid campaign protection price")
            if (self.target_price - self.stop_price) * (1 if self.direction == "LONG" else -1) <= 0:
                raise ValueError("inverted campaign protection")

    def invalidated_by_close(self, frame: CausalFrame) -> bool | None:
        """None means unobservable; False means an observed thesis still holds.

        Only a later completed causal bar may invalidate a frozen entry thesis.
        Missing input does not manufacture either validity or invalidity.
        """
        if (
            self.close_invalidation_price is None
            and self.live_channel_bars is None
            and self.validity_indicator is None
        ):
            return None
        if frame.instrument_id != self.instrument_id:
            raise ValueError("campaign validity instrument mismatch")
        if not frame.continuous or not frame.candles:
            return None
        candle = frame.candles[-1]
        if candle.end_ns <= self.decision_ns:
            return None
        sign = 1 if self.direction == "LONG" else -1
        if self.validity_indicator == "macd-zero":
            from v8_next.experts.features import macd_line

            if len(frame.candles) < 34:
                return None
            return macd_line(frame) * sign <= 0
        reference = self.close_invalidation_price
        if self.validity_indicator == "ema5-above-ema20":
            from v8_next.experts.features import trend_emas

            if len(frame.candles) < 20:
                return None
            fast, slow = trend_emas(frame)
            if fast <= slow:
                return True
            if reference is None:
                return False
        if self.live_channel_bars is not None:
            if len(frame.candles) < self.live_channel_bars + 1:
                return None
            prior = frame.candles[-self.live_channel_bars - 1 : -1]
            reference = min(c.low for c in prior) if sign == 1 else max(c.high for c in prior)
        if self.validity_indicator == "kijun26":
            if len(frame.candles) < 26:
                return None
            window = frame.candles[-26:]
            reference = (max(c.high for c in window) + min(c.low for c in window)) / 2
        assert reference is not None
        return (candle.close - reference) * sign <= 0

    def to_record(self) -> dict[str, Any]:
        return {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in asdict(self).items()
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "PaperCampaign":
        decoded = dict(record)
        for key in ("quantity", "stop_price", "target_price", "close_invalidation_price"):
            if decoded.get(key) is not None:
                decoded[key] = Decimal(decoded[key])
        return cls(**decoded)
