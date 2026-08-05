"""Discovery channel D: embedding density and outliers.

Uses a hashing vectoriser rather than a downloaded model: it is deterministic,
needs no network, and the channel's job is *relative* geometry (which nodes sit
far from everything else), not absolute semantic quality. Open question 2 --
which local embedding model has adequate sensitivity to trading jargon -- stays
open, and swapping this out is a single class.

Outliers are not assumed valuable. They receive their own review quota so that
dense clusters cannot starve them.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass

from .tokenize import bigrams, tokens

DIMENSIONS = 256


def _bucket(term: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(term.encode("utf-8"), digest_size=4).digest(), "little"
    ) % DIMENSIONS


def embed(text: str, dimensions: int = DIMENSIONS) -> list[float]:
    term_list = tokens(text)
    counts = Counter(term_list + bigrams(term_list))
    vector = [0.0] * dimensions
    for term, count in counts.items():
        vector[_bucket(term) % dimensions] += 1.0 + math.log(count)
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


@dataclass
class OutlierHit:
    node_id: str
    mean_neighbor_similarity: float
    isolation: float


class EmbeddingIndex:
    def __init__(self, dimensions: int = DIMENSIONS) -> None:
        self.dimensions = dimensions
        self.vectors: dict[str, list[float]] = {}

    def add(self, node_id: str, text: str) -> None:
        self.vectors[node_id] = embed(text, self.dimensions)

    def neighbors(self, node_id: str, k: int = 5) -> list[tuple[str, float]]:
        target = self.vectors.get(node_id)
        if target is None:
            return []
        scored = [
            (other, cosine(target, vector))
            for other, vector in self.vectors.items()
            if other != node_id
        ]
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:k]

    def outliers(self, k: int = 5, limit: int = 25) -> list[OutlierHit]:
        """Rank nodes by distance from their k nearest neighbours."""
        hits: list[OutlierHit] = []
        for node_id in self.vectors:
            neighbors = self.neighbors(node_id, k)
            if not neighbors:
                continue
            mean_similarity = sum(score for _, score in neighbors) / len(neighbors)
            hits.append(
                OutlierHit(node_id, round(mean_similarity, 4), round(1 - mean_similarity, 4))
            )
        hits.sort(key=lambda hit: (-hit.isolation, hit.node_id))
        return hits[:limit]

    def dense_representatives(self, k: int = 5, limit: int = 25) -> list[str]:
        """The opposite view: nodes at the centre of dense clusters."""
        hits: list[OutlierHit] = []
        for node_id in self.vectors:
            neighbors = self.neighbors(node_id, k)
            if not neighbors:
                continue
            mean_similarity = sum(score for _, score in neighbors) / len(neighbors)
            hits.append(OutlierHit(node_id, mean_similarity, 1 - mean_similarity))
        hits.sort(key=lambda hit: (-hit.mean_neighbor_similarity, hit.node_id))
        return [hit.node_id for hit in hits[:limit]]
