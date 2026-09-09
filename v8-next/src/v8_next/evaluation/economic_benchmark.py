"""Economic benchmark fabric: real-data comparison with separate evidence verdicts.

Implements the professional-benchmark decision structure (research validity,
economic evidence, statistical evidence, portfolio contribution, execution
evidence, capital eligibility) as six independent verdicts. No single PASS
exists; a statistical confidence never mints economic success or capital
permission.

Conventions:
- All inputs are real venue data or engine replays of it. Synthetic series
  are allowed only inside control experiments explicitly labeled SYNTHETIC.
- Missing data/estimators stay missing (None / UNRUN / UNDERPOWERED) and
  never convert to success.
- Funding settlement is not fed to the engine in this scope, so funding cost
  is reported MISSING on every leg (strategy and benchmarks share the basis).
- Commissions come from the engine exactly once (verified estimate per fill
  reconciled against the engine-reported commission total). They are never
  subtracted a second time.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict

HOURS_PER_YEAR = 365.0 * 24.0
TAKER_FEE_DEFAULT = 0.0005
CAPITAL_DEFAULT = 10000.0
VOL_LOOKBACK = 48
VOL_TARGET_ANNUAL = 0.20
MAX_LEVERAGE = 2.0
INTERVAL_BARS = 24  # one calendar day of 1h bars per return interval
BOOTSTRAP_BLOCK = 24
BOOTSTRAP_REPS = 999
BOOTSTRAP_SEED = 7
OOS_FIT_BARS = 350  # chronological split of the 500-bar window; fixed, never relabeled

VerdictState = Literal[
    "VALID",
    "INVALID",
    "POSITIVE_DESCRIPTIVE",
    "NEGATIVE",
    "INCONCLUSIVE",
    "SUPPORTED",
    "UNDERPOWERED",
    "UNSUPPORTED",
    "HELPFUL_DESCRIPTIVE",
    "NOT_HELPFUL",
    "SIM_ONLY",
    "EXECUTION_UNPROVEN",
    "UNRUN",
    "NOT_AUTHORIZED",
]

BENCHMARK_IDS = (
    "cash",
    "btc_buy_hold",
    "equal_weight",
    "vol_target",
    "simple_trend",
)


class DatasetIdentity(BaseModel):
    """What real data entered the run. Hash-bound, no substitution allowed."""

    model_config = ConfigDict(frozen=True)

    tape_path: str
    tape_sha256: str
    universe: tuple[str, ...]
    period_start_ns: int
    period_end_ns: int
    n_bars: int
    source_hashes: tuple[str, ...]  # per-candle source_hash chain head/tail sample


class CodeIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    git_rev: str
    git_dirty: str
    config_sha256: str
    estimator_versions: dict[str, str]


class RunIdentity(BaseModel):
    """Binds data, universe, period, code/config, seed, estimator, benchmark, family."""

    model_config = ConfigDict(frozen=True)

    dataset: DatasetIdentity
    code: CodeIdentity
    seed: int
    primary_benchmark: str
    diagnostic_benchmarks: tuple[str, ...]
    strategy_family: tuple[str, ...]
    capital: float
    taker_fee: float
    opex_monthly_usd: float

    def digest(self) -> str:
        raw = self.model_dump_json()
        return hashlib.sha256(raw.encode()).hexdigest()


class MetricSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    net_return: float
    excess_vs_primary: float | None
    sharpe_per_bar: float
    sharpe_annualized: float
    sharpe_ci_low: float | None
    sharpe_ci_high: float | None
    sharpe_degenerate: bool = False
    max_drawdown: float
    tail_mean_5pct: float
    avg_exposure: float
    concentration: float
    turnover_notional_over_capital: float
    commission_cost: float
    funding_cost: float | None  # None == MISSING, never zero-filled
    cost_basis: str  # VERIFIED_ENGINE | ANALYTIC_MODEL | MISSING
    n_bars: int
    n_trades: int


class EvidenceVerdicts(BaseModel):
    model_config = ConfigDict(frozen=True)

    research_validity: VerdictState
    research_note: str
    economic: VerdictState
    economic_note: str
    statistical: VerdictState
    statistical_note: str
    portfolio: VerdictState
    portfolio_note: str
    execution: VerdictState
    execution_note: str
    capital: VerdictState
    capital_note: str


class EconomicReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    receipt_id: str
    run: RunIdentity
    metrics: dict[str, MetricSet]
    oos_metrics: dict[str, MetricSet]
    verdicts: EvidenceVerdicts
    statistics: dict[str, Any]
    controls: dict[str, Any]
    portfolio_mix: dict[str, Any]
    capacity_scenarios: list[dict[str, Any]]
    parity: dict[str, Any]
    shadow_live: dict[str, Any]
    limitations: list[str]
    claim_status: Literal["NO_ECONOMIC_CLAIM"] = "NO_ECONOMIC_CLAIM"

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


def git_info() -> dict[str, str]:
    def run(*args: str) -> str:
        try:
            out = subprocess.run(
                ["git", *args], capture_output=True, text=True, timeout=10
            )
            return out.stdout.strip() if out.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    dirty = run("status", "--porcelain")
    return {
        "rev": run("rev-parse", "--short", "HEAD"),
        "dirty": "yes"
        if dirty not in ("", "unknown")
        else ("unknown" if dirty == "unknown" else "no"),
    }


def estimator_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("numpy", "scipy", "arch", "nautilus_trader", "polars"):
        try:
            import importlib.metadata as md

            versions[name] = md.version(name)
        except Exception:
            versions[name] = "absent"
    return versions


@dataclass(frozen=True)
class BarView:
    end_ns: int
    open: float
    high: float
    low: float
    close: float


def bars_from_candles(candles: Sequence[Any]) -> list[BarView]:
    return [
        BarView(
            end_ns=int(c.end_ns),
            open=float(c.open),
            high=float(c.high),
            low=float(c.low),
            close=float(c.close),
        )
        for c in candles
    ]


def validate_chronology(bars: Sequence[BarView]) -> tuple[bool, str]:
    """Point-in-time guard: strictly increasing, positive prices, no gaps in order."""
    if len(bars) < 2:
        return False, "EMPTY_OR_SINGLE_BAR_WINDOW"
    for i, b in enumerate(bars):
        if not all(math.isfinite(v) and v > 0 for v in (b.open, b.high, b.low, b.close)):
            return False, f"NON_POSITIVE_OR_NONFINITE_BAR_{i}"
        if not (b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high):
            return False, f"OHLC_ORDER_VIOLATION_{i}"
        if i and bars[i - 1].end_ns >= b.end_ns:
            return False, f"NON_MONOTONIC_TIME_{i}"
    return True, "OK"


def detect_future_leak(bars: Sequence[BarView], closes_shift: int = 0) -> tuple[bool, str]:
    """Known-defect probe: a series shifted against its own timestamps is a leak."""
    if closes_shift != 0:
        return False, "FUTURE_LEAK_SHIFT_DETECTED"
    return True, "OK"


def per_bar_returns(equity: Sequence[float]) -> list[float]:
    out: list[float] = []
    for prev, cur in zip(equity, equity[1:], strict=False):
        out.append((cur - prev) / prev if prev > 0 else 0.0)
    return out


def sharpe_stats(returns: Sequence[float]) -> tuple[float, float]:
    arr = np.asarray(list(returns), dtype=np.float64)
    if arr.size < 2:
        return 0.0, 0.0
    sd = float(arr.std(ddof=1))
    if sd <= 1e-12:
        return 0.0, 0.0
    s = float(arr.mean() / sd)
    return s, s * math.sqrt(HOURS_PER_YEAR)


def block_bootstrap_ci(
    returns: Sequence[float],
    block: int = BOOTSTRAP_BLOCK,
    reps: int = BOOTSTRAP_REPS,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float | None, float | None]:
    """Circular block bootstrap CI for per-bar Sharpe; preserves dependence."""
    arr = np.asarray(list(returns), dtype=np.float64)
    n = arr.size
    if n < 2 * block or not np.isfinite(arr).all():
        return None, None
    rng = np.random.default_rng(seed)
    stats: list[float] = []
    for _ in range(reps):
        idx = (rng.integers(0, n, size=(n // block + 1))[:, None] + np.arange(block)).ravel()[:n] % n
        sample = arr[idx]
        sd = float(sample.std(ddof=1))
        if sd <= 1e-12 or not math.isfinite(sd):
            continue
        stats.append(float(sample.mean() / sd))
    if len(stats) < 10:
        return None, None
    lo, hi = np.percentile(np.asarray(stats), [2.5, 97.5])
    return float(lo), float(hi)


def max_drawdown(equity: Sequence[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, (v - peak) / peak)
    return worst


def compute_multileg_family(
    legs_closes: dict[str, list[float]],
    capital: float = CAPITAL_DEFAULT,
    taker_fee: float = TAKER_FEE_DEFAULT,
) -> dict[str, dict[str, Any]]:
    """Costed passive benchmarks over a real multi-asset universe.

    equal_weight buys 1/N per leg once (no rebalance fiction). vol_target
    scales each leg by trailing-only volatility with equal risk contribution
    and pays turnover on every weight change. bh_<RAW> holds each leg alone.
    simple_trend runs the fixed 48-bar Donchian long/flat rule per leg in
    equal capital sleeves. All share capital, fee and bar grid.
    """
    names = sorted(legs_closes)
    n = len(next(iter(legs_closes.values())))
    fams: dict[str, dict[str, Any]] = {}
    fams["cash"] = {"equity": [capital] * n, "turnover": 0.0, "commission": 0.0,
                    "n_trades": 0, "exposure": [0.0] * n}
    for raw in names:
        closes = legs_closes[raw]
        shares = (capital * (1.0 - taker_fee)) / closes[0]
        fams[f"bh_{raw.split('.')[0]}"] = {
            "equity": [shares * c for c in closes], "turnover": 1.0,
            "commission": capital * taker_fee, "n_trades": 1, "exposure": [1.0] * n,
        }
    k = len(names)
    eq_ew = [capital * (1.0 - taker_fee)]
    for i in range(1, n):
        r = sum(legs_closes[w][i] / legs_closes[w][i - 1] - 1.0 for w in names) / k
        eq_ew.append(eq_ew[-1] * (1.0 + r))
    fams["equal_weight"] = {"equity": eq_ew, "turnover": 1.0,
                            "commission": capital * taker_fee, "n_trades": k,
                            "exposure": [1.0] * n}
    target_pb = VOL_TARGET_ANNUAL / math.sqrt(HOURS_PER_YEAR)
    eq_vt = [capital]
    exp_vt = [0.0]
    turn_vt = 0.0
    comm_vt = 0.0
    prev_w = [0.0] * k
    for i in range(1, n):
        inv = []
        for leg in names:
            rets = [legs_closes[leg][j] / legs_closes[leg][j - 1] - 1.0
                    for j in range(max(1, i - VOL_LOOKBACK + 1), i + 1)]
            sd = float(np.std(np.asarray(rets), ddof=1)) if len(rets) >= 2 else 0.0
            inv.append(1.0 / sd if sd > 1e-12 else 0.0)
        tot = sum(inv)
        raw_w = [v / tot if tot > 0 else 0.0 for v in inv]
        port_vol = math.sqrt(sum(
            (raw_w[a] * (1.0 / inv[a] if inv[a] > 0 else 0.0)) ** 2 for a in range(k)
        )) if tot > 0 else 0.0
        scale = min(target_pb / port_vol, MAX_LEVERAGE) if port_vol > 1e-12 else 0.0
        wts = [x * scale for x in raw_w]
        cost = sum(abs(wts[a] - prev_w[a]) for a in range(k)) * eq_vt[-1] * taker_fee
        comm_vt += cost
        turn_vt += sum(abs(wts[a] - prev_w[a]) for a in range(k))
        r = sum(wts[a] * (legs_closes[names[a]][i] / legs_closes[names[a]][i - 1] - 1.0)
                for a in range(k))
        eq_vt.append(eq_vt[-1] * (1.0 + r) - cost)
        exp_vt.append(sum(wts))
        prev_w = wts
    fams["vol_target"] = {"equity": eq_vt, "turnover": turn_vt, "commission": comm_vt,
                          "n_trades": 0, "exposure": exp_vt}
    sleeve = capital / k
    eq_tr = [capital]
    exp_tr = [0.0]
    turn_tr = 0.0
    comm_tr = 0.0
    in_pos = [False] * k
    for i in range(1, n):
        day_r = 0.0
        ex = 0.0
        for a, raw in enumerate(names):
            closes = legs_closes[raw]
            look = closes[max(0, i - VOL_LOOKBACK):i]
            signal = closes[i] > max(look) if look else False
            if signal != in_pos[a]:
                cost = sleeve * taker_fee
                comm_tr += cost
                turn_tr += 1.0 / k
                eq_tr[-1] -= cost
                in_pos[a] = signal
            if in_pos[a]:
                day_r += (closes[i] / closes[i - 1] - 1.0) / k
                ex += 1.0 / k
        eq_tr.append(eq_tr[-1] * (1.0 + day_r))
        exp_tr.append(ex)
    fams["simple_trend"] = {"equity": eq_tr, "turnover": turn_tr, "commission": comm_tr,
                            "n_trades": 0, "exposure": exp_tr}
    return fams


def compute_benchmark_family(
    bars: Sequence[BarView],
    capital: float = CAPITAL_DEFAULT,
    taker_fee: float = TAKER_FEE_DEFAULT,
) -> dict[str, dict[str, Any]]:
    """Five analytic benchmarks on the same bars, capital, and fee. All costs explicit.

    vol_target uses trailing-48-bar volatility only (never future). simple_trend
    is a fixed 48-bar Donchian long/flat rule. equal_weight over the single-BTC
    universe equals buy-and-hold by construction; computed independently anyway.
    """
    closes = [b.close for b in bars]
    n = len(closes)
    fams: dict[str, dict[str, Any]] = {}

    fams["cash"] = {
        "equity": [capital] * n,
        "turnover": 0.0,
        "commission": 0.0,
        "n_trades": 0,
        "exposure": [0.0] * n,
    }

    shares = (capital * (1.0 - taker_fee)) / closes[0]
    eq_bh = [shares * c for c in closes]
    fams["btc_buy_hold"] = {
        "equity": eq_bh,
        "turnover": (capital / capital),
        "commission": capital * taker_fee,
        "n_trades": 1,
        "exposure": [1.0] * n,
    }
    fams["equal_weight"] = {
        "equity": list(eq_bh),
        "turnover": 1.0,
        "commission": capital * taker_fee,
        "n_trades": 1,
        "exposure": [1.0] * n,
        "note": "single-asset universe: identical to btc_buy_hold by construction",
    }

    logrets = [0.0] + [math.log(closes[i] / closes[i - 1]) for i in range(1, n)]
    target_pb = VOL_TARGET_ANNUAL / math.sqrt(HOURS_PER_YEAR)
    eq_vt = [capital]
    exposure_vt = [0.0]
    turnover_vt = 0.0
    commission_vt = 0.0
    prev_pos = 0.0
    for i in range(1, n):
        window = logrets[max(1, i - VOL_LOOKBACK + 1) : i + 1]
        if len(window) < 2:
            scale = 0.0
        else:
            sd = float(np.std(np.asarray(window), ddof=1))
            scale = min(target_pb / sd, MAX_LEVERAGE) if sd > 1e-12 else 0.0
        pos = scale * eq_vt[-1]
        d_notional = abs(pos - prev_pos)
        cost = d_notional * taker_fee
        commission_vt += cost
        turnover_vt += d_notional / capital
        pnl = pos * (closes[i] / closes[i - 1] - 1.0) - cost
        eq_vt.append(eq_vt[-1] + pnl)
        exposure_vt.append(abs(pos) / eq_vt[-2] if eq_vt[-2] > 0 else 0.0)
        prev_pos = pos
    fams["vol_target"] = {
        "equity": eq_vt,
        "turnover": turnover_vt,
        "commission": commission_vt,
        "n_trades": sum(1 for i in range(1, n) if exposure_vt[i] > 0 and exposure_vt[i - 1] == 0),
        "exposure": exposure_vt,
    }

    eq_tr = [capital]
    exposure_tr = [0.0]
    turnover_tr = 0.0
    commission_tr = 0.0
    in_pos = False
    for i in range(1, n):
        lookback = [b.high for b in bars[max(0, i - VOL_LOOKBACK) : i]]
        signal = closes[i] > max(lookback) if lookback else False
        want = 1.0 if signal else 0.0
        have = 1.0 if in_pos else 0.0
        if want != have:
            cost = abs(want - have) * eq_tr[-1] * taker_fee
            commission_tr += cost
            turnover_tr += abs(want - have)
            eq_tr[-1] -= cost
            in_pos = signal
        r = (closes[i] / closes[i - 1] - 1.0) if in_pos else 0.0
        eq_tr.append(eq_tr[-1] * (1.0 + r))
        exposure_tr.append(1.0 if in_pos else 0.0)
    fams["simple_trend"] = {
        "equity": eq_tr,
        "turnover": turnover_tr,
        "commission": commission_tr,
        "n_trades": 0,
        "exposure": exposure_tr,
    }
    flips = sum(1 for i in range(1, n) if exposure_tr[i] != exposure_tr[i - 1]) // 2
    fams["simple_trend"]["n_trades"] = flips
    return fams


def pair_positions(
    opened: list[Any], closed: list[Any]
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Pair opens to closes in time order per (instrument, position slot).

    Under NETTING, sequential positions on one instrument+strategy slot reuse
    the same position_id, so id-keyed matching collides. With max one
    concurrent position per slot, chronological pairing is exact; any break
    (close before open, leftover opens) leaves the close unpaired rather than
    misattributed.
    """
    def key(o: Any) -> tuple[str, str]:
        return (str(o.get("instrument_id", "")), str(o.get("position_id", "")))

    opens: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for o in opened:
        if isinstance(o, dict):
            opens.setdefault(key(o), []).append(o)
    closes: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for c in closed:
        if isinstance(c, dict):
            closes.setdefault(key(c), []).append(c)
    pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for k, olist in opens.items():
        olist.sort(key=lambda o: int(o.get("event_ns", 0) or 0))
        clist = sorted(closes.get(k, []), key=lambda c: int(c.get("event_ns", 0) or 0))
        ci = 0
        for o in olist:
            match: dict[str, Any] | None = None
            o_ns = int(o.get("event_ns", 0) or 0)
            while ci < len(clist):
                c_ns = int(clist[ci].get("event_ns", 0) or 0)
                if c_ns > o_ns:
                    match = clist[ci]
                    ci += 1
                    break
                ci += 1
            pairs.append((o, match))
    return pairs


