"""Validated external simulation assumptions; no economic defaults."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from v8_next.economics.observer_policy import validate_observer_policy


class PaperConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    maker_fee: Decimal = Field(ge=0)
    taker_fee: Decimal = Field(ge=0)
    initial_balance: Decimal = Field(gt=0)
    max_notional: Decimal = Field(gt=0)
    max_exposure_fraction: Decimal = Field(gt=0, le=1)

    observer_policy: str = "squeeze"

    @field_validator("observer_policy")
    @classmethod
    def valid_observer_policy(cls, value: str) -> str:
        return validate_observer_policy(value)
