"""Source parsing to text with page coordinates.

Stdlib-first: .txt and .epub need no third-party dependency at all, and PDF
extraction shells out to pdftotext when available. A parse failure is recorded
rather than silently producing empty text -- a source that failed to parse must
show up as BLOCKED_MISSING_SOURCE, not as a source with no findings.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from ..ids import sha256_hex

#: pdftotext emits form feed between pages; this is how page coordinates survive.
PAGE_BREAK = "\f"


@dataclass
class ParsedDocument:
    text: str
    page_offsets: list[int] = field(default_factory=list)
    source_kind: str = "text"
    page_count: int = 0
    parse_ok: bool = True
    parse_error: str = ""

    @property
    def text_sha256(self) -> str:
        return sha256_hex(self.text)

    def page_at(self, char_offset: int) -> int | None:
        """1-based page number containing a character offset."""
        if not self.page_offsets:
            return None
        lo, hi = 0, len(self.page_offsets) - 1
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.page_offsets[mid] <= char_offset:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best + 1


def _page_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == PAGE_BREAK:
            offsets.append(index + 1)
    return offsets


def parse_txt(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    offsets = _page_offsets(text)
    return ParsedDocument(text, offsets, "txt", len(offsets))


def parse_pdf(path: Path) -> ParsedDocument:
    if shutil.which("pdftotext") is None:
        return ParsedDocument("", [], "pdf", 0, False, "pdftotext not installed")
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            timeout=600,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return ParsedDocument("", [], "pdf", 0, False, f"pdftotext failed: {exc}")
    if result.returncode != 0:
        return ParsedDocument(
            "", [], "pdf", 0, False, result.stderr.decode("utf-8", "replace")[:400]
        )
    text = result.stdout.decode("utf-8", "replace")
    offsets = _page_offsets(text)
    return ParsedDocument(text, offsets, "pdf", len(offsets), bool(text.strip()))


_TAG = re.compile(r"<[^>]+>")
_BLOCK_END = re.compile(r"</(p|div|h[1-6]|li|br)\s*>", re.I)


def parse_epub(path: Path) -> ParsedDocument:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [
                n
                for n in archive.namelist()
                if n.lower().endswith((".xhtml", ".html", ".htm"))
            ]
            names.sort()
            chunks: list[str] = []
            offsets: list[int] = []
            cursor = 0
            for name in names:
                raw = archive.read(name).decode("utf-8", "replace")
                body = _BLOCK_END.sub("\n", raw)
                body = _TAG.sub("", body)
                body = html.unescape(body)
                body = re.sub(r"\n{3,}", "\n\n", body).strip()
                if not body:
                    continue
                offsets.append(cursor)
                chunk = body + "\n" + PAGE_BREAK
                chunks.append(chunk)
                cursor += len(chunk)
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        return ParsedDocument("", [], "epub", 0, False, f"epub read failed: {exc}")
    text = "".join(chunks)
    return ParsedDocument(text, offsets, "epub", len(offsets), bool(text.strip()))


PARSERS = {
    ".txt": parse_txt,
    ".text": parse_txt,
    ".md": parse_txt,
    ".pdf": parse_pdf,
    ".epub": parse_epub,
}


def parse(path: Path) -> ParsedDocument:
    parser = PARSERS.get(path.suffix.lower())
    if parser is None:
        return ParsedDocument(
            "", [], path.suffix.lstrip("."), 0, False, f"no parser for {path.suffix}"
        )
    return parser(path)
