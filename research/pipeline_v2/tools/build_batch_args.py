#!/usr/bin/env python3
"""research_pipeline_v2.0 — build batch args for corpus-wide calibration_v2 runs.

Reads the corpus manifest and emits per-batch `args` JSON files (book list with
parts) for the calibration_v2 workflow, excluding already-processed books.

usage: build_batch_args.py --batch-size 12 --exclude book_0002,book_0005,... [--out dir]
"""
from __future__ import annotations

import argparse
import json
import os


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-size', type=int, default=12)
    ap.add_argument('--exclude', default='',
                    help='comma-separated book_ids already processed')
    ap.add_argument('--out', default='research/pipeline_v2/corpus/batch_args')
    args = ap.parse_args()

    manifest = json.load(open('research/pipeline_v2/corpus/books_manifest.json'))
    exclude = {x.strip() for x in args.exclude.split(',') if x.strip()}
    books = [b for b in manifest['books']
             if b.get('parts') and b['book_id'] not in exclude]
    books.sort(key=lambda b: b['book_id'])

    os.makedirs(args.out, exist_ok=True)
    batches = []
    for i in range(0, len(books), args.batch_size):
        chunk = books[i:i + args.batch_size]
        payload = {'books': [{
            'book_id': b['book_id'],
            'title': b['title'],
            'parts': [{'order': p['order'], 'part_id': p['part_id'],
                       'path': p['path'], 'chars': p['chars']}
                      for p in b['parts']],
        } for b in chunk]}
        batch_no = i // args.batch_size + 1
        path = os.path.join(args.out, f'batch_{batch_no:03d}.json')
        json.dump(payload, open(path, 'w'), indent=1)
        total_parts = sum(len(b['parts']) for b in chunk)
        batches.append({'batch': batch_no, 'path': path, 'books': len(chunk),
                        'parts': total_parts})
        print(f'batch_{batch_no:03d}: {len(chunk)} books, {total_parts} parts -> {path}')

    print(f'\n{len(batches)} batches; {len(books)} books remaining (excluded {len(exclude)})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
