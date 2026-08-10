"""V8 x Recoverable Regret v0.2 — Phase 3: recoverability evaluation.

Implements `reports/accp/v8-rr-v02-phase0/source/FCR-V8RR-009.accp.yaml`
exactly. Tests whether each of Phase 2's confirmed SYSTEMATIC_FINDING slices
is recoverable within a small, declared, decision-time policy class — never
whether it is profitable (that claim stays blocked, rule 12).

Performs NO replay of its own: every utility number consumed here is
already in the certified Phase-0 cube (tools/regret.py). This module's only
job is enumerating and selecting among a small policy class, and estimating
the selected policy's value on the PROTECTED confirmation half — reusing
v8.statistics for every estimator, exactly as Phase 2 does.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO))

from v8.schema import sha1_hex
from v8.store import AppendOnlyLog
from v8.statistics import select_block_size, bootstrap_ci

from tools.regret_phase2 import N_RESAMPLES, CI, MIN_NET_R, _seed_for

# FCR-V8RR-009 FT002 — frozen, declared BEFORE any slice is scored.
FEATURES = ('rsi14', 'bb_pct_b', 'adx14')
GATE_DIRECTIONS = ('NO_TRADE_BELOW', 'NO_TRADE_ABOVE')
QUANTILES = (0.2, 0.4, 0.6, 0.8)

RECOVERABLE_WITHIN_CLASS = 'RECOVERABLE_WITHIN_CLASS'
NOT_RECOVERABLE_WITHIN_CLASS = 'NOT_RECOVERABLE_WITHIN_CLASS'


@dataclass(frozen=True)
class PolicySpec:
    policy_id: str
    kind: str            # ALWAYS_TRADE | THRESHOLD_GATE
    feature: str | None
    direction: str | None
    threshold: float | None


def _feature_value(state_rec: dict, symbol: str, feature: str) -> float | None:
    fv = state_rec.get('features', {}).get(f'{symbol}.{feature}')
    if fv is None:
        return None
    v = fv.get('value')
    return float(v) if isinstance(v, (int, float)) else None


def _load_birth_features(store_dir: Path, symbol: str) -> dict:
    """candidate_id -> {feature: value}, read from each candidate's OWN
    birth_state_id (FT001: never a later clock, never recomputed)."""
    trans = AppendOnlyLog(store_dir / 'candidates.jsonl').read()
    birth_state_id = {r['candidate_id']: r.get('state_id')
                      for r in trans if r.get('to_state') == 'DETECTED'}
    states_by_id = {}
    for rec in AppendOnlyLog(store_dir / 'states.jsonl').read():
        if rec['state_id'] in set(birth_state_id.values()):
            states_by_id[rec['state_id']] = rec

    out = {}
    for cid, sid in birth_state_id.items():
        st = states_by_id.get(sid)
        if st is None:
            continue
        out[cid] = {f: _feature_value(st, symbol, f) for f in FEATURES}
    return out


def declare_policies(discovery_series_by_feature: dict) -> list[PolicySpec]:
    """FT002: 1 + 3*2*4 = 25 policies. Thresholds are the DISCOVERY-half
    quantile of each feature — computed once per slice, never per-candidate."""
    policies = [PolicySpec('ALWAYS_TRADE', 'ALWAYS_TRADE', None, None, None)]
    for feature in FEATURES:
        values = sorted(v for v in discovery_series_by_feature.get(feature, [])
                        if v is not None)
        if not values:
            continue
        for q in QUANTILES:
            idx = min(len(values) - 1, max(0, int(len(values) * q)))
            threshold = values[idx]
            for direction in GATE_DIRECTIONS:
                pid = f'THRESHOLD_GATE|{feature}|{direction}|{threshold:.6g}|q{q}'
                policies.append(PolicySpec(pid, 'THRESHOLD_GATE', feature, direction, threshold))
    return policies


def apply_policy(policy: PolicySpec, feature_values: dict, actual_utility: float) -> float:
    """Returns the policy's utility for one Candidate. THRESHOLD_GATE selects
    NO_TRADE (utility 0.0, FCR-V8RR-004 FT011i) when it fires; otherwise the
    Candidate's already-replayed actual utility — no new replay."""
    if policy.kind == 'ALWAYS_TRADE':
        return actual_utility
    v = feature_values.get(policy.feature)
    if v is None:
        return actual_utility   # feature unavailable at this clock: gate cannot fire, trade proceeds
    fires = (v < policy.threshold) if policy.direction == 'NO_TRADE_BELOW' \
        else (v > policy.threshold)
    return 0.0 if fires else actual_utility


