"""Bitemporal ontology annotations.

Under ontology version X, how did the research program interpret the finding?
An annotation is versioned; a Finding is not. Closing one annotation's
validity interval and opening a successor is the only permitted "edit".
"""

from __future__ import annotations

from ..contracts.finding import Finding
from ..contracts.ontology import OntologyAnnotation


def annotate(
    finding: Finding,
    concept_ids: list[str],
    ontology_version: str,
    schema_version: int,
    *,
    relation_assertions: list[dict] | None = None,
    provenance: str = "MODEL_PROPOSED",
    migration_confidence: float = 1.0,
    asserted_at: str = "",
) -> OntologyAnnotation:
    return OntologyAnnotation(
        annotation_id=OntologyAnnotation.make_id(finding.finding_id, ontology_version),
        finding_id=finding.finding_id,
        ontology_version=ontology_version,
        concept_ids=concept_ids,
        relation_assertions=relation_assertions or [],
        valid_from_schema_version=schema_version,
        valid_to_schema_version=None,
        asserted_at=asserted_at,
        migration_confidence=migration_confidence,
        annotation_provenance=provenance,
    )


def close_and_supersede(
    old: OntologyAnnotation,
    new_concept_ids: list[str],
    new_ontology_version: str,
    closing_schema_version: int,
    **kwargs,
) -> tuple[OntologyAnnotation, OntologyAnnotation]:
    """Split/merge never rewrites history: close `old`, create a successor.

    Returns (closed_old, new_annotation). The caller writes both -- the closed
    copy is a new record with `valid_to_schema_version` set, appended to the
    log rather than mutating the original in place.
    """
    if not old.is_open:
        raise ValueError(f"annotation {old.annotation_id} is already closed")
    closed = OntologyAnnotation(
        annotation_id=old.annotation_id,
        finding_id=old.finding_id,
        ontology_version=old.ontology_version,
        concept_ids=old.concept_ids,
        relation_assertions=old.relation_assertions,
        valid_from_schema_version=old.valid_from_schema_version,
        valid_to_schema_version=closing_schema_version,
        asserted_at=old.asserted_at,
        superseded_by=None,  # filled below once the successor id is known
        migration_confidence=old.migration_confidence,
        annotation_provenance=old.annotation_provenance,
    )
    successor = OntologyAnnotation(
        annotation_id=OntologyAnnotation.make_id(old.finding_id, new_ontology_version),
        finding_id=old.finding_id,
        ontology_version=new_ontology_version,
        concept_ids=new_concept_ids,
        valid_from_schema_version=closing_schema_version,
        **kwargs,
    )
    closed.superseded_by = successor.annotation_id
    return closed, successor
