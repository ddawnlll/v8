#!/usr/bin/env python3
"""Dev-window confluence experiment runner (D-076).

Builds a single-symbol SOLUSDT tape inside the declared dev window (strictly
before the frozen 2026-07-01 holdout — `build_multi_tape` REFUSES any month
at or past it), runs the `fib_rsi_bb_confluence` family — both variants, a
STRICT (all three legs) and b MAJORITY (two of three) — through the canonical
Lab with a realistic taker cost, and reports per-variant + pooled after-cost
statistics beside a zero-cost reference row.

EXPLORATORY, NOT A PREREGISTERED TEST. This is a dev-window probe: no
preregistered alpha, no frozen holdout, and — without an authority receipt —
the verdict stays NO_ECONOMIC_CLAIM (V8_CONSTITUTION rule 12). The report
prints n_triggered per variant so a near-zero STRICT count reads as "the
confluence almost never co-occurs" (a structural finding recorded in D-076),
never as a broken detector.

Deterministic: fixed bootstrap seed, no wall clock. One fresh store per run
(one store = one immutable run's evidence).

Usage:
  python tools/run_fib_rsi_bb_confluence.py [--months 12] [--cost-bps 10.0]
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from v8.lab import Lab, _geometry_version  # noqa: E402
from v8.schema import ExperimentManifest  # noqa: E402
from v8.store import AppendOnlyLog  # noqa: E402
from v8.experts import FibRsiBbConfluenceExpert  # noqa: E402
from v8.statistics import (EpisodeExposure, mean_log_drift_per_bar,  # noqa: E402
                           detrend_net_r, select_block_size, bootstrap_ci)

SOURCE_TAPE = ROOT / 'research' / 'tape' / 'multi-1h-4y'
SYMBOL = 'SOLUSDT'
HOLDOUT_ANCHOR = '2026-07'          # build_multi_tape refuses months >= this
BOOTSTRAP_SEED = 7
N_RESAMPLES = 2000
CI = 0.90


def _months(start: str, end: str) -> list[str]:
    y0, m0 = map(int, start.split('-'))
    y1, m1 = map(int, end.split('-'))
    out, y, m = [], y0, m0
    while (y, m) < (y1, m1):
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def build_tape(start: str, end: str) -> Path:
    """Copy the SOL zips for the window into a fresh dir and build a
    single-symbol tape through the canonical builder (offline; the source
    dir already holds the archives + CHECKSUMs). Returns the tape path."""
    out_dir = ROOT / 'research' / 'tape' / f'sol-dev-{SYMBOL.lower()}-{start}-{end}'
    out_dir.mkdir(parents=True, exist_ok=True)
    want = set(_months(start, end))
    copied = 0
    for f in sorted(SOURCE_TAPE.iterdir()):
        if not f.name.startswith(f'{SYMBOL}-'):
            continue
        # 'SOLUSDT-1h-2025-07.zip' and 'SOLUSDT-1h-2025-07.zip.CHECKSUM'
        # both carry the month before '.zip'.
        m = re.search(r'-(\d{4}-\d{2})\.zip', f.name)
        month = m.group(1) if m else None
        if month not in want:
            continue
        dst = out_dir / f.name
        if not dst.exists():
            shutil.copy2(f, dst)
        copied += 1
    if copied == 0:
        raise SystemExit(f'no {SYMBOL} archives found in {SOURCE_TAPE} for {start}..{end}')
    tape = out_dir / 'tape.jsonl'
    if not tape.exists():
        print(f'[tape] building {tape.name} from {copied} archives ({start}..{end})...')
        subprocess.run(
            [sys.executable, str(ROOT / 'tools' / 'build_multi_tape.py'),
             '--out', str(out_dir), '--symbols', SYMBOL,
             '--start', start, '--end', end],
            check=True, cwd=str(ROOT))
    else:
        print(f'[tape] reusing existing {tape}')
    return tape


def _variant_geometry_versions() -> dict[str, str]:
    """Reproduce lab._geometry_version for the two variants' structural
    geometry — the same hashes the lab records on DETECTED."""
    base = {'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0, 'stop_r': 1.0,
            'expiry_bars': 8}
    return {v: _geometry_version(SimpleNamespace(
                risk_geometry={**base, 'variant': v})) for v in ('a', 'b')}


def _run(store_dir: Path, rows, manifest):
    lab = Lab(store_dir, universe=(SYMBOL,))
    lab.ingest(rows)
    return lab.run(manifest, [FibRsiBbConfluenceExpert(),
                              FibRsiBbConfluenceExpert(variant_id='b')])


def _stats(store_dir: Path, drift: float) -> dict:
    """Per-variant + pooled statistics from the candidates/outcomes ledgers."""
    variant_by_cid: dict[str, str] = {}
    direction_by_cid: dict[str, str] = {}
    versions = _variant_geometry_versions()
    for rec in AppendOnlyLog(store_dir / 'candidates.jsonl').read():
        if rec.get('to_state') == 'DETECTED' \
                and rec.get('expert_id') == 'fib_rsi_bb_confluence':
            gv = rec.get('geometry_version')
            v = next((v for v, h in versions.items() if h == gv), None)
            if v is not None:
                variant_by_cid[rec['candidate_id']] = v
                direction_by_cid[rec['candidate_id']] = rec.get('direction', '')
    outcomes = AppendOnlyLog(store_dir / 'outcomes.jsonl').read()
    rows_by_cid: dict[str, dict] = {}
    for o in outcomes:
        rows_by_cid[o['candidate_id']] = o
    # Pool the outcome rows by variant (join through the candidate ledger).
    by_variant: dict[str, list[dict]] = {'a': [], 'b': []}
    for cid, v in variant_by_cid.items():
        o = rows_by_cid.get(cid)
        if o is not None:
            by_variant[v].append({**o, 'direction': direction_by_cid.get(cid, '')})

    def summarize(outs: list[dict]) -> dict | None:
        executed = [o for o in outs if o.get('label_status') != 'NOT_EXECUTED']
        n_trig = len(outs)
        n_ex = len(executed)
        if n_ex == 0:
            return {'n_triggered': n_trig, 'n_executed': 0}
        net_rs = [o['net_r'] for o in executed]
        wins = sum(1 for r in net_rs if r > 0.0)
        exposures = [EpisodeExposure(net_r=o['net_r'], direction=o['direction'],
                                     entry_price=o['entry_price'],
                                     risk_unit_price=o['risk_unit_price'],
                                     horizon_bars=o['horizon_bars'])
                     for o in executed]
        detrended = detrend_net_r(exposures, drift)
        block = select_block_size(net_rs)
        lo, hi = bootstrap_ci(detrended, block, N_RESAMPLES, BOOTSTRAP_SEED, CI)
        gross_win = sum(r for r in net_rs if r > 0.0)
        gross_loss = sum(r for r in net_rs if r < 0.0)
        pf = gross_win / -gross_loss if gross_loss < 0.0 else None
        return {
            'n_triggered': n_trig, 'n_executed': n_ex,
            'win_rate': wins / n_ex if n_ex else None,
            'mean_net_r': sum(net_rs) / n_ex,
            'mean_detrended': sum(detrended) / n_ex if detrended else None,
            'ci_lo': lo, 'ci_hi': hi, 'block_size': block,
            'profit_factor': pf,
            'mean_mae': sum(o['mae_r'] for o in executed) / n_ex,
            'mean_mfe': sum(o['mfe_r'] for o in executed) / n_ex,
        }
    pooled = summarize([o for v in by_variant.values() for o in v])
    per_variant = {v: summarize(outs) for v, outs in by_variant.items()}
    return {'per_variant': per_variant, 'pooled': pooled,
            'n_detected_unknown': sum(1 for o in outcomes
                                      if o['candidate_id'] not in variant_by_cid)}


def _fmt(stats: dict | None) -> str:
    if stats is None:
        return f'{"—":>9} {"0":>9} {"—":>7} {"—":>9} {"—":>9} {"—":>18} {"—":>7} {"—":>7} {"—":>7}'
    trig = stats['n_triggered']
    if stats.get('n_executed', 0) == 0:
        return f'{trig:>9} {"0":>9} {"—":>7} {"—":>9} {"—":>9} {"—":>18} {"—":>7} {"—":>7} {"—":>7}'
    wr = stats['win_rate']
    lo, hi = stats['ci_lo'], stats['ci_hi']
    return (f'{stats["n_triggered"]:>9} {stats["n_executed"]:>9} '
            f'{wr:>7.1%} {stats["mean_net_r"]:>9.3f} '
            f'{stats["mean_detrended"]:>9.3f} '
            f'[{lo:>7.3f}, {hi:>7.3f}] '
            f'{stats["profit_factor"] if stats["profit_factor"] is not None else float("nan"):>7.2f} '
            f'{stats["mean_mae"]:>7.3f} {stats["mean_mfe"]:>7.3f}')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--months', type=int, default=12, help='dev-window length in months')
    ap.add_argument('--cost-bps', type=float, default=10.0,
                    help='round-trip taker cost in bps (0 = signal-before-cost row)')
    args = ap.parse_args(argv)
    end_y, end_m = 2026, 7          # exclusive: the holdout anchor
    months = args.months
    start_y, start_m = end_y, end_m - months
    while start_m <= 0:
        start_y, start_m = start_y - 1, start_m + 12
    start = f'{start_y:04d}-{start_m:02d}'
    end = f'{end_y:04d}-{end_m:02d}'
    if end > HOLDOUT_ANCHOR:
        raise SystemExit(f'window {start}..{end} reaches the holdout — refuse')

    tape_path = build_tape(start, end)
    rows = AppendOnlyLog(tape_path).replay_tape()
    bars = [r for r in rows if r.channel == 'kline' and r.payload.get('closed')]
    closes = [float(r.payload['close']) for r in sorted(
        bars, key=lambda r: r.available_time)]
    if len(bars) < 300:
        raise SystemExit(f'tape has only {len(bars)} bars — too small for the run')
    start_ns = min(r.event_time for r in bars)
    end_ns = max(r.event_time for r in bars)
    drift = mean_log_drift_per_bar(closes)
    print(f'[data] {len(bars)} closed 1h bars, drift per bar {drift:+.6f}')

    base = dict(experiment_id='fib_rsi_bb_confluence_dev', code_hash='',
                data_hash='', universe=(SYMBOL,), start_ns=start_ns,
                end_ns=end_ns, interval='1h', funding_rate_r=0.0,
                funding_hours=8, risk_per_trade=0.01, min_trades=300)
    store_cost = ROOT / '.audit' / 'confluence' / f'{start}-{end}-cost{args.cost_bps:g}'
    store_zero = ROOT / '.audit' / 'confluence' / f'{start}-{end}-cost0'
    for d in (store_cost, store_zero):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    m_cost = ExperimentManifest(**{**base, 'round_trip_cost_bps': args.cost_bps})
    m_zero = ExperimentManifest(**{**base, 'round_trip_cost_bps': 0.0})
    print(f'[run] costing {args.cost_bps:g} bps round-trip...')
    cost_report = _run(store_cost, rows, m_cost)
    print('[run] zero-cost reference...')
    _run(store_zero, rows, m_zero)

    print(f'\n=== fib_rsi_bb_confluence dev-window experiment '
          f'{start}..{end} ({SYMBOL}, 1h) — EXPLORATORY ===')
    hdr = (f'{"variant":<9}{"trig":>9}{"exec":>9}{"win":>7}{"meanR":>9}'
           f'{"detR":>9}{"90% CI":>18}{"PF":>7}{"MAE":>7}{"MFE":>7}')
    print(hdr)
    print('-' * len(hdr))
    s = _stats(store_cost, drift)
    for v in ('a', 'b'):
        print(f'{v:<9}' + _fmt(s['per_variant'][v]))
    print(f'{"pooled":<9}' + _fmt(s['pooled']))
    if s['n_detected_unknown']:
        print(f'({s["n_detected_unknown"]} detected candidates not assigned to '
              'a variant — geometry-version mapping gap)')
    z = _stats(store_zero, drift)
    print('-' * len(hdr))
    print('zero-cost reference (signal before cost):')
    for v in ('a', 'b'):
        print(f'{v:<9}' + _fmt(z['per_variant'][v]))
    print(f'{"pooled":<9}' + _fmt(z['pooled']))

    print(f'\n--- lab report (cost {args.cost_bps:g} bps) ---')
    print(f'verdict: {cost_report.verdict}')
    print(f'candidates: {cost_report.candidate_count} | '
          f'executed: {cost_report.n_executed} | '
          f'portfolio-rejected: {cost_report.n_portfolio_rejected}')
    print(f'evaluation_distribution: {dict(cost_report.evaluation_distribution or {})}')
    print(f'rejection_distribution: {dict(cost_report.rejection_distribution or {})}')
    print(f'final_equity: {cost_report.final_equity} | '
          f'max_drawdown: {cost_report.max_drawdown} | '
          f'risk_of_ruin: {cost_report.risk_of_ruin}')
    print(f'profit_factor (report): {cost_report.profit_factor} | '
          f'breakeven win rate w_min: {cost_report.w_min}')
    if cost_report.economic_note:
        print(f'note: {cost_report.economic_note}')
    # Cost drag on the pooled executed intersection.
    out_cost = {o['candidate_id']: o['net_r']
                for o in AppendOnlyLog(store_cost / 'outcomes.jsonl').read()
                if o['label_status'] != 'NOT_EXECUTED'}
    out_zero = {o['candidate_id']: o['net_r']
                for o in AppendOnlyLog(store_zero / 'outcomes.jsonl').read()
                if o['label_status'] != 'NOT_EXECUTED'}
    inter = sorted(set(out_cost) & set(out_zero))
    if inter:
        drag = sum(out_zero[c] - out_cost[c] for c in inter) / len(inter)
        print(f'cost drag (pooled, n={len(inter)}): '
              f'{sum(out_zero[c] for c in inter)/len(inter):+.3f} R at 0 bps -> '
              f'{sum(out_cost[c] for c in inter)/len(inter):+.3f} R at {args.cost_bps:g} '
              f'bps ({drag:+.3f} R/episode)')
    print('\nNo authority receipt: the economic verdict stays NO_ECONOMIC_CLAIM. '
          'This is a dev-window probe, not a registered experiment.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
