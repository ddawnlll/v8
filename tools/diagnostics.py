"""Single report center for V8 diagnostics (consolidated 2026-08-08).

One file, one report: the deterministic diagnostic engine (9 sections +
per-expert forensics + portfolio verdict), the multi-symbol matrix runner,
and the self-contained HTML renderer all live here. Everything else that used
to import `tools.diagnostic`, `tools.forensics`, `tools.diagnostic_report` or
`tools.multi_diagnostic` continues to work through the thin re-export shims
in those paths.

Entry points:
- `run_diagnostic(tape, expert_classes, out_dir, **kw)` — single-report run.
- `run_multi(tape_path, symbols, timeframes, *, span_ns, out_dir, ...)` —
  multi-symbol matrix run (the former multi_diagnostic).
- `render_html(report, trades)` / `render_multi_html(report)` — HTML render.
- `main(argv)` — CLI: single report by default; pass `--symbols` for the
  matrix report.
"""
from __future__ import annotations
import json
import math
import platform
import random
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from v8.lab import _geometry_version, _view_for
from v8.lifecycle import episode_key
from v8.marketstate import build_multi_state, build_bar_series
from v8.schema import CandidateDraft, sha1_hex, record_dict
from v8.simulator import CanonicalSimulator, OpenPosition, risk_unit
from v8.store import AppendOnlyLog
from v8.synth import HOUR_NS
from v8.interval import INTERVAL_NS

# Report center identity: the tools/ parent is the repo root, and running
# this file standalone (python tools/diagnostics.py) needs the repo on sys.path
# for the `v8.*` and `tools.*` imports, exactly as the pre-consolidation
# diagnostic.py set it up.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO))
import html
from v8.interval import aggregate
from v8.experts import ( TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert, FailedBreakout2BExpert, TrendPullbackDepthExpert, RangeBreakout1To1Expert, CandlestickReversalExpert, RsiStochReversionExpert, MacdStochTrendExpert, Divergence12SetupsExpert, BollingerBreakoutExpert, BollingerReversionExpert, DonchianBreakoutExpert, BreakoutRetestExpert, FibRetracementContinuationExpert, FibProjectionReversalExpert, PatternMeasuringObjectiveExpert, VolumeConfirmedBreakoutExpert, VolumeClimaxReversalExpert, ObvAdlRegimeExpert, IchimokuCloudExpert, FloorTraderPivotExpert, MarketProfileValueAreaExpert, GapExhaustionExpert, OpenInterestDivergenceExpert, FundingCrowdingReversalExpert, PandfBreakoutExpert, )



ENGINE_VERSION = 'diagnostic-v1'
HORIZONS_BARS = (1, 2, 4, 8, 12, 24, 48, 72, 96, 120, 168)   # 1h..7d
MARKOUT_DELTAS = (1, 2, 3, 6, 12, 24)                        # bars after entry
SL_GRID = (0.5, 0.75, 1.0, 1.5, 2.0)
TP_GRID = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
NULL_REPLICATIONS = 200
NULL_MAX_ENTRIES = 1000
TOLERANCE = 1e-9

VERDICTS = ('MECHANICAL_FLOOR', 'COST_DOMINATED', 'NO_EDGE',
            'EXIT_MISSPECIFIED', 'SIMULATOR_INVALID', 'INDETERMINATE')

_WRITE_GUARD = 'diagnostic engine is read-only against the decision path'
_ALLOWED_OUT = ('report.md', 'report.json', 'report.html', 'trades.jsonl',
                'manifest.json')


class DiagnosticWriteError(RuntimeError):
    """Raised on any attempt to write outside the engine's own output dir."""


_PROTECTED_DIRS = ('src', 'docs', 'site', 'research', 'tests', 'tools')
_STORE_ARTIFACTS = ('candidates.jsonl', 'outcomes.jsonl', 'tape.jsonl',
                    'states.jsonl', 'evaluations.jsonl', 'manifest.json')


def _provenance() -> dict:
    """Wall-clock provenance for the report header — the ONLY non-deterministic
    field in a diagnostic run. Every economic number is a pure function of
    (tape, code, config, seed) and is byte-deterministic; this stamp records
    WHEN and WHERE the report was produced so it is attributable (a report
    without a date is a report without an audit trail)."""
    git = None
    try:
        git = subprocess.run(
            ['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        git = None
    return {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'python_version': sys.version.split()[0],
        'platform': platform.platform(),
        'host': platform.node(),
        'git_commit': git,
    }


def _guard_no_write(path: Path) -> None:
    """Fail closed if a caller tries to write a non-artifact path.

    The engine is read-only against the decision path: it must never write a
    store ledger, a registry/authority file, or anything under the repo's
    protected dirs. Its own artifacts (the four names in _ALLOWED_OUT) may go
    anywhere the caller designates (e.g. a scratch/test dir). The protected-dir
    check is RELATIVE to the repo root (`Path(__file__).parents[1]`): the
    absolute path may legitimately contain `src` (e.g. a home dir under
    /Users/.../src/...) without meaning the repo's decision path."""
    if path.name not in _ALLOWED_OUT:
        raise DiagnosticWriteError(f'{_WRITE_GUARD}; refused to write {path}')
    repo_root = Path(__file__).resolve().parents[1]
    try:
        rel = Path(path).resolve().relative_to(repo_root)
    except ValueError:
        return  # outside the repo — not a decision-path target
    for part in rel.parts:
        if part in _PROTECTED_DIRS:
            raise DiagnosticWriteError(
                f'{_WRITE_GUARD}; refused to write under {part}/: {path}')
    if path.name in _STORE_ARTIFACTS:
        raise DiagnosticWriteError(
            f'{_WRITE_GUARD}; refused to write a store ledger: {path}')


@dataclass(frozen=True)
class SimTrade:
    """One simulated trade with the exact R decomposition (identity holds)."""
    candidate_id: str
    expert_id: str
    direction: str
    entry_idx: int
    entry_price: float
    unit: float
    exit_idx: int                  # -1 if the tape ended before expiry
    endpoint: str                  # TARGET | STOP | EXPIRY | TIME_EXIT
    net_r: float
    gross_r: float                 # sign*(exit-entry)/unit  (derived, exact)
    cost_r: float
    funding_r: float
    mae_r: float
    mfe_r: float
    ambiguous_bars: int
    bars_held: int
    exit_price: float
    stop_r: float                  # the stop_r actually simulated (override or own)
    target_r: float                # the target_r actually simulated
    stop_price: float              # the ABSOLUTE stop level used (stop_ref if
                                   # declared, else entry - sign*stop_r*unit)
    time_to_mae: int               # last bar index where mae_r reached its max
    time_to_mfe: int               # last bar index where mfe_r reached its max
    post_exit_max_r: float | None  # max favorable R in the 24 bars after exit


@dataclass(frozen=True)
class _WalkResult:
    """The bar walk of one (draft, entry) under ZERO cost/funding.

    `CanonicalSimulator.step()` reads `round_trip_cost_r` only in the terminal
    net formula (and the breakeven-margin default — no v8 draft declares a
    breakeven roll, so it cannot matter), and funding only accumulates
    `funding_paid_r` — neither changes the walk's endpoint, exit index,
    excursions or holding time. So one frictionless walk serves every
    cost/funding re-arithmetic: Section 2's four ablations, the forensics cost
    sweep and the six identical full-set sims all share it (the diagnostic's
    dominant cost on a multi-month tape).

    `walk_net` is the frictionless leg (`realized + remaining*leg`); a
    requested (cost, funding) re-derives `net = walk_net - cost - funding`,
    which is BIT-EXACT for the scalar funding path (identical expression tree
    to a dedicated walk's `realized + remaining*leg - cost - funding`), and the
    only non-derivable case (a non-zero funding rate) keeps the dedicated
    `_simulate_full` fallback.
    """
    entry: float
    unit: float
    stop_r: float
    target_r: float
    stop_price: float
    exit_idx: int
    endpoint: str
    bars_held: int
    mae_r: float
    mfe_r: float
    ambiguous_bars: int
    time_to_mae: int
    time_to_mfe: int
    funding_paid: float
    walk_net: float
    post_exit_max: float | None
    direction: str
    expert_id: str


def _mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def _pct(xs, q):
    if not xs:
        return float('nan')
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _realized_vol(closes, at):
    """Std of log returns over the 32 bars before `at` (per-bar sigma)."""
    lo = max(0, at - 32)
    if at - lo < 4:
        return float('nan')
    rets = [math.log(closes[j] / closes[j - 1])
            for j in range(lo + 1, at + 1) if closes[j - 1] > 0]
    if len(rets) < 4:
        return float('nan')
    m = sum(rets) / len(rets)
    return math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))


