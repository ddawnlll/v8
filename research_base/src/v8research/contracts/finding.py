"""Finding: immutable evidence interpretation at verification time.

`frozen=True` is load-bearing, not stylistic. Constitution rule 11 makes
findings immutable and rule 5 in the ontology section requires that changing
the ontology never alters a finding hash -- enforcing that at the dataclass
level means a correction must create a successor rather than mutate history.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import FindingStatus


@dataclasses.dataclass(frozen=True)
class Finding(Record):
    KIND: ClassVar[str] = "finding"

    finding_id: str
    finding_statement: str
    claim_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    independent_lineage_ids: tuple[str, ...] = ()
    decision_relevance_without_v8: str = ""
    verification_quality: float = 0.0
    source_independence: float = 0.0
    preregistered_value: int = 1
    known_counterevidence_ids: tuple[str, ...] = ()
    unresolved_reread_ids: tuple[str, ...] = ()
    status: FindingStatus = FindingStatus.PROVISIONAL
    finding_version: int = 1
    supersedes_finding_id: str | None = None
    content_hash: str = ""

    @staticmethod
    def make_id(finding_statement: str, claim_ids: tuple[str, ...]) -> str:
        return derive_id("FND", finding_statement, sorted(claim_ids))

    def with_hash(self) -> "Finding":
        return dataclasses.replace(self, content_hash=self.compute_hash())

    def superseded_by(self, statement: str, **changes) -> "Finding":
        """Create a successor. The original record is never rewritten."""
        payload = dataclasses.asdict(self)
        payload.update(changes)
        payload["finding_statement"] = statement
        payload["finding_version"] = self.finding_version + 1
        payload["supersedes_finding_id"] = self.finding_id
        payload["claim_ids"] = tuple(payload["claim_ids"])
        payload["source_ids"] = tuple(payload["source_ids"])
        payload["independent_lineage_ids"] = tuple(payload["independent_lineage_ids"])
        payload["known_counterevidence_ids"] = tuple(payload["known_counterevidence_ids"])
        payload["unresolved_reread_ids"] = tuple(payload["unresolved_reread_ids"])
        payload["finding_id"] = Finding.make_id(statement, payload["claim_ids"])
        payload["content_hash"] = ""
        return Finding(**payload).with_hash()
