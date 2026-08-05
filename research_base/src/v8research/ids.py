"""Content-addressed identity.

Research constitution rule 21 requires every artifact to be content-addressed
and tied to code, prompt, model, and schema versions. Random identifiers would
break scheduler replay (a pinned manifest must reproduce task identity), so
every id here is a pure function of the payload that defines the artifact.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

_DIGEST_CHARS = 16


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def content_hash(payload: Any) -> str:
    """Stable `sha256:` hash of a payload's canonical JSON form."""
    return "sha256:" + sha256_hex(canonical_json(payload))


def derive_id(prefix: str, *parts: Any) -> str:
    """Deterministic identifier from the parts that define the artifact.

    Two calls with equal parts always return the same id; this is what makes
    duplicate task detection free rather than a separate bookkeeping table.
    """
    digest = sha256_hex(canonical_json(list(parts)))[:_DIGEST_CHARS]
    return f"{prefix}-{digest}"


def span_id(node_id: str, char_start: int, char_end: int) -> str:
    return derive_id("SPAN", node_id, char_start, char_end)


def range_hash(text: str) -> str:
    return "sha256:" + sha256_hex(text)
