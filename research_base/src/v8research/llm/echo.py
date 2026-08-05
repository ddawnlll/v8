"""Deterministic offline client.

Every stage must have a cheaper deterministic baseline (constitution rule 19),
and the pipeline must be testable end to end without network access or spend.
EchoClient answers each worker with a schema-valid, content-derived response so
plumbing, caching and accounting can be verified independently of model quality.
"""

from __future__ import annotations

import hashlib
import json
import re

from ..contracts.enums import ModelTier
from .base import LLMResponse, estimate_tokens

_SENTENCE = re.compile(r"[^.!?\n]{40,400}[.!?]")


def _pick(text: str, seed: str, count: int) -> list[str]:
    """Deterministically choose sentences from the text as pseudo-findings."""
    sentences = [s.strip() for s in _SENTENCE.findall(text)]
    if not sentences:
        return []
    digest = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    chosen: list[str] = []
    for offset in range(min(count, len(sentences))):
        chosen.append(sentences[(digest + offset * 7919) % len(sentences)])
    return chosen


class EchoClient:
    """Baseline client whose output depends only on its input."""

    def __init__(self, tier: ModelTier = ModelTier.SMALL, marks_per_call: int = 2) -> None:
        self.tier = tier
        self.model_id = f"echo-{tier.lower()}"
        self.marks_per_call = marks_per_call
        self.calls = 0

    def complete(
        self, system: str, user: str, max_output_tokens: int = 1024
    ) -> LLMResponse:
        self.calls += 1
        payload = self._route(system, user)
        text = json.dumps(payload, ensure_ascii=False)
        return LLMResponse(
            text=text,
            model_id=self.model_id,
            input_tokens=estimate_tokens(system + user),
            output_tokens=estimate_tokens(text),
        )

    def _route(self, system: str, user: str) -> dict:
        seed = hashlib.sha256(user.encode()).hexdigest()
        body = user.split("<<<TEXT>>>")[-1]
        if "NAVIGATION" in system:
            picks = _pick(body, seed, 1)
            return {
                "gist": (picks[0][:120] if picks else "no salient content"),
                "salient_terms_verbatim": self._terms(body, seed, 3),
                "examples_present": " example" in body.lower(),
                "exceptions_present": "however" in body.lower() or "except" in body.lower(),
                "tables_figures_present": "figure" in body.lower() or "table" in body.lower(),
                "internal_references": [],
                "navigation_uncertainties": [],
            }
        if "MARKING" in system:
            return {
                "marks": [
                    {
                        "verbatim_anchor": anchor,
                        "why_marked": "Echo baseline selected this span deterministically.",
                        "open_codes": self._terms(anchor, seed + str(index), 2),
                        "conditions_seen": [],
                        "exceptions_seen": [],
                        "unresolved_questions": (
                            ["What observable event defines this?"] if index == 0 else []
                        ),
                        "cross_section_dependencies": [],
                    }
                    for index, anchor in enumerate(_pick(body, seed, self.marks_per_call))
                ]
            }
        if "CLAIM_EXTRACTION" in system:
            return {
                "claims": [
                    {
                        "source_statement": anchor,
                        "normalized_claim": anchor[:200],
                        "epistemic_act": "PRESCRIPTIVE" if " should " in anchor else "OBSERVED",
                        "modality": "USUALLY",
                        "conditions": [],
                        "exceptions": [],
                        "population_scope": None,
                    }
                    for anchor in _pick(body, seed, 1)
                ]
            }
        if "VERIFICATION" in system:
            # The claim must actually appear in the presented evidence.
            claim = self._between(user, "<<<CLAIM>>>", "<<<EVIDENCE>>>").strip()
            evidence = user.split("<<<EVIDENCE>>>")[-1]
            entailed = bool(claim) and claim[:60].lower() in evidence.lower()
            return {
                "entailed": entailed,
                "modality_preserved": entailed,
                "scope_supported": entailed,
                "conditions_complete": entailed,
                "requires_reread": not entailed,
                "notes": "echo baseline substring entailment",
            }
        if "CHAPTER_SYNTHESIS" in system:
            return {
                "chapter_findings": _pick(body, seed, 1),
                "incomplete_sections": [],
                "argument_summary": (_pick(body, seed, 1) or [""])[0][:200],
            }
        if "REREAD" in system:
            picks = _pick(body, seed, 1)
            return {
                "status": "RESOLVED" if picks else "UNRESOLVABLE_IN_SOURCE",
                "answer": picks[0] if picks else "The supplied source text does not answer the question.",
                "evidence_anchors": picks,
                "note": "echo baseline selected an exact source sentence",
            }
        if "V8_MAPPING" in system:
            return {"relation": "NO_IMPACT", "rationale": "echo baseline abstains", "confidence": 0.0}
        return {"result": None}

    @staticmethod
    def _between(text: str, start: str, end: str) -> str:
        if start not in text:
            return ""
        tail = text.split(start, 1)[1]
        return tail.split(end, 1)[0] if end in tail else tail

    @staticmethod
    def _terms(text: str, seed: str, count: int) -> list[str]:
        words = sorted({w for w in re.findall(r"[a-z]{6,}", text.lower())})
        if not words:
            return []
        digest = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        return [words[(digest + i * 31) % len(words)] for i in range(min(count, len(words)))]