class DiagnosticEngine:
    """Runs the 9 diagnostic sections on one fixed entry set."""

    def __init__(self, tape, expert_classes, *, cost_r=0.07, funding_rate_r=0.0,
                 funding_hours=8, fill_policy='FILL_AT_BAR_CLOSE', lag=2,
                 window_bars=None, allow_surface=False, seed=7,
                 store_dir=None, base_interval='1h', do_forensics=True,
                 cost_bps=None):
        self.cost_r = cost_r
        # bps-of-notional cost. When set it REPLACES the flat R charge for the
        # DEFAULT cost only; the cost sweep and the zero-cost ablation still
        # pass explicit R values, because their job is to vary the charge
        # against a fixed geometry.
        self.cost_bps = cost_bps
        self.funding_rate_r = funding_rate_r
        self.funding_hours = funding_hours
        self.fill_policy = fill_policy
        self.lag = lag
        self.allow_surface = allow_surface
        self.seed = seed
        self.do_forensics = do_forensics
        self.base_interval = base_interval
        self.store_dir = Path(store_dir) if store_dir else None

        rows = sorted(tape, key=lambda r: r.available_time)
        self.bars = [r for r in rows if r.channel == 'kline'
                     and r.payload.get('closed') is True]
        if window_bars:
            self.bars = self.bars[:window_bars]
        if not self.bars:
            raise ValueError('diagnostic: tape has no closed klines')
        # Uniqueness / monotonicity (invariant 4, checked here and in §9).
        avails = [b.available_time for b in self.bars]
        if len(avails) != len(set(avails)):
            raise ValueError('diagnostic: duplicate decision clocks (available_time)')
        self.times = avails
        self._interval_ns = INTERVAL_NS.get(base_interval, HOUR_NS)
        self._experts = [cls() for cls in expert_classes]

        # Detect the fixed entry set (canonical detection + D-053 view).
        self.drafts: list[tuple[CandidateDraft, int]] = self._detect()
        self.entry_indices = [min(bi + lag, len(self.bars) - 1)
                              for _, bi in self.drafts]
        # Precompute closes for realized-vol / mark-out.
        self.closes = [float(b.payload['close']) for b in self.bars]
        # Walk memoization: one bar walk per (draft, entry, geometry) serves
        # every cost/funding variant the sections ask for (see _WalkResult).
        self._walk_cache: dict[tuple, _WalkResult] = {}

    # ------------------------------------------------------------------ #
    # Detection (mirrors lab.run PHASE 3: sorted expert_id, _view_for)
    # ------------------------------------------------------------------ #
    def _detect(self) -> list[tuple[CandidateDraft, int]]:
        from v8.interval import INTERVAL_NS as _NS
        universe = tuple({r.instrument for r in self.bars})
        if not universe:
            return []
        declared_union: list[str] = []
        depth_union: dict[str, int] = {}
        for ex in self._experts:
            if not hasattr(ex, 'declared_intervals'):
                continue
            for tf in ex.declared_intervals(self.base_interval):
                if tf != self.base_interval and tf not in declared_union:
                    declared_union.append(tf)
                depth_union[tf] = max(depth_union.get(tf, 0),
                                      ex.declared_depth(tf))
        declared_union.sort(key=lambda t: _NS.get(t, 0))
        pit = sorted(self.bars, key=lambda r: r.available_time)
        series = {}
        for sym in universe:
            sym_kline = [r for r in pit if r.instrument == sym]
            series[sym] = build_bar_series(
                [r for r in sym_kline if r.payload.get('closed') is True],
                sym_kline,
                [r for r in pit if r.channel == 'funding' and r.instrument == sym],
                [r for r in pit if r.channel == 'open_interest'
                 and r.instrument == sym])
        states = {}
        acc: list = []
        it = iter(pit)
        nxt = next(it, None)
        for i, bar in enumerate(self.bars):
            while nxt is not None and nxt.available_time <= bar.available_time:
                acc.append(nxt)
                nxt = next(it, None)
            states[i] = build_multi_state(
                acc, bar.available_time, universe,
                base_interval=self.base_interval,
                intervals=tuple(declared_union), depths=depth_union,
                series={self.base_interval: series})
        known = frozenset(_NS)
        out: list[tuple[CandidateDraft, int]] = []
        seen: set[str] = set()
        # D-054 per-expert MarketState audit: every Expert evaluates a VIEW of
        # the canonical state projected to its declared intervals + `requires`
        # groups. This records each expert's declaration and verifies the view
        # actually withheld every undeclared feature group (the projection is
        # enforced by project_state, but the report must SAY it is — the
        # user-facing confirmation that "each expert has its own MarketState").
        #
        # Perf (2026-08-07): everything below is invariant to the bar index —
        # the expert sort, the declaration, the group closure and the projection
        # spec — so it is hoisted once. Only `_view_for` + `evaluate` are
        # per-bar (a profiled hot path on a multi-month tape).
        from v8.marketstate import group_closure, projection_allowed_keys
        sorted_experts = sorted(self._experts, key=lambda e: e.expert_id)
        self.expert_state_audit: dict[str, dict] = {}
        view_specs: dict[str, tuple] = {}
        for ex in sorted_experts:
            intervals = ex.declared_intervals(self.base_interval)
            groups = tuple(getattr(ex, 'requires', ()) or ())
            closure = group_closure(groups)
            view_specs[ex.expert_id] = (
                projection_allowed_keys(universe, closure,
                                        frozenset(intervals) | {self.base_interval},
                                        self.base_interval, known),
                {tf: ex.declared_depth(tf) for tf in intervals},
                intervals, closure)
            self.expert_state_audit[ex.expert_id] = {
                'intervals': list(intervals),
                'requires': list(groups),
                'depth': {tf: ex.declared_depth(tf) for tf in intervals},
                'canonical_feature_count': 0,
                'view_feature_count': 0,
                'view_groups_verified': True,
            }
        for i, bar in enumerate(self.bars):
            state = states[i]
            for ex in sorted_experts:
                spec = view_specs[ex.expert_id]
                view = _view_for(ex, state, self.base_interval, known,
                                 allowed_keys=spec[0], depths=spec[1],
                                 intervals=spec[2])
                aud = self.expert_state_audit[ex.expert_id]
                aud['canonical_feature_count'] = len(state.features)
                aud['view_feature_count'] = len(view.features)
                aud['view_groups_verified'] = aud['view_groups_verified'] and all(
                    fv.group in spec[3] for fv in view.features.values())
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
                out.append((d, i))
        return out

    # ------------------------------------------------------------------ #
    # Simulation core — one canonical path, geometry overrides only
    # ------------------------------------------------------------------ #
    def _walk_result(self, draft: CandidateDraft, entry_idx: int, *,
                     sl: float | None = None, tp: float | None = None,
                     expiry: int | None = None,
                     geometry_extra: dict | None = None) -> _WalkResult:
        """Run (or fetch) the bar walk for one (draft, entry, geometry) under
        ZERO cost/funding. The walk is a pure function of the geometry — cost
        and funding enter only the terminal net arithmetic — so identical
        (draft, entry, sl/tp/expiry) pairs share one walk across sections."""
        key = (id(draft), entry_idx, sl, tp, expiry,
               tuple(sorted((geometry_extra or {}).items())))
        cached = self._walk_cache.get(key)
        if cached is not None:
            return cached
        entry = float(self.bars[entry_idx].payload['close'])
        unit = risk_unit(draft, entry)
        geom = dict(draft.risk_geometry)
        if sl is not None:
            geom['stop_r'] = float(sl)
        if tp is not None:
            geom['target_r'] = float(tp)
        if expiry is not None:
            geom['expiry_bars'] = int(expiry)
        if geometry_extra:
            geom.update(geometry_extra)
        draft2 = replace(draft, risk_geometry=geom)
        sim = CanonicalSimulator(
            round_trip_cost_r=0.0, funding_rate_r=0.0,
            funding_hours=self.funding_hours, fill_policy=self.fill_policy)
        pos = OpenPosition(candidate_id=f'{draft.expert_id}:{entry_idx}',
                           draft=draft2, entry_price=entry,
                           entry_bar_index=entry_idx,
                           entry_time_ns=self.times[entry_idx])
        sign = 1.0 if draft.direction == 'LONG' else -1.0
        # The ABSOLUTE stop the simulator actually uses: the frozen structural
        # stop when declared (issue #63), else the ATR-multiple of the entry.
        stop_price = (float(geom['stop_ref']) if 'stop_ref' in geom
                      else entry - sign * float(geom['stop_r']) * unit)
        time_to_mae = time_to_mfe = entry_idx
        prev_mae = prev_mfe = 0.0
        for k in range(entry_idx + 1, len(self.bars)):
            res = sim.step(pos, self.bars[k].payload, bar_time=self.times[k])
            nxt = res.next_pos if res.next_pos is not None else pos
            if nxt.mae_r > prev_mae:
                time_to_mae = k
            if nxt.mfe_r > prev_mfe:
                time_to_mfe = k
            prev_mae, prev_mfe = nxt.mae_r, nxt.mfe_r
            if res.closed and res.endpoint and res.net_r is not None:
                wr = _WalkResult(
                    entry=entry, unit=unit,
                    stop_r=float(geom['stop_r']),
                    target_r=float(geom['target_r']), stop_price=stop_price,
                    exit_idx=k, endpoint=res.endpoint, bars_held=nxt.bars_held,
                    mae_r=nxt.mae_r, mfe_r=nxt.mfe_r,
                    ambiguous_bars=nxt.ambiguous_bars,
                    time_to_mae=time_to_mae, time_to_mfe=time_to_mfe,
                    funding_paid=nxt.funding_paid_r, walk_net=res.net_r,
                    post_exit_max=self._post_exit_max(draft, entry, unit, k),
                    direction=draft.direction, expert_id=draft.expert_id)
                self._walk_cache[key] = wr
                return wr
            pos = nxt
        # Tape ended before expiry.
        final_close = float(self.bars[-1].payload['close'])
        net = sim.close_out(pos, final_close)
        wr = _WalkResult(
            entry=entry, unit=unit, stop_r=float(geom['stop_r']),
            target_r=float(geom['target_r']), stop_price=stop_price,
            exit_idx=len(self.bars) - 1, endpoint='EXPIRY',
            bars_held=pos.bars_held, mae_r=pos.mae_r, mfe_r=pos.mfe_r,
            ambiguous_bars=pos.ambiguous_bars,
            time_to_mae=time_to_mae, time_to_mfe=time_to_mfe,
            funding_paid=pos.funding_paid_r, walk_net=net,
            post_exit_max=None, direction=draft.direction,
            expert_id=draft.expert_id)
        self._walk_cache[key] = wr
        return wr

    def _simulate(self, draft: CandidateDraft, entry_idx: int, *,
                  sl: float | None = None, tp: float | None = None,
                  expiry: int | None = None, cost_r: float | None = None,
                  funding_rate_r: float | None = None,
                  geometry_extra: dict | None = None) -> SimTrade:
        """SimTrade for a requested (cost, funding), sharing the geometry walk
        across all variants. Bit-exact for the scalar funding path: net_r is
        `walk_net - cost - funding`, the identical expression tree a dedicated
        walk evaluates, and every other field is cost/funding-invariant. A
        non-zero funding rate falls back to a dedicated full walk (never hit
        by the real sections, which use the default funding rate 0.0)."""
        cost = self.cost_r if cost_r is None else cost_r
        f_rate = self.funding_rate_r if funding_rate_r is None \
            else funding_rate_r
        if f_rate != 0.0:
            return self._simulate_full(draft, entry_idx, sl=sl, tp=tp,
                                       expiry=expiry, cost_r=cost,
                                       funding_rate_r=f_rate,
                                       geometry_extra=geometry_extra)
        funding = 0.0
        wr = self._walk_result(draft, entry_idx, sl=sl, tp=tp, expiry=expiry,
                               geometry_extra=geometry_extra)
        # A bps cost is entry-price / R-unit dependent, so it can only be
        # resolved once the walk has produced them. An EXPLICIT cost_r
        # argument still wins — the cost sweep and the zero-cost ablation pass
        # one deliberately and must not be silently overridden.
        if cost_r is None and self.cost_bps is not None:
            cost = (self.cost_bps / 10_000.0) * wr.entry / wr.unit
        # Bit-exact: same expression tree as the dedicated walk's
        # `realized + remaining*leg - cost - 0.0` (walk_net is that leg).
        net = wr.walk_net - cost
        gross = net + cost + funding
        sign = 1.0 if wr.direction == 'LONG' else -1.0
        exit_price = wr.entry + sign * gross * wr.unit
        return SimTrade(
            candidate_id=f'{draft.expert_id}:{entry_idx}',
            expert_id=wr.expert_id, direction=wr.direction,
            entry_idx=entry_idx, entry_price=wr.entry, unit=wr.unit,
            exit_idx=wr.exit_idx, endpoint=wr.endpoint, net_r=net,
            gross_r=gross, cost_r=cost, funding_r=funding,
            mae_r=wr.mae_r, mfe_r=wr.mfe_r, ambiguous_bars=wr.ambiguous_bars,
            bars_held=wr.bars_held, exit_price=exit_price,
            stop_r=wr.stop_r, target_r=wr.target_r, stop_price=wr.stop_price,
            time_to_mae=wr.time_to_mae, time_to_mfe=wr.time_to_mfe,
            post_exit_max_r=wr.post_exit_max)

    def _simulate_full(self, draft: CandidateDraft, entry_idx: int, *,
                       sl: float | None = None, tp: float | None = None,
                       expiry: int | None = None, cost_r: float | None = None,
                       funding_rate_r: float | None = None,
                       geometry_extra: dict | None = None) -> SimTrade:
        """Dedicated full walk for a funding rate the memoized path cannot
        derive (non-zero) — the exact pre-memoization behavior, kept as the
        correctness fallback."""
        entry = float(self.bars[entry_idx].payload['close'])
        unit = risk_unit(draft, entry)
        geom = dict(draft.risk_geometry)
        if sl is not None:
            geom['stop_r'] = float(sl)
        if tp is not None:
            geom['target_r'] = float(tp)
        if expiry is not None:
            geom['expiry_bars'] = int(expiry)
        if geometry_extra:
            geom.update(geometry_extra)
        draft2 = replace(draft, risk_geometry=geom)
        sim = CanonicalSimulator(
            round_trip_cost_r=self.cost_r if cost_r is None else cost_r,
            funding_rate_r=self.funding_rate_r if funding_rate_r is None
            else funding_rate_r,
            funding_hours=self.funding_hours, fill_policy=self.fill_policy)
        pos = OpenPosition(candidate_id=f'{draft.expert_id}:{entry_idx}',
                           draft=draft2, entry_price=entry,
                           entry_bar_index=entry_idx,
                           entry_time_ns=self.times[entry_idx])
        sign = 1.0 if draft.direction == 'LONG' else -1.0
        # The ABSOLUTE stop the simulator actually uses: the frozen structural
        # stop when declared (issue #63), else the ATR-multiple of the entry.
        stop_price = (float(geom['stop_ref']) if 'stop_ref' in geom
                      else entry - sign * float(geom['stop_r']) * unit)
        time_to_mae = time_to_mfe = entry_idx
        prev_mae = prev_mfe = 0.0
        for k in range(entry_idx + 1, len(self.bars)):
            res = sim.step(pos, self.bars[k].payload, bar_time=self.times[k])
            nxt = res.next_pos if res.next_pos is not None else pos
            if nxt.mae_r > prev_mae:
                time_to_mae = k
            if nxt.mfe_r > prev_mfe:
                time_to_mfe = k
            prev_mae, prev_mfe = nxt.mae_r, nxt.mfe_r
            if res.closed and res.endpoint and res.net_r is not None:
                net = res.net_r
                funding = nxt.funding_paid_r
                gross = net + (self.cost_r if cost_r is None else cost_r) \
                    + funding
                exit_price = entry + sign * gross * unit
                post = self._post_exit_max(draft, entry, unit, k)
                return SimTrade(
                    candidate_id=f'{draft.expert_id}:{entry_idx}',
                    expert_id=draft.expert_id, direction=draft.direction,
                    entry_idx=entry_idx, entry_price=entry, unit=unit,
                    exit_idx=k, endpoint=res.endpoint, net_r=net,
                    gross_r=gross, cost_r=self.cost_r if cost_r is None
                    else cost_r, funding_r=funding,
                    mae_r=nxt.mae_r, mfe_r=nxt.mfe_r,
                    ambiguous_bars=nxt.ambiguous_bars,
                    bars_held=nxt.bars_held, exit_price=exit_price,
                    stop_r=float(geom['stop_r']),
                    target_r=float(geom['target_r']),
                    stop_price=stop_price,
                    time_to_mae=time_to_mae, time_to_mfe=time_to_mfe,
                    post_exit_max_r=post)
            pos = nxt
        # Tape ended before expiry.
        final_close = float(self.bars[-1].payload['close'])
        net = sim.close_out(pos, final_close)
        funding = pos.funding_paid_r
        cost = self.cost_r if cost_r is None else cost_r
        gross = net + cost + funding
        exit_price = entry + sign * gross * unit
        return SimTrade(
            candidate_id=f'{draft.expert_id}:{entry_idx}',
            expert_id=draft.expert_id, direction=draft.direction,
            entry_idx=entry_idx, entry_price=entry, unit=unit,
            exit_idx=len(self.bars) - 1, endpoint='EXPIRY', net_r=net,
            gross_r=gross, cost_r=cost, funding_r=funding,
            mae_r=pos.mae_r, mfe_r=pos.mfe_r, ambiguous_bars=pos.ambiguous_bars,
            bars_held=pos.bars_held, exit_price=exit_price,
            stop_r=float(geom['stop_r']), target_r=float(geom['target_r']),
            stop_price=stop_price,
            time_to_mae=time_to_mae, time_to_mfe=time_to_mfe,
            post_exit_max_r=None)

    def _post_exit_max(self, draft, entry, unit, exit_idx):
        """Max favorable R over the 24 bars after exit (early-TP evidence)."""
        sign = 1.0 if draft.direction == 'LONG' else -1.0
        best = None
        for k in range(exit_idx + 1, min(exit_idx + 25, len(self.bars))):
            hi = float(self.bars[k].payload['high'])
            lo = float(self.bars[k].payload['low'])
            fav = hi if draft.direction == 'LONG' else lo
            r = sign * (fav - entry) / unit
            if best is None or r > best:
                best = r
        return best

    # ------------------------------------------------------------------ #
    # Section 0 — identity + R-denominator census
    # ------------------------------------------------------------------ #
    def _section0(self, trades):
        bad = [t for t in trades
               if abs(t.net_r - (t.gross_r - t.cost_r - t.funding_r)) > TOLERANCE]
        units = [t.unit for t in trades]
        n_unique = len(set(round(u, 12) for u in units))
        # R-denominator distribution + stop distance vs ATR / realized vol.
        stop_dists = []
        for (draft, bi), t in zip(self.drafts, trades):
            entry_idx = min(bi + self.lag, len(self.bars) - 1)
            entry = float(self.bars[entry_idx].payload['close'])
            stop_price = entry - (1.0 if draft.direction == 'LONG' else -1.0) \
                * float(draft.risk_geometry.get('stop_r', 1.0)) * t.unit
            stop_dist = abs(entry - stop_price)
            atr = float(draft.risk_geometry.get('atr_ref', t.unit))
            rv = _realized_vol(self.closes, entry_idx)
            stop_dists.append({'stop_dist_price': stop_dist,
                               'stop_dist_atr': stop_dist / atr if atr else None,
                               'realized_vol_per_bar': rv,
                               'stop_dist_rv': stop_dist / (rv * entry)
                               if rv and rv > 0 else None})
        return {
            'identity_ok': len(bad) == 0,
            'identity_violations': len(bad),
            'r_denominator': {
                'min': min(units) if units else None,
                'p25': _pct(units, 0.25) if units else None,
                'median': _pct(units, 0.5) if units else None,
                'p75': _pct(units, 0.75) if units else None,
                'max': max(units) if units else None,
                'unique_count': n_unique,
                'constant_warning': n_unique == 1,
            },
            'stop_distance': {'stop_dist_atr_mean': _mean(
                [s['stop_dist_atr'] for s in stop_dists
                 if s['stop_dist_atr'] is not None]),
                'stop_dist_rv_mean': _mean(
                    [s['stop_dist_rv'] for s in stop_dists
                     if s['stop_dist_rv'] is not None]),
                'realized_vol_mean': _mean(
                    [s['realized_vol_per_bar'] for s in stop_dists
                     if s['realized_vol_per_bar'] == s['realized_vol_per_bar']])},
        }

    # ------------------------------------------------------------------ #
    # Section 1 — cost census
    # ------------------------------------------------------------------ #
    def _section1(self, trades):
        n = len(trades)
        gross = _mean([t.gross_r for t in trades])
        cost = _mean([t.cost_r for t in trades])
        funding = _mean([t.funding_r for t in trades])
        net = _mean([t.net_r for t in trades])
        total_net = sum(t.net_r for t in trades)
        breakeven_gross = cost + funding
        # cost is flat (constant in R) -> verify, never assume.
        costs = [t.cost_r for t in trades]
        cost_flat = len({round(c, 12) for c in costs}) == 1
        # funding vs duration correlation (Pearson on the R series).
        durations = [t.bars_held for t in trades]
        fundings = [t.funding_r for t in trades]
        corr = _pearson(durations, fundings)
        return {
            'n': n,
            'rows': {'gross_R': {'mean': gross, 'total': sum(t.gross_r for t in trades)},
                     'cost_R_fee_plus_slippage': {'mean': cost,
                                                  'total': sum(t.cost_r for t in trades)},
                     'funding_R': {'mean': funding,
                                   'total': sum(t.funding_r for t in trades)}},
            'net_R_mean': net, 'net_R_total': total_net,
            'cost_pct_of_net': (cost / net * 100) if net else None,
            'breakeven_gross_R': breakeven_gross,
            'cost_is_flat_R': cost_flat,
            'cost_form': 'flat_r' if self.cost_bps is None else 'bps',
            'cost_bps': self.cost_bps,
            # Under bps the charge is a DISTRIBUTION, not a constant, and the
            # spread is the diagnostic: it is exactly how much the R unit
            # varies across the window. A census that asserts "flat" while a
            # bps cost is configured would be stating the opposite of the
            # model in force.
            'cost_R_min': min(costs) if costs else None,
            'cost_R_max': max(costs) if costs else None,
            'cost_R_median': _pct(sorted(costs), 0.5) if costs else None,
            'cost_flat_note': (
                'cost is ONE flat R charge per trade (fee+slippage as a single '
                'round_trip_cost_r; no per-leg split, no notional % — the '
                'exit-fee-on-exit-notional check is therefore not applicable '
                'and the cost is entry-price-independent by construction). '
                'NOTE: being denominated in R, this charge is invariant to the '
                'R unit — widening the risk unit cannot dilute it. Use '
                '--cost-bps to price cost as a fraction of notional.'
                if self.cost_bps is None else
                f'cost is {self.cost_bps} bps of notional, resolved per trade '
                f'as (bps/1e4) * entry_price / risk_unit — so it MOVES with '
                f'the R unit. The min/max spread below is the R-unit variation '
                f'across the window, not noise.'),
            'funding_duration_corr': corr,
        }

    # ------------------------------------------------------------------ #
    # Section 2 — zero-cost ablation
    # ------------------------------------------------------------------ #
    def _section2(self):
        def run(cost, funding):
            return [self._simulate(d, min(bi + self.lag, len(self.bars) - 1),
                                   cost_r=cost, funding_rate_r=funding)
                    for d, bi in self.drafts]
        actual = run(self.cost_r, self.funding_rate_r)
        no_cost = run(0.0, self.funding_rate_r)
        no_funding = run(self.cost_r, 0.0)
        frictionless = run(0.0, 0.0)
        return {
            'actual': _mean([t.net_r for t in actual]),
            'no_cost': _mean([t.net_r for t in no_cost]),
            'no_funding': _mean([t.net_r for t in no_funding]),
            'frictionless': _mean([t.net_r for t in frictionless]),
            'frictionless_sign': ('positive' if _mean([t.net_r for t in frictionless]) > 0
                                  else 'non-positive'),
            'note_slippage': 'V8 has no separate slippage model; no_cost == no_slip',
        }

    # ------------------------------------------------------------------ #
    # Section 3 — null baselines
    # ------------------------------------------------------------------ #
    def _median_atr(self) -> float:
        """Median atr_ref across the actual entry set — the null baselines use
        this as their standard R unit so null vs actual comparisons are on the
        same R scale."""
        atrs = [float(d.risk_geometry['atr_ref']) for d, _bi in self.drafts
                if d.risk_geometry.get('atr_ref') is not None]
        return _pct(atrs, 0.5) if atrs else float('nan')

    def _null_draft(self, k, direction, tag):
        return CandidateDraft(
            expert_id=tag, expert_version='v1',
            instrument=self.bars[k].instrument, direction=direction,
            setup_fingerprint=f'{tag}:{k}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': self._median_atr()},
            birth_time=self.times[k], setup_anchor_event_id=f'{tag}:{k}')

    def _section3(self, actual_trades):
        rng = random.Random(self.seed)
        actual_mean = _mean([t.net_r for t in actual_trades])
        n = min(len(self.drafts), NULL_MAX_ENTRIES)
        wins = len([t for t in actual_trades if t.net_r > 0])
        # (a) random_entry: uniform random entries + uniform direction, the
        # standard geometry (stop 1.0 / target 1.0 / expiry 8) on the median R
        # unit of the actual entry set.
        def random_run():
            tot = 0.0
            for _ in range(n):
                k = rng.randrange(len(self.bars))
                d = rng.randrange(2)
                draft = self._null_draft(
                    k, 'LONG' if d == 0 else 'SHORT', 'null_random')
                tot += self._simulate(draft, k, sl=1.0, tp=1.0, expiry=8).net_r
            return tot / n
        random_means = [random_run() for _ in range(NULL_REPLICATIONS)]
        random_median = _pct(random_means, 0.5)
        pct_of_random = sum(1 for m in random_means if m <= actual_mean) \
            / len(random_means) * 100
        # (b) inverted_signal: flip directions on the actual entry set.
        inv = []
        for d, bi in self.drafts:
            flipped = replace(d, direction='SHORT' if d.direction == 'LONG'
                              else 'LONG')
            inv.append(self._simulate(
                flipped, min(bi + self.lag, len(self.bars) - 1)))
        inv_mean = _mean([t.net_r for t in inv])
        # (c) always_long / always_short: fixed direction, no signal, same N.
        def fixed_dir(direction):
            tot = 0.0
            for _ in range(n):
                k = rng.randrange(len(self.bars))
                draft = self._null_draft(k, direction,
                                         f'null_{direction.lower()}')
                tot += self._simulate(draft, k, sl=1.0, tp=1.0, expiry=8).net_r
            return tot / n
        always_long = fixed_dir('LONG')
        always_short = fixed_dir('SHORT')
        return {
            'actual_mean': actual_mean,
            'actual_win_rate': wins / len(actual_trades) if actual_trades else None,
            'random_entry': {
                'replications': NULL_REPLICATIONS, 'n_per_run': n,
                'mean': _mean(random_means), 'median': random_median,
                'p05': _pct(random_means, 0.05), 'p95': _pct(random_means, 0.95),
                'actual_percentile': pct_of_random,
                'signal_not_engaged': abs(actual_mean - random_median) < 0.01,
            },
            'inverted_signal_mean': inv_mean,
            'always_long_mean': always_long,
            'always_short_mean': always_short,
        }

    # ------------------------------------------------------------------ #
    # Section 4 — path statistics
    # ------------------------------------------------------------------ #
    def _section4(self, trades):
        reasons = Counter()
        by_reason = {}
        for t in trades:
            reasons[t.endpoint] += 1
            r = by_reason.setdefault(t.endpoint, [])
            r.append(t)
        census = {}
        for ep, group in sorted(by_reason.items()):
            census[ep] = {'count': len(group),
                          'mean_R': _mean([t.net_r for t in group]),
                          'mean_duration': _mean([t.bars_held for t in group])}
        stops = by_reason.get('STOP', [])
        early_sl = [t for t in stops if t.mfe_r > 0.5]
        tps = by_reason.get('TARGET', [])
        early_tp = [t for t in tps
                    if t.post_exit_max_r is not None
                    and t.post_exit_max_r > 2.0 * max(t.net_r, 0.01)]
        ambiguous = [t for t in trades if t.ambiguous_bars > 0]
        # intrabar ambiguity bracket: pessimistic (canonical) vs a local
        # optimistic estimate (target-first on the ambiguous bar). Diagnostic
        # only — the canonical tie-break stays STOP_FIRST in the decision path.
        bracket = None
        if ambiguous:
            opt = []
            for t in ambiguous:
                # optimistic: treat the ambiguous bar as a target fill at the
                # target barrier price.
                entry = t.entry_price
                sign = 1.0 if t.direction == 'LONG' else -1.0
                target = entry + sign * float(self.drafts[0][0].risk_geometry
                                              .get('target_r', 1.0)) * t.unit \
                    if self.drafts else entry
                opt_net = sign * (target - entry) / t.unit \
                    - t.cost_r - t.funding_r
                opt.append(opt_net)
            bracket = {'ambiguous_count': len(ambiguous),
                       'pessimistic_mean': _mean([t.net_r for t in ambiguous]),
                       'optimistic_mean': _mean(opt),
                       'spread_R': abs(_mean(opt) - _mean([t.net_r for t in ambiguous]))}
        return {
            'exit_reason_census': census,
            'early_stop_loss': {
                'n_stopped': len(stops),
                'n_mfe_gt_half_R_before_stop': len(early_sl),
                'fraction': len(early_sl) / len(stops) if stops else None,
                'meaning': 'a stop that saw >0.5R favorable first suggests an '
                           'intrabar SL/TP ordering problem'},
            'early_take_profit': {
                'n_target': len(tps),
                'n_post_exit_gt_2R': len(early_tp),
                'fraction': len(early_tp) / len(tps) if tps else None,
                'mean_post_exit_max_r': _mean(
                    [t.post_exit_max_r for t in tps
                     if t.post_exit_max_r is not None]) if tps else None,
                'meaning': 'a target that continued >2R after exit suggests '
                           'the TP is too tight'},
            'intrabar_ambiguity': bracket or {'ambiguous_count': 0},
            'mae_mfe': {'mae_mean': _mean([t.mae_r for t in trades]),
                        'mfe_mean': _mean([t.mfe_r for t in trades]),
                        'mae_p50': _pct([t.mae_r for t in trades], 0.5),
                        'mfe_p50': _pct([t.mfe_r for t in trades], 0.5)},
        }

    # ------------------------------------------------------------------ #
    # Section 5 — horizon sweep + duration
    # ------------------------------------------------------------------ #
    def _section5(self):
        # actual duration stats from the shipped-geometry simulation
        actual = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1))
                  for d, bi in self.drafts]
        durations = [t.bars_held for t in actual]
        dur = {'mean': _mean(durations), 'median': _pct(durations, 0.5),
               'p90': _pct(durations, 0.9)}
        horizon = {}
        for h in HORIZONS_BARS:
            # variant "clean": no stop/TP, pure mark-to-market at h
            clean = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1),
                                    sl=1e6, tp=1e6, expiry=h)
                     for d, bi in self.drafts]
            nets = [t.net_r for t in clean]
            wins = [t for t in clean if t.net_r > 0]
            losses = [t for t in clean if t.net_r <= 0]
            # variant "stop": shipped stop still fires, no TP
            stop = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1),
                                   tp=1e6, expiry=h)
                    for d, bi in self.drafts]
            stopped_before = sum(1 for t in stop if t.endpoint == 'STOP')
            overlap = self._mean_overlap(h)
            horizon[h] = {
                'net_R': _mean(nets), 'hit_rate': len(wins) / len(clean),
                'mean_win': _mean([t.net_r for t in wins]) if wins else None,
                'mean_loss': _mean([t.net_r for t in losses]) if losses else None,
                'stopped_before_h_at_shipped_SL': stopped_before,
                'mean_overlap_count': overlap,
                'note_overlap': 'CI should be widened via block bootstrap with '
                                'block = h bars when overlap > 1',
            }
        return {'duration_bars': dur, 'duration_by_reason': self._duration_by_reason(actual),
                'horizons': horizon}

    def _duration_by_reason(self, trades):
        out = {}
        for t in trades:
            r = out.setdefault(t.endpoint, [])
            r.append(t.bars_held)
        return {ep: {'mean': _mean(v), 'median': _pct(v, 0.5), 'n': len(v)}
                for ep, v in sorted(out.items())}

    def _mean_overlap(self, h):
        """Mean count of simultaneously-open positions if every entry held h
        bars. Position-time / window (O(N)): mean active count at a random bar
        equals the sum of per-trade holding lengths divided by the window."""
        t = len(self.bars)
        if t == 0:
            return 0.0
        pos_time = 0.0
        for _d, bi in self.drafts:
            s = min(bi + self.lag, t - 1)
            pos_time += min(s + h, t) - s
        return pos_time / t

    # ------------------------------------------------------------------ #
    # Section 6 — exit parameter surface (gated by --allow-surface)
    # ------------------------------------------------------------------ #
    def _section6(self):
        if not self.allow_surface:
            return None
        cells: dict[str, dict] = {}
        for sl in SL_GRID:
            for tp in TP_GRID:
                nets = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1),
                                       sl=sl, tp=tp, expiry=168).net_r
                        for d, bi in self.drafts]
                cells[f'SL={sl},TP={tp}'] = {'mean_net_R': _mean(nets)}
        # no-TP variant (SL only + 7d expiry)
        for sl in SL_GRID:
            nets = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1),
                                   sl=sl, tp=None, expiry=168).net_r
                    for d, bi in self.drafts]
            cells[f'SL={sl},TP=none'] = {'mean_net_R': _mean(nets)}
        # best cell + naive & Bonferroni p-values (two-sided t-test vs 0).
        # The whole surface is printed; no single best value is emphasized.
        n_configs = len(cells)
        best_key = max(cells, key=lambda k: cells[k]['mean_net_R'])
        best_mean = cells[best_key]['mean_net_R']
        m = best_key.split(',')
        sl_s, tp_s = m[0][3:], m[1][3:]
        nets = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1),
                               sl=None if sl_s == 'none' else float(sl_s),
                               tp=None if tp_s == 'none' else float(tp_s),
                               expiry=168).net_r
                for d, bi in self.drafts]
        naive_p = _t_pvalue(nets)
        return {
            'n_configs_searched': n_configs,
            'cells': cells,
            'best_cell': best_key, 'best_mean_net_R': best_mean,
            'naive_p_value': naive_p,
            'bonferroni_p_value': min(1.0, naive_p * n_configs)
            if naive_p is not None else None,
            'promotion_required': 'new preregistration',
            'note': 'full surface printed; no single best value is emphasized',
        }

    # ------------------------------------------------------------------ #
    # Section 7 — entry timing mark-out
    # ------------------------------------------------------------------ #
    def _section7(self):
        out = {}
        for d, bi in self.drafts:
            k = min(bi + self.lag, len(self.bars) - 1)
            entry = float(self.bars[k].payload['close'])
            sign = 1.0 if d.direction == 'LONG' else -1.0
            for delta in MARKOUT_DELTAS:
                j = k + delta
                if j >= len(self.bars):
                    continue
                mo = sign * (float(self.bars[j].payload['close']) - entry) \
                    / entry * 1e4  # bps
                out.setdefault(delta, []).append(mo)
        return {str(delta): {'mean_markout_bps': _mean(vals), 'n': len(vals)}
                for delta, vals in sorted(out.items())}

    # ------------------------------------------------------------------ #
    # Section 8 — segment breakdown (descriptive only)
    # ------------------------------------------------------------------ #
    def _section8(self, trades):
        cells = {}
        for t in trades:
            rv = _realized_vol(self.closes, t.entry_idx)
            vol_t = ('low' if (rv and rv < 0.005) else
                     'high' if (rv and rv > 0.012) else 'mid')
            hour = (self.times[t.entry_idx] // HOUR_NS) % 24
            month = (self.times[t.entry_idx] // HOUR_NS) // (24 * 30) % 12
            for name, key in (('side', t.direction), ('vol_tercile', vol_t),
                              ('session_hour', hour), ('month', month)):
                cell = cells.setdefault((name, key), [])
                cell.append(t.net_r)
        out = {}
        for (name, key), nets in sorted(cells.items()):
            mean = _mean(nets)
            sd = math.sqrt(sum((x - mean) ** 2 for x in nets) / len(nets)) \
                if len(nets) > 1 else float('nan')
            # N needed to detect a true 0.01R mean at 95% two-sided CI.
            min_n = (1.96 * sd / 0.01) ** 2 if sd == sd else float('inf')
            out.setdefault(name, {})[str(key)] = {
                'N': len(nets),
                'net_R': mean if len(nets) >= min_n else None,
                'min_N_for_0_01R': min_n,
                'status': 'INSUFFICIENT' if len(nets) < min_n else 'OK',
            }
        return out

    # ------------------------------------------------------------------ #
    # Section 9 — simulator invariants
    # ------------------------------------------------------------------ #
    def _section9(self, trades):
        fails = []
        # 1: entry fill within the bar range (entry = bar close; OHLC holds).
        for t in trades:
            bar = self.bars[t.entry_idx].payload
            if not (float(bar['low']) - TOLERANCE <= t.entry_price
                    <= float(bar['high']) + TOLERANCE):
                fails.append(f'entry fill {t.candidate_id} out of range')
        # 2/3: exit fill per V8's documented semantics:
        #   STOP   -> worse of barrier and bar open (gap semantics)
        #   TARGET -> exactly the barrier (LIMIT semantics; a favorable gap
        #             through the barrier keeps the barrier fill — the
        #             conservative clip documented as issue #71, NOT an
        #             invariant violation)
        #   other  -> bar close
        for t in trades:
            ebar = self.bars[t.exit_idx].payload
            sign = 1.0 if t.direction == 'LONG' else -1.0
            if t.endpoint == 'STOP':
                barrier = t.stop_price          # the level the simulator used
                open_ = float(ebar['open'])
                worse = min(barrier, open_) if t.direction == 'LONG' \
                    else max(barrier, open_)
                if abs(t.exit_price - worse) > TOLERANCE * max(1.0, abs(worse)):
                    fails.append(f'gap-through {t.candidate_id}: STOP fill '
                                 f'{t.exit_price:.6f} != worse-of {worse:.6f}')
                if not (float(ebar['low']) - TOLERANCE <= t.exit_price
                        <= float(ebar['high']) + TOLERANCE):
                    fails.append(f'STOP exit {t.candidate_id} outside bar range')
            elif t.endpoint == 'TARGET':
                barrier = t.entry_price + sign * t.unit * t.target_r
                if abs(t.exit_price - barrier) > TOLERANCE * max(1.0, abs(barrier)):
                    fails.append(f'limit fill {t.candidate_id}: TARGET exit '
                                 f'{t.exit_price:.6f} != barrier {barrier:.6f}')
                # barrier may sit outside [low, high] on a favorable gap —
                # allowed (limit semantics, issue #71); only check the barrier
                # was actually reachable that bar: traded through normally
                # (low <= barrier <= high) OR gapped through on the favorable
                # side (a LONG's buy limit gapped ABOVE its barrier: lo >
                # barrier; a SHORT's sell limit gapped BELOW its barrier:
                # hi < barrier).
                lo, hi = float(ebar['low']), float(ebar['high'])
                traded = lo - TOLERANCE <= barrier <= hi + TOLERANCE
                gapped = (t.direction == 'LONG' and lo > barrier + TOLERANCE) \
                    or (t.direction == 'SHORT' and hi < barrier - TOLERANCE)
                if not traded and not gapped:
                    fails.append(f'limit fill {t.candidate_id}: barrier '
                                 f'{barrier:.6f} not traded through bar range '
                                 f'[{lo}, {hi}] and no gap')
            else:
                close = float(ebar['close'])
                if abs(t.exit_price - close) > TOLERANCE * max(1.0, abs(close)):
                    fails.append(f'{t.endpoint} exit {t.candidate_id} != bar close')
                if not (float(ebar['low']) - TOLERANCE <= t.exit_price
                        <= float(ebar['high']) + TOLERANCE):
                    fails.append(f'{t.endpoint} exit {t.candidate_id} outside range')
        # 4: funding prefix + monotonicity (no lookahead).
        for a, b in zip(self.times, self.times[1:]):
            if a >= b:
                fails.append('decision clocks not strictly increasing')
        # 5/6: determinism — re-simulate once and compare byte-identical.
        h1 = sha1_hex([(t.candidate_id, t.endpoint, t.net_r) for t in trades])
        trades2 = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1))
                   for d, bi in self.drafts]
        h2 = sha1_hex([(t.candidate_id, t.endpoint, t.net_r) for t in trades2])
        if h1 != h2:
            fails.append('non-determinism: two identical runs diverged')
        return {'ok': not fails, 'fails': fails[:10],
                'n_fails': len(fails),
                'note_parity': 'V8 has ONE canonical simulator; sim-vs-fast_sim '
                               'parity is replaced by run determinism + fill '
                               'semantics checks (limit fills may sit outside '
                               'the bar range on a favorable gap — the '
                               'documented issue-#71 conservative clip)'}

    # ------------------------------------------------------------------ #
    # Verdict
    # ------------------------------------------------------------------ #
    def _verdict(self, sec0, sec1, sec2, sec3, sec4, sec5, sec9):
        if not sec9['ok']:
            return 'SIMULATOR_INVALID', {'section9': 'invariants failed'}
        if not sec0['identity_ok']:
            return 'SIMULATOR_INVALID', {'section0': 'identity violation'}
        frictionless = sec2['frictionless']
        actual = sec2['actual']
        evidence = {}
        # Order matters. MECHANICAL_FLOOR first: if the actual is inside the
        # random-entry null's central 90% (p05..p95 of the replication means),
        # the signal is indistinguishable from random entries — no economic
        # reading (NO_EDGE/COST_DOMINATED) is meaningful yet.
        pct = sec3['random_entry']['actual_percentile']
        p05 = sec3['random_entry']['p05']
        p95 = sec3['random_entry']['p95']
        if p05 <= actual <= p95:
            verdict = 'MECHANICAL_FLOOR'
            evidence = {'section3': f'actual {actual:.4f} inside the random-'
                                    f'entry null [{p05:.4f}, {p95:.4f}] '
                                    f'(percentile {pct:.1f}%) — signal '
                                    'indistinguishable from random entries'}
        elif frictionless <= 0.01:
            verdict = 'NO_EDGE'
            evidence = {'section2': f'frictionless net_R {frictionless:.4f} <= 0.01 '
                                    '(no edge even without cost)'}
        elif actual < -0.005:
            verdict = 'COST_DOMINATED'
            evidence = {'section2': f'frictionless {frictionless:.4f} > 0, '
                                    f'actual {actual:.4f} < 0',
                        'section1': f'breakeven gross {sec1["breakeven_gross_R"]:.4f}',
                        'section3': f'actual percentile of random null '
                                    f'{sec3["random_entry"]["actual_percentile"]:.1f}%'}
        else:
            # frictionless positive and actual not clearly negative — check
            # whether the exits clip a larger signal (horizon / early-TP).
            horizon = sec5['horizons']
            h168 = horizon.get(168, {})
            long_hold = h168.get('net_R', 0.0)
            tp_evidence = sec4['early_take_profit']
            if long_hold > frictionless * 1.5 \
                    or (tp_evidence.get('fraction') or 0) > 0.3:
                verdict = 'EXIT_MISSPECIFIED'
                evidence = {'section2': f'frictionless {frictionless:.4f}',
                            'section5': f'net_R at 7d horizon {long_hold:.4f}',
                            'section4': f'early-TP fraction '
                                        f'{tp_evidence.get("fraction")}'}
            else:
                verdict = 'INDETERMINATE'
                evidence = {'section2': f'frictionless {frictionless:.4f}',
                            'section3': f'random-null percentile '
                                        f'{sec3["random_entry"]["actual_percentile"]:.1f}%'}
        return verdict, evidence

    # ------------------------------------------------------------------ #
    # Run
    # ------------------------------------------------------------------ #
    def run(self) -> dict:
        if self.store_dir is not None:
            self._check_ledger_parity()
        actual = [self._simulate(d, min(bi + self.lag, len(self.bars) - 1))
                  for d, bi in self.drafts]
        sec0 = self._section0(actual)
        sec1 = self._section1(actual)
        sec2 = self._section2()
        sec3 = self._section3(actual)
        sec4 = self._section4(actual)
        sec5 = self._section5()
        sec6 = self._section6()
        sec7 = self._section7()
        sec8 = self._section8(actual)
        sec9 = self._section9(actual)
        verdict, evidence = self._verdict(sec0, sec1, sec2, sec3, sec4, sec5, sec9)
        # Search volume, itemised. A single opaque count understated it: the
        # per-expert exit cross is searched ONCE PER EXPERT, so the number that
        # matters for a multiplicity argument is cells x experts, not cells.
        n_experts = len({d.expert_id for d, _ in self.drafts})
        n_configs_detail = {
            'exit_surface_portfolio': (len(SL_GRID) * (len(TP_GRID) + 1)
                                       if sec6 else 0),
            'horizon_sweep': len(HORIZONS_BARS) * 2,
            'ablation_and_nulls': 5 + 4,
            'exit_cross_per_expert': len(EXIT_CROSS_NAMES),
            'experts_scored': n_experts,
            'exit_cross_total': len(EXIT_CROSS_NAMES) * n_experts,
        }
        n_configs = (n_configs_detail['exit_surface_portfolio']
                     + n_configs_detail['horizon_sweep']
                     + n_configs_detail['ablation_and_nulls']
                     + n_configs_detail['exit_cross_total'])
        report = {
            'authority': 'NONE',
            'diagnostic_only': True,
            'engine_version': ENGINE_VERSION,
            'verdict': verdict,
            'verdict_evidence': evidence,
            'n_configs_searched': n_configs,
            'n_configs_detail': n_configs_detail,
            'promotion_requires': 'new preregistration',
            'sections': {
                'identity': sec0, 'cost_census': sec1, 'ablation': sec2,
                'null_baselines': sec3, 'path_stats': sec4, 'horizon': sec5,
                'exit_surface': sec6, 'entry_timing': sec7, 'segments': sec8,
                'invariants': sec9},
            # D-054 per-expert MarketState audit (which intervals/groups each
            # expert evaluated and whether the projection withheld undeclared
            # groups).
            'state_audit': self.expert_state_audit,
            'coverage': self._coverage(),
            'manifest': self._manifest(),
        }
        if self.do_forensics:
            report['forensics'] = run_forensics(self, seed=self.seed)
        return report

    def _coverage(self) -> dict:
        """What was actually evaluated, versus what exists.

        Two silent gaps this closes:

        1. ZERO-DRAFT experts. An expert that fired no setup on the window
           appears in the state audit and nowhere else — it drops out of the
           decision table because there is nothing to score. "Zero setups in N
           bars" is a finding, not an absence; a threshold that never triggers
           is as reportable as one that triggers badly.

        2. UNREGISTERED VARIANTS. A family's variants are separate classes
           (base.py: parameter/threshold/geometry changes are VARIANTS of one
           family). Only the classes in ALL_EXPERT_CLASSES run. Where variant
           `a` is directionally restricted and its siblings are not, a row
           labelled with the family name reads as a statement about the family
           while measuring one variant — e.g. a long-only `a` shows SHORT n=0,
           which looks like a broken direction and is in fact the registered
           variant's definition.
        """
        import inspect as _inspect
        import pkgutil as _pkgutil
        import importlib as _importlib
        from v8.experts.base import Expert as _Expert
        import v8.experts as _pkg

        evaluated = {d.expert_id for d, _ in self.drafts}
        registered = {}
        for ex in self._experts:
            registered[ex.expert_id] = getattr(ex, 'variant_id', '') or ''
        zero_draft = sorted(set(registered) - evaluated)

        defined, unregistered = 0, []
        reg_names = {type(ex).__name__ for ex in self._experts}
        for m in _pkgutil.iter_modules(_pkg.__path__):
            mod = _importlib.import_module(f'v8.experts.{m.name}')
            for nm, obj in _inspect.getmembers(mod, _inspect.isclass):
                if (issubclass(obj, _Expert) and obj is not _Expert
                        and obj.__module__ == mod.__name__):
                    defined += 1
                    if nm not in reg_names:
                        unregistered.append(
                            {'module': m.name, 'class': nm,
                             'expert_id': getattr(obj, 'expert_id', ''),
                             'variant_id': getattr(obj, 'variant_id', '')})
        unregistered.sort(key=lambda r: (r['module'], r['variant_id'],
                                         r['class']))
        return {
            'registered_experts': len(registered),
            'evaluated_experts': len(evaluated),
            'zero_draft_experts': zero_draft,
            'defined_variant_classes': defined,
            'unregistered_variants': unregistered,
            'note': 'zero-draft experts and unregistered variants are '
                    'reported so the decision table is read as coverage of '
                    'the registered set, never of the family',
        }

    def _manifest(self) -> dict:
        data_hash = sha1_hex([record_dict(r, source=r.source)
                              for r in self.bars])
        multi_interval = [eid for eid, a in self.expert_state_audit.items()
                          if len(a['intervals']) > 1]
        return {'engine_version': ENGINE_VERSION,
                'data_hash': data_hash,
                'seed': self.seed, 'lag': self.lag,
                'provenance': _provenance(),
                'cost_r': self.cost_r, 'cost_bps': self.cost_bps,
                'cost_form': 'flat_r' if self.cost_bps is None else 'bps',
                'funding_rate_r': self.funding_rate_r,
                'fill_policy': self.fill_policy,
                'base_interval': self.base_interval,
                'window_bars': len(self.bars),
                'n_drafts': len(self.drafts),
                'expert_ids': sorted({e.expert_id for e in self._experts}),
                # D-054: every expert evaluates a per-expert MarketState view
                # (its declared intervals + `requires` groups only). Verified
                # per expert (view_groups_verified) and surfaced here.
                'per_expert_state_projection': all(
                    a['view_groups_verified']
                    for a in self.expert_state_audit.values()),
                'multi_interval_experts': multi_interval,
                'adaptations': ['location=tools/ (code-hash boundary, D-032)',
                                'entry set = re-detected drafts, entry at birth+lag close',
                                'all simulation via CanonicalSimulator.step() geometry overrides',
                                'cost is ONE flat round_trip_cost_r (no per-leg fee/slippage)',
                                'horizons in 1h bars (15m not representable)',
                                'no liquidation model; stopped-before-h = shipped-SL stop',
                                'trades.jsonl instead of parquet (stdlib-only, D-031)',
                                f'per-expert MarketState projection (D-054): each expert '
                                'evaluates ONLY its declared intervals + requires groups']}

    # ------------------------------------------------------------------ #
    # Store ledger parity (the real identity check on real data)
    # ------------------------------------------------------------------ #
    def _check_ledger_parity(self) -> None:
        """Spec §0 identity on REAL data: every executed outcome must satisfy
        net_R == gross_R - cost_R - funding_R, where gross_R is reconstructed
        from the outcome's OWN fields (entry_price, risk_unit_price, endpoint)
        and the exit bar (label_available_time) using the canonical exit-price
        semantics. A mismatch means the ledger is internally inconsistent —
        stop the engine (spec: identity violation halts the motor)."""
        store = self.store_dir
        if not (store / 'outcomes.jsonl').exists():
            return
        outcomes = [json.loads(l)
                    for l in (store / 'outcomes.jsonl').read_text().splitlines()]
        cand = [json.loads(l)
                for l in (store / 'candidates.jsonl').read_text().splitlines()]
        owner = {rec['candidate_id']: rec for rec in cand
                 if rec.get('candidate_id') and rec.get('direction')}
        # map available_time -> bar index for exit-bar lookup
        time_to_idx = {t: i for i, t in enumerate(self.times)}
        mismatches = []
        for o in outcomes:
            if o.get('label_status') == 'NOT_EXECUTED':
                continue
            cid = o['candidate_id']
            src = owner.get(cid)
            if src is None:
                continue
            entry = float(o['entry_price'])
            unit = float(o['risk_unit_price'])
            if not unit > 0:
                mismatches.append({'candidate_id': cid,
                                   'reason': 'non-positive risk_unit_price'})
                continue
            sign = 1.0 if src.get('direction') == 'LONG' else -1.0
            net = float(o['net_r'])
            cost = self.cost_r
            funding = 0.0  # scalar funding not split in the ledger either
            # find the exit bar by label_available_time
            exit_idx = time_to_idx.get(int(o.get('label_available_time', 0)))
            if exit_idx is None:
                continue
            ebar = self.bars[exit_idx].payload
            endpoint = o.get('endpoint')
            # reconstruct the exit price via the canonical exit semantics
            geom = {}
            for d, _bi in self.drafts:
                if d.expert_id == src.get('expert_id'):
                    geom = d.risk_geometry
                    break
            if endpoint == 'STOP':
                barrier = entry - sign * float(geom.get('stop_r', 1.0)) * unit
                exit_price = min(barrier, float(ebar['open'])) \
                    if sign > 0 else max(barrier, float(ebar['open']))
            elif endpoint == 'TARGET':
                exit_price = entry + sign * float(geom.get('target_r', 1.0)) * unit
            else:
                exit_price = float(ebar['close'])
            gross = sign * (exit_price - entry) / unit
            expected = gross - cost - funding
            if abs(net - expected) > 1e-6:
                mismatches.append({'candidate_id': cid, 'ledger_net_r': net,
                                   'reconstructed_net_r': expected,
                                   'endpoint': endpoint})
        if mismatches:
            raise RuntimeError(
                'DIAGNOSTIC INVALID — identity violation: ledger net_r does not '
                'reconstruct as gross - cost - funding for '
                f'{len(mismatches)} executed outcomes '
                f'(first: {mismatches[0]})')


