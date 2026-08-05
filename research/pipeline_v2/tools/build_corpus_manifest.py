#!/usr/bin/env python3
"""research_pipeline_v2.0 — corpus manifest builder.

Input:  books/_extracted/<slug>.txt  (master text per book, produced by the
        extraction pipeline: pdftotext / OCR / epub / mobi).
Output: research/pipeline_v2/corpus/books_manifest.json  + regenerated parts
        under books/_extracted/_parts/<slug>__pN.txt (full text, consistent
        chunking — no truncation, narratives included in full).

Every book and every part is integrity-checked (sha256). A book's parts are
the authoritative input to claim scouting; a part never overlaps another and
the concatenation in order equals the master text (up to paragraph-boundary
chunking, which may drop the boundary whitespace only).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = '/Users/hootie/src/v8'
BOOKS = os.path.join(ROOT, 'books')
EXTRACTED = os.path.join(BOOKS, '_extracted')
PARTS = os.path.join(EXTRACTED, '_parts')
OUT_DIR = os.path.join(ROOT, 'research', 'pipeline_v2', 'corpus')
CHUNK = 320_000

# source_kind per format from the canonical list
FMT_KIND = {'pdf': 'pdf', 'epub': 'epub', 'mobi': 'mobi', 'azw': 'mobi'}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: str) -> str:
    return sha256_bytes(open(p, 'rb').read())


def slugify(title: str) -> str:
    s = re.sub(r'\.(pdf|epub|mobi|azw)$', '', title, flags=re.I)
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:120] or 'untitled'


def split_text(text: str, chunk: int):
    parts = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + chunk, n)
        if end < n:
            cut = text.rfind('\n\n', max(start, end - 8000), end)
            if cut > start:
                end = cut + 2
        parts.append(text[start:end])
        start = end
    return parts


def pdf_pages(src: str) -> int | None:
    if not src.lower().endswith('.pdf'):
        return None
    try:
        r = subprocess.run(['pdfinfo', src], capture_output=True, text=True, timeout=30)
        for line in r.stdout.splitlines():
            if line.lower().startswith('pages'):
                v = line.split(':', 1)[1].strip()
                return int(v) if v.isdigit() else None
    except Exception:
        return None
    return None


def main() -> None:
    os.makedirs(PARTS, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    # canonical unique-book list (from the dedupe step)
    canon = json.load(open('/tmp/v8books_canonical.json'))['books']

    manifest = []
    for i, b in enumerate(sorted(canon, key=lambda x: x['key']), 1):
        src = os.path.join(BOOKS, b['source_file'])
        slug = slugify(b['display_title'])
        master = os.path.join(EXTRACTED, slug + '.txt')
        if not os.path.exists(master):
            # book could not be extracted at all -> record as BLOCKED
            manifest.append({
                'book_id': f'book_{i:04d}',
                'title': b['display_title'],
                'source_file': b['source_file'],
                'source_sha256': sha256_file(src) if os.path.exists(src) else None,
                'source_kind': FMT_KIND.get(b['format'], 'unknown'),
                'page_count': pdf_pages(src),
                'status': 'EXTRACTION_BLOCKED',
            })
            continue
        text = open(master, encoding='utf-8', errors='replace').read()
        if len(text) < 3000:
            manifest.append({
                'book_id': f'book_{i:04d}',
                'title': b['display_title'],
                'source_file': b['source_file'],
                'source_sha256': sha256_file(src) if os.path.exists(src) else None,
                'source_kind': FMT_KIND.get(b['format'], 'unknown'),
                'page_count': pdf_pages(src),
                'text_chars': len(text),
                'status': 'TEXT_UNUSABLE',
            })
            continue

        # regenerate consistent full-text parts
        parts = split_text(text, CHUNK)
        part_recs = []
        for j, part in enumerate(parts, 1):
            part_path = os.path.join(PARTS, f'{slug}__p{j}.txt')
            with open(part_path, 'w') as f:
                f.write(part)
            pb = part.encode('utf-8')
            part_recs.append({
                'part_id': f'{slug}__p{j}',
                'order': j,
                'path': part_path.replace(ROOT + '/', ''),
                'chars': len(part),
                'bytes': len(pb),
                'sha256': sha256_bytes(pb),
                'token_estimate': len(pb) // 4,
                'page_start': None,
                'page_end': None,
            })

        work_id = re.sub(r'[-_]+', '_', slug).strip('_')
        manifest.append({
            'book_id': f'book_{i:04d}',
            'work_id': work_id,
            'edition_id': f'{work_id}_{b["year"] or "x"}',
            'title': b['display_title'],
            'edition': b['year'],
            'language': 'en',
            'source_file': b['source_file'],
            'source_sha256': sha256_file(src) if os.path.exists(src) else None,
            'source_kind': FMT_KIND.get(b['format'], 'unknown'),
            'page_count': pdf_pages(src),
            'text_sha256': sha256_file(master),
            'text_chars': len(text),
            'n_parts': len(part_recs),
            'parts': part_recs,
            'processing_status': {'ingestion': 'complete', 'structural_map': 'pending',
                                  'extraction': 'pending', 'audit': 'pending'},
        })

    out = {
        'pipeline_version': 'research_pipeline_v2.0',
        'generated_at': '2026-08-02',
        'corpus_root': 'books/_extracted/',
        'books': manifest,
    }
    out_path = os.path.join(OUT_DIR, 'books_manifest.json')
    json.dump(out, open(out_path, 'w'), indent=1)
    n = len(manifest)
    n_ok = sum(1 for b in manifest if b.get('parts'))
    n_blocked = n - n_ok
    tot_chars = sum(b['text_chars'] for b in manifest if b.get('text_chars'))
    print(f'corpus manifest: {n} books ({n_ok} usable, {n_blocked} blocked)')
    print(f'total text chars: {tot_chars:,}  -> {tot_chars // 4:,} token estimate')
    print(f'parts written under {PARTS}')
    print(f'manifest: {out_path}')


if __name__ == '__main__':
    main()