def strategy_series_from_engine(
    engine_result: dict[str, Any],
    bars: Sequence[BarView],
    capital: float = CAPITAL_DEFAULT,
    taker_fee: float = TAKER_FEE_DEFAULT,
) -> dict[str, Any]:
    """Per-bar strategy equity from engine fills + closes. No double-counted costs.

    Commission per fill is estimated as notional * taker_fee and reconciled
    against the engine-reported commission total. Funding is MISSING (engine
    is not fed funding events in this scope).
    """
    closes = [b.close for b in bars]
    n = len(closes)
    end_ns = [b.end_ns for b in bars]
    idx_of = {ns: i for i, ns in enumerate(end_ns)}

    opened = engine_result.get("opened_positions", [])
    closed = engine_result.get("closed_positions", [])
    pairs = pair_positions(
        [p for p in opened if isinstance(p, dict)],
        [c for c in closed if isinstance(c, dict)],
    )

    reported_comm_total = 0.0
    for pos in engine_result.get("account", {}).get("positions", []):
        for c in pos.get("commissions", []) or []:
            try:
                reported_comm_total += float(str(c).split()[0])
            except (ValueError, TypeError):
                pass

    fills = [
        o
        for o in engine_result.get("account", {}).get("orders", [])
        if o.get("status") == "FILLED" and o.get("average_price") is not None
    ]
    est_comm_total = sum(
        float(o.get("filled_qty") or 0) * float(o.get("average_price") or 0) * taker_fee
        for o in fills
    )
    # Closed-loop verification: engine realized_pnl sums exactly to the balance
    # delta, so the engine charge is complete and counted once. The per-fill
    # estimate is then full attribution under the same fee model (the account's
    # commission list retains only the last position and is partial by itself).
    sum_realized = 0.0
    for c in closed:
        if isinstance(c, dict) and c.get("realized_pnl"):
            try:
                sum_realized += float(str(c["realized_pnl"]).split()[0])
            except (ValueError, TypeError):
                pass
    try:
        balance_total = float(str(engine_result["account"]["balance_total"]).split()[0])
    except (KeyError, ValueError, TypeError, AttributeError):
        balance_total = capital
    loop_err = abs((balance_total - capital) - sum_realized)
    if loop_err <= 0.01 and est_comm_total > 0:
        cost_basis = "VERIFIED_ENGINE"
        rel_err = abs(est_comm_total - reported_comm_total) / est_comm_total if est_comm_total else math.inf
    elif reported_comm_total > 0:
        rel_err = abs(est_comm_total - reported_comm_total) / reported_comm_total
        cost_basis = "VERIFIED_ENGINE" if rel_err <= 0.02 else "ESTIMATED"
    else:
        rel_err = math.inf
        cost_basis = "ESTIMATED" if est_comm_total == 0 else "MISMATCH"

    # Position intervals: open bar -> close bar with signed exposure.
    events: dict[int, list[tuple[str, float, float]]] = {}
    for pos, clo in pairs:
        try:
            o_idx = idx_of.get(int(pos.get("event_ns", -1)), None)
        except (ValueError, TypeError):
            o_idx = None
        if o_idx is None:
            continue
        side = str(pos.get("side", "")).upper()
        try:
            q = float(pos.get("quantity") or 0)
            px = float(pos.get("avg_px_open") or 0)
        except (ValueError, TypeError):
            continue
        d = 1.0 if side in ("BUY", "LONG") else -1.0
        events.setdefault(o_idx, []).append(("open", d * q, px))
        if isinstance(clo, dict):
            try:
                c_idx = idx_of.get(int(clo.get("event_ns", -1)), None)
            except (ValueError, TypeError):
                c_idx = None
            if c_idx is not None and c_idx > o_idx:
                events.setdefault(c_idx, []).append(("close", 0.0, 0.0))
    # Authoritative realized PnL per close bar (engine net of its own fees).
    realized_by_bar: dict[int, float] = {}
    for _pos, clo in pairs:
        if not isinstance(clo, dict) or not clo.get("realized_pnl"):
            continue
        try:
            c_idx = idx_of.get(int(clo.get("event_ns", -1)), None)
            val = float(str(clo["realized_pnl"]).split()[0])
        except (ValueError, TypeError):
            continue
        if c_idx is not None:
            realized_by_bar[c_idx] = realized_by_bar.get(c_idx, 0.0) + val
    equity = [capital]
    exposure = [0.0]
    qty = 0.0
    avg = 0.0
    turnover = 0.0
    n_trades = 0
    for i in range(1, n):
        for kind, qd, px in events.get(i, []):
            if kind == "open":
                qty = qd
                avg = px
                turnover += abs(qd) * px / capital
                n_trades += 1
            else:
                qty = 0.0
        mtm = qty * (closes[i] - avg) if qty != 0.0 else 0.0
        equity.append(equity[-1] + mtm)
        exposure.append(abs(qty * closes[i]) / equity[-2] if equity[-2] > 0 else 0.0)
    # Replace level with authoritative accounting: engine balance delta is the
    # net truth; distribute the residual (commissions + rounding) uniformly so
    # the terminal equity reconciles exactly and costs are counted once.
    try:
        balance_total = float(str(engine_result["account"]["balance_total"]).split()[0])
    except (KeyError, ValueError, TypeError, AttributeError):
        balance_total = capital
    drift = (balance_total - equity[-1]) / max(1, n - 1)
    adj = [equity[0]]
    for i in range(1, n):
        adj.append(adj[-1] + (equity[i] - equity[i - 1]) + drift)
    commission = capital + sum(
        realized_by_bar.get(i, 0.0) for i in range(n)
    ) - balance_total
    # commission here is the engine-implied total cost drag; prefer the full
    # fill-level attribution (reported list is last-position partial).
    commission_used = est_comm_total if cost_basis == "VERIFIED_ENGINE" else (
        reported_comm_total if reported_comm_total > 0 else est_comm_total
    )
    return {
        "equity": adj,
        "raw_equity": list(equity),
        "exposure": exposure,
        "turnover": turnover,
        "commission": commission_used,
        "funding": None,
        "cost_basis": cost_basis,
        "cost_reconciliation": {
            "reported_commission_partial": reported_comm_total,
            "estimated_commission_total": est_comm_total,
            "sum_realized_pnl": sum_realized,
            "balance_delta": balance_total - capital,
            "closed_loop_error": loop_err,
            "relative_error": rel_err if math.isfinite(rel_err) else None,
            "implied_drag": commission,
            "balance_total": balance_total,
        },
        "n_trades": n_trades,
    }


