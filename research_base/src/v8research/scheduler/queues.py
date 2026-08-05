"""Named queues and typed task envelopes.

The scheduler operates on artifact metadata and dependency graphs, not on
full corpus text -- a queue item carries ids and a payload, never the source
text itself, so the orchestrator's own context stays small regardless of
corpus size.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any

from ..contracts.enums import PriorityClass, QueueName

_PRIORITY_ORDER: dict[PriorityClass, int] = {
    PriorityClass.CRITICAL: 0,
    PriorityClass.HIGH: 1,
    PriorityClass.NORMAL: 2,
    PriorityClass.AUDIT: 3,
    PriorityClass.BACKGROUND: 4,
}


@dataclass
class QueueItem:
    queue: QueueName
    priority: PriorityClass
    task_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    estimated_tokens: int = 0
    estimated_value: float = 0.0


@dataclass(order=True)
class _Entry:
    sort_key: tuple
    sequence: int
    item: QueueItem = field(compare=False)


class TaskQueue:
    """A priority queue with a protected minimum share for AUDIT items.

    Audit work receives protected capacity and cannot be starved by a
    high-priority flood (constitution rule / failure-mode table): every Nth
    dequeue, an AUDIT item is served ahead of the priority order if one is
    waiting, even under CRITICAL-queue pressure.
    """

    def __init__(self, audit_protect_every: int = 5) -> None:
        self._heap: list[_Entry] = []
        self._counter = itertools.count()
        self._dequeues = 0
        self.audit_protect_every = audit_protect_every

    def push(self, item: QueueItem) -> None:
        key = (_PRIORITY_ORDER[item.priority], -item.estimated_value)
        heapq.heappush(self._heap, _Entry(key, next(self._counter), item))

    def __len__(self) -> int:
        return len(self._heap)

    def pop(self) -> QueueItem | None:
        if not self._heap:
            return None
        self._dequeues += 1
        if self.audit_protect_every and self._dequeues % self.audit_protect_every == 0:
            audit_index = self._find_audit_index()
            if audit_index is not None:
                entry = self._heap.pop(audit_index)
                heapq.heapify(self._heap)
                return entry.item
        return heapq.heappop(self._heap).item

    def _find_audit_index(self) -> int | None:
        for index, entry in enumerate(self._heap):
            if entry.item.priority == PriorityClass.AUDIT:
                return index
        return None

    def peek_all(self) -> list[QueueItem]:
        return [entry.item for entry in self._heap]

    def counts_by_priority(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._heap:
            counts[entry.item.priority] = counts.get(entry.item.priority, 0) + 1
        return counts
