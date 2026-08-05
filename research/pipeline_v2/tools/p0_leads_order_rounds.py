#!/usr/bin/env python3
"""P0.3 + P0.4 + P0.5 — lead->section binding, density book order, round partition.

All deterministic, 0 LLM calls.
"""
from __future__ import annotations

import json
import os

ROOT = '/Users/hootie/src/v8'
MANIFEST = os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.v21.json')
LEADS = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads')
LEADS_V21 = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads_v21')
SECTIONS = os.path.join(ROOT, 'research/pipeline_v2/corpus/sections')
REGISTRY = os.path.join(ROOT, 'research/pipeline_v2/registry')

STRONG = {'ENTRY_RULE', 'TRIGGER_RULE', 'STOP_RULE', 'EXIT_RULE', 'INVALIDATION',
          'POSITION_SIZING', 'RISK_RULE', 'EMPIRICAL_CLAIM', 'METHODOLOGY'}

LINEAGES = {
    'dow_magee': ['technical analysis of stock trends', 'technical analysis and stock market profits',
                  'technical analysis of the financial markets', 'technical analysis explained'],
    'wyckoff_volume': ['volume price analysis'],
    'candlestick': ['candlestick course', 'japanese candlestick', 'beyond candlesticks', 'candlestick charting'],
    'elliott_gann': ['harmonic trading', 'timing solutions', 'alchemy of finance'],
    'quant_academic': ['evidence-based technical', 'algorithmic trading', 'fooled by randomness',
                       'random walk', 'dual momentum', 'option volatility'],
    'microstructure': ['inside the currency market', 'currency trading and intermarket', 'trading etfs'],
    'risk_sizing': ['trade your way', 'come into my trading room', 'master swing trader'],
    'marketing_low': ['17 proven currency', 'binary options', 'forex trading basics'],
}


def load_sections(book_id: str) -> list[dict]:
    p = os.path.join(SECTIONS, book_id + '.sections.jsonl')
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def bind(lead: dict, sections: list[dict]) -> dict:
    part = lead['part_id']
    lo, hi = lead['local_start_line'], lead['local_end_line']
    best = None
    for s in sections:
        if s['part_id'] != part:
            continue
        if s['line_start'] <= lo and hi <= s['line_end']:
            best = s
            break
        # partial overlap: pick the section with max overlap
        ov = min(s['line_end'], hi) - max(s['line_start'], lo)
        if ov >= 0 and (best is None or ov > best[1]):
            best = (s, ov)
    if best is None:
        lead['section_id'] = None
        lead['page_start'] = None
        lead['page_end'] = None
        lead['page_anchor_status'] = 'UNMAPPED'
    elif isinstance(best, tuple):
        s = best[0]
        lead['section_id'] = s['section_id']
        lead['page_start'] = s['page_start']
        lead['page_end'] = s['page_end']
        lead['page_anchor_status'] = 'MAPPED' if s['page_start'] is not None else 'UNMAPPED'
    else:
        lead['section_id'] = best['section_id']
        lead['page_start'] = best['page_start']
        lead['page_end'] = best['page_end']
        lead['page_anchor_status'] = 'MAPPED' if best['page_start'] is not None else 'UNMAPPED'
    return lead


def main() -> int:
    os.makedirs(LEADS_V21, exist_ok=True)
    os.makedirs(REGISTRY, exist_ok=True)
    manifest = json.load(open(MANIFEST))
    byid = {b['book_id']: b for b in manifest['books']}

    book_meta = {}
    for book in manifest['books']:
        bid = book['book_id']
        if not book.get('parts'):
            continue
        # --- P0.3 bind leads ---
        lsrc = os.path.join(LEADS, bid + '.jsonl')
        sections = load_sections(bid)
        if os.path.exists(lsrc):
            leads = [json.loads(l) for l in open(lsrc) if l.strip()]
            bound = [bind(dict(l), sections) for l in leads]
            with open(os.path.join(LEADS_V21, bid + '.jsonl'), 'w') as f:
                for l in bound:
                    f.write(json.dumps(l, ensure_ascii=False) + '\n')
        else:
            bound = []
        n_strong = sum(1 for l in bound if any(t in STRONG for t in l['claim_type_candidates']))
        tokens = book['text_chars'] // 4
        density = n_strong / max(1, tokens / 1000)
        book_meta[bid] = {'book_id': bid, 'title': book['title'], 'leads': len(bound),
                          'n_strong': n_strong, 'tokens': tokens, 'density': density,
                          'lineage': None}

    # --- P0.4 book order ---
    ordered = sorted(book_meta.values(), key=lambda x: -x['density'])
    with open(os.path.join(REGISTRY, 'book_order.json'), 'w') as f:
        json.dump({'pipeline_version': 'research_pipeline_v2.1', 'order': ordered}, f, indent=1)
    print(f'book order: {len(ordered)} books by density (max {ordered[0]["density"]:.2f}, min {ordered[-1]["density"]:.2f})')

    # --- P0.5 lineage suggestion + rounds ---
    # assign lineage by title keyword (P1 book_router verifies)
    for m in book_meta.values():
        t = m['title'].lower()
        for lin, kws in LINEAGES.items():
            if any(k in t for k in kws):
                m['lineage'] = lin
                break
    # seed round: one book per lineage (highest density), then fill to 10
    seeds = []
    for lin in LINEAGES:
        cands = [m for m in ordered if m['lineage'] == lin and m not in seeds]
        if cands:
            seeds.append(cands[0])
    for m in ordered:
        if len(seeds) >= 10:
            break
        if m not in seeds:
            seeds.append(m)

    rounds = []
    remaining = [m for m in ordered if m not in seeds]
    rounds.append({'round': 1, 'seed_round': True, 'books': [s['book_id'] for s in seeds]})
    for r in range(2, 14):
        chunk = remaining[:10]
        remaining = remaining[10:]
        if not chunk:
            break
        rounds.append({'round': r, 'seed_round': False, 'books': [m['book_id'] for m in chunk]})
    if remaining:
        rounds[-1]['books'].extend(m['book_id'] for m in remaining)

    with open(os.path.join(REGISTRY, 'rounds.json'), 'w') as f:
        json.dump({'pipeline_version': 'research_pipeline_v2.1', 'rounds': rounds}, f, indent=1)
    total = sum(len(r['books']) for r in rounds)
    print(f'rounds: {len(rounds)} (books allocated {total})')
    for r in rounds:
        lin = [book_meta[b]['lineage'] for b in r['books'] if book_meta[b]['lineage']]
        print(f"  round {r['round']:>2d}: {len(r['books']):>3d} books | lineages: {sorted(set(lin))[:5]}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
