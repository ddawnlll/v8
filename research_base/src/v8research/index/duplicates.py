"""MinHash near-duplicate detection. Pure stdlib.

Feeds two things: POSSIBLE_COPY lineage edges, and the deduplication level
"near-identical wording" in the candidate union.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

from .tokenize import shingles

_MASK = (1 << 61) - 1


def _hash(value: str, seed: int) -> int:
    digest = hashlib.blake2b(
        value.encode("utf-8"), digest_size=8, salt=seed.to_bytes(8, "little")
    ).digest()
    return int.from_bytes(digest, "little") & _MASK


def minhash(text: str, permutations: int = 64, shingle_size: int = 5) -> list[int]:
    grams = shingles(text, shingle_size)
    if not grams:
        return [_MASK] * permutations
    return [min(_hash(g, seed) for g in grams) for seed in range(permutations)]


def jaccard(left: list[int], right: list[int]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    matches = sum(1 for a, b in zip(left, right) if a == b)
    return matches / len(left)


class MinHashLSH:
    """Banded LSH so candidate pairs are found without an O(n^2) sweep."""

    def __init__(self, permutations: int = 64, bands: int = 16) -> None:
        if permutations % bands:
            raise ValueError("permutations must be divisible by bands")
        self.permutations = permutations
        self.bands = bands
        self.rows = permutations // bands
        self.signatures: dict[str, list[int]] = {}
        self._buckets: list[dict[tuple, list[str]]] = [
            defaultdict(list) for _ in range(bands)
        ]

    def add(self, key: str, text: str) -> None:
        signature = minhash(text, self.permutations)
        self.signatures[key] = signature
        for band in range(self.bands):
            chunk = tuple(signature[band * self.rows : (band + 1) * self.rows])
            self._buckets[band][chunk].append(key)

    def candidate_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for buckets in self._buckets:
            for members in buckets.values():
                if len(members) < 2:
                    continue
                for i, left in enumerate(members):
                    for right in members[i + 1 :]:
                        pairs.add(tuple(sorted((left, right))))  # type: ignore[arg-type]
        return pairs

    def similarities(self, threshold: float = 0.5) -> dict[tuple[str, str], float]:
        out: dict[tuple[str, str], float] = {}
        for left, right in self.candidate_pairs():
            score = jaccard(self.signatures[left], self.signatures[right])
            if score >= threshold:
                out[(left, right)] = score
        return out


def exact_duplicates(texts: dict[str, str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for key, text in texts.items():
        digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        groups[digest].append(key)
    return {d: sorted(keys) for d, keys in groups.items() if len(keys) > 1}
