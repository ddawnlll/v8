"""RereadTask: a typed research action, not "spend more tokens".

A reread exists to resolve one named uncertainty. The reason code is part of
the task identity, which is what lets the receipt log reject a repeat read of
the same range that has no new question behind it (rule 17).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import ReadMode, RereadTrigger, TaskStatus


@dataclasses.dataclass
class RereadTask(Record):
    KIND: ClassVar[str] = "reread_task"

    reread_id: str
    origin_mark_ids: list[str]
    reason_code: RereadTrigger
    target_node_ids: list[str]
    question: str
    required_resolution: str
    preferred_read_mode: ReadMode = ReadMode.CONTIGUOUS_SECTION
    required_context_before: int = 1
    required_context_after: int = 1
    priority_basis: list[str] = dataclasses.field(default_factory=list)
    status: TaskStatus = TaskStatus.OPEN
    attempts: list[dict] = dataclasses.field(default_factory=list)
    created_by_run: str = ""
    estimated_tokens: int = 0
    is_critical: bool = False
    max_attempts: int = 3
    max_dependency_depth: int = 2

    @staticmethod
    def make_id(target_node_ids: list[str], reason_code: str, question: str) -> str:
        return derive_id("RR", sorted(target_node_ids), reason_code, question)

    def record_attempt(
        self,
        receipt_id: str,
        resolved: bool,
        note: str = "",
        status: TaskStatus | None = None,
    ) -> None:
        self.attempts.append(
            {"receipt_id": receipt_id, "resolved": resolved, "note": note}
        )
        if status is not None:
            self.status = status
        elif resolved:
            self.status = TaskStatus.RESOLVED
