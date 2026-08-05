"""Shared tokenisation for every local index.

One tokeniser for BM25, rarity and duplicate detection, so a term means the
same thing in all three channels and their scores stay comparable.
"""

from __future__ import annotations

import re

WORD = re.compile(r"[a-z][a-z0-9'\-]{1,}")

STOPWORDS = frozenset(
    """a an the and or but if then than that this these those of in on at to for
    with without from by as is are was were be been being it its it's he she they
    them his her their you your we our i me my not no nor so such can could will
    would shall should may might must do does did done have has had having there
    here when where which who whom what how why all any both each few more most
    other some only own same too very just also into over under again further
    once about against between during before after above below up down out off""".split()
)


def tokens(text: str, keep_stopwords: bool = False) -> list[str]:
    found = WORD.findall(text.lower())
    if keep_stopwords:
        return found
    return [t for t in found if t not in STOPWORDS]


def bigrams(term_list: list[str]) -> list[str]:
    return [f"{a}_{b}" for a, b in zip(term_list, term_list[1:])]


def shingles(text: str, size: int = 5) -> set[str]:
    """Word shingles for near-duplicate detection."""
    words = tokens(text, keep_stopwords=True)
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}
