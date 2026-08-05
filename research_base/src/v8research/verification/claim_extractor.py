"""Pass A: atomic claim discovery.

Extracts the smallest independently supportable/rejectable claims from a mark
or a directly-read node. Does not map to V8 -- that happens only after
Pass C verification produces immutable findings.
"""

from __future__ import annotations

from ..contracts.claim import Claim
from ..contracts.enums import EpistemicAct, Modality, ReadPurpose
from ..contracts.structure import DocumentNode
from ..ids import range_hash, sha256_hex
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore
from .prompts_ref import CLAIM_EXTRACTION_SYSTEM, PROMPT_VERSIONS

_VALID_ACTS = {a.value for a in EpistemicAct}
_VALID_MODALITY = {m.value for m in Modality}


def extract_claims(
    node: DocumentNode,
    text: str,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
    origin_mark_ids: list[str] | None = None,
) -> list[Claim]:
    range_key = range_hash(text)
    question_hash = sha256_hex("claim_extraction")
    prompt_version = PROMPT_VERSIONS["claim_extraction"]
    cached = receipts.find_cached(
        [range_key], ReadPurpose.MARKING, question_hash, prompt_version, client.model_id
    )
    if cached is None:
        response = client.complete(CLAIM_EXTRACTION_SYSTEM, f"<<<TEXT>>>\n{text}")
        cached = receipts.record(
            source_range_hashes=[range_key],
            structural_node_ids=[node.node_id],
            purpose=ReadPurpose.MARKING,
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
        payload = store.cache.get(cached.read_receipt_id) or {"claims": []}

    claims = []
    for entry in payload.get("claims", []):
        statement = entry.get("source_statement", "")
        if not statement:
            continue
        act = entry.get("epistemic_act", "OBSERVED")
        modality = entry.get("modality", "USUALLY")
        claims.append(
            Claim(
                claim_id=Claim.make_id(node.node_id, entry.get("normalized_claim", statement)),
                source_id=node.source_id,
                node_id=node.node_id,
                source_statement=statement,
                normalized_claim=entry.get("normalized_claim", statement),
                epistemic_act=EpistemicAct(act if act in _VALID_ACTS else "OBSERVED"),
                modality=Modality(modality if modality in _VALID_MODALITY else "USUALLY"),
                population_scope=entry.get("population_scope"),
                conditions=entry.get("conditions", []),
                exceptions=entry.get("exceptions", []),
                origin_mark_ids=origin_mark_ids or [],
                read_receipt_id=cached.read_receipt_id,
            )
        )
    return claims
