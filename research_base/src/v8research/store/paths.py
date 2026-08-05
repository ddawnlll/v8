"""Physical layout of a research workspace.

File names follow the specification's persistence baseline. Everything is
written as append-only JSONL first (crash-safe, line-addressable) and
materialised to Parquet for analytics; the JSONL remains the authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: record KIND -> base file name
TABLES: dict[str, str] = {
    "source": "sources",
    "lineage_edge": "source_lineage_edges",
    "document_node": "document_nodes",
    "navigation_memory": "navigation_memories",
    "mark": "marks",
    "reread_task": "reread_tasks",
    "read_receipt": "read_receipts",
    "evidence_span": "evidence_spans",
    "claim": "claims",
    "verification": "claim_verifications",
    "finding": "findings",
    "concept": "ontology_concepts",
    "concept_proposal": "ontology_proposals",
    "ontology_annotation": "ontology_annotations",
    "schema_change": "schema_change_log",
    "v8_assumption": "v8_assumptions",
    "v8_impact": "v8_impact_edges",
    "research_proposal": "research_proposals",
    "run_manifest": "run_manifests",
}


@dataclass(frozen=True)
class Workspace:
    root: Path

    @classmethod
    def create(cls, root: str | Path) -> "Workspace":
        ws = cls(Path(root))
        for directory in (ws.records, ws.parquet, ws.cache, ws.text, ws.reports):
            directory.mkdir(parents=True, exist_ok=True)
        return ws

    @property
    def records(self) -> Path:
        return self.root / "records"

    @property
    def parquet(self) -> Path:
        return self.root / "parquet"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def text(self) -> Path:
        return self.root / "text"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def corpus_manifest(self) -> Path:
        return self.root / "corpus_manifest.json"

    def jsonl(self, kind: str) -> Path:
        return self.records / f"{TABLES.get(kind, kind)}.jsonl"

    def parquet_file(self, kind: str) -> Path:
        return self.parquet / f"{TABLES.get(kind, kind)}.parquet"

    def node_text(self, node_id: str) -> Path:
        return self.text / f"{node_id}.txt"
