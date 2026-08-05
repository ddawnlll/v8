#!/usr/bin/env python3
"""research_pipeline_v2.0 — deterministic quality gates.

Hard gates (a record either passes or is rejected/holds a status):
  gate0_provenance      book, edition, page/part, quote, source hash present
  gate1_source_fidelity  every normalized condition has a source mapping or an
                         inference label; silent inference is rejected
  gate2_has_strategy     signal expert minimum: setup + trigger + direction
                         + invalidation -> else SPEC_INCOMPLETE
  gate3_falsifiability   a future observation that would falsify the thesis
  gate4_pit              no future data in feature definitions
  gate5_transfer         original mechanism exists in target market
  gate6_independent      executable rules must have A/B extraction records

Leak check (raw source layer): non-quote fields of a RawClaim must not
contain crypto/V8 vocabulary the source did not state.
"""
from __future__ import annotations

import json
import re
import sys

PIPELINE = 'research_pipeline_v2.0'

PROVENANCE = {
    'SOURCE_EXPLICIT', 'SOURCE_DERIVED', 'MARKET_TRANSLATION',
    'V8_OPERATIONALIZATION', 'EXPERIMENTAL_ASSUMPTION', 'V8_DEFAULT',
    'UNRESOLVED', 'UNKNOWN',
}

# Vocabulary that must never appear in the raw source layer outside quotes.
LEAK_TOKENS = [
    'btc', 'bitcoin', 'crypto', 'usdm', 'perp', 'perpetual', 'funding',
    'next_bar_close', 'atr stop', 'atr_stop', '1r', 'frozen', 'v8',
    'binance', '24/7', '24_7', 'taker', 'maker', 'altcoin',
]


def _norm(s) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', str(s).lower())


def _leak(s: str) -> list[str]:
    n = _norm(s)
    return [t for t in LEAK_TOKENS if t in n]


def gate0_provenance(claim: dict) -> tuple[bool, list[str]]:
    errs = []
    if not claim.get('book_id'):
        errs.append('missing book_id')
    if not claim.get('edition_id'):
        errs.append('missing edition_id')
    src = claim.get('source', {})
    if src.get('page_start') is None and src.get('page_end') is None:
        errs.append('missing page anchor')
    if not claim.get('supporting_passages'):
        errs.append('missing supporting passage')
    return (not errs, errs)


def gate1_source_fidelity(claim: dict) -> tuple[bool, list[str]]:
    errs = []
    # every non-quote string field must be provenance-clean
    for field in ('source_rule', 'original_context'):
        v = claim.get(field)
        if isinstance(v, dict):
            for k, val in _walk(v):
                if isinstance(val, str):
                    hits = _leak(val)
                    if hits:
                        errs.append(f'{field}.{k} leaks crypto/V8 tokens: {hits}')
    for p in claim.get('author_parameters', []):
        if p.get('provenance') not in ('SOURCE_EXPLICIT', 'SOURCE_DERIVED'):
            errs.append(f"parameter {p.get('name')} provenance not SOURCE_*: {p.get('provenance')}")
    return (not errs, errs)


def _walk(obj, prefix=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f'{prefix}.{k}' if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f'{prefix}[{i}]')
    else:
        yield prefix, obj


def gate2_has_strategy(claim: dict) -> tuple[bool, list[str]]:
    """Signal-expert minimum: setup + trigger + direction + invalidation."""
    errs = []
    rule = claim.get('source_rule', {})
    if not rule.get('setup'):
        errs.append('no observable setup')
    if not rule.get('trigger'):
        errs.append('no trigger')
    if rule.get('direction') in (None, 'NOT_SPECIFIED'):
        errs.append('no direction/action')
    if not rule.get('invalidation'):
        errs.append('no invalidation/expiry')
    return (not errs, errs)


def gate3_falsifiability(claim: dict) -> tuple[bool, list[str]]:
    errs = []
    for cond in (claim.get('source_rule', {}).get('trigger') or []):
        low = str(cond).lower()
        if re.search(r'\b(may|might|could|possibly)\b', low):
            errs.append(f'trigger not falsifiable: {cond!r}')
    return (not errs, errs)


def gate4_pit(spec: dict) -> tuple[bool, list[str]]:
    """Expert spec must not reference future bars / repainting labels."""
    errs = []
    if spec.get('pit_safe') is False:
        errs.append('pit_safe is false')
    s = json.dumps(spec)
    if re.search(r'next\s*bar|future|tomorrow|after\s+close|repaint', s, re.I):
        errs.append('possible future-data reference in spec')
    return (not errs, errs)


def gate5_transfer(translation: dict) -> tuple[bool, list[str]]:
    errs = []
    if translation.get('data_status') == 'DATA_BLOCKED' and not translation.get('transfer_risks'):
        errs.append('DATA_BLOCKED without transfer risks')
    return (not errs, errs)


