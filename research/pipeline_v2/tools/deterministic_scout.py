#!/usr/bin/env python3
"""research_pipeline_v2.0 — deterministic claim scout (vectorized).

Replaces the LLM claim_scout stage for corpus-wide runs. Scans every part of
every book with a strategy-claim lexicon and emits candidate leads (passage
windows + line anchors). Zero LLM cost; ~1-2 CPU-minutes for the full corpus.

The extractor stages still read the located passages through the strong model;
this stage only REDUCES the text the model must read (typically 100% -> 5-15%).
"""
from __future__ import annotations

import json
import os
import re

ROOT = '/Users/hootie/src/v8'
MANIFEST = os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.json')
OUT = os.path.join(ROOT, 'research/pipeline_v2/corpus/leads')

# (claim_type, regex, weight). Weights mark how strongly a hit signals a real claim.
LEXICON = [
    ('ENTRY_RULE', r'\b(enter(?:ing|s)?(?: a| the| long| short)?|buy signal|sell signal|go long|go short|initiate)\b', 3),
    ('TRIGGER_RULE', r'\b(trigger|signal (?:is|gets)|when (?:the|a|price)|if (?:the|a|price)|confirmation)\b', 3),
    ('EXIT_RULE', r'\b(exit(?:s|ing)?|take profit|profit target|target price|target\b.{0,30}(?:profit|price)|cover(?:ing)? (?:long|position)|square(?:ing)?)\b', 3),
    ('STOP_RULE', r'\b(stop[- ]loss|protective stop|trailing stop|stop\b.{0,25}(?:below|above|exit))', 4),
    ('INVALIDATION', r'\b(invalidat(?:e|ed|ion)|stop(?:s)? out|abort|abandon|no longer valid|signal (?:fails|failed))\b', 3),
    ('POSITION_SIZING', r'\b(position (?:size|sizing)|risk (?:per trade|per position|of (?:account|equity|capital))|2%? percent rule|money management|bet (?:size|sizing)|unit(s)? (?:risk|size))\b', 4),
    ('RISK_RULE', r'\b(maximum loss|max loss|drawdown|risk management|capital preservation|survival(?: first)?|never risk)\b', 3),
    ('REGIME_FILTER', r'\b(trending market|range[- ]bound|sideways|choppy|bull(?:ish)? market|bear(?:ish)? market|regime|market phase)\b', 2),
    ('EMPIRICAL_CLAIM', r'\b(win rate|success rate|profit factor|backtest|back-tested|test (?:results|period)|sample(?: size)?|average (?:gain|loss|win|profit)|hit rate|expectancy|probability of (?:success|winning)|percent of trades)\b', 4),
    ('FAILURE_CLAIM', r'\b(failure|failed|whipsaw|false (?:signal|breakout)|unreliable|do not (?:use|trade|rely)|never (?:trade|use|enter)|mistake|caution|warning)\b', 2),
    ('METHODOLOGY', r'\b(data snooping|overfit(?:ting)?|statistical significance|hypothesis|replication|out of sample|walk[- ]forward|sample selection)\b', 4),
    ('FEATURE_CLAIM', r'\b(moving average|rsi|stochastic|relative strength|momentum|oscillator|divergence|on[- ]balance volume|volume (?:spike|surge|climax))\b', 1),
    ('SETUP_DEFINITION', r'\b(setup|pattern|formation|configuration|reversal|breakout)\b', 2),
]

WINDOW_LINES = 5          # +/- lines around a hit that belong to one lead
MAX_CHARS = 1100          # anchor_text cap per lead
CLUSTER_GAP = 8           # merge hits closer than this many lines (one strategy paragraph = one lead)
MIN_CLUSTER_WEIGHT = 5    # drop clusters below this total weight
STRONG_TYPES = {'ENTRY_RULE', 'TRIGGER_RULE', 'STOP_RULE', 'EXIT_RULE',
                'INVALIDATION', 'POSITION_SIZING', 'RISK_RULE',
                'EMPIRICAL_CLAIM', 'METHODOLOGY'}
INDEX_RE = re.compile(r'^\s*[A-Za-z][^,]{0,60},\s*\d{1,4}(-\d{1,4})?(\s*,\s*\d{1,4}(-\d{1,4})?)*\s*$')
SKIP_WORDS = {'copyright', 'library of congress', 'isbn', 'all rights reserved',
              'table of contents', 'preface', 'acknowledgments', 'praise for'}