def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def _t_pvalue(nets):
    """Two-sided one-sample t-test p-value of mean != 0 (stdlib-only; the
    Student-t tail is computed from the F(1, df) relation through the
    regularized incomplete beta — no scipy under D-031)."""
    n = len(nets)
    if n < 2:
        return None
    m = _mean(nets)
    sd = math.sqrt(sum((x - m) ** 2 for x in nets) / (n - 1))
    if sd == 0 or not math.isfinite(sd):
        return 1.0 if abs(m) < 1e-12 else 0.0
    t = m / (sd / math.sqrt(n))
    df = n - 1
    # T^2 ~ F(1, df): the two-sided t p-value equals P(F(1,df) > t^2) =
    # I_{df/(df+t^2)}(df/2, 1/2) (upper tail of the F CDF).
    x = df / (df + t * t)
    p = _betainc(df / 2.0, 0.5, x)
    return max(0.0, min(1.0, p))


def _betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b) via continued fraction (Numerical
    Recipes betacf). Valid for 0 <= x <= 1."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(_lgamma(a + b) - _lgamma(a) - _lgamma(b)
                  + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _betacf(a, b, x, max_iter=200, eps=3e-9):
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _lgamma(x):
    """Lanczos log-gamma (stdlib `math.lgamma` exists — use it)."""
    return math.lgamma(x)


