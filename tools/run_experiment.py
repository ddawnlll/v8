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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from v8.lab import Lab  # noqa: E402
from v8.schema import ExperimentManifest, sha1_hex  # noqa: E402
from v8.statistics import (EpisodeExposure, block_bootstrap_means,  # noqa: E402
                           detrend_net_r, effective_search_size,
                           expected_false_positives, mean_log_drift_per_bar)
from v8.store import AppendOnlyLog  # noqa: E402
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert  # noqa: E402

REGISTRY_PATH = Path(__file__).resolve().parents[1] / 'docs' / 'EXPERTS_REGISTRY.yaml'

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
# Block bootstrap (prereg §9): a fixed mechanical rule, not a free parameter.
# 24 episode-blocks (one day) by default; if the estimated lag-1
# autocorrelation of the family's episode net_R exceeds 0.10 in magnitude,
# 168 (one week). Fixed seed so the lower bound is reproducible run-to-run.
BLOCK_SIZE_DEFAULT = 24
BLOCK_SIZE_WEEK = 168
LAG1_AUTOCORR_GATE = 0.10
N_RESAMPLES = 2000
BOOTSTRAP_SEED = 7
# Holdout anchor: the frozen OOS is strictly after the dev window (prereg
# §13). 2026-07-01 00:00 UTC in ns.
HOLDOUT_ANCHOR_NS = 1782864000000000000
# Sufficiency gates (prereg §12): >= 30 episodes and >= 1400 bars.
MIN_EPISODES = 30
MIN_BARS = 1400

_EXPERTS = list(FAMILIES.values())


def _lag1_autocorrelation(xs: list[float]) -> float:
    """Lag-1 autocorrelation of the episode net_R series (prereg §9 gate)."""
    n = len(xs)
    if n < 3:
        return 0.0
    m = sum(xs) / n
    num = sum((xs[i] - m) * (xs[i + 1] - m) for i in range(n - 1))
    den = sum((x - m) ** 2 for x in xs)
    return num / den if den else 0.0


def _block_size(net_rs: list[float]) -> int:
    """Prereg §9 mechanical block-size rule: 24 by default; 168 when the
    lag-1 autocorrelation of the family's episode net_R exceeds 0.10 in
    magnitude. Fixed, never tuned."""
    return BLOCK_SIZE_WEEK if abs(_lag1_autocorrelation(net_rs)) > LAG1_AUTOCORR_GATE \
        else BLOCK_SIZE_DEFAULT


def block_bootstrap_lower_bound(net_rs: list[float], *,
                                n_resamples: int = N_RESAMPLES,
                                seed: int = BOOTSTRAP_SEED) -> float:
    """2.5th-percentile lower bound of the block bootstrap on episode net_R
    (prereg §9: mechanical block-size rule + fixed seed). One-sided at alpha_f
    via the percentile method; H0 (mu_f <= 0) is rejected only when this bound
    > 0 AND n_f >= MIN_EPISODES (composite §11/§12 test). Deterministic for a
    fixed seed; an empty sample returns 0.0 (no signal).

    METH-4 / EV_METHODS E-04 sampler unification: the resamples come from
    `v8.statistics.block_bootstrap_means`, the SAME circular fixed-block
    sampler `reality_check_p_value` uses. A second, non-circular sampler would
    make the single-config gate and the WRC sampling-inequivalent for the
    "same" section-9 rule — this is the one block sampler of record.
    """
    block = _block_size(net_rs)
    if not net_rs:
        return 0.0
    means = block_bootstrap_means(net_rs, block, n_resamples, seed)
    means.sort()
    # The 2.5th-percentile LOWER bound: int(n_resamples * alpha_f) of the
    # sorted resample means sits below alpha_f of the distribution. (The
    # 97.5th percentile would be the UPPER bound — the wrong side for a
    # one-sided H0: mu_f <= 0 test; caught by the dev-tape smoke run.)
    return means[int(n_resamples * ALPHA_F)]


