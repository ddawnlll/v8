"""Pass B: exact evidence alignment.

Binds a claim to an exact span, not a paraphrase. If the source statement
cannot be located verbatim (allowing for minor whitespace normalisation), the
claim is not silently accepted -- it is flagged so a reread or rejection
follows, matching the "no silent inference" invariant.
"""

from __future__ import annotations

import re

from ..contracts.claim import Claim
from ..contracts.structure import DocumentNode, EvidenceSpan

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def locate_span(node: DocumentNode, node_text: str, statement: str) -> tuple[int, int] | None:
    """Find the character offsets of `statement` within `node_text`.

    Falls back to a normalised-whitespace search so quotes that survived a
    paraphrase-by-newline still align; returns None rather than guessing.
    """
    exact = node_text.find(statement)
    if exact != -1:
        return node.char_start + exact, node.char_start + exact + len(statement)

    normalized_target = _normalize(statement)
    if not normalized_target:
        return None
    normalized_text = _normalize(node_text)
    position = normalized_text.find(normalized_target)
    if position == -1:
        return None
    # Approximate back-projection: good enough for an audit trail, not exact
    # to the character in text that had heavy whitespace collapsing.
    ratio = len(node_text) / max(1, len(normalized_text))
    approx_start = int(position * ratio)
    approx_end = int((position + len(normalized_target)) * ratio)
    return node.char_start + approx_start, node.char_start + min(approx_end, len(node_text))


def align_evidence(
    claim: Claim, node: DocumentNode, node_text: str
) -> tuple[Claim, EvidenceSpan | None]:
    located = locate_span(node, node_text, claim.source_statement)
    if located is None:
        return claim, None
    char_start, char_end = located
    verbatim = node_text[
        char_start - node.char_start : char_end - node.char_start
    ]
    span = EvidenceSpan(
        span_id=EvidenceSpan.make_id(node.node_id, char_start, char_end),
        node_id=node.node_id,
        source_id=node.source_id,
        source_version=node.source_version,
        char_start=char_start,
        char_end=char_end,
        verbatim_text=verbatim,
        page=node.page_start,
    )
    if span.span_id not in claim.evidence_span_ids:
        claim.evidence_span_ids.append(span.span_id)
    return claim, span