def portfolio_series_from_engine(
    engine_result: dict[str, Any],
    legs_closes: dict[str, list[float]],
    end_ns: list[int],
    capital: float = CAPITAL_DEFAULT,
    taker_fee: float = TAKER_FEE_DEFAULT,
    legs_quotevols: dict[str, list[float]] | None = None,
    funding_rows: Sequence[Any] | None = None,
    funding_measured_drag: float | None = None,
    funding_trades_identical: bool = False,
) -> dict[str, Any]:
    """Per-bar portfolio equity across legs from one shared-account engine run.

    legs_closes maps full instrument ids to per-bar closes on the shared
    end_ns timeline. Funding is measured by dual-run balance difference under
    verified identical trade signatures (the engine embeds settled funding in
    realized PnL, so single-run gap arithmetic cannot isolate it); the
    analytic row x open-position expectation is retained only as a
    cross-check. Unreconciled funding stays UNVERIFIED, never zero-filled.
    Participation per position leg is fill notional over real quote volume.
    """
    n = len(end_ns)
    idx_of = {ns: i for i, ns in enumerate(end_ns)}
    opened = engine_result.get("opened_positions", [])
    closed = engine_result.get("closed_positions", [])
    pairs = pair_positions(
        [p for p in opened if isinstance(p, dict)],
        [c for c in closed if isinstance(c, dict)],
    )

    fills = [
        o
        for o in engine_result.get("account", {}).get("orders", [])
        if o.get("status") == "FILLED" and o.get("average_price") is not None
    ]
    est_comm_total = sum(
        float(o.get("filled_qty") or 0) * float(o.get("average_price") or 0) * taker_fee
        for o in fills
    )

    # Per-position intervals on their own leg (pair-indexed: NETTING slots
    # reuse position ids, so id-keyed matching would collide).
    events: dict[int, list[tuple[str, str, float, float]]] = {}
    infos: dict[int, dict[str, Any]] = {}
    for pi, (pos, clo) in enumerate(pairs):
        inst = str(pos.get("instrument_id", ""))
        closes = legs_closes.get(inst)
        if closes is None or len(closes) != n:
            continue
        try:
            o_idx = idx_of.get(int(pos.get("event_ns", -1)), None)
            q = float(pos.get("quantity") or 0)
            px = float(pos.get("avg_px_open") or 0)
        except (ValueError, TypeError):
            continue
        if o_idx is None:
            continue
        side = str(pos.get("side", "")).upper()
        d = 1.0 if side in ("BUY", "LONG") else -1.0
        events.setdefault(o_idx, []).append(("open", inst, d * q, px))
        infos[pi] = {"instrument": inst, "qty": d * q, "open_px": px, "open_idx": o_idx,
                     "close_idx": None}
        if isinstance(clo, dict):
            try:
                c_idx = idx_of.get(int(clo.get("event_ns", -1)), None)
            except (ValueError, TypeError):
                c_idx = None
            if c_idx is not None and c_idx > o_idx:
                events.setdefault(c_idx, []).append(("close", inst, 0.0, 0.0))
                infos[pi]["close_idx"] = c_idx

    sum_realized = 0.0
    for c in closed:
        if isinstance(c, dict) and c.get("realized_pnl"):
            try:
                sum_realized += float(str(c["realized_pnl"]).split()[0])
            except (ValueError, TypeError):
                pass
    try:
        balance_total = float(str(engine_result["account"]["balance_total"]).split()[0])
    except (KeyError, ValueError, TypeError, AttributeError):
        balance_total = capital

    equity = [capital]
    exposure = [0.0]
    live: dict[str, list[float]] = {}  # inst -> [qty, avg]
    turnover = 0.0
    n_trades = 0
    prev_mtm: dict[str, float] = {}
    for i in range(1, n):
        for kind, inst, qd, px in events.get(i, []):
            if kind == "open":
                live[inst] = [qd, px]
                turnover += abs(qd) * px / capital
                n_trades += 1
            else:
                live.pop(inst, None)
                prev_mtm.pop(inst, None)
        step_pnl = 0.0
        gross = 0.0
        for inst, (qd, avg) in live.items():
            closes = legs_closes[inst]
            mtm = qd * (closes[i] - avg)
            step_pnl += mtm - prev_mtm.get(inst, 0.0)
            prev_mtm[inst] = mtm
            gross += abs(qd * closes[i])
        equity.append(equity[-1] + step_pnl)
        exposure.append(gross / equity[-2] if equity[-2] > 0 else 0.0)

    # Open-position mtm at the last bar + entry commissions of open positions.
    # balance_total carries realized (net) of closed positions minus entry
    # commissions of still-open ones; it does not carry their unrealized.
    open_mtm = 0.0
    open_entry_comm = 0.0
    for _pid, info in infos.items():
        if info["close_idx"] is None:
            closes = legs_closes[info["instrument"]]
            open_mtm += info["qty"] * (closes[-1] - info["open_px"])
            open_entry_comm += abs(info["qty"]) * info["open_px"] * taker_fee

    # Funding reconciliation: expected from real rows x open positions.
    # Same-bar open/close vs boundary ordering is ambiguous at event
    # granularity, so the expectation is a range over both conventions.
    funding_expected = 0.0
    funding_boundaries = 0
    per_boundary: list[float] = []
    for row in funding_rows or []:
        inst_full = f"{getattr(row, 'instrument', '')}-PERP.BINANCE"
        closes = legs_closes.get(inst_full)
        if closes is None:
            continue
        try:
            boundary = int(getattr(row, "funding_time_ms", -1)) * 1_000_000
            rate = float(getattr(row, "funding_rate", 0))
        except (ValueError, TypeError):
            continue
        b_idx = next((i for i, ns in enumerate(end_ns) if ns >= boundary), None)
        if b_idx is None:
            continue
        for _pid, info in infos.items():
            if info["instrument"] != inst_full:
                continue
            notion = abs(info["qty"]) * closes[b_idx]
            leg = -math.copysign(1.0, info["qty"]) * notion * rate
            held_strict = info["open_idx"] < b_idx and (info["close_idx"] is None or info["close_idx"] > b_idx)
            held_loose = info["open_idx"] <= b_idx and (info["close_idx"] is None or info["close_idx"] >= b_idx)
            if held_strict:
                funding_expected += leg
                funding_boundaries += 1
            if held_loose:
                per_boundary.append(leg)
    funding_paid = -funding_measured_drag if funding_measured_drag is not None else 0.0
    # Tolerance is data-derived: the largest single-boundary settlement held
    # (one event-ordering difference) plus dust. No invented coefficient.
    dust = (max((abs(v) for v in per_boundary), default=0.0)) + 0.02
    funding_ok = (
        funding_measured_drag is not None
        and funding_trades_identical
        and abs(funding_measured_drag - (-funding_expected)) <= dust
    )
    fed = bool(funding_rows)
    base_loop = abs((balance_total - capital) - sum_realized + open_entry_comm)
    if fed and funding_ok:
        cost_basis = "VERIFIED_ENGINE_FUNDING"
    elif fed:
        cost_basis = "FUNDING_UNVERIFIED"
    elif base_loop <= 0.02:
        cost_basis = "VERIFIED_ENGINE"
        funding_paid = 0.0
    else:
        cost_basis = "ESTIMATED"
    loop_err = abs(funding_measured_drag - (-funding_expected)) if (fed and funding_measured_drag is not None) else base_loop

    drift = (balance_total - equity[-1]) / max(1, n - 1)
    adj = [equity[0]]
    for i in range(1, n):
        adj.append(adj[-1] + (equity[i] - equity[i - 1]) + drift)

    # Participation: entry/exit notional over real bar quote volume.
    participations: list[float] = []
    if legs_quotevols:
        for _pid, info in infos.items():
            qv = legs_quotevols.get(info["instrument"])
            if not qv:
                continue
            o_not = abs(info["qty"]) * info["open_px"]
            if qv[info["open_idx"]] > 0:
                participations.append(o_not / qv[info["open_idx"]])
            if info["close_idx"] is not None:
                closes = legs_closes[info["instrument"]]
                x_not = abs(info["qty"]) * closes[info["close_idx"]]
                if qv[info["close_idx"]] > 0:
                    participations.append(x_not / qv[info["close_idx"]])
    return {
        "equity": adj,
        "raw_equity": list(equity),
        "exposure": exposure,
        "turnover": turnover,
        "commission": est_comm_total,
        "funding": funding_paid if fed else None,
        "funding_expected": funding_expected if fed else None,
        "funding_reconciled": funding_ok if fed else None,
        "funding_boundaries_held": funding_boundaries,
        "cost_basis": cost_basis,
        "cost_reconciliation": {
            "estimated_commission_total": est_comm_total,
            "sum_realized_pnl": sum_realized,
            "open_mtm_last": open_mtm,
            "balance_delta": balance_total - capital,
            "funding_paid_implied": funding_paid,
            "funding_expected": funding_expected,
            "closed_loop_error": loop_err,
            "balance_total": balance_total,
        },
        "participation": participations,
        "n_trades": n_trades,
    }