def _family_exposures(store_dir: Path) -> dict[str, list[EpisodeExposure]]:
    """Per family id, the executed episodes with the exposure that produced
    them (label_status != NOT_EXECUTED), grouped by the candidate's expert via
    the frozen FAMILIES mapping. Cost-gated / invalidated / D-024-vetoed
    rejections never become episodes (prereg §15 denominator) — only executed
    outcomes count.

    D-045: the direction comes from the candidate record and the R unit from
    the outcome, because the detrended null needs the SAME denominator the
    simulator used, not a re-derived one."""
    family_by_expert = {cls.expert_id: fid for fid, cls in FAMILIES.items()}
    candidates = [json.loads(l) for l in
                  (store_dir / 'candidates.jsonl').read_text().splitlines()]
    outcomes = {o['candidate_id']: o for o in (
        json.loads(l) for l in (store_dir / 'outcomes.jsonl').read_text().splitlines())}
    by_family: dict[str, list[EpisodeExposure]] = {fid: [] for fid in FAMILIES}
    seen: set[str] = set()
    for rec in candidates:
        cid = rec['candidate_id']
        fid = family_by_expert.get(rec.get('expert_id'))
        if fid is None or cid in seen:
            continue
        seen.add(cid)
        o = outcomes.get(cid)
        if o is None or o.get('label_status') == 'NOT_EXECUTED':
            continue
        if not float(o.get('risk_unit_price', 0.0)) > 0:
            raise ValueError(
                f'executed outcome {cid} carries no risk_unit_price: it was '
                'written by a pre-D-045 ledger and cannot be detrended — '
                're-run the lab rather than scoring an uncentered series')
        by_family[fid].append(EpisodeExposure(
            net_r=float(o['net_r']), direction=rec['direction'],
            entry_price=float(o['entry_price']),
            risk_unit_price=float(o['risk_unit_price']),
            horizon_bars=int(o['horizon_bars'])))
    return by_family


