"""Per-run cost accounting.

Every run reports the fields the specification names under "Cost accounting",
built entirely from ReadReceipt records already on disk -- accounting is a
report over the evidence base, never a separate ledger that could drift from
what actually happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.receipt import ReadReceipt
from ..reading.receipts import ReceiptLog


@dataclass
class RunAccounting:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    reads_by_purpose: dict[str, int] = field(default_factory=dict)
    tokens_by_model: dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    marks_per_million_unique_tokens: float = 0.0
    verified_findings_per_million_unique_tokens: float = 0.0

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total else 0.0


def build_accounting(
    receipts: list[ReadReceipt],
    *,
    mark_count: int = 0,
    verified_finding_count: int = 0,
    unique_source_tokens: int = 0,
) -> RunAccounting:
    accounting = RunAccounting()
    for receipt in receipts:
        accounting.total_input_tokens += receipt.input_tokens
        accounting.total_output_tokens += receipt.output_tokens
        accounting.reads_by_purpose[receipt.purpose] = (
            accounting.reads_by_purpose.get(receipt.purpose, 0) + 1
        )
        accounting.tokens_by_model[receipt.model_id] = (
            accounting.tokens_by_model.get(receipt.model_id, 0)
            + receipt.input_tokens
            + receipt.output_tokens
        )
        if receipt.cache_hit:
            accounting.cache_hits += 1
        else:
            accounting.cache_misses += 1

    if unique_source_tokens:
        millions = unique_source_tokens / 1_000_000
        accounting.marks_per_million_unique_tokens = round(mark_count / millions, 4)
        accounting.verified_findings_per_million_unique_tokens = round(
            verified_finding_count / millions, 4
        )
    return accounting


def accounting_report(
    receipt_log: ReceiptLog,
    node_tokens: dict[str, int],
    *,
    mark_count: int,
    verified_finding_count: int,
) -> dict:
    all_receipts = receipt_log.store.read(ReadReceipt)
    duplication = receipt_log.duplication_report(node_tokens)
    accounting = build_accounting(
        all_receipts,
        mark_count=mark_count,
        verified_finding_count=verified_finding_count,
        unique_source_tokens=duplication.unique_source_tokens,
    )
    return {
        "total_input_tokens": accounting.total_input_tokens,
        "total_output_tokens": accounting.total_output_tokens,
        "reads_by_purpose": accounting.reads_by_purpose,
        "tokens_by_model": accounting.tokens_by_model,
        "cache_hit_rate": round(accounting.cache_hit_rate, 4),
        "unique_source_tokens": duplication.unique_source_tokens,
        "repeated_source_tokens": duplication.repeated_source_tokens,
        "duplicated_context_ratio": round(duplication.duplicated_context_ratio, 4),
        "marks_per_million_unique_source_tokens": accounting.marks_per_million_unique_tokens,
        "verified_findings_per_million_unique_source_tokens": (
            accounting.verified_findings_per_million_unique_tokens
        ),
    }
