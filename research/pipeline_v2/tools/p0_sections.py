#!/usr/bin/env python3
"""P0.2 — section re-chunk (deterministic, 0 LLM calls).

Parts (~80k tokens) are too coarse for "prev-tail + current + next-head"
context. Split each part into sections of ~4-8k tokens, aligned to heading-like
lines and paragraph breaks. Section char ranges tile the part exactly
(coverage == 1.0 is the gate). Page ranges are derived from the P0.1 pagemap.

Output: corpus/sections/<book_id>.sections.jsonl
"""
from __future__ import annotations

import json
import os
import re

ROOT = '/Users/hootie/src/v8'
MANIFEST = os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.v21.json')
PAGES_OUT = os.path.join(ROOT, 'research/pipeline_v2/corpus/pages')
SECTIONS_OUT = os.path.join(ROOT, 'research/pipeline_v2/corpus/sections')
MIN_TOK = 1800          # don't cut below this many tokens
TARGET_TOK = 5500       # aim for this many tokens per section (bytes/4)
MAX_TOK = 8000

HEADING_RE = re.compile(
    r'^\s*((CHAPTER|CHAPTERS|PART|SECTION|LESSON|MODULE|APPENDIX|SESSION|LESSON)\s+[0-9IVXLC]+'
    r'|(\d+(\.\d+)*)[\s\.\):]'
    r'|[A-Z][A-Z\s\-\'\&,]{8,60}$)'
)


def tok_est(text: str) -> int:
    return len(text.encode('utf-8')) // 4


def page_of(pagemap: list[dict], char_pos: int) -> int | None:
    for p in pagemap:
        if p['char_start'] <= char_pos <= p['char_end']:
            return p['page']
    return None


def sectionize(part_path: str, pagemap: list[dict]) -> list[dict]:
    with open(part_path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    lines = text.split('\n')
    sections = []
    cur_start = 0
    cur_tok = 0
    n = len(lines)

    def emit(end_line: int):
        nonlocal cur_start, cur_tok
        char_start = sum(len(l) + 1 for l in lines[:cur_start])
        char_end = sum(len(l) + 1 for l in lines[:end_line + 1])
        seg = '\n'.join(lines[cur_start:end_line + 1])
        sections.append({
            'char_start': char_start,
            'char_end': char_end,
            'line_start': cur_start,
            'line_end': end_line,
            'token_estimate': tok_est(seg),
            'page_start': page_of(pagemap, char_start),
            'page_end': page_of(pagemap, char_end),
        })
        cur_start = end_line + 1
        cur_tok = 0

    i = 0
    while i < n:
        line = lines[i]
        cur_tok += tok_est(line) or 1
        # candidate cut: heading line OR paragraph boundary, at or past MIN_TOK
        if cur_tok >= MIN_TOK and i < n - 1:
            is_heading = bool(HEADING_RE.match(line))
            is_para = (line.strip() == '' and i + 1 < n and lines[i + 1].strip() != '')
            if (is_heading or is_para) and cur_tok >= TARGET_TOK:
                emit(i - (1 if is_para and i > cur_start else 0))
                i += 1
                continue
            if cur_tok >= MAX_TOK:
                emit(i)
                i += 1
                continue
        i += 1
    if cur_start <= n - 1:
        emit(n - 1)
    return sections


def main() -> int:
    os.makedirs(SECTIONS_OUT, exist_ok=True)
    manifest = json.load(open(MANIFEST))
    total_sections = 0
    coverage_fail = []
    for book in manifest['books']:
        if not book.get('parts'):
            continue
        all_sections = []
        order = 0
        for part in book['parts']:
            part_path = os.path.join(ROOT, part['path'])
            with open(part_path, encoding='utf-8', errors='replace') as _f:
                part_chars = len(_f.read())
            pm_path = os.path.join(PAGES_OUT, part['part_id'] + '.pagemap.json')
            pagemap = json.load(open(pm_path)) if os.path.exists(pm_path) else []
            segs = sectionize(part_path, pagemap)
            prev = None
            for s in segs:
                sid = f"{book['book_id']}__p{part['order']}__s{order:03d}"
                rec = {
                    'section_id': sid,
                    'book_id': book['book_id'],
                    'part_id': part['part_id'],
                    'order': order,
                    'prev_section_id': prev,
                    'next_section_id': None,
                    **s,
                }
                if prev:
                    for pr in reversed(all_sections):
                        if pr['section_id'] == prev:
                            pr['next_section_id'] = sid
                            break
                all_sections.append(rec)
                prev = sid
                order += 1
            # coverage gate: last section of this part must reach part end (±2 for trailing newline)
            if segs and abs(segs[-1]['char_end'] - part_chars) > 2:
                coverage_fail.append((book['book_id'], part['part_id'], segs[-1]['char_end'], part_chars))
        total_sections += len(all_sections)
        with open(os.path.join(SECTIONS_OUT, book['book_id'] + '.sections.jsonl'), 'w') as f:
            for s in all_sections:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')

    print(f'sections built: {total_sections} across {len(manifest["books"])} books')
    print(f'coverage gate: {len(coverage_fail)} part mismatches')
    for c in coverage_fail[:8]:
        print('  FAIL', c)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
