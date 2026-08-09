"""Repro for issue #66 — prior_high/prior_low are UNBOUNDED prefix extremes,
so the lab's pre-entry invalidation gate is dead code for the 6 experts that
do not freeze their own prior_high_ref/prior_low_ref.

Static leg (verified against the current tree):
  * src/v8/marketstate.py:761-762 — series path computes a RUNNING prefix
    max/min over the whole tape (ph.append(ph[-1] if ph[-1] >= highs[j]
    else highs[j])), i.e. all-time extremes, never a window.
  * src/v8/marketstate.py:951 — comment: "prior_high/prior_low are the
    UNBOUNDED prefix extremes".
  * src/v8/lab.py:753-756 — pre-entry invalidation level falls back to the
    all-bars state feature when the draft geometry has no frozen ref.

Dynamic leg: detect_drafts over the first 2500 closed bars of the real tape,
then for every draft of the 6 no-frozen-ref experts, at the trigger bar
(birth_idx+1) test the invalidation predicate against the unbounded prefix
extreme:
    LONG : low(trigger) < prior_low(prefix [0..trigger-1])
    SHORT: high(trigger) > prior_high(prefix [0..trigger-1])
A fire requires a NEW ALL-TIME low / high on the trigger bar. We also test the
lab-mechanism-exact variant using the BIRTH-bar level (prefix [0..birth-1]),
which is what Lab.run() actually freezes into `pending[cid]`.

Deterministic: fixed window, no wall clock.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_probe import load_window, detect_drafts, SYMBOL  # noqa: E402

NO_REF_EXPERTS = [
    'trend_pullback', 'rsi_stoch_reversion', 'macd_stoch_trend',
    'ichimoku_cloud', 'bollinger_breakout', 'bollinger_reversion',
]
NO_REF_SET = set(NO_REF_EXPERTS)

N_BARS = 2500
rows = load_window(n_bars=N_BARS)
states, drafts = detect_drafts(rows, n_bars=N_BARS)

pit = sorted(rows, key=lambda r: r.available_time)
bars = [r for r in pit if r.channel == 'kline'
        and r.payload.get('closed') is True][:N_BARS]
highs = [float(b.payload['high']) for b in bars]
lows = [float(b.payload['low']) for b in bars]


def _last_argmax(hi):
    m = max(highs[:hi + 1])
    for j in range(hi, -1, -1):
        if highs[j] == m:
            return j
    return None


def _last_argmin(hi):
    m = min(lows[:hi + 1])
    for j in range(hi, -1, -1):
        if lows[j] == m:
            return j
    return None


def _feature(st, name):
    fv = st.features.get(f'{SYMBOL}.{name}')
    return None if fv is None else fv.value


# Filter drafts to the 6 no-frozen-ref experts.
sel = [(cid, d, b) for cid, d, b in drafts if d.expert_id in NO_REF_SET]
drafts_total = len(sel)

fires_birth_level = 0     # lab-exact: level frozen at birth (prefix [0..b-1])
fires_trigger_level = 0   # issue-specified: state feature at trigger bar
skipped = 0               # trigger bar missing / level None (not computable)
per_expert_total = {e: 0 for e in NO_REF_SET}
per_expert_fires = {e: 0 for e in NO_REF_SET}
staleness_examples = []
mismatch_feature_vs_payload = 0
fire_details = []         # each fire: birth_idx, staleness of pinned extreme
drafts_past_warmup = 0    # drafts with birth_idx >= 30 (prefix no longer tiny)
fires_past_warmup = 0
skip_details = []

for cid, d, b in sel:
    i = b + 1                       # trigger bar (PHASE 2 evaluates at birth+1)
    if i >= len(bars):
        skipped += 1
        skip_details.append({'expert_id': d.expert_id, 'birth_idx': b,
                             'trigger_idx': i, 'reason': 'no trigger bar'})
        continue
    per_expert_total[d.expert_id] += 1
    if b >= 30:
        drafts_past_warmup += 1
    low_i, high_i = lows[i], highs[i]

    # ---- issue-specified check: state feature at the trigger bar ----------
    st = states[bars[i].available_time]
    pl = _feature(st, 'prior_low')
    ph = _feature(st, 'prior_high')
    if pl is None or ph is None:
        skipped += 1
        skip_details.append({'expert_id': d.expert_id, 'birth_idx': b,
                             'trigger_idx': i, 'reason': 'level None'})
        continue
    # cross-check: the state feature must equal the pure prefix extreme
    # over bars[0..i-1] (the running prefix min/max, excluding bar i).
    if abs(pl - min(lows[:i])) > 1e-9 or abs(ph - max(highs[:i])) > 1e-9:
        mismatch_feature_vs_payload += 1
    fired_trigger = (d.direction == 'LONG' and low_i < pl) \
        or (d.direction == 'SHORT' and high_i > ph)
    if fired_trigger:
        fires_trigger_level += 1
        per_expert_fires[d.expert_id] += 1

    # ---- lab-exact check: level frozen at birth (prefix [0..b-1]) ---------
    fired_birth = False
    if b >= 1:
        if d.direction == 'LONG':
            fired_birth = low_i < min(lows[:b])
        else:
            fired_birth = high_i > max(highs[:b])
        if fired_birth:
            fires_birth_level += 1

    # ---- staleness: age of the all-time extreme pinned at the birth bar ----
    if fired_trigger or fired_birth:
        j = None
        if b >= 1:
            if d.direction == 'LONG':
                j = _last_argmin(b - 1)
            else:
                j = _last_argmax(b - 1)
        fire_details.append({
            'expert_id': d.expert_id, 'direction': d.direction,
            'birth_idx': b, 'trigger_idx': i,
            'extreme_set_bar_idx': j,
            'staleness_bars': (b - j) if j is not None else None,
        })
    if b >= 30 and (fired_trigger or fired_birth):
        fires_past_warmup += 1
    if b >= 1:
        if d.direction == 'LONG':
            j = _last_argmin(b - 1)
        else:
            j = _last_argmax(b - 1)
        if j is not None and len(staleness_examples) < 3:
            staleness_examples.append({
                'expert_id': d.expert_id, 'direction': d.direction,
                'birth_idx': b, 'extreme_set_bar_idx': j,
                'staleness_bars': b - j,
                'extreme_price': lows[j] if d.direction == 'LONG' else highs[j],
                'trigger_low': low_i, 'trigger_high': high_i,
            })

evidence = {
    'issue': 66,
    'title': 'prior_high/prior_low unbounded prefix extremes -> '
             'pre-entry invalidation dead code for 6 experts',
    'static':
        'series path src/v8/marketstate.py:761-762 is a running all-time '
        'prefix max/min (ph.append(ph[-1] if ph[-1] >= highs[j] else '
        'highs[j])); comment at :951 "prior_high/prior_low are the '
        'UNBOUNDED prefix extremes"; lab.py:753-756 falls back to the '
        'all-bars state feature when no prior_*_ref frozen.',
    'experts_without_frozen_ref': NO_REF_EXPERTS,
    'experts_without_frozen_ref_count': len(NO_REF_EXPERTS),
    'drafts_total': drafts_total,
    'drafts_skipped': skipped,
    'invalidation_fires_birth_level': fires_birth_level,
    'invalidation_fires_trigger_level': fires_trigger_level,
    'drafts_past_warmup_ge30': drafts_past_warmup,
    'fires_past_warmup_ge30': fires_past_warmup,
    'fire_details': fire_details,
    'skip_details': skip_details,
    'per_expert_total': per_expert_total,
    'per_expert_fires': per_expert_fires,
    'example_staleness_bars': staleness_examples,
    'feature_vs_payload_mismatches': mismatch_feature_vs_payload,
    'window_bars': N_BARS,
}

out = Path(__file__).resolve().parent / 'out'
out.mkdir(exist_ok=True)
(out / '66.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2))
