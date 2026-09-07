#!/usr/bin/env python3
"""W2 gate certificate normalizer: strips wall-clock measurement fields and
S6 Timer lines from full-audit stdout so runs are comparable byte-for-byte.
Domain/economic values are NEVER stripped (only *_sec/duration/wall_time)."""
import re
import sys

PAT = re.compile(
    r'"(allegory_duration_sec|analysis_duration_sec|concurrency_wall_duration_sec|'
    r'eval_duration_sec|fingerprint_duration_sec|html_duration_sec|oracle_duration_sec|'
    r'total_duration_sec|total_wall_time_sec|usdm_duration_sec)"\s*:\s*[^,\n]+,?'
)

def norm(src: str, dst: str) -> None:
    txt = open(src).read()
    if not txt.lstrip().startswith('{'):  # skip stderr banner, keep JSON cert
        txt = txt[txt.index('{'):]
    out = []
    for line in txt.splitlines(keepends=True):
        if 'S6 Timer' in line:
            continue
        out.append(PAT.sub('', line))
    open(dst, 'w').write(''.join(out))

if __name__ == '__main__':
    norm(sys.argv[1], sys.argv[2])
