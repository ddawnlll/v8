#!/usr/bin/env python3
"""Build a resumable, page-addressable index for the V8 technical-analysis book review.

The PDF text extraction is intentionally kept as a separate source artifact. This
script only derives small JSON checkpoints from that immutable extraction so a
review can resume after an interrupted session without re-reading the whole book.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOPIC_PATTERNS = {
    "strategy": r"\b(strategy|strategies|trading system|entry|breakout|reversal|trend following|mean reversion)\b",
    "market_state": r"\b(market phase|market state|trend|volatility|volume|open interest|breadth|sentiment|cycle|relative strength|momentum|regime)\b",
    "risk": r"\b(risk|drawdown|exposure|leverage|capital|money management|position sizing|risk profile)\b",
    "position_management": r"\b(position|stoploss|stop loss|target|exit|trailing|hedg|scale|pyramid|participat)\b",
    "validation": r"\b(testing|optimization|overfitting|performance measurement|expectancy|profit factor|backtest|sample)\b",
    "visual_structure": r"\b(chart|pattern|candlestick|fibonacci|ichimoku|market profile|point-and-figure|figure|table)\b",
}

CHAPTER_RE = re.compile(r"^\s*(?:CHAPTER|Chapter)\s+(\d+)\s+(.+?)\s*$")
SUBSECTION_RE = re.compile(r"^\s*(\d+\.\d+)\s+(.+?)\s*$")

PRINTED_CHAPTER_STARTS = [
    (1, "Introduction to the Art and Science of Technical Analysis", 1),
    (2, "Introduction to Dow Theory", 45),
    (3, "Mechanics and Dynamics of Charting", 65),
    (4, "Market Phase Analysis", 99),
    (5, "Trend Analysis", 125),
    (6, "Volume and Open Interest", 173),
    (7, "Bar Chart Analysis", 209),
    (8, "Window Oscillators and Overlay Indicators", 235),
    (9, "Divergence Analysis", 267),
    (10, "Fibonacci Number and Ratio Analysis", 357),
    (11, "Moving Averages", 433),
    (12, "Envelopes and Methods of Price Containment", 465),
    (13, "Chart Pattern Analysis", 495),
    (14, "Japanese Candlestick Analysis", 541),
    (15, "Point-and-Figure Charting", 589),
    (16, "Ichimoku Charting and Analysis", 627),
    (17, "Market Profile", 651),
    (18, "Basic Elliott Wave Analysis", 673),
    (19, "Basics of Gann Analysis", 687),
    (20, "Cycle Analysis", 713),
    (21, "Volatility Analysis", 733),
    (22, "Market Breadth", 759),
    (23, "Sentiment Indicators and Contrary Opinion", 779),
    (24, "Relative Strength Analysis", 793),
    (25, "Investor Psychology", 813),
    (26, "Trader Risk Profiling and Position Analysis", 825),
    (27, "Integrated Technical Analysis", 849),
    (28, "Money Management", 879),
    (29, "Technical Trading Systems", 913),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": now(), **event}, ensure_ascii=False) + "\n")


def load_state(path: Path, source_hash: str, page_count: int) -> dict[str, Any]:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("source_sha256") != source_hash:
            raise SystemExit("source hash changed; use a new workdir or remove the stale checkpoint")
        return state
    state = {
        "schema_version": "v8-handbook-index-v0.1",
        "source_sha256": source_hash,
        "page_count": page_count,
        "created_at": now(),
        "updated_at": now(),
        "phase": "INDEXING",
        "last_completed_batch": 0,
        "completed_batches": [],
        "outputs": [],
    }
    write_json(path, state)
    return state


def page_record(number: int, text: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in text.splitlines()]
    nonempty = [line.strip() for line in lines if line.strip()]
    joined = " ".join(nonempty)
    headings: list[dict[str, str]] = []
    for line in nonempty:
        match = CHAPTER_RE.match(line) or SUBSECTION_RE.match(line)
        if match:
            headings.append({"id": match.group(1), "title": match.group(2).strip()})
    topic_hits = {
        topic: len(re.findall(pattern, joined, flags=re.IGNORECASE))
        for topic, pattern in TOPIC_PATTERNS.items()
    }
    return {
        "page": number,
        "chars": len(text),
        "lines": len(lines),
        "first_text": nonempty[0][:240] if nonempty else "",
        "last_text": nonempty[-1][:240] if nonempty else "",
        "headings": headings,
        "topic_hits": topic_hits,
        "has_visual_terms": topic_hits["visual_structure"] > 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    text = args.text.read_text(encoding="utf-8")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    source_hash = sha256(args.source)
    checkpoints = args.workdir / "checkpoints"
    state_path = checkpoints / "state.json"
    events_path = checkpoints / "events.jsonl"
    state = load_state(state_path, source_hash, len(pages))

    page_index_path = checkpoints / "page_index.json"
    page_index: list[dict[str, Any]] = []
    if page_index_path.exists():
        page_index = json.loads(page_index_path.read_text(encoding="utf-8"))
    indexed_pages = {record["page"] for record in page_index}

    start = max(0, int(state.get("last_completed_batch", 0)) * args.batch_size)
    for batch_start in range(start, len(pages), args.batch_size):
        batch_number = batch_start // args.batch_size + 1
        records = [
            page_record(number, pages[number - 1])
            for number in range(batch_start + 1, min(batch_start + args.batch_size, len(pages)) + 1)
            if number not in indexed_pages
        ]
        page_index.extend(records)
        page_index.sort(key=lambda record: record["page"])
        write_json(page_index_path, page_index)

        batch_path = checkpoints / f"batch_{batch_number:04d}.json"
        write_json(
            batch_path,
            {
                "schema_version": "v8-handbook-index-batch-v0.1",
                "source_sha256": source_hash,
                "batch": batch_number,
                "page_start": batch_start + 1,
                "page_end": min(batch_start + args.batch_size, len(pages)),
                "records": records,
            },
        )
        state["last_completed_batch"] = batch_number
        state["completed_batches"] = sorted(set(state.get("completed_batches", [])) | {batch_number})
        state["updated_at"] = now()
        state["outputs"] = sorted(set(state.get("outputs", [])) | {"page_index.json", batch_path.name})
        write_json(state_path, state)
        append_event(events_path, {"event": "batch_completed", "batch": batch_number, "pages": len(records)})

    # The printed chapter pages are stable in the contents (the PDF has 26
    # front-matter pages before printed page 1). Avoid OCR/foreword references
    # such as "Chapter 1" and keep both printed and physical page numbers.
    page_offset = 26
    chapters = [
        {
            "chapter": chapter,
            "title": title,
            "printed_page_start": printed_page,
            "page_start": printed_page + page_offset,
            "page_offset": page_offset,
        }
        for chapter, title, printed_page in PRINTED_CHAPTER_STARTS
    ]
    for current, following in zip(chapters, chapters[1:]):
        current["page_end"] = following["page_start"] - 1
    if chapters:
        # The printed chapter list ends at page 920.  Physical pages 949 onward
        # are Appendix A/B, the test-bank note, and the index; keeping them out
        # of Chapter 29 is essential for a chapter-faithful review.
        chapters[-1]["page_end"] = chapters[-1]["printed_page_start"] + page_offset + 7
    write_json(checkpoints / "chapter_map.json", chapters)

    topic_pages = {
        topic: [record["page"] for record in page_index if record["topic_hits"][topic] > 0]
        for topic in TOPIC_PATTERNS
    }
    write_json(checkpoints / "topic_pages.json", topic_pages)
    state.update({"phase": "INDEXED", "updated_at": now(), "outputs": sorted(set(state["outputs"]) | {"chapter_map.json", "topic_pages.json"})})
    write_json(state_path, state)
    append_event(events_path, {"event": "index_completed", "page_count": len(pages), "chapter_count": len(chapters)})
    print(json.dumps({"page_count": len(pages), "chapter_count": len(chapters), "last_completed_batch": state["last_completed_batch"]}, indent=2))


if __name__ == "__main__":
    main()
