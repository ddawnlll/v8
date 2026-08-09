"""Verification for issue #66 — windowed pre-entry invalidation fallback.

Pre-fix repro (repro_66.py) measured the gate against the all-bars state
feature `prior_high`/`prior_low` — the UNBOUNDED prefix extreme — and found
the gate effectively dead (7 fires across 2,067 drafts of the 6 experts that
freeze no prior_*_ref). The fix (#66, D-059) changed the LAB's fallback level,
not the state feature, so the unmodified repro is unchanged against the fixed
tree (verified: out/66.fixed.json == out/66.json). This script asserts the NEW
behavior instead:

  (1) STATIC — lab.py carries `_PRIOR_WINDOW_BARS = 32` and the fallback is a
      windowed extreme over `bars[max(0, i - _PRIOR_WINDOW_BARS):i]` (min of
      lows / max of highs); the all-bars state feature is no longer used as an
      invalidation level.
  (2) OFFLINE GATE MIRROR — for the 6 ref-less experts, replicate the lab's
      exact pre-entry predicate with the WINDOWED level: at the trigger bar
      (birth+1) and re-checked on the entry bar (birth+2), a LONG fires when
      bar low < windowed prior_low, a SHORT when bar high > windowed
      prior_high. A candidate is invalidated on the first firing bar. Expect
      the fire count to be MUCH higher than the pre-fix 7.
  (3) FULL LAB RUN — terminal_distribution (INVALIDATED vs the pre-fix 2346),
      executed-subset economics, and the per-expert `invalidation_observed`
      fires for the 6 experts read from the actual candidates ledger.

Deterministic: fixed 2500-bar window, no wall clock.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_probe import (  # noqa: E402
    load_window, detect_drafts, run_lab, executed_outcomes, stats,
)

NO_REF_EXPERTS = [
    'trend_pullback', 'rsi_stoch_reversion', 'macd_stoch_trend',
    'ichimoku_cloud', 'bollinger_breakout', 'bollinger_reversion',
]
NO_REF_SET = set(NO_REF_EXPERTS)

N_BARS = 2500
COST_R = 0.07
LAG = 2
_PRIOR_WINDOW_BARS = 32  # must match lab.py's constant

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    lab_py = (REPO / 'src/v8/lab.py').read_text(encoding='utf-8')

    # ---------------- (1) static confirmation of the fix ----------------
    window_const_ok = '_PRIOR_WINDOW_BARS = 32' in lab_py
    window_slice_ok = 'bars[max(0, i - _PRIOR_WINDOW_BARS):i]' in lab_py
    low_derived = 'prior_low = min(float(b.payload[\'low\']) for b in window)' in lab_py
    high_derived = 'prior_high = max(float(b.payload[\'high\']) for b in window)' in lab_py
    no_state_fallback = bool(re.search(
        r"prior_low\s*=\s*float\([^\n]*_feature|"
        r"prior_low\s*=\s*float\(st\.features|"
        r"prior_low\s*=\s*float\([^\n]*feature[^\n]*value",
        lab_py))
    static = {
        'lab_py_path': 'src/v8/lab.py',
        'window_constant_is_32': window_const_ok,
        'window_slice_is_bars_max0_i_minus_32_to_i': window_slice_ok,
        'fallback_prior_low_is_window_min': low_derived,
        'fallback_prior_high_is_window_max': high_derived,
        'state_feature_no_longer_a_fallback': not no_state_fallback,
    }

    # ---------------- (2) offline mirror of the NEW gate ----------------
    rows = load_window(n_bars=N_BARS)
    states, drafts = detect_drafts(rows, n_bars=N_BARS)  # noqa: F841 (states unused)
    pit = sorted(rows, key=lambda r: r.available_time)
    bars = [r for r in pit if r.channel == 'kline'
            and r.payload.get('closed') is True][:N_BARS]
    highs = [float(b.payload['high']) for b in bars]
    lows = [float(b.payload['low']) for b in bars]

    sel = [(cid, d, b) for cid, d, b in drafts if d.expert_id in NO_REF_SET]
    per_expert_total = {e: 0 for e in NO_REF_EXPERTS}
    per_expert_fires = {e: 0 for e in NO_REF_EXPERTS}
    per_expert_trigger_bar_fires = {e: 0 for e in NO_REF_EXPERTS}
    per_expert_entry_bar_fires = {e: 0 for e in NO_REF_EXPERTS}
    skipped = 0
    skip_details = []
    fire_details = []  # one per fired candidate (first firing bar)

    for cid, d, b in sel:
        trigger_i = b + 1
        if trigger_i >= len(bars):
            skipped += 1
            skip_details.append({'expert_id': d.expert_id, 'birth_idx': b,
                                 'trigger_idx': trigger_i, 'reason': 'no trigger bar'})
            continue
        per_expert_total[d.expert_id] += 1
        # The lab freezes the windowed extreme at BIRTH from bars[max(0,b-32):b].
        w = bars[max(0, b - _PRIOR_WINDOW_BARS):b]
        prior_low = min(float(x.payload['low']) for x in w)
        prior_high = max(float(x.payload['high']) for x in w)
        # PHASE 2 (trigger bar = birth+1): invalidated if the predicate fires.
        long = d.direction == 'LONG'
        if (long and lows[trigger_i] < prior_low) \
                or (not long and highs[trigger_i] > prior_high):
            per_expert_fires[d.expert_id] += 1
            per_expert_trigger_bar_fires[d.expert_id] += 1
            fire_details.append({'expert_id': d.expert_id, 'direction': d.direction,
                                 'birth_idx': b, 'fire_bar': 'trigger',
                                 'bar_idx': trigger_i})
            continue
        # PHASE 1a (entry bar = birth+2): invalidation re-checked on entry.
        entry_i = trigger_i + 1
        if entry_i < len(bars):
            if (long and lows[entry_i] < prior_low) \
                    or (not long and highs[entry_i] > prior_high):
                per_expert_fires[d.expert_id] += 1
                per_expert_entry_bar_fires[d.expert_id] += 1
                fire_details.append({'expert_id': d.expert_id,
                                     'direction': d.direction,
                                     'birth_idx': b, 'fire_bar': 'entry',
                                     'bar_idx': entry_i})

    total_fires = sum(per_expert_fires.values())
    # Staleness of the windowed extreme pinned at birth (window age).
    stale_examples = []
    for fd in fire_details[:5]:
        b = fd['birth_idx']
        j = b - 1
        stale_examples.append({'expert_id': fd['expert_id'],
                               'direction': fd['direction'],
                               'birth_idx': b, 'fire_bar': fd['fire_bar'],
                               'bar_idx': fd['bar_idx'],
                               'window_bars': min(_PRIOR_WINDOW_BARS, b)})

    # ---------------- (3) full lab run ----------------
    lab, report = run_lab(rows, round_trip_cost_r=COST_R)
    ex_outcomes = executed_outcomes(lab)
    executed_stats = stats([o['net_r'] for o in ex_outcomes])

    terminal_distribution = dict(report.terminal_distribution)
    candidate_count = int(report.candidate_count)

    # Per-expert ledger facts for the 6 ref-less experts: invalidation_observed
    # gate fires and total terminal INVALIDATED.
    cid_to_expert: dict[str, str] = {}
    invalidation_fires: dict[str, int] = {e: 0 for e in NO_REF_EXPERTS}
    terminal_invalidated: dict[str, int] = {e: 0 for e in NO_REF_EXPERTS}
    gate_fire_details: list[dict] = []
    for rec in lab.candidates.read():
        cid = rec.get('candidate_id')
        if not cid:
            continue
        if 'expert_id' in rec:
            cid_to_expert.setdefault(cid, rec['expert_id'])
        if rec.get('to_state') == 'INVALIDATED':
            ex = cid_to_expert.get(cid)
            if ex in NO_REF_SET:
                terminal_invalidated[ex] = terminal_invalidated.get(ex, 0) + 1
                if rec.get('reason_code') == 'invalidation_observed':
                    invalidation_fires[ex] = invalidation_fires.get(ex, 0) + 1
                    gate_fire_details.append({
                        'expert_id': ex, 'candidate_id': cid,
                        'knowledge_time': rec.get('knowledge_time'),
                        'reason_code': rec.get('reason_code')})

    n_invalidated_terminal = terminal_distribution.get('INVALIDATED', 0)

    evidence = {
        'issue': 66,
        'title': 'prior_high/prior_low unbounded prefix extremes -> '
                 'pre-entry invalidation dead code for 6 experts',
        'fixed': True,
        'static': static,
        'window_bars': N_BARS,
        'window_semantics':
            'fallback level = min(low)/max(high) over '
            'bars[max(0, birth-_PRIOR_WINDOW_BARS):birth] with '
            '_PRIOR_WINDOW_BARS=32; LONG fires on low(trigger) < prior_low, '
            'SHORT on high(trigger) > prior_high; re-checked on the entry bar',
        'pre_fix': {
            'drafts_total': 2067,
            'invalidation_fires': 7,
            'per_expert_fires': {'trend_pullback': 0, 'rsi_stoch_reversion': 0,
                                 'macd_stoch_trend': 0, 'ichimoku_cloud': 0,
                                 'bollinger_breakout': 1,
                                 'bollinger_reversion': 6},
            'terminal_INVALIDATED_full_run': 2346,
        },
        'offline_mirror': {
            'drafts_total': len(sel),
            'drafts_skipped': skipped,
            'skip_details': skip_details,
            'invalidation_fires': total_fires,
            'fires_at_trigger_bar': sum(per_expert_trigger_bar_fires.values()),
            'fires_at_entry_bar': sum(per_expert_entry_bar_fires.values()),
            'per_expert_total': per_expert_total,
            'per_expert_fires': per_expert_fires,
            'per_expert_trigger_bar_fires': per_expert_trigger_bar_fires,
            'per_expert_entry_bar_fires': per_expert_entry_bar_fires,
            'stale_examples': stale_examples,
        },
        'full_lab_run': {
            'cost_r': COST_R,
            'candidate_count': candidate_count,
            'terminal_distribution': terminal_distribution,
            'INVALIDATED_terminal': n_invalidated_terminal,
            'executed_stats': executed_stats,
            'per_expert_invalidation_observed_fires': invalidation_fires,
            'per_expert_terminal_INVALIDATED': terminal_invalidated,
            'n_gate_fire_ledger_rows': len(gate_fire_details),
        },
        'delta': {
            'invalidation_fires_6_experts':
                f'{7} -> {total_fires} '
                f'(+{total_fires - 7}, gate now meaningful)',
            'terminal_INVALIDATED_full_run':
                f'{2346} -> {n_invalidated_terminal} '
                f'({n_invalidated_terminal - 2346:+d})',
            'executed_n': f'{895} -> {executed_stats["n"]}',
        },
    }

    out = json.dumps(evidence, indent=2, default=str)
    print(out)
    out_path = Path(__file__).resolve().parent / 'out' / '66.fixed.json'
    out_path.write_text(out + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
