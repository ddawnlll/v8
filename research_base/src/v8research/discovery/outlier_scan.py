"""Channel D: embedding density and outliers.

Both directions are reported. Outliers are not assumed valuable -- they get a
distinct review quota so dense clusters cannot starve them (constitution rule
14 / failure mode "Dense clusters dominate reread budget").
"""

from __future__ import annotations

from ..index.embeddings import EmbeddingIndex, OutlierHit


def select_outlier_candidates(index: EmbeddingIndex, k: int = 5, limit: int = 40) -> list[OutlierHit]:
    return index.outliers(k=k, limit=limit)


def select_dense_representatives(index: EmbeddingIndex, k: int = 5, limit: int = 20) -> list[str]:
    """A distinct, smaller quota: dense clusters still get *some* deliberate coverage."""
    return index.dense_representatives(k=k, limit=limit)
