"""Channel B: chapter-level independent synthesis.

Not a concatenation of section summaries -- a separate read of the whole
chapter, so distributed arguments and later qualifications become visible.
The set difference against unioned section findings is the empirical
diagnostic of section-level recall limits (spec: "Chapter-level control").
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.enums import DiscoveryChannel, ReadPurpose
from ..contracts.mark import Mark
from ..contracts.structure import DocumentNode
from ..ids import derive_id, range_hash, sha256_hex
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore
from .prompts import CHAPTER_SYNTHESIS_SYSTEM, PROMPT_VERSIONS


@dataclass
class ChapterSynthesis:
    chapter_id: str
    chapter_findings: list[str]
    incomplete_sections: list[str]
    argument_summary: str
    read_receipt_id: str


def synthesize_chapter(
    chapter: DocumentNode,
    full_text: str,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
) -> ChapterSynthesis:
    range_key = range_hash(full_text)
    question_hash = sha256_hex("chapter_synthesis")
    prompt_version = PROMPT_VERSIONS["chapter_synthesis"]
    cached = receipts.find_cached(
        [range_key], ReadPurpose.MARKING, question_hash, prompt_version, client.model_id
    )
    if cached is None:
        response = client.complete(CHAPTER_SYNTHESIS_SYSTEM, f"<<<TEXT>>>\n{full_text}")
        cached = receipts.record(
            source_range_hashes=[range_key],
            structural_node_ids=[chapter.node_id],
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
        payload = store.cache.get(cached.read_receipt_id) or {}

    return ChapterSynthesis(
        chapter_id=chapter.node_id,
        chapter_findings=payload.get("chapter_findings", []),
        incomplete_sections=payload.get("incomplete_sections", []),
        argument_summary=payload.get("argument_summary", ""),
        read_receipt_id=cached.read_receipt_id,
    )


def chapter_findings_as_marks(synthesis: ChapterSynthesis, source_id: str) -> list[Mark]:
    marks = []
    for finding in synthesis.chapter_findings:
        marks.append(
            Mark(
                mark_id=derive_id("MARK", synthesis.chapter_id, finding, "chapter"),
                node_id=synthesis.chapter_id,
                source_id=source_id,
                span_refs=[],
                verbatim_anchor=finding,
                why_marked="Chapter-scale argument not visible at section granularity.",
                open_codes=[],
                discovery_channels=[DiscoveryChannel.CHAPTER_SYNTHESIS],
                read_receipt_id=synthesis.read_receipt_id,
            )
        )
    return marks


def recall_gap(chapter_finding_texts: list[str], section_mark_anchors: list[str]) -> dict:
    """spec: chapter_findings - union(section_findings), and the inverse.

    A crude containment check (substring match), sufficient as a diagnostic
    signal for whether the chapter channel is finding anything the section
    channel missed -- exact semantic matching is not the point here.
    """
    section_blob = " ".join(section_mark_anchors).lower()
    chapter_only = [f for f in chapter_finding_texts if f.lower()[:40] not in section_blob]
    return {
        "chapter_only_count": len(chapter_only),
        "chapter_only": chapter_only,
        "total_chapter_findings": len(chapter_finding_texts),
    }
