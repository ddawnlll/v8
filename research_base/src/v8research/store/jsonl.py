"""Append-only JSONL tables.

Every stage writes its artifacts before the next stage begins, so a run may
pause at any point and resume from what is on disk. Nothing is ever rewritten
in place: an updated record is appended and the last write wins on read.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator


def append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def append_many(path: Path, payloads: list[dict[str, Any]]) -> None:
    if not payloads:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(
                json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def read(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_latest(path: Path, key: str) -> list[dict[str, Any]]:
    """Collapse an append-only log to the newest version of each record."""
    latest: dict[str, dict[str, Any]] = {}
    for payload in read(path):
        identity = payload.get(key)
        if identity is not None:
            latest[identity] = payload
    return list(latest.values())


def count(path: Path) -> int:
    return sum(1 for _ in read(path))
