"""v8_slice_001 experiment runner (HYPOTHESIS_LAB_PROTOCOL;
PREREGISTRATION_V8_SLICE_001).

Reads a frozen holdout manifest, verifies the frozen out-of-sample tape, runs
the two pilot families on the chronological OOS vs the no-trade baseline,
computes the family-level one-sided tests with a deterministic block bootstrap
and Bonferroni multiplicity control, and applies the D-027 attribution-validity
gates first (authority blocks first: without a receipt the verdict stays
NO_ECONOMIC_CLAIM).

The RUN is gated on the frozen holdout existing (the first two published
months strictly after 2026-07-01 + 9-bar label-horizon extension, prereg §13).
When the holdout is absent the runner fails closed with a NO_ECONOMIC_CLAIM
report — it never fabricates a holdout, a hash, or a verdict. The holdout
hash is recorded (pinned in the manifest at download time) and verified
before any evaluation; a mismatch fails closed (prereg §16).

Deterministic: the bootstrap uses a fixed seed (no wall clock, no RNG from
the environment); sha1_hex for every hash (PERSISTENCE_REPLAY_SPEC 4).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from v8.lab import Lab  # noqa: E402
from v8.schema import ExperimentManifest, sha1_hex  # noqa: E402
from v8.store import AppendOnlyLog  # noqa: E402
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert  # noqa: E402

# --- Frozen preregistration constants (PREREGISTRATION_V8_SLICE_001) --------
# O-017 thresholds and the holdout anchor are fixed forever — never re-set
# after a verdict (prereg §15-16). The family set and the multiplicity rule
# are the prereg's own; any change requires a new preregistration.
EXPERIMENT_ID = 'v8_slice_001'
UNIVERSE = ('BTCUSDT',)
INTERVAL = '1h'
HOLDOUT_ANCHOR_UTC = '2026-07-01 00:00'
# The two experiment families (prereg §3): family id -> pilot Expert.
FAMILIES = {
    'trend_continuation': TrendPullbackExpert,
    'failed_breakout_reentry': FailedBreakoutExpert,
}
N_FAMILIES = len(FAMILIES)
ALPHA_FAMILY = 0.05
ALPHA_F = ALPHA_FAMILY / N_FAMILIES          # Bonferroni per-family alpha
# Block bootstrap (prereg §9): fixed mechanical block size and a fixed seed
# so the lower bound is reproducible run-to-run.
BLOCK_SIZE = 24
N_RESAMPLES = 2000
BOOTSTRAP_SEED = 7
# Sufficiency gates (prereg §12): >= 30 episodes and >= 1400 bars.
MIN_EPISODES = 30
MIN_BARS = 1400

_EXPERTS = list(FAMILIES.values())


def block_bootstrap_lower_bound(net_rs: list[float], *, block: int = BLOCK_SIZE,
                                n_resamples: int = N_RESAMPLES,
                                seed: int = BOOTSTRAP_SEED) -> float:
    """2.5th-percentile lower bound of the block bootstrap on episode net_R
    (prereg §9: fixed block size, mechanical rule). One-sided at alpha_f via
    the percentile method; H0 (mu_f <= 0) is rejected when this bound > 0.
    Deterministic for a fixed seed; an empty sample returns 0.0 (no signal)."""
    n = len(net_rs)
    if n == 0:
        return 0.0
    rng = random.Random(seed)
    max_start = max(1, n - block + 1)
    n_blocks = (n + block - 1) // block
    means = []
    for _ in range(n_resamples):
        idxs: list[int] = []
        for _ in range(n_blocks):
            start = rng.randrange(max_start)
            idxs.extend(range(start, min(start + block, n)))
        sample = [net_rs[i] for i in idxs[:n]]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(n_resamples * (1 - ALPHA_F)) - 1]


def _family_net_rs(store_dir: Path) -> dict[str, list[float]]:
    """Per family id, the executed episodes' net_R (label_status !=
    NOT_EXECUTED), grouped by the candidate's expert via the frozen FAMILIES
    mapping. Cost-gated / invalidated / D-024-vetoed rejections never become
    episodes (prereg §15 denominator) — only executed outcomes count."""
    family_by_expert = {cls.expert_id: fid for fid, cls in FAMILIES.items()}
    candidates = [json.loads(l) for l in
                  (store_dir / 'candidates.jsonl').read_text().splitlines()]
    outcomes = {o['candidate_id']: o for o in (
        json.loads(l) for l in (store_dir / 'outcomes.jsonl').read_text().splitlines())}
    by_family: dict[str, list[float]] = {fid: [] for fid in FAMILIES}
    seen: set[str] = set()
    for rec in candidates:
        cid = rec['candidate_id']
        fid = family_by_expert.get(rec.get('expert_id'))
        if fid is None or cid in seen:
            continue
        seen.add(cid)
        o = outcomes.get(cid)
        if o is not None and o.get('label_status') != 'NOT_EXECUTED':
            by_family[fid].append(float(o['net_r']))
    return by_family


def run_experiment(manifest_path: Path) -> dict:
    """Execute v8_slice_001 against the frozen manifest; returns the report."""
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    tape_path = Path(data.pop('tape_path'))
    manifest = ExperimentManifest(**data)

    if manifest.experiment_id != EXPERIMENT_ID:
        raise ValueError(
            f'frozen manifest experiment_id {manifest.experiment_id!r} != '
            f'{EXPERIMENT_ID!r} — a different preregistration cannot run here')
    if tuple(manifest.universe) != UNIVERSE:
        raise ValueError(
            f'frozen manifest universe {tuple(manifest.universe)} != {UNIVERSE}')
    if manifest.interval != INTERVAL:
        raise ValueError(
            f'frozen manifest interval {manifest.interval!r} != {INTERVAL!r}')

    # The frozen holdout is the preregistration's OOS tape (downloaded only at
    # experiment time, prereg §13). Absent -> fail closed, never fabricate.
    holdout_present = tape_path.exists()
    holdout_hash: str | None = None
    if holdout_present:
        rows = AppendOnlyLog(tape_path).read()
        holdout_hash = sha1_hex(rows)
        if manifest.data_hash and manifest.data_hash != holdout_hash:
            raise ValueError(
                f'holdout tape hash {holdout_hash} != manifest data_hash '
                f'{manifest.data_hash}: the holdout was recorded at download '
                'time before any evaluation (prereg §16) — a mismatch means '
                'the tape changed after recording; fail closed')

    # Authority blocks first (HYPOTHESIS_LAB_PROTOCOL): the lab computes the
    # D-027 attribution statistics always, but the verdict stays
    # NO_ECONOMIC_CLAIM without a receipt.
    report: dict = {
        'experiment_id': EXPERIMENT_ID,
        'verdict': 'NO_ECONOMIC_CLAIM',
        'authority_receipt': manifest.authority_receipt,
        'holdout': {
            'anchor_utc': HOLDOUT_ANCHOR_UTC,
            'present': holdout_present,
            'hash': holdout_hash,
            'recorded_before_evaluation': holdout_present
            and manifest.data_hash is not None,
        },
        'd027': None,
        'families': {fid: None for fid in FAMILIES},
        'multiplicity': {'method': 'bonferroni', 'alpha_family': ALPHA_FAMILY,
                         'alpha_f': ALPHA_F},
        'sufficiency': {'min_bars': MIN_BARS, 'bars': 0,
                        'min_episodes': MIN_EPISODES},
        'holdout_unavailable': not holdout_present,
    }
    if not holdout_present:
        return report

    lab = Lab(manifest_path.parent / 'store', universe=UNIVERSE)
    lab.ingest(AppendOnlyLog(tape_path).replay_tape())
    r = lab.run(manifest, [cls() for cls in _EXPERTS])

    report['verdict'] = r.verdict
    report['d027'] = {
        'n_executed': r.n_executed,
        'n_portfolio_rejected': r.n_portfolio_rejected,
        'execution_share': r.execution_share,
        'divergence_ks': r.divergence_ks,
    }
    report['sufficiency']['bars'] = sum(
        1 for r in AppendOnlyLog(tape_path).read() if r.get('channel') == 'kline')
    net_by_family = _family_net_rs(lab.dir)
    for fid, net_rs in net_by_family.items():
        n = len(net_rs)
        mu_hat = (sum(net_rs) / n) if n else 0.0
        lower = block_bootstrap_lower_bound(net_rs)
        report['families'][fid] = {
            'n': n,
            'mu_hat': mu_hat,
            'ci_lower_2p5': lower,
            'h0_rejected': lower > 0.0,
        }
    report['sufficiency']['episodes_ok'] = \
        report['sufficiency']['bars'] >= MIN_BARS and all(
            (report['families'][fid] or {}).get('n', 0) >= MIN_EPISODES
            for fid in FAMILIES)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True,
                    help='frozen holdout ExperimentManifest JSON '
                         '(prereg §6/§16: data_hash recorded at download time)')
    args = ap.parse_args(argv)
    report = run_experiment(args.manifest)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
