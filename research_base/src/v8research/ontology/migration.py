"""Ontology schema migrations.

Constitution rule 12: migrations are bitemporal and reproducible. Every
structural change to the concept graph is logged as a SchemaChange so a
migration can be replayed or audited, and cheap executable test #5 ("changing
the ontology does not change immutable finding hashes") is checkable by
construction: this module never touches Finding records.
"""

from __future__ import annotations

from ..contracts.enums import OntologyOperation
from ..contracts.ontology import Concept, SchemaChange


def merge_concepts(
    survivor: Concept, absorbed: list[Concept], to_version: int, rationale: str
) -> tuple[Concept, SchemaChange]:
    merged = Concept(
        concept_id=survivor.concept_id,
        name=survivor.name,
        definition=survivor.definition,
        ontology_version=to_version,
        is_source_term=survivor.is_source_term,
        nearest_concept_ids=survivor.nearest_concept_ids,
        supporting_finding_ids=sorted(
            set(survivor.supporting_finding_ids)
            | {fid for c in absorbed for fid in c.supporting_finding_ids}
        ),
        counterexample_finding_ids=sorted(
            set(survivor.counterexample_finding_ids)
            | {fid for c in absorbed for fid in c.counterexample_finding_ids}
        ),
    )
    change = SchemaChange(
        change_id=SchemaChange.make_id(
            OntologyOperation.MERGE_CONCEPTS, survivor.ontology_version, to_version
        ),
        operation=OntologyOperation.MERGE_CONCEPTS,
        from_version=survivor.ontology_version,
        to_version=to_version,
        affected_concept_ids=[survivor.concept_id, *(c.concept_id for c in absorbed)],
        rationale=rationale,
        automated=False,
    )
    return merged, change


def split_concept(
    original: Concept,
    into: list[tuple[str, str, list[str]]],
    to_version: int,
    rationale: str,
) -> tuple[list[Concept], SchemaChange]:
    """`into` is (name, definition, supporting_finding_ids) per new concept."""
    new_concepts = [
        Concept(
            concept_id=Concept.make_id(name),
            name=name,
            definition=definition,
            ontology_version=to_version,
            supporting_finding_ids=finding_ids,
            nearest_concept_ids=[original.concept_id],
        )
        for name, definition, finding_ids in into
    ]
    change = SchemaChange(
        change_id=SchemaChange.make_id(
            OntologyOperation.SPLIT_CONCEPT, original.ontology_version, to_version
        ),
        operation=OntologyOperation.SPLIT_CONCEPT,
        from_version=original.ontology_version,
        to_version=to_version,
        affected_concept_ids=[original.concept_id, *(c.concept_id for c in new_concepts)],
        rationale=rationale,
        automated=False,
    )
    return new_concepts, change


def deprecate_concept(concept: Concept, to_version: int, rationale: str) -> tuple[Concept, SchemaChange]:
    deprecated = Concept(
        concept_id=concept.concept_id,
        name=concept.name,
        definition=concept.definition,
        ontology_version=to_version,
        is_source_term=concept.is_source_term,
        nearest_concept_ids=concept.nearest_concept_ids,
        supporting_finding_ids=concept.supporting_finding_ids,
        counterexample_finding_ids=concept.counterexample_finding_ids,
        deprecated=True,
    )
    change = SchemaChange(
        change_id=SchemaChange.make_id(
            OntologyOperation.DEPRECATE_CONCEPT, concept.ontology_version, to_version
        ),
        operation=OntologyOperation.DEPRECATE_CONCEPT,
        from_version=concept.ontology_version,
        to_version=to_version,
        affected_concept_ids=[concept.concept_id],
        rationale=rationale,
        automated=False,
    )
    return deprecated, change
