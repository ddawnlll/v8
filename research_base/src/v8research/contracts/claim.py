"""Claims and their verification.

A source statement, a model interpretation, a V8 implication and an economic
claim are separate objects (constitution rule 5). This module owns only the
first two.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import EpistemicAct, EvidenceLabel, Modality


@dataclasses.dataclass
class Claim(Record):
    KIND: ClassVar[str] = "claim"

    claim_id: str
    source_id: str
    node_id: str
    source_statement: str
    normalized_claim: str
    epistemic_act: EpistemicAct
    modality: Modality
    evidence_span_ids: list[str] = dataclasses.field(default_factory=list)
    population_scope: str | None = None
    market_scope: str | None = None
    time_scope: str | None = None
    conditions: list[str] = dataclasses.field(default_factory=list)
    exceptions: list[str] = dataclasses.field(default_factory=list)
    evidence_label: EvidenceLabel = EvidenceLabel.MODEL_INTERPRETATION
    origin_mark_ids: list[str] = dataclasses.field(default_factory=list)
    read_receipt_id: str | None = None
    is_primary: bool = True

    @staticmethod
    def make_id(node_id: str, normalized_claim: str) -> str:
        return derive_id("CLM", node_id, normalized_claim)


@dataclasses.dataclass
class Verification(Record):
    KIND: ClassVar[str] = "verification"

    verification_id: str
    claim_id: str
    entailed: bool
    modality_preserved: bool
    scope_supported: bool
    conditions_complete: bool
    verdict: EvidenceLabel
    verifier_model_id: str
    verifier_notes: str = ""
    requires_reread: bool = False
    reread_reason: str | None = None
    read_receipt_id: str | None = None

    @property
    def passed(self) -> bool:
        return (
            self.entailed
            and self.modality_preserved
            and self.scope_supported
            and self.conditions_complete
            and not self.requires_reread
        )

    @staticmethod
    def make_id(claim_id: str, verifier_model_id: str) -> str:
        return derive_id("VER", claim_id, verifier_model_id)
