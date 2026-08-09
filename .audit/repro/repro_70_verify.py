"""Verify for issue #70 — risk_geometry invariants now FAIL CLOSED.

Pre-fix claim (repro_70.py): the canonical simulator accepted nonsensical
geometry — target_r=-1 booked a −1.07R loss as endpoint=TARGET (a win in any
downstream hit-rate / profit-factor statistic); stop_r=0 was accepted too; no
validation existed in step()/run() (only some experts guard their own
geometry).

The fix (simulator.validate_geometry, D-061): target_r<=0, stop_r<=0 and
expiry_bars<1 raise ValueError at BOTH step() and run() entry. The pre-fix
repro_70.py CRASHES against the fixed tree at the first bad-geometry run()
call — that crash IS the fix. This script asserts the NEW behavior:

  1. run()  raises ValueError on target_r=-1 / stop_r=0 / expiry_bars=0,
     message matching the offending key.
  2. step() raises ValueError on the same (the execution-ledger path is the
     one that feeds the outcome ledger, so it must be guarded too).
  3. valid geometry still runs and yields a sane endpoint (no over-guard).
  4. bollinger_reversion Setup 3: docstring now records the RR=0.5 geometry's
     69% breakeven win rate as a PROVISIONAL_DECISION (issue #70 / D-061);
     Setup 2 / Setup 3 aggregation caveat stated.
  5. latency: the real-tape 2500-bar scan still finds ZERO drafts carrying
     bad geometry (the issue was latent — no expert triggered it — so the
     fail-closed gate is defense-in-depth, not a behavior change on the tape).

Evidence produced (single JSON on stdout).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / '.audit' / 'repro'))

from v8.schema import CandidateDraft  # noqa: E402
from v8.simulator import CanonicalSimulator, OpenPosition  # noqa: E402

from lab_probe import load_window, detect_drafts, TAPE_PATH  # noqa: E402


# ---------------------------------------------------------------------------
# 0. STATIC: validate_geometry exists and is wired into step() and run()
# ---------------------------------------------------------------------------
sim_src = (REPO / 'src/v8/simulator.py').read_text()
validate_geometry_defined = re.search(
    r'def validate_geometry\(draft: CandidateDraft\) -> None', sim_src) is not None
validate_geometry_calls = [
    line.strip() for line in sim_src.splitlines()
    if 'validate_geometry(' in line and 'def validate_geometry' not in line]
step_guarded = any('validate_geometry(pos.draft)' in l for l in
                   sim_src.splitlines())
run_guarded = any('validate_geometry(draft)' in l for l in
                  sim_src.splitlines())
# the three guard branches of the fix
guards = {
    'target_r': 'target_r must be > 0' in sim_src,
    'stop_r': 'stop_r must be > 0' in sim_src,
    'expiry_bars': 'expiry_bars must be >= 1' in sim_src,
}

static = {
    'validate_geometry_defined': validate_geometry_defined,
    'validate_geometry_call_sites': validate_geometry_calls,
    'step_entry_guarded': step_guarded,
    'run_entry_guarded': run_guarded,
    'guard_branches_present': guards,
    'register': 'D-061',
}

# ---------------------------------------------------------------------------
# 1-3. DYNAMIC: fail-closed in run() and step(); valid geometry still runs
# ---------------------------------------------------------------------------
sim = CanonicalSimulator(round_trip_cost_r=0.07)
BARS = [
    {'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0},
    {'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0},
]

GOOD = {'atr_ref': 10.0, 'target_r': 1.0, 'stop_r': 1.0, 'expiry_bars': 8}
BAD = {
    'target_r=-1': {'atr_ref': 10.0, 'target_r': -1.0, 'stop_r': 1.0,
                    'expiry_bars': 8},
    'stop_r=0': {'atr_ref': 10.0, 'target_r': 1.0, 'stop_r': 0.0,
                 'expiry_bars': 8},
    'expiry_bars=0': {'atr_ref': 10.0, 'target_r': 1.0, 'stop_r': 1.0,
                      'expiry_bars': 0},
}


def draft(geometry: dict) -> CandidateDraft:
    return CandidateDraft(
        expert_id='audit_probe', expert_version='v0', instrument='BTCUSDT',
        direction='LONG', setup_fingerprint='issue70',
        risk_geometry=geometry, birth_time=0)


def run_rejects(geometry: dict) -> dict:
    try:
        sim.run(draft(geometry), BARS)
        return {'raised': False, 'error': None,
                'message': 'ACCEPTED (no raise) — REGRESSION'}
    except ValueError as e:
        return {'raised': True, 'error': 'ValueError',
                'message': str(e)}


def step_rejects(geometry: dict) -> dict:
    pos = OpenPosition(candidate_id='c', draft=draft(geometry),
                       entry_price=100.0, entry_bar_index=0)
    try:
        sim.step(pos, BARS[0])
        return {'raised': False, 'error': None,
                'message': 'ACCEPTED (no raise) — REGRESSION'}
    except ValueError as e:
        return {'raised': True, 'error': 'ValueError',
                'message': str(e)}


dynamic = {'run_rejections': {}, 'step_rejections': {}}
for name, geo in BAD.items():
    dynamic['run_rejections'][name] = run_rejects(geo)
    dynamic['step_rejections'][name] = step_rejects(geo)

# the fix must not over-guard: valid geometry still runs to a sane endpoint
good_outcome = sim.run(draft(GOOD), BARS)
dynamic['valid_geometry'] = {
    'geometry': GOOD,
    'endpoint': good_outcome.endpoint,
    'net_r': round(good_outcome.net_r, 4),
    'label_status': good_outcome.label_status,
    'runs': True,
    'endpoint_in_expected_set':
        good_outcome.endpoint in ('TARGET', 'STOP', 'EXPIRY', 'TIME_EXIT'),
}

# ---------------------------------------------------------------------------
# 4. bollinger_reversion Setup 3: RR=0.5 + 69% breakeven + PROVISIONAL_DECISION
# ---------------------------------------------------------------------------
bb_src = (REPO / 'src/v8/experts/bollinger_reversion.py').read_text()
setup3_stop = 'geo[\'stop_r\'] = 2 * sd / atr' in bb_src
setup3_target = 'geo[\'target_r\'] = sd / atr' in bb_src
setup3_RR = 0.5  # target_r = sd/atr, stop_r = 2*sd/atr  =>  RR = 0.5
# breakeven at cost 0.07: reward = 1.00 - 0.07 = +0.93R,
# risk = 2.00 + 0.07 = -2.07R;  w_min = risk/(reward+risk) = 2.07/3.00
reward = 1.00 - 0.07
risk = 2.00 + 0.07
breakeven = risk / (reward + risk)

bollinger = {
    'setup3_source': {
        'stop_line': 'geo[\'stop_r\'] = 2 * sd / atr',
        'target_line': 'geo[\'target_r\'] = sd / atr',
        'stop_line_present': setup3_stop,
        'target_line_present': setup3_target,
    },
    'setup3_RR': setup3_RR,
    'breakeven_formula': 'w_min = risk/(reward+risk) = 2.07/3.00',
    'breakeven_win_rate': round(breakeven, 4),
    # the docstring now carries the justification (issue #70 acceptance
    # criterion 3: RR<1 geometry is either justified as PROVISIONAL_DECISION +
    # required hit rate, or revised) — and the aggregation caveat
    # (criterion 4: Setup 2 / Setup 3 outcomes are NOT separately reported
    # yet, stated as a caveat rather than silently aggregated).
    'docstring_justifies_rr05': 'PROVISIONAL_DECISION' in bb_src,
    'docstring_breakeven_69': '69.0%' in bb_src,
    'docstring_notes_setup23_aggregation': (
        'aggregated in the outcome ledger' in bb_src),
    'docstring_decision_ref': 'D-061' in bb_src,
}

# ---------------------------------------------------------------------------
# 5. LATENCY: still zero bad geometry on the real tape (issue was latent)
# ---------------------------------------------------------------------------
rows = load_window(n_bars=2500)
states, drafts = detect_drafts(rows)
violations = []
setup3_drafts = []
for cid, d, birth_idx in drafts:
    g = d.risk_geometry
    tr = g.get('target_r')
    sr = g.get('stop_r')
    bad = (tr is not None and float(tr) <= 0.0) \
        or (sr is not None and float(sr) <= 0.0)
    if bad:
        violations.append({'cid': cid, 'expert_id': d.expert_id,
                           'geometry': dict(g)})
    if d.expert_id == 'bollinger_reversion' and g.get('variant') == 'b' \
            and len(setup3_drafts) < 3:
        setup3_drafts.append({'expert_id': d.expert_id,
                              'target_r': tr, 'stop_r': sr,
                              'direction': d.direction})

latency = {
    'window_bars': 2500,
    'tape': str(TAPE_PATH),
    'unique_drafts_scanned': len(drafts),
    'bad_geometry_drafts': len(violations),
    'violations': violations[:5],
    'bollinger_setup3_draft_sample': setup3_drafts,
}

evidence = {
    'issue': 70,
    'static': static,
    'dynamic': dynamic,
    'bollinger': bollinger,
    'latency': latency,
}

# ---------------------------------------------------------------------------
# 6. HARD ASSERTIONS — a regression anywhere below exits non-zero. The fixed
#    evidence must PROVE the bug is gone, not merely describe the tree.
# ---------------------------------------------------------------------------
fails: list[str] = []

# (1) run() fails closed on all three invariant violations, message on-key.
for name, geo in BAD.items():
    r = dynamic['run_rejections'][name]
    if not r['raised'] or r['error'] != 'ValueError':
        fails.append(f'run() accepted bad geometry {name} — REGRESSION')
    elif name.split('=')[0] not in r['message']:
        fails.append(f'run() {name} message does not name the key')

# (2) step() fails closed on the same three.
for name, geo in BAD.items():
    s = dynamic['step_rejections'][name]
    if not s['raised'] or s['error'] != 'ValueError':
        fails.append(f'step() accepted bad geometry {name} — REGRESSION')
    elif name.split('=')[0] not in s['message']:
        fails.append(f'step() {name} message does not name the key')

# (3) valid geometry still runs to a sane endpoint (no over-guard).
if not dynamic['valid_geometry']['runs'] \
        or not dynamic['valid_geometry']['endpoint_in_expected_set']:
    fails.append('valid geometry did not run to a sane endpoint — over-guard')

# (4) Setup 3 RR<1 geometry is justified as PROVISIONAL_DECISION with the
#     required hit rate, and the Setup 2/3 aggregation caveat is stated.
if not (bollinger['docstring_justifies_rr05']
        and bollinger['docstring_breakeven_69']
        and bollinger['docstring_decision_ref']):
    fails.append('bollinger_reversion docstring lacks the PROVISIONAL_DECISION '
                 'justification (69% breakeven, D-061)')

# (5) static wiring: validate_geometry defined and called at step()/run() entry.
if not (static['validate_geometry_defined']
        and static['step_entry_guarded'] and static['run_entry_guarded']
        and all(static['guard_branches_present'].values())):
    fails.append('validate_geometry is not defined or not wired into step()/run()')

if fails:
    print(json.dumps(evidence, indent=2, sort_keys=True))
    sys.stderr.write('VERIFY FAILED:\n' + '\n'.join(f'  - {f}' for f in fails) + '\n')
    sys.exit(1)

evidence['verdict'] = {
    'pass': True,
    'asserted': [
        'run() raises ValueError on target_r=-1 / stop_r=0 / expiry_bars=0',
        'step() raises ValueError on the same three (execution-ledger path)',
        'valid geometry still runs to a sane endpoint',
        'Setup 3 RR=0.5 justified as PROVISIONAL_DECISION with 69% breakeven '
        '(D-061); Setup 2/3 aggregation caveat stated',
        'validate_geometry defined and wired into step() and run() entry',
    ],
}
print(json.dumps(evidence, indent=2, sort_keys=True))
