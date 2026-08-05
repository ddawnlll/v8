"""Model interface and tier routing.

Provider-agnostic on purpose: model tiering is an architectural decision
("expensive models resolve ambiguity, they do not bulk-transcribe"), and the
tier -> vendor mapping is configuration that must be swappable without touching
any worker.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..contracts.enums import ModelTier


@dataclass
class LLMResponse:
    text: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end_turn"
    raw: dict[str, Any] = field(default_factory=dict)

    def json(self) -> Any:
        """Parse the response as JSON, tolerating fenced code blocks."""
        return parse_json(self.text)


class LLMClient(Protocol):
    model_id: str
    tier: ModelTier

    def complete(
        self, system: str, user: str, max_output_tokens: int = 1024
    ) -> LLMResponse: ...


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json(text: str) -> Any:
    """Extract a JSON value from model output.

    Workers demand structured artifacts, but even instructed models wrap them in
    prose or fences. A parse failure raises rather than returning a partial
    object, so a malformed extraction becomes a typed retry instead of silent
    data loss.
    """
    candidate = text.strip()
    match = _FENCE.search(candidate)
    if match:
        candidate = match.group(1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = candidate.find(opener)
        end = candidate.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON object in model output: {text[:200]!r}")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
