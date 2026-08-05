"""Structure-aware ingestion: parse, recover structure, detect lineage."""

from .lineage import LineageGraph, detect_edition_families, detect_same_author, possible_copies
from .parse import ParsedDocument, parse
from .structure import build_nodes, chapters, sections_of

__all__ = [
    "LineageGraph",
    "ParsedDocument",
    "build_nodes",
    "chapters",
    "detect_edition_families",
    "detect_same_author",
    "parse",
    "possible_copies",
    "sections_of",
]
