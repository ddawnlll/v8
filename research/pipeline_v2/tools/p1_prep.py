#!/usr/bin/env python3
"""P1 prep — extract section text files, select recall + calibration samples.

Deterministic (position-stratified, no randomness). Outputs:
  corpus/sections_text/<section_id>.txt   full section text (all sections)
  /tmp/p1_recall_sample.json              sections for the recall audit
  /tmp/p1_calib_sample.json               leads for the 5-book calibration
"""
from __future__ import annotations

import json
import os

ROOT = '/Users/hootie/src/v8'
SECTIONS = os.path.join(ROOT, 'research/pipeline_v2/corpus/sections')
SEC_TEXT = os.path.join(ROOT, 'research/pipeline_v2/corpus/sections_text')
LEADS_V21 = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads_v21')

CALIB_BOOKS = ['book_0002', 'book_0005', 'book_0018', 'book_0042', 'book_0108']
RECALL_BOOKS = {'m_dense': 'book_0038', 'x': 'book_0005', 'g': 'book_0108',
                'f': 'book_0042', 'ocr': 'book_0018'}


def main() -> int:
    os.makedirs(SEC_TEXT, exist_ok=True)
    manifest = json.load(open(os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.v21.json')))
    part_path = {}
    for b in manifest['books']:
        for p in b.get('parts', []):
            part_path[p['part_id']] = p['path']

    # extract all sections to text files + index by section_id
    all_sections = {}
    for fn in sorted(os.listdir(SECTIONS)):
        if not fn.endswith('.sections.jsonl'):
            continue
        for line in open(os.path.join(SECTIONS, fn)):
            s = json.loads(line)
            all_sections[s['section_id']] = s
            pp = part_path.get(s['part_id'])
            if not pp:
                continue
            with open(os.path.join(ROOT, pp), encoding='utf-8', errors='replace') as f:
                text = f.read()
            seg = text[s['char_start']:s['char_end']]
            with open(os.path.join(SEC_TEXT, s['section_id'] + '.txt'), 'w') as f:
                f.write(seg)
    print(f'sections text extracted: {len(all_sections)}')

    # lead line ranges per book
    lead_ranges = {}
    for bid in set(CALIB_BOOKS) | set(RECALL_BOOKS.values()):
        ranges = []
        fp = os.path.join(LEADS_V21, bid + '.jsonl')
        if os.path.exists(fp):
            for l in open(fp):
                d = json.loads(l)
                ranges.append((d['part_id'], d['local_start_line'], d['local_end_line']))
        lead_ranges[bid] = ranges

    def has_lead(s: dict) -> bool:
        return any(p == s['part_id'] and not (le < s['line_start'] or lo > s['line_end'])
                   for (p, lo, le) in lead_ranges[s['book_id']])

    # ---- recall sample: 6 books x (early-stratum, late-stratum, lead-less) ----
    recall = []
    for label, bid in RECALL_BOOKS.items():
        secs = sorted([s for s in all_sections.values() if s['book_id'] == bid],
                      key=lambda s: s['order'])
        if len(secs) < 2:
            continue
        picks = [secs[len(secs) // 3], secs[-1]]
        leadless = [s for s in secs if not has_lead(s)]
        picks.append(leadless[0] if leadless else secs[len(secs) // 2])
        seen = set()
        for s in picks:
            if s['section_id'] in seen:
                continue
            seen.add(s['section_id'])
            recall.append({'label': label, 'section_id': s['section_id'],
                           'book_id': bid,
                           'text_path': f'research/pipeline_v2/corpus/sections_text/{s["section_id"]}.txt',
                           'is_leadless': not has_lead(s)})
    json.dump(recall, open('/tmp/p1_recall_sample.json', 'w'), indent=1)
    print(f'recall sample: {len(recall)} sections')

    # ---- calibration lead sample: 8 high + 2 medium per book ----
    calib = []
    for bid in CALIB_BOOKS:
        leads = [json.loads(l) for l in open(os.path.join(LEADS_V21, bid + '.jsonl'))]
        picked = [l for l in leads if l['priority'] == 'high'][:8] + \
                 [l for l in leads if l['priority'] == 'medium'][:2]
        for l in picked:
            l['book_id'] = bid
        calib.extend(picked)
    json.dump(calib, open('/tmp/p1_calib_sample.json', 'w'), indent=1)
    print(f'calibration lead sample: {len(calib)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
