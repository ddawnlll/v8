"""ReadReceipt: exactly what was shown to which model, and why.

This is the artifact that makes the duplicated-context ratio measurable. A
wider reread must reference the narrower receipt it supersedes and state what
was missing, so repeated reading is always attributable.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record
from .enums import ReadPurpose


@dataclasses.dataclass
class ReadReceipt(Record):
    KIND: ClassVar[str] = "read_receipt"

    read_receipt_id: str
    source_range_hashes: list[str]
    structural_node_ids: list[str]
    purpose: ReadPurpose
    question_hash: str
    prompt_version: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit: bool = False
    supersedes_receipt: str | None = None
    missing_information: str = ""
    produced_artifact_ids: list[str] = dataclasses.field(default_factory=list)
    timestamp: str = ""
    run_id: str = ""

    @staticmethod
    def make_id(
        source_range_hashes: list[str],
        purpose: str,
        question_hash: str,
        prompt_version: str,
        model_id: str,
    ) -> str:
        """Identity is the full cache key.

        Two reads that agree on range, purpose, question, prompt and model are
        the same read; the second one must be served from cache.
        """
        return derive_id(
            "READ",
            sorted(source_range_hashes),
            purpose,
            question_hash,
            prompt_version,
            model_id,
        )
