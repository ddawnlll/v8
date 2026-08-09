"""Issue #62 repro: PENDING->TRIGGERED has no trigger predicate.

Static claim (src/v8/lab.py, PHASE 2, lines 635-694): a candidate born at bar
i-1 is advanced PENDING->TRIGGERED at bar i UNCONDITIONALLY — the only gate is
the pre-entry invalidation check (LONG: low < prior_low, SHORT: high >
prior_high). No trigger predicate (trigger_ref) is ever evaluated at entry.

Dynamic repro:
  1. full-slate detect_drafts (byte-consistent with the lab),
  2. filter candlestick_reversal drafts (they carry risk_geometry['trigger_ref']),
  3. replicate the lab's PHASE-2 gate on the trigger bar (birth_idx + 1),
  4. among drafts that entered PENDING->TRIGGERED, evaluate the would-be book
     predicate (Ch14.2: entry only on a CLOSE beyond the trigger):
         LONG  -> close > trigger_ref
         SHORT -> close < trigger_ref
  5. ground-truth: run the full lab and count actual PENDING->TRIGGERED
     transitions for candlestick_reversal candidates; cross-check.

Deterministic: no wall clock, fixed window, fixed expert slate.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_probe import load_window, detect_drafts, run_lab, ALL_EXPERT_CLASSES  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
N_BARS = 2500
EXPERT_ID = 'candlestick_reversal'

rows = load_window(n_bars=N_BARS)
pit = sorted(rows, key=lambda r: r.available_time)
bars = [r for r in pit if r.channel == 'kline'
        and r.payload.get('closed') is True][:N_BARS]
bar_time_to_idx = {b.available_time: i for i, b in enumerate(bars)}

# ---- dynamic: draft-level replication of the lab PHASE-2 gate -----------------
states, drafts = detect_drafts(rows)
cd_drafts = [d for d in drafts if d[1].expert_id == EXPERT_ID]
n_candlestick_drafts = len(cd_drafts)

n_triggered = 0          # entered the unconditional PENDING->TRIGGERED path
n_invalidated = 0        # stopped by the PHASE-2 invalidation gate (never triggered)
n_no_trigger_bar = 0     # born on the final bar: no trigger bar inside the window
n_would_trigger = 0      # triggered AND book predicate satisfied on the trigger bar
n_would_not_trigger = 0  # triggered AND book predicate FAILED on the trigger bar
examples: list[dict] = []

for cid, draft, birth_idx in cd_drafts:
    trig_idx = birth_idx + 1
    if trig_idx >= len(bars):
        n_no_trigger_bar += 1
        continue
    tb = bars[trig_idx].payload
    geom = draft.risk_geometry
    long = draft.direction == 'LONG'
    # PHASE-2 invalidation gate (lab.py:642) — mirrors info['prior_low'] /
    # info['prior_high']: candlestick_reversal freezes prior_low_ref /
    # prior_high_ref (= the pattern stop) into the geometry at birth.
    if long:
        prior = float(geom['prior_low_ref'])
        invalidated = float(tb['low']) < prior
    else:
        prior = float(geom['prior_high_ref'])
        invalidated = float(tb['high']) > prior
    if invalidated:
        n_invalidated += 1
        continue
    n_triggered += 1
    # would-be book trigger predicate (Ch14.2): entry only on a close beyond
    # the trigger. Never evaluated by lab.py — this is the counterfactual.
    trig_ref = float(geom['trigger_ref'])
    close = float(tb['close'])
    holds = (long and close > trig_ref) or (not long and close < trig_ref)
    if holds:
        n_would_trigger += 1
    else:
        n_would_not_trigger += 1
        if len(examples) < 5:
            examples.append({
                'cid': cid[:12], 'variant': geom.get('variant'),
                'direction': draft.direction,
                'birth_idx': birth_idx,
                'trigger_bar_close': close,
                'trigger_ref': trig_ref,
            })

assert n_triggered + n_invalidated + n_no_trigger_bar == n_candlestick_drafts

# ---- ground truth: full lab run ----------------------------------------------
lab, _report = run_lab(rows)
recs = lab.candidates.read()
cd_cids = {r['candidate_id'] for r in recs
           if r.get('to_state') == 'DETECTED' and r.get('expert_id') == EXPERT_ID}
lab_triggered = Counter()
for r in recs:
    if r.get('to_state') == 'TRIGGERED' and r['candidate_id'] in cd_cids:
        lab_triggered[r['candidate_id']] = r['knowledge_time']
# for the actual lab-triggered set, evaluate the book predicate on the real
# trigger bar (knowledge_time of the TRIGGERED transition == trigger bar as_of)
lab_would_not = 0
lab_would = 0
lab_unresolved = 0
cand_to_draft = {}
for cid, draft, birth_idx in cd_drafts:
    if cid in lab_triggered:
        cand_to_draft[cid] = (draft, birth_idx)
for cid, ts in lab_triggered.items():
    idx = bar_time_to_idx.get(ts)
    if idx is None or idx + 1 >= len(bars):
        lab_unresolved += 1
        continue
    draft, birth_idx = cand_to_draft[cid]
    tb = bars[idx].payload
    long = draft.direction == 'LONG'
    trig_ref = float(draft.risk_geometry['trigger_ref'])
    close = float(tb['close'])
    if (long and close > trig_ref) or (not long and close < trig_ref):
        lab_would += 1
    else:
        lab_would_not += 1

fraction_not_triggering = (n_would_not_trigger / n_triggered) if n_triggered else None
fraction_not_triggering_all = (n_would_not_trigger / n_candlestick_drafts) \
    if n_candlestick_drafts else None

evidence = {
    'issue': 62,
    'static': {
        'lab_phase2': 'lab.py:635-694: PHASE 2 advances PENDING->TRIGGERED at '
                      'line 650 (reason_code=trigger_observed) with NO trigger '
                      'predicate; the only gate before it is the invalidation '
                      'check at line 642 (LONG low<prior_low / SHORT '
                      'high>prior_high). trigger_ref is never read by lab.py.',
        'trigger_ref_consumers': (
            'grep -rn "trigger_ref" src/v8/: only experts/candlestick_reversal.py '
            '(line 280 writes it into risk_geometry; line 305 reads it in '
            'still_valid() — an OPEN-position thesis check, NOT an entry '
            'predicate). lab.py / lifecycle / simulator: zero reads.'
        ),
    },
    'dynamic': {
        'n_candlestick_drafts': n_candlestick_drafts,
        'n_triggered_unconditionally': n_triggered,
        'n_invalidated_at_trigger_bar': n_invalidated,
        'n_no_trigger_bar': n_no_trigger_bar,
        'n_would_trigger': n_would_trigger,
        'n_would_not_trigger': n_would_not_trigger,
        'fraction_not_triggering_among_triggered': fraction_not_triggering,
        'fraction_not_triggering_of_all_drafts': fraction_not_triggering_all,
        'example_failures': examples,
    },
    'ground_truth_lab_run': {
        'n_candlestick_detected': len(cd_cids),
        'n_lab_TRIGGERED': len(lab_triggered),
        'n_lab_would_trigger': lab_would,
        'n_lab_would_not_trigger': lab_would_not,
        'n_lab_unresolved': lab_unresolved,
    },
}

key_numbers = {
    'n_candlestick_drafts': n_candlestick_drafts,
    'n_would_not_trigger': n_would_not_trigger,
    'n_would_trigger': n_would_trigger,
    'fraction_not_triggering': fraction_not_triggering,
    'n_triggered_unconditionally': n_triggered,
    'n_invalidated_at_trigger_bar': n_invalidated,
    'fraction_not_triggering_of_all_drafts': fraction_not_triggering_all,
    'lab_ground_truth_n_triggered': len(lab_triggered),
    'lab_ground_truth_n_would_not': lab_would_not,
}

out = json.dumps({'issue': 62,
                  'title': 'PENDING->TRIGGERED has no trigger predicate',
                  'reproduced': True,
                  'claim': ('lab.py PHASE 2 advances PENDING->TRIGGERED '
                            'unconditionally (only invalidation gates it); the '
                            'trigger price computed by candlestick_reversal '
                            '(trigger_ref) is never evaluated as an entry '
                            'predicate.'),
                  'key_numbers': key_numbers,
                  'evidence': evidence}, indent=2, sort_keys=True)
print(out)

(Path(__file__).resolve().parent / 'out' / '62.json').write_text(out + '\n',
                                                                 encoding='utf-8')
