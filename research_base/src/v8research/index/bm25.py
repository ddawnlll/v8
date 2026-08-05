"""BM25 retrieval over document nodes. Pure stdlib."""

from __future__ import annotations

import math
from collections import Counter

from .tokenize import tokens


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_ids: list[str] = []
        self.term_freqs: list[Counter[str]] = []
        self.lengths: list[int] = []
        self.doc_freq: Counter[str] = Counter()
        self.avg_length = 0.0

    def add(self, doc_id: str, text: str) -> None:
        term_list = tokens(text)
        freqs = Counter(term_list)
        self.doc_ids.append(doc_id)
        self.term_freqs.append(freqs)
        self.lengths.append(len(term_list))
        self.doc_freq.update(freqs.keys())

    def finalize(self) -> None:
        self.avg_length = (
            sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        )

    def _idf(self, term: str) -> float:
        total = len(self.doc_ids)
        df = self.doc_freq.get(term, 0)
        return math.log(1 + (total - df + 0.5) / (df + 0.5))

    def search(self, query: str, limit: int = 20) -> list[tuple[str, float]]:
        if not self.avg_length:
            self.finalize()
        query_terms = tokens(query)
        scored: list[tuple[str, float]] = []
        for index, doc_id in enumerate(self.doc_ids):
            freqs = self.term_freqs[index]
            length = self.lengths[index] or 1
            score = 0.0
            for term in query_terms:
                tf = freqs.get(term, 0)
                if not tf:
                    continue
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * length / (self.avg_length or 1)
                )
                score += self._idf(term) * tf * (self.k1 + 1) / denominator
            if score > 0:
                scored.append((doc_id, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:limit]
