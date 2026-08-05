"""ReceiptLog: the anti-repetition gate.

This is the single most important control in the system. Anti-waste rule 1
says identical source range + purpose + prompt + model configuration is served
from cache; rule 2 says a wider reread must reference the narrower receipt and
state what was missing. Both are enforced here, not left to worker discipline
-- v2's "milliar token" failure mode was exactly this check missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.enums import ReadPurpose
from ..contracts.receipt import ReadReceipt
from ..ids import range_hash
from ..store.store import ResearchStore


@dataclass
class DuplicationReport:
    total_receipts: int
    cache_hits: int
    unique_source_tokens: int
    repeated_source_tokens: int

    @property
    def duplicated_context_ratio(self) -> float:
        total = self.unique_source_tokens + self.repeated_source_tokens
        return self.repeated_source_tokens / total if total else 0.0


class ReceiptLog:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store
        self._by_range: dict[str, list[ReadReceipt]] = {}
        for receipt in store.read(ReadReceipt):
            self._index(receipt)

    def _index(self, receipt: ReadReceipt) -> None:
        for range_key in receipt.source_range_hashes:
            self._by_range.setdefault(range_key, []).append(receipt)

    def find_cached(
        self,
        source_range_hashes: list[str],
        purpose: ReadPurpose,
        question_hash: str,
        prompt_version: str,
        model_id: str,
    ) -> ReadReceipt | None:
        receipt_id = ReadReceipt.make_id(
            source_range_hashes, purpose, question_hash, prompt_version, model_id
        )
        for candidate in self._by_range.get(source_range_hashes[0], []) if source_range_hashes else []:
            if candidate.read_receipt_id == receipt_id:
                return candidate
        return None

    def prior_reads(self, node_id: str, purpose: ReadPurpose | None = None) -> list[ReadReceipt]:
        """All receipts that touched this structural node, for reread justification."""
        found = [
            r for r in self._by_range.get(range_hash(node_id), [])
        ]
        by_node = [
            r
            for receipts in self._by_range.values()
            for r in receipts
            if node_id in r.structural_node_ids
        ]
        combined = {r.read_receipt_id: r for r in found + by_node}
        results = list(combined.values())
        if purpose is not None:
            results = [r for r in results if r.purpose == purpose]
        return results

    def record(
        self,
        *,
        source_range_hashes: list[str],
        structural_node_ids: list[str],
        purpose: ReadPurpose,
        question_hash: str,
        prompt_version: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cache_hit: bool,
        run_id: str,
        supersedes_receipt: str | None = None,
        missing_information: str = "",
        produced_artifact_ids: list[str] | None = None,
        timestamp: str = "",
    ) -> ReadReceipt:
        if supersedes_receipt is None and not cache_hit and purpose == ReadPurpose.REREAD:
            self._require_new_reason(structural_node_ids, purpose, missing_information)
        receipt_id = ReadReceipt.make_id(
            source_range_hashes, purpose, question_hash, prompt_version, model_id
        )
        receipt = ReadReceipt(
            read_receipt_id=receipt_id,
            source_range_hashes=source_range_hashes,
            structural_node_ids=structural_node_ids,
            purpose=purpose,
            question_hash=question_hash,
            prompt_version=prompt_version,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_hit=cache_hit,
            supersedes_receipt=supersedes_receipt,
            missing_information=missing_information,
            produced_artifact_ids=produced_artifact_ids or [],
            timestamp=timestamp,
            run_id=run_id,
        )
        self.store.append(receipt)
        self._index(receipt)
        return receipt

    def _require_new_reason(
        self, structural_node_ids: list[str], purpose: ReadPurpose, missing_information: str
    ) -> None:
        """Reject a fresh (non-cached) REREAD of an already-read range with no stated reason.

        Anti-waste rule 2 is specific to widening a reread: it does not apply
        to NAVIGATION or MARKING, where independent discovery channels are
        expected to touch the same node with genuinely different questions --
        that is the point of having multiple channels, not repetition.
        """
        if missing_information.strip():
            return
        for node_id in structural_node_ids:
            if self.prior_reads(node_id, purpose):
                raise ValueError(
                    f"repeat reread of {node_id} with no missing_information reason; "
                    "cite the narrower receipt or use the cache"
                )

    def duplication_report(self, node_tokens: dict[str, int]) -> DuplicationReport:
        """Unique vs. repeated source tokens across every recorded read.

        This is the number the specification calls the most important waste
        metric: `duplicated_context_ratio`.
        """
        seen: set[str] = set()
        unique_tokens = 0
        repeated_tokens = 0
        total = 0
        hits = 0
        for receipts in self._by_range.values():
            for receipt in receipts:
                total += 1
                if receipt.cache_hit:
                    hits += 1
                    continue
                for node_id in receipt.structural_node_ids:
                    tokens = node_tokens.get(node_id, 0)
                    if node_id in seen:
                        repeated_tokens += tokens
                    else:
                        seen.add(node_id)
                        unique_tokens += tokens
        return DuplicationReport(total, hits, unique_tokens, repeated_tokens)
