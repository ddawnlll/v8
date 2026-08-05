#!/usr/bin/env python3
"""
P4 v2.3 A2.1 — deterministic name-candidate mining (0 tokens).

Runs over the 101 unprocessed books' p4_gate_input anchor_text and extracts
candidate NAMED METHOD names using the validated PATS approach from
P4_FULL_RUN_TASK.md Bölüm V A2.1. Output is a frequency-sorted candidate list
for A2.2 (LLM approval). No LLM used here.
"""
import json, re, glob, os
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(BASE, 'processed_books')

# The 101 books to process (from Bölüm II)
TODO = """book_0001 book_0003 book_0004 book_0006 book_0007 book_0008 book_0011
book_0013 book_0015 book_0017 book_0018 book_0019 book_0021 book_0022 book_0023
book_0024 book_0026 book_0027 book_0028 book_0029 book_0030 book_0031 book_0033
book_0034 book_0035 book_0036 book_0037 book_0038 book_0039 book_0040 book_0041
book_0042 book_0043 book_0044 book_0046 book_0047 book_0048 book_0049 book_0050
book_0051 book_0054 book_0057 book_0058 book_0059 book_0060 book_0061 book_0062
book_0063 book_0064 book_0065 book_0066 book_0067 book_0068 book_0069 book_0070
book_0071 book_0072 book_0073 book_0074 book_0075 book_0076 book_0077 book_0079
book_0080 book_0081 book_0083 book_0084 book_0085 book_0086 book_0087 book_0089
book_0090 book_0091 book_0092 book_0093 book_0094 book_0095 book_0096 book_0097
book_0099 book_0100 book_0101 book_0103 book_0104 book_0105 book_0106 book_0107
book_0108 book_0109 book_0111 book_0112 book_0113 book_0115 book_0116 book_0117
book_0118 book_0119 book_0122 book_0123 book_0124 book_0125""".split()

PATS = [
    r'\b(?:the\s+)?([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,3})\s+'
    r'(?:pattern|method|indicator|oscillator|strategy|setup|system|line|cloud|channel|band|wave)\b',
    r'\bknown as (?:the\s+)?([A-Z][A-Za-z\- ]{2,30})',
    r'\bcalled (?:the\s+)?([A-Z][A-Za-z\- ]{2,30})',
    r'\breferred to as (?:the\s+)?([A-Z][A-Za-z\- ]{2,30})',
]

NOISE = {'the', 'this', 'that', 'figure', 'chapter', 'using', 'another',
         'example', 'following', 'above', 'below', 'see', 'shown', 'next',
         'previous', 'first', 'second', 'third', 'last', 'each', 'every',
         'such', 'same', 'other', 'more', 'most', 'some', 'these', 'those',
         'one', 'two', 'three', 'both', 'all', 'any', 'also', 'can', 'will',
         'may', 'should', 'must', 'would', 'could', 'when', 'where', 'which',
         'what', 'how', 'into', 'from', 'over', 'under', 'between', 'during'}

RX = [re.compile(p) for p in PATS]

def mine(text):
    found = []
    for rx in RX:
        for m in rx.finditer(text):
            name = m.group(1).strip()
            toks = name.split()
            if not toks:
                continue
            if toks[0].lower() in NOISE:
                continue
            if len(toks[-1]) < 3 or len(name) < 3 or len(name) > 40:
                continue
            found.append(name)
    return found

def main():
    counts = Counter()
    per_book = {}
    total_records = 0
    for b in sorted(TODO):
        files = sorted(glob.glob(os.path.join(GATE, b, 'p4_gate_input', '*.jsonl')))
        names = Counter()
        for f in files:
            for line in open(f, encoding='utf-8', errors='replace'):
                line = line.strip()
                if not line:
                    continue
                total_records += 1
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                text = rec.get('anchor_text', '') or ''
                for n in mine(text):
                    names[n] += 1
        per_book[b] = names
        for n, c in names.items():
            counts[n] += c

    # dedupe candidates that are strict subsets of a longer candidate (e.g.
    # "Fibonacci Retracement" vs "Fibonacci Retracement Tool")
    keys = sorted(counts, key=lambda k: (-len(k.split()), -counts[k]))
    keep = []
    for k in keys:
        toks = k.split()
        if any(toks == o.split()[:len(toks)] for o in keep if len(o.split()) > len(toks)):
            continue
        keep.append(k)
    keep.sort(key=lambda k: (-counts[k], k))

    print(f"total gate records scanned: {total_records}")
    print(f"distinct candidate names:   {len(keep)}")
    print("\n=== candidates (name : count : #books) ===")
    for n in keep:
        nb = sum(1 for b in per_book if per_book[b].get(n))
        print(f"{n!r} : {counts[n]} : {nb}")

    # persist for A2.2
    out = {
        'stage': 'A2.1',
        'total_records': total_records,
        'candidates': [{'name': n, 'count': counts[n],
                        'books': sum(1 for b in per_book if per_book[b].get(n))}
                       for n in keep],
    }
    with open(os.path.join(BASE, 'registry', 'p4_a21_candidates.json'), 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nwrote registry/p4_a21_candidates.json")

if __name__ == '__main__':
    main()
