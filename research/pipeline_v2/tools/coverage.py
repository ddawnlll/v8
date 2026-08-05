#!/usr/bin/env python3
"""research_pipeline_v2.0 — coverage accountant.

Takes the corpus manifest + a per-book coverage record (book_map) and computes
the coverage metrics the protocol tracks:
  page_coverage, part_coverage, figure coverage (stub), claim page-citation rate,
  orphan-claim rate, per-book coverage report.
"""
from __future__ import annotations

import json
import sys


def part_coverage(book_map: dict) -> dict:
    total = book_map.get('total_parts', 0)
    mapped = book_map.get('mapped_parts', 0)
    return {'part_coverage': (mapped / total) if total else 0.0,
            'mapped_parts': mapped, 'total_parts': total,
            'missing_parts': book_map.get('missing_parts', [])}


def claim_page_citation_rate(claims: list) -> dict:
    n = len(claims)
    cited = sum(1 for c in claims
                if (c.get('source') or {}).get('page_start') is not None
                or any((p or {}).get('page') is not None
                       for p in c.get('supporting_passages', [])))
    return {'claims': n, 'page_cited': cited,
            'page_citation_rate': (cited / n) if n else 0.0}


def orphan_claim_rate(claims: list, leads: list) -> dict:
    lead_ids = {l.get('lead_id') for l in leads}
    n = len(claims)
    orphan = sum(1 for c in claims if c.get('lead_id') not in lead_ids)
    return {'orphan_claims': orphan, 'orphan_rate': (orphan / n) if n else 0.0}


def report(manifest_entry: dict, book_map: dict, claims: list, leads: list) -> dict:
    pc = part_coverage(book_map)
    cr = claim_page_citation_rate(claims)
    oc = orphan_claim_rate(claims, leads)
    return {
        'book_id': manifest_entry.get('book_id'),
        'text_chars': manifest_entry.get('text_chars'),
        'parts': manifest_entry.get('n_parts'),
        **pc,
        **cr,
        **oc,
    }


def main() -> int:
    """usage: coverage.py <manifest.json> <book_map.json> <claims.jsonl> <leads.jsonl>"""
    if len(sys.argv) < 5:
        print('usage: coverage.py <manifest.json> <book_map.json> <claims.jsonl> <leads.jsonl>')
        return 1
    manifest = json.load(open(sys.argv[1]))
    book_map = json.load(open(sys.argv[2]))
    claims = [json.loads(l) for l in open(sys.argv[3]) if l.strip()]
    leads = [json.loads(l) for l in open(sys.argv[4]) if l.strip()]
    entry = next((b for b in manifest['books'] if b['book_id'] == book_map.get('book_id')), {})
    r = report(entry, book_map, claims, leads)
    print(json.dumps(r, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
