"""Dynamic research ontology: induction, bitemporal annotation, migration."""

from .annotations import annotate, close_and_supersede
from .induction import approve_concept, propose_concept, requires_merge_review
from .migration import deprecate_concept, merge_concepts, split_concept

__all__ = [
    "annotate",
    "approve_concept",
    "close_and_supersede",
    "deprecate_concept",
    "merge_concepts",
    "propose_concept",
    "requires_merge_review",
    "split_concept",
]
