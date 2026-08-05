"""Pass C: independent verification.

The verifier sees only the claim, the exact evidence, and local structure --
never the extractor's reasoning or persuasive narrative (verifier
independence). Where possible the verifier is drawn from a different model
tier than the extractor, so their errors are not perfectly correlated.
"""

from __future__ import annotations

from ..contracts.claim import Claim, Verification
from ..contracts.enums import EvidenceLabel, ReadPurpose
from ..contracts.structure import DocumentNode, EvidenceSpan
from ..ids import range_hash, sha256_hex
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore
from .modality import modality_preserved
from .prompts_ref import PROMPT_VERSIONS, VERIFICATION_SYSTEM


def verify_claim(
    claim: Claim,
    span: EvidenceSpan | None,
    node: DocumentNode,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
) -> Verification:
    if span is None:
        return Verification(
            verification_id=Verification.make_id(claim.claim_id, client.model_id),
            claim_id=claim.claim_id,
            entailed=False,
            modality_preserved=False,
            scope_supported=False,
            conditions_complete=False,
            verdict=EvidenceLabel.REJECTED_EXTRACTION,
            verifier_model_id=client.model_id,
            verifier_notes="no evidence span located; claim not entailed by construction",
        )

    evidence_text = span.verbatim_text
    prompt_input = f"<<<CLAIM>>>\n{claim.normalized_claim}\n<<<EVIDENCE>>>\n{evidence_text}"
    range_key = range_hash(evidence_text)
    question_hash = sha256_hex(f"verify:{claim.claim_id}")
    prompt_version = PROMPT_VERSIONS["verification"]

    cached = receipts.find_cached(
        [range_key], ReadPurpose.VERIFICATION, question_hash, prompt_version, client.model_id
    )
    if cached is None:
        response = client.complete(VERIFICATION_SYSTEM, prompt_input)
        cached = receipts.record(
            source_range_hashes=[range_key],
            structural_node_ids=[node.node_id],
            purpose=ReadPurpose.VERIFICATION,
            question_hash=question_hash,
            prompt_version=prompt_version,
            model_id=client.model_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cache_hit=False,
            run_id=run_id,
        )
        payload = response.json()
        store.cache.put(cached.read_receipt_id, payload)
    else:
        payload = store.cache.get(cached.read_receipt_id) or {}

    entailed = bool(payload.get("entailed", False))
    model_says_modality_ok = bool(payload.get("modality_preserved", False))
    # The deterministic modality ceiling always wins over the model's opinion:
    # this is what makes "reject a claim whose modality exceeds its evidence"
    # a guarantee rather than a suggestion.
    modality_ok = model_says_modality_ok and modality_preserved(claim.modality, evidence_text)
    scope_ok = bool(payload.get("scope_supported", False))
    conditions_ok = bool(payload.get("conditions_complete", False))
    requires_reread = bool(payload.get("requires_reread", not entailed))

    if entailed and modality_ok and scope_ok and conditions_ok:
        verdict = EvidenceLabel.VERIFIED_ENTAILMENT
    elif not entailed:
        verdict = EvidenceLabel.REJECTED_EXTRACTION
    else:
        verdict = EvidenceLabel.OPEN_QUESTION

    return Verification(
        verification_id=Verification.make_id(claim.claim_id, client.model_id),
        claim_id=claim.claim_id,
        entailed=entailed,
        modality_preserved=modality_ok,
        scope_supported=scope_ok,
        conditions_complete=conditions_ok,
        verdict=verdict,
        verifier_model_id=client.model_id,
        verifier_notes=payload.get("notes", ""),
        requires_reread=requires_reread and verdict != EvidenceLabel.VERIFIED_ENTAILMENT,
        reread_reason="VERIFIER_SCOPE_FAILURE" if requires_reread else None,
        read_receipt_id=cached.read_receipt_id,
    )
