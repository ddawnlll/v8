"""Standalone perf probe: time + cProfile a realistic Lab.run.

Not part of the shipped tooling — a scratch profiling harness. Builds an
8760-bar continuous synthetic tape and runs the full registered expert set,
mirroring the heaviest materialize_views-style shape.
"""
from __future__ import annotations

import cProfile
import io
import pstats
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from v8.experts import (TrendPullbackExpert, FailedBreakoutExpert,
                        LiquiditySweepReclaimExpert, FailedBreakout2BExpert,
                        TrendPullbackDepthExpert, RangeBreakout1To1Expert,
                        CandlestickReversalExpert, RsiStochReversionExpert,
                        MacdStochTrendExpert, Divergence12SetupsExpert,
                        BollingerBreakoutExpert, BollingerReversionExpert,
                        DonchianBreakoutExpert, BreakoutRetestExpert,
                        FibRetracementContinuationExpert,
                        FibProjectionReversalExpert,
                        PatternMeasuringObjectiveExpert,
                        VolumeConfirmedBreakoutExpert,
                        VolumeClimaxReversalExpert, ObvAdlRegimeExpert,
                        IchimokuCloudExpert, FloorTraderPivotExpert,
                        MarketProfileValueAreaExpert, GapExhaustionExpert,
                        OpenInterestDivergenceExpert,
                        FundingCrowdingReversalExpert, PandfBreakoutExpert)
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

ALL = [cls() for cls in (
    TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert,
    FailedBreakout2BExpert, TrendPullbackDepthExpert, RangeBreakout1To1Expert,
    CandlestickReversalExpert, RsiStochReversionExpert, MacdStochTrendExpert,
    Divergence12SetupsExpert, BollingerBreakoutExpert, BollingerReversionExpert,
    DonchianBreakoutExpert, BreakoutRetestExpert,
    FibRetracementContinuationExpert, FibProjectionReversalExpert,
    PatternMeasuringObjectiveExpert, VolumeConfirmedBreakoutExpert,
    VolumeClimaxReversalExpert, ObvAdlRegimeExpert, IchimokuCloudExpert,
    FloorTraderPivotExpert, MarketProfileValueAreaExpert, GapExhaustionExpert,
    OpenInterestDivergenceExpert, FundingCrowdingReversalExpert, PandfBreakoutExpert,
)]


def make_manifest(n_bars: int, store_dir: Path):
    tape = make_synthetic_tape(seed=11, n_bars=n_bars, continuous=True)
    lab = Lab(store_dir)
    lab.ingest(tape)
    return lab, tape


def run_profile(experts, n_bars: int = 8760, profile: bool = False):
    with tempfile.TemporaryDirectory() as td:
        store = Path(td)
        lab, tape = make_manifest(n_bars, store)
        manifest = ExperimentManifest(
            experiment_id='perf_probe',
            code_hash=lab.__class__.__module__ and '',  # empty -> computed live
            data_hash='',
            universe=('SOLUSDT',),
            start_ns=tape[0].event_time,
            end_ns=tape[-1].event_time,
        )
        t0 = time.perf_counter()
        if profile:
            pr = cProfile.Profile()
            pr.enable()
            report = lab.run(manifest, experts)
            pr.disable()
            t1 = time.perf_counter()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats(45)
            print(s.getvalue())
        else:
            report = lab.run(manifest, experts)
            t1 = time.perf_counter()
        print(f'n_bars={n_bars} experts={len(experts)} '
              f'candidates={report.candidate_count} elapsed={t1 - t0:.2f}s')
        return t1 - t0


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8760
    if which == 'all':
        run_profile(ALL, n_bars=n)
    elif which == 'pilot':
        run_profile([TrendPullbackExpert(), FailedBreakoutExpert(),
                     LiquiditySweepReclaimExpert()], n_bars=n)
    elif which == 'profile':
        run_profile(ALL, n_bars=n, profile=True)
    else:
        raise SystemExit(f'unknown mode {which!r}')
