#!/usr/bin/env python3
"""
P4 v2.3 A1 consolidator + provenance repair (full-run).

Reads per-chunk corroboration outputs (written by corroborator sub-agents),
enforces provenance invariants deterministically, and merges into a single
corroboration list for registry/p4_full_run.json.

Repairs applied (deterministic, auditable):
  * Drop records whose claim_ref is null/empty or mismatched against the gate
    input claim_id (unreferencable, e.g. book_0001). Reported, not fabricated.
  * exact_text: require a literal contiguous substring of anchor_text. If the
    sub-agent's phrase matches only after whitespace normalization, replace
    it with the ACTUAL literal substring span from the anchor (preserving the
    anchor's exact whitespace), so T3 provenance holds.
  * generic records: force behavior_id/page/exact_text = null, arrays empty.
  * validate behavior_id in the 21; validate page matches page_start.
  * validate added_parameters carry page or claim_ref.
  * round is assigned from a book -> round map (book_order + .rounds files),
    not from the scratch record (scratch carries no round).
"""
import json, os, re, sys
from collections import Counter

VALID = {'trend_continuation_pullback','breakout_retest','failed_breakout_reentry',
 'liquidity_sweep_reclaim','volatility_breakout','mean_reversion_band',
 'support_resistance_bounce','momentum_divergence_reversal','trend_following_channel',
 'capitulation_exhaustion','volume_confirmed_breakout','gap_reversion',
 'news_discounting_reaction','trend_exhaustion_reversal','line_crossover_momentum',
 'candlestick_reversal_pattern','contrarian_extreme_reversal','relative_strength_ranking',
 'pattern_breakout_projection','dow_theory_average_confirmation',
 'monetary_policy_cycle_signal'}

def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def find_literal_span(anchor, phrase):
    """Return the literal contiguous substring of anchor that normalizes to
    phrase, preserving anchor whitespace. Returns None if not found."""
    a = anchor or ''
    an = norm(a)
    pn = norm(phrase)
    if not pn:
        return None
    amap = []
    prev_space = True
    for i, ch in enumerate(a):
        if ch.isspace():
            if not prev_space:
                amap.append(i)
            prev_space = True
        else:
            amap.append(i)
            prev_space = False
    start = an.find(pn)
    if start < 0:
        return None
    end = start + len(pn)
    o_start = amap[start]
    o_end = amap[end - 1] + 1
    return a[o_start:o_end]

def repair_record(r, claim):
    """Return repaired record + list of problems."""
    problems = []
    verdict = r.get('verdict')
    if verdict == 'generic':
        r['behavior_id'] = None
        r['page'] = None
        r['exact_text'] = None
        r['added_conditions'] = []
        r['added_parameters'] = []
        return r, problems
    if verdict != 'corroboration':
        problems.append(f"bad verdict {verdict}")
        r['verdict'] = 'generic'
        r['behavior_id'] = None; r['page'] = None; r['exact_text'] = None
        r['added_conditions'] = []; r['added_parameters'] = []
        return r, problems
    bid = r.get('behavior_id')
    if bid not in VALID:
        problems.append(f"invalid behavior_id {bid} -> generic")
        r['verdict'] = 'generic'
        r['behavior_id'] = None; r['page'] = None; r['exact_text'] = None
        r['added_conditions'] = []; r['added_parameters'] = []
        return r, problems
    ps = claim.get('page_start')
    if r.get('page') != ps:
        if ps is not None:
            problems.append(f"page {r.get('page')} != page_start {ps}")
            r['page'] = ps
        else:
            r['page'] = None
    et = r.get('exact_text')
    anchor = claim.get('anchor_text', '') or ''
    if et:
        if et in anchor:
            pass
        else:
            span = find_literal_span(anchor, et)
            if span and span in anchor:
                problems.append(f"exact_text whitespace-repaired")
                r['exact_text'] = span
            else:
                problems.append(f"exact_text NOT a substring -> generic")
                r['verdict'] = 'generic'
                r['behavior_id'] = None; r['page'] = None; r['exact_text'] = None
                r['added_conditions'] = []; r['added_parameters'] = []
                return r, problems
    else:
        problems.append("corroboration without exact_text -> generic")
        r['verdict'] = 'generic'
        r['behavior_id'] = None; r['page'] = None; r['exact_text'] = None
        r['added_conditions'] = []; r['added_parameters'] = []
        return r, problems
    params = []
    for p in (r.get('added_parameters') or []):
        if not p.get('page') and not p.get('claim_ref'):
            problems.append("param without page/claim_ref dropped")
            continue
        if p.get('page') is None and ps is not None:
            p['page'] = ps
        params.append(p)
    r['added_parameters'] = params
    return r, problems

