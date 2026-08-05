"""Channel A: section-level open extraction, and the NAVIGATE stage.

Every eligible structural unit gets a navigation gist at least once. This
creates breadth but is explicitly not treated as a recall guarantee -- it is
the shallow first pass that later channels and the reread planner correct.
"""

from __future__ import annotations

from ..contracts.enums import DiscoveryChannel, ReadPurpose
from ..contracts.mark import Mark
from ..contracts.navigation import NavigationMemory
from ..contracts.structure import DocumentNode
from ..ids import range_hash, sha256_hex
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore
from .prompts import MARKING_SYSTEM, NAVIGATION_SYSTEM, PROMPT_VERSIONS


def navigate_node(
    node: DocumentNode,
    text: str,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
) -> NavigationMemory:
    range_key = range_hash(text)
    question_hash = sha256_hex("navigate")
    cached = receipts.find_cached(
        [range_key], ReadPurpose.NAVIGATION, question_hash, PROMPT_VERSIONS["navigation"], client.model_id
    )
    if cached is None:
        response = client.complete(NAVIGATION_SYSTEM, f"<<<TEXT>>>\n{text}")
        cached = receipts.record(
            source_range_hashes=[range_key],
            structural_node_ids=[node.node_id],
            purpose=ReadPurpose.NAVIGATION,
            question_hash=question_hash,
            prompt_version=PROMPT_VERSIONS["navigation"],
            model_id=client.model_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cache_hit=False,
            run_id=run_id,
        )
        payload = response.json()
    else:
        payload = store.cache.get(cached.read_receipt_id) or {}

    navigation = NavigationMemory(
        navigation_id=NavigationMemory.make_id(node.node_id),
        node_id=node.node_id,
        source_id=node.source_id,
        gist=payload.get("gist", ""),
        salient_terms_verbatim=payload.get("salient_terms_verbatim", []),
        named_entities=payload.get("named_entities", []),
        processes_observed=payload.get("processes_observed", []),
        examples_present=bool(payload.get("examples_present", False)),
        exceptions_present=bool(payload.get("exceptions_present", False)),
        tables_figures_present=bool(payload.get("tables_figures_present", False)),
        internal_references=payload.get("internal_references", []),
        navigation_uncertainties=payload.get("navigation_uncertainties", []),
        read_receipt_id=cached.read_receipt_id,
    )
    if not cached.cache_hit:
        store.cache.put(cached.read_receipt_id, payload)
    return navigation


def mark_section(
    node: DocumentNode,
    text: str,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
    channel: DiscoveryChannel = DiscoveryChannel.SECTION_LLM,
    system_prompt: str = MARKING_SYSTEM,
    prompt_version: str = PROMPT_VERSIONS["marking"],
) -> list[Mark]:
    """Channel A (and, with an override, channel G): open-coded marks for one node."""
    range_key = range_hash(text)
    question_hash = sha256_hex(f"mark:{channel}")
    cached = receipts.find_cached(
        [range_key], ReadPurpose.MARKING, question_hash, prompt_version, client.model_id
    )
    if cached is None:
        response = client.complete(system_prompt, f"<<<TEXT>>>\n{text}")
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
        payload = store.cache.get(cached.read_receipt_id) or {"marks": []}

    marks = []
    for entry in payload.get("marks", []):
        anchor = entry.get("verbatim_anchor", "")
        if not anchor:
            continue
        marks.append(
            Mark(
                mark_id=Mark.make_id(node.node_id, anchor),
                node_id=node.node_id,
                source_id=node.source_id,
                span_refs=[],
                verbatim_anchor=anchor,
                why_marked=entry.get("why_marked", ""),
                open_codes=entry.get("open_codes", []),
                conditions_seen=entry.get("conditions_seen", []),
                exceptions_seen=entry.get("exceptions_seen", []),
                cross_section_dependencies=entry.get("cross_section_dependencies", []),
                unresolved_questions=entry.get("unresolved_questions", []),
                discovery_channels=[channel],
                read_receipt_id=cached.read_receipt_id,
            )
        )
    return marks
