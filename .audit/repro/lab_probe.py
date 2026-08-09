"""Probe harness for the #61-#72 audit reproductions.

Runs the full expert slate over a real-tape window and captures BOTH populations
needed by the issues:

  * the ALL-SETUPS population — every unique draft the experts emit, re-simulated
    offline through the canonical simulator (no ExposureBook contention), and
  * the EXECUTED population — the subset that actually entered through
    Lab.run()'s ExposureBook + risk gate (the ledger's real outcome records).

Everything is deterministic and runs against the CURRENT working tree, so the
same harness produces the before (baseline) and after (fixed) numbers.

Usage (import-only; the repro scripts import `probe_*`):
    from lab_probe import load_window, detect_drafts, run_lab, offline_resim
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

from v8.store import AppendOnlyLog  # noqa: E402
from v8.lab import Lab  # noqa: E402
from v8.schema import ExperimentManifest  # noqa: E402
from v8.lifecycle import episode_key  # noqa: E402
from v8.simulator import CanonicalSimulator  # noqa: E402

# The full admitted pilot slate (docs/EXPERTS_REGISTRY.yaml, D-042), in the
# canonical registry order from v8/experts/__init__.py.
from v8.experts import (  # noqa: E402
    TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert,
    FailedBreakout2BExpert, TrendPullbackDepthExpert, RangeBreakout1To1Expert,
    CandlestickReversalExpert, RsiStochReversionExpert, MacdStochTrendExpert,
    Divergence12SetupsExpert, BollingerBreakoutExpert, BollingerReversionExpert,
    DonchianBreakoutExpert, BreakoutRetestExpert, FibRetracementContinuationExpert,
    FibProjectionReversalExpert, PatternMeasuringObjectiveExpert,
    VolumeConfirmedBreakoutExpert, VolumeClimaxReversalExpert, ObvAdlRegimeExpert,
    IchimokuCloudExpert, FloorTraderPivotExpert, MarketProfileValueAreaExpert,
    GapExhaustionExpert, OpenInterestDivergenceExpert, FundingCrowdingReversalExpert,
    PandfBreakoutExpert,
)

ALL_EXPERT_CLASSES = [
    TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert,
    FailedBreakout2BExpert, TrendPullbackDepthExpert, RangeBreakout1To1Expert,
    CandlestickReversalExpert, RsiStochReversionExpert, MacdStochTrendExpert,
    Divergence12SetupsExpert, BollingerBreakoutExpert, BollingerReversionExpert,
    DonchianBreakoutExpert, BreakoutRetestExpert, FibRetracementContinuationExpert,
    FibProjectionReversalExpert, PatternMeasuringObjectiveExpert,
    VolumeConfirmedBreakoutExpert, VolumeClimaxReversalExpert, ObvAdlRegimeExpert,
    IchimokuCloudExpert, FloorTraderPivotExpert, MarketProfileValueAreaExpert,
    GapExhaustionExpert, OpenInterestDivergenceExpert, FundingCrowdingReversalExpert,
    PandfBreakoutExpert,
]

TAPE_PATH = REPO / 'research/tape/btcusdt-1h-12m/tape.jsonl'
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
UNIVERSE = (SYMBOL,)


def load_window(tape_path: Path = TAPE_PATH, n_bars: int = 2500):
    """Rows (pit) up to and including the n_bars-th closed kline."""
    rows = AppendOnlyLog(tape_path).replay_tape()
    bars = [r for r in rows if r.channel == 'kline'
            and r.payload.get('closed') is True]
    cutoff = bars[min(n_bars, len(bars)) - 1].available_time
    subset = [r for r in rows if r.available_time <= cutoff]
    return subset


def _series_for(pit, universe=UNIVERSE, base_interval=INTERVAL):
    from v8.marketstate import build_bar_series
    series = {}
    for sym in universe:
        sym_kline = [r for r in pit if r.instrument == sym
                     and r.channel == 'kline']
        if any(b.payload.get('closed') is True for b in sym_kline):
            series[sym] = build_bar_series(
                [b for b in sym_kline if b.payload.get('closed') is True],
                sym_kline,
                [r for r in pit if r.instrument == sym and r.channel == 'funding'],
                [r for r in pit if r.instrument == sym
                 and r.channel == 'open_interest'])
    return {base_interval: series}


def detect_drafts(rows, expert_classes=ALL_EXPERT_CLASSES,
                  n_bars: int = 2500):
    """Replicate the lab's PHASE-3 detection loop: evaluate every expert in
    canonical sorted-expert_id order at every bar, collect each unique draft
    (deduped by episode_key). Returns (states, drafts) where drafts is a list of
    (cid, draft, birth_idx) and states maps bar available_time -> MarketState.

    The lab's per-bar state is rebuilt via build_multi_state with the series
    cache (byte-identical to the uncached path, pinned by
    tests/test_state_cache_identity.py).
    """
    from v8.marketstate import build_multi_state
    experts = [cls() for cls in expert_classes]
    pit = sorted(rows, key=lambda r: r.available_time)
    bars = [r for r in pit if r.channel == 'kline'
            and r.payload.get('closed') is True][:n_bars]
    # declared interval/depth union, mirroring Lab.run
    from v8.interval import INTERVAL_NS
    declared_union: list[str] = []
    depth_union: dict[str, int] = {}
    for ex in experts:
        if not hasattr(ex, 'declared_intervals'):
            continue
        for tf in ex.declared_intervals(INTERVAL):
            if tf != INTERVAL and tf not in declared_union:
                declared_union.append(tf)
            depth_union[tf] = max(depth_union.get(tf, 0), ex.declared_depth(tf))
    declared_union.sort(key=lambda t: INTERVAL_NS.get(t, 0))
    series = _series_for(pit)
    # incremental row accumulation identical to Lab.run
    states = {}
    acc_rows: list = []
    pit_it = iter(pit)
    next_row = next(pit_it, None)
    for bar in bars:
        while next_row is not None and next_row.available_time <= bar.available_time:
            acc_rows.append(next_row)
            next_row = next(pit_it, None)
        states[bar.available_time] = build_multi_state(
            acc_rows, bar.available_time, UNIVERSE,
            base_interval=INTERVAL, intervals=tuple(declared_union),
            depths=depth_union, series=series)
    from v8.lab import _geometry_version, _view_for
    drafts = []
    seen: set[str] = set()
    for i, bar in enumerate(bars):
        as_of = bar.available_time
        state = states[as_of]
        for ex in sorted(experts, key=lambda e: e.expert_id):
            view = _view_for(ex, state, INTERVAL, frozenset(INTERVAL_NS))
            ev = ex.evaluate(view)
            if ev.draft is None:
                continue
            d = ev.draft
            cid = episode_key(ex.expert_id, ex.version, d.instrument,
                              d.direction, d.setup_anchor_event_id,
                              _geometry_version(d))
            if cid in seen:
                continue
            seen.add(cid)
            drafts.append((cid, d, i))
    return states, drafts


def run_lab(rows, store_dir=None, expert_classes=ALL_EXPERT_CLASSES,
            **manifest_kwargs):
    """Full Lab.run() over the window with parameterizable manifest economics.

    Returns (lab, report-as-dict). Reads the outcome ledger afterward for the
    executed population. `store_dir` must be a fresh path (one store = one run).
    """
    experts = [cls() for cls in expert_classes]
    kline_events = [r.event_time for r in rows if r.channel == 'kline']
    # code_hash/data_hash are left falsy so the lab computes the LIVE hashes of
    # the current working tree (repro runs are pinned per-run by the lab's own
    # report hashes, not by a stale manifest pin).
    manifest = ExperimentManifest(
        experiment_id='audit-repro',
        code_hash='', data_hash='',
        universe=UNIVERSE,
        start_ns=min(kline_events) if kline_events else 0,
        end_ns=max(kline_events) if kline_events else 0,
        interval=INTERVAL,
        **manifest_kwargs)
    if store_dir is None:
        store_dir = tempfile.mkdtemp(prefix='v8-audit-repro-')
    lab = Lab(store_dir, universe=UNIVERSE)
    lab.ingest(rows)
    report = lab.run(manifest, experts)
    return lab, report


def executed_outcomes(lab: Lab) -> list[dict]:
    """Outcome records whose label_status != NOT_EXECUTED (the executed
    population), in ledger order."""
    return [o for o in lab.outcomes.read()
            if o.get('label_status') != 'NOT_EXECUTED']


def all_outcomes(lab: Lab) -> list[dict]:
    return lab.outcomes.read()


def offline_resim(rows, drafts, *, cost_r: float = 0.07,
                  lag: int = 2, geometry_override: dict | None = None,
                  n_bars: int = 2500) -> list[dict]:
    """Re-simulate every draft offline (no contention) from `lag` bars after its
    birth bar, FILL_AT_BAR_CLOSE, through the canonical simulator. Returns
    outcome-like dicts (endpoint, net_r, mae_r, mfe_r, cid).

    `geometry_override` (e.g. {'target_r': 1.0, 'stop_r': 1.0}) replaces the
    draft's risk_geometry so different issues compare the SAME signals under a
    different geometry (the audit's "1R:1R" convention).
    """
    from dataclasses import replace as _dreplace
    sim = CanonicalSimulator(round_trip_cost_r=cost_r)
    pit = sorted(rows, key=lambda r: r.available_time)
    bars = [r for r in pit if r.channel == 'kline'
            and r.payload.get('closed') is True][:n_bars]
    out = []
    for cid, draft, birth_idx in drafts:
        entry_idx = birth_idx + lag
        if entry_idx >= len(bars):
            continue
        d = draft
        if geometry_override is not None:
            d = _dreplace(draft, risk_geometry={**draft.risk_geometry,
                                                **geometry_override})
        tail = [b.payload for b in bars[entry_idx:]]
        times = [b.available_time for b in bars[entry_idx:]]
        r = sim.run(d, tail, times=times)
        out.append({'cid': cid, 'expert_id': draft.expert_id,
                    'direction': draft.direction,
                    'endpoint': r.endpoint, 'net_r': r.net_r,
                    'mae_r': r.mae_r, 'mfe_r': r.mfe_r,
                    'birth_idx': birth_idx,
                    'geometry': dict(draft.risk_geometry)})
    return out


def stats(net_rs: list[float]) -> dict:
    n = len(net_rs)
    if not n:
        return {'n': 0, 'mean_net_r': None, 'win_rate': None, 'total_r': 0.0}
    return {'n': n, 'mean_net_r': sum(net_rs) / n,
            'win_rate': sum(1 for x in net_rs if x > 0) / n,
            'total_r': sum(net_rs)}
