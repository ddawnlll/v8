"""Anthropic-backed client. Optional dependency."""

from __future__ import annotations

import os

from ..contracts.enums import ModelTier
from .base import LLMResponse

try:  # pragma: no cover - import guard
    import anthropic  # type: ignore

    AVAILABLE = True
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]
    AVAILABLE = False


class AnthropicClient:
    def __init__(
        self,
        model_id: str = "claude-sonnet-5",
        tier: ModelTier = ModelTier.STRONG,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        if not AVAILABLE or anthropic is None:
            raise RuntimeError("anthropic package not installed; install the 'llm' extra")
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=key, timeout=timeout)
        self.model_id = model_id
        self.tier = tier

    def complete(
        self, system: str, user: str, max_output_tokens: int = 1024
    ) -> LLMResponse:
        message = self._client.messages.create(
            model=self.model_id,
            system=system,
            max_tokens=max_output_tokens,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        return LLMResponse(
            text=text,
            model_id=self.model_id,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            stop_reason=message.stop_reason or "end_turn",
        )
