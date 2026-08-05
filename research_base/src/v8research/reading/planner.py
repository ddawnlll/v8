"""Reread planning: turn a mark's unresolved question into a typed task.

Rereading is not "spend more tokens on high-scoring text" -- every RereadTask
must carry a reason code from the fixed trigger vocabulary and a question that
names what would resolve it.
"""

from __future__ import annotations

from ..contracts.enums import ReadMode, RereadTrigger
from ..contracts.mark import Mark
from ..contracts.reread import RereadTask

#: Which read mode best answers each trigger, absent a more specific override.
DEFAULT_MODE_FOR_TRIGGER: dict[RereadTrigger, ReadMode] = {
    RereadTrigger.CONDITION_MISSING: ReadMode.LOCAL_WINDOW,
    RereadTrigger.DEFINITION_MISSING: ReadMode.LOCAL_WINDOW,
    RereadTrigger.CROSS_SECTION_DEPENDENCY: ReadMode.MULTI_SECTION,
    RereadTrigger.CHAPTER_ARGUMENT_INCOMPLETE: ReadMode.CHAPTER_READ,
    RereadTrigger.LATER_QUALIFICATION_POSSIBLE: ReadMode.CONTIGUOUS_SECTION,
    RereadTrigger.EXAMPLE_RULE_MISMATCH: ReadMode.CONTIGUOUS_SECTION,
    RereadTrigger.CONTRADICTION_UNRESOLVED: ReadMode.MULTI_SECTION,
    RereadTrigger.SOURCE_LINEAGE_UNCLEAR: ReadMode.CROSS_SOURCE,
    RereadTrigger.TABLE_OR_FIGURE_REQUIRED: ReadMode.FIGURE_TABLE_READ,
    RereadTrigger.VERIFIER_SCOPE_FAILURE: ReadMode.CONTIGUOUS_SECTION,
    RereadTrigger.MODALITY_UNCLEAR: ReadMode.LOCAL_WINDOW,
    RereadTrigger.V8_HIGH_IMPACT_REQUIRES_CONTEXT: ReadMode.CHAPTER_READ,
    RereadTrigger.RANDOM_AUDIT: ReadMode.SPAN_ONLY,
    RereadTrigger.HUMAN_REVIEW_REQUEST: ReadMode.CONTIGUOUS_SECTION,
}

#: Triggers that always count as CRITICAL for the completion gate.
CRITICAL_TRIGGERS = frozenset(
    {
        RereadTrigger.CONTRADICTION_UNRESOLVED,
        RereadTrigger.V8_HIGH_IMPACT_REQUIRES_CONTEXT,
        RereadTrigger.VERIFIER_SCOPE_FAILURE,
    }
)


def plan_reread(
    mark: Mark,
    reason_code: RereadTrigger,
    question: str,
    required_resolution: str,
    *,
    target_node_ids: list[str] | None = None,
    priority_basis: list[str] | None = None,
    created_by_run: str = "",
    estimated_tokens: int = 0,
) -> RereadTask:
    nodes = target_node_ids or [mark.node_id, *mark.cross_section_dependencies]
    return RereadTask(
        reread_id=RereadTask.make_id(nodes, reason_code, question),
        origin_mark_ids=[mark.mark_id],
        reason_code=reason_code,
        target_node_ids=nodes,
        question=question,
        required_resolution=required_resolution,
        preferred_read_mode=DEFAULT_MODE_FOR_TRIGGER.get(reason_code, ReadMode.CONTIGUOUS_SECTION),
        priority_basis=priority_basis or [],
        created_by_run=created_by_run,
        estimated_tokens=estimated_tokens,
        is_critical=reason_code in CRITICAL_TRIGGERS,
    )


def plan_from_unresolved_questions(
    mark: Mark, created_by_run: str = "", estimated_tokens: int = 0
) -> list[RereadTask]:
    """The common case: one mark's own unresolved_questions become tasks."""
    tasks = []
    for question in mark.unresolved_questions:
        trigger = (
            RereadTrigger.CROSS_SECTION_DEPENDENCY
            if mark.cross_section_dependencies
            else RereadTrigger.CONDITION_MISSING
        )
        tasks.append(
            plan_reread(
                mark,
                trigger,
                question,
                required_resolution="Extract an observable answer or mark the question as unresolved.",
                created_by_run=created_by_run,
                estimated_tokens=estimated_tokens,
            )
        )
    return tasks


def dedupe_tasks(tasks: list[RereadTask]) -> list[RereadTask]:
    """Two tasks with the same id are the same research action; merge origins."""
    by_id: dict[str, RereadTask] = {}
    for task in tasks:
        existing = by_id.get(task.reread_id)
        if existing is None:
            by_id[task.reread_id] = task
            continue
        for mark_id in task.origin_mark_ids:
            if mark_id not in existing.origin_mark_ids:
                existing.origin_mark_ids.append(mark_id)
    return list(by_id.values())
