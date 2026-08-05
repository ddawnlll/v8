"""Content-addressed cache.

Anti-waste rule 1: identical source range + purpose + prompt + model
configuration is served from cache. The cache key is the ReadReceipt id, which
is itself derived from exactly those five components -- so a cache miss means
something genuinely differed, and that difference is inspectable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ContentCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _path(self, key: str) -> Path:
        # Shard by prefix so a corpus-scale run does not create one flat
        # directory with hundreds of thousands of entries.
        return self.root / key[-2:] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, key: str, value: dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, sort_keys=True, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def has(self, key: str) -> bool:
        return self._path(key).exists()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def stats(self) -> dict[str, Any]:
        return {"hits": self.hits, "misses": self.misses, "hit_rate": self.hit_rate}
