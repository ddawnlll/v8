"""Candidate union and provenance-aware deduplication.

No merge may discard source provenance, modality, conditions, exceptions,
independent lineage, discovery channel, or a rejected alternative
interpretation. Merging is therefore additive: channels combine, codes
combine, nothing is dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.mark import Mark
from ..index.duplicates import jaccard, minhash

NEAR_DUPLICATE_THRESHOLD = 0.7


@dataclass
class UnionReport:
    input_count: int
    output_count: int
    exact_merges: int
    near_merges: int


def union_marks(marks: list[Mark]) -> tuple[list[Mark], UnionReport]:
    """Merge marks by evidence identity, then by near-identical wording.

    Exact merge: same node_id + same verbatim_anchor (this is what
    Mark.make_id already keys on, so exact duplicates share an id and this
    step mainly combines their channel/code provenance). Near merge: same
    node_id, high-similarity anchor text, different exact wording.
    """
    by_id: dict[str, Mark] = {}
    exact_merges = 0
    for mark in marks:
        existing = by_id.get(mark.mark_id)
        if existing is None:
            by_id[mark.mark_id] = mark
        else:
            existing.merge_channels(mark)
            exact_merges += 1

    survivors = list(by_id.values())
    near_merges = 0
    by_node: dict[str, list[Mark]] = {}
    for mark in survivors:
        by_node.setdefault(mark.node_id, []).append(mark)

    kept: list[Mark] = []
    dropped: set[str] = set()
    for node_marks in by_node.values():
        signatures = {m.mark_id: minhash(m.verbatim_anchor) for m in node_marks}
        for i, left in enumerate(node_marks):
            if left.mark_id in dropped:
                continue
            for right in node_marks[i + 1 :]:
                if right.mark_id in dropped:
                    continue
                score = jaccard(signatures[left.mark_id], signatures[right.mark_id])
                if score >= NEAR_DUPLICATE_THRESHOLD:
                    left.merge_channels(right)
                    dropped.add(right.mark_id)
                    near_merges += 1
        kept.extend(m for m in node_marks if m.mark_id not in dropped)

    report = UnionReport(len(marks), len(kept), exact_merges, near_merges)
    return kept, report
