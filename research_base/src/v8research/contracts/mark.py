"""Mark: a persistent, open-coded research trace.

`open_codes` are free strings on purpose. A model may propose any number of
them and must never be forced into an OTHER bucket because a predefined
category is missing (constitution rule 2).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import DiscoveryChannel, MarkStatus


@dataclasses.dataclass
class Mark(Record):
    KIND: ClassVar[str] = "mark"

    mark_id: str
    node_id: str
    source_id: str
    span_refs: list[str]
    verbatim_anchor: str
    why_marked: str
    open_codes: list[str] = dataclasses.field(default_factory=list)
    candidate_relations: list[str] = dataclasses.field(default_factory=list)
    conditions_seen: list[str] = dataclasses.field(default_factory=list)
    exceptions_seen: list[str] = dataclasses.field(default_factory=list)
    cross_section_dependencies: list[str] = dataclasses.field(default_factory=list)
    unresolved_questions: list[str] = dataclasses.field(default_factory=list)
    discovery_channels: list[DiscoveryChannel] = dataclasses.field(default_factory=list)
    status: MarkStatus = MarkStatus.MARKED
    mark_version: int = 1
    read_receipt_id: str | None = None

    @staticmethod
    def make_id(node_id: str, verbatim_anchor: str) -> str:
        return derive_id("MARK", node_id, verbatim_anchor)

    def merge_channels(self, other: "Mark") -> None:
        """Union channel provenance without losing either side's codes.

        Deduplication may never discard discovery channel or rejected
        alternative interpretation, so a merge only ever adds.
        """
        for channel in other.discovery_channels:
            if channel not in self.discovery_channels:
                self.discovery_channels.append(channel)
        for code in other.open_codes:
            if code not in self.open_codes:
                self.open_codes.append(code)
        for question in other.unresolved_questions:
            if question not in self.unresolved_questions:
                self.unresolved_questions.append(question)
        for dep in other.cross_section_dependencies:
            if dep not in self.cross_section_dependencies:
                self.cross_section_dependencies.append(dep)
