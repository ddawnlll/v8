"""Bounded reread execution and terminal task accounting."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.enums import TaskStatus
from ..contracts.reread import RereadTask
from ..contracts.structure import DocumentNode
from ..llm.base import LLMClient
from ..store.store import ResearchStore
from ..discovery.prompts import REREAD_SYSTEM
from .reader import read_task
from .receipts import ReceiptLog

TERMINAL_STATUSES = frozenset(
    {
        TaskStatus.RESOLVED,
        TaskStatus.PARTIALLY_RESOLVED,
        TaskStatus.UNRESOLVABLE_IN_SOURCE,
        TaskStatus.REQUIRES_EXTERNAL_SOURCE,
        TaskStatus.DUPLICATE_QUESTION,
        TaskStatus.ABANDONED_LOW_VALUE,
        TaskStatus.FAILED,
    }
)


@dataclass(frozen=True)
class RereadExecutionReport:
    attempted: int
    resolved: int
    terminal_unresolved: int
    pending: int
    cache_hits: int


def execute_rereads(
    tasks: list[RereadTask],
    *,
    nodes_by_id: dict[str, DocumentNode],
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
    max_output_tokens: int = 1024,
) -> RereadExecutionReport:
    attempted = resolved = terminal_unresolved = pending = cache_hits = 0
    for task in tasks:
        if task.status in TERMINAL_STATUSES:
            continue
        if len(task.attempts) >= task.max_attempts:
            task.status = TaskStatus.FAILED
            terminal_unresolved += 1
            store.append(task)
            continue
        task.status = TaskStatus.IN_PROGRESS
        result = read_task(
            task,
            nodes_by_id=nodes_by_id,
            store=store,
            receipts=receipts,
            client=client,
            system_prompt=REREAD_SYSTEM,
            prompt_version="reread-v1",
            run_id=run_id,
            max_output_tokens=max_output_tokens,
        )
        attempted += 1
        cache_hits += int(result.cache_hit)
        payload = result.response.json() if result.response is not None else {}
        raw_status = str(payload.get("status", "FAILED"))
        try:
            status = TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.FAILED
        note = str(payload.get("note", payload.get("answer", "")))[:1000]
        task.record_attempt(result.receipt_id, status == TaskStatus.RESOLVED, note, status)
        if status == TaskStatus.RESOLVED:
            resolved += 1
        elif status in TERMINAL_STATUSES:
            terminal_unresolved += 1
        else:
            task.status = TaskStatus.OPEN
            pending += 1
        store.append(task)
    pending += sum(1 for task in tasks if task.status in {TaskStatus.OPEN, TaskStatus.IN_PROGRESS})
    return RereadExecutionReport(attempted, resolved, terminal_unresolved, pending, cache_hits)
