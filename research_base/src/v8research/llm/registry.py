"""Tier -> client routing.

The default routing table encodes the specification's model tiering: local
tools for statistics, a cheap model for first-pass navigation and marking, a
strong and *independently chosen* model for entailment verification. Verifier
independence matters -- using the same model to extract and to verify makes
correlated errors invisible (open question 9).
"""

from __future__ import annotations

from ..contracts.enums import ModelTier
from .base import LLMClient
from .echo import EchoClient


class ModelRegistry:
    def __init__(self) -> None:
        self._clients: dict[ModelTier, LLMClient] = {}
        self.calls_by_model: dict[str, int] = {}

    def register(self, tier: ModelTier, client: LLMClient) -> None:
        self._clients[tier] = client

    def get(self, tier: ModelTier) -> LLMClient:
        if tier not in self._clients:
            raise KeyError(f"no client registered for tier {tier}")
        return self._clients[tier]

    def has(self, tier: ModelTier) -> bool:
        return tier in self._clients

    def note_call(self, model_id: str) -> None:
        self.calls_by_model[model_id] = self.calls_by_model.get(model_id, 0) + 1

    @classmethod
    def offline(cls) -> "ModelRegistry":
        """All tiers served by deterministic baselines."""
        registry = cls()
        for tier in (ModelTier.SMALL, ModelTier.MEDIUM, ModelTier.STRONG):
            registry.register(tier, EchoClient(tier))
        return registry

    def verifier_for(self, extractor_model_id: str) -> LLMClient:
        """Pick a verifier that is not the extractor.

        Falls back to the same model only when nothing else is registered, and
        callers are expected to record that the independence assumption was not
        satisfied for that verification.
        """
        strong = self._clients.get(ModelTier.STRONG)
        if strong is not None and strong.model_id != extractor_model_id:
            return strong
        for tier in (ModelTier.MEDIUM, ModelTier.SMALL):
            client = self._clients.get(tier)
            if client is not None and client.model_id != extractor_model_id:
                return client
        if strong is not None:
            return strong
        raise KeyError("no verifier client registered")
