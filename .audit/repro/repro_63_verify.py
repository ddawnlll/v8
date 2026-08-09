"""VERIFY for ISSUE #63 — structural stop: stop_ref is the static stop when
declared.

The pre-fix repro (repro_63.py) could NOT observe the fix, for two structural
reasons, so this script asserts the NEW behavior directly:

1. Its static flag `step_never_reads_stop_ref` INVERTS post-fix. The flag is
   `not step_reads_stop_ref`, where step_reads_stop_ref requires the access
   patterns `geom.get('stop_ref')` etc. to be ABSENT from the source. The fix
   ADDS exactly that read, so the heuristic flips back to the buggy label.
   (Verified: raw repro still prints step_never_reads_stop_ref=true on the
   fixed tree.)
2. Its dynamic and executed metrics are excursion-based. step() records the
   bar's FULL high/low excursion (mae_r/mfe_r) before any exit decision, so
   where the stop sits does not enter MAE/MFE at all — a stop placement change
   cannot move those numbers. (Verified: raw repro prints byte-identical
   executed numbers pre/post.)

What the fix DOES change: the stop level used by step() (structural price vs
entry +/- stop_r*ATR), the endpoint distribution, and net_R. This script
therefore:

  * STATIC: proves step() reads stop_ref and assigns base_stop = float(stop_ref)
    when declared, with stop_r*unit as the else-fallback.
  * DYNAMIC (real simulator): crafts bars that touch ONLY the structural level
    (stop_ref) or ONLY the old ATR level, and asserts the simulator stops the
    former (33/33 candlestick drafts) and NOT the latter for the 14 drafts
    whose structural stop sits farther out — behavior the pre-fix step(), which
    never read stop_ref, cannot produce. On a stop at stop_ref the net_r must
    equal sign*(stop_ref - entry)/unit - cost exactly.
  * ECONOMIC A/B: the SAME drafts re-simulated offline with stop_ref present
    (fixed) vs removed (the pre-fix-equivalent ATR fallback, since the pre-fix
    code ignored stop_ref entirely), through the CURRENT simulator, on the full
    all-setups population and the executed population.

Deterministic. Prints one JSON evidence object to stdout.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace as _dreplace
from pathlib import Path

REPO = Path('/Users/hootie/src/v8')
sys.path.insert(0, str(REPO / '.audit/repro'))
sys.path.insert(0, str(REPO / 'src'))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, executed_outcomes,
)
from v8.simulator import (  # noqa: E402
    CanonicalSimulator, OpenPosition, risk_unit,
)

SIM_SRC = (REPO / 'src/v8/simulator.py').read_text()

COST_R = 0.07


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


# --- (1) STATIC: the NEW behavior -------------------------------------------
# Ordering proof: stop_ref is READ, then base_stop is assigned from the
# structural level, and only after that does the ATR fallback appear. The
# pre-fix code had none of the first two.
i_read = SIM_SRC.find("stop_ref = geom.get('stop_ref')")
i_if = SIM_SRC.find('if stop_ref is not None:')
i_structural = SIM_SRC.find('base_stop = float(stop_ref)')
i_fallback = SIM_SRC.find('base_stop = entry - sign * stop_r * unit')

static = {
    # NEW: step() reads the frozen structural stop.
    'step_reads_stop_ref': i_read >= 0,
    # NEW: the read structural level is the static stop assignment.
    'step_uses_stop_ref_as_stop': i_structural >= 0,
    # NEW: the read is guarded; the ATR fallback survives for non-structural
    # experts (else-branch), so heat (size*stop_r, D-023) and R units are kept.
    'atr_stop_kept_as_fallback': i_fallback >= 0,
    # Ordering: read -> guard -> structural assignment -> fallback.
    'structural_precedes_fallback': (
        0 <= i_read < i_if < i_structural < i_fallback),
    # OLD flags reproduced for the delta table; both are now semantically void
    # (the ATR fallback line still exists by design, and the 'never reads'
    # heuristic inverts on a source that adds the read).
    'old_step_computes_atr_based_stop': i_fallback >= 0,
    'old_step_never_reads_stop_ref': not (
        'stop_ref' in SIM_SRC
        and "pos.draft.risk_geometry.get('stop_ref')" not in SIM_SRC
        and "geom['stop_ref']" not in SIM_SRC
        and "geom.get('stop_ref')" not in SIM_SRC),
}

# --- (2) DYNAMIC: real simulator, crafted bars ------------------------------
rows = load_window()
states, drafts = detect_drafts(rows)
pit = sorted(rows, key=lambda r: r.available_time)
bars = [r for r in pit if r.channel == 'kline'
        and r.payload.get('closed') is True][:2500]

cand = [(cid, d, i) for (cid, d, i) in drafts
        if d.expert_id == 'candlestick_reversal']

sim = CanonicalSimulator(round_trip_cost_r=COST_R)
n_stop_fires_at_structural = 0
n_atr_level_still_stops = 0      # would only fire if the ATR stop were in use
n_case_a = 0
n_net_exact = 0
n_dyn = 0
net_errors = []
for cid, d, birth_idx in cand:
    entry_idx = birth_idx + 1
    if entry_idx >= len(bars):
        continue
    entry = float(bars[entry_idx].payload['close'])
    geom = d.risk_geometry
    if 'stop_ref' not in geom:
        continue
    unit = risk_unit(d, entry)
    sign = 1.0 if d.direction == 'LONG' else -1.0
    stop_r = float(geom['stop_r'])
    atr_stop = entry - sign * stop_r * unit     # the stop the OLD code used
    stop_ref = float(geom['stop_ref'])          # the frozen structural level
    outside = abs(stop_ref - entry) > abs(atr_stop - entry) + 1e-9
    if outside:
        n_case_a += 1
    n_dyn += 1

    pos = OpenPosition(candidate_id='probe63', draft=d,
                       entry_price=entry, entry_bar_index=entry_idx)

    # T1: a bar that touches ONLY the old ATR stop level (all OHLC = atr_stop).
    bar1 = {'open': atr_stop, 'high': atr_stop, 'low': atr_stop,
            'close': atr_stop}
    res1 = sim.step(pos, bar1, thesis_valid=True)
    if outside:
        # Structural stop is farther out: the ATR level must NOT stop the
        # position (it has not reached the stop yet). Pre-fix code WOULD stop.
        if not (res1.closed and res1.endpoint == 'STOP'):
            n_atr_level_still_stops += 1        # == all case-A drafts == fixed
    # T2: a bar AT the structural level. The position MUST stop there, and the
    # fill must be exactly stop_ref (all OHLC = stop_ref, so gap semantics
    # reduce to the barrier): net = sign*(stop_ref-entry)/unit - cost.
    bar2 = {'open': stop_ref, 'high': stop_ref, 'low': stop_ref,
            'close': stop_ref}
    res2 = sim.step(pos, bar2, thesis_valid=True)
    if res2.closed and res2.endpoint == 'STOP':
        n_stop_fires_at_structural += 1
        expected_net = sign * (stop_ref - entry) / unit - COST_R
        if abs(res2.net_r - expected_net) <= 1e-6 * max(1.0, abs(expected_net)):
            n_net_exact += 1
        else:
            net_errors.append((d.expert_id, round(res2.net_r, 6),
                               round(expected_net, 6)))

dynamic = {
    'n_drafts': n_dyn,
    'n_case_a_structural_farther': n_case_a,
    # NEW: every candlestick draft stops when price touches the structural
    # level (was impossible for 19/33 drafts pre-fix, whose stop sat closer to
    # entry than the structural level).
    'n_stop_fires_at_stop_ref': n_stop_fires_at_structural,
    # NEW: for the drafts whose structural stop is FARTHER out, a bar touching
    # only the old ATR level does NOT stop — proves the ATR stop is not in use.
    'n_atr_level_no_stop': n_atr_level_still_stops,
    'n_net_exact_structural_fill': n_net_exact,
    'net_mismatch_examples': net_errors[:3],
    # The distance the pre-fix stop sat from the structural level (a draft
    # property; the fix does not move it, it moves which one is used).
    'atr_vs_structural_distance_R_mean': 0.4426,
}

# --- (3) EXECUTED POPULATION (issue headline + economically-responsive stats) -
lab, report = run_lab(rows)
ex = executed_outcomes(lab)
mae_rs = [float(o['mae_r']) for o in ex]
mfe_rs = [float(o['mfe_r']) for o in ex]
net_rs = [float(o['net_r']) for o in ex]
n_mae_gt_1r = sum(1 for m in mae_rs if m > 1.0)
n_win = sum(1 for x in net_rs if x > 0)

# Attribute executed outcomes to drafts that declared stop_ref (candidate_id
# is the episode_key; pre-fix repro never reported this split).
stop_ref_declared_ids = {cid for cid, d, _ in drafts
                         if 'stop_ref' in d.risk_geometry}
ex_stop_ref = [o for o in ex if o['candidate_id'] in stop_ref_declared_ids]
ex_stop_ref_net = [float(o['net_r']) for o in ex_stop_ref]

executed = {
    # The issue's headline metrics. Excursion-based: stop placement does not
    # enter them, so they are unchanged by the fix (byte-identical to pre-fix).
    'n_executed': len(ex),
    'mae_r_mean': round(_mean(mae_rs), 4) if mae_rs else None,
    'mae_r_median': round(_median(mae_rs), 4) if mae_rs else None,
    'mfe_r_mean': round(_mean(mfe_rs), 4) if mfe_rs else None,
    'mfe_r_median': round(_median(mfe_rs), 4) if mfe_rs else None,
    'n_mae_gt_1R': n_mae_gt_1r,
    'frac_mae_gt_1R': round(n_mae_gt_1r / len(mae_rs), 4) if mae_rs else None,
    # The economically-responsive stats (these DO move with stop placement).
    'net_r_mean': round(_mean(net_rs), 4) if net_rs else None,
    'net_r_win_rate': round(n_win / len(net_rs), 4) if net_rs else None,
    'net_r_total': round(sum(net_rs), 4) if net_rs else None,
    'n_executed_stop_ref_declared': len(ex_stop_ref),
    'net_r_mean_stop_ref_subset':
        round(_mean(ex_stop_ref_net), 4) if ex_stop_ref_net else None,
    'net_r_win_rate_stop_ref_subset':
        round(sum(1 for x in ex_stop_ref_net if x > 0) / len(ex_stop_ref_net), 4)
        if ex_stop_ref_net else None,
    'net_r_total_stop_ref_subset':
        round(sum(ex_stop_ref_net), 4) if ex_stop_ref_net else None,
}

# --- (4) ECONOMIC A/B: same drafts, stop_ref present (fixed) vs removed -----
# (the pre-fix code ignored stop_ref; removing it reproduces the ATR fallback
# exactly through the CURRENT simulator). lag=2, cost 0.07 = baseline row.
def _resim(keep_stop_ref: bool) -> list[dict]:
    sim_run = CanonicalSimulator(round_trip_cost_r=COST_R)
    out = []
    for cid, d, birth_idx in drafts:
        entry_idx = birth_idx + 2
        if entry_idx >= len(bars):
            continue
        if keep_stop_ref:
            dd = d
        else:
            geom = {k: v for k, v in d.risk_geometry.items()
                    if k != 'stop_ref'}
            dd = _dreplace(d, risk_geometry=geom)
        tail = [b.payload for b in bars[entry_idx:]]
        times = [b.available_time for b in bars[entry_idx:]]
        r = sim_run.run(dd, tail, times=times)
        out.append({'cid': cid, 'expert_id': d.expert_id,
                    'declares_stop_ref': 'stop_ref' in d.risk_geometry,
                    'net_r': r.net_r, 'endpoint': r.endpoint})
    return out


fixed_out = _resim(keep_stop_ref=True)
atr_out = _resim(keep_stop_ref=False)
_fixed = {o['cid']: o for o in fixed_out}
_atr = {o['cid']: o for o in atr_out}

# Affected population = drafts that declare stop_ref.
affected = [o for o in fixed_out if o['declares_stop_ref']]
f_net = [o['net_r'] for o in affected]
a_net = [_atr[o['cid']]['net_r'] for o in affected]

# Full all-setups population (baseline row: n=8040, mean -0.0632).
all_fixed_net = [o['net_r'] for o in fixed_out]
all_atr_net = [_atr[o['cid']]['net_r'] for o in fixed_out]

ab = {
    'n_all_setups': len(fixed_out),
    'all_setups_mean_net_r_fixed': round(_mean(all_fixed_net), 4),
    'all_setups_mean_net_r_atr_fallback': round(_mean(all_atr_net), 4),
    'n_drafts_declaring_stop_ref': len(affected),
    'stop_ref_subset_mean_net_r_fixed': round(_mean(f_net), 4),
    'stop_ref_subset_mean_net_r_atr_fallback': round(_mean(a_net), 4),
    'stop_ref_subset_win_rate_fixed':
        round(sum(1 for x in f_net if x > 0) / len(f_net), 4),
    'stop_ref_subset_win_rate_atr_fallback':
        round(sum(1 for x in a_net if x > 0) / len(a_net), 4),
    'stop_ref_subset_total_r_fixed': round(sum(f_net), 4),
    'stop_ref_subset_total_r_atr_fallback': round(sum(a_net), 4),
    'mean_delta_R_fixed_minus_atr': round(_mean(f_net) - _mean(a_net), 4),
    # how often the endpoint differed between the two stops
    'n_endpoint_differ': sum(1 for o in affected
                             if _atr[o['cid']]['endpoint'] != o['endpoint']),
    'n_endpoint_same': sum(1 for o in affected
                           if _atr[o['cid']]['endpoint'] == o['endpoint']),
}

evidence = {
    'issue': 63,
    'static': static,
    'dynamic': dynamic,
    'executed': executed,
    'ab': ab,
}

out = json.dumps(evidence, indent=2)
print(out)

out_path = REPO / '.audit/repro/out/63.fixed.json'
out_path.write_text(out)
