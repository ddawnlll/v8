"""Document structure: the only source of structural truth.

Fixed-size chunks may exist as derived retrieval views, but never as the
authority. `heading_path` is what makes "locate, then read continuously"
possible -- without it a multi-section reconstruction cannot tell which
sections belong to the same argument.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id, span_id
from .base import Record
from .enums import NodeType


@dataclasses.dataclass
class DocumentNode(Record):
    KIND: ClassVar[str] = "document_node"

    node_id: str
    source_id: str
    source_version: str
    node_type: NodeType
    order: int
    heading_path: list[str] = dataclasses.field(default_factory=list)
    parent_id: str | None = None
    ordered_child_ids: list[str] = dataclasses.field(default_factory=list)
    prev_node_id: str | None = None
    next_node_id: str | None = None
    char_start: int = 0
    char_end: int = 0
    line_start: int = 0
    line_end: int = 0
    page_start: int | None = None
    page_end: int | None = None
    token_estimate: int = 0
    content_hash: str = ""
    cross_reference_targets: list[str] = dataclasses.field(default_factory=list)
    figure_table_refs: list[str] = dataclasses.field(default_factory=list)

    @staticmethod
    def make_id(source_id: str, order: int, node_type: str) -> str:
        return derive_id("NODE", source_id, order, node_type)


@dataclasses.dataclass
class EvidenceSpan(Record):
    KIND: ClassVar[str] = "evidence_span"

    span_id: str
    node_id: str
    source_id: str
    source_version: str
    char_start: int
    char_end: int
    verbatim_text: str
    page: int | None = None
    is_ocr: bool = False

    @staticmethod
    def make_id(node_id: str, char_start: int, char_end: int) -> str:
        return span_id(node_id, char_start, char_end)
