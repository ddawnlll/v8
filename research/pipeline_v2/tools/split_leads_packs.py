#!/usr/bin/env python3
"""research_pipeline_v2.0 — split per-book leads into extractor packs.

Deterministic. Each pack holds up to LEAD_PACK_SIZE leads from one book and is
written to corpus/leads_packs/<pack_id>.jsonl. Also emits a packs manifest and
computes the deterministic v1-recall coverage (how many v1 strategy mentions
appear inside at least one lead's anchor text).
"""
from __future__ import annotations

import json
import os

ROOT = '/Users/hootie/src/v8'
LEADS = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads')
PACKS = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads_packs')
LEAD_PACK_SIZE = 60


def main() -> int:
    os.makedirs(PACKS, exist_ok=True)
    manifest = {'pipeline_version': 'research_pipeline_v2.0', 'pack_size': LEAD_PACK_SIZE, 'packs': [], 'packs_b': []}
    n_leads = 0
    n_packs = 0
    for fn in sorted(os.listdir(LEADS)):
        if not fn.endswith('.jsonl'):
            continue
        book_id = fn[:-6]
        leads = [json.loads(l) for l in open(os.path.join(LEADS, fn), encoding='utf-8') if l.strip()]
        n_leads += len(leads)
        for i in range(0, len(leads), LEAD_PACK_SIZE):
            chunk = leads[i:i + LEAD_PACK_SIZE]
            pack_id = f'{book_id}__pack{i // LEAD_PACK_SIZE + 1:02d}'
            path = os.path.join(PACKS, pack_id + '.jsonl')
            with open(path, 'w') as f:
                for l in chunk:
                    f.write(json.dumps(l, ensure_ascii=False) + '\n')
            manifest['packs'].append({
                'pack_id': pack_id, 'book_id': book_id, 'path': path,
                'n_leads': len(chunk),
                'n_high': sum(1 for l in chunk if l['priority'] == 'high'),
            })
            n_packs += 1
        # extractor-B packs: high-priority leads only
        high = [l for l in leads if l['priority'] == 'high']
        for i in range(0, len(high), LEAD_PACK_SIZE):
            chunk = high[i:i + LEAD_PACK_SIZE]
            pack_id = f'{book_id}__bh{i // LEAD_PACK_SIZE + 1:02d}'
            path = os.path.join(PACKS, pack_id + '.jsonl')
            with open(path, 'w') as f:
                for l in chunk:
                    f.write(json.dumps(l, ensure_ascii=False) + '\n')
            manifest['packs_b'].append({
                'pack_id': pack_id, 'book_id': book_id, 'path': path,
                'n_leads': len(chunk),
            })

    json.dump(manifest, open(os.path.join(ROOT, 'research/pipeline_v2/corpus/leads_packs_manifest.json'), 'w'), indent=1)
    n_b = len(manifest['packs_b'])
    print(f'{n_leads} leads -> {n_packs} A-packs + {n_b} B-packs (high-only, batch {LEAD_PACK_SIZE})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
