"""Dynamic research ontology: concepts, proposals, bitemporal annotations.

A split or merge never rewrites old annotations. It closes their validity
interval and creates new ones, so "how did we read this finding under ontology
v17" stays answerable forever.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import OntologyOperation


@dataclasses.dataclass
class Concept(Record):
    KIND: ClassVar[str] = "concept"

    concept_id: str
    name: str
    definition: str
    ontology_version: int
    is_source_term: bool = False
    nearest_concept_ids: list[str] = dataclasses.field(default_factory=list)
    supporting_finding_ids: list[str] = dataclasses.field(default_factory=list)
    counterexample_finding_ids: list[str] = dataclasses.field(default_factory=list)
    deprecated: bool = False

    @staticmethod
    def make_id(name: str) -> str:
        return derive_id("CON", name)


@dataclasses.dataclass
class ConceptProposal(Record):
    KIND: ClassVar[str] = "concept_proposal"

    proposal_id: str
    operation: OntologyOperation
    proposed_name: str
    definition: str
    why_existing_schema_is_insufficient: str
    lexical_novelty: float = 0.0
    semantic_novelty: float = 0.0
    decision_novelty: float = 0.0
    observable_novelty: float = 0.0
    relation_novelty: float = 0.0
    architecture_novelty: float = 0.0
    supporting_finding_ids: list[str] = dataclasses.field(default_factory=list)
    counterexample_finding_ids: list[str] = dataclasses.field(default_factory=list)
    nearest_concept_ids: list[str] = dataclasses.field(default_factory=list)
    target_concept_ids: list[str] = dataclasses.field(default_factory=list)
    is_source_term: bool = False
    status: str = "PROPOSED"

    @staticmethod
    def make_id(operation: str, proposed_name: str) -> str:
        return derive_id("ONTO-PROP", operation, proposed_name)


@dataclasses.dataclass
class OntologyAnnotation(Record):
    KIND: ClassVar[str] = "ontology_annotation"

    annotation_id: str
    finding_id: str
    ontology_version: str
    concept_ids: list[str] = dataclasses.field(default_factory=list)
    relation_assertions: list[dict] = dataclasses.field(default_factory=list)
    valid_from_schema_version: int = 1
    valid_to_schema_version: int | None = None
    asserted_at: str = ""
    superseded_by: str | None = None
    migration_confidence: float = 1.0
    annotation_provenance: str = "MODEL_PROPOSED"

    @property
    def is_open(self) -> bool:
        return self.valid_to_schema_version is None

    @staticmethod
    def make_id(finding_id: str, ontology_version: str) -> str:
        return derive_id("ANN", finding_id, ontology_version)


@dataclasses.dataclass
class SchemaChange(Record):
    KIND: ClassVar[str] = "schema_change"

    change_id: str
    operation: OntologyOperation
    from_version: int
    to_version: int
    affected_concept_ids: list[str] = dataclasses.field(default_factory=list)
    rationale: str = ""
    automated: bool = False

    @staticmethod
    def make_id(operation: str, from_version: int, to_version: int) -> str:
        return derive_id("SCHEMA", operation, from_version, to_version)
