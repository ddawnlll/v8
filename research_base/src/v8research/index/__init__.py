"""Local, LLM-free indexes backing the deterministic discovery channels."""

from .bm25 import BM25Index
from .duplicates import MinHashLSH, exact_duplicates, jaccard, minhash
from .embeddings import EmbeddingIndex, OutlierHit, cosine, embed
from .lexical_rarity import RarityHit, RarityIndex
from .tokenize import bigrams, shingles, tokens

__all__ = [
    "BM25Index",
    "EmbeddingIndex",
    "MinHashLSH",
    "OutlierHit",
    "RarityHit",
    "RarityIndex",
    "bigrams",
    "cosine",
    "embed",
    "exact_duplicates",
    "jaccard",
    "minhash",
    "shingles",
    "tokens",
]