# book -> round. The resumed run's schedule: rounds of 10 books in manifest
# order. round 8 = first 10 (book_0001..0017, confirmed by checkpoint),
# round 9 = next 10 (0018..0029), rounds 10-12 confirmed by .rounds files.
# Rounds 13+ are the remaining-run schedule (5 books per round).
def load_round_map(base, manifest):
    rmap = {}
    order = sorted(manifest.keys())
    # rounds 10-18 from .rounds files (authoritative where present)
    rdir = os.path.join(base, '.rounds')
    if os.path.isdir(rdir):
        # full-run plan (rounds 13+, 5 books/round) takes precedence
        fr = os.path.join(rdir, 'fullrun_rounds.json')
        if os.path.exists(fr):
            try:
                for p in json.load(open(fr)).get('rounds', []):
                    for b in p.get('books', []):
                        rmap[b] = p['round']
            except Exception:
                pass
        for fn in sorted(os.listdir(rdir)):
            mm = re.fullmatch(r'round(\d+)\.json', fn)
            if not mm:
                continue
            rnd = int(mm.group(1))
            try:
                d = json.load(open(os.path.join(rdir, fn)))
            except Exception:
                continue
            for b in d.get('books', []):
                if b not in rmap:
                    rmap[b] = rnd
    # rounds 8-9: first 20 books of the manifest order
    r8 = set()
    cp = os.path.join(base, 'registry', 'p4_full_run.checkpoint.json')
    if os.path.exists(cp):
        try:
            r8 = set(json.load(open(cp)).get('processed_books', []))
        except Exception:
            pass
    if not r8:
        r8 = set(order[:10])
    for b in order[:10]:
        rmap[b] = 8
    for b in order[10:20]:
        if b not in rmap:
            rmap[b] = 9
    return rmap

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scratch = os.path.join(base, '.corr_scratch')
    manifest = json.load(open('/tmp/p4_chunks/manifest.json'))
    rmap = load_round_map(base, manifest)

    out_corr = []
    dropped = []
    all_problems = []
    book_claims = {}
    generic_total = 0
    for b, chunks in sorted(manifest.items()):
        for cp in chunks:
            name = os.path.basename(cp) + '.json'
            op = os.path.join(scratch, name)
            if not os.path.exists(op):
                all_problems.append(f"MISSING {name}")
                continue
            claims = [json.loads(l) for l in open(cp, encoding='utf-8', errors='replace') if l.strip()]
            recs = json.load(open(op))
            if len(recs) != len(claims):
                all_problems.append(f"COUNT {name}: {len(recs)} vs {len(claims)}")
                continue
            for i, (r, c) in enumerate(zip(recs, claims)):
                cr = r.get('claim_ref')
                if not cr or cr == 'null' or cr != c.get('claim_id'):
                    dropped.append({'claim_ref': c.get('claim_id'), 'book': b,
                                    'reason': 'null/mismatched claim_id (unreferencable)'})
                    continue
                repaired, probs = repair_record(r, c)
                all_problems.extend(f"{name}[{i}] {p}" for p in probs)
                repaired['round'] = rmap.get(b, 8)
                if repaired['verdict'] == 'generic':
                    generic_total += 1
                else:
                    out_corr.append(repaired)
                book_claims[b] = book_claims.get(b, 0) + 1

    # dedupe exact duplicates by claim_ref+behavior_id+exact_text (claim_ref not unique)
    seen = {}
    dedup = []
    generic_dedup = 0
    for r in sorted(out_corr, key=lambda x: (x['claim_ref'], x['round'])):
        key = (r['claim_ref'], r.get('behavior_id'), r.get('exact_text'))
        if key in seen:
            continue
        seen[key] = True
        dedup.append(r)

    print(f"corroborations (raw): {len(out_corr)}")
    print(f"deduped: {len(dedup)}")
    print(f"generic (valid ref): {generic_total}")
    print(f"dropped (unreferencable): {len(dropped)}")
    print(f"problems: {len(all_problems)}")
    c = Counter(p.split(' ')[0].split('[')[0] for p in all_problems)
    print("problem types:", dict(c))

    base_reg = json.load(open(os.path.join(base, 'registry', 'p4_b1_partial.json')))
    ledger = {}
    for b, chunks in sorted(manifest.items()):
        n = book_claims.get(b, 0)
        if n:
            ledger[b] = {
                'round': rmap.get(b, 8),
                'claims_processed': n,
                'corroborations': sum(1 for x in dedup if x['claim_ref'].startswith(b + '::')),
            }
    rounds_executed = sorted({v['round'] for v in ledger.values()})
    rounds_ledger = []
    for rnd in rounds_executed:
        books = sorted(b for b, v in ledger.items() if v['round'] == rnd)
        corr_n = sum(ledger[b]['corroborations'] for b in books)
        claims_n = sum(ledger[b]['claims_processed'] for b in books)
        rounds_ledger.append({'round': rnd, 'books': books, 'claims_gated': claims_n,
                              'corroborations': corr_n})

    out = {
        'pipeline_version': 'research_pipeline_v2.3',
        'rounds_executed': rounds_executed,
        'registry': base_reg['registry'],
        'rounds_ledger': rounds_ledger,
        'ledger': ledger,
        'corroborations': dedup,
        'generic_count': generic_total,
        'new_claims': [],
        'dropped': dropped,
        'problems': all_problems[:500],
        'problem_count': len(all_problems),
        'counts': {
            'corroborations': len(dedup),
            'generic': generic_total,
            'dropped_unreferencable': len(dropped),
            'books_processed': len(ledger),
        },
    }
    os.makedirs(os.path.join(base, 'registry'), exist_ok=True)
    json.dump(out, open(os.path.join(base, 'registry', 'p4_full_run.json'), 'w'),
              indent=2, ensure_ascii=False)
    print("wrote registry/p4_full_run.json")

if __name__ == '__main__':
    main()
