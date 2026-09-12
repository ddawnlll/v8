"""Evidence-backed capacity and market-impact measurement.

Only sequenced quote/fill/ADV observations are accepted.  OHLCV scaling is
not a capacity measurement and therefore is intentionally absent here.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MicrostructureObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    timestamp_ns: int = Field(ge=0)
    instrument_id: str
    mid: float = Field(gt=0.0)
    spread: float = Field(ge=0.0)
    adv_qty: float = Field(gt=0.0)
    requested_qty: float = Field(gt=0.0)
    filled_qty: float = Field(ge=0.0)
    fill_price: float = Field(gt=0.0)

    @model_validator(mode="after")
    def validate_row(self) -> MicrostructureObservation:
        if not self.instrument_id.strip():
            raise ValueError("instrument_id is required")
        if self.filled_qty > self.requested_qty:
            raise ValueError("filled quantity exceeds requested quantity")
        if not all(
            math.isfinite(value)
            for value in (
                self.mid,
                self.spread,
                self.adv_qty,
                self.requested_qty,
                self.filled_qty,
                self.fill_price,
            )
        ):
            raise ValueError("microstructure values must be finite")
        return self


class CapacityScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scale: float = Field(gt=0.0)
    requested_multiplier: float = Field(gt=0.0)


class CapacityMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["DATA_BLOCKED", "UNRESOLVED", "NO_ECONOMIC_CLAIM"]
    scale: float
    participation: float | None
    fill_ratio: float | None
    spread_cost_bps: float | None
    impact_bps: float | None
    shortfall_bps: float | None
    observation_count: int


def measure_capacity(
    observations: tuple[MicrostructureObservation, ...], scenario: CapacityScenario
) -> CapacityMeasurement:
    if not observations:
        return CapacityMeasurement(
            status="DATA_BLOCKED",
            scale=scenario.scale,
            participation=None,
            fill_ratio=None,
            spread_cost_bps=None,
            impact_bps=None,
            shortfall_bps=None,
            observation_count=0,
        )
    n = len(observations)
    participation = sum(
        row.requested_qty * scenario.requested_multiplier / row.adv_qty for row in observations
    ) / n
    fill_ratio = sum(row.filled_qty / row.requested_qty for row in observations) / n
    spread_cost = sum(row.spread / row.mid * 10_000.0 for row in observations) / n
    impact = sum(abs(row.fill_price - row.mid) / row.mid * 10_000.0 for row in observations) / n
    # Spread and impact are separately reported; neither is reused as a hidden
    # linear coefficient for another scale.
    shortfall = sum(
        (abs(row.fill_price - row.mid) + row.spread / 2.0) / row.mid * 10_000.0
        for row in observations
    ) / n
    return CapacityMeasurement(
        status="NO_ECONOMIC_CLAIM",
        scale=scenario.scale,
        participation=participation,
        fill_ratio=fill_ratio,
        spread_cost_bps=spread_cost,
        impact_bps=impact,
        shortfall_bps=shortfall,
        observation_count=n,
    )
