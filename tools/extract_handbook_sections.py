#!/usr/bin/env python3
"""Materialize chapter text slices with per-chapter resume checkpoints."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--chapter-map", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true", help="rebuild already checkpointed chapter files")
    args = parser.parse_args()

    pages = args.text.read_text(encoding="utf-8").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    chapters = json.loads(args.chapter_map.read_text(encoding="utf-8"))
    out_dir = args.workdir / "source" / "chapters"
    checkpoint_dir = args.workdir / "checkpoints"
    state_path = checkpoint_dir / "chapter_extraction_state.json"
    events_path = checkpoint_dir / "events.jsonl"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        "schema_version": "v8-handbook-chapter-extraction-v0.1",
        "phase": "EXTRACTING_CHAPTERS",
        "completed_chapters": [],
        "updated_at": now(),
    }

    completed = set(state.get("completed_chapters", []))
    for chapter in chapters:
        number = chapter["chapter"]
        output = out_dir / f"chapter_{number:02d}.txt"
        if not args.refresh and number in completed and output.exists():
            continue
        start = chapter["page_start"]
        end = chapter["page_end"]
        chunks = []
        for physical_page in range(start, end + 1):
            if 1 <= physical_page <= len(pages):
                chunks.append(f"\n\n===== PHYSICAL PAGE {physical_page} / PRINTED PAGE {physical_page - chapter['page_offset']} =====\n\n")
                chunks.append(pages[physical_page - 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("".join(chunks), encoding="utf-8")
        completed.add(number)
        state.update({"completed_chapters": sorted(completed), "last_completed_chapter": number, "updated_at": now()})
        write_json(state_path, state)
        with events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": now(), "event": "chapter_text_completed", "chapter": number, "page_start": start, "page_end": end}, ensure_ascii=False) + "\n")

    state.update({"phase": "CHAPTERS_EXTRACTED", "updated_at": now()})
    write_json(state_path, state)
    print(json.dumps({"chapters": len(chapters), "completed": len(completed), "output_dir": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
