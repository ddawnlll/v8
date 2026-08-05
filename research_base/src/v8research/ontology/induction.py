"""Open concept induction.

Clustering surfaces candidates but is never sufficient for admission. A
proposal must state what cannot be represented by existing concepts, or the
concept registry becomes synonym soup (failure mode: "Ontology produces
synonym explosion").
"""

from __future__ import annotations

from ..contracts.enums import OntologyOperation
from ..contracts.finding import Finding
from ..contracts.ontology import Concept, ConceptProposal


def propose_concept(
    proposed_name: str,
    definition: str,
    why_existing_schema_is_insufficient: str,
    *,
    supporting_findings: list[Finding],
    counterexample_findings: list[Finding] | None = None,
    nearest_concepts: list[Concept] | None = None,
    is_source_term: bool = False,
    lexical_novelty: float = 0.0,
    semantic_novelty: float = 0.0,
    decision_novelty: float = 0.0,
    observable_novelty: float = 0.0,
    relation_novelty: float = 0.0,
    architecture_novelty: float = 0.0,
) -> ConceptProposal:
    if not why_existing_schema_is_insufficient.strip():
        raise ValueError(
            "a concept proposal must explain why existing concepts cannot "
            "represent this finding"
        )
    return ConceptProposal(
        proposal_id=ConceptProposal.make_id(OntologyOperation.ADD_CONCEPT, proposed_name),
        operation=OntologyOperation.ADD_CONCEPT,
        proposed_name=proposed_name,
        definition=definition,
        why_existing_schema_is_insufficient=why_existing_schema_is_insufficient,
        lexical_novelty=lexical_novelty,
        semantic_novelty=semantic_novelty,
        decision_novelty=decision_novelty,
        observable_novelty=observable_novelty,
        relation_novelty=relation_novelty,
        architecture_novelty=architecture_novelty,
        supporting_finding_ids=[f.finding_id for f in supporting_findings],
        counterexample_finding_ids=[f.finding_id for f in (counterexample_findings or [])],
        nearest_concept_ids=[c.concept_id for c in (nearest_concepts or [])],
        is_source_term=is_source_term,
    )


#: Below this, a proposal is a duplicate rather than a new concept.
NOVELTY_ADMISSION_FLOOR = 0.3


def requires_merge_review(proposal: ConceptProposal) -> bool:
    """No single novelty score controls admission (spec), but a proposal that
    scores low on every dimension at once is almost certainly a duplicate and
    should be routed to merge review rather than silently admitted.
    """
    scores = [
        proposal.lexical_novelty,
        proposal.semantic_novelty,
        proposal.decision_novelty,
        proposal.observable_novelty,
        proposal.relation_novelty,
        proposal.architecture_novelty,
    ]
    return max(scores, default=0.0) < NOVELTY_ADMISSION_FLOOR


def approve_concept(proposal: ConceptProposal, ontology_version: int) -> Concept:
    return Concept(
        concept_id=Concept.make_id(proposal.proposed_name),
        name=proposal.proposed_name,
        definition=proposal.definition,
        ontology_version=ontology_version,
        is_source_term=proposal.is_source_term,
        nearest_concept_ids=proposal.nearest_concept_ids,
        supporting_finding_ids=proposal.supporting_finding_ids,
        counterexample_finding_ids=proposal.counterexample_finding_ids,
    )