def _search_accounting() -> dict[str, tuple[int, int]]:
    """Per family id, `(search_universe_size, len(variants_evaluated))` (D-046).

    Reported with every family statistic so a reader can see the multiplicity
    denominator the p-value was computed against. `yaml` is a dev/tooling
    dependency; this runner lives in `tools/`, outside the stdlib-only
    decision path of D-031."""
    import yaml
    doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding='utf-8'))
    by_expert = {e['expert_id']: e for e in doc['experts']}
    out: dict[str, tuple[int, int]] = {}
    for fid, cls in FAMILIES.items():
        entry = by_expert.get(cls.expert_id)
        if entry is None or 'search_universe_size' not in entry:
            raise ValueError(
                f'{cls.expert_id}: no search_universe_size in the registry — '
                'the family multiplicity denominator is undeclared (D-046); '
                'fail closed rather than assuming the search was minimal')
        out[fid] = (int(entry['search_universe_size']),
                    len(entry['variants_evaluated']))
    return out


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
        # The frozen OOS must be strictly after the dev window (prereg §13);
        # a manifest whose window overlaps the dev tape cannot be the holdout.
        if manifest.start_ns < HOLDOUT_ANCHOR_NS:
            raise ValueError(
                f'frozen manifest start_ns {manifest.start_ns} is before the '
                f'holdout anchor {HOLDOUT_ANCHOR_UTC} ({HOLDOUT_ANCHOR_NS}): '
                'the OOS window must be strictly after the dev window '
                '(prereg §13); a dev-overlapping tape is not the holdout')
        rows = AppendOnlyLog(tape_path).read()
        holdout_hash = sha1_hex(rows)
        if not manifest.data_hash:
            raise ValueError(
                'frozen manifest data_hash is empty: the holdout hash must be '
                'recorded at download time before any evaluation (prereg §16) '
                '— fail closed, never evaluate an un-pinned holdout')
        if manifest.data_hash != holdout_hash:
            raise ValueError(
                f'holdout tape hash {holdout_hash} != manifest data_hash '
                f'{manifest.data_hash}: the holdout was recorded at download '
                'time before any evaluation (prereg §16) — a mismatch means '
                'the tape changed after recording; fail closed')
        # The declared holdout window must match the tape's actual content
        # (prereg §13): data_hash binds the file bytes, not the window — a dev
        # tape (or a dev+OOS merge) authored with start_ns >= anchor would
        # otherwise be evaluated as the frozen OOS. Verify the kline event
        # range sits inside [start_ns, end_ns].
        kline_events = [r['event_time'] for r in rows
                        if r.get('channel') == 'kline']
        if not kline_events:
            raise ValueError('holdout tape has no kline rows — nothing to evaluate')
        min_ev, max_ev = min(kline_events), max(kline_events)
        if min_ev < manifest.start_ns:
            raise ValueError(
                f'holdout tape first kline event {min_ev} is before the '
                f'declared window start {manifest.start_ns}: the recorded '
                'tape must match the prereg §13 OOS window — fail closed')
        if manifest.end_ns and max_ev > manifest.end_ns:
            raise ValueError(
                f'holdout tape last kline event {max_ev} is after the declared '
                f'window end {manifest.end_ns}: fail closed')

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
    # D-027 is evaluated first (prereg §11): when the attribution-validity gate
    # fires ATTRIBUTION_UNSAFE_*, the run is NOT scored for the primary metric.
    if r.verdict.startswith('ATTRIBUTION_UNSAFE_'):
        report['families'] = {fid: {'scored': False} for fid in FAMILIES}
        return report
    rows = AppendOnlyLog(tape_path).read()
    klines = [r for r in rows if r.get('channel') == 'kline']
    report['sufficiency']['bars'] = len(klines)
    # D-045: the centering constant for the detrended null. Estimated on the
    # SAME window the test scores (Appendix A defines detrending as centering
    # by the sample's own mean) and from the true, undetrended tape — signal
    # generation already happened above and never sees this number.
    drift = mean_log_drift_per_bar([float(r['payload']['close']) for r in klines])
    report['detrending'] = {
        'method': 'aronson-appendix-a-same-exposure-benchmark',
        'mean_log_drift_per_bar': drift,
        'estimated_on': 'frozen-oos-window',
    }
    search = _search_accounting()
    exposures_by_family = _family_exposures(lab.dir)
    # METH-6 (G-11): program-level expected false positives under the null,
    # summed over the families actually scored.
    total_expected_false_positives = 0.0
    for fid, exposures in exposures_by_family.items():
        n = len(exposures)
        raw = [e.net_r for e in exposures]
        # METH-1 (D-045): the tests receive the PRE-CENTERED series. The
        # caller (this runner) centers via detrend_net_r; the single-config
        # percentile test and the WRC never recenter for position bias inside
        # (Aronson Appendix A equivalence: centering by the sample's own mean
        # subtracts a same-exposure benchmark).
        detrended = detrend_net_r(exposures, drift)
        mu_raw = (sum(raw) / n) if n else 0.0
        mu_hat = (sum(detrended) / n) if n else 0.0
        lower = block_bootstrap_lower_bound(detrended)
        universe_size, n_variants = search[fid]
        # METH-2 (D-046/G-01): the honest family size for multiplicity lines —
        # max(variants_evaluated, search_universe_size), never less than the
        # declared search. The RC max-stat denominator stays variants_evaluated;
        # the gap to effective_search_size is surfaced via
        # multiplicity_undercounted.
        eff_size = effective_search_size(n_variants, universe_size)
        # METH-6 (G-11): N x alpha_f false positives expected by chance —
        # Aronson's 6,402 x 0.05 = 320.1 calibration. Report beside the family.
        efp = expected_false_positives(eff_size, ALPHA_F)
        total_expected_false_positives += efp
        report['families'][fid] = {
            'n': n,
            # PRIMARY (prereg §10, D-045): the detrended mean. The raw mean is
            # kept beside it as a diagnostic — on a trending tape the gap
            # between them IS the position-bias component, and reporting only
            # one of the two hides how much of the result was drift.
            'mu_hat': mu_hat,
            'mu_hat_raw': mu_raw,
            'position_bias_component': mu_raw - mu_hat,
            'ci_lower_2p5': lower,
            'block_size': _block_size(detrended),
            # Composite §11/§12 test: the lower bound must exceed 0 AND the
            # family must have >= MIN_EPISODES executed episodes (n_f < 30
            # blocks the family-level conclusion).
            'h0_rejected': lower > 0.0 and n >= MIN_EPISODES,
            # D-046: the multiplicity denominator this p-value was computed
            # against. When the declared search exceeds the variants whose
            # series were retained, the within-family control saw only part of
            # the search and the result is optimistic by that margin — say so
            # in the record rather than letting a reader assume full coverage.
            'search_universe_size': universe_size,
            'variants_evaluated': n_variants,
            'multiplicity_undercounted': universe_size > n_variants,
            # METH-2 (G-01): the honest family size and the expected false
            # positives at alpha_f (METH-6, G-11) — the Aronson calibration
            # line every family verdict is read against.
            'effective_search_size': eff_size,
            'expected_false_positives': efp,
        }
    report['expected_false_positives'] = {
        'method': 'program-level sum of family effective_search_size x alpha_f '
                  '(Aronson G-11 calibration: 6,402 x 0.05 = 320.1)',
        'total': total_expected_false_positives,
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
