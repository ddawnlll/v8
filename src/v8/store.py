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
        # Open the append handle ONCE (per-record open/close dominated append
        # cost — ~half the profiled run time). flush() per append keeps the
        # crash-loss policy bounded to the current record.
        self._fh = self.path.open('a', encoding='utf-8')
        self._inbox: dict[tuple[str, str], None] = {}
        # Parsed-log cache. The log is append-only and this handle is the only
        # writer, so the file can only change via append() — which invalidates.
        # Without it every read() re-read AND re-parsed the whole JSONL, and
        # `hash` re-parsed it and then re-serialized the entire list: 17 reads
        # cost ~5.9s of a ~39s run on the 8760-bar dev tape (14% of wall).
        self._cache: list[dict] | None = None
        self._hash: str | None = None
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                rec = json.loads(line)
                self._inbox[(rec['source'], rec['event_id'])] = None

    def append(self, record: dict) -> bool:
        """Return False if the (source, event_id) was already applied."""
        key = (record['source'], record['event_id'])
        if key in self._inbox:
            return False
        self._fh.write(json.dumps(record, sort_keys=True) + '\n')
        self._fh.flush()
        self._inbox[key] = None
        # Invalidate rather than splice `record` into the cache: the stored
        # form is its JSON round-trip (tuples become lists), so inserting the
        # in-memory dict would make read() disagree with the file.
        self._cache = None
        self._hash = None
        return True

    def read(self) -> list[dict]:
        """Parsed records in file order. The returned list is a fresh copy, but
        the record dicts are shared with the cache — callers must treat them as
        read-only (every current caller only iterates, filters or sorts)."""
        if self._cache is None:
            if not self.path.exists():
                self._cache = []
            else:
                self._cache = [json.loads(l) for l
                               in self.path.read_text(encoding='utf-8').splitlines()]
        return list(self._cache)

    def replay_tape(self) -> list[TapeRow]:
        """Tape rows in canonical replay order (event, available, sequence)."""
        rows = [TapeRow(**r) for r in self.read() if 'channel' in r]
        rows.sort(key=lambda r: (r.event_time, r.available_time, r.venue_sequence))
        return rows

    @property
    def hash(self) -> str:
        if self._hash is None:
            self._hash = sha1_hex(self.read())
        return self._hash
