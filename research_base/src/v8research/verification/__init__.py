"""Claim extraction, evidence alignment, and independent verification."""

from .claim_extractor import extract_claims
from .entailment import verify_claim
from .evidence_aligner import align_evidence, locate_span
from .modality import evidence_modality_ceiling, modality_preserved
from .source_independence import materialize_finding, source_independence_score, verification_quality

__all__ = [
    "align_evidence",
    "evidence_modality_ceiling",
    "extract_claims",
    "locate_span",
    "materialize_finding",
    "modality_preserved",
    "source_independence_score",
    "verification_quality",
    "verify_claim",
]
