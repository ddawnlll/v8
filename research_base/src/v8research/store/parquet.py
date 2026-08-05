"""Parquet materialisation.

Optional dependency by design: the JSONL log is the evidence authority, and a
workspace must stay fully usable without pyarrow installed. Materialisation is
a derived view that can always be rebuilt -- and rebuilding it from pinned
artifacts must yield identical row hashes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import guard
    import pyarrow  # type: ignore
    import pyarrow.parquet  # type: ignore

    AVAILABLE = True
except ImportError:  # pragma: no cover
    pyarrow = None  # type: ignore[assignment]
    AVAILABLE = False


def _normalise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give every row the same key set and JSON-encode nested values.

    Parquet needs a stable schema; research records legitimately carry nested
    lists of dicts (reread attempts, relation assertions), so those are stored
    as canonical JSON strings rather than forcing a nested arrow type.
    """
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    out = []
    for row in rows:
        flat: dict[str, Any] = {}
        for key in keys:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
            elif value is not None and not isinstance(value, (str, int, float, bool)):
                value = str(value)
            flat[key] = value
        out.append(flat)
    return out


def write_table(rows: list[dict[str, Any]], path: Path) -> bool:
    if not AVAILABLE or pyarrow is None or not rows:
        return False
    table = pyarrow.Table.from_pylist(_normalise(rows))
    path.parent.mkdir(parents=True, exist_ok=True)
    pyarrow.parquet.write_table(table, path)
    return True


def read_table(path: Path) -> list[dict[str, Any]]:
    if not AVAILABLE or pyarrow is None or not path.exists():
        return []
    return pyarrow.parquet.read_table(path).to_pylist()
