#!/usr/bin/env python3
"""Pre-holdout dev-window diagnostic sweep (NOT the preregistered OOS run).

Runs every registered expert family (registry primary variant) through the Lab
on the materialized 12-month BTCUSDT dev tape (D-041 window) and applies the
preregistered D-045 detrended-null machinery (METH-1/2/4/6) to the executed
episodes.

This is a DIAGNOSTIC, not the frozen OOS evaluation: dev-window results are
in-sample and carry the selection bias D-044 / METH-2 exist to control. The
verdict stays NO_ECONOMIC_CLAIM until the frozen holdout opens and the D-027
authority gate passes (rule 12, prereg §16). It also surfaces, for the first
time, whether the preregistered statistics run at all against a real LabReport
(the gap D-044 flagged: "statistics.py is unit-tested on synthetic data only,
not yet exercised against a real LabReport").

Usage: .venv/bin/python tools/diagnose_experts_dev.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import yaml  # dev/tooling only (D-031: never on the decision path)

import run_experiment as runner  # reuse _block_size / N_RESAMPLES / seeds
from v8.experts.base import Expert
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.statistics import (EpisodeExposure, block_bootstrap_means,
                           detrend_net_r, mean_log_drift_per_bar)
from v8.store import AppendOnlyLog

TAPE = ROOT / 'research/tape/btcusdt-1h-12m/tape.jsonl'
REGISTRY = ROOT / 'docs/EXPERTS_REGISTRY.yaml'
STORE = Path('/tmp/v8-diagnostic-dev-store')

# Cross-family Bonferroni alpha, D-044 (rule unchanged; F = preregistered
# families post-D-050). The two-pilot runner hardcodes 0.05/2; a diagnostic
# over the full preregistered slate must use the slate's own F.
N_FAMILIES = 28
ALPHA_F = 0.05 / N_FAMILIES
MIN_EPISODES = runner.MIN_EPISODES          # prereg §12: n_f >= 30
# D-052: the bound is the int(N * alpha_f)-th smallest resample mean. This
# slate's alpha_f is 0.05/28, where the runner's 2000 put that index at 3 —
# the 4th-smallest draw standing in for a 0.18th percentile. Tied to alpha.
N_RESAMPLES = runner.resamples_for_alpha(ALPHA_F)
BOOTSTRAP_SEED = runner.BOOTSTRAP_SEED      # 7


def _effective_search_size(n_variants: int, universe_size: int) -> int:
    """METH-2 / D-046: the honest family size for multiplicity lines —
    max(variants_evaluated, search_universe_size), never less than declared."""
    return max(n_variants, universe_size)


def _expected_false_positives(eff_size: int, alpha_f: float) -> float:
    """METH-6 / G-11: expected false positives by chance at this alpha."""
    return eff_size * alpha_f


def _discover_families() -> dict[str, dict]:
    """expert_id -> {cls, mechanism_family_id, variant_id, search accounting}
    for every registered expert that has code (27 of 28: `capitulation` is
    DATA_BLOCKED with no code module by D-050)."""
    import v8.experts as exmod
    reg = yaml.safe_load(REGISTRY.read_text(encoding='utf-8'))
    by_id = {e['expert_id']: e for e in reg['experts']}
    classes: dict[str, list[type]] = {}
    for name in dir(exmod):
        obj = getattr(exmod, name)
        if (isinstance(obj, type) and issubclass(obj, Expert)
                and obj is not Expert and obj.expert_id):
            classes.setdefault(obj.expert_id, []).append(obj)
    out: dict[str, dict] = {}
    for eid in sorted(classes):
        entry = by_id[eid]
        prim = entry.get('variant_id')
        pick = next((c for c in classes[eid] if c.variant_id == prim), None) \
            or sorted(classes[eid], key=lambda c: c.variant_id)[0]
        n_variants = len(entry.get('variants_evaluated') or [pick.variant_id])
        out[eid] = {
            'cls': pick,
            'mechanism_family_id': entry.get('mechanism_family_id', ''),
            'variant_id': pick.variant_id,
            'search_universe_size': int(entry.get('search_universe_size', 1)),
            'variants_evaluated': n_variants,
        }
    return out


def _family_exposures(store_dir: Path,
                      families: dict[str, dict]) -> dict[str, list[EpisodeExposure]]:
    """Per expert_id, the executed episodes (label_status != NOT_EXECUTED),
    grouped by the candidate's expert. Mirrors the frozen runner's
    `_family_exposures` (D-045: R unit from the outcome, direction from the
    candidate record — never re-derived)."""
    candidates = [json.loads(l) for l in
                  (store_dir / 'candidates.jsonl').read_text().splitlines()]
    outcomes = {o['candidate_id']: o for o in (
        json.loads(l) for l in (store_dir / 'outcomes.jsonl').read_text().splitlines())}
    out: dict[str, list[EpisodeExposure]] = {eid: [] for eid in families}
    seen: set[str] = set()
    for rec in candidates:
        cid = rec['candidate_id']
        if cid in seen:
            continue
        seen.add(cid)
        eid = rec.get('expert_id')
        if eid not in out:
            continue
        o = outcomes.get(cid)
        if o is None or o.get('label_status') == 'NOT_EXECUTED':
            continue
        if not float(o.get('risk_unit_price', 0.0)) > 0:
            raise ValueError(
                f'executed outcome {cid} carries no risk_unit_price: pre-D-045 '
                'ledger cannot be detrended — fail closed')
        out[eid].append(EpisodeExposure(
            net_r=float(o['net_r']), direction=rec['direction'],
            entry_price=float(o['entry_price']),
            risk_unit_price=float(o['risk_unit_price']),
            horizon_bars=int(o['horizon_bars'])))
    return out


def _lower_bound(net_rs: list[float], alpha_f: float = ALPHA_F):
    """Prereg §9 mechanical block bootstrap, one-sided lower bound at alpha_f
    via the fixed seed (D-052: alpha_f-th percentile, never 2.5 — the old name
    said 2.5 while the code always used alpha_f). Empty sample -> (0.0, 0)."""
    if not net_rs:
        return 0.0, 0
    block = runner._block_size(net_rs)
    means = block_bootstrap_means(net_rs, block, N_RESAMPLES, BOOTSTRAP_SEED)
    means.sort()
    idx = int(N_RESAMPLES * alpha_f)
    return means[idx], block


def main() -> int:
    families = _discover_families()
    print(f'families with code: {len(families)} / registry 28 '
          f'(capitulation: DATA_BLOCKED no-code, D-050); '
          f'Bonferroni F = {N_FAMILIES}, alpha_f = {ALPHA_F:.6f}')

    rows = AppendOnlyLog(TAPE).read()
    klines = [r for r in rows if r.get('channel') == 'kline']
    events = [r['event_time'] for r in klines]
    print(f'dev tape: {len(rows)} rows, {len(klines)} closed klines, '
          f'{sum(1 for r in rows if r.get("channel")=="funding")} funding rows')

    manifest = ExperimentManifest(
        experiment_id='v8-diagnostic-dev-20260806', code_hash='', data_hash='',
        universe=('BTCUSDT',), start_ns=min(events), end_ns=max(events),
        interval='1h', authority_receipt=None)

    if STORE.exists():
        shutil.rmtree(STORE)   # /tmp diagnostic scratch: one store = one run
    STORE.mkdir(parents=True)
    lab = Lab(STORE, universe=('BTCUSDT',))
    lab.ingest(AppendOnlyLog(TAPE).replay_tape())
    experts = [d['cls']() for d in families.values()]
    r = lab.run(manifest, experts)
    print(f'lab run: candidate_count={r.candidate_count} '
          f'verdict={r.verdict} ledger_hash={r.ledger_hash[:12]}')

    drift = mean_log_drift_per_bar(
        [float(k['payload']['close']) for k in klines])
    exposures = _family_exposures(lab.dir, families)

    total_efp = 0.0
    report = {'diagnostic': True, 'verdict': 'NO_ECONOMIC_CLAIM',
              'pre_holdout': True,
              'note': 'dev-window, in-sample, selection-biased; never a claim',
              'experiment_id': manifest.experiment_id,
              'window': {'first_kline': events[0], 'last_kline': events[-1],
                         'n_klines': len(klines)},
              'detrending': {'method': 'aronson-appendix-a-same-exposure',
                             'mean_log_drift_per_bar': drift},
              'multiplicity': {'F_preregistered': N_FAMILIES,
                               'alpha_f': ALPHA_F,
                               'method': 'bonferroni'},
              'families': {}}
    for eid, d in families.items():
        xs = exposures[eid]
        n = len(xs)
        raw = [e.net_r for e in xs]
        detrended = detrend_net_r(xs, drift)
        mu_raw = (sum(raw) / n) if n else 0.0
        mu_hat = (sum(detrended) / n) if n else 0.0
        lower, block = _lower_bound(detrended)
        eff = _effective_search_size(d['variants_evaluated'],
                                     d['search_universe_size'])
        efp = _expected_false_positives(eff, ALPHA_F)
        total_efp += efp
        long_n = sum(1 for e in xs if e.direction == 'LONG')
        report['families'][eid] = {
            'mechanism_family_id': d['mechanism_family_id'],
            'variant_id': d['variant_id'],
            'n': n,
            'long_share': (long_n / n) if n else None,
            'mu_hat': mu_hat,                    # PRIMARY: detrended mean
            'mu_hat_raw': mu_raw,                # diagnostic: raw mean
            'position_bias_component': mu_raw - mu_hat,
            'ci_lower_at_alpha_f': lower,
            'block_size': block,
            'h0_diagnostic': lower > 0.0 and n >= MIN_EPISODES,
            'search_universe_size': d['search_universe_size'],
            'variants_evaluated': d['variants_evaluated'],
            'multiplicity_undercounted': d['search_universe_size'] > d['variants_evaluated'],
            'effective_search_size': eff,
            'expected_false_positives': efp,
        }
    report['expected_false_positives_total'] = total_efp
    report['sufficiency'] = {
        'bars_ok': len(klines) >= runner.MIN_BARS,
        'min_episodes': MIN_EPISODES,
        'n_families_with_episodes': sum(1 for f in report['families'].values()
                                        if f['n'] > 0),
        'n_families_ge_min_episodes': sum(1 for f in report['families'].values()
                                          if f['n'] >= MIN_EPISODES),
    }

    out = Path('/tmp/v8-diagnostic-dev-report.json')
    out.write_text(json.dumps(report, indent=2))
    print(f'wrote {out}')

    print()
    hdr = (f'{"family":24s} {"n":>4s} {"long%":>6s} {"mu_hat":>9s} '
           f'{"raw":>9s} {"pbias":>9s} {"ci_low":>9s} {"H0?":>5s}')
    print(hdr)
    print('-' * len(hdr))
    for eid, f in report['families'].items():
        ls = '  -' if f['long_share'] is None else f'{f["long_share"]*100:5.1f}'
        print(f'{eid:24s} {f["n"]:4d} {ls} '
              f'{f["mu_hat"]:9.4f} {f["mu_hat_raw"]:9.4f} '
              f'{f["position_bias_component"]:9.4f} {f["ci_lower_at_alpha_f"]:9.4f} '
              f'{"YES" if f["h0_diagnostic"] else "no":>5s}')
    print('-' * len(hdr))
    print(f'total expected false positives at alpha_f: {total_efp:.2f} '
          f'(across effective search sizes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