def slug(book_id: str) -> str:
    return book_id


def scan_part(book: dict, part: dict) -> list[dict]:
    path = os.path.join(ROOT, part['path'])
    if not os.path.exists(path):
        return []
    text = open(path, encoding='utf-8', errors='replace').read()
    lines = text.split('\n')

    hits = []
    for i, line in enumerate(lines):
        low = line.lower()
        if any(w in low for w in SKIP_WORDS):
            continue
        for ct, pat, w in LEXICON:
            if re.search(pat, line, re.I):
                hits.append((i, ct, w))

    if not hits:
        return []

    # cluster nearby hits into leads
    hits.sort(key=lambda h: h[0])
    clusters = []
    cur = [hits[0]]
    for h in hits[1:]:
        if h[0] - cur[-1][0] <= CLUSTER_GAP + WINDOW_LINES:
            cur.append(h)
        else:
            clusters.append(cur)
            cur = [h]
    clusters.append(cur)

    leads = []
    for ci, cl in enumerate(clusters):
        start = max(0, cl[0][0] - WINDOW_LINES)
        end = min(len(lines), cl[-1][0] + WINDOW_LINES + 1)
        anchor = '\n'.join(l for l in lines[start:end] if l.strip())
        anchor = anchor[:MAX_CHARS]
        types = sorted({ct for _, ct, _ in cl}, key=lambda x: x)
        weight_sum = sum(w for _, _, w in cl)
        n_types = len(types)
        n_strong = sum(1 for _, ct, _ in cl if ct in STRONG_TYPES)
        # quality gate: a lead must contain at least one strong signal
        # (entry/trigger/stop/exit/invalidation/sizing/risk/empirical/methodology)
        if n_strong == 0:
            continue
        if weight_sum < MIN_CLUSTER_WEIGHT:
            continue
        if len(anchor.strip()) < 40:
            continue
        index_only = sum(1 for l in lines[start:end] if INDEX_RE.match(l)) >= max(2, len(cl) // 2)
        if index_only and n_strong == 0:
            priority = 'low'
        else:
            priority = ('high' if (weight_sum >= 9 and n_types >= 2 and n_strong >= 1)
                        else 'medium' if weight_sum >= 5 else 'low')
        reason = f'{n_types} pattern classes, {weight_sum} weight; types: {",".join(types)}'
        leads.append({
            'lead_id': f'lead_{book["book_id"]}_{part["order"]}_{ci:03d}',
            'book_id': book['book_id'],
            'part_id': part['part_id'],
            'claim_type_candidates': types,
            'anchor_text': anchor,
            'local_start_line': start,
            'local_end_line': end - 1,
            'reason': reason,
            'priority': priority,
            'index_only': index_only,
            'source_chars': part['chars'],
        })
    return leads


def main() -> int:
    manifest = json.load(open(MANIFEST))
    os.makedirs(OUT, exist_ok=True)
    total_leads = 0
    total_hits = 0
    per_book = {}
    for book in manifest['books']:
        if not book.get('parts'):
            continue
        leads = []
        for part in book['parts']:
            leads.extend(scan_part(book, part))
        leads.sort(key=lambda l: l['local_start_line'])
        # dedupe near-identical anchor texts (same book, same text)
        seen = set()
        uniq = []
        for l in leads:
            k = l['anchor_text'][:300]
            if k in seen:
                continue
            seen.add(k)
            uniq.append(l)
        out = os.path.join(OUT, f"{book['book_id']}.jsonl")
        with open(out, 'w') as f:
            for l in uniq:
                f.write(json.dumps(l, ensure_ascii=False) + '\n')
        total_leads += len(uniq)
        per_book[book['book_id']] = len(uniq)
        total_hits += len(leads)

    print(f'corpus scouted: {len(manifest["books"])} books, {total_leads} leads (raw hits {total_hits})')
    import collections
    prio = collections.Counter()
    for book in manifest['books']:
        fp = os.path.join(OUT, f"{book['book_id']}.jsonl")
        if os.path.exists(fp):
            for line in open(fp):
                prio[json.loads(line)['priority']] += 1
    print('priority distribution:', dict(prio))
    top = sorted(per_book.items(), key=lambda kv: -kv[1])[:8]
    print('top books by lead count:', top)
    low = sorted(per_book.items(), key=lambda kv: kv[1])[:5]
    print('books with fewest leads:', low)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
