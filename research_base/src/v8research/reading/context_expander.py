"""Resolve a ReadMode into the exact set of nodes to present.

DeepRead's lesson lives here: marks point to structural coordinates, and
expansion supports contiguous, order-preserving reading rather than retrieving
isolated fragments without the local argument that qualifies them.
"""

from __future__ import annotations

from ..contracts.enums import ReadMode
from ..contracts.structure import DocumentNode


def expand(
    nodes_by_id: dict[str, DocumentNode],
    target_node_ids: list[str],
    mode: ReadMode,
    context_before: int = 1,
    context_after: int = 1,
) -> list[str]:
    """Return an ordered, deduplicated list of node ids to read together."""
    if mode == ReadMode.SPAN_ONLY:
        return list(dict.fromkeys(target_node_ids))

    if mode == ReadMode.LOCAL_WINDOW:
        result: list[str] = []
        for node_id in target_node_ids:
            result.extend(_window(nodes_by_id, node_id, context_before, context_after))
        return list(dict.fromkeys(result))

    if mode == ReadMode.CONTIGUOUS_SECTION:
        result = []
        for node_id in target_node_ids:
            result.extend(_contiguous_run(nodes_by_id, node_id))
        return list(dict.fromkeys(result))

    if mode == ReadMode.MULTI_SECTION:
        # Preserve document order across possibly distant sections.
        return sorted(
            dict.fromkeys(target_node_ids),
            key=lambda nid: nodes_by_id[nid].order if nid in nodes_by_id else 0,
        )

    if mode == ReadMode.CHAPTER_READ:
        result = []
        for node_id in target_node_ids:
            result.extend(_chapter_of(nodes_by_id, node_id))
        return list(dict.fromkeys(result))

    if mode == ReadMode.CROSS_SOURCE:
        return sorted(
            dict.fromkeys(target_node_ids),
            key=lambda nid: (
                nodes_by_id[nid].source_id if nid in nodes_by_id else "",
                nodes_by_id[nid].order if nid in nodes_by_id else 0,
            ),
        )

    if mode == ReadMode.FIGURE_TABLE_READ:
        return list(dict.fromkeys(target_node_ids))

    return list(dict.fromkeys(target_node_ids))


def _window(
    nodes_by_id: dict[str, DocumentNode], node_id: str, before: int, after: int
) -> list[str]:
    node = nodes_by_id.get(node_id)
    if node is None:
        return [node_id]
    chain = [node_id]
    cursor = node
    for _ in range(before):
        if not cursor.prev_node_id:
            break
        cursor = nodes_by_id.get(cursor.prev_node_id)
        if cursor is None:
            break
        chain.insert(0, cursor.node_id)
    cursor = node
    for _ in range(after):
        if not cursor.next_node_id:
            break
        cursor = nodes_by_id.get(cursor.next_node_id)
        if cursor is None:
            break
        chain.append(cursor.node_id)
    return chain


def _contiguous_run(nodes_by_id: dict[str, DocumentNode], node_id: str) -> list[str]:
    """The full run of sibling sections under the same parent chapter."""
    node = nodes_by_id.get(node_id)
    if node is None or node.parent_id is None:
        return [node_id]
    parent = nodes_by_id.get(node.parent_id)
    if parent is None:
        return [node_id]
    return [nid for nid in parent.ordered_child_ids if nid in nodes_by_id] or [node_id]


def _chapter_of(nodes_by_id: dict[str, DocumentNode], node_id: str) -> list[str]:
    node = nodes_by_id.get(node_id)
    if node is None:
        return [node_id]
    chapter_id = node.parent_id or node_id
    chapter = nodes_by_id.get(chapter_id)
    if chapter is None:
        return [node_id]
    return [chapter_id] + [nid for nid in chapter.ordered_child_ids if nid in nodes_by_id]
