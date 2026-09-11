"""Counterfactual authority and fail-closed outcome semantics — port of
v8-core/src/oracle/authority.rs (TARGET_ORACLE_SPEC §8, §16, §18.1).

Authority level and identifiability status are strictly orthogonal. ``OracleOutcome`` is a
closed set of four shapes and **UNKNOWN is first-class**: it carries a typed refusal and never
collapses into a zero point estimate. Every constructor refuses the states the Rust side
refuses, with the same refusal code (``INSUFFICIENT_SUPPORT``).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import StrEnum

from v8_next.oracle.taxonomy import (
    AuthorityLevel,
    Identifiability,
    OracleRefusal,
)


class OracleRefused(Exception):
    """Raised when an outcome is asked for a state the data does not support."""

    def __init__(self, refusal: OracleRefusal, message: str = "") -> None:
        super().__init__(f"{refusal.value}{': ' + message if message else ''}")
        self.refusal = refusal


@dataclass(frozen=True)
class CounterfactualAuthority:
    """Explicit counterfactual authority composition (the Rust *struct*, not the axis enum)."""

    oracle_authority_level: AuthorityLevel
    identifiability_status: Identifiability
    support_rule_id: str
    environment_model_id: str
    assumptions: tuple[str, ...] = ()

    def identity(self) -> str:
        payload = json.dumps(
            {
                "oracle_authority_level": self.oracle_authority_level.name,
                "identifiability_status": self.identifiability_status.value,
                "support_rule_id": self.support_rule_id,
                "environment_model_id": self.environment_model_id,
                "assumptions": list(self.assumptions),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha1(f"counterfactual-authority-v1|{payload}".encode()).hexdigest()

    def is_identified(self) -> bool:
        return self.identifiability_status is Identifiability.IDENTIFIED

    def as_dict(self) -> dict[str, object]:
        return {
            "oracle_authority_level": self.oracle_authority_level.name,
            "identifiability_status": self.identifiability_status.value,
            "support_rule_id": self.support_rule_id,
            "environment_model_id": self.environment_model_id,
            "assumptions": list(self.assumptions),
            "identity": self.identity(),
        }


class OracleOutcomeKind(StrEnum):
    IDENTIFIED = "IDENTIFIED"
    PARTIALLY_IDENTIFIED = "PARTIALLY_IDENTIFIED"
    MODEL_DERIVED = "MODEL_DERIVED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OracleOutcome:
    """A counterfactual answer, or a typed refusal. UNKNOWN is never a zero."""

    kind: OracleOutcomeKind
    authority: CounterfactualAuthority
    point_estimate: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    refusal: OracleRefusal | None = None
    supporting_evidence: dict[str, object] = field(default_factory=dict)

    # -- constructors, each refusing what the Rust side refuses ----------------------

    @classmethod
    def identified(cls, point: float, authority: CounterfactualAuthority) -> OracleOutcome:
        if authority.identifiability_status is not Identifiability.IDENTIFIED:
            raise OracleRefused(OracleRefusal.INSUFFICIENT_SUPPORT, "authority is not identified")
        if not math.isfinite(point):
            raise OracleRefused(OracleRefusal.INSUFFICIENT_SUPPORT, "non-finite point estimate")
        return cls(OracleOutcomeKind.IDENTIFIED, authority, point_estimate=point)

    @classmethod
    def partially_identified(
        cls, lower: float, upper: float, authority: CounterfactualAuthority
    ) -> OracleOutcome:
        if authority.identifiability_status is not Identifiability.PARTIALLY_IDENTIFIED:
            raise OracleRefused(OracleRefusal.INSUFFICIENT_SUPPORT, "authority is not partial")
        if not (math.isfinite(lower) and math.isfinite(upper)) or lower > upper:
            raise OracleRefused(OracleRefusal.INSUFFICIENT_SUPPORT, "invalid bounds")
        return cls(
            OracleOutcomeKind.PARTIALLY_IDENTIFIED, authority, lower_bound=lower, upper_bound=upper
        )

    @classmethod
    def model_derived(
        cls,
        point: float | None,
        lower: float | None,
        upper: float | None,
        authority: CounterfactualAuthority,
    ) -> OracleOutcome:
        if authority.identifiability_status is not Identifiability.MODEL_DERIVED:
            raise OracleRefused(OracleRefusal.INSUFFICIENT_SUPPORT, "authority is not model-derived")
        return cls(
            OracleOutcomeKind.MODEL_DERIVED,
            authority,
            point_estimate=point,
            lower_bound=lower,
            upper_bound=upper,
        )

    @classmethod
    def unknown(
        cls, refusal: OracleRefusal, authority: CounterfactualAuthority
    ) -> OracleOutcome:
        return cls(OracleOutcomeKind.UNKNOWN, authority, refusal=refusal)

    # -- read side --------------------------------------------------------------------

    def is_unknown(self) -> bool:
        return self.kind is OracleOutcomeKind.UNKNOWN

    def is_identified(self) -> bool:
        return self.kind is OracleOutcomeKind.IDENTIFIED

    def bounds(self) -> tuple[float, float] | None:
        if self.lower_bound is None or self.upper_bound is None:
            return None
        return (self.lower_bound, self.upper_bound)

    def refusal_reason(self) -> OracleRefusal | None:
        return self.refusal

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "point_estimate": self.point_estimate,
            "bounds": None if self.bounds() is None else list(self.bounds() or ()),
            "refusal": None if self.refusal is None else self.refusal.value,
            "authority": self.authority.as_dict(),
            "supporting_evidence": self.supporting_evidence,
            "note": (
                "an UNKNOWN outcome carries a typed refusal; it is never a zero point estimate"
                if self.is_unknown()
                else None
            ),
        }
