"""Source identity and lineage.

Every source gets a stable identity before any LLM work begins, so that
`raw_source_count` and `independent_lineage_count` can always be reported
separately (constitution rule 13).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import LineageRelation


@dataclasses.dataclass
class Source(Record):
    KIND: ClassVar[str] = "source"

    source_id: str
    source_version: str
    title: str
    source_family: str = "practitioner_book"
    language: str = "en"
    author_ids: list[str] = dataclasses.field(default_factory=list)
    publication_date: str | None = None
    edition: str | None = None
    work_id: str | None = None
    edition_id: str | None = None
    rights_status: str = "user_supplied"
    source_kind: str = "text"
    page_count: int | None = None
    parent_sources: list[str] = dataclasses.field(default_factory=list)
    declared_citations: list[str] = dataclasses.field(default_factory=list)
    possible_derivation_edges: list[str] = dataclasses.field(default_factory=list)
    ingestion_manifest_hash: str | None = None

    @staticmethod
    def make_id(title: str, edition: str | None) -> str:
        return derive_id("SRC", title, edition or "")


@dataclasses.dataclass
class LineageEdge(Record):
    KIND: ClassVar[str] = "lineage_edge"

    edge_id: str
    from_source_id: str
    to_source_id: str
    relation: LineageRelation
    confidence: float = 1.0
    evidence: str = ""
    detector: str = "manual"

    @staticmethod
    def make_id(from_source_id: str, to_source_id: str, relation: str) -> str:
        return derive_id("LIN", from_source_id, to_source_id, relation)


#: Relations that make two sources non-independent for corroboration counting.
#: CITES is excluded: citing a work is normal scholarship, not shared origin.
NON_INDEPENDENT_RELATIONS = frozenset(
    {
        LineageRelation.DERIVES_FROM,
        LineageRelation.REPHRASES,
        LineageRelation.SAME_AUTHOR_LINEAGE,
        LineageRelation.SAME_DATASET,
        LineageRelation.SAME_EDITION_FAMILY,
        LineageRelation.POSSIBLE_COPY,
        LineageRelation.TRANSLATION_OF,
    }
)
