"""Heading recovery and the document node tree.

`heading_path` is the field that makes "locate, then read continuously"
possible: without it a multi-section reconstruction cannot tell which sections
belong to the same argument. Recovery is heuristic and deliberately
conservative -- a missed heading costs granularity, a false heading splits an
argument in half.
"""

from __future__ import annotations

import re

from ..ids import derive_id, range_hash
from ..contracts.structure import DocumentNode
from ..contracts.enums import NodeType
from .parse import PAGE_BREAK, ParsedDocument

_ORDINAL_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    "fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
)
#: The divider must be followed by a real enumerator. An earlier version allowed
#: any word here, which turned prose like "book based on lectures..." into a
#: chapter and inflated the chapter count roughly fivefold.
CHAPTER_PATTERNS = [
    re.compile(
        rf"^\s*(chapter|part|book|section)\s+(\d{{1,3}}|[ivxlcdm]{{1,7}}|{_ORDINAL_WORDS})"
        r"\b\s*[:.—-]?\s*(.{0,80})$",
        re.I,
    ),
    re.compile(
        r"^\s*(appendix|preface|foreword|introduction|epilogue|glossary|"
        r"acknowledg(?:e)?ments|bibliography|index|notes)\s*$",
        re.I,
    ),
]
NUMBERED_HEADING = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){1,3})\s+(\S.{2,90})$")
MAX_HEADING_WORDS = 14
MAX_HEADING_CHARS = 90

CROSS_REFERENCE = re.compile(
    r"\b(?:see|as (?:discussed|described|shown|noted)|refer to|in)\s+"
    r"(chapter|section|part|appendix|figure|table)\s+([0-9]+(?:\.[0-9]+)*|[ivxlc]+)\b",
    re.I,
)
FIGURE_TABLE = re.compile(r"\b(figure|table|exhibit)\s+([0-9]+(?:[.\-][0-9]+)?)", re.I)


def _looks_like_prose(text: str) -> bool:
    """Reject sentence-shaped lines that happen to start with a heading word."""
    if text.count(" ") > MAX_HEADING_WORDS:
        return True
    body = text.rstrip()
    return body.endswith((",", ";", "and", "the", "of", "that", "which")) or (
        "." in body[:-1] and body.count(" ") > 6
    )


def _is_heading(line: str) -> tuple[bool, int]:
    """Return (is_heading, level). Level 1 = chapter, 2 = section."""
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_HEADING_CHARS:
        return False, 0
    if _looks_like_prose(stripped):
        return False, 0
    for pattern in CHAPTER_PATTERNS:
        if pattern.match(stripped):
            return True, 1
    if NUMBERED_HEADING.match(stripped):
        depth = stripped.split()[0].count(".") + 1
        return True, min(depth + 1, 4)
    words = stripped.split()
    if len(words) <= MAX_HEADING_WORDS and stripped == stripped.upper():
        letters = [c for c in stripped if c.isalpha()]
        if len(letters) >= 3 and not stripped.endswith((".", ",", ";", ":")):
            return True, 2
    return False, 0


def _estimate_tokens(text: str) -> int:
    # Deliberately cheap: scheduling needs a stable cost proxy, not accuracy.
    return max(1, len(text) // 4)


def build_nodes(
    source_id: str,
    source_version: str,
    document: ParsedDocument,
    min_section_chars: int = 400,
) -> tuple[list[DocumentNode], dict[str, str]]:
    """Split parsed text into an ordered SECTION tree with heading paths.

    Returns the nodes and a `node_id -> text` mapping; the text is stored
    separately so structural records stay small.
    """
    text = document.text
    if not text.strip():
        return [], {}

    lines = text.split("\n")
    line_offsets: list[int] = []
    cursor = 0
    for line in lines:
        line_offsets.append(cursor)
        cursor += len(line) + 1

    boundaries: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        clean = line.replace(PAGE_BREAK, "").strip()
        is_heading, level = _is_heading(clean)
        if is_heading:
            boundaries.append((index, level, clean))
    if not boundaries or boundaries[0][0] != 0:
        boundaries.insert(0, (0, 1, "(front matter)"))

    nodes: list[DocumentNode] = []
    texts: dict[str, str] = {}
    heading_stack: list[tuple[int, str]] = []
    order = 0

    for position, (line_index, level, heading) in enumerate(boundaries):
        end_line = (
            boundaries[position + 1][0] if position + 1 < len(boundaries) else len(lines)
        )
        char_start = line_offsets[line_index]
        char_end = (
            line_offsets[end_line] if end_line < len(line_offsets) else len(text)
        )
        body = text[char_start:char_end]
        if len(body.strip()) < min_section_chars and position + 1 < len(boundaries):
            continue

        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, heading))
        heading_path = [h for _, h in heading_stack]

        node_id = derive_id("NODE", source_id, order)
        node = DocumentNode(
            node_id=node_id,
            source_id=source_id,
            source_version=source_version,
            node_type=NodeType.CHAPTER if level == 1 else NodeType.SECTION,
            order=order,
            heading_path=heading_path,
            char_start=char_start,
            char_end=char_end,
            line_start=line_index,
            line_end=end_line,
            page_start=document.page_at(char_start),
            page_end=document.page_at(max(char_start, char_end - 1)),
            token_estimate=_estimate_tokens(body),
            content_hash=range_hash(body),
            cross_reference_targets=sorted(
                {f"{kind.lower()}:{ref}" for kind, ref in CROSS_REFERENCE.findall(body)}
            ),
            figure_table_refs=sorted(
                {f"{kind.lower()}:{ref}" for kind, ref in FIGURE_TABLE.findall(body)}
            ),
        )
        nodes.append(node)
        texts[node_id] = body
        order += 1

    for index, node in enumerate(nodes):
        node.prev_node_id = nodes[index - 1].node_id if index else None
        node.next_node_id = (
            nodes[index + 1].node_id if index + 1 < len(nodes) else None
        )
    _attach_parents(nodes)
    return nodes, texts


def _attach_parents(nodes: list[DocumentNode]) -> None:
    """Link each SECTION to the most recent CHAPTER above it."""
    current_chapter: DocumentNode | None = None
    for node in nodes:
        if node.node_type == NodeType.CHAPTER:
            current_chapter = node
            continue
        if current_chapter is not None:
            node.parent_id = current_chapter.node_id
            current_chapter.ordered_child_ids.append(node.node_id)


def chapters(nodes: list[DocumentNode]) -> list[DocumentNode]:
    return [n for n in nodes if n.node_type == NodeType.CHAPTER]


def sections_of(nodes: list[DocumentNode], chapter_id: str) -> list[DocumentNode]:
    return [n for n in nodes if n.parent_id == chapter_id]
