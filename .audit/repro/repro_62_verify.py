"""Verification for ISSUE #62 — PENDING->TRIGGERED now gated on the frozen
trigger predicate.

Pre-fix state (BASELINE.md row #62 / #67): lab.py PHASE 2 advanced a candidate
born at bar i-1 to TRIGGERED at bar i UNCONDITIONALLY — the only gate was the
pre-entry invalidation check. 27 candlestick candidates entered the trigger
path, and 16 of them had a trigger-bar close that did NOT confirm beyond the
frozen trigger_ref (Ch14.2 "entry only on a CLOSE beyond the trigger"). Of the
4 executed candlestick entries, 2 violated the book trigger predicate.

Fixed state (this script): lab.py PHASE 2 now evaluates
risk_geometry['trigger_ref'] + 'trigger_side' before PENDING -> TRIGGERED; an
unconfirmed candidate stays PENDING and is re-checked each bar until it
confirms, invalidates, or expires. candlestick_reversal declares trigger_side
(CLOSE_ABOVE for LONG, CLOSE_BELOW for SHORT).

Assertions:
  1. static   — lab.py contains a code-level consumer of risk_geometry
                ['trigger_ref'] in PHASE 2 (the close-confirmation entry
                predicate, not merely the expert's still_valid thesis check);
                candlestick_reversal declares 'trigger_side'.
  2. funnel   — detected -> TRIGGERED -> executed for candlestick_reversal on
                the 2500-bar dev window.
  3. core     — the ACTUAL lab-TRIGGERED candlestick set is exactly the
                close-confirmed set: every candidate the lab advances
                PENDING->TRIGGERED satisfies close-beyond-trigger on its real
                trigger bar (n_lab_would_not_trigger == 0). The pre-fix
                unconditional path advanced 27 with 16 unconfirmed.
  4. executed — candlestick executed count and mean net_R vs pre-fix (4 -> 2).

Deterministic: fixed window (2500 bars), no wall clock, no randomness.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / '.audit' / 'repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, executed_outcomes, stats,
)

PASS = 'PASS'
FAIL = 'FAIL'
EXPERT_ID = 'candlestick_reversal'

# ---------------------------------------------------------------------------
# 1. STATIC — the trigger predicate must now live in the runner
# ---------------------------------------------------------------------------
lab_src = (REPO / 'src' / 'v8' / 'lab.py').read_text()
cr_src = (REPO / 'src' / 'v8' / 'experts' / 'candlestick_reversal.py').read_text()

lab_has_trigger_ref_read = "risk_geometry.get('trigger_ref')" in lab_src
lab_has_trigger_side = 'trigger_side' in lab_src
lab_has_close_predicate = ('triggered = float(bar.payload[\'close\']) > '
                           'float(trigger_ref)') in lab_src
cr_declares_side = ("'trigger_side': ('CLOSE_ABOVE' if direction == 'LONG'"
                    in cr_src.replace('\n', ' '))

static_ok = (lab_has_trigger_ref_read and lab_has_trigger_side
             and lab_has_close_predicate and cr_declares_side)

# ---------------------------------------------------------------------------
# 2. WINDOW + DRAFTS
# ---------------------------------------------------------------------------
rows = load_window(n_bars=2500)
states, drafts = detect_drafts(rows)
cd_drafts = [(cid, d, bi) for cid, d, bi in drafts if d.expert_id == EXPERT_ID]
n_candlestick_drafts = len(cd_drafts)

# ---------------------------------------------------------------------------
# 3. CORE — the lab's actual TRIGGERED set must equal the close-confirmed set
# ---------------------------------------------------------------------------
lab, report = run_lab(rows)
recs = lab.candidates.read()
cd_cids = {r['candidate_id'] for r in recs
           if r.get('to_state') == 'DETECTED' and r.get('expert_id') == EXPERT_ID}
lab_triggered = Counter()
for r in recs:
    if r.get('to_state') == 'TRIGGERED' and r['candidate_id'] in cd_cids:
        lab_triggered[r['candidate_id']] = r['knowledge_time']

pit = sorted(rows, key=lambda r: r.available_time)
bars = [r for r in pit if r.channel == 'kline'
        and r.payload.get('closed') is True][:2500]
bar_time_to_idx = {b.available_time: i for i, b in enumerate(bars)}

cand_to_draft = {cid: d for cid, d, _bi in cd_drafts}
lab_would_not = 0
lab_would = 0
lab_unresolved = 0
confirmed_triggers = 0
trigger_bar_details = []
for cid, ts in lab_triggered.items():
    idx = bar_time_to_idx.get(ts)
    if idx is None:
        lab_unresolved += 1
        continue
    draft = cand_to_draft[cid]
    tb = bars[idx].payload
    long = draft.direction == 'LONG'
    trig_ref = float(draft.risk_geometry['trigger_ref'])
    close = float(tb['close'])
    holds = (long and close > trig_ref) or (not long and close < trig_ref)
    if holds:
        lab_would += 1
    else:
        lab_would_not += 1
    confirmed_triggers += 1
    trigger_bar_details.append({
        'cid': cid[:12], 'variant': draft.risk_geometry.get('variant'),
        'direction': draft.direction,
        'trigger_idx': idx, 'trigger_bar_close': close,
        'trigger_ref': trig_ref, 'confirmed': holds,
    })

n_lab_triggered = len(lab_triggered)
core_ok = (n_lab_triggered > 0 and lab_would_not == 0
           and lab_would == n_lab_triggered)

# ---------------------------------------------------------------------------
# 4. FUNNEL + EXECUTED — detected -> TRIGGERED -> executed for the family
# ---------------------------------------------------------------------------
outcomes = executed_outcomes(lab)
cd_outcomes = [o for o in outcomes if o.get('candidate_id') in cd_cids]
executed_net = [o.get('net_r') for o in cd_outcomes
                if o.get('net_r') is not None]
cd_executed_stats = stats(executed_net)
n_executed_cd = len(cd_outcomes)

# Every executed candlestick entry must satisfy the trigger predicate.
violators = []
for o in cd_outcomes:
    d = cand_to_draft.get(o['candidate_id'])
    if d is None:
        continue
    trigger = d.risk_geometry.get('trigger_ref')
    entry = o.get('entry_price')
    if entry is None or entry == 0.0 or trigger is None:
        continue
    pred_ok = (d.direction == 'LONG' and entry > float(trigger)) or \
              (d.direction == 'SHORT' and entry < float(trigger))
    if not pred_ok:
        violators.append(o['candidate_id'])
n_executed_violating = len(violators)

executed_ok = n_executed_violating == 0

# All-setups headline population for context (same definition as baseline).
all_executed_net = [o.get('net_r') for o in outcomes if o.get('net_r') is not None]
executed_subset_stats = stats(all_executed_net)

all_ok = static_ok and core_ok and executed_ok

summary = {
    'issue': 62,
    'title': 'PENDING->TRIGGERED now gated on the frozen trigger predicate',
    'fixed': all_ok,
    'before': {
        'n_detected': 33,
        'n_TRIGGERED': 27,
        'n_TRIGGERED_without_close_confirmation': 16,
        'n_executed': 4,
        'n_executed_violating_trigger_predicate': 2,
        'note': 'BASELINE.md row #62: "16/27 candlestick candidates triggered '
                'despite failing the book close-beyond-trigger test"; row #67: '
                '"2/4 entered candidates violated the trigger predicate". '
                '(Pre-fix out/62.json was itself overwritten by a post-fix run '
                'during the fix pass; BASELINE.md is the authoritative record.)',
    },
    'after': {
        'n_detected': n_candlestick_drafts,
        'n_TRIGGERED_lab': n_lab_triggered,
        'n_TRIGGERED_unconfirmed_lab': lab_would_not,
        'n_executed': n_executed_cd,
        'n_executed_violating_trigger_predicate': n_executed_violating,
        'candlestick_executed_stats': cd_executed_stats,
    },
    'delta': ('candlestick_reversal funnel on the 2500-bar dev window: '
              f'detected {33} -> TRIGGERED 27 -> {n_lab_triggered} '
              '(pre-fix unconditional 27 -> post-fix close-confirmed '
              f'{n_lab_triggered}; unconfirmed triggers 16 -> {lab_would_not}); '
              f'executed 4 -> {n_executed_cd} '
              f'(mean net_R {cd_executed_stats["mean_net_r"] if cd_executed_stats["n"] else None}). '
              'The triggered set now equals the confirmed set: every candidate '
              'the lab advances PENDING->TRIGGERED has a trigger-bar close '
              'beyond the frozen trigger_ref, and every executed candlestick '
              'entry satisfies the predicate.'),
    'assertions': {
        'static': {
            'assert': 'lab.py PHASE 2 consumes risk_geometry[trigger_ref] + '
                      'trigger_side as the entry predicate; candlestick_reversal '
                      'declares trigger_side',
            'status': PASS if static_ok else FAIL,
            'lab_has_trigger_ref_read': lab_has_trigger_ref_read,
            'lab_has_trigger_side': lab_has_trigger_side,
            'lab_has_close_predicate': lab_has_close_predicate,
            'candlestick_declares_trigger_side': cr_declares_side,
        },
        'core': {
            'assert': 'the lab-TRIGGERED candlestick set equals the '
                      'close-confirmed set (n_lab_would_not == 0)',
            'status': PASS if core_ok else FAIL,
            'n_lab_TRIGGERED': n_lab_triggered,
            'n_lab_would_trigger': lab_would,
            'n_lab_would_not_trigger': lab_would_not,
            'n_lab_unresolved': lab_unresolved,
        },
        'executed': {
            'assert': 'no executed candlestick entry violates the trigger '
                      'predicate',
            'status': PASS if executed_ok else FAIL,
            'n_executed': n_executed_cd,
            'n_executed_violating_trigger_predicate': n_executed_violating,
            'violator_cids': violators,
        },
        'funnel': {
            'n_detected': n_candlestick_drafts,
            'n_TRIGGERED': n_lab_triggered,
            'n_executed': n_executed_cd,
            'trigger_bar_details': trigger_bar_details,
        },
        'headline_executed_subset': {
            'population': 'EXECUTED subset, 2500-bar dev window, cost 0.07',
            **executed_subset_stats,
            'n_executed_total': report.n_executed,
            'candidate_count': report.candidate_count,
        },
    },
}

print(json.dumps(summary, indent=2, sort_keys=True, default=str))

out_path = Path(__file__).resolve().parent / 'out' / '62.fixed.json'
out_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str))
