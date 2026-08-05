"""Source lineage detection.

Constitution rule 13: popularity is not evidence strength. A passage copied
into ten books raises raw source count by ten and independent lineage count by
one, and this module is what makes that distinction computable.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ..contracts.source import NON_INDEPENDENT_RELATIONS, LineageEdge, Source
from ..contracts.enums import LineageRelation

_PUNCT = re.compile(r"[^a-z0-9\s]")
_STOP_TITLE = {
    "the", "a", "an", "of", "and", "to", "for", "in", "on", "with", "how",
    "edition", "revised", "updated", "2nd", "3rd", "4th", "second", "third",
}


def normalize_work(title: str) -> str:
    """Collapse a title to a work identity, ignoring edition decoration."""
    base = title.split(" - ")[0].lower()
    base = _PUNCT.sub(" ", base)
    words = [w for w in base.split() if w and w not in _STOP_TITLE]
    return "_".join(words[:8])


def detect_edition_families(sources: list[Source]) -> list[LineageEdge]:
    """Sources sharing a work identity are the same edition family."""
    groups: dict[str, list[Source]] = defaultdict(list)
    for source in sources:
        groups[source.work_id or normalize_work(source.title)].append(source)

    edges: list[LineageEdge] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        anchor = min(members, key=lambda s: s.source_id)
        for other in members:
            if other.source_id == anchor.source_id:
                continue
            edges.append(
                LineageEdge(
                    edge_id=LineageEdge.make_id(
                        other.source_id, anchor.source_id, LineageRelation.SAME_EDITION_FAMILY
                    ),
                    from_source_id=other.source_id,
                    to_source_id=anchor.source_id,
                    relation=LineageRelation.SAME_EDITION_FAMILY,
                    confidence=1.0,
                    evidence=f"shared work identity: {anchor.work_id or normalize_work(anchor.title)}",
                    detector="edition_family",
                )
            )
    return edges


def detect_same_author(sources: list[Source]) -> list[LineageEdge]:
    groups: dict[str, list[Source]] = defaultdict(list)
    for source in sources:
        for author in source.author_ids:
            groups[author].append(source)

    edges: list[LineageEdge] = []
    seen: set[tuple[str, str]] = set()
    for author, members in groups.items():
        if len(members) < 2:
            continue
        anchor = min(members, key=lambda s: s.source_id)
        for other in members:
            pair = (other.source_id, anchor.source_id)
            if other.source_id == anchor.source_id or pair in seen:
                continue
            seen.add(pair)
            edges.append(
                LineageEdge(
                    edge_id=LineageEdge.make_id(
                        other.source_id, anchor.source_id, LineageRelation.SAME_AUTHOR_LINEAGE
                    ),
                    from_source_id=other.source_id,
                    to_source_id=anchor.source_id,
                    relation=LineageRelation.SAME_AUTHOR_LINEAGE,
                    confidence=1.0,
                    evidence=f"shared author: {author}",
                    detector="same_author",
                )
            )
    return edges


def possible_copies(
    similarities: dict[tuple[str, str], float], threshold: float = 0.6
) -> list[LineageEdge]:
    """Turn near-duplicate similarity into POSSIBLE_COPY edges.

    Deliberately named "possible": shared tradition and direct copying are not
    reliably separable by text overlap alone (open question 6).
    """
    edges: list[LineageEdge] = []
    for (left, right), score in similarities.items():
        if score < threshold or left == right:
            continue
        source, target = sorted((left, right))
        edges.append(
            LineageEdge(
                edge_id=LineageEdge.make_id(
                    source, target, LineageRelation.POSSIBLE_COPY
                ),
                from_source_id=source,
                to_source_id=target,
                relation=LineageRelation.POSSIBLE_COPY,
                confidence=round(score, 4),
                evidence=f"minhash jaccard={score:.3f}",
                detector="minhash",
            )
        )
    return edges


class LineageGraph:
    """Union-find over non-independent relations."""

    def __init__(self, edges: list[LineageEdge]) -> None:
        self._parent: dict[str, str] = {}
        for edge in edges:
            if edge.relation in NON_INDEPENDENT_RELATIONS:
                self._union(edge.from_source_id, edge.to_source_id)

    def _find(self, node: str) -> str:
        self._parent.setdefault(node, node)
        while self._parent[node] != node:
            self._parent[node] = self._parent[self._parent[node]]
            node = self._parent[node]
        return node

    def _union(self, left: str, right: str) -> None:
        left_root, right_root = self._find(left), self._find(right)
        if left_root != right_root:
            self._parent[max(left_root, right_root)] = min(left_root, right_root)

    def lineage_id(self, source_id: str) -> str:
        return f"LIN-{self._find(source_id)}"

    def independent_lineages(self, source_ids: list[str]) -> list[str]:
        return sorted({self.lineage_id(s) for s in source_ids})

    def counts(self, source_ids: list[str]) -> tuple[int, int]:
        """(raw_source_count, independent_lineage_count)"""
        return len(source_ids), len(self.independent_lineages(source_ids))
