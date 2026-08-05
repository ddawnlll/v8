"""map_to_v8: the only function allowed to consume unverified-vs-verified state.

Only VERIFIED or PROVISIONAL findings with quality above the floor reach this
stage (guarded by `map_to_v8`, not by caller discipline). The mapper must
support NO_IMPACT as a first-class, expected answer -- a system that finds a
V8 use for every finding has stopped doing research.
"""

from __future__ import annotations

from ..contracts.enums import FindingStatus, ImpactRelation, ReadPurpose
from ..contracts.finding import Finding
from ..contracts.v8_impact import V8Assumption, V8Impact
from ..discovery.prompts import PROMPT_VERSIONS, V8_MAPPING_SYSTEM
from ..ids import sha256_hex
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore

_VALID_RELATIONS = {r.value for r in ImpactRelation}

MIN_QUALITY_FOR_MAPPING = 0.5


class UnverifiedFindingError(ValueError):
    pass


def map_to_v8(
    finding: Finding,
    assumption: V8Assumption,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
    ontology_version: str = "",
) -> V8Impact:
    if finding.status not in (FindingStatus.VERIFIED, FindingStatus.PROVISIONAL):
        raise UnverifiedFindingError(
            f"finding {finding.finding_id} is {finding.status}; only VERIFIED or "
            "PROVISIONAL findings may be mapped to V8"
        )
    if finding.verification_quality < MIN_QUALITY_FOR_MAPPING:
        raise UnverifiedFindingError(
            f"finding {finding.finding_id} verification_quality "
            f"{finding.verification_quality} is below the mapping floor"
        )

    prompt = (
        f"<<<FINDING>>>\n{finding.finding_statement}\n"
        f"<<<ASSUMPTION>>>\n{assumption.statement}"
    )
    question_hash = sha256_hex(f"v8map:{finding.finding_id}:{assumption.assumption_id}")
    prompt_version = PROMPT_VERSIONS["v8_mapping"]
    range_key = sha256_hex(prompt)

    cached = receipts.find_cached(
        [range_key], ReadPurpose.VERIFICATION, question_hash, prompt_version, client.model_id
    )
    if cached is None:
        response = client.complete(V8_MAPPING_SYSTEM, prompt)
        cached = receipts.record(
            source_range_hashes=[range_key],
            structural_node_ids=[],
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

    relation = payload.get("relation", "NO_IMPACT")
    if relation not in _VALID_RELATIONS:
        relation = "NO_IMPACT"

    return V8Impact(
        impact_id=V8Impact.make_id(finding.finding_id, assumption.assumption_id, relation),
        finding_id=finding.finding_id,
        assumption_id=assumption.assumption_id,
        relation=ImpactRelation(relation),
        rationale=payload.get("rationale", ""),
        confidence=float(payload.get("confidence", 0.0)),
        mapped_by_model_id=client.model_id,
        ontology_version=ontology_version,
    )
