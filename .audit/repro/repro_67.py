"""Repro for ISSUE #67 — trigger_ref is written to geometry but never read by
the runner.

Claim: candlestick_reversal computes trigger_ref and writes it to
risk_geometry; the lab runner never consumes it as an entry predicate. The
field enters the geometry hash (episode identity) but not the behavior.

Evidence produced:
  1. static   — the decision-path consumers of trigger_ref (writer + the only
                reader is candlestick_reversal.still_valid, a POST-ENTRY thesis
                check; lab.py / simulator.py have zero occurrences).
  2. identity — _geometry_version excludes atr_ref / prior_high_ref /
                prior_low_ref but INCLUDES trigger_ref, so trigger_ref changes
                episode_key.  Demonstrated on every candlestick_reversal draft.
  3. dynamic  — executed candlestick_reversal entries whose entry-bar close
                did NOT satisfy the book trigger predicate (LONG close > trigger;
                SHORT close < trigger).  Non-zero => entry was unconditional.

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
    load_window, detect_drafts, run_lab, executed_outcomes,
)
from v8.lab import _geometry_version  # noqa: E402
from v8.lifecycle import episode_key  # noqa: E402

# ---------------------------------------------------------------------------
# 1. STATIC — decision-path consumers of trigger_ref
# ---------------------------------------------------------------------------
consumers = []          # (file, kind)
writer = None
for py in sorted((REPO / 'src' / 'v8').rglob('*.py')):
    rel = py.relative_to(REPO)
    for ln, line in enumerate(py.read_text().splitlines(), 1):
        if 'trigger_ref' in line:
            if 'candlestick_reversal' in str(rel):
                if "trigger_ref':" in line:
                    writer = f'{rel}:{ln}'
                    consumers.append({'file': f'{rel}:{ln}',
                                      'kind': 'WRITE (evaluate geometry)'})
                elif '.get(' in line or "['trigger_ref']" in line:
                    consumers.append({'file': f'{rel}:{ln}',
                                      'kind': 'READ (still_valid thesis check)'})
                else:
                    consumers.append({'file': f'{rel}:{ln}', 'kind': 'other'})
            else:
                consumers.append({'file': f'{rel}:{ln}', 'kind': 'other'})

# zero occurrences in the runner / simulator
lab_hits = [c for c in consumers if 'lab.py' in c['file']]
sim_hits = [c for c in consumers if 'simulator.py' in c['file']]

# Which risk_geometry keys does the decision path actually consume?
lab_consumed = ['prior_low_ref', 'prior_high_ref', 'limit_price',
                'target_r', 'stop_r']
lab_src = (REPO / 'src' / 'v8' / 'lab.py').read_text()
sim_src = (REPO / 'src' / 'v8' / 'simulator.py').read_text()
lab_consumes = {k: (k in lab_src) for k in lab_consumed}
sim_consumes = {'trigger_ref': 'trigger_ref' in sim_src,
                'atr_ref': 'atr_ref' in sim_src,
                'limit_price': 'limit_price' in sim_src,
                'risk_frac': 'risk_frac' in sim_src}

# ---------------------------------------------------------------------------
# 2. WINDOW + DRAFTS
# ---------------------------------------------------------------------------
rows = load_window(n_bars=2500)
states, drafts = detect_drafts(rows, n_bars=2500)
cr_drafts = [(cid, d, bi) for cid, d, bi in drafts
             if d.expert_id == 'candlestick_reversal']

# ---------------------------------------------------------------------------
# 3. IDENTITY — trigger_ref is part of episode_key via _geometry_version
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

# Sanity: removing an EXCLUDED key (atr_ref) must NOT change the key.
_excluded_demo = None
if cr_drafts:
    _cid0, _d0, _bi0 = cr_drafts[0]
    _d_no_atr = replace(
        _d0, risk_geometry={k: v for k, v in _d0.risk_geometry.items()
                            if k != 'atr_ref'})
    _cid_no_atr = episode_key(_d0.expert_id, _d0.expert_version,
                              _d0.instrument, _d0.direction,
                              _d0.setup_anchor_event_id,
                              _geometry_version(_d_no_atr))
    _cid_base = episode_key(_d0.expert_id, _d0.expert_version,
                            _d0.instrument, _d0.direction,
                            _d0.setup_anchor_event_id,
                            _geometry_version(_d0))
    _excluded_demo = {
        'excluded_key': 'atr_ref',
        'same_cid_without_excluded_key': (_cid_base == _cid_no_atr),
    }

episode_key_differs = n_identity_change > 0

# ---------------------------------------------------------------------------
# 4. DYNAMIC — executed candlestick_reversal entries vs the trigger predicate
# ---------------------------------------------------------------------------
lab, report = run_lab(rows)
outcomes = executed_outcomes(lab)
cr_by_cid = {cid: (d, bi) for cid, d, bi in cr_drafts}

n_entered = 0
violators = []          # entries whose entry-bar close broke the trigger predicate
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
        continue            # never entered (NOT_EXECUTED guard, belt & braces)
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
violators_sorted = sorted(violators, key=lambda v: (v['direction'], v['cid']))

evidence = {
    'static': {
        'trigger_ref_occurrences': consumers,
        'writer': writer,
        'lab_py_hits': lab_hits,
        'simulator_py_hits': sim_hits,
        'lab_consumed_geometry_keys': lab_consumes,
        'simulator_consumed_geometry_keys': sim_consumes,
        'runner_entry_predicates': [
            'pre-entry invalidation via prior_low_ref/prior_high_ref '
            '(lab.py PHASE 1a / PHASE 2)',
            'tradability_mask_veto (lab.py)',
            'RiskGate.admit (lab.py)',
            'FILL_AT_LIMIT limit_price (lab.py + simulator.py)',
            'trigger_ref: NO pre-entry consumer in lab.py / simulator.py',
        ],
    },
    'identity': {
        'n_candlestick_reversal_drafts': len(cr_drafts),
        'n_drafts_whose_key_changes_without_trigger_ref': n_identity_change,
        'episode_key_differs': episode_key_differs,
        'example': identity_example,
        'excluded_key_control': _excluded_demo,
        'geometry_version_excluded_keys':
            ('atr_ref', 'prior_high_ref', 'prior_low_ref'),
        'geometry_version_included_nonstructural_keys':
            ('trigger_ref', 'stop_ref', 'variant', 'stop_r', 'target_r',
             'expiry_bars', 'entry'),
    },
    'dynamic': {
        'n_entered': n_entered,
        'n_entered_violating_trigger_predicate': n_entered_violating,
        'violators': violators_sorted,
        'trigger_predicate': 'LONG: entry_close > trigger_ref; '
                             'SHORT: entry_close < trigger_ref',
        'n_executed_outcomes_total': len(outcomes),
        'n_candlestick_reversal_executed_outcomes_matched': matched,
    },
}

print(json.dumps(evidence, indent=2, sort_keys=True, default=str))

out_path = Path(__file__).resolve().parent / 'out' / '67.json'
out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True,
                               default=str))
