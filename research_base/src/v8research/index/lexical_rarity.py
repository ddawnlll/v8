"""Discovery channel C: lexical rarity and terminology drift.

Surfaces rare phrases, venue-specific jargon and historical vocabulary -- the
terms whose local distribution differs sharply from the corpus norm. This is
the channel most likely to find a practice that has no name in the project yet,
because a designer's keyword list cannot contain a word they do not know.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from .tokenize import bigrams, tokens


@dataclass
class RarityHit:
    node_id: str
    term: str
    local_count: int
    document_frequency: int
    rarity: float


@dataclass
class RarityIndex:
    document_frequency: Counter[str] = field(default_factory=Counter)
    node_terms: dict[str, Counter[str]] = field(default_factory=dict)
    total_nodes: int = 0

    def add(self, node_id: str, text: str) -> None:
        term_list = tokens(text)
        all_terms = term_list + bigrams(term_list)
        counts = Counter(all_terms)
        self.node_terms[node_id] = counts
        self.document_frequency.update(counts.keys())
        self.total_nodes += 1

    def rarity(self, term: str, local_count: int) -> float:
        """High when a term is frequent locally but rare corpus-wide."""
        df = self.document_frequency.get(term, 1)
        idf = math.log((self.total_nodes + 1) / df)
        return round(math.log1p(local_count) * idf, 4)

    def hits(
        self, node_id: str, min_local: int = 2, max_df_ratio: float = 0.05, limit: int = 12
    ) -> list[RarityHit]:
        counts = self.node_terms.get(node_id)
        if not counts or not self.total_nodes:
            return []
        # Floor of 3: on a small corpus a pure ratio collapses the threshold to
        # 1-2 documents, which combined with min_local yields no hits at all.
        max_df = max(3, int(self.total_nodes * max_df_ratio))
        found: list[RarityHit] = []
        for term, local_count in counts.items():
            if local_count < min_local:
                continue
            df = self.document_frequency.get(term, 1)
            if df > max_df:
                continue
            found.append(
                RarityHit(node_id, term, local_count, df, self.rarity(term, local_count))
            )
        found.sort(key=lambda hit: (-hit.rarity, hit.term))
        return found[:limit]

    def drift(self, term: str) -> float:
        """Dispersion of a term's usage across nodes.

        A term used heavily in a few nodes and lightly elsewhere scores high;
        this is the signal for vocabulary whose meaning may be shifting between
        authors or eras.
        """
        counts = [
            node_counts.get(term, 0)
            for node_counts in self.node_terms.values()
            if term in node_counts
        ]
        if len(counts) < 2:
            return 0.0
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        return round(math.sqrt(variance) / mean, 4) if mean else 0.0
