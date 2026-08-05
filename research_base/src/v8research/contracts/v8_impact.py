"""V8 assumption registry and impact mapping.

Only verified findings reach this layer, and the mapper must be able to answer
NO_IMPACT. A system that finds a V8 use for every finding has stopped doing
research and started confirming itself.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import AssumptionStatus, ImpactRelation, ProposalKind


@dataclasses.dataclass
class V8Assumption(Record):
    KIND: ClassVar[str] = "v8_assumption"

    assumption_id: str
    statement: str
    status: AssumptionStatus
    component_ids: list[str] = dataclasses.field(default_factory=list)
    supporting_finding_ids: list[str] = dataclasses.field(default_factory=list)
    challenging_finding_ids: list[str] = dataclasses.field(default_factory=list)
    narrowing_finding_ids: list[str] = dataclasses.field(default_factory=list)
    missing_variable_finding_ids: list[str] = dataclasses.field(default_factory=list)
    untested_interaction_finding_ids: list[str] = dataclasses.field(default_factory=list)
    last_reviewed_ontology_version: int = 0

    @staticmethod
    def make_id(statement: str) -> str:
        return derive_id("V8-A", statement)


@dataclasses.dataclass
class V8Impact(Record):
    KIND: ClassVar[str] = "v8_impact"

    impact_id: str
    finding_id: str
    assumption_id: str
    relation: ImpactRelation
    rationale: str = ""
    confidence: float = 0.0
    mapped_by_model_id: str = ""
    ontology_version: str = ""

    @staticmethod
    def make_id(finding_id: str, assumption_id: str, relation: str) -> str:
        return derive_id("IMP", finding_id, assumption_id, relation)


@dataclasses.dataclass
class ResearchProposal(Record):
    KIND: ClassVar[str] = "research_proposal"

    proposal_id: str
    kind: ProposalKind
    title: str
    body: str
    supporting_finding_ids: list[str] = dataclasses.field(default_factory=list)
    related_assumption_ids: list[str] = dataclasses.field(default_factory=list)
    falsifiable_prediction: str = ""
    required_observables: list[str] = dataclasses.field(default_factory=list)
    status: str = "DRAFT"

    @staticmethod
    def make_id(kind: str, title: str) -> str:
        return derive_id("PROP", kind, title)