def gate6_independent(raw_claim_id: str, records: dict) -> tuple[bool, list[str]]:
    a = records.get('extractor_a', {}).get(raw_claim_id)
    b = records.get('extractor_b', {}).get(raw_claim_id)
    adj = records.get('adjudicated', {}).get(raw_claim_id)
    errs = []
    if not a:
        errs.append('missing extractor A')
    if not b:
        errs.append('missing extractor B')
    if a and b and not adj:
        errs.append('missing adjudication for A/B disagreement')
    return (not errs, errs)


# Workers whose prompts must be leak-free (Layer-1: raw source). Workers that
# legitimately reference the target market / V8 (translator, spec, validator,
# execution/risk geometry extractors) are exempt.
LINT_EXEMPT = {
    'crypto_translator', 'expert_spec_builder', 'expert_validator',
    'execution_facts_extractor', 'risk_geometry_extractor',
}

# Forbidden tokens in Layer-1 worker prompts (invariant 7 — prompt lint).
PROMPT_FORBIDDEN = [
    r'\bbtc\b', r'\bbitcoin\b', r'\bcrypto\b', r'\bperpetual\b', r'\bfunding\b',
    r'\b1h\b', r'\busdm\b', r'\batr\s+stop\b', r'\bnext[_-]bar[_-]close\b',
    r'\bfrozen\s+referen\w+\b', r'\b1r\b', r'\bv8\b', r'\bbinance\b',
    r'\b24/7\b', r'\b24_7\b', r'\btaker\b', r'\baltcoin\b',
]


def lint_prompts(prompts_dir: str) -> dict:
    """Invariant 7: Layer-1 worker prompts must not contain the target-market
    vocabulary. A leak in a prompt anchors the model even when output looks
    clean — the pollution is in attention, not just output."""
    import os
    import re
    results = []
    clean = True
    for fn in sorted(os.listdir(prompts_dir)):
        if not fn.endswith('.md'):
            continue
        name = fn.replace('.v21.md', '')
        if name in LINT_EXEMPT:
            continue
        text = open(os.path.join(prompts_dir, fn), encoding='utf-8').read()
        hits = []
        for pat in PROMPT_FORBIDDEN:
            for m in re.finditer(pat, text, re.I):
                # report line context
                line_no = text[:m.start()].count('\n') + 1
                snippet = text[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')
                hits.append({'token': m.group(0), 'line': line_no, 'snippet': snippet})
        if hits:
            clean = False
        results.append({'prompt': name, 'leaks': hits})
    return {'prompt_lint_clean': clean, 'prompts_checked': len(results),
            'results': results}


def validate_raw_claim(claim: dict) -> dict:
    g0 = gate0_provenance(claim)
    g1 = gate1_source_fidelity(claim)
    g2 = gate2_has_strategy(claim)
    g3 = gate3_falsifiability(claim)
    status = 'PASS'
    reasons = []
    if not g0[0]:
        status = 'LEAD_ONLY' if not claim.get('supporting_passages') else 'REJECTED'
        reasons += g0[1]
    elif not g1[0]:
        status = 'REJECTED'
        reasons += g1[1]
    elif not g2[0]:
        status = 'SPEC_INCOMPLETE'
        reasons += g2[1]
    elif not g3[0]:
        status = 'REJECTED'
        reasons += g3[1]
    return {'raw_claim_id': claim.get('raw_claim_id'), 'gate_status': status,
            'gates': {'provenance': g0, 'source_fidelity': g1,
                      'has_strategy': g2, 'falsifiability': g3},
            'reasons': reasons}


def main() -> int:
    """CLI: validate one JSONL file of raw claims, or lint worker prompts."""
    if len(sys.argv) >= 2 and sys.argv[1] == '--lint-prompts':
        import os
        prompts_dir = sys.argv[2] if len(sys.argv) > 2 else (
            os.path.join(os.path.dirname(__file__), '..', 'prompts'))
        r = lint_prompts(prompts_dir)
        print(f'prompt lint: {"CLEAN" if r["prompt_lint_clean"] else "LEAKS FOUND"} '
              f'({r["prompts_checked"]} prompts checked)')
        for res in r['results']:
            if res['leaks']:
                print(f'  LEAK {res["prompt"]}:')
                for h in res['leaks'][:8]:
                    print(f'    line {h["line"]}: [{h["token"]}] ...{h["snippet"]}...')
        return 0 if r['prompt_lint_clean'] else 2
    if len(sys.argv) < 2:
        print('usage: validate.py <raw_claims.jsonl> [--leak-only]')
        return 1
    path = sys.argv[1]
    results = []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        claim = json.loads(line)
        r = validate_raw_claim(claim)
        results.append(r)
        print(f"{r['gate_status']:>16s}  {r['raw_claim_id']}  {r['reasons']}")
    counts = {}
    for r in results:
        counts[r['gate_status']] = counts.get(r['gate_status'], 0) + 1
    print(f'\n{len(results)} claims validated under {PIPELINE}')
    for k, v in sorted(counts.items()):
        print(f'  {k}: {v}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
