"""Descriptive causal regimes, never calibrated habitat or admission authority."""

from dataclasses import dataclass
from decimal import Decimal

from v8_next.domain.market import CausalFrame
from v8_next.domain.positioning import PositioningReading, positioning_at


@dataclass(frozen=True)
class RegimeObservation:
    instrument_id: str
    decision_ns: int
    volume: str | None
    funding: str | None
    volume_ratio: str | None
    funding_rate: str | None
    version: str = "volume20-settled-funding-v1"
    trend: str | None = None
    volatility: str | None = None
    habitat_status: str = "UNQUALIFIED"


def observe_regime(
    frame: CausalFrame, *, readings: tuple[PositioningReading, ...] = ()
) -> RegimeObservation:
    """Current-inclusive 20 closed bars; funding retains provider expiry policy.

    Thresholds come from legacy quant.rs. Unlike its ablation caller, this
    version requires a full 20-bar window and never labels missing inputs normal.
    Trend/ATR definitions are not yet qualified and remain absent.
    """
    ratio = None
    volume = None
    if frame.continuous and len(frame.candles) >= 20:
        window = frame.candles[-20:]
        average = sum((c.volume for c in window), Decimal(0)) / 20
        if average > 0:
            ratio = window[-1].volume / average
            volume = (
                "VolumeExpansion"
                if ratio >= Decimal("1.30")
                else "VolumeDrought"
                if ratio <= Decimal("0.70")
                else "NormalVolume"
            )
    rate = positioning_at(readings, frame.instrument_id, "settled_funding_rate", frame.decision_ns)
    funding = None
    if rate is not None:
        funding = (
            "CrowdedLong"
            if rate >= Decimal("0.00015")
            else "CrowdedShort"
            if rate <= Decimal("-0.00015")
            else "NeutralFunding"
        )
    return RegimeObservation(
        frame.instrument_id,
        frame.decision_ns,
        volume,
        funding,
        str(ratio) if ratio is not None else None,
        str(rate) if rate is not None else None,
    )
