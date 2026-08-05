"""ResearchStore: the single entry point for persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, TypeVar

from ..contracts.base import Record
from . import jsonl, parquet
from .cache import ContentCache
from .paths import TABLES, Workspace

R = TypeVar("R", bound=Record)

#: primary key field per record kind, used to collapse the append-only log
PRIMARY_KEYS: dict[str, str] = {
    "source": "source_id",
    "lineage_edge": "edge_id",
    "document_node": "node_id",
    "navigation_memory": "navigation_id",
    "mark": "mark_id",
    "reread_task": "reread_id",
    "read_receipt": "read_receipt_id",
    "evidence_span": "span_id",
    "claim": "claim_id",
    "verification": "verification_id",
    "finding": "finding_id",
    "concept": "concept_id",
    "concept_proposal": "proposal_id",
    "ontology_annotation": "annotation_id",
    "schema_change": "change_id",
    "v8_assumption": "assumption_id",
    "v8_impact": "impact_id",
    "research_proposal": "proposal_id",
}


class ResearchStore:
    def __init__(self, root: str | Path) -> None:
        self.workspace = Workspace.create(root)
        self.cache = ContentCache(self.workspace.cache)

    def append(self, record: Record) -> None:
        jsonl.append(self.workspace.jsonl(record.KIND), record.to_dict())

    def append_many(self, records: Iterable[Record]) -> int:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(record.KIND, []).append(record.to_dict())
        for kind, payloads in grouped.items():
            jsonl.append_many(self.workspace.jsonl(kind), payloads)
        return sum(len(v) for v in grouped.values())

    def read(self, cls: type[R]) -> list[R]:
        """Latest version of every record of this kind."""
        key = PRIMARY_KEYS.get(cls.KIND)
        path = self.workspace.jsonl(cls.KIND)
        payloads = (
            jsonl.read_latest(path, key) if key else list(jsonl.read(path))
        )
        return [cls.from_dict(p) for p in payloads]

    def read_raw(self, kind: str) -> list[dict[str, Any]]:
        return list(jsonl.read(self.workspace.jsonl(kind)))

    def count(self, kind: str) -> int:
        return jsonl.count(self.workspace.jsonl(kind))

    def put_text(self, node_id: str, text: str) -> None:
        self.workspace.node_text(node_id).write_text(text, encoding="utf-8")

    def get_text(self, node_id: str) -> str:
        path = self.workspace.node_text(node_id)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def materialize(self) -> dict[str, int]:
        """Rebuild every Parquet table from the JSONL authority."""
        written: dict[str, int] = {}
        for kind in TABLES:
            key = PRIMARY_KEYS.get(kind)
            path = self.workspace.jsonl(kind)
            rows = jsonl.read_latest(path, key) if key else list(jsonl.read(path))
            if rows and parquet.write_table(rows, self.workspace.parquet_file(kind)):
                written[kind] = len(rows)
        return written
