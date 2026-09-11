"""Controlled Oracle — Python port of v8-core/src/oracle (TARGET_ORACLE_SPEC §2, §8, §16).

Ported so the two systems share one vocabulary for counterfactuals: the four orthogonal
authority dimensions, the canonical fail-closed refusal codes, and the outcome type where
UNKNOWN is first-class and never collapses to a zero point estimate.
"""

from v8_next.oracle.authority import (
    CounterfactualAuthority,
    OracleOutcome,
    OracleOutcomeKind,
)
from v8_next.oracle.taxonomy import (
    AuditState,
    AuthorityError,
    AuthorityLevel,
    EconomicEvidenceStage,
    Identifiability,
    OracleContext,
    OracleRefusal,
    OracleRole,
    StatisticalVerdict,
    UnknownReasonCode,
    ValueNotion,
    VerificationDimension,
)
from v8_next.oracle.taxonomy import (
    CounterfactualAuthority as CounterfactualAuthorityLevel,
)

__all__ = [
    "AuditState",
    "AuthorityError",
    "AuthorityLevel",
    "CounterfactualAuthority",
    "CounterfactualAuthorityLevel",
    "EconomicEvidenceStage",
    "Identifiability",
    "OracleContext",
    "OracleOutcome",
    "OracleOutcomeKind",
    "OracleRefusal",
    "OracleRole",
    "StatisticalVerdict",
    "UnknownReasonCode",
    "ValueNotion",
    "VerificationDimension",
]
