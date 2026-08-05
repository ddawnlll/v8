"""map_document / mark_node / plan_rereads glue: the minimum interfaces.

This module is the only place that sequences ingest -> discovery -> reading
end to end for a single source. The orchestrator (a future CLI/workflow layer)
calls these functions; it never inlines their logic, so the pipeline stays
testable stage by stage.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.enums import NodeType
from ..contracts.navigation import NavigationMemory
from ..contracts.source import Source
from ..contracts.structure import DocumentNode
from ..discovery.section_worker import mark_section, navigate_node
from ..ingest.parse import parse
from ..ingest.structure import build_nodes
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore


@dataclass
class MapResult:
    source: Source
    nodes: list[DocumentNode]
    navigations: list[NavigationMemory]


def map_document(
    source: Source,
    file_path: str,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
    navigate: bool = True,
) -> MapResult:
    from pathlib import Path

    document = parse(Path(file_path))
    if not document.parse_ok:
        raise RuntimeError(f"parse failed for {source.source_id}: {document.parse_error}")

    nodes, texts = build_nodes(source.source_id, document.text_sha256, document)
    store.append(source)
    for node in nodes:
        store.append(node)
        store.put_text(node.node_id, texts[node.node_id])

    navigations: list[NavigationMemory] = []
    if navigate:
        for node in nodes:
            if node.node_type != NodeType.SECTION:
                continue
            nav = navigate_node(
                node, texts[node.node_id], store=store, receipts=receipts, client=client, run_id=run_id
            )
            store.append(nav)
            navigations.append(nav)

    return MapResult(source, nodes, navigations)


def mark_node(
    node: DocumentNode,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
):
    text = store.get_text(node.node_id)
    marks = mark_section(node, text, store=store, receipts=receipts, client=client, run_id=run_id)
    for mark in marks:
        store.append(mark)
    return marks
