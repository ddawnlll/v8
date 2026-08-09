"""Repro for issue #70 — risk_geometry invariants not enforced.

Claim: the canonical simulator accepts nonsensical geometry: target_r<0 puts
the target on the wrong side and the loss is recorded as endpoint=TARGET (a
win in any downstream stat); stop_r=0 is accepted too. No validation exists in
step()/run() (only a few experts guard their own geometry).

Evidence produced (single JSON on stdout):
  static: validation grep over src/v8/simulator.py, src/v8/lab.py,
          src/v8/schema.py for target_r/stop_r guard patterns; presence of any
          validate_geometry symbol; expert-side guard inventory.
  dynamic: CanonicalSimulator().run() on a LONG CandidateDraft with
           target_r=-1.0 (and stop_r=0) over two bar payloads — the actual
           outcome records (endpoint, net_r, label_status).
  mechanism: computed target/stop levels showing the target lands on the
             wrong side of entry.
  contrast: atr_ref=0 and atr_ref=-5 correctly raise ValueError (the only
            geometry guard that exists) — proving the gap is specific to
            target_r/stop_r.
  bollinger: source-derived Setup 3 RR (target_r/stop_r) and the breakeven
             win rate at round_trip_cost_r=0.07; on-tape Setup-3 drafts.
  latency:  detect_drafts over the real 2500-bar BTCUSDT 1h window — count of
            drafts carrying target_r<=0 or stop_r<=0 (0 = latent, untriggered).
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / '.audit' / 'repro'))

from v8.schema import CandidateDraft  # noqa: E402
from v8.simulator import CanonicalSimulator  # noqa: E402

from lab_probe import load_window, detect_drafts, TAPE_PATH  # noqa: E402


# ---------------------------------------------------------------------------
# 1. STATIC: does any geometry validation exist in the decision-path core?
# ---------------------------------------------------------------------------
def _guardish(line: str) -> bool:
    low = line.lower()
    return any(k in low for k in ('raise', 'valid', '<', '>'))


def grep_validation(rel: str) -> dict:
    """Lines mentioning target_r or stop_r that also carry a guard signal."""
    text = (REPO / rel).read_text()
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if ('target_r' in line or 'stop_r' in line) and _guardish(line):
            hits.append({'line': i, 'text': line.strip()})
    return {'file': rel, 'guardish_hits': hits}


# validate_geometry anywhere in src/v8?
validate_geometry_hits = sorted(
    str(p.relative_to(REPO)) for p in (REPO / 'src' / 'v8').rglob('*.py')
    if 'validate_geometry' in p.read_text())

# expert-side guards (the partial, single-layer defence the issue describes)
expert_guard_files = []
for p in sorted((REPO / 'src' / 'v8' / 'experts').glob('*.py')):
    if 'stop_r <= 0' in p.read_text() or 'target_r <= 0' in p.read_text():
        expert_guard_files.append(p.name)

static = {
    'simulator': grep_validation('src/v8/simulator.py'),
    'lab': grep_validation('src/v8/lab.py'),
    'schema': grep_validation('src/v8/schema.py'),
    'validate_geometry_symbols': validate_geometry_hits,
    'expert_guard_files': expert_guard_files,
    'expert_guard_file_count': len(expert_guard_files),
}

# ---------------------------------------------------------------------------
# 2. DYNAMIC: nonsense geometry through the canonical simulator
# ---------------------------------------------------------------------------
sim = CanonicalSimulator(round_trip_cost_r=0.07)
BARS = [
    {'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0},
    {'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0},
]


def draft(geometry: dict) -> CandidateDraft:
    return CandidateDraft(
        expert_id='audit_probe', expert_version='v0', instrument='BTCUSDT',
        direction='LONG', setup_fingerprint='issue70',
        risk_geometry=geometry, birth_time=0)


def outcome_dict(o) -> dict:
    d = asdict(o)
    d.pop('simulator_hash', None)  # source-hash bound; irrelevant to the claim
    return d


neg_geo = {'atr_ref': 10.0, 'target_r': -1.0, 'stop_r': 1.0, 'expiry_bars': 8}
zero_geo = {'atr_ref': 10.0, 'target_r': 1.0, 'stop_r': 0.0, 'expiry_bars': 8}
entry = BARS[0]['close']
neg_outcome = outcome_dict(sim.run(draft(neg_geo), BARS))
zero_outcome = outcome_dict(sim.run(draft(zero_geo), BARS))

# mechanism: where do the barriers land for a LONG at entry=100, unit=10?
neg_target_price = entry + 1.0 * neg_geo['target_r'] * 10.0
neg_stop_price = entry - 1.0 * neg_geo['stop_r'] * 10.0
zero_target_price = entry + 1.0 * zero_geo['target_r'] * 10.0
zero_stop_price = entry - 1.0 * zero_geo['stop_r'] * 10.0

# contrast: the guards that DO exist (risk_unit) — atr_ref=0 / atr_ref=-5
atr_rejections = {}
for atr in (0.0, -5.0):
    try:
        sim.run(draft({'atr_ref': atr, 'target_r': 1.0, 'stop_r': 1.0,
                       'expiry_bars': 8}), BARS)
        atr_rejections[str(atr)] = 'ACCEPTED (no raise)'
    except ValueError as e:
        atr_rejections[str(atr)] = f'ValueError: {str(e)[:60]}'

# downstream mislabeling: an endpoint-based hit-rate would count the -1.07R
# loss as a hit because the endpoint says TARGET.
endpoint_hit_rate = sum(
    1 for _o in (neg_outcome, zero_outcome)
    if _o['endpoint'] == 'TARGET') / 2.0

dynamic = {
    'entry_price': entry,
    'risk_unit_price': 10.0,
    'negative_target': {
        'geometry': neg_geo,
        'computed_target_price': neg_target_price,
        'computed_stop_price': neg_stop_price,
        'target_side_vs_entry': 'BELOW (wrong side for LONG)'
        if neg_target_price < entry else 'above',
        'outcome': neg_outcome,
    },
    'zero_stop': {
        'geometry': zero_geo,
        'computed_target_price': zero_target_price,
        'computed_stop_price': zero_stop_price,
        'stop_equals_entry': zero_stop_price == entry,
        'outcome': zero_outcome,
    },
    'atr_ref_rejections': atr_rejections,
    'endpoint_hit_rate_over_sample': endpoint_hit_rate,
}

# ---------------------------------------------------------------------------
# 3. bollinger_reversion Setup 3: RR = 0.5, breakeven win rate
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
    'setup3_observed_on_2500bar_window': None,  # set after the tape scan
    'note': 'RR=0.5 is source-derived from bollinger_reversion._geometry '
            '(stop_r = 2*sd/atr, target_r = sd/atr); if no Setup-3 (variant b) '
            'draft fired within the 2500-bar window, the sample is empty (the '
            'issue measured Setup 2/3 combined, n=82, on the full tape).',
}

# ---------------------------------------------------------------------------
# 4. LATENCY on the real tape: do any of the 27 experts ship bad geometry?
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
bollinger['setup3_observed_on_2500bar_window'] = len(setup3_drafts) > 0

evidence = {
    'issue': 70,
    'static': static,
    'dynamic': dynamic,
    'bollinger': bollinger,
    'latency': latency,
}
print(json.dumps(evidence, indent=2, sort_keys=True))