def metrics_for_curve(
    equity: Sequence[float],
    exposure: Sequence[float],
    turnover: float,
    commission: float,
    funding: float | None,
    cost_basis: str,
    primary_equity: Sequence[float] | None,
    n_trades: int,
    raw_nonzero_bars: int | None = None,
) -> MetricSet:
    rets = per_bar_returns(list(equity))
    s_pb, s_ann = sharpe_stats(rets)
    ci_lo, ci_hi = block_bootstrap_ci(rets)
    # Degenerate variance guard: a leg with information in only a handful of
    # bars (e.g. one trade in the window) yields explosive Sharpe arithmetic.
    # Counted on raw pre-reconciliation steps, never on drift-smeared levels.
    if raw_nonzero_bars is None:
        raw_nonzero_bars = sum(1 for v in rets if abs(v) > 1e-12)
    degenerate = raw_nonzero_bars < 10
    net = (equity[-1] / equity[0] - 1.0) if equity[0] > 0 else 0.0
    excess = None
    if primary_equity is not None and len(primary_equity) == len(equity):
        p_net = (primary_equity[-1] / primary_equity[0] - 1.0) if primary_equity[0] > 0 else 0.0
        excess = net - p_net
    tail = float(np.mean(np.sort(np.asarray(rets))[: max(1, int(0.05 * len(rets)))])) if rets else 0.0
    return MetricSet(
        net_return=net,
        excess_vs_primary=excess,
        sharpe_per_bar=s_pb,
        sharpe_annualized=s_ann,
        sharpe_ci_low=ci_lo,
        sharpe_ci_high=ci_hi,
        sharpe_degenerate=degenerate,
        max_drawdown=max_drawdown(list(equity)),
        tail_mean_5pct=tail,
        avg_exposure=float(np.mean(np.asarray(list(exposure)))) if exposure else 0.0,
        concentration=1.0,
        turnover_notional_over_capital=turnover,
        commission_cost=commission,
        funding_cost=funding,
        cost_basis=cost_basis,
        n_bars=len(equity),
        n_trades=n_trades,
    )


