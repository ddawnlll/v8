"""Declared-assumption minimum track-length estimator.

MinTRL is horizon evidence only.  It does not select a strategy, certify a
Sharpe ratio, or create an economic claim.  Every statistical and dependence
assumption is supplied by the caller; absent inputs fail closed.
"""

from __future__ import annotations

import hashlib
import math
from statistics import NormalDist
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from v8_next.evaluation.store import canonical


class MinTRLPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_sharpe: float
    null_sharpe: float
    confidence: float = Field(gt=0.0, lt=1.0)
    power: float = Field(gt=0.0, lt=1.0)
    variance: float = Field(gt=0.0)
    dependence_factor: float = Field(gt=0.0)
    interval_unit: str
    annualization_factor: float = Field(gt=0.0)
    method_version: str

    @model_validator(mode="after")
    def validate_assumptions(self) -> MinTRLPlan:
        values = (
            self.target_sharpe,
            self.null_sharpe,
            self.confidence,
            self.power,
            self.variance,
            self.dependence_factor,
            self.annualization_factor,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("MinTRL assumptions must be finite")
        if self.target_sharpe <= self.null_sharpe:
            raise ValueError("target Sharpe must exceed null Sharpe")
        if not self.interval_unit.strip() or not self.method_version.strip():
            raise ValueError("interval unit and method version are required")
        return self

    @property
    def alpha(self) -> float:
        return 1.0 - self.confidence

    @property
    def plan_hash(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json")).encode()).hexdigest()


class MinTRLResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["UNDERPOWERED", "SUPPORTED_HORIZON", "UNSUPPORTED"]
    required_intervals: int | None
    observed_intervals: int
    effective_intervals: float | None
    plan_hash: str
    reason: str | None = None


def estimate_min_trl(plan: MinTRLPlan | None, observed_intervals: int) -> MinTRLResult:
    """Estimate required aligned intervals under one declared normal model.

    The variance/dependence terms are explicit rather than replaced with a
    universal trade-count or calendar threshold.  Annualization is part of
    plan identity and is validated even though Sharpe is already declared in
    the plan's interval unit.
    """

    if type(observed_intervals) is not int or observed_intervals < 0:
        raise ValueError("observed_intervals must be a non-negative integer")
    if plan is None:
        return MinTRLResult(
            status="UNSUPPORTED",
            required_intervals=None,
            observed_intervals=observed_intervals,
            effective_intervals=None,
            plan_hash="",
            reason="DECLARED_MINTRL_PLAN_REQUIRED",
        )
    z_alpha = NormalDist().inv_cdf(1.0 - plan.alpha / 2.0)
    z_power = NormalDist().inv_cdf(plan.power)
    delta = plan.target_sharpe - plan.null_sharpe
    required = math.ceil(
        ((z_alpha + z_power) ** 2 * plan.variance * plan.dependence_factor) / (delta**2)
    )
    effective = observed_intervals / plan.dependence_factor
    return MinTRLResult(
        status="SUPPORTED_HORIZON" if observed_intervals >= required else "UNDERPOWERED",
        required_intervals=max(1, required),
        observed_intervals=observed_intervals,
        effective_intervals=effective,
        plan_hash=plan.plan_hash,
    )
