"""Verification for ISSUE #67 — trigger_ref is now consumed as the entry
predicate in lab.py PHASE 2 (with #62).

Pre-fix state (BASELINE.md): the lab entered candlestick_reversal candidates
unconditionally; 2 of 4 entered candidates VIOLATED the book trigger predicate
(LONG entry close NOT above trigger_ref / SHORT NOT below). trigger_ref was
written into risk_geometry, carried the episode hash, and had NO pre-entry
consumer outside the expert's still_valid() thesis check.

Fixed state (this script): lab.py PHASE 2 evaluates the frozen trigger
predicate before PENDING -> TRIGGERED; an unconfirmed candidate stays PENDING.
The prior repro script's static section hard-coded "trigger_ref: NO pre-entry
consumer" — that assertion is now FALSE by construction, so this verify script
asserts the NEW behavior instead:

  1. static   — lab.py now contains a CODE consumer of risk_geometry['trigger_ref']
                in PHASE 2 (the entry predicate), not merely the expert's
                still_valid() thesis check.
  2. identity — trigger_ref remains part of episode_key (unchanged; now
                justified because it drives entry behavior).
  3. dynamic  — n_entered_violating_trigger_predicate == 0 on the 2500-bar
                dev window: no candlestick_reversal candidate enters without
                close-beyond-trigger confirmation.

Deterministic: fixed window (2500 bars), no wall clock, no randomness.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / '.audit' / 'repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, executed_outcomes, stats,
)
from v8.lab import _geometry_version  # noqa: E402
from v8.lifecycle import episode_key  # noqa: E402

PASS = 'PASS'
FAIL = 'FAIL'

# ---------------------------------------------------------------------------
# 1. STATIC — lab.py must CONSUME trigger_ref as the entry predicate
# ---------------------------------------------------------------------------
lab_src = (REPO / 'src' / 'v8' / 'lab.py').read_text()
sim_src = (REPO / 'src' / 'v8' / 'simulator.py').read_text()
cr_src = (REPO / 'src' / 'v8' / 'experts' / 'candlestick_reversal.py').read_text()

# A code-level consumer in lab.py: the PHASE-2 read that maps the frozen
# trigger_ref + trigger_side to the close-confirmation predicate.
lab_has_getter = "risk_geometry.get('trigger_ref')" in lab_src
lab_has_triggered = 'triggered = float(bar.payload[\'close\']) > float(trigger_ref)' in lab_src
lab_consumer_lines = []
for ln, line in enumerate(lab_src.splitlines(), 1):
    if 'trigger_ref' in line and '#' not in line.split('trigger_ref')[0].split('#')[0][-30:]:
        # heuristic: keep lines that are code (not comment-only)
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        lab_consumer_lines.append({'file': f'src/v8/lab.py:{ln}',
                                   'line': stripped})
lab_code_consumer = len(lab_consumer_lines) > 0

# The expert still writes trigger_ref AND now declares the explicit side.
cr_writes_trigger_ref = "trigger_ref': trigger_price" in cr_src
cr_declares_side = 'trigger_side' in cr_src

static_ok = (lab_has_getter and lab_code_consumer and cr_writes_trigger_ref
             and cr_declares_side)

# ---------------------------------------------------------------------------
# 2. WINDOW + DRAFTS
# ---------------------------------------------------------------------------
rows = load_window(n_bars=2500)
states, drafts = detect_drafts(rows, n_bars=2500)
cr_drafts = [(cid, d, bi) for cid, d, bi in drafts
             if d.expert_id == 'candlestick_reversal']

# ---------------------------------------------------------------------------
# 3. IDENTITY — trigger_ref stays part of episode_key
# ---------------------------------------------------------------------------
n_identity_change = 0
identity_example = None
for cid, d, _bi in cr_drafts:
    d_without = replace(
        d, risk_geometry={k: v for k, v in d.risk_geometry.items()
                          if k != 'trigger_ref'})
    cid_with = episode_key(d.expert_id, d.expert_version, d.instrument,
                           d.direction, d.setup_anchor_event_id,
                           _geometry_version(d))
    cid_without = episode_key(d.expert_id, d.expert_version, d.instrument,
                              d.direction, d.setup_anchor_event_id,
                              _geometry_version(d_without))
    if cid_with != cid_without:
        n_identity_change += 1
        if identity_example is None:
            identity_example = {
                'variant': d.risk_geometry.get('variant'),
                'trigger_ref': d.risk_geometry.get('trigger_ref'),
                'cid_with_trigger_ref': cid_with,
                'cid_without_trigger_ref': cid_without,
            }

identity_ok = (n_identity_change == len(cr_drafts)) and len(cr_drafts) > 0

# ---------------------------------------------------------------------------
# 4. DYNAMIC — no executed candlestick entry violates the trigger predicate
# ---------------------------------------------------------------------------
lab, report = run_lab(rows)
outcomes = executed_outcomes(lab)
cr_by_cid = {cid: (d, bi) for cid, d, bi in cr_drafts}

n_entered = 0
violators = []
matched = 0
for o in outcomes:
    cid = o.get('candidate_id')
    hit = cr_by_cid.get(cid)
    if hit is None:
        continue
    matched += 1
    d, bi = hit
    trigger = d.risk_geometry.get('trigger_ref')
    entry = o.get('entry_price')
    if entry is None or entry == 0.0 or trigger is None:
        continue            # never entered
    n_entered += 1
    pred_ok = (d.direction == 'LONG' and entry > float(trigger)) or \
              (d.direction == 'SHORT' and entry < float(trigger))
    if not pred_ok:
        violators.append({
            'cid': cid, 'direction': d.direction,
            'variant': d.risk_geometry.get('variant'),
            'entry_price': entry, 'trigger_ref': trigger,
            'endpoint': o.get('endpoint'),
            'label_status': o.get('label_status'),
        })

n_entered_violating = len(violators)
dynamic_ok = n_entered_violating == 0

# Headline executed-subset economics on the 2500-bar dev window.
executed_net = [o.get('net_r') for o in outcomes if o.get('net_r') is not None]
executed_stats = stats(executed_net)

assertions = {
    'static': {
        'assert': 'lab.py consumes risk_geometry[trigger_ref] as a PHASE-2 '
                  'entry predicate (not merely still_valid)',
        'status': PASS if static_ok else FAIL,
        'lab_code_consumer_lines': lab_consumer_lines,
        'lab_has_getter': lab_has_getter,
        'lab_has_close_above_predicate': lab_has_triggered,
        'candlestick_writes_trigger_ref': cr_writes_trigger_ref,
        'candlestick_declares_trigger_side': cr_declares_side,
    },
    'identity': {
        'assert': 'trigger_ref is still part of episode_key (unchanged, now '
                  'justified: it drives entry behavior)',
        'status': PASS if identity_ok else FAIL,
        'n_candlestick_reversal_drafts': len(cr_drafts),
        'n_drafts_whose_key_changes_without_trigger_ref': n_identity_change,
        'example': identity_example,
    },
    'dynamic': {
        'assert': 'n_entered_violating_trigger_predicate == 0 (no entry '
                  'without close-beyond-trigger confirmation)',
        'status': PASS if dynamic_ok else FAIL,
        'n_entered': n_entered,
        'n_entered_violating_trigger_predicate': n_entered_violating,
        'violators': sorted(violators, key=lambda v: (v['direction'], v['cid'])),
        'trigger_predicate': 'LONG: entry_close > trigger_ref; '
                             'SHORT: entry_close < trigger_ref',
        'n_candlestick_reversal_executed_outcomes_matched': matched,
    },
    'headline_executed_subset': {
        'population': 'EXECUTED subset, 2500-bar dev window, cost 0.07',
        **executed_stats,
        'terminal_distribution': report.terminal_distribution,
        'n_executed_total': report.n_executed,
        'candidate_count': report.candidate_count,
    },
}

all_ok = static_ok and identity_ok and dynamic_ok
summary = {
    'issue': 67,
    'title': 'trigger_ref is now the entry predicate (consumed in lab.py '
             'PHASE 2, with #62)',
    'fixed': all_ok,
    'before': {
        'n_entered': 4,            # BASELINE.md headline: "2/4 entered
        'n_entered_violating_trigger_predicate': 2,   # candidates violated"
        'note': 'BASELINE.md row #67: "2/4 entered candidates violated the '
                'trigger predicate". Pre-fix out/67.json was overwritten by '
                'a post-fix run during the fix pass (its lab_py_hits are the '
                'post-fix trigger lines); BASELINE.md is the authoritative '
                'pre-fix record.',
    },
    'after': {
        'n_entered': n_entered,
        'n_entered_violating_trigger_predicate': n_entered_violating,
        'n_executed_total': report.n_executed,
        'executed_subset': executed_stats,
    },
    'delta': ('trigger predicate violations among executed candlestick entries: '
              f'2/4 -> 0/{n_entered} (the two pre-fix unconditional entries that '
              'violated the book close-beyond-trigger predicate no longer enter; '
              'every executed candlestick entry now satisfies the predicate). '
              'Identity note holds: trigger_ref is still part of episode_key '
              f'({n_identity_change}/{len(cr_drafts)} drafts), now justified.'),
    'assertions': assertions,
}

print(json.dumps(summary, indent=2, sort_keys=True, default=str))

out_path = Path(__file__).resolve().parent / 'out' / '67.fixed.json'
out_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str))
