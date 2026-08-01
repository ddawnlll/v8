#!/usr/bin/env python3
"""Download user-supplied reading-list resources and create a provenance manifest.

SOURCE is a one-off pasted list (used once to bootstrap the corpus); the
manifest it produced lives at research/manifest/research_papers_manifest.json.
"""
from __future__ import annotations
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE = Path("/Users/hootie/.codex/attachments/bbaded32-fbd5-4908-985a-6d491b25b471/pasted-text.txt")
OUT = Path("research/papers")
MANIFEST = Path("research/manifest/research_papers_manifest.json")
OUT.mkdir(parents=True, exist_ok=True)
text = SOURCE.read_text(encoding="utf-8")
blocks = re.split(r"(?m)^(?=\d+\. \*\*)", text)
manifest: list[dict[str, object]] = []

def fetch(url: str, path: Path) -> tuple[bool, str | None]:
    try:
        req = Request(url, headers={"User-Agent": "V8-research/1.0 contact=local-research"})
        with urlopen(req, timeout=45) as response:
            body = response.read()
        if len(body) < 1024:
            return False, "response_under_1KiB"
        path.write_bytes(body)
        return True, None
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return False, f"{type(exc).__name__}: {exc}"

for block in blocks:
    match = re.match(r"(\d+)\. \*\*(.*?)\*\*", block, re.S)
    if not match:
        continue
    number, title = int(match.group(1)), " ".join(match.group(2).split())
    urls = re.findall(r"https?://[^\s)\]]+", block)
    arxiv = re.search(r"(?:arxiv\.org/(?:abs|pdf|html)/|ar5iv\.labs\.arxiv\.org/html/)(\d{4}\.\d{4,5})", block)
    identifier = arxiv.group(1) if arxiv else None
    canonical = f"https://arxiv.org/pdf/{identifier}.pdf" if identifier else (urls[0] if urls else None)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70]
    ext = ".pdf" if canonical and (identifier or ".pdf" in canonical) else ".html"
    filename = f"{number:02d}_{identifier or 'external'}_{slug}{ext}"
    record: dict[str, object] = {"list_number": number, "title": title, "urls": urls, "arxiv_id": identifier,
                                  "canonical_url": canonical, "file": str(OUT / filename), "duplicate_of": None}
    duplicate = next((r for r in manifest if identifier and r.get("arxiv_id") == identifier), None)
    if duplicate:
        record["duplicate_of"] = duplicate["list_number"]
        record["download_status"] = "DUPLICATE_REFERENCE"
    elif not canonical:
        record["download_status"] = "NO_URL"
    else:
        ok, error = fetch(canonical, OUT / filename)
        record["download_status"] = "DOWNLOADED" if ok else "UNAVAILABLE"
        record["error"] = error
        if ok:
            record["sha256"] = hashlib.sha256((OUT / filename).read_bytes()).hexdigest()
        time.sleep(0.15)
    manifest.append(record)

MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"records": len(manifest), "downloaded": sum(r["download_status"] == "DOWNLOADED" for r in manifest),
                  "duplicates": sum(r["download_status"] == "DUPLICATE_REFERENCE" for r in manifest),
                  "unavailable": sum(r["download_status"] == "UNAVAILABLE" for r in manifest)}, indent=2))