def evaluate_slice_recoverability(slice_key: str, expert_id: str, symbol: str,
                                  direction: str, store_dir: Path,
                                  discovery_rows: list, confirmation_rows: list,
                                  out_dir: Path) -> dict:
    disc = [r for r in discovery_rows if r['expert_id'] == expert_id
           and r['symbol'] == symbol and r['direction'] == direction
           and r['gap_status'] == 'COMPUTED']
    conf = [r for r in confirmation_rows if r['expert_id'] == expert_id
           and r['symbol'] == symbol and r['direction'] == direction
           and r['gap_status'] == 'COMPUTED']

    birth_features = _load_birth_features(store_dir, symbol)
    disc_features_by_cid = {r['candidate_id']: birth_features.get(r['candidate_id'], {})
                            for r in disc}
    disc_series_by_feature = {f: [disc_features_by_cid[r['candidate_id']].get(f)
                                  for r in disc] for f in FEATURES}
    policies = declare_policies(disc_series_by_feature)

    attempt_rows = []
    best_policy, best_mean = None, None
    for policy in policies:
        utils = []
        for r in disc:
            fv = disc_features_by_cid.get(r['candidate_id'], {})
            utils.append(apply_policy(policy, fv, r['actual_utility']))
        mean_u = sum(utils) / len(utils) if utils else None
        attempt_rows.append({'slice_key': slice_key, 'stage': 'discovery_selection',
                             **asdict(policy), 'n': len(utils), 'mean_utility': mean_u})
        if mean_u is not None and (best_mean is None or mean_u > best_mean):
            best_policy, best_mean = policy, mean_u

    conf_features_by_cid = {r['candidate_id']: birth_features.get(r['candidate_id'], {})
                            for r in conf}
    deltas = []
    for r in conf:
        fv = conf_features_by_cid.get(r['candidate_id'], {})
        policy_u = apply_policy(best_policy, fv, r['actual_utility'])
        deltas.append(policy_u - r['actual_utility'])

    v_a = sum(r['actual_utility'] for r in conf) / len(conf) if conf else None
    v_r = (v_a + sum(deltas) / len(deltas)) if (conf and v_a is not None) else None
    g_r = (sum(deltas) / len(deltas)) if deltas else None

    if deltas and any(d != 0.0 for d in deltas):
        block = select_block_size(deltas)
        seed = _seed_for(slice_key + '|phase3')
        ci_lower, ci_upper = bootstrap_ci(deltas, block, N_RESAMPLES, seed, ci=CI)
    else:
        ci_lower = ci_upper = 0.0

    verdict = RECOVERABLE_WITHIN_CLASS if (g_r is not None and ci_lower > 0.0
                                          and g_r >= MIN_NET_R) else NOT_RECOVERABLE_WITHIN_CLASS
    result = {
        'slice_key': slice_key, 'expert_id': expert_id, 'symbol': symbol,
        'direction': direction, 'n_discovery': len(disc), 'n_confirmation': len(conf),
        'selected_policy': asdict(best_policy) if best_policy else None,
        'discovery_selection_mean_utility': best_mean,
        'confirmation_v_a': v_a, 'confirmation_v_r': v_r,
        'confirmation_g_r': g_r, 'confirmation_g_r_ci_lower': ci_lower,
        'confirmation_g_r_ci_upper': ci_upper, 'recoverability_verdict': verdict,
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'recoverability_attempts.jsonl').open('a', encoding='utf-8') as fh:
        for a in attempt_rows:
            fh.write(json.dumps(a, sort_keys=True, default=str) + '\n')
        fh.write(json.dumps({**result, 'stage': 'confirmation_result'},
                            sort_keys=True, default=str) + '\n')
    return result


def run_phase3(confirmed_slice_keys: list, discovery_rows: list,
              confirmation_rows: list, store_dirs: dict, out_dir: Path) -> dict:
    out = Path(out_dir)
    results = []
    for key in confirmed_slice_keys:
        expert_id, symbol, direction, estimand = key.split('|')
        result = evaluate_slice_recoverability(
            key, expert_id, symbol, direction, Path(store_dirs[symbol]),
            discovery_rows, confirmation_rows, out)
        results.append(result)

    recoverable = [r for r in results if r['recoverability_verdict'] == RECOVERABLE_WITHIN_CLASS]
    summary = {
        'n_slices_tested': len(results),
        'n_recoverable_within_class': len(recoverable),
        'n_not_recoverable_within_class': len(results) - len(recoverable),
        'recoverable_slices': [r['slice_key'] for r in recoverable],
        'results': results,
    }
    (out / 'phase3_summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, default=str) + '\n', encoding='utf-8')
    return summary