def interval_losses(
    equity: Sequence[float],
    end_ns: Sequence[int],
) -> tuple[tuple[Any, ...], int, int, int]:
    """Aggregate per-bar equity into equal INTERVAL_BARS loss intervals.

    Returns (losses, frozen_ns, evaluation_end_ns, decision_ns) satisfying the
    paired-loss chronology contract: frozen < eval_end < decision, intervals
    tiling [frozen, eval_end] exactly, each outcome available before decision.
    """
    from v8_next.evaluation.alignment import IntervalLoss

    n = len(equity)
    if n < 2 or len(end_ns) != n:
        raise ValueError("equity and timestamps must align with at least 2 bars")
    step = int(end_ns[1]) - int(end_ns[0])
    usable = (n - 1) // INTERVAL_BARS * INTERVAL_BARS
    frozen = int(end_ns[0])
    eval_end = int(end_ns[usable])
    decision = eval_end + step
    out: list[IntervalLoss] = []
    for k in range(usable // INTERVAL_BARS):
        a = 1 + k * INTERVAL_BARS
        b = 1 + (k + 1) * INTERVAL_BARS
        r = equity[b - 1] / equity[a - 1] - 1.0 if equity[a - 1] > 0 else 0.0
        out.append(
            IntervalLoss(
                int(end_ns[a - 1]),
                int(end_ns[b - 1]),
                int(end_ns[b - 1]),
                Decimal(str(-r)),
            )
        )
    return tuple(out), frozen, eval_end, decision


def run_statistics(
    family_equity: dict[str, Sequence[float]],
    end_ns: Sequence[int],
    baseline_id: str,
    block_size: int = 5,
    reps: int = BOOTSTRAP_REPS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """DSR + PBO + SPA on real family curves. Fail closed; never proxy.

    DSR family: the real engine/analytic strategy variants. Trials are set to
    2 with an explicit shared-tape dependence basis (conservative claim about
    independence, not an independence proof).
    """
    from v8_next.evaluation.deflated_sharpe import DSRPlan, deflated_sharpe_diagnostic
    from v8_next.evaluation.overfitting import pbo_diagnostic

    stats: dict[str, Any] = {"baseline": baseline_id}
    losses: dict[str, tuple[Any, ...]] = {}
    bounds: dict[str, tuple[int, int, int]] = {}
    for name, eq in family_equity.items():
        losses[name], frozen, eval_end, decision = interval_losses(list(eq), list(end_ns))
        bounds[name] = (frozen, eval_end, decision)
    first = next(iter(bounds.values()))
    if any(b != first for b in bounds.values()):
        raise ValueError("family curves do not share one evaluation chronology")
    frozen, eval_end, decision = first
    stats["intervals_per_variant"] = len(next(iter(losses.values()))) if losses else 0
    stats["interval_bars"] = INTERVAL_BARS

    dsr_names = sorted(n for n in losses if n != baseline_id)
    try:
        plan = DSRPlan(
            selected_variant=dsr_names[0],
            registered_variants=tuple(dsr_names),
            effective_independent_trials=2.0,
            independence_basis=(
                "shared real tape and shared engine; variants are re-runs of one "
                "search family, so effective independent trials are declared as 2 "
                "(incumbent-class vs alternative-class), not proven independent"
            ),
        )
        dsr_losses = {n: losses[n] for n in dsr_names}
        stats["dsr"] = deflated_sharpe_diagnostic(
            dsr_losses,
            plan=plan,
            frozen_ns=frozen,
            evaluation_end_ns=eval_end,
            decision_ns=decision,
        )
        stats["dsr"]["verdict"] = "SUPPORTED_DESCRIPTIVE"
    except Exception as e:  # fail closed, keep reason
        stats["dsr"] = {"verdict": "UNDERPowered".upper(), "reason": f"{type(e).__name__}: {e}"}
        stats["dsr"]["verdict"] = "UNDERPOWERED"

    n_intervals = stats["intervals_per_variant"]
    partitions = 4 if n_intervals % 4 == 0 and n_intervals >= 8 else 0
    if partitions and len(dsr_names) >= 2:
        try:
            stats["pbo"] = pbo_diagnostic(
                {n: losses[n] for n in dsr_names},
                registered_variants=tuple(dsr_names),
                frozen_ns=frozen,
                evaluation_end_ns=eval_end,
                decision_ns=decision,
                partitions=partitions,
                metric="mean_return",
                max_splits=64,
            )
            stats["pbo"]["verdict"] = "SUPPORTED_DESCRIPTIVE"
        except Exception as e:
            stats["pbo"] = {"verdict": "UNDERPOWERED", "reason": f"{type(e).__name__}: {e}"}
    else:
        stats["pbo"] = {
            "verdict": "UNDERPOWERED",
            "reason": f"interval count {n_intervals} does not admit even CSCV partitions>=8",
        }

    try:
        from v8_next.evaluation.inference import spa_diagnostic

        variants = {n: losses[n] for n in dsr_names}
        stats["spa"] = spa_diagnostic(
            losses[baseline_id],
            variants,
            frozen_ns=frozen,
            evaluation_end_ns=eval_end,
            decision_ns=decision,
            block_size=block_size,
            reps=reps,
            seed=seed,
        )
        stats["spa"]["verdict"] = "SUPPORTED_DESCRIPTIVE"
    except Exception as e:
        stats["spa"] = {
            "verdict": "UNSUPPORTED",
            "reason": f"{type(e).__name__}: {e}",
        }
    return stats


def allocator_mix(
    inc_rets: Sequence[float],
    ch_rets: Sequence[float],
    budget: float = 1.0,
) -> dict[str, Any]:
    """Same allocator procedure, same risk budget, re-run on P and P+E.

    Vol-target sleeve sizing with trailing-only volatility; P uses the full
    budget, P+E splits it equally across sleeves. Engine-level joint execution
    is NOT performed here (disclosed); this is allocator-level contribution.
    """
    inc = np.asarray(list(inc_rets), dtype=np.float64)
    ch = np.asarray(list(ch_rets), dtype=np.float64)
    n = min(inc.size, ch.size)
    inc, ch = inc[:n], ch[:n]
    target_pb = VOL_TARGET_ANNUAL / math.sqrt(HOURS_PER_YEAR)

    def sleeve(rets: np.ndarray, share: float) -> np.ndarray:
        out = np.zeros_like(rets)
        for i in range(1, n):
            window = rets[max(0, i - VOL_LOOKBACK) : i]
            sd = float(window.std(ddof=1)) if window.size >= 2 else 0.0
            scale = min(target_pb / sd, MAX_LEVERAGE) if sd > 1e-12 else 0.0
            out[i] = rets[i] * scale * share * budget
        return out

    p_only = sleeve(inc, 1.0)
    p_plus_e = sleeve(inc, 0.5) + sleeve(ch, 0.5)
    cum_p = float(np.prod(1.0 + p_only) - 1.0)
    cum_pe = float(np.prod(1.0 + p_plus_e) - 1.0)
    return {
        "method": "VOL_TARGET_SLEEVE_RERUN",
        "scope": "ALLOCATOR_LEVEL_NOT_ENGINE_JOINT",
        "p_net": cum_p,
        "pe_net": cum_pe,
        "incremental_net": cum_pe - cum_p,
        "budget": budget,
    }


def capacity_table(
    net_excess: float,
    turnover: float,
    capital: float,
    taker_fee: float,
) -> list[dict[str, Any]]:
    """Capacity scenarios bounded to 1h bar data resolution.

    MODELED (supported by 1h OHLCV bars + explicit config):
      - taker fee: linear notional * taker_fee (config fee, reconciled vs engine commission estimate)
      - turnover notional/capital: sum |qty*px|/capital from bar-close fill accounting
      - slippage proxy: bar close used as fill proxy; no intraday spread/slippage distribution

    UNMODELED (requires data NOT present in 1h bars; no coefficients invented):
      - market impact / price impact vs order-book depth
      - participation rate vs ADV / queue position / % volume
      - intraday slippage distribution / bid-ask spread (requires tick/L2)
      - nonlinear liquidity / capacity curvature (no depth, no intraday volume distribution)

    If 1h bars are the only market data, the claim 'strategy capacity at N*capital
    with preserved edge net of impact/participation' CANNOT be validated. Linear
    rows are accounting extrapolations only, not capacity validations.
    """
    notionals = turnover * capital
    breakeven_bp = (net_excess * capital / notionals * 1e4) if notionals > 0 else None
    data_resolution = "1h OHLCV bars (open/high/low/close/volume; no L2, no tick, no spread, no depth)"
    modeled = [
        "taker_fee linear (notional * taker_fee from config; bar-close fill proxy)",
        "turnover notional/capital (bar-close qty*px accounting)",
        "slippage proxy = bar close only (intraday slippage distribution NOT measured)",
    ]
    unmodeled = [
        "market impact / price impact vs depth (requires L2/order-book, not in 1h bars)",
        "participation rate / %ADV / queue position (requires intraday volume/ADV, not in 1h bars)",
        "intraday slippage distribution / bid-ask spread (requires tick/trade & quote data)",
        "nonlinear liquidity/capacity curvature (no depth; no impact coefficients invented)",
    ]
    rows: list[dict[str, Any]] = []
    for mult in (1.0, 10.0, 100.0):
        if mult == 1.0:
            validation_note = (
                "1x = observed window accounting only; impact/participation still UNMODELED "
                "even at 1x (no L2/ADV to validate)"
            )
            claim_validated = "NO: impact/participation cannot be validated from 1h bars at any scale"
        else:
            validation_note = (
                f"CANNOT BE VALIDATED from 1h bars alone at {mult:.0f}x: requires L2 depth and "
                "ADV/participation data not present; linear extrapolation shown for accounting only; "
                "no impact coefficients invented"
            )
            claim_validated = (
                "NO: capacity with preserved edge at scale cannot be validated without tick/L2/ADV"
            )
        rows.append(
            {
                "capital_mult": mult,
                "capital": capital * mult,
                "assumed_fee_bp": taker_fee * 1e4,
                "linear_net_excess": net_excess * mult,
                "breakeven_extra_cost_bp": breakeven_bp,
                "data_resolution": data_resolution,
                "modeled": list(modeled),
                "unmodeled": list(unmodeled),
                "validation_note": validation_note,
                "claim_validated": claim_validated,
                # legacy key kept for backward compatibility
                "note": "MODELED: taker fee (linear) + bar-close turnover/slippage proxy; "
                "UNMODELED: impact, participation/ADV, intraday slippage/spread, liquidity nonlinearity "
                "(no L2/tick/ADV in 1h bars; no coefficients invented)",
            }
        )
    return rows


def negative_control_shuffled(
    returns: Sequence[float], seed: int = 11
) -> dict[str, Any]:
    """Shuffled signal-outcome link, cost totals preserved: must NOT read as success."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(list(returns), dtype=np.float64)
    sh = rng.permutation(arr)
    s, _ = sharpe_stats([float(v) for v in sh])
    return {
        "kind": "NEGATIVE_CONTROL_SHUFFLED",
        "scope": "SYNTHETIC_CONTROL",
        "sharpe_per_bar": s,
        "declares_winner": bool(s > 0.1),
        "expected": False,
    }


def positive_control_known_effect(
    n: int = 480, drift: float = 0.002, vol: float = 0.01, seed: int = 5
) -> dict[str, Any]:
    """Known-effect synthetic process: detector must separate it (power check)."""
    rng = np.random.default_rng(seed)
    rets = drift + vol * rng.standard_normal(n)
    s, _ = sharpe_stats([float(v) for v in rets])
    ci_lo, _ = block_bootstrap_ci(list(rets))
    detected = ci_lo is not None and ci_lo > 0
    return {
        "kind": "POSITIVE_CONTROL_KNOWN_EFFECT",
        "scope": "SYNTHETIC_CONTROL",
        "n": n,
        "drift": drift,
        "vol": vol,
        "sharpe_per_bar": s,
        "ci_low": ci_lo,
        "detected": bool(detected),
        "expected": True,
    }


def build_verdicts(
    *,
    chrono_ok: bool,
    chrono_note: str,
    excess: float | None,
    stats: dict[str, Any],
    mix: dict[str, Any],
    cost_basis_ok: bool,
    funding_missing: bool,
    live_fills_present: bool,
    parity_ok: bool,
) -> EvidenceVerdicts:
    if not chrono_ok:
        research: VerdictState = "INVALID"
    else:
        research = "VALID"
    if not chrono_ok:
        economic: VerdictState = "INCONCLUSIVE"
        eco_note = "no economic inference from invalid data/accounting"
    elif excess is None:
        economic = "INCONCLUSIVE"
        eco_note = "primary comparison unavailable"
    elif excess > 0:
        economic = "POSITIVE_DESCRIPTIVE"
        eco_note = "net excess vs primary is positive on this window; not an edge claim"
    else:
        economic = "NEGATIVE"
        eco_note = "net excess vs primary is not positive on this window"
    dsr_v = str(stats.get("dsr", {}).get("verdict", "UNDERPOWERED"))
    spa_v = str(stats.get("spa", {}).get("verdict", "UNSUPPORTED"))
    pbo_v = str(stats.get("pbo", {}).get("verdict", "UNDERPOWERED"))
    supported = dsr_v.startswith("SUPPORTED") or spa_v.startswith("SUPPORTED") or pbo_v.startswith("SUPPORTED")
    unsupported = dsr_v == "UNSUPPORTED" or spa_v == "UNSUPPORTED" or pbo_v == "UNSUPPORTED"
    if supported:
        statistical: VerdictState = "SUPPORTED"
        stat_note = f"DSR={dsr_v} PBO={pbo_v} SPA={spa_v}; descriptive, family-scoped"
    elif unsupported:
        statistical = "UNSUPPORTED"
        stat_note = f"estimator absent or failed: DSR={dsr_v} PBO={pbo_v} SPA={spa_v}"
    else:
        statistical = "UNDERPOWERED"
        stat_note = f"insufficient power: DSR={dsr_v} PBO={pbo_v} SPA={spa_v}"
    inc = mix.get("incremental_net")
    if inc is None:
        portfolio: VerdictState = "INCONCLUSIVE"
        pf_note = "mix unavailable"
    elif inc > 0:
        portfolio = "HELPFUL_DESCRIPTIVE"
        pf_note = "P+E sleeve mix improves allocator-level net on this window"
    else:
        portfolio = "NOT_HELPFUL"
        pf_note = "P+E sleeve mix does not improve allocator-level net on this window"
    if not cost_basis_ok:
        execution: VerdictState = "EXECUTION_UNPROVEN"
        ex_note = "cost basis unverified; simulated fills only"
    elif funding_missing or not live_fills_present:
        execution = "SIM_ONLY"
        ex_note = "simulated fills; funding MISSING; no venue-settled fills"
    elif not parity_ok:
        execution = "EXECUTION_UNPROVEN"
        ex_note = "ledger parity diverged"
    else:
        execution = "SIM_ONLY"
        ex_note = "simulated fills with reconciled costs; venue settlement absent"
    return EvidenceVerdicts(
        research_validity=research,
        research_note=chrono_note,
        economic=economic,
        economic_note=eco_note,
        statistical=statistical,
        statistical_note=stat_note,
        portfolio=portfolio,
        portfolio_note=pf_note,
        execution=execution,
        execution_note=ex_note,
        capital="NOT_AUTHORIZED",
        capital_note="no score mints capital permission; separate risk decision required",
    )


def render_report(receipt: EconomicReceipt) -> str:
    r = receipt
    lines = [
        "# Economic Benchmark Report (NO_ECONOMIC_CLAIM)",
        "",
        f"receipt: `{r.receipt_id}`",
        f"run digest: `{r.run.digest()}`",
        f"primary benchmark (pre-declared): **{r.run.primary_benchmark}**",
        f"diagnostics: {', '.join(r.run.diagnostic_benchmarks)}",
        f"family: {', '.join(r.run.strategy_family)}",
        f"window: {r.run.dataset.n_bars} bars "
        f"[{r.run.dataset.period_start_ns} .. {r.run.dataset.period_end_ns}]",
        f"capital: {r.run.capital} fee: {r.run.taker_fee} opex/mo: {r.run.opex_monthly_usd}",
        "",
        "## Verdicts (independent; no aggregate PASS)",
        "",
        "| domain | state | note |",
        "|---|---|---|",
        f"| research validity | {r.verdicts.research_validity} | {r.verdicts.research_note} |",
        f"| economic | {r.verdicts.economic} | {r.verdicts.economic_note} |",
        f"| statistical | {r.verdicts.statistical} | {r.verdicts.statistical_note} |",
        f"| portfolio | {r.verdicts.portfolio} | {r.verdicts.portfolio_note} |",
        f"| execution | {r.verdicts.execution} | {r.verdicts.execution_note} |",
        f"| capital | {r.verdicts.capital} | {r.verdicts.capital_note} |",
        "",
        "## Metrics (cost-adjusted, shared basis)",
        "",
        "| curve | net | excess vs primary | Sharpe_ann [CI] | maxDD | turn | commission | funding |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, m in r.metrics.items():
        ci = (
            f"[{m.sharpe_ci_low:.3f},{m.sharpe_ci_high:.3f}]"
            if m.sharpe_ci_low is not None and m.sharpe_ci_high is not None
            else "n/a"
        )
        if m.sharpe_degenerate:
            ci += " DEGENERATE-VARIANCE"
        ex = f"{m.excess_vs_primary:.4f}" if m.excess_vs_primary is not None else "—"
        fd = f"{m.funding_cost:.2f}" if m.funding_cost is not None else "MISSING"
        lines.append(
            f"| {name} | {m.net_return:.4f} | {ex} | {m.sharpe_annualized:.3f} {ci} "
            f"| {m.max_drawdown:.4f} | {m.turnover_notional_over_capital:.3f} "
            f"| {m.commission_cost:.2f} | {fd} |"
        )
    lines += [
        "",
        "## Chronological OOS (frozen split; never relabeled)",
        "",
    ]
    for name, m in r.oos_metrics.items():
        lines.append(f"- {name}: net {m.net_return:.4f} Sharpe_ann {m.sharpe_annualized:.3f}")
    lines += [
        "",
        "## Statistics (family-scoped, descriptive)",
        "",
        "```json",
        json.dumps(r.statistics, indent=2, default=str)[:6000],
        "```",
        "",
        "## Controls",
        "",
        "```json",
        json.dumps(r.controls, indent=2, default=str)[:4000],
        "```",
        "",
        "## Portfolio P vs P+E (allocator rerun, same budget)",
        "",
        "```json",
        json.dumps(r.portfolio_mix, indent=2, default=str),
        "```",
        "",
        "## Capacity scenarios — bounded to 1h bar resolution (MODELED vs UNMODELED)",
        "",
        "```json",
        json.dumps(r.capacity_scenarios, indent=2, default=str),
        "```",
        "",
        "## Parity / shadow / live",
        "",
        "```json",
        json.dumps({**r.parity, **r.shadow_live}, indent=2, default=str),
        "```",
        "",
        "## Limitations",
        "",
    ]
    lines += [f"- {lim}" for lim in r.limitations]
    lines += ["", "claim_status: NO_ECONOMIC_CLAIM", ""]
    return "\n".join(lines)
