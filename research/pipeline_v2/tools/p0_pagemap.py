#!/usr/bin/env python3
"""P0.1 — page map from form-feed boundaries (deterministic, 0 LLM calls).

Every part file is split on the form-feed character (\\f, inserted by
pdftotext at page boundaries). Per page we record char/line spans. The sum of
pages across a book's parts is compared with the book's pdfinfo page_count;
books with >5% discrepancy are marked page_anchor_status: UNMAPPED (claims in
those books anchor by part_id + line range instead — page numbers are never
invented).

Outputs:
  corpus/pages/<part_id>.pagemap.json     [{page, char_start, char_end, line_start, line_end}]
  corpus/books_manifest.v21.json          manifest copy with page_start/page_end + page_anchor_status
"""
from __future__ import annotations

import json
import os

ROOT = '/Users/hootie/src/v8'
MANIFEST = os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.json')
PAGES_OUT = os.path.join(ROOT, 'research/pipeline_v2/corpus/pages')
V21_MANIFEST = os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.v21.json')
TOLERANCE = 0.05


def pagemap(part_path: str) -> list[dict]:
    with open(part_path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    pages = []
    char_pos = 0
    line_num = 1
    # split on \f; each piece is one page
    pieces = text.split('\f')
    for pno, piece in enumerate(pieces, 1):
        if piece:
            n_newlines = piece.count('\n')
            pages.append({
                'page': pno,
                'char_start': char_pos,
                'char_end': char_pos + len(piece),
                'line_start': line_num,
                'line_end': line_num + n_newlines,
            })
        char_pos += len(piece) + 1          # +1 for the \f itself
        line_num += piece.count('\n') + 1   # page break adds a line
    # final page without trailing \f
    if pages and pages[-1]['page'] != len(pieces):
        pages.append({'page': len(pieces), 'char_start': pages[-1]['char_end'] + 1,
                      'char_end': len(text), 'line_start': pages[-1]['line_end'] + 1,
                      'line_end': text.count('\n')})
    return pages


def main() -> int:
    os.makedirs(PAGES_OUT, exist_ok=True)
    manifest = json.load(open(MANIFEST))
    v21 = dict(manifest)
    unmapped = []
    total_pages = 0
    for book in v21['books']:
        if not book.get('parts'):
            continue
        book_pages = 0
        part_maps = {}
        for part in book['parts']:
            pm = pagemap(os.path.join(ROOT, part['path']))
            part_maps[part['part_id']] = pm
            book_pages += len(pm)
            part['page_start'] = pm[0]['page'] if pm else None
            part['page_end'] = pm[-1]['page'] if pm else None
            with open(os.path.join(PAGES_OUT, part['part_id'] + '.pagemap.json'), 'w') as f:
                json.dump(pm, f, indent=1)
        total_pages += book_pages
        pc = book.get('page_count')
        if pc and abs(book_pages - pc) / max(1, pc) > TOLERANCE:
            book['page_anchor_status'] = 'UNMAPPED'
            unmapped.append((book['book_id'], book_pages, pc))
        elif not pc:
            book['page_anchor_status'] = 'UNMAPPED'   # no ground truth
            unmapped.append((book['book_id'], book_pages, None))
        else:
            book['page_anchor_status'] = 'MAPPED'
        book['pages_detected'] = book_pages

    json.dump(v21, open(V21_MANIFEST, 'w'), indent=1)
    n_mapped = sum(1 for b in v21['books'] if b.get('page_anchor_status') == 'MAPPED')
    print(f'pagemap done: {total_pages} pages detected across {len(v21["books"])} books')
    print(f'page_anchor_status: MAPPED={n_mapped}, UNMAPPED={len(unmapped)}')
    for bid, det, ref in unmapped[:12]:
        print(f'  UNMAPPED {bid}: detected={det} pdfinfo={ref}')
    if len(unmapped) > 12:
        print(f'  ... and {len(unmapped) - 12} more')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
