#!/usr/bin/env python3
"""Merge per-job triage files into per-book claims.jsonl (v2.1, A2/A2b scope).

Lead-triage decisions are JOINED with the lead passages (anchor_text,
section_id, page) from leads_v21/<book_id>.jsonl. Section-triage claims (A1,
partial) are kept as-is. DROP records go to rejected_leads.jsonl; only
route != DROP records land in claims.jsonl.
"""
from __future__ import annotations

import glob
import json
import os

ROOT = '/Users/hootie/src/v8'
PB = os.path.join(ROOT, 'research/pipeline_v2/processed_books')
LEADS = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads_v21')


def main() -> int:
    total_claims = 0
    total_rejected = 0
    for book_dir in sorted(glob.glob(os.path.join(PB, 'book_*'))):
        bid = os.path.basename(book_dir)

        # lead index for joining anchors
        lead_index = {}
        lfp = os.path.join(LEADS, bid + '.jsonl')
        if os.path.exists(lfp):
            for l in open(lfp):
                d = json.loads(l)
                lead_index[d['lead_id']] = d

        claims = []
        rejected = []

        # A1 section triage claims (partial or absent)
        for fp in sorted(glob.glob(os.path.join(book_dir, 'triage_sections', '*.jsonl'))):
            for l in open(fp):
                l = l.strip()
                if not l:
                    continue
                rec = json.loads(l)
                rec['_source'] = 'section'
                (rejected if rec.get('route') == 'DROP' else claims).append(rec)

        # A2/A2b lead triage decisions joined with lead passages
        for fp in sorted(glob.glob(os.path.join(book_dir, 'triage_leads', '*.jsonl'))):
            for l in open(fp):
                l = l.strip()
                if not l:
                    continue
                rec = json.loads(l)
                lead = lead_index.get(rec.get('lead_id')) or {}
                joined = {
                    '_source': 'lead',
                    'claim_id': f"{bid}::{rec.get('lead_id')}",
                    'lead_id': rec.get('lead_id'),
                    'route': rec.get('route'),
                    'claim_type': rec.get('claim_type'),
                    'drop_reason': rec.get('drop_reason'),
                    'needs_wider_context': rec.get('needs_wider_context'),
                    'carries_quantity': rec.get('carries_quantity'),
                    'confidence': rec.get('confidence'),
                    'anchor_text': lead.get('anchor_text'),
                    'section_id': lead.get('section_id'),
                    'page_start': lead.get('page_start'),
                    'page_end': lead.get('page_end'),
                }
                (rejected if rec.get('route') == 'DROP' else claims).append(joined)

        if not claims and not rejected:
            continue
        with open(os.path.join(book_dir, 'claims.jsonl'), 'w') as f:
            for c in claims:
                f.write(json.dumps(c, ensure_ascii=False) + '\n')
        with open(os.path.join(book_dir, 'rejected_leads.jsonl'), 'w') as f:
            for r in rejected:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        total_claims += len(claims)
        total_rejected += len(rejected)
        print(f'{bid}: {len(claims)} claims, {len(rejected)} rejected')
    print(f'\nTOTAL: {total_claims} claims, {total_rejected} rejected')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
