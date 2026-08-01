"""Append-only log with idempotent dedup and deterministic replay.

Log first, apply second; replay is byte-identical; duplicates are dropped
against the (source, event_id) inbox (PERSISTENCE_REPLAY_SPEC sections 3-4).
"""
from __future__ import annotations

import json
from pathlib import Path

from .schema import TapeRow, sha1_hex


class AppendOnlyLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._inbox: dict[tuple[str, str], None] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                rec = json.loads(line)
                self._inbox[(rec['source'], rec['event_id'])] = None

    def append(self, record: dict) -> bool:
        """Return False if the (source, event_id) was already applied."""
        key = (record['source'], record['event_id'])
        if key in self._inbox:
            return False
        with self.path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, sort_keys=True) + '\n')
        self._inbox[key] = None
        return True

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding='utf-8').splitlines()]

    def replay_tape(self) -> list[TapeRow]:
        """Tape rows in canonical replay order (event, available, sequence)."""
        rows = [TapeRow(**r) for r in self.read() if 'channel' in r]
        rows.sort(key=lambda r: (r.event_time, r.available_time, r.venue_sequence))
        return rows

    @property
    def hash(self) -> str:
        return sha1_hex(self.read())
