"""Economic campaign value; no native engine import."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaperCampaign:
    campaign_id: str
    opportunity_id: str
    instrument_id: str
    direction: str
    quantity: Decimal
    decision_ns: int
    expires_ns: int

    def __post_init__(self) -> None:
        if self.direction not in {"LONG", "SHORT"}:
            raise ValueError("invalid campaign direction")
        if not self.quantity.is_finite() or self.quantity <= 0:
            raise ValueError("invalid campaign quantity")
        if self.expires_ns <= self.decision_ns:
            raise ValueError("invalid campaign expiry")
