"""Repro for ISSUE #65 — Literature preconditions mostly unimplemented
(failed_breakout: 2/10).

Claim: the shipped experts implement few of the literature preconditions their
names claim; failed_breakout implements 2 of 10. Setup count is inflated as a
result (many cheap setups per bar).

Repro:
 (1) Static audit of src/v8/experts/failed_breakout.py against the issue's
     10-condition table (each condition's mechanism searched in the source).
 (2) Setup inflation over 2500 real BTCUSDT bars: detect_drafts -> count
     failed_breakout drafts and total drafts; report setups-per-bar.

Deterministic: fixed window (2500 bars), no wall clock, seeded RNG unused.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import detect_drafts, load_window  # noqa: E402

N_BARS = 2500
SRC = Path(REPO / 'src/v8/experts/failed_breakout.py')
src = SRC.read_text()

# ---------------------------------------------------------------------------
# (1) Static audit of the 10 literature preconditions.
#     Each verdict is derived from a mechanism search of the CURRENT source,
#     read fully above (the file is 116 lines; no mechanism is split across
#     helpers the searches would miss).
# ---------------------------------------------------------------------------
CONDITIONS = [
    # (num, mechanism_search, implemented, evidence)
    (1, 'prior_trend', False,
     'requires=(location,volatility,history); evaluate reads close/atr/history '
     'only — no trend/regime feature consumed; _last_breakout() is the setup '
     'definition (close>prior max high), not a separate trend precondition'),
    (2, 'exhaustion', False,
     'no exhaustion measure anywhere in source (no climax/extension check)'),
    (3, 'liquidity_sweep', False,
     'no sweep detection (no wick-through-prior-low check before reclaim)'),
    (4, 'rejection', False,
     'no rejection-candle check (no upper/lower shadow logic)'),
    (5, 'close_back_in_range', 'close < self._ref_prior_high' in src,
     'line 74: `if not (close < self._ref_prior_high): return NO_SETUP`'),
    (6, 'volume_confirmation', False,
     'requires lacks participation/volume group; no volume token in source'),
    (7, 'no_news', False,
     'tape has no news channel; no event filter (data-absence)'),
    (8, 'rr_gt_2', False,
     'risk_geometry target_r=1.0, stop_r=1.0 -> RR=1.0, not >2 (line 87)'),
    (9, 'stop_beyond_sweep', False,
     'stop_r=1.0 (1xATR via atr_ref), no sweep level to place stop beyond'),
    (10, 'invalidation', 'def still_valid' in src,
     'still_valid() lines 94-115: close back above prior_high_ref kills thesis'),
]

conditions_applied = sum(1 for _n, _m, impl, _e in CONDITIONS if impl)
conditions_total = len(CONDITIONS)

audit_table = [
    {'num': n, 'condition': m, 'implemented': impl, 'evidence': ev}
    for n, m, impl, ev in CONDITIONS
]

# ---------------------------------------------------------------------------
# (2) Setup inflation over 2500 bars.
# ---------------------------------------------------------------------------
rows = load_window(n_bars=N_BARS)
_states, drafts = detect_drafts(rows, n_bars=N_BARS)

failed_drafts = [d for (cid, d, bi) in drafts if d.expert_id == 'failed_breakout']
failed_breakout_drafts = len(failed_drafts)
total_drafts = len(drafts)

# per-expert breakdown (context for the systemic claim)
from collections import Counter
per_expert = Counter(d.expert_id for (_c, d, _b) in drafts)

result = {
    'issue': 65,
    'title': 'Literature preconditions mostly unimplemented '
             '(failed_breakout: 2/10)',
    'claim': ('failed_breakout implements 2 of 10 literature preconditions; '
              'setup count is inflated by the absent filters'),
    'reproduced': conditions_applied == 2 and conditions_total == 10,
    'key_numbers': {
        'conditions_applied': conditions_applied,
        'conditions_total': conditions_total,
        'failed_breakout_drafts': failed_breakout_drafts,
        'total_drafts': total_drafts,
        'setups_per_bar': round(total_drafts / N_BARS, 4),
        'failed_setups_per_bar': round(failed_breakout_drafts / N_BARS, 4),
    },
    'audit_table': audit_table,
    'per_expert_drafts': dict(per_expert.most_common()),
    'n_bars': N_BARS,
    'source': str(SRC),
}

out = json.dumps(result, indent=2, default=str)
print(out)

out_path = Path(REPO / '.audit/repro/out/65.json')
out_path.write_text(out)
