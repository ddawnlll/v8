"""V8 x Recoverable Regret v0.2 — Phase 2: systematicity discovery.

Implements `reports/accp/v8-rr-v02-phase0/source/FCR-V8RR-007.accp.yaml`
exactly. Reuses `src/v8/statistics.py` in full — this module writes ZERO new
estimator code. Its only two responsibilities are the slice-builder (turn
Phase-1's joined dataset into aligned per-slice net_R series) and the
attempt ledger (log every declared slice BEFORE its result is known, per
the task's own search-accounting requirement).

Never re-runs Lab, the Phase-0 evaluator, or Phase 1's join — reads
`tools.regret_phase1`'s frozen dataset only (FCR-V8RR-007 OM002).
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
from v8.statistics import (select_block_size, bootstrap_ci, effective_independent_episodes,
                           practical_significance, expected_false_positives,
                           effective_search_size)

# --- FCR-V8RR-007 frozen constants ------------------------------------------

EXPERTS = ('trend_pullback', 'failed_breakout', 'liquidity_sweep_reclaim')   # FT003
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT')  # FT003
DIRECTIONS = ('LONG', 'SHORT')                                               # FT003
ESTIMANDS = ('mean_legal_hindsight_gap', 'mean_actual_vs_no_trade')          # FT001

MIN_N_COMPUTED = 30          # FT003 minimum support
MIN_EFFECTIVE_EPISODES = 8   # FT003 minimum support
N_RESAMPLES = 2000           # FT004
CI = 0.90                    # FT004
ALPHA_FAMILY = 0.05          # FT005 (pre-correction)
MIN_NET_R = 0.05             # FT007 materiality floor
MIN_TRADES_MATERIALITY = 30  # FT007 — same bar as MIN_N_COMPUTED by design

DISCOVERY_VERDICTS = ('CANDIDATE_SYSTEMATIC', 'INSUFFICIENT_SUPPORT',
                      'EXCLUDED_EMPTY', 'NOT_MATERIAL', 'NOT_SIGNIFICANT')
CONFIRMATION_VERDICTS = ('SYSTEMATIC_FINDING', 'FAILED_CONFIRMATION')


@dataclass(frozen=True)
class SliceResult:
    slice_key: str
    expert_id: str
    symbol: str
    direction: str
    estimand: str
    n_total_in_slice: int
    n_computed: int
    effective_independent_episodes: float
    mean: float | None
    ci_lower: float | None
    ci_upper: float | None
    block_size: int | None
    alpha_slate: float
    practically_significant: bool | None
    materiality_note: str
    discovery_verdict: str
    confirmation_verdict: str | None
    confirmation_mean: float | None
    confirmation_ci_lower: float | None
    confirmation_ci_upper: float | None


def _seed_for(slice_key: str) -> int:
    """Deterministic per-slice seed (FT004) — never wall-clock, never
    run-order dependent. Truncated sha1 to a positive int."""
    return int(sha1_hex(slice_key)[:8], 16)


def _estimand_series(rows: list, estimand: str) -> list:
    """AS002: restrict to gap_status=COMPUTED before touching any estimator
    — a None/non-COMPUTED row is never coerced into a float."""
    computed = [r for r in rows if r['gap_status'] == 'COMPUTED']
    if estimand == 'mean_legal_hindsight_gap':
        return [r['legal_hindsight_gap'] for r in computed
               if r['legal_hindsight_gap'] is not None], computed
    if estimand == 'mean_actual_vs_no_trade':
        return [r['actual_utility'] for r in computed
               if r['actual_utility'] is not None], computed
    raise ValueError(f'unknown estimand {estimand!r}')


def _max_hold_bars(rows: list) -> int:
    holds = [r.get('horizon_bars') for r in rows if r.get('horizon_bars')]
    return max(holds) if holds else 1


def declare_slices() -> list[tuple]:
    """FT003: the full 72-slice discovery family, declared BEFORE any data
    is touched. Every slice is logged in the attempt ledger, including ones
    that turn out EXCLUDED_EMPTY."""
    out = []
    for expert_id in EXPERTS:
        for symbol in SYMBOLS:
            for direction in DIRECTIONS:
                for estimand in ESTIMANDS:
                    key = f'{expert_id}|{symbol}|{direction}|{estimand}'
                    out.append((key, expert_id, symbol, direction, estimand))
    return out


def score_slice(key: str, expert_id: str, symbol: str, direction: str,
                estimand: str, dataset_rows: list) -> SliceResult:
    slice_rows = [r for r in dataset_rows if r['expert_id'] == expert_id
                 and r['symbol'] == symbol and r['direction'] == direction]
    alpha_slate = ALPHA_FAMILY / effective_search_size(len(declare_slices()), len(declare_slices()))

    if not slice_rows:
        return SliceResult(key, expert_id, symbol, direction, estimand, 0, 0, 0.0,
                           None, None, None, None, alpha_slate, None,
                           'no candidates in this slice', 'EXCLUDED_EMPTY',
                           None, None, None, None)

    series, computed_rows = _estimand_series(slice_rows, estimand)
    n_computed = len(series)
    eff_n = effective_independent_episodes(n_computed, _max_hold_bars(computed_rows)) \
        if n_computed else 0.0

    if n_computed < MIN_N_COMPUTED or eff_n < MIN_EFFECTIVE_EPISODES:
        return SliceResult(key, expert_id, symbol, direction, estimand,
                           len(slice_rows), n_computed, eff_n, None, None, None,
                           None, alpha_slate, None,
                           f'n_computed={n_computed} (need >={MIN_N_COMPUTED}) or '
                           f'effective_independent_episodes={eff_n:.2f} '
                           f'(need >={MIN_EFFECTIVE_EPISODES})',
                           'INSUFFICIENT_SUPPORT', None, None, None, None)

    block = select_block_size(series)
    seed = _seed_for(key)
    ci_lower, ci_upper = bootstrap_ci(series, block, N_RESAMPLES, seed, ci=CI)
    meets, note = practical_significance(series, MIN_NET_R, MIN_TRADES_MATERIALITY)
    mean = sum(series) / len(series)

    if not meets:
        verdict = 'NOT_MATERIAL'
    elif ci_lower <= 0.0:
        # FT005/FT007: the CI must exclude the null in the direction claimed
        # (a lower bound at or below zero cannot support a "systematic"
        # positive-gap or positive-edge claim at this slice's alpha).
        verdict = 'NOT_SIGNIFICANT'
    else:
        verdict = 'CANDIDATE_SYSTEMATIC'

    return SliceResult(key, expert_id, symbol, direction, estimand, len(slice_rows),
                       n_computed, eff_n, mean, ci_lower, ci_upper, block,
                       alpha_slate, meets, note, verdict, None, None, None, None)


def run_discovery(dataset_path: Path, discovery_rows: list, out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slices = declare_slices()
    results = [score_slice(*s, discovery_rows) for s in slices]

    attempt_path = out / 'attempts.jsonl'
    with attempt_path.open('w', encoding='utf-8') as fh:
        for r in results:
            rec = asdict(r)
            rec['source'] = 'regret-phase2-attempt'
            rec['event_id'] = r.slice_key
            fh.write(json.dumps(rec, sort_keys=True) + '\n')

    n_candidate = sum(1 for r in results if r.discovery_verdict == 'CANDIDATE_SYSTEMATIC')
    verdict_counts = {v: sum(1 for r in results if r.discovery_verdict == v)
                      for v in DISCOVERY_VERDICTS}
    summary = {
        'n_slices_declared': len(slices),
        'discovery_verdict_distribution': verdict_counts,
        'n_candidate_systematic': n_candidate,
        'expected_false_positives_at_family_alpha':
            expected_false_positives(len(slices), ALPHA_FAMILY),
        'alpha_slate_bonferroni': ALPHA_FAMILY / len(slices),
        'candidate_systematic_slices': [r.slice_key for r in results
                                        if r.discovery_verdict == 'CANDIDATE_SYSTEMATIC'],
    }
    (out / 'discovery_summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, default=list) + '\n', encoding='utf-8')
    return summary, results


def run_confirmation(candidate_results: list, confirmation_rows: list, out_dir: Path) -> dict:
    """FT006: each CANDIDATE_SYSTEMATIC slice is queried AGAINST CONFIRMATION
    EXACTLY ONCE. A failure is recorded permanently and never re-tested
    (FCR-V8RR-007 AP002)."""
    out = Path(out_dir)
    confirmed = []
    for r in candidate_results:
        slice_rows = [row for row in confirmation_rows if row['expert_id'] == r.expert_id
                     and row['symbol'] == r.symbol and row['direction'] == r.direction]
        series, computed_rows = _estimand_series(slice_rows, r.estimand) if slice_rows else ([], [])
        n_computed = len(series)
        eff_n = effective_independent_episodes(n_computed, _max_hold_bars(computed_rows)) \
            if n_computed else 0.0

        if n_computed < MIN_N_COMPUTED or eff_n < MIN_EFFECTIVE_EPISODES:
            verdict, mean, lo, hi = 'FAILED_CONFIRMATION', None, None, None
        else:
            block = select_block_size(series)
            seed = _seed_for(r.slice_key + '|confirmation')
            lo, hi = bootstrap_ci(series, block, N_RESAMPLES, seed, ci=CI)
            mean = sum(series) / len(series)
            meets, _ = practical_significance(series, MIN_NET_R, MIN_TRADES_MATERIALITY)
            verdict = 'SYSTEMATIC_FINDING' if (meets and lo > 0.0) else 'FAILED_CONFIRMATION'

        confirmed.append({**asdict(r), 'confirmation_verdict': verdict,
                          'confirmation_mean': mean, 'confirmation_ci_lower': lo,
                          'confirmation_ci_upper': hi, 'confirmation_n_computed': n_computed})

    (out / 'confirmation_results.jsonl').write_text(
        '\n'.join(json.dumps(c, sort_keys=True) for c in confirmed) +
        ('\n' if confirmed else ''), encoding='utf-8')
    findings = [c for c in confirmed if c['confirmation_verdict'] == 'SYSTEMATIC_FINDING']
    summary = {'n_candidate_systematic_tested': len(confirmed),
              'n_systematic_finding': len(findings),
              'n_failed_confirmation': len(confirmed) - len(findings),
              'systematic_findings': [c['slice_key'] for c in findings]}
    (out / 'confirmation_summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, default=list) + '\n', encoding='utf-8')
    return summary
