"""Modality preservation check.

A verifier must reject a claim whose modality is stronger than its evidence
(cheap executable test #8). This module owns the deterministic half of that
check: keyword evidence for how strongly the source itself hedges, independent
of what the extractor claimed.
"""

from __future__ import annotations

import re

from ..contracts.enums import MODALITY_RANK, Modality

_HEDGE_TERMS: list[tuple[re.Pattern[str], Modality]] = [
    (re.compile(r"\bmust\b|\balways\b|\bnever\b", re.I), Modality.MUST),
    (re.compile(r"\btypically\b|\busually\b|\bgenerally\b", re.I), Modality.USUALLY),
    (re.compile(r"\boften\b|\bfrequently\b", re.I), Modality.OFTEN),
    (re.compile(r"\bsometimes\b|\boccasionally\b", re.I), Modality.SOMETIMES),
    (re.compile(r"\bmay\b|\bmight\b|\bcan\b|\bcould\b", re.I), Modality.MAY),
]


def evidence_modality_ceiling(evidence_text: str) -> Modality:
    """The strongest modality the evidence text's own language supports.

    Absent any hedge word, ALWAYS is not assumed -- USUALLY is the ceiling,
    matching the specification's default and avoiding a silent upgrade to a
    universal claim the source never made.
    """
    for pattern, modality in _HEDGE_TERMS:
        if pattern.search(evidence_text):
            return modality
    return Modality.USUALLY


def modality_preserved(claimed: Modality, evidence_text: str) -> bool:
    ceiling = evidence_modality_ceiling(evidence_text)
    return MODALITY_RANK[claimed] <= MODALITY_RANK[ceiling]