def _serialize(report) -> str:
    return json.dumps(report, indent=2, sort_keys=True, default=str)


def write_report(out_dir: Path, report: dict, trades) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'report.json').write_text(_serialize(report) + '\n')
    with open(out_dir / 'trades.jsonl', 'w') as f:
        for t in trades:
            f.write(json.dumps({
                'candidate_id': t.candidate_id, 'expert_id': t.expert_id,
                'direction': t.direction, 'entry_idx': t.entry_idx,
                'entry_price': t.entry_price, 'unit': t.unit,
                'exit_idx': t.exit_idx, 'endpoint': t.endpoint,
                'net_r': t.net_r, 'gross_r': t.gross_r, 'cost_r': t.cost_r,
                'funding_r': t.funding_r, 'mae_r': t.mae_r, 'mfe_r': t.mfe_r,
                'ambiguous_bars': t.ambiguous_bars, 'bars_held': t.bars_held,
                'exit_price': t.exit_price, 'time_to_mae': t.time_to_mae,
                'time_to_mfe': t.time_to_mfe}) + '\n')
    (out_dir / 'manifest.json').write_text(
        json.dumps(report['manifest'], indent=2, sort_keys=True) + '\n')
    (out_dir / 'report.md').write_text(_render_md(report))
    # Self-contained HTML report with inline-SVG charts (stdlib-only).
    (out_dir / 'report.html').write_text(
        render_html(report, trades), encoding='utf-8')
    # Guard: these are the ONLY writes the engine performs.
    for p in out_dir.iterdir():
        if p.name not in _ALLOWED_OUT:
            raise DiagnosticWriteError(f'{_WRITE_GUARD}; unexpected artifact {p.name}')


def _render_md(report: dict) -> str:
    s = report['sections']
    lines = [
        '# Diagnostic report',
        '',
        'AUTHORITY: NONE — DIAGNOSTIC ONLY',
        f"VERDICT: **{report['verdict']}**",
        f"Verdict evidence: `{report['verdict_evidence']}`",
        f"configs searched: {report['n_configs_searched']}",
        f"PROMOTION_REQUIRES: {report['promotion_requires']}",
        '',
        '## 9 — Simulator invariants',
        f"ok={s['invariants']['ok']} n_fails={s['invariants']['n_fails']}",
        *(f"  - {f}" for f in s['invariants']['fails']),
        '',
        '## 0 — Identity + R denominator',
        f"identity_ok={s['identity']['identity_ok']} "
        f"violations={s['identity']['identity_violations']}",
        f"R unit: min={s['identity']['r_denominator']['min']:.4g} "
        f"median={s['identity']['r_denominator']['median']:.4g} "
        f"max={s['identity']['r_denominator']['max']:.4g} "
        f"unique={s['identity']['r_denominator']['unique_count']}",
        '',
        '## 1 — Cost census',
        f"net_R mean={s['cost_census']['net_R_mean']:.4f} "
        f"total={s['cost_census']['net_R_total']:.2f}",
        f"gross mean={s['cost_census']['rows']['gross_R']['mean']:.4f}",
        f"cost mean={s['cost_census']['rows']['cost_R_fee_plus_slippage']['mean']:.4f} "
        f"({s['cost_census']['cost_flat_note']})",
        f"funding mean={s['cost_census']['rows']['funding_R']['mean']:.4f}",
        f"breakeven gross_R={s['cost_census']['breakeven_gross_R']:.4f}",
        f"funding-duration corr={s['cost_census']['funding_duration_corr']}",
        '',
        '## 2 — Ablation',
        f"actual={s['ablation']['actual']:.4f} no_cost={s['ablation']['no_cost']:.4f} "
        f"no_funding={s['ablation']['no_funding']:.4f} "
        f"frictionless={s['ablation']['frictionless']:.4f}",
        '',
        '## 3 — Null baselines',
        f"random-entry median={s['null_baselines']['random_entry']['median']:.4f} "
        f"(actual percentile {s['null_baselines']['random_entry']['actual_percentile']:.1f}%)",
        f"inverted={s['null_baselines']['inverted_signal_mean']:.4f} "
        f"always_long={s['null_baselines']['always_long_mean']:.4f} "
        f"always_short={s['null_baselines']['always_short_mean']:.4f}",
        '',
        '## 4 — Path statistics',
        f"exit reasons: {json.dumps(s['path_stats']['exit_reason_census'])}",
        f"early-SL: {s['path_stats']['early_stop_loss']}",
        f"early-TP: {s['path_stats']['early_take_profit']}",
        f"ambiguity: {s['path_stats']['intrabar_ambiguity']}",
        '',
        '## 5 — Horizon sweep (bars = 1h)',
        *[f"h={h}: net_R={s['horizon']['horizons'][h]['net_R']:.4f} "
          f"hit={s['horizon']['horizons'][h]['hit_rate']:.3f} "
          f"overlap={s['horizon']['horizons'][h]['mean_overlap_count']:.2f}"
          for h in HORIZONS_BARS],
        f"actual duration (bars): mean={s['horizon']['duration_bars']['mean']:.1f} "
        f"median={s['horizon']['duration_bars']['median']:.1f} "
        f"p90={s['horizon']['duration_bars']['p90']:.1f}",
        '',
        '## 6 — Exit surface',
        ('(not run; --allow-surface required)' if s['exit_surface'] is None
         else f"n_configs={s['exit_surface']['n_configs_searched']} "
              f"best={s['exit_surface']['best_cell']} "
              f"naive_p={s['exit_surface']['naive_p_value']} "
              f"bonf_p={s['exit_surface']['bonferroni_p_value']}"),
        '',
        '## 7 — Entry timing (mark-out bps)',
        f"{json.dumps(s['entry_timing'])}",
        '',
        '## 8 — Segments',
        f"{json.dumps(s['segments'])}",
        '',
    ]
    return '\n'.join(lines)


def run_diagnostic(tape, expert_classes, out_dir, **kwargs) -> dict:
    """Run the engine and write the artifacts. Returns the report dict.

    Read-only against the decision path: the ONLY writes are the four
    artifacts under `out_dir` (a write anywhere else raises).
    """
    eng = DiagnosticEngine(tape, expert_classes, **kwargs)
    report = eng.run()
    trades = [eng._simulate(d, min(bi + eng.lag, len(eng.bars) - 1))
              for d, bi in eng.drafts]
    out = Path(out_dir)
    _guard_no_write(out / 'report.json')
    write_report(out, report, trades)
    return report




COST_SWEEP = (0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10)

# The per-expert exit grid is a CROSS of target x horizon, never a 1-D sweep.
# A 4R target paired with the shipped 8-bar expiry is an incoherent cell: the
# horizon section shows mean favorable excursion only reaches ~4R near 48 bars,
# so a 4R/8-bar cell converts targets into expiries and its loss says nothing
# about whether a 1:4 geometry works. Katz & McCormick's Standard Exit Strategy
# (Encyclopedia of Trading Strategies, 2000, ch. 13) moves the two together
# (1 ATR stop / 4 ATR target / 10 bar limit); the grid has to be able to
# express that shape or the "exit" diagnosis is unfalsifiable.
EXIT_TP_GRID = (1.0, 2.0, 3.0, 4.0, None)      # None -> no take-profit
EXIT_EXPIRY_GRID = (8, 24, 48, 96)


def _build_exit_variants():
    """(name, override) pairs for the target x horizon cross plus two
    structural probes. Deterministic order: TP outer, expiry inner."""
    out = []
    for tp in EXIT_TP_GRID:
        tp_tag = 'notp' if tp is None else f'tp{tp:g}r'
        for ex in EXIT_EXPIRY_GRID:
            # 1e6 is the module's existing "disabled barrier" sentinel.
            out.append((f'{tp_tag}_x{ex}',
                        {'tp': 1e6 if tp is None else tp, 'expiry': ex}))
    # Structural probes: not part of the cross, reported separately because
    # they change the KIND of exit rather than its parameters.
    out.append(('no_sl', {'sl': 1e6}))
    out.append(('trail_1atr', {'geometry_extra': {'trail_stop_atr': 1.0}}))
    return tuple(out)


EXIT_VARIANTS = _build_exit_variants()
# Cells that form the searched cross (excludes the structural probes). Used for
# the multiplicity correction: selecting the max over these is a best-of-N pick
# and its naive p-value is not interpretable without the count.
EXIT_CROSS_NAMES = tuple(
    n for n, _ in EXIT_VARIANTS if n not in ('no_sl', 'trail_1atr'))
RANDOM_NULL_REPS = 40
RANDOM_NULL_SAMPLE = 150
PERM_REPS = 200






def _side_stats(trades):
    nets = [t.net_r for t in trades]
    wins = [r for r in nets if r > 0]
    losses = [r for r in nets if r < 0]
    pf = sum(wins) / abs(sum(losses)) if losses and abs(sum(losses)) > 0 else None
    return {'n': len(trades), 'net_mean': _mean(nets), 'gross_mean':
            _mean([t.gross_r for t in trades]),
            'winrate': len(wins) / len(nets) if nets else None, 'pf': pf,
            'mfe_mean': _mean([t.mfe_r for t in trades]),
            'mae_mean': _mean([t.mae_r for t in trades]),
            'total_net': sum(nets),
            # Kept so the decision table can compute the sample floor for a
            # side claim instead of asserting one from the mean alone.
            'nets': nets}


def _max_dd(nets):
    cum = peak = dd = 0.0
    for r in nets:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def _sign_perm_p(nets, seed, reps=PERM_REPS):
    """One-sided sign-permutation p-value: fraction of random-sign re-labelled
    means that beat the actual mean. Tests whether the expert's directional
    edge is distinguishable from sign noise."""
    if len(nets) < 4:
        return 1.0
    rng = random.Random(seed)
    actual = _mean(nets)
    count = 0
    for _ in range(reps):
        m = _mean([r if rng.random() < 0.5 else -r for r in nets])
        if m >= actual:
            count += 1
    return count / reps


def _bootstrap_ci(nets, seed, reps=500):
    """Percentile bootstrap 95% CI of the mean (block-free; the per-expert
    series is short and the block length guidance lives in the horizon
    section)."""
    if len(nets) < 3:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        means.append(_mean([nets[rng.randrange(len(nets))]
                            for _ in range(len(nets))]))
    return {'p025': _pct(means, 0.025), 'p975': _pct(means, 0.975),
            'se': math.sqrt(sum((m - _mean(means)) ** 2 for m in means)
                            / (len(means) - 1))}


def _entry_regime(eng, entry_idx):
    """Classify the entry bar: vol tercile, bull/bear, trending/ranging."""
    closes = eng.closes
    lo = max(0, entry_idx - 20)
    window = closes[lo:entry_idx]
    rv = None
    drift = None
    if len(window) >= 8:
        rets = [math.log(closes[j] / closes[j - 1])
                for j in range(lo + 1, entry_idx) if closes[j - 1] > 0]
        if len(rets) >= 8:
            m = _mean(rets)
            sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))
            rv = sd
            drift = abs(m * len(rets))
    vol = ('high' if (rv is not None and rv > 0.012)
           else 'low' if (rv is not None and rv < 0.005) else 'mid')
    sma = _mean(window) if window else closes[entry_idx]
    bull = 'bull' if closes[entry_idx] > sma else 'bear'
    trend = 'trending' if (drift is not None and rv is not None
                           and rv > 0 and drift / (rv * math.sqrt(len(window)))
                           > 0.5) else 'ranging'
    return vol, bull, trend


def _regime_concentration(trades, eng):
    """Fraction of net LOSS in the worst regime bucket (vol tercile)."""
    loss_by_regime = {}
    net_by_regime = {}
    for t in trades:
        if t.net_r < 0:
            vol, _b, _tr = _entry_regime(eng, t.entry_idx)
            loss_by_regime[vol] = loss_by_regime.get(vol, 0.0) + abs(t.net_r)
        vol, _b, _tr = _entry_regime(eng, t.entry_idx)
        net_by_regime.setdefault(vol, []).append(t.net_r)
    total_loss = sum(loss_by_regime.values())
    worst = max(loss_by_regime.values()) if loss_by_regime else 0.0
    return (worst / total_loss if total_loss > 0 else 0.0,
            # `nets` is kept so the decision table can size the cell before
            # treating a regime split as evidence (section 8's own floor).
            {k: {'n': len(v), 'net_mean': _mean(v), 'nets': v}
             for k, v in sorted(net_by_regime.items())})


