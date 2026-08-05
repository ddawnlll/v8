"""Channel E: citation and cross-reference composition.

Follows "as discussed in Chapter 3", figure references, and repeated examples
into multi-span reconstruction tasks -- this channel proposes RereadTasks
rather than producing marks directly, because a cross-reference is by
definition a claim that spans more than one node.
"""

from __future__ import annotations

from ..contracts.enums import ReadMode, RereadTrigger
from ..contracts.reread import RereadTask
from ..contracts.structure import DocumentNode


def _resolve_target(nodes_by_heading: dict[str, str], reference: str) -> str | None:
    """Best-effort match of a reference string ('chapter:3') to a node id."""
    _, _, value = reference.partition(":")
    for heading_key, node_id in nodes_by_heading.items():
        if value and value in heading_key:
            return node_id
    return None


def build_heading_index(nodes: list[DocumentNode]) -> dict[str, str]:
    index: dict[str, str] = {}
    for node in nodes:
        for heading in node.heading_path:
            index[heading.lower()] = node.node_id
    return index


def cross_reference_tasks(
    nodes: list[DocumentNode], created_by_run: str = ""
) -> list[RereadTask]:
    heading_index = build_heading_index(nodes)
    tasks: list[RereadTask] = []
    for node in nodes:
        refs = node.cross_reference_targets + node.figure_table_refs
        if not refs:
            continue
        targets = [node.node_id]
        for ref in refs:
            resolved = _resolve_target(heading_index, ref)
            if resolved and resolved != node.node_id:
                targets.append(resolved)
        if len(targets) < 2:
            continue
        is_figure = any(r.startswith(("figure:", "table:")) for r in refs)
        reason = RereadTrigger.TABLE_OR_FIGURE_REQUIRED if is_figure else RereadTrigger.CROSS_SECTION_DEPENDENCY
        question = f"Does the referenced content ({', '.join(refs)}) qualify or complete this passage?"
        tasks.append(
            RereadTask(
                reread_id=RereadTask.make_id(targets, reason, question),
                origin_mark_ids=[],
                reason_code=reason,
                target_node_ids=targets,
                question=question,
                required_resolution="Reconstruct the composed claim or mark it unresolved.",
                preferred_read_mode=(
                    ReadMode.FIGURE_TABLE_READ if is_figure else ReadMode.MULTI_SECTION
                ),
                priority_basis=["COMPOSITION_DISCOVERY"],
                created_by_run=created_by_run,
            )
        )
    return tasks
