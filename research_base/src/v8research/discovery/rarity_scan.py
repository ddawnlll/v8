"""Channel C: lexical rarity and terminology drift -> candidate nodes.

Detection is local and free (`index.RarityIndex`); this module only decides
*which* nodes earn a marking pass because of what the detector found, and
tags the resulting marks with their triggering terms for audit.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..index.lexical_rarity import RarityIndex


@dataclass
class RarityCandidate:
    node_id: str
    trigger_terms: list[str]
    max_rarity: float


def select_rarity_candidates(
    index: RarityIndex, node_ids: list[str], top_k: int = 40
) -> list[RarityCandidate]:
    """Rank nodes by their strongest rarity signal; caller marks the top_k."""
    scored: list[RarityCandidate] = []
    for node_id in node_ids:
        hits = index.hits(node_id)
        if not hits:
            continue
        scored.append(
            RarityCandidate(
                node_id=node_id,
                trigger_terms=[h.term for h in hits],
                max_rarity=hits[0].rarity,
            )
        )
    scored.sort(key=lambda c: (-c.max_rarity, c.node_id))
    return scored[:top_k]


def terminology_drift_report(index: RarityIndex, terms: list[str]) -> dict[str, float]:
    """Corpus-wide drift score per term, for the terminology-drift diagnostic."""
    return {term: index.drift(term) for term in terms}
