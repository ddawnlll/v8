"""Physical venue-cost calibration and operating-net accounting."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from v8_next.evaluation.parity import ArtifactBinding


class VenueFillCost(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    quantity: Decimal = Field(gt=0)
    fee: Decimal = Field(ge=0)
    fill_price: Decimal = Field(gt=0)
    reference_mid: Decimal | None = Field(default=None, gt=0)


class VenueCostReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["CALIBRATED", "DATA_BLOCKED"]
    fee_rate: Decimal | None
    fill_vs_mid_bps: Decimal | None
    source_artifact: ArtifactBinding
    calibration_version: str


class OperatingExpense(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    amount: Decimal = Field(ge=0)
    currency: str
    period_start_ns: int
    period_end_ns: int
    source_artifact: ArtifactBinding

    @model_validator(mode="after")
    def validate_period(self) -> OperatingExpense:
        if self.period_end_ns <= self.period_start_ns or not self.currency.strip():
            raise ValueError("operating expense period/currency is invalid")
        return self


class OperatingNetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["NO_ECONOMIC_CLAIM", "DATA_BLOCKED"]
    transaction_pnl: Decimal
    funding: Decimal
    explicit_fees: Decimal
    strategy_net: Decimal
    operating_costs: Decimal
    operating_net: Decimal
    currency: str
    period_start_ns: int
    period_end_ns: int


def calibrate_venue_cost(
    fills: tuple[VenueFillCost, ...], source_artifact: ArtifactBinding
) -> VenueCostReceipt:
    verified, detail = source_artifact.verify()
    if not verified:
        raise ValueError(f"DATA_BLOCKED_COST_ARTIFACT: {detail}")
    if not fills:
        return VenueCostReceipt(
            status="DATA_BLOCKED",
            fee_rate=None,
            fill_vs_mid_bps=None,
            source_artifact=source_artifact,
            calibration_version="venue-cost.v1",
        )
    quantity = sum((row.quantity for row in fills), Decimal(0))
    fee_rate = sum((row.fee for row in fills), Decimal(0)) / quantity
    with_mid = [row for row in fills if row.reference_mid is not None]
    if not with_mid:
        return VenueCostReceipt(
            status="DATA_BLOCKED",
            fee_rate=None,
            fill_vs_mid_bps=None,
            source_artifact=source_artifact,
            calibration_version="venue-cost.v1",
        )
    friction_total = Decimal(0)
    for row in with_mid:
        reference_mid = row.reference_mid
        assert reference_mid is not None
        friction_total += abs(row.fill_price - reference_mid) / reference_mid * Decimal(10_000)
    friction = friction_total / Decimal(len(with_mid))
    return VenueCostReceipt(
        status="CALIBRATED",
        fee_rate=fee_rate,
        fill_vs_mid_bps=friction,
        source_artifact=source_artifact,
        calibration_version="venue-cost.v1",
    )


def compute_operating_net(
    *,
    transaction_pnl: Decimal,
    funding: Decimal | None,
    explicit_fees: Decimal | None,
    expenses: tuple[OperatingExpense, ...],
    currency: str,
    price_pnl_already_net_of_friction: bool = False,
) -> OperatingNetResult:
    if funding is None or explicit_fees is None or not expenses:
        return OperatingNetResult(
            status="DATA_BLOCKED",
            transaction_pnl=transaction_pnl,
            funding=funding or Decimal(0),
            explicit_fees=explicit_fees or Decimal(0),
            strategy_net=Decimal(0),
            operating_costs=Decimal(0),
            operating_net=Decimal(0),
            currency=currency,
            period_start_ns=0,
            period_end_ns=0,
        )
    if not currency.strip() or any(exp.currency != currency for exp in expenses):
        raise ValueError("operating-net currency mismatch")
    for expense in expenses:
        verified, detail = expense.source_artifact.verify()
        if not verified:
            raise ValueError(f"DATA_BLOCKED_COST_ARTIFACT: {detail}")
    if not all(value.is_finite() for value in (transaction_pnl, funding, explicit_fees)):
        raise ValueError("operating-net values must be finite")
    strategy_net = transaction_pnl + funding
    if not price_pnl_already_net_of_friction:
        strategy_net -= explicit_fees
    operating_costs = sum((exp.amount for exp in expenses), Decimal(0))
    start = min(exp.period_start_ns for exp in expenses)
    end = max(exp.period_end_ns for exp in expenses)
    return OperatingNetResult(
        status="NO_ECONOMIC_CLAIM",
        transaction_pnl=transaction_pnl,
        funding=funding,
        explicit_fees=explicit_fees,
        strategy_net=strategy_net,
        operating_costs=operating_costs,
        operating_net=strategy_net - operating_costs,
        currency=currency,
        period_start_ns=start,
        period_end_ns=end,
    )