def _time_of_day(trades, eng):
    # Buckets are WALL-CLOCK hours (HOUR_NS), independent of the bar interval —
    # on a 4h tape a bar's `time // interval_ns % 24` would mislabel the bucket.
    out = {}
    for t in trades:
        hour = (eng.times[t.entry_idx] // HOUR_NS) % 24
        bucket = f'{hour // 4 * 4:02d}-{hour // 4 * 4 + 4:02d}'
        out.setdefault(bucket, []).append(t.net_r)
    return {k: {'n': len(v), 'net_mean': _mean(v)} for k, v in sorted(out.items())}


def _window_split(trades, eng):
    cutoff = int(len(eng.bars) * 0.6)
    is_nets = [t.net_r for t in trades if t.entry_idx < cutoff]
    oos_nets = [t.net_r for t in trades if t.entry_idx >= cutoff]
    return {'is_net': _mean(is_nets) if is_nets else None,
            'oos_net': _mean(oos_nets) if oos_nets else None,
            'is_n': len(is_nets), 'oos_n': len(oos_nets),
            'unstable': (len(is_nets) >= 10 and len(oos_nets) >= 10
                         and (is_nets and oos_nets)
                         and _mean(is_nets) > 0.01 and _mean(oos_nets) < -0.01)}


def _expert_random_null(eng, drafts, seed, reps=RANDOM_NULL_REPS,
                        sample=RANDOM_NULL_SAMPLE):
    """Random-entry null for ONE expert: the expert's own drafts re-entered at
    random bars (same geometry, randomized entry time). Answers "is the entry
    timing/selection adding value vs entering at random times?"."""
    n = len(drafts)
    if n < 5:
        return None
    k = min(n, sample)
    rng = random.Random(seed)
    actual = _mean([eng._simulate(d, min(bi + eng.lag, len(eng.bars) - 1)).net_r
                    for d, bi in drafts])
    means = []
    for _ in range(reps):
        tot = 0.0
        for _ in range(k):
            d, _bi = drafts[rng.randrange(n)]
            rnd = rng.randrange(len(eng.bars) - 2)
            tot += eng._simulate(d, rnd).net_r
        means.append(tot / k)
    pct = sum(1 for m in means if m <= actual) / len(means) * 100
    return {'reps': reps, 'sample': k, 'mean': _mean(means),
            'p05': _pct(means, 0.05), 'p95': _pct(means, 0.95),
            'actual_percentile': pct,
            'real_edge': actual > _pct(means, 0.95)}


def _expert_forensics(eng, expert_id, drafts, seed):
    ei = [min(bi + eng.lag, len(eng.bars) - 1) for _d, bi in drafts]
    trades = [eng._simulate(d, e) for d, e in zip([d for d, _ in drafts], ei)]
    st = _side_stats(trades)
    nets = [t.net_r for t in trades]
    longs = [t for t in trades if t.direction == 'LONG']
    shorts = [t for t in trades if t.direction == 'SHORT']
    st['long'] = _side_stats(longs)
    st['short'] = _side_stats(shorts)
    st['max_dd'] = _max_dd(nets)
    st['avg_duration'] = _mean([t.bars_held for t in trades])
    st['zero_cost_edge'] = _mean(
        [eng._simulate(d, e, cost_r=0.0).net_r for d, e in zip([d for d, _ in drafts], ei)])
    cost_curve = {}
    for c in COST_SWEEP:
        cost_curve[str(c)] = _mean(
            [eng._simulate(d, e, cost_r=c).net_r
             for d, e in zip([d for d, _ in drafts], ei)])
    st['cost_curve'] = cost_curve
    # breakeven cost: the lowest cost that flips the edge to negative
    be = None
    for c in COST_SWEEP[1:]:
        if cost_curve[str(c)] < 0 < cost_curve.get(str(COST_SWEEP[COST_SWEEP.index(c) - 1]), 0):
            be = c
            break
    st['breakeven_cost'] = be
    # exit variants — target x horizon cross + structural probes
    variants, variant_nets = {}, {}
    for name, ov in EXIT_VARIANTS:
        vnets = [eng._simulate(d, e, **ov).net_r
                 for d, e in zip([d for d, _ in drafts], ei)]
        variant_nets[name] = vnets
        variants[name] = _mean(vnets)
    st['exit_variants'] = variants
    # The max over the cross is a best-of-N pick. Report it WITH the search
    # size and a Bonferroni-corrected p, never as a bare "best exit" — the
    # naive p of a selected maximum is not a p-value.
    cross = {k: variants[k] for k in EXIT_CROSS_NAMES if k in variants}
    best = max(cross, key=lambda k: cross[k]) if cross else None
    naive_p = _t_pvalue(variant_nets[best]) if best else None
    st['exit_cross'] = {
        'n_cells_searched': len(cross),
        'best_cell': best,
        'best_mean_net_R': cross[best] if best else None,
        'improvement_vs_shipped': (cross[best] - st['net_mean'])
        if best else None,
        'naive_p_value': naive_p,
        'bonferroni_p_value': (min(1.0, naive_p * len(cross))
                               if naive_p is not None else None),
        'selection_note': 'max over a searched grid; naive p is uncorrected',
    }
    st['best_exit'] = best
    st['exit_improvement'] = st['exit_cross']['improvement_vs_shipped'] or 0.0
    # significance
    st['perm_p'] = _sign_perm_p(nets, seed)
    # Sample needed to resolve the edge this expert CLAIMS. Stored (rather
    # than the raw series) because the verdict gate needs it and the report
    # JSON should not carry every trade twice.
    st['min_n_for_edge'] = _min_n_for(nets, abs(st['zero_cost_edge']))
    st['bootstrap_ci'] = _bootstrap_ci(nets, seed)
    st['random_null'] = _expert_random_null(eng, drafts, seed)
    # regime / tod / window
    st['regime_concentration'], st['regime'] = _regime_concentration(trades, eng)
    st['tod'] = _time_of_day(trades, eng)
    st['window_split'] = _window_split(trades, eng)
    # TP robustness: spread of the TP sweep AT THE SHIPPED HORIZON (8 bars).
    # Sweeping TP across horizons too would conflate "sensitive to the target"
    # with "sensitive to how long you hold", which the horizon section already
    # measures; `cross_spread` reports the full-grid range separately.
    tp_at_shipped = [variants[f'{("notp" if tp is None else f"tp{tp:g}r")}_x8']
                     for tp in EXIT_TP_GRID
                     if f'{("notp" if tp is None else f"tp{tp:g}r")}_x8'
                     in variants]
    tp_vals = [st['net_mean']] + tp_at_shipped
    cross_vals = [variants[k] for k in EXIT_CROSS_NAMES if k in variants]
    st['tp_robustness'] = {
        'spread': max(tp_vals) - min(tp_vals),
        'robust': max(tp_vals) - min(tp_vals) < 0.05,
        'cross_spread': (max(cross_vals) - min(cross_vals))
        if cross_vals else None}
    st['verdict'], st['problem'], st['action'] = _decide(st)
    return st


def _decide(st):
    n = st['n']
    zero = st['zero_cost_edge']
    live = st['net_mean']
    p = st['perm_p']
    rn = st.get('random_null') or {}
    real_edge = bool(rn.get('real_edge'))
    if n < 10:
        return ('INVESTIGATE', 'Low sample',
                f'n={n} — below the floor for any per-expert statement')
    if zero <= 0.005:
        return ('HARD_REPAIR', 'No edge (zero-cost ≤ 0.005R)',
                f'frictionless mean {zero:+.4f}R — negative before any cost')
    probs = _observations(st)
    # KEEP needs a strong frictionless edge that clears cost AND is
    # distinguishable from the expert's own random-entry null (the spec's
    # "most critical filter": entry selection adds value). The sign-permutation
    # p is reported but not the sole gate — per-trade variance is so large that
    # no per-expert sign-permutation is significant on this window; requiring
    # it would make the decision table vacuous (0 KEEP).
    # Only SUPPORTED observations may name the verdict's reason; an
    # under-powered one is printed in the forensics but cannot label a row.
    sup = [o for o in probs if o[2]]
    head = (sup[0][0], sup[0][1]) if sup else None
    if zero >= 0.05 and live >= 0.005 and (p < 0.05 or real_edge):
        # KEEP is the strongest thing this table can say, so it carries the
        # strictest sample requirement: enough trades to resolve the edge it
        # is claiming. `n >= 10` alone let an n=10 expert reach KEEP on a
        # random-null percentile while its own observation read "not
        # distinguishable from sign noise" — a row contradicting its own
        # evidence column. Under-powered candidates are not demoted to a
        # failure, they are held at INVESTIGATE: the claim may well be true,
        # there is simply not enough of it yet.
        need = st.get('min_n_for_edge', float('inf'))
        if n < need:
            return ('INVESTIGATE', 'Under-powered',
                    f'{live:+.4f}R live and outside its random-entry null, '
                    f'but n={n} against the {_fmt_n(need)} needed to resolve '
                    f'a {zero:+.4f}R edge')
        structural = _structural_problem(st)
        if structural:
            return 'REPAIR', structural[0], structural[1]
        return ('KEEP', (head[0] if head else 'OK'),
                (head[1] if head else
                 f'clears cost ({live:+.4f}R live) and its own random-entry '
                 f'null'))
    if zero >= 0.02:
        return ('REPAIR', (head[0] if head else 'Cost / exit'),
                (head[1] if head else
                 f'frictionless {zero:+.4f}R does not survive the charge'))
    if zero >= 0.01:
        return ('INVESTIGATE', (head[0] if head else 'Marginal edge'),
                (head[1] if head else f'frictionless {zero:+.4f}R, marginal'))
    if live < -0.01:
        return ('HARD_REPAIR', 'No significant edge',
                f'frictionless {zero:+.4f}R, live {live:+.4f}R')
    return ('INVESTIGATE', 'Marginal edge',
            f'frictionless {zero:+.4f}R, live {live:+.4f}R')


def _min_n_for(nets, effect_r):
    """Sample size needed for a 95% two-sided CI narrower than `effect_r` —
    the same criterion section 8 already applies to segment cells. Returns
    inf when the dispersion is unknown."""
    if not nets or len(nets) < 2 or not effect_r or effect_r <= 0:
        return float('inf')
    m = _mean(nets)
    sd = math.sqrt(sum((x - m) ** 2 for x in nets) / (len(nets) - 1))
    if not (sd == sd):                      # NaN dispersion: unknowable
        return float('inf')
    if sd <= 0:
        # Zero dispersion resolves any effect exactly — inf here would flag a
        # perfectly determined subgroup as under-powered, the opposite of the
        # truth. (Degenerate in real data; reachable in fixtures.)
        return 0.0
    return (1.96 * sd / effect_r) ** 2


def _observations(st):
    """Evidence-gated observations about an expert.

    Every entry is (kind, text, supported). `supported` is False when the
    subgroup that produced the observation is too small to resolve the effect
    it claims — section 8 already refuses to score such cells, and the
    decision table must apply the same floor rather than contradicting it.
    An UNSUPPORTED observation is still printed (suppressing it would hide a
    lead) but may never drive a verdict or imply a change.

    These are observations, not actions. A diagnostic that emits "disable
    long" over a 44-cell search space is prescribing the best corner of that
    search; the change it implies is a preregistered challenger (rule 12),
    which is a decision this tool has no authority to make.
    """
    obs = []
    # --- side asymmetry ---------------------------------------------------- #
    ln, sn = st['long']['net_mean'], st['short']['net_mean']
    l_nets, s_nets = st['long'].get('nets') or [], st['short'].get('nets') or []
    if (ln == ln and sn == sn) and abs(ln - sn) > 0.10 and min(ln, sn) < 0:
        gap = abs(ln - sn)
        need = max(_min_n_for(l_nets, gap), _min_n_for(s_nets, gap))
        have = min(len(l_nets), len(s_nets))
        ok = have >= need
        weak = 'short' if sn < ln else 'long'
        obs.append((
            f'{weak.capitalize()} side',
            f'{weak} side {min(ln, sn):+.4f}R vs {max(ln, sn):+.4f}R '
            f'(gap {gap:.4f}R); n={have}/side, needs {_fmt_n(need)} to '
            f'resolve a gap this size',
            ok))
    # --- cost -------------------------------------------------------------- #
    if st['net_mean'] < 0 and st['zero_cost_edge'] > 0.01:
        obs.append((
            'Cost',
            f'zero-cost {st["zero_cost_edge"]:+.4f}R turns negative after the '
            f'flat charge (live {st["net_mean"]:+.4f}R)',
            True))
    # --- exit -------------------------------------------------------------- #
    xc = st.get('exit_cross') or {}
    if st['exit_improvement'] > 0.03 and xc.get('best_cell'):
        bp = xc.get('bonferroni_p_value')
        ok = bp is not None and bp < 0.05
        obs.append((
            'Exit',
            f'best grid cell {xc["best_cell"]} is '
            f'{st["exit_improvement"]:+.4f}R above shipped, selected from '
            f'{xc.get("n_cells_searched", "?")} cells '
            f'(Bonferroni p={_fmt_p(bp)})',
            ok))
    # --- regime ------------------------------------------------------------ #
    if st['regime_concentration'] > 0.6:
        reg = st.get('regime') or {}
        worst = min(reg, key=lambda k: (reg[k].get('net_mean')
                                        if reg[k].get('net_mean') is not None
                                        else 0.0)) if reg else None
        cell = reg.get(worst) or {}
        cn = cell.get('n', 0)
        eff = abs(cell.get('net_mean') or 0.0)
        need = _min_n_for(cell.get('nets') or [], eff)
        ok = cn >= need
        obs.append((
            'Regime',
            f'loss concentrates in regime "{worst}" '
            f'({cell.get("net_mean", float("nan")):+.4f}R, n={cn}; needs '
            f'{_fmt_n(need)})',
            ok))
    # --- significance ------------------------------------------------------ #
    if st['perm_p'] >= 0.05:
        obs.append((
            'No significance',
            f'sign-permutation p={st["perm_p"]:.3f} — not distinguishable '
            f'from sign noise on this window',
            True))
    # Supported observations first; within each group, insertion order.
    return sorted(obs, key=lambda o: not o[2])


def _fmt_n(x):
    if x is None or x != x or x == float('inf'):
        return 'n/a'
    return f'{x:.0f}'


def _fmt_p(p):
    return 'n/a' if p is None else f'{p:.3f}'


def _structural_problem(st):
    """A structural (strategy-level) observation strong enough to hold a
    profitable expert at REPAIR. Only SUPPORTED observations qualify — an
    under-powered subgroup must not move a verdict. Cost is an execution
    concern, not structural."""
    for kind, text, ok in _observations(st):
        if not ok:
            continue
        if kind in ('Short side', 'Long side'):
            return (kind, text)
        if kind == 'Exit' and st['exit_improvement'] > 0.10:
            return (kind, text)
        if kind == 'Regime':
            return (kind, text)
    return None


def run_forensics(eng, seed=7) -> dict:
    """Per-expert forensics over the engine's entry set. Returns
    {'experts': {...}, 'decision_table': [...], 'portfolio': {...}}."""
    by_expert = {}
    for d, bi in eng.drafts:
        by_expert.setdefault(d.expert_id, []).append((d, bi))
    experts = {}
    for i, (expert_id, drafts) in enumerate(sorted(by_expert.items())):
        experts[expert_id] = _expert_forensics(
            eng, expert_id, drafts, seed + i * 101)

    # decision table (sorted by zero-cost edge desc)
    rows = []
    for eid, st in sorted(experts.items(),
                          key=lambda kv: kv[1]['zero_cost_edge'], reverse=True):
        rows.append({'expert': eid, 'verdict': st['verdict'], 'n': st['n'],
                     'zero_cost_edge': st['zero_cost_edge'],
                     'net_edge': st['net_mean'], 'pf': st['pf'],
                     'winrate': st['winrate'], 'max_dd': st['max_dd'],
                     'long_net': st['long']['net_mean'],
                     'short_net': st['short']['net_mean'],
                     'problem': st['problem'],
                     # `observation` is the current name; `action` is kept as
                     # an alias only so an older reader does not KeyError on a
                     # new report. Both carry the same non-prescriptive text.
                     'observation': st['action'], 'action': st['action'],
                     'min_n_for_edge': st.get('min_n_for_edge')})

    # portfolio conclusion
    counts = Counter(r['verdict'] for r in rows)
    strong = [r for r in rows if r['n'] >= 30]
    strongest = strong[0]['expert'] if strong else None
    weakest = rows[-1]['expert'] if rows else None
    dominant = Counter(r['problem'] for r in rows if r['problem'] != 'OK') \
        .most_common(1)
    def _finite_mean(xs):
        vals = [x for x in xs if x == x and x is not None]
        return _mean(vals) if vals else None
    agg_long = _finite_mean([st['long']['net_mean'] for st in experts.values()])
    agg_short = _finite_mean([st['short']['net_mean'] for st in experts.values()])
    # Exit vs entry. Two numbers, and the difference between them is the point:
    #   `best_exit`  — per-expert max over the grid, then averaged. Every term
    #                  is a selected maximum, so this is an UPPER BOUND
    #                  inflated by selection, not an achievable figure.
    #   `fixed_exit` — the single best grid cell chosen ONCE for the whole
    #                  portfolio, then applied to every expert. One choice
    #                  instead of `n_experts` choices, so it is what a single
    #                  preregistered geometry change could actually deliver.
    agg_best_exit = _finite_mean([
        max((st['exit_variants'][k] for k in EXIT_CROSS_NAMES
             if k in st['exit_variants']), default=float('nan'))
        for st in experts.values()])
    agg_live = _finite_mean([st['net_mean'] for st in experts.values()])
    cell_means = {}
    for name in EXIT_CROSS_NAMES:
        vals = [st['exit_variants'][name] for st in experts.values()
                if name in st['exit_variants']]
        if vals:
            cell_means[name] = _mean(vals)
    fixed_cell = max(cell_means, key=lambda k: cell_means[k]) \
        if cell_means else None
    portfolio = {
        'experts': len(experts),
        'counts': dict(counts),
        'strongest_edge': strongest,
        'weakest_edge': weakest,
        'dominant_failure': dominant[0][0] if dominant else None,
        'long_vs_short': {'long': agg_long, 'short': agg_short},
        'exit_vs_entry': {
            'live': agg_live,
            'best_exit': agg_best_exit,
            'improvement': (agg_best_exit - agg_live)
            if (agg_best_exit is not None and agg_live is not None) else None,
            'best_exit_is_selection_inflated': True,
            'n_cells_searched': len(cell_means),
            'fixed_cell': fixed_cell,
            'fixed_cell_mean': cell_means.get(fixed_cell)
            if fixed_cell else None,
            'fixed_cell_improvement': (cell_means[fixed_cell] - agg_live)
            if (fixed_cell and agg_live is not None) else None,
            'cell_means': cell_means},
        'recommendation': _portfolio_recommendation(counts, experts, rows),
    }
    return {'experts': experts, 'decision_table': rows, 'portfolio': portfolio}


def _portfolio_recommendation(counts, experts, rows):
    n_repair = counts.get('REPAIR', 0)
    n_keep = counts.get('KEEP', 0)
    # recommend the highest-impact, lowest-effort next experiment
    repair_exits = [r['expert'] for r in rows
                    if r['verdict'] == 'REPAIR' and r['problem'] == 'Exit']
    repair_costs = [r['expert'] for r in rows
                    if r['verdict'] == 'REPAIR' and r['problem'] == 'Cost']
    short_probs = [r['expert'] for r in rows
                   if 'Short' in (r['problem'] or '')]
    parts = []
    if n_keep:
        parts.append(f'KEEP {n_keep} experts; protect them from '
                     'cross-expert contention (the neutral tie-break, D-066)')
    if repair_costs:
        parts.append(f'cost kills {len(repair_costs)} experts: the next '
                     'experiment is the O-025 venue-cost receipt (R-unit '
                     'widening, not cost-cutting)')
    if repair_exits:
        parts.append(f'exit clips {len(repair_exits)} experts: a preregistered '
                     'TP/trail challenger (O-027) on the frozen OOS')
    if short_probs:
        parts.append(f'{len(short_probs)} experts are dragged by their short '
                     'side: a disable-short variant is a challenger')
    if not parts:
        parts.append('no expert survives frictionless — the entry signal '
                     'itself is the next experiment (per-expert variant '
                     'preconditions, O-024)')
    return '; '.join(parts)



# --------------------------------------------------------------------------- #
# SVG primitives
# --------------------------------------------------------------------------- #

_PALETTE = {
    'positive': '#1a9850', 'negative': '#d73027', 'neutral': '#7f8c8d',
    'accent': '#2c6fbb', 'bg': '#f7f9fb', 'grid': '#dfe6ec',
    'ink': '#1f2937', 'muted': '#6b7280',
}

_VERDICT_STYLE = {
    'KEEP': 'background:#1a9850;color:#fff', 'REPAIR': 'background:#f0ad4e;color:#fff',
    'INVESTIGATE': 'background:#f39c12;color:#fff',
    'HARD_REPAIR': 'background:#d73027;color:#fff',
}


def _verdict_badge(v):
    st = _VERDICT_STYLE.get(v, 'background:#7f8c8d;color:#fff')
    return f'<span class="vbadge" style="{st}">{html.escape(v)}</span>'


def _fmt(v, nd=4):
    if v is None:
        return '—'
    try:
        return f'{v:+.{nd}f}'
    except (TypeError, ValueError):
        return str(v)


def _svg_line_chart(series, *, width=680, height=260, y_label='', mark=None):
    """Inline SVG line chart. `series`: list of (x_label, y_value).
    `mark`: optional (x_label, y_value) to draw a dashed marker line."""
    if not series:
        return '<div class="chart-empty">no data</div>'
    pad_l, pad_r, pad_t, pad_b = 56, 18, 18, 40
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    vals = [v for _, v in series]
    vmin, vmax = min(vals), max(vals)
    if vmax - vmin < 1e-12:
        vmax = vmin + 1.0
    lo, hi = vmin - 0.08 * (vmax - vmin), vmax + 0.08 * (vmax - vmin)

    def X(i):
        if len(series) == 1:
            return pad_l + iw / 2
        return pad_l + i / (len(series) - 1) * iw

    def Y(v):
        return pad_t + ih - (v - lo) / (hi - lo) * ih

    # horizontal grid + y labels (5 ticks)
    grid = ''
    for k in range(6):
        frac = k / 5
        y = pad_t + ih - frac * ih
        v = lo + frac * (hi - lo)
        grid += (f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" '
                 f'y2="{y:.1f}" stroke="{_PALETTE["grid"]}" stroke-width="1"/>'
                 f'<text x="{pad_l - 8}" y="{y + 3:.1f}" text-anchor="end" '
                 f'class="axis">{v:+.3f}</text>')
    # zero line
    if lo <= 0 <= hi:
        zy = Y(0)
        grid += (f'<line x1="{pad_l}" y1="{zy:.1f}" x2="{pad_l + iw}" '
                 f'y2="{zy:.1f}" stroke="{_PALETTE["neutral"]}" '
                 'stroke-width="1" stroke-dasharray="4 3"/>')
    # x labels
    xt = ''
    for i, (label, _) in enumerate(series):
        xt += (f'<text x="{X(i):.1f}" y="{height - 12}" text-anchor="middle" '
               f'class="axis">{html.escape(str(label))}</text>')
    # polyline
    pts = ' '.join(f'{X(i):.1f},{Y(v):.1f}' for i, (_, v) in enumerate(series))
    line = (f'<polyline points="{pts}" fill="none" '
            f'stroke="{_PALETTE["accent"]}" stroke-width="2.5"/>')
    # point dots + value labels
    dots = ''
    for i, (_, v) in enumerate(series):
        dots += (f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.5" '
                 f'fill="{_PALETTE["accent"]}"/>'
                 f'<text x="{X(i):.1f}" y="{Y(v) - 8:.1f}" text-anchor="middle" '
                 f'class="datapoint">{_fmt(v)}</text>')
    # dashed marker for `mark`
    marker = ''
    if mark is not None and len(series) > 1:
        ml = mark[0]
        for i, (label, _) in enumerate(series):
            if str(label) == str(ml):
                mx = X(i)
                marker = (f'<line x1="{mx:.1f}" y1="{pad_t}" x2="{mx:.1f}" '
                          f'y2="{pad_t + ih}" stroke="{_PALETTE["negative"]}" '
                          'stroke-width="1.5" stroke-dasharray="6 4"/>'
                          f'<text x="{mx:.1f}" y="{pad_t - 4}" text-anchor="middle" '
                          f'class="marker">{html.escape(str(ml))}</text>')
                break
    ylab = (f'<text x="14" y="{pad_t + ih / 2}" text-anchor="middle" '
            f'transform="rotate(-90 14 {pad_t + ih / 2})" '
            f'class="axis">{html.escape(y_label)}</text>' if y_label else '')
    return (f'<svg viewBox="0 0 {width} {height}" class="chart" '
            f'role="img">{grid}{marker}{ylab}{xt}{line}{dots}</svg>')


def _svg_bar_chart(items, *, width=680, height=260, y_label='',
                   color_by_sign=True):
    """Inline SVG bar chart. `items`: list of (label, value). Bars are colored
    by sign when `color_by_sign` (green positive / red negative)."""
    if not items:
        return '<div class="chart-empty">no data</div>'
    pad_l, pad_r, pad_t, pad_b = 56, 18, 18, 44
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    vals = [v for _, v in items]
    vmin, vmax = min(vals), max(vals)
    if vmax - vmin < 1e-12:
        vmax = vmin + 1.0
    lo, hi = min(0.0, vmin - 0.06 * (vmax - vmin)), \
        max(0.0, vmax + 0.06 * (vmax - vmin))
    n = len(items)
    slot = iw / n
    bw = slot * 0.62
    zero_y = pad_t + ih - (0 - lo) / (hi - lo) * ih

    def Y(v):
        return pad_t + ih - (v - lo) / (hi - lo) * ih

    grid = ''
    for k in range(5):
        frac = k / 4
        y = pad_t + ih - frac * ih
        v = lo + frac * (hi - lo)
        grid += (f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" '
                 f'y2="{y:.1f}" stroke="{_PALETTE["grid"]}" stroke-width="1"/>'
                 f'<text x="{pad_l - 8}" y="{y + 3:.1f}" text-anchor="end" '
                 f'class="axis">{v:+.3f}</text>')
    bars = ''
    for i, (label, v) in enumerate(items):
        x = pad_l + i * slot + (slot - bw) / 2
        y0, y1 = zero_y, Y(v)
        top = min(y0, y1)
        hgt = abs(y1 - y0)
        color = _PALETTE['positive'] if v >= 0 else _PALETTE['negative'] \
            if color_by_sign else _PALETTE['accent']
        bars += (f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" '
                 f'height="{hgt:.1f}" fill="{color}" rx="2"/>'
                 f'<text x="{x + bw / 2:.1f}" y="{top - 4:.1f}" '
                 f'text-anchor="middle" class="datapoint">{_fmt(v)}</text>'
                 f'<text x="{x + bw / 2:.1f}" y="{height - 12}" '
                 f'text-anchor="middle" class="axis">'
                 f'{html.escape(str(label))}</text>')
    ylab = (f'<text x="14" y="{pad_t + ih / 2}" text-anchor="middle" '
            f'transform="rotate(-90 14 {pad_t + ih / 2})" '
            f'class="axis">{html.escape(y_label)}</text>' if y_label else '')
    return (f'<svg viewBox="0 0 {width} {height}" class="chart" '
            f'role="img">{grid}{ylab}{bars}</svg>')


def _svg_histogram(values, *, width=680, height=240, bins=24, x_label='',
                   color='#2c6fbb'):
    """Inline SVG histogram over `values`."""
    values = [v for v in values if v is not None and v == v]
    if len(values) < 2:
        return '<div class="chart-empty">insufficient data</div>'
    pad_l, pad_r, pad_t, pad_b = 56, 18, 18, 44
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        hi = lo + 1.0
    counts = [0] * bins
    for v in values:
        k = int((v - lo) / (hi - lo) * bins)
        counts[min(k, bins - 1)] += 1
    cmax = max(counts)
    slot = iw / bins
    bw = slot * 0.9
    grid = ''
    for k in range(4):
        frac = k / 3
        y = pad_t + ih - frac * ih
        grid += (f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" '
                 f'y2="{y:.1f}" stroke="{_PALETTE["grid"]}" stroke-width="1"/>'
                 f'<text x="{pad_l - 8}" y="{y + 3:.1f}" text-anchor="end" '
                 f'class="axis">{int(cmax * frac)}</text>')
    bars = ''
    for k, c in enumerate(counts):
        x = pad_l + k * slot + (slot - bw) / 2
        hgt = c / cmax * ih
        bars += (f'<rect x="{x:.1f}" y="{pad_t + ih - hgt:.1f}" '
                 f'width="{bw:.1f}" height="{hgt:.1f}" fill="{color}" '
                 'opacity="0.85" rx="1"/>')
    # x labels: first, middle, last
    for k, frac in ((0, 0), (bins // 2, 0.5), (bins - 1, 1.0)):
        v = lo + frac * (hi - lo)
        x = pad_l + k * slot + slot / 2
        bars += (f'<text x="{x:.1f}" y="{height - 12}" text-anchor="middle" '
                 f'class="axis">{v:+.3f}</text>')
    xlab = (f'<text x="{pad_l + iw / 2}" y="{height - 2}" text-anchor="middle" '
            f'class="axis">{html.escape(x_label)}</text>' if x_label else '')
    return (f'<svg viewBox="0 0 {width} {height}" class="chart" '
            f'role="img">{grid}{xlab}{bars}</svg>')


def _svg_null_band(actual, p05, p95, median, width=680, height=120):
    """Horizontal band chart: the actual vs the random-entry null's central
    90% — the MECHANICAL_FLOOR visual."""
    pad_l, pad_r = 56, 24
    iw = width - pad_l - pad_r
    vals = [actual, p05, p95, median]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        hi = lo + 1.0
    span = hi - lo
    lo -= 0.1 * span
    hi += 0.1 * span
    y = 46

    def X(v):
        return pad_l + (v - lo) / (hi - lo) * iw

    x05, x95, xm, xa = X(p05), X(p95), X(median), X(actual)
    band = (f'<rect x="{x05:.1f}" y="{y - 8}" width="{x95 - x05:.1f}" '
            f'height="16" fill="{_PALETTE["neutral"]}" opacity="0.35" rx="3"/>')
    med = (f'<line x1="{xm:.1f}" y1="{y - 12}" x2="{xm:.1f}" y2="{y + 12}" '
           f'stroke="{_PALETTE["neutral"]}" stroke-width="2"/>'
           f'<text x="{xm:.1f}" y="{y + 30}" text-anchor="middle" '
           f'class="axis">null median</text>')
    act = (f'<line x1="{xa:.1f}" y1="{y - 20}" x2="{xa:.1f}" y2="{y + 20}" '
           f'stroke="{_PALETTE["accent"]}" stroke-width="3"/>'
           f'<text x="{xa:.1f}" y="{y - 26}" text-anchor="middle" '
           f'class="marker">actual {_fmt(actual)}</text>')
    labels = (f'<text x="{x05:.1f}" y="{y + 30}" text-anchor="middle" '
              f'class="axis">p05 {_fmt(p05)}</text>'
              f'<text x="{x95:.1f}" y="{y + 30}" text-anchor="middle" '
              f'class="axis">p95 {_fmt(p95)}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">'
            f'{band}{med}{act}{labels}</svg>')


# --------------------------------------------------------------------------- #
# HTML sections
# --------------------------------------------------------------------------- #

_CSS = """
:root{--ink:#1f2937;--muted:#6b7280;--accent:#2c6fbb;--pos:#1a9850;
--neg:#d73027;--bg:#f7f9fb;--card:#fff;--border:#dfe6ec}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,
Helvetica,Arial,sans-serif;color:var(--ink);margin:0;background:var(--bg);
line-height:1.5}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
header{background:linear-gradient(135deg,#1f3a5f,#2c6fbb);color:#fff;
border-radius:10px;padding:26px 30px;margin-bottom:24px}
header h1{margin:0 0 4px;font-size:22px}
header .sub{opacity:.85;font-size:13px;margin-bottom:14px}
.verdict{display:inline-block;font-size:20px;font-weight:700;
padding:8px 18px;border-radius:6px;background:rgba(255,255,255,.16);
border:1px solid rgba(255,255,255,.35)}
.verdict-ok{background:rgba(26,152,80,.9)} .verdict-bad{background:rgba(215,48,39,.85)}
.authority{display:inline-block;margin-left:10px;font-size:12px;
font-weight:600;letter-spacing:.06em;background:rgba(0,0,0,.25);
padding:5px 12px;border-radius:4px}
.meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-size:12px;
opacity:.9}
.meta b{font-weight:600}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;
padding:20px 24px;margin-bottom:20px}
.card h2{margin:0 0 4px;font-size:17px;color:#16283f}
.card .sec{font-size:12px;color:var(--muted);margin-bottom:14px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
th,td{padding:6px 10px;text-align:right;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;
letter-spacing:.03em}
td:first-child,th:first-child{text-align:left}
tr:last-child td{border-bottom:none}
.pos{color:var(--pos);font-weight:600}.neg{color:var(--neg);font-weight:600}
.chart{width:100%;height:auto;display:block;margin-top:8px}
.chart-empty{color:var(--muted);font-style:italic;padding:16px;
text-align:center;border:1px dashed var(--border);border-radius:6px}
.axis{font-size:10px;fill:var(--muted)}
.datapoint{font-size:9.5px;fill:var(--ink)}
.marker{font-size:11px;font-weight:700;fill:var(--neg)}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:12px;margin-top:14px}
.kpi div{background:var(--bg);border:1px solid var(--border);border-radius:6px;
padding:10px 14px}
.kpi .k{font-size:11px;color:var(--muted);text-transform:uppercase;
letter-spacing:.03em}
.kpi .v{font-size:20px;font-weight:700;margin-top:2px}
.kpi .d{font-size:11px;color:var(--muted)}
.note{background:#fff8e6;border:1px solid #f0d98c;border-radius:6px;
padding:10px 14px;font-size:12.5px;margin-top:10px}
.invalid{background:#fdecea;border-color:#f3b4ad;border-radius:6px;
padding:12px 16px;font-size:13px;margin-bottom:20px}
.vbadge{display:inline-block;padding:3px 10px;border-radius:4px;
font-size:11px;font-weight:700;letter-spacing:.04em}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:var(--muted);
margin:10px 0 4px}
.legend span{display:inline-flex;align-items:center;gap:5px}
.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
details{background:var(--bg);border:1px solid var(--border);border-radius:6px;
padding:10px 14px;margin-top:8px}
details summary{cursor:pointer;font-weight:600;font-size:13px;
display:flex;gap:10px;align-items:center}
details summary .verdict-detail{margin-left:auto;font-weight:700}
details[open]{background:#fff}
.fx-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px}
.fx-grid h4{margin:0 0 4px;font-size:12px;color:var(--muted);
text-transform:uppercase;letter-spacing:.03em}
.fx-grid table{margin-top:2px}
.portfolio-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
gap:12px;margin-top:12px}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:30px}
footer b{letter-spacing:.05em}
"""


def _table(headers, rows, number_cols=()):
    h = ''.join(f'<th>{html.escape(str(x))}</th>' for x in headers)
    body = ''
    for row in rows:
        tds = []
        for i, cell in enumerate(row):
            if i in number_cols and isinstance(cell, (int, float)):
                cls = 'pos' if cell > 0 else ('neg' if cell < 0 else '')
                tds.append(f'<td class="{cls}">{_fmt(cell)}</td>')
            else:
                tds.append(f'<td>{html.escape(str(cell))}</td>')
        body += '<tr>' + ''.join(tds) + '</tr>'
    return f'<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


def _kpi(items):
    cells = ''.join(
        f'<div><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{html.escape(str(v))}</div>'
        f'<div class="d">{html.escape(str(d))}</div></div>'
        for k, v, d in items)
    return f'<div class="kpi">{cells}</div>'


def _section(num, title, body, sec_note=''):
    return (f'<div class="card"><h2>{num} — {html.escape(title)}</h2>'
            f'<div class="sec">{html.escape(sec_note)}</div>{body}</div>')


# --------------------------------------------------------------------------- #
# Forensics (per-expert decision table + drill-down + portfolio)
# --------------------------------------------------------------------------- #

def _render_decision_table(fx):
    def cell(v, col=None):
        cls = f' class="{col}"' if col else ''
        return f'<td{cls}>{v}</td>'
    rows = ''
    for r in fx['decision_table']:
        rows += ('<tr>'
                 f'<td><b>{html.escape(r["expert"])}</b></td>'
                 f'<td>{_verdict_badge(r["verdict"])}</td>'
                 f'<td>{r["n"]}</td>'
                 + cell(_fmt(r['zero_cost_edge']),
                        'pos' if r['zero_cost_edge'] > 0 else 'neg')
                 + cell(_fmt(r['net_edge']),
                        'pos' if r['net_edge'] > 0 else 'neg')
                 + cell(_fmt(r['pf']) if r['pf'] is not None else '—')
                 + cell(_fmt(r['winrate'], 3) if r['winrate'] is not None
                        else '—')
                 + cell(_fmt(r['max_dd']))
                 + cell(_fmt(r['long_net']),
                        'pos' if r['long_net'] > 0 else 'neg')
                 + cell(_fmt(r['short_net']),
                        'pos' if r['short_net'] > 0 else 'neg')
                 + cell(html.escape(r['problem']))
                 + cell(html.escape(r['action']))
                 + '</tr>')
    return ('<div class="legend">'
            '<span><i style="background:#1a9850"></i>KEEP</span>'
            '<span><i style="background:#f0ad4e"></i>REPAIR</span>'
            '<span><i style="background:#f39c12"></i>INVESTIGATE</span>'
            '<span><i style="background:#d73027"></i>HARD_REPAIR</span></div>'
            '<table><thead><tr><th>expert</th><th>verdict</th><th>N</th>'
            '<th>zero-cost edge</th><th>live edge</th><th>PF</th>'
            '<th>winrate</th><th>max DD</th><th>long</th><th>short</th>'
            '<th>main problem</th><th>observation</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            '<div class="sec">the last column is an OBSERVATION, not an '
            'action. This table does not prescribe: naming the best corner of '
            'a searched grid (a side, a regime, an exit cell) IS the selection '
            'that inflates it. Any change it suggests is a new preregistered '
            'challenger (rule 12). Under-powered observations are printed in '
            'the per-expert forensics below, flagged, and never used to label '
            'a row. Ranked by zero-cost edge.</div>')


def _render_expert_details(fx):
    out = []
    for r in fx['decision_table']:
        st = fx['experts'][r['expert']]
        cv = st['cost_curve']
        cost_rows = [['0.00', cv['0.0']]] + \
            [[k, v] for k, v in cv.items() if k != '0.0']
        ev = st['exit_variants']
        exit_rows = [[k, v] for k, v in sorted(ev.items(),
                                               key=lambda kv: kv[1], reverse=True)]
        details = ('<div class="fx-grid">'
                   '<div><h4>Cost sensitivity</h4>'
                   + _table(['cost R', 'net R'], cost_rows, number_cols=(1,))
                   + '</div>'
                   '<div><h4>Exit variants</h4>'
                   + _table(['variant', 'net R'], exit_rows, number_cols=(1,))
                   + '</div>'
                   '<div><h4>Long / Short</h4>'
                   + _table(['side', 'n', 'net R', 'winrate'],
                            [['LONG', st['long']['n'], st['long']['net_mean'],
                              st['long']['winrate']],
                             ['SHORT', st['short']['n'], st['short']['net_mean'],
                              st['short']['winrate']]], number_cols=(1, 2, 3))
                   + '</div>'
                   '<div><h4>Regime</h4>'
                   + _table(['regime', 'n', 'net R'],
                            [[k, v['n'], v['net_mean']]
                             for k, v in sorted(st['regime'].items())],
                            number_cols=(1, 2))
                   + '</div>'
                   '<div><h4>Time of day</h4>'
                   + _table(['bucket', 'n', 'net R'],
                            [[k, v['n'], v['net_mean']]
                             for k, v in sorted(st['tod'].items())],
                            number_cols=(1, 2))
                   + '</div>'
                   '<div><h4>Window split (first 60% / last 40%)</h4>'
                   + _table(['window', 'n', 'net R'],
                            [['IS (first 60%)', st['window_split']['is_n'],
                              st['window_split']['is_net']],
                             ['OOS (last 40%)', st['window_split']['oos_n'],
                              st['window_split']['oos_net']]],
                            number_cols=(1, 2))
                   + ('<div class="note">unstable across the window — '
                      'first-half edge does not survive the second half</div>'
                      if st['window_split'].get('unstable') else '')
                   + '</div>'
                   '<div><h4>Significance & sample</h4>'
                   + _table(['stat', 'value'],
                            [['N', st['n']], ['permutation p', st['perm_p']],
                             ['bootstrap 95% CI',
                              (f"[{st['bootstrap_ci']['p025']:.4f}, "
                               f"{st['bootstrap_ci']['p975']:.4f}]")
                              if st['bootstrap_ci'] else '—'],
                             ['breakeven cost', st['breakeven_cost']],
                             ['TP robustness spread', st['tp_robustness']['spread']],
                             ['max drawdown (R)', st['max_dd']],
                             ['avg duration (bars)', st['avg_duration']]],
                            number_cols=(1,))
                   + '</div>'
                   '<div><h4>Random-entry null (this expert)</h4>'
                   + (f"<div class='sec'>actual percentile "
                      f"<b>{st['random_null']['actual_percentile']:.0f}%</b> of "
                      f"the null [{st['random_null']['p05']:.4f}, "
                      f"{st['random_null']['p95']:.4f}] — "
                      f"{'REAL EDGE' if st['random_null']['real_edge'] else 'INSIDE null'}"
                      "</div>"
                      if st['random_null'] else '<div class="sec">insufficient</div>')
                   + '</div>'
                   '</div>')
        verdict = st['verdict']
        out.append(
            f'<details><summary><span>{html.escape(r["expert"])}</span>'
            f'<span class="problem">{html.escape(r["problem"])}</span>'
            f'<span class="verdict-detail">{_verdict_badge(verdict)}</span>'
            f'</summary>{details}</details>')
    return '\n'.join(out)


def _render_portfolio(pf):
    counts = pf['counts']
    cells = ''.join(
        f'<div><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{v}</div></div>'
        for k, v in sorted(counts.items()))
    ev = pf['exit_vs_entry']
    def _r(v):
        return f'{v:+.4f}' if v is not None else '—'
    rows = [['experts analysed', pf['experts']],
            ['strongest edge (zero-cost)', pf['strongest_edge']],
            ['weakest edge', pf['weakest_edge']],
            ['dominant failure', pf['dominant_failure']],
            ['aggregate long / short',
             f'{_r(pf["long_vs_short"]["long"])} / {_r(pf["long_vs_short"]["short"])}'],
            ['live → best-exit (SELECTION-INFLATED upper bound)',
             f'{_r(ev["live"])} → {_r(ev["best_exit"])} '
             f'({_r(ev["improvement"])}) over '
             f'{ev.get("n_cells_searched", "?")} cells/expert'],
            ['live → single fixed exit cell (one choice, all experts)',
             f'{_r(ev["live"])} → {_r(ev.get("fixed_cell_mean"))} '
             f'({_r(ev.get("fixed_cell_improvement"))}) '
             f'at {ev.get("fixed_cell") or "—"}']]
    return (_section('L', 'Portfolio-level conclusion',
                     '<div class="portfolio-kpis">' + cells + '</div>'
                     + _table(['metric', 'value'], rows, number_cols=(1,))
                     + f'<div class="note"><b>Recommended next experiment:</b> '
                       f'{html.escape(pf["recommendation"])}</div>',
                     'one diagnostic suggestion per expert; every change is a '
                     'preregistered challenger (rule 12)'))


def _render_forensics(report):
    fx = report.get('forensics')
    if not fx:
        return ''
    table = _section('S', 'Strategy decision table (KEEP / REPAIR / '
                     'HARD_REPAIR / INVESTIGATE)',
                     _render_decision_table(fx),
                     'which strategy to keep, soft-repair or hard-repair — the '
                     'actionable layer of this report. No expert is ever '
                     '"killed": HARD_REPAIR means it is broken and needs a '
                     'fundamental rebuild.')
    details = _section('E', 'Per-expert forensics',
                       _render_expert_details(fx),
                       'expand each expert for the full cost/exit/regime/TOD/'
                       'window/significance drill-down')
    return table + details + _render_portfolio(fx['portfolio'])


def _render_coverage(report):
    cov = report.get('coverage')
    if not cov:
        return ''
    zero = cov['zero_draft_experts']
    unreg = cov['unregistered_variants']
    body = _table(
        ['metric', 'value'],
        [['registered experts evaluated', cov['registered_experts']],
         ['of those, produced >=1 setup', cov['evaluated_experts']],
         ['produced ZERO setups', len(zero)],
         ['Expert subclasses defined in v8.experts',
          cov['defined_variant_classes']],
         ['defined but NOT registered (never run)', len(unreg)]],
        number_cols=(1,))
    if zero:
        body += ('<div class="note"><b>Zero-setup experts '
                 f'({len(zero)}):</b> ' + html.escape(', '.join(zero))
                 + ' — these fired no setup on this window, so they carry no '
                 'row in the decision table. A threshold that never triggers '
                 'is a finding, not an absence.</div>')
    if unreg:
        rows = [[u['module'], u['class'], u['expert_id'] or '—',
                 u['variant_id'] or '—'] for u in unreg]
        body += ('<h3 style="margin:14px 0 2px">Defined but unregistered '
                 'variants</h3>'
                 '<div class="sec">these classes exist in the package and are '
                 'NOT in ALL_EXPERT_CLASSES, so nothing below measures them. '
                 'Where the registered variant is directionally restricted, a '
                 'row labelled with the family name is a statement about ONE '
                 'variant — a SHORT n=0 there is the variant&#8217;s '
                 'definition, not a broken direction.</div>'
                 + _table(['module', 'class', 'expert_id', 'variant'], rows))
    return _section('C', 'Coverage — what was evaluated vs what exists', body,
                    'zero-setup experts and unregistered variants, so the '
                    'decision table is read as coverage of the REGISTERED set')


def _render_state_audit(report):
    audit = report.get('state_audit')
    if not audit:
        return ''
    base = report['manifest']['base_interval']
    multi = report['manifest']['multi_interval_experts']
    verified = report['manifest']['per_expert_state_projection']
    rows = []
    for eid, a in sorted(audit.items()):
        rows.append([eid, ', '.join(a['intervals']), ', '.join(a['requires']),
                     str(a['depth']), a['view_feature_count'],
                     a['canonical_feature_count'],
                     'OK' if a['view_groups_verified'] else 'FAIL'])
    note = (f'the tape base interval is <b>{base}</b>. All experts currently '
            f'declare the base interval only '
            f'({"none" if not multi else ", ".join(multi)} declare '
            'multi-interval). Every expert evaluated a <b>projected '
            'per-expert MarketState</b> (D-054): the canonical state filtered '
            'to its declared intervals + feature groups, so an expert never '
            'sees another expert\'s undeclared features. Verification: '
            f'<b>{"PASSED" if verified else "FAILED"}</b> — every view '
            'contained only the declared groups\' features.')
    return _section('D', 'Per-expert MarketState (D-054)',
                    f'<div class="note">{note}</div>'
                    + _table(['expert', 'intervals', 'requires (groups)',
                              'depth', 'view features', 'canonical features',
                              'projection'],
                             rows, number_cols=(4, 5)),
                    'each expert has its OWN MarketState view; the economics '
                    'below are computed from those per-expert views')


# --------------------------------------------------------------------------- #
# Main renderer
# --------------------------------------------------------------------------- #

def render_html(report: dict, trades, fragment: bool = False) -> str:
    """One self-contained HTML report string from the engine's report dict and
    its actual-config trade list.

    ``fragment=True`` returns the body WITHOUT the ``<html>/<head>/<style>``
    wrapper, so a caller can embed a cell report inside a parent document that
    already carries ``_CSS``. ``fragment=False`` (default) is the byte-identical
    legacy self-contained report."""

    s = report['sections']
    verdict = report['verdict']
    vbad = verdict in ('SIMULATOR_INVALID',)
    vcls = 'verdict-bad' if vbad else 'verdict-ok' \
        if verdict in ('COST_DOMINATED', 'EXIT_MISSPECIFIED', 'MECHANICAL_FLOOR') \
        else ''
    prov = report['manifest'].get('provenance', {})
    prov_line = (f'<div class="meta"><span><b>generated:</b> '
                 f'{html.escape(prov.get("generated_at_utc", "—"))} UTC</span>'
                 f'<span><b>python:</b> {html.escape(prov.get("python_version", "—"))}</span>'
                 f'<span><b>os:</b> {html.escape(prov.get("platform", "—"))}</span>'
                 f'<span><b>git:</b> {html.escape(prov.get("git_commit", "—"))}</span>'
                 f'</div>')
    header = (
        f'<header><h1>V8 Diagnostic Report — why is it negative?</h1>'
        f'<div class="sub">Deterministic diagnostic of the lab economics '
        f'(&#8220;explains, never fixes&#8221;). Engine '
        f'{html.escape(report["manifest"]["engine_version"])} · data hash '
        f'<code>{report["manifest"]["data_hash"][:12]}&#8230;</code></div>'
        f'<span class="verdict {vcls}">VERDICT: {html.escape(verdict)}</span>'
        f'<span class="authority">AUTHORITY: NONE — DIAGNOSTIC ONLY</span>'
        f'<div class="meta">'
        f'<span><b>configs searched:</b> {report["n_configs_searched"]}</span>'
        f'<span><b>drafts:</b> {report["manifest"]["n_drafts"]}</span>'
        f'<span><b>window:</b> {report["manifest"]["window_bars"]} bars</span>'
        f'<span><b>cost:</b> {report["manifest"]["cost_r"]}R</span>'
        f'<span><b>funding:</b> {report["manifest"]["funding_rate_r"]}</span>'
        f'<span><b>seed:</b> {report["manifest"]["seed"]}</span>'
        f'</div>{prov_line}</header>')

    # ---- executive summary ------------------------------------------------ #
    c = s['cost_census']
    a = s['ablation']
    hz = s['horizon']
    dur = hz['duration_bars']
    tp = s['path_stats']['early_take_profit']
    sl = s['path_stats']['early_stop_loss']
    amb = s['path_stats']['intrabar_ambiguity']
    best_h = max(hz['horizons'].items(), key=lambda kv: kv[1]['net_R']) \
        if hz['horizons'] else (None, {})
    def _pct_or_dash(v):
        return f'{v * 100:.0f}%' if v is not None else '—'
    kpis = _kpi([
        ('net R / trade', _fmt(c['net_R_mean']), 'mean over executed-setup trades'),
        ('gross edge', _fmt(c['rows']['gross_R']['mean']),
         f'before {_fmt(c["rows"]["cost_R_fee_plus_slippage"]["mean"])}R cost'),
        ('cost / edge', f'{c["rows"]["cost_R_fee_plus_slippage"]["mean"] / c["rows"]["gross_R"]["mean"]:.1f}x'
         if c['rows']['gross_R']['mean'] else '—', 'flat cost vs gross edge'),
        ('frictionless', _fmt(a['frictionless']), 'zero-cost counterfactual'),
        ('mean duration', f'{dur["mean"]:.1f} bars',
         f'median {dur["median"]} · p90 {dur["p90"]}'),
        ('best horizon', f'{best_h[0]} bars' if best_h[0] else '—',
         _fmt(best_h[1].get('net_R')) if best_h[1] else ''),
        ('early-TP', _pct_or_dash(tp.get('fraction')),
         f'of targets continued >2R (mean +{tp.get("mean_post_exit_max_r") or 0:.1f}R)'),
        ('early-SL', _pct_or_dash(sl.get('fraction')),
         'of stops saw >0.5R favorable first'),
    ])
    ev_text = json.dumps(report['verdict_evidence'])
    exec_summary = _section(
        '0', 'Executive summary', kpis,
        f'verdict evidence: <code>{html.escape(ev_text)}</code> · '
        f'<b>PROMOTION_REQUIRES: {html.escape(report["promotion_requires"])}</b>')

    # ---- identity + R denominator ---------------------------------------- #
    ident = s['identity']
    rd = ident['r_denominator']
    id_body = (_table(['stat', 'value'],
                      [['net_R == gross − cost − funding', 'OK' if ident['identity_ok']
                        else f"{ident['identity_violations']} violations"],
                       ['R unit unique count', rd['unique_count']],
                       ['R unit median (price)', round(rd['median'], 2)],
                       ['R unit min', round(rd['min'], 2)],
                       ['R unit max', round(rd['max'], 2)]], number_cols=(1,)))
    if rd.get('constant_warning'):
        id_body += ('<div class="note"><b>WARNING:</b> R denominator is '
                    'constant — cross-hypothesis net_R comparison is invalid.'
                    '</div>')
    id_body += (_table(['stop distance / ATR', 'stop distance / realized-vol'],
                       [[round(ident['stop_distance']['stop_dist_atr_mean'], 3),
                         round(ident['stop_distance']['stop_dist_rv_mean'], 3)]],
                       number_cols=(0, 1)))
    sections = [exec_summary]
    if report.get('forensics'):
        sections.append(_render_forensics(report))
    if report.get('state_audit'):
        sections.append(_render_coverage(report))
    sections.append(_render_state_audit(report))
    sections.append(
        _section('1', 'Identity + R-denominator census', id_body,
                 'the R unit is the price distance of one R '
                 '(atr_ref); a constant unit would invalidate '
                 'cross-hypothesis comparison'))

    # ---- horizon sweep ---------------------------------------------------- #
    h_rows = []
    h_series = []
    for h in sorted(hz['horizons'], key=int):
        row = hz['horizons'][h]
        h_rows.append([f'{h} bars', row['net_R'], row['hit_rate'],
                       row['mean_win'] if row['mean_win'] is not None else '—',
                       row['mean_loss'] if row['mean_loss'] is not None else '—',
                       row['mean_overlap_count'],
                       row['stopped_before_h_at_shipped_SL']])
        h_series.append((h, row['net_R']))
    actual_mark = (round(dur['mean']), None) if dur['mean'] else None
    h_body = (_svg_line_chart(h_series, y_label='net R', mark=actual_mark)
              + '<div class="sec">dashed line = actual mean duration '
              f'({dur["mean"]:.1f} bars); clean mark-to-market (no stop/TP) '
              'with the shipped stop counted in &#8220;stopped before h&#8221;.'
              '</div>'
              + _table(['horizon', 'net R', 'hit rate', 'mean win',
                        'mean loss', 'overlap', 'stopped@SL before h'],
                       h_rows, number_cols=(1, 2, 3, 4, 5, 6)))
    sections.append(_section('5', 'Horizon sweep — holding longer?', h_body,
                             'mark-to-market at fixed horizons; overlap > 1 '
                             'means pseudo-replication — widen CI via block '
                             'bootstrap with block = h'))

    # ---- cost census ------------------------------------------------------ #
    rows = c['rows']
    cost_body = (_svg_bar_chart(
        [('gross', rows['gross_R']['mean']),
         ('cost', rows['cost_R_fee_plus_slippage']['mean']),
         ('funding', rows['funding_R']['mean']),
         ('net', c['net_R_mean'])], y_label='R')
        + _table(['item', 'mean R', 'total R', '% of net'],
                 [['gross_R', rows['gross_R']['mean'], rows['gross_R']['total'],
                   round(rows['gross_R']['mean'] / c['net_R_mean'] * 100, 1)
                   if c['net_R_mean'] else '—'],
                  ['cost_R (fee + slippage)', rows['cost_R_fee_plus_slippage']['mean'],
                   rows['cost_R_fee_plus_slippage']['total'],
                   round(rows['cost_R_fee_plus_slippage']['mean'] / c['net_R_mean'] * 100, 1)
                   if c['net_R_mean'] else '—'],
                  ['funding_R', rows['funding_R']['mean'], rows['funding_R']['total'],
                   round(rows['funding_R']['mean'] / c['net_R_mean'] * 100, 1)
                   if c['net_R_mean'] else '—']],
                 number_cols=(1, 2, 3))
        + f'<div class="note"><b>breakeven gross = {_fmt(c["breakeven_gross_R"])}R</b> '
          '— the gross the signal must clear per trade to break even. '
          f'<code>{html.escape(c["cost_flat_note"])}</code></div>')
    sections.append(_section('2', 'Cost census', cost_body,
                             'V8 models fee+slippage as ONE flat '
                             'round_trip_cost_r'))

    # ---- ablation --------------------------------------------------------- #
    ab_body = (_svg_bar_chart(
        [('actual', a['actual']), ('no_cost', a['no_cost']),
         ('no_funding', a['no_funding']), ('frictionless', a['frictionless'])],
        y_label='net R')
        + _table(['config', 'fee', 'funding', 'net R'],
                 [['actual', 'on', 'on', a['actual']],
                  ['no_cost', '0', 'on', a['no_cost']],
                  ['no_funding', 'on', '0', a['no_funding']],
                  ['frictionless', '0', '0', a['frictionless']]],
                 number_cols=(3,)))
    sections.append(_section('3', 'Zero-cost ablation', ab_body,
                             'the frictionless sign is the first diagnostic '
                             'split'))

    # ---- null baselines --------------------------------------------------- #
    nb_all = s['null_baselines']
    nb = nb_all['random_entry']
    null_body = (_svg_null_band(a['actual'], nb['p05'], nb['p95'], nb['median'])
                 + _table(['baseline', 'mean net R'],
                          [['random_entry (200 reps × N)',
                            round(nb['mean'], 4)],
                           ['random_entry median', round(nb['median'], 4)],
                           ['inverted_signal', round(nb_all['inverted_signal_mean'], 4)],
                           ['always_long', round(nb_all['always_long_mean'], 4)],
                           ['always_short', round(nb_all['always_short_mean'], 4)],
                           ['ACTUAL', round(a['actual'], 4)]],
                          number_cols=(1,))
                 + f'<div class="sec">actual percentile of the random-entry '
                   f'null: <b>{nb["actual_percentile"]:.1f}%</b> '
                   f'({nb["replications"]} replications, n={nb["n_per_run"]} '
                   'per run). If the actual sits inside the null band, the '
                   'signal is indistinguishable from random entries.</div>')
    sections.append(_section('4', 'Null baselines', null_body,
                             'does the signal beat random entries?'))

    # ---- path statistics -------------------------------------------------- #
    p = s['path_stats']
    census = p['exit_reason_census']
    reason_items = [(ep, info['count']) for ep, info in sorted(census.items())]
    reason_rows = [[ep, info['count'], info['mean_R'], info['mean_duration']]
                   for ep, info in sorted(census.items())]
    path_body = (_svg_bar_chart(reason_items, y_label='count',
                                color_by_sign=False)
                 + _table(['exit reason', 'count', 'mean R', 'mean duration'],
                          reason_rows, number_cols=(1, 2, 3))
                 + '<h3 style="margin:16px 0 4px">Early stop-loss</h3>'
                 + _table(['stat', 'value'],
                          [['stopped', sl['n_stopped']],
                           ['saw >0.5R favorable first', sl['n_mfe_gt_half_R_before_stop']],
                           ['fraction', _pct_or_dash(sl.get('fraction'))]],
                          number_cols=(1,))
                 + '<h3 style="margin:16px 0 4px">Early take-profit</h3>'
                 + _table(['stat', 'value'],
                          [['target exits', tp['n_target']],
                           ['continued >2R after exit', tp['n_post_exit_gt_2R']],
                           ['fraction', _pct_or_dash(tp.get('fraction'))],
                           ['mean post-exit max R',
                            round(tp.get('mean_post_exit_max_r') or 0, 3)]],
                          number_cols=(1,))
                 + '<h3 style="margin:16px 0 4px">Intrabar ambiguity</h3>'
                 + (f'<div class="note">{amb.get("ambiguous_count", 0)} trades '
                    f'touched both barriers; pessimistic '
                    f'{_fmt(amb["pessimistic_mean"])} vs optimistic '
                    f'{_fmt(amb["optimistic_mean"])} (spread '
                    f'{_fmt(amb["spread_R"])}R) — the tie-break rule '
                    'dominates this classification.</div>'
                    if amb.get('ambiguous_count') else
                    '<div class="sec">no ambiguous bars</div>'))
    sections.append(_section('6', 'Path statistics (MFE / MAE / exits)',
                             path_body,
                             'early-SL &#8804; stop saw favorable first; '
                             'early-TP &#8805; target continued after exit'))

    # ---- distributions (from per-trade ledger) --------------------------- #
    nets = [t.net_r for t in trades]
    maes = [t.mae_r for t in trades]
    mfes = [t.mfe_r for t in trades]
    durs = [t.bars_held for t in trades]
    dist_body = (f'<div class="grid2">'
                 f'<div><div class="sec">net R</div>'
                 f'{_svg_histogram(nets, x_label="net R", color="#2c6fbb")}</div>'
                 f'<div><div class="sec">MAE (R)</div>'
                 f'{_svg_histogram(maes, x_label="MAE R", color="#d73027")}</div>'
                 f'<div><div class="sec">MFE (R)</div>'
                 f'{_svg_histogram(mfes, x_label="MFE R", color="#1a9850")}</div>'
                 f'<div><div class="sec">duration (bars)</div>'
                 f'{_svg_histogram(durs, x_label="bars", color="#7f8c8d")}</div>'
                 f'</div>')
    sections.append(_section('7', 'Trade distributions', dist_body,
                             'per-trade path statistics from trades.jsonl'))

    # ---- entry timing ----------------------------------------------------- #
    et = s['entry_timing']
    et_series = [(d, et[d]['mean_markout_bps']) for d in sorted(et, key=int)]
    et_body = (_svg_line_chart(et_series, y_label='mark-out bps')
               + _table(['Δ (bars)', 'mean mark-out (bps)', 'n'],
                        [[d, et[d]['mean_markout_bps'], et[d]['n']]
                         for d in sorted(et, key=int)],
                        number_cols=(1, 2))
               + '<div class="sec">negative mark-out growing with Δ = '
               'systematically bad entry ticks (separate from the slippage '
               'model).</div>')
    sections.append(_section('8', 'Entry timing — mark-out', et_body,
                             'signed, direction-corrected close-to-close '
                             'move from entry'))

    # ---- segments --------------------------------------------------------- #
    seg = s['segments']
    seg_body = ''
    for name in ('side', 'vol_tercile', 'session_hour', 'month'):
        cells = seg.get(name, {})
        if not cells:
            continue
        rows = []
        for k, v in sorted(cells.items(), key=lambda kv: kv[0]):
            min_n = v['min_N_for_0_01R']
            rows.append([k, v['N'],
                         (v['net_R'] if v['net_R'] is not None else '—'),
                         (f'{min_n:.0f}' if min_n is not None
                          and min_n == min_n and min_n < float('inf')
                          else '∞'),
                         v['status']])
        seg_body += (f'<h3 style="margin:12px 0 2px">{name}</h3>'
                     + _table(['cell', 'N', 'net R', 'min N for 0.01R',
                               'status'], rows, number_cols=(1, 2, 3)))
    sections.append(_section('9', 'Segment breakdown', seg_body,
                             'INSUFFICIENT cells are not scored (no subgroup '
                             'mining)'))

    # ---- invariants ------------------------------------------------------- #
    inv = s['invariants']
    inv_class = 'invalid' if not inv['ok'] else 'sec'
    inv_text = ('FAIL — report INVALID, sections 1-9 not to be used.'
                if not inv['ok'] else 'all simulator invariants held')
    inv_body = ('<div class="' + inv_class + '"><b>' + inv_text
                + '</b><br>' + html.escape(inv['note_parity']) + '</div>')
    if inv['fails']:
        inv_body += _table(['invariant failure'],
                           [[f] for f in inv['fails'][:10]], number_cols=())
    sections.append(_section('10', 'Simulator invariants', inv_body,
                             'fills in range, gap-through semantics, funding '
                             'prefix, monotonicity, determinism'))

    body = '\n'.join(sections)
    footer = ('<footer><b>AUTHORITY: NONE — DIAGNOSTIC ONLY</b> · generated '
              f'deterministically by <code>tools/diagnostic.py</code> '
              f'({html.escape(report["manifest"]["engine_version"])}) · '
              'this report explains, it does not decide.</footer>')
    if fragment:
        # Body only — no <html>/<head>/<style>, so a parent document (the dev
        # multi report) that already carries _CSS can embed this cell report.
        return f'<div class="wrap">{header}{body}{footer}</div>'
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>V8 Diagnostic Report — {html.escape(verdict)}</title>'
            f'<style>{_CSS}</style></head><body><div class="wrap">'
            f'{header}{body}{footer}'
            '</div></body></html>')



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

VERDICT_ORDER = ('KEEP', 'REPAIR', 'INVESTIGATE', 'HARD_REPAIR')


def _slice_cell(rows, symbol, span_ns):
    sym = [r for r in rows if r.instrument == symbol]
    klines = [r for r in sym if r.channel == 'kline']
    if not klines:
        return []
    last = max(r.available_time for r in klines)
    return [r for r in sym if r.available_time > last - span_ns]


def _run_cell(args):
    """One (symbol, timeframe) cell. Top-level for multiprocessing."""
    (symbol, tf, tape_path, span_ns, seed, out_dir, allow_surface,
     cost_r, cost_bps) = args
    rows = AppendOnlyLog(tape_path).replay_tape()
    cell_rows = _slice_cell(rows, symbol, span_ns)
    if not cell_rows:
        return {'symbol': symbol, 'tf': tf, 'error': 'no bars in span'}
    if tf != '1h':
        cell_rows = aggregate(cell_rows, '1h', tf)
    if not cell_rows:
        return {'symbol': symbol, 'tf': tf, 'error': 'aggregation empty'}
    eng = DiagnosticEngine(cell_rows, ALL_EXPERT_CLASSES, seed=seed,
                           base_interval=tf, do_forensics=True,
                           allow_surface=allow_surface,
                           cost_r=cost_r, cost_bps=cost_bps)
    report = eng.run()
    trades = [eng._simulate(d, min(bi + eng.lag, len(eng.bars) - 1))
              for d, bi in eng.drafts]
    cell_dir = Path(out_dir) / f'{symbol}-{tf}'
    write_report(cell_dir, report, trades)
    return {'symbol': symbol, 'tf': tf,
            'verdict': report['verdict'],
            'n_drafts': report['manifest']['n_drafts'],
            'state_projection': report['manifest']['per_expert_state_projection'],
            'decision_table': report['forensics']['decision_table'],
            'portfolio': report['forensics']['portfolio'],
            'path': str(cell_dir),
            # Full cell report + trades, kept so the dev multi HTML can embed
            # every cell's complete report in ONE file (100% of the info).
            'report': report,
            'trades': trades}


def plan_cells(tape_path, symbols, timeframes, *, span_ns, out_dir, seed,
               allow_surface, cost_r, cost_bps):
    """The (symbol x timeframe) job list, built ONCE before any fork.

    Each cell's seed is derived from its POSITION in this fixed enumeration,
    so the job list — and therefore every cell's output — is identical no
    matter how many processes consume it. Pure and separately testable on
    purpose: the determinism of the multi-cell run is a property of this
    function alone.
    """
    return [(s, tf, str(tape_path), span_ns, seed + i, str(out_dir),
             allow_surface, cost_r, cost_bps)
            for i, (s, tf) in enumerate(
                (s, tf) for s in symbols for tf in timeframes)]


def run_multi(tape_path, symbols, timeframes, *, span_ns, out_dir, seed=7,
              processes=4, allow_surface=False, cost_r=0.07,
              cost_bps=None) -> dict:
    """Run every (symbol, timeframe) cell and aggregate.

    Deterministic in `processes`: the per-cell seed is derived from the cell's
    POSITION in the fixed (symbol x timeframe) enumeration, so `--processes 1`
    and `--processes 8` produce identical output. (Before 2026-08-09 the
    parallel branch used `seed + i` while the sequential branch used a bare
    `seed`, so the two paths silently disagreed on every cell but the first —
    a determinism break in the one property this project cannot trade away.)
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cells = []
    jobs = plan_cells(tape_path, symbols, timeframes, span_ns=span_ns,
                      out_dir=out, seed=seed, allow_surface=allow_surface,
                      cost_r=cost_r, cost_bps=cost_bps)
    # Parallelism only affects wall time and RETURN order, never the per-cell
    # output (each cell writes its own dir and carries its own seed).
    if processes and processes > 1:
        import multiprocessing as mp
        with mp.Pool(processes=processes) as pool:
            results = pool.map(_run_cell, jobs)
        cells = [r for r in results if 'error' not in r]
        errors = [r for r in results if 'error' in r]
    else:
        errors = []
        for job in jobs:
            r = _run_cell(job)
            if 'error' in r:
                print(f'  cell {r["symbol"]}-{r["tf"]}: {r["error"]}',
                      file=sys.stderr)
                errors.append(r)
                continue
            cells.append(r)
    report = _aggregate(cells, errors, span_ns, seed, symbols, timeframes)
    # report.json carries the aggregate only — the per-cell full reports/trades
    # are bulky and already on disk under out/{symbol}-{tf}/ (write_report).
    (out / 'report.json').write_text(
        json.dumps(_jsonable_multi_report(report), indent=2, sort_keys=True,
                   default=str) + '\n')
    return report


def _jsonable_multi_report(report: dict) -> dict:
    """report dict minus the bulky per-cell full reports/trades. The live
    `report` (with them) stays in memory for render_multi_html; this is only
    the JSON-persistence view."""
    r = {k: v for k, v in report.items() if k != 'cells'}
    r['cells'] = [{k: v for k, v in c.items()
                   if k not in ('report', 'trades')} for c in report['cells']]
    return r


def _aggregate(cells, errors, span_ns, seed, symbols, timeframes):
    # per-cell verdict by expert
    cells_by_key = {}
    for c in cells:
        cells_by_key[f"{c['symbol']}-{c['tf']}"] = c
    # matrix: expert -> {cell_key: verdict}
    experts = sorted({r['expert'] for c in cells
                      for r in c['decision_table']})
    matrix = {e: {} for e in experts}
    zero_edge = {e: [] for e in experts}
    for c in cells:
        for r in c['decision_table']:
            key = f"{c['symbol']}-{c['tf']}"
            matrix[r['expert']][key] = r['verdict']
            zero_edge[r['expert']].append(r['zero_cost_edge'])
    # consistency: modal verdict + stability + worst verdict
    consistency = {}
    for e in experts:
        counts = {}
        for v in matrix[e].values():
            counts[v] = counts.get(v, 0) + 1
        if not counts:
            continue
        modal = max(counts, key=lambda k: (counts[k], -VERDICT_ORDER.index(k)))
        n_cells = len(matrix[e])
        worst = min(matrix[e].values(),
                    key=lambda v: VERDICT_ORDER.index(v)) \
            if n_cells else 'INVESTIGATE'
        consistency[e] = {
            'cells': n_cells, 'modal': modal,
            'stability': counts.get(modal, 0) / n_cells,
            'worst': worst,
            'mean_zero_edge': (sum(zero_edge[e]) / len(zero_edge[e])
                               if zero_edge[e] else None),
            'robust': (modal in ('KEEP', 'REPAIR') and worst != 'HARD_REPAIR'
                       and counts.get(modal, 0) / n_cells >= 0.5),
            'flips': worst in ('KEEP', 'REPAIR') and modal in
                     ('HARD_REPAIR', 'INVESTIGATE') or
                     (modal in ('KEEP', 'REPAIR') and worst == 'HARD_REPAIR'),
        }
    # aggregate portfolio
    all_counts = {}
    for c in cells:
        for v, n in c['portfolio']['counts'].items():
            all_counts[v] = all_counts.get(v, 0) + n
    robust = sorted([e for e, s in consistency.items() if s['robust']],
                    key=lambda e: -(consistency[e]['mean_zero_edge'] or 0))
    flips = sorted([e for e, s in consistency.items() if s['flips']],
                   key=lambda e: e)
    recommendation = _multi_recommendation(robust, flips, all_counts)
    return {
        'authority': 'NONE', 'diagnostic_only': True,
        'span_ns': span_ns, 'span_days': round(span_ns / (24 * HOUR_NS), 1),
        'symbols': list(symbols), 'timeframes': list(timeframes),
        'seed': seed, 'cells': cells, 'cell_errors': errors,
        'provenance': _provenance(),
        'matrix': matrix,
        'consistency': consistency,
        'portfolio': {'verdict_counts': all_counts,
                      'robust_experts': robust,
                      'flip_experts': flips,
                      'recommendation': recommendation},
    }


def _multi_recommendation(robust, flips, all_counts):
    parts = []
    if robust:
        parts.append(f'{len(robust)} experts are robustly salvageable across '
                     f'symbols/timeframes: {", ".join(robust[:5])}')
    if flips:
        parts.append(f'{len(flips)} experts FLIP across cells '
                     f'(salvageable in some, broken in others): '
                     f'{", ".join(flips[:5])} — symbol/timeframe-specific, '
                     'not a cross-asset edge')
    n_hard = all_counts.get('HARD_REPAIR', 0)
    if n_hard:
        parts.append(f'{n_hard} expert-cell verdicts are HARD_REPAIR (broken '
                     'even frictionless) — the candidate list for rebuilds')
    if not parts:
        parts.append('no expert is consistently salvageable across the tested '
                     'cells — the entry signal itself is the next experiment')
    return '; '.join(parts)


def render_multi_html(report: dict) -> str:
    """One DEV HTML for the multi-symbol × multi-timeframe report.

    The cross-symbol verdict matrix (summary) sits on top; below it, EVERY
    cell's complete report (9 sections + forensics + state audit + charts) is
    embedded as a fragment — 100% of the information in one file. Cell order is
    the fixed (symbol, timeframe) enumeration, so the document is deterministic.
    """
    cells = report['cells']
    cell_keys = [f"{c['symbol']}-{c['tf']}" for c in cells]
    experts = sorted(report['matrix'].keys())
    # matrix rows: expert | per-cell verdict badge | modal | stability | mean zero edge
    rows = []
    for e in experts:
        m = report['matrix'][e]
        cons = report['consistency'].get(e, {})
        cell_cells = ''.join(
            f'<td>{_verdict_badge(m.get(k, "—")) if k in m else "—"}</td>'
            for k in cell_keys)
        rows.append(('<tr>'
                     f'<td><b>{e}</b></td>{cell_cells}'
                     f'<td>{_verdict_badge(cons.get("modal", "—"))}</td>'
                     f'<td>{cons.get("stability", 0) * 100:.0f}%</td>'
                     f'<td>{_fmt(cons.get("mean_zero_edge"))}</td>'
                     f'<td>{"🟢 robust" if cons.get("robust") else ("🔀 flips" if cons.get("flips") else "")}</td>'
                     '</tr>'))
    headers = (['expert'] + cell_keys +
               ['modal', 'stability', 'mean zero-cost edge', 'robust?'])
    matrix_html = ('<table><thead><tr>' +
                   ''.join(f'<th>{html_escape(h)}</th>' for h in headers) +
                   f'</tr></thead><tbody>{"".join(rows)}</tbody></table>')
    # per-cell verdict counts table
    counts_rows = []
    for c in cells:
        cnt = c['portfolio']['counts']
        counts_rows.append([f"{c['symbol']}-{c['tf']}", c['verdict'],
                            c['n_drafts'],
                            cnt.get('KEEP', 0), cnt.get('REPAIR', 0),
                            cnt.get('INVESTIGATE', 0),
                            cnt.get('HARD_REPAIR', 0)])
    # robust / flip lists
    cons = report['portfolio']
    robust_html = ('<div class="sec">' + (', '.join(cons['robust_experts'])
                                           if cons['robust_experts']
                                           else 'none — no expert is '
                                                'consistently salvageable') +
                   '</div>')
    flip_html = ('<div class="sec">' + (', '.join(cons['flip_experts'])
                                         if cons['flip_experts']
                                         else 'none') + '</div>')
    all_counts = cons['verdict_counts']
    counts_kpi = ''.join(
        f'<div><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in sorted(all_counts.items()))
    prov = report.get('provenance', {})
    prov_line = (f'<div class="meta"><span><b>generated:</b> '
                 f'{html_escape(prov.get("generated_at_utc", "—"))} UTC</span>'
                 f'<span><b>python:</b> {html_escape(prov.get("python_version", "—"))}</span>'
                 f'<span><b>os:</b> {html_escape(prov.get("platform", "—"))}</span>'
                 f'<span><b>git:</b> {html_escape(prov.get("git_commit", "—"))}</span>'
                 f'</div>')
    # Navigation menu: one anchor per cell, jumping to the embedded full
    # report below. Deterministic order (symbol, timeframe enumeration).
    nav = ('<nav class="cell-nav">' +
           ''.join(f'<a href="#cell-{html_escape(k)}">{html_escape(k)}</a>'
                   for k in cell_keys) + '</nav>')
    # Every cell's COMPLETE report, embedded as a body fragment (the parent
    # document already carries _CSS; the fragment adds no <html>/<head>).
    cell_sections = []
    for c in cells:
        if 'error' in c:
            cell_sections.append(
                f'<section id="cell-{html_escape(c["symbol"])}-'
                f'{html_escape(c["tf"])}" class="cell-report">'
                f'<h2>{html_escape(c["symbol"])}-{html_escape(c["tf"])}</h2>'
                f'<div class="note"><b>cell error:</b> '
                f'{html_escape(c["error"])}</div></section>')
            continue
        frag = render_html(c['report'], c['trades'], fragment=True)
        cell_sections.append(
            f'<section id="cell-{html_escape(c["symbol"])}-'
            f'{html_escape(c["tf"])}" class="cell-report">'
            f'<h2>{html_escape(c["symbol"])}-{html_escape(c["tf"])} — '
            f'full report</h2>{frag}</section>')
    cell_html = '\n'.join(cell_sections)
    body = (
        '<header><h1>Multi-symbol × Multi-timeframe Diagnostic</h1>'
        f'<div class="sub">cells: {", ".join(cell_keys)} · span '
        f'{report["span_days"]} days · seed {report["seed"]}</div>'
        '<span class="authority">AUTHORITY: NONE — DIAGNOSTIC ONLY</span>'
        f'{prov_line}'
        '</header>'
        f'{nav}'
        '<div class="card"><h2>Cross-symbol verdict matrix</h2>'
        '<div class="sec">each expert × each (symbol, timeframe) cell; modal '
        'verdict and stability across cells; &#8220;robust&#8221; = modal '
        'KEEP/REPAIR, never HARD_REPAIR, ≥50% stable. Rows ranked '
        'alphabetically.</div>'
        f'{matrix_html}</div>'
        '<div class="card"><h2>Robust vs flipping experts</h2>'
        '<h3>Robustly salvageable across cells</h3>' + robust_html
        + '<h3>Flip across cells (symbol/timeframe-specific)</h3>' + flip_html
        + '</div>'
        '<div class="card"><h2>Aggregate portfolio</h2>'
        '<div class="portfolio-kpis">' + counts_kpi + '</div>'
        + _table(['cell', 'aggregate verdict', 'drafts',
                  'KEEP', 'REPAIR', 'INVESTIGATE', 'HARD_REPAIR'],
                 counts_rows, number_cols=(2, 3, 4, 5, 6))
        + f'<div class="note"><b>Recommendation:</b> '
          f'{html_escape(cons["recommendation"])}</div></div>'
        '<div class="card"><h2>Per-cell full reports</h2>'
        '<div class="sec">every cell&#8217;s complete diagnostic report '
        '(9 sections + per-expert forensics + MarketState audit + charts), '
        'embedded below — 100% of the information in one file.</div>'
        f'{cell_html}</div>'
        '<footer><b>AUTHORITY: NONE — DIAGNOSTIC ONLY</b> · cross-symbol '
        'suggestions still need a preregistered challenger (rule 12)</footer>')
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Multi-symbol × Multi-timeframe Diagnostic</title>'
            f'<style>{_CSS}</style></head><body><div class="wrap">{body}'
            '</div></body></html>')


def html_escape(s):
    import html as _h
    return _h.escape(str(s))



# --------------------------------------------------------------------------- #
# Unified CLI: single-report by default; --symbols opts into the matrix report
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tape', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--store', type=Path, default=None)
    ap.add_argument('--window', type=int, default=None)
    ap.add_argument('--cost', type=float, default=0.07,
                    help='flat round-trip cost in R (default 0.07)')
    ap.add_argument('--cost-bps', type=float, default=None,
                    help='round-trip cost in bps of notional; REPLACES --cost. '
                         'Unlike the flat R charge this scales with the R '
                         'unit, so an R-widening experiment moves it')
    ap.add_argument('--allow-surface', action='store_true')
    # matrix-report mode (the consolidated multi-diagnostic)
    ap.add_argument('--symbols', type=str, default=None,
                    help='comma-separated symbols -> matrix report '
                         '(default: single-symbol report on the tape universe)')
    ap.add_argument('--timeframes', type=str, default='1h,4h')
    ap.add_argument('--span-days', type=int, default=116)
    ap.add_argument('--processes', type=int, default=4)
    args = ap.parse_args(argv)

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
        timeframes = [t.strip() for t in args.timeframes.split(',') if t.strip()]
        span_ns = args.span_days * 24 * HOUR_NS
        report = run_multi(args.tape, symbols, timeframes, span_ns=span_ns,
                           out_dir=args.out, processes=args.processes,
                           allow_surface=args.allow_surface,
                           cost_r=args.cost, cost_bps=args.cost_bps)
        (Path(args.out) / 'report.html').write_text(
            render_multi_html(report), encoding='utf-8')
        print(_serialize(report))
    else:
        tape = AppendOnlyLog(args.tape).replay_tape()
        report = run_diagnostic(tape, ALL_EXPERT_CLASSES, args.out,
                                store_dir=args.store,
                                window_bars=args.window, cost_r=args.cost,
                                cost_bps=args.cost_bps,
                                allow_surface=args.allow_surface)
        print(_serialize(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
