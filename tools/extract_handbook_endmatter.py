#!/usr/bin/env python3
"""Extract the non-chapter end matter into a resumable review artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()

    pages = args.text.read_text(encoding="utf-8").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    # Printed pages 923–end correspond to physical pages 949–980.
    start, end, offset = 949, len(pages), 26
    chunks: list[str] = []
    for physical_page in range(start, end + 1):
        chunks.append(
            f"\n\n===== PHYSICAL PAGE {physical_page} / PRINTED PAGE {physical_page - offset} =====\n\n"
        )
        chunks.append(pages[physical_page - 1])
    output = args.workdir / "source" / "endmatter.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(chunks), encoding="utf-8")
    checkpoint = args.workdir / "checkpoints" / "endmatter_state.json"
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": "v8-handbook-endmatter-v0.1",
                "phase": "ENDMATTER_EXTRACTED",
                "physical_page_start": start,
                "physical_page_end": end,
                "printed_page_start": start - offset,
                "printed_page_end": end - offset,
                "updated_at": now(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "pages": end - start + 1}, indent=2))


if __name__ == "__main__":
    main()
