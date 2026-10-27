#!/usr/bin/env python
"""Trend + funding-carry + cross-sectional momentum edge study on Binance UM perpetuals.

Builds a daily panel from Binance Vision monthly 1h kline and fundingRate archives
(SHA-256 verified against the published ``.CHECKSUM``), runs the full registered search
family that was explored, and reports the selected portfolio
(``v8_next.economics.trend_carry``) with:

* annualised Sharpe with Lo (2002) standard error and a circular-block bootstrap CI;
* in-sample (2020-2023) vs. post-design (2024+) split, per-year and per-month results;
* cost x2 / x3 and one-extra-day execution-lag stress;
* Deflated Sharpe (``deflated_sharpe_diagnostic``) over the whole registered family,
  CSCV probability of backtest overfitting (``pbo_diagnostic``) and White's reality
  check vs. flat (``reality_check_diagnostic``);
* BTC beta.

The universe is 20 large perpetuals chosen with present-day knowledge (survivorship
bias is a declared limitation). Funding is real settlement data; fees+slippage are a
declared per-unit-turnover assumption; fills are at the daily close. Nothing here is an
economic claim (Rule 12): it is a diagnostic over real public bars.

Usage (repository root):

    uv run --project v8-next --extra dev --extra research \\
        python v8-next/tools/nx_trend_carry_edge.py --download
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from v8_next.economics import trend_carry as tc
from v8_next.evaluation.alignment import IntervalLoss
from v8_next.evaluation.deflated_sharpe import DSRPlan, deflated_sharpe_diagnostic
from v8_next.evaluation.overfitting import pbo_diagnostic
from v8_next.evaluation.reality_check import reality_check_diagnostic

ROOT = Path(__file__).resolve().parents[2]
VISION = "https://data.binance.vision/data/futures/um/monthly"
UNIVERSE = (
    "BTCUSDT ETHUSDT BNBUSDT XRPUSDT ADAUSDT SOLUSDT DOGEUSDT LTCUSDT LINKUSDT DOTUSDT "
    "AVAXUSDT TRXUSDT BCHUSDT ETCUSDT XLMUSDT ATOMUSDT UNIUSDT FILUSDT AAVEUSDT NEARUSDT"
).split()
DAY_MS = 86_400_000
DAY_NS = DAY_MS * 1_000_000
IS_END = "2024-01-01"
SELECTED = "portfolio_trend_carry_xsmom"


def _months(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _fetch(url: str, dest: Path) -> str:
    if dest.exists():
        return "cached"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            blob = resp.read()
        with urllib.request.urlopen(url + ".CHECKSUM", timeout=60) as resp:
            expected = resp.read().decode().split()[0]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "absent"
        raise
    if hashlib.sha256(blob).hexdigest() != expected:
        raise ValueError(f"checksum mismatch for {url}")
    dest.write_bytes(blob)
    return "downloaded"


def download(raw: Path, first: str, last: str) -> dict[str, int]:
    raw.mkdir(parents=True, exist_ok=True)
    jobs = []
    for sym in UNIVERSE:
        for mo in _months(first, last):
            jobs.append((f"{VISION}/klines/{sym}/1h/{sym}-1h-{mo}.zip", raw / f"{sym}-1h-{mo}.zip"))
            jobs.append(
                (
                    f"{VISION}/fundingRate/{sym}/{sym}-fundingRate-{mo}.zip",
                    raw / f"{sym}-fundingRate-{mo}.zip",
                )
            )
    with ThreadPoolExecutor(16) as pool:
        results = list(pool.map(lambda j: _fetch(*j), jobs))
    return {k: results.count(k) for k in sorted(set(results))}


def _rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as z:
        text = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8").read()
    lines = text.strip().splitlines()
    if lines and not lines[0][:1].isdigit():
        lines = lines[1:]
    return [line.split(",") for line in lines]


def build_panel(raw: Path) -> tuple[tc.Panel, dict[str, Any]]:
    close: dict[str, dict[int, tuple[int, float]]] = {s: {} for s in UNIVERSE}
    funding: dict[str, dict[int, float]] = {s: {} for s in UNIVERSE}
    seen_funding: dict[str, set[int]] = {s: set() for s in UNIVERSE}
    digest = hashlib.sha256()
    files = sorted(raw.glob("*.zip"))
    for path in files:
        digest.update(path.name.encode() + hashlib.sha256(path.read_bytes()).digest())
        sym = path.name.split("-")[0]
        if sym not in close:
            continue
        if "-1h-" in path.name:
            for r in _rows(path):
                t = int(r[0])
                day = t // DAY_MS
                prev = close[sym].get(day)
                if prev is None or t > prev[0]:
                    close[sym][day] = (t, float(r[4]))
        else:
            for r in _rows(path):
                t = int(r[0])
                if t in seen_funding[sym]:
                    continue
                seen_funding[sym].add(t)
                funding[sym][t // DAY_MS] = funding[sym].get(t // DAY_MS, 0.0) + float(r[2])
    all_days = [d for s in UNIVERSE for d in close[s]]
    days = np.arange(min(all_days), max(all_days) + 1, dtype=np.int64)
    c = np.full((len(days), len(UNIVERSE)), np.nan)
    f = np.zeros_like(c)
    for j, sym in enumerate(UNIVERSE):
        for d, (_, px) in close[sym].items():
            c[d - days[0], j] = px
        for d, rate in funding[sym].items():
            if days[0] <= d <= days[-1]:
                f[d - days[0], j] = rate
    panel = tc.Panel(days * DAY_NS, tuple(UNIVERSE), c, f)
    meta = {
        "archives": len(files),
        "archive_set_sha256": digest.hexdigest(),
        "first_day": str(np.datetime64(int(days[0]) * DAY_MS, "ms"))[:10],
        "last_day": str(np.datetime64(int(days[-1]) * DAY_MS, "ms"))[:10],
        "days": len(days),
        "funding_settlements": sum(len(v) for v in seen_funding.values()),
    }
    return panel, meta


def registered_family(panel: tc.Panel, ins: np.ndarray, cost: float) -> dict[str, np.ndarray]:
    """Every variant explored while designing the study (search lineage, not a menu)."""
    valid, vol = panel.valid, tc.ewm_vol(panel.returns)

    def vs(sig: np.ndarray) -> np.ndarray:
        return tc.vol_scale(sig, vol, valid)

    def net(w: np.ndarray) -> np.ndarray:
        return tc.simulate(panel, w, cost_per_turnover=cost).net

    def unit(w: np.ndarray) -> np.ndarray:
        sd = net(w)[ins].std() * np.sqrt(tc.DAYS_PER_YEAR)
        return w * tc.SLEEVE_TARGET_VOL / sd

    family: dict[str, np.ndarray] = {}
    for lb in (10, 20, 60, 120):
        family[f"tsmom_ls_lb{lb}"] = net(vs(np.sign(tc.trailing_return(panel.close, lb))))
    trend = tc.trend_weights(panel)
    votes = np.stack([np.sign(tc.trailing_return(panel.close, lb)) for lb in tc.TREND_LOOKBACKS])
    counted = np.isfinite(votes).sum(axis=0)
    ens = np.where(counted > 0, np.nansum(votes, axis=0) / counted.clip(1), np.nan)
    trend_long = vs(np.clip(ens, 0, None))
    family["tsmom_ens_ls"] = net(trend)
    family["tsmom_ens_long"] = net(trend_long)
    family["buy_hold_volscaled"] = net(vs(np.ones_like(panel.close)))
    for lb in (7, 14, 30, 60):
        family[f"xsmom_lb{lb}"] = net(vs(tc.xs_rank(tc.trailing_return(panel.close, lb), valid)))
    for lb in (1, 3):
        family[f"xsrev_lb{lb}"] = net(vs(-tc.xs_rank(tc.trailing_return(panel.close, lb), valid)))
    carry_daily = None
    for lb in (3, 7, 14, 30):
        sig = vs(-tc.xs_rank(tc.trailing_mean(panel.funding, lb), valid))
        if lb == 7:
            carry_daily = sig
        for rb in (1, 3, 7, 14):
            family[f"carry_lb{lb}_rb{rb}"] = net(tc.hold(sig, rb))
    assert carry_daily is not None
    carry = tc.carry_weights(panel)
    family["portfolio_trend_carry"] = net((unit(trend) + unit(carry)) / 2)
    family["portfolio_trendlong_carry"] = net((unit(trend_long) + unit(carry)) / 2)
    family["portfolio_trendlong_carrydaily"] = net((unit(trend_long) + unit(carry_daily)) / 2)
    family[SELECTED] = net(tc.portfolio_weights(panel, ins, cost_per_turnover=cost)[0])
    return family


def _losses(panel: tc.Panel, daily: np.ndarray, mask: np.ndarray) -> tuple[IntervalLoss, ...]:
    starts = panel.day_ns[mask]
    return tuple(
        IntervalLoss(int(s), int(s + DAY_NS), int(s + DAY_NS), Decimal(repr(-float(x))))
        for s, x in zip(starts, daily[mask], strict=True)
    )


def _bootstrap_sharpe_ci(daily: np.ndarray, block: int, reps: int, seed: int) -> list[float]:
    arch = __import__("arch.bootstrap", fromlist=["CircularBlockBootstrap"])
    bs = arch.CircularBlockBootstrap(block, daily, seed=seed)
    draws = [x.mean() / x.std(ddof=1) * np.sqrt(tc.DAYS_PER_YEAR) for (x,), _ in bs.bootstrap(reps)]
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, Decimal):
        return str(x)
    return x


def run(raw: Path, cost: float) -> dict[str, Any]:
    panel, meta = build_panel(raw)
    years = (panel.day_ns // DAY_NS).astype("datetime64[D]").astype("datetime64[Y]").astype(int)
    years = years + 1970
    split_day = np.datetime64(IS_END).astype("datetime64[D]").astype(np.int64)
    ins = (panel.day_ns // DAY_NS) < split_day
    oos = ~ins
    weights, scales = tc.portfolio_weights(panel, ins, cost_per_turnover=cost)

    def sim(w: np.ndarray, c: float = cost, lag: int = 1) -> tc.Simulation:
        return tc.simulate(panel, w, cost_per_turnover=c, lag=lag)

    base = sim(weights)
    # drop the warm-up before any sleeve can trade
    live = np.cumsum(np.abs(base.held).sum(axis=1) > 0) > 0
    window = live & np.isfinite(base.net)
    net = base.net
    btc = np.nan_to_num(panel.returns[:, panel.instruments.index("BTCUSDT")])
    beta = float(np.polyfit(btc[window], net[window], 1)[0])
    months = (panel.day_ns // DAY_NS).astype("datetime64[D]").astype("datetime64[M]")
    month_ret = {
        str(m): float(np.prod(1 + net[window & (months == m)]) - 1)
        for m in np.unique(months[window])
    }

    sleeves = {}
    for name in tc.SLEEVES:
        s = sim(tc.SLEEVES[name](panel) * scales[name])
        sleeves[name] = {
            "in_sample": tc.summary(s.net[window & ins]),
            "post_design": tc.summary(s.net[window & oos]),
        }
    sleeve_nets = np.column_stack(
        [sim(tc.SLEEVES[n](panel) * scales[n]).net[window] for n in tc.SLEEVES]
    )

    report: dict[str, Any] = {
        "study": "trend_carry_xsmom_v1",
        "claim_status": "NO_ECONOMIC_CLAIM",
        "data": meta | {"universe": list(panel.instruments)},
        "assumptions": {
            "cost_per_unit_turnover": cost,
            "cost_basis": "declared: 5 bp taker fee + 2 bp slippage per unit notional traded",
            "fills": "daily UTC close of decision day; one-day lag stress reported",
            "funding": "real Vision settlement rates; long pays positive funding",
            "accounting": "simulated daily portfolio return on constant capital; not venue cash",
            "in_sample_end": IS_END,
            "sleeve_vol_scales_from_in_sample_only": scales,
        },
        "parameters": {
            "trend_lookbacks": tc.TREND_LOOKBACKS,
            "carry_lookback": tc.CARRY_LOOKBACK,
            "carry_rebalance_days": tc.CARRY_REBALANCE_DAYS,
            "xs_momentum_lookback": tc.XS_MOMENTUM_LOOKBACK,
            "vol_span": tc.VOL_SPAN,
            "sleeve_target_vol": tc.SLEEVE_TARGET_VOL,
        },
        "portfolio": {
            "full": tc.summary(net[window]),
            "in_sample": tc.summary(net[window & ins]),
            "post_design": tc.summary(net[window & oos]),
            "bootstrap_sharpe_ci95_full": _bootstrap_sharpe_ci(net[window], 20, 2000, 7),
            "bootstrap_sharpe_ci95_post_design": _bootstrap_sharpe_ci(
                net[window & oos], 20, 2000, 7
            ),
            "by_year": {
                int(y): tc.summary(net[window & (years == y)]) for y in np.unique(years[window])
            },
            "positive_months": sum(v > 0 for v in month_ret.values()),
            "months": len(month_ret),
            "monthly_returns": month_ret,
            "btc_beta": beta,
            "mean_daily_turnover": float(base.turnover[window].mean()),
            "annual_components": {
                "gross_price": float(base.gross[window].mean() * tc.DAYS_PER_YEAR),
                "funding": float(base.funding[window].mean() * tc.DAYS_PER_YEAR),
                "cost": float(-base.cost[window].mean() * tc.DAYS_PER_YEAR),
            },
        },
        "sleeves": sleeves,
        "sleeve_correlation": np.corrcoef(sleeve_nets.T).round(3).tolist(),
        "stress": {
            "cost_x2": tc.summary(sim(weights, 2 * cost).net[window]),
            "cost_x3": tc.summary(sim(weights, 3 * cost).net[window]),
            "lag_2_days": tc.summary(sim(weights, lag=2).net[window]),
            "cost_x2_post_design": tc.summary(sim(weights, 2 * cost).net[window & oos]),
        },
    }

    family = registered_family(panel, ins, cost)
    report["family"] = {
        name: {
            "full_sharpe": tc.summary(x[window])["sharpe_annualised"],
            "in_sample_sharpe": tc.summary(x[window & ins])["sharpe_annualised"],
            "post_design_sharpe": tc.summary(x[window & oos])["sharpe_annualised"],
        }
        for name, x in sorted(family.items())
    }
    names = tuple(sorted(family))
    is_best = max(names, key=lambda n: report["family"][n]["in_sample_sharpe"])
    report["in_sample_best"] = {
        "variant": is_best,
        "by_year": {
            int(y): tc.summary(family[is_best][window & (years == y)])
            for y in np.unique(years[window])
        },
        "btc_beta": float(np.polyfit(btc[window], family[is_best][window], 1)[0]),
    }
    # The reversal variants are sign flips of the momentum bets; their large negative
    # Sharpe inflates the cross-trial variance. Both readings are published.
    family_sets = {
        "all": names,
        "excluding_sign_mirrors": tuple(n for n in names if not n.startswith("xsrev_")),
    }
    statistics: dict[str, Any] = {}
    for label, mask in (("full", window), ("post_design", window & oos)):
        losses = {n: _losses(panel, family[n], mask) for n in names}
        start = int(panel.day_ns[mask][0])
        end = int(panel.day_ns[mask][-1] + DAY_NS)
        bounds = dict(frozen_ns=start, evaluation_end_ns=end, decision_ns=end + 1)
        for selected in (SELECTED, is_best):
            for set_name, members in family_sets.items():
                dsr = deflated_sharpe_diagnostic(
                    {n: losses[n] for n in members},
                    plan=DSRPlan(selected, members, float(len(members)), f"{set_name} counted"),
                    **bounds,
                )
                dsr.pop("multiple_testing", None)
                dsr.pop("dependency_versions", None)
                statistics[f"dsr_{label}_{selected}_{set_name}"] = dsr
        flat = tuple(
            IntervalLoss(r.start_ns, r.end_ns, r.available_ns, Decimal(0)) for r in losses[SELECTED]
        )
        rc = reality_check_diagnostic(
            flat, losses, block_size=20, reps=2000, seed=11, bootstrap="stationary", **bounds
        )
        statistics[f"reality_check_{label}"] = {
            k: rc[k] for k in rc if k in ("method", "p_value", "observed_max_mean", "reps")
        }
    n_full = int(window.sum())
    keep = n_full - n_full % 10
    trimmed = {n: _losses(panel, family[n], window)[-keep:] for n in names}
    t0 = trimmed[names[0]][0].start_ns
    t1 = trimmed[names[0]][-1].end_ns
    pbo = pbo_diagnostic(
        trimmed,
        registered_variants=names,
        frozen_ns=t0,
        evaluation_end_ns=t1,
        decision_ns=t1 + 1,
        partitions=10,
        metric="sharpe",
        max_splits=252,
    )
    statistics["pbo"] = {k: pbo[k] for k in pbo if k not in ("splits",)}
    report["statistics"] = statistics
    return _jsonable(report)


def render_markdown(r: dict[str, Any]) -> str:
    p = r["portfolio"]

    def row(label: str, s: dict[str, float]) -> str:
        return (
            f"| {label} | {s['sharpe_annualised']:+.2f} ± {s['sharpe_se_annualised']:.2f} | "
            f"{s['mean_return_annualised']:+.1%} | {s['volatility_annualised']:.1%} | "
            f"{s['cagr']:+.1%} | {s['max_drawdown']:.1%} | {s['days']} |"
        )

    head = "| window | Sharpe ± SE | ann. return | vol | CAGR | max DD | days |\n|---|---|---|---|---|---|---|"
    lines = [
        "# Trend + funding-carry + XS-momentum study (NO_ECONOMIC_CLAIM)",
        "",
        f"Data: {r['data']['archives']} Binance Vision archives, {r['data']['first_day']} → "
        f"{r['data']['last_day']}, {len(r['data']['universe'])} UM perpetuals; archive-set "
        f"sha256 `{r['data']['archive_set_sha256'][:16]}…`.",
        "",
        head,
        row("full", p["full"]),
        row("in-sample 2020–2023", p["in_sample"]),
        row("post-design 2024+", p["post_design"]),
        *[row(str(y), s) for y, s in p["by_year"].items()],
        "",
        f"Bootstrap 95% CI of Sharpe (circular block 20d): full {p['bootstrap_sharpe_ci95_full']}, "
        f"post-design {p['bootstrap_sharpe_ci95_post_design']}.",
        f"Positive months: {p['positive_months']}/{p['months']}. BTC beta {p['btc_beta']:+.3f}. "
        f"Mean daily turnover {p['mean_daily_turnover']:.3f}.",
        f"Annual components: price {p['annual_components']['gross_price']:+.1%}, funding "
        f"{p['annual_components']['funding']:+.1%}, cost {p['annual_components']['cost']:+.1%}.",
        "",
        "## Stress",
        head,
        *[row(k, v) for k, v in r["stress"].items()],
        "",
        "## Sleeves",
        "| sleeve | IS Sharpe | post-design Sharpe |\n|---|---|---|",
        *[
            f"| {k} | {v['in_sample']['sharpe_annualised']:+.2f} | "
            f"{v['post_design']['sharpe_annualised']:+.2f} |"
            for k, v in r["sleeves"].items()
        ],
        f"\nSleeve correlation (trend, carry, xs_momentum): {r['sleeve_correlation']}",
        "",
        "## Multiple-testing diagnostics over the registered family",
        f"Family size {len(r['family'])} (every explored variant).",
    ]
    st = r["statistics"]
    best = r["in_sample_best"]["variant"]
    for key, d in st.items():
        if not key.startswith("dsr_"):
            continue
        lines.append(
            f"- DSR confidence `{key[4:]}`: {d['dsr_confidence']:.4f} (expected max null "
            f"annualised SR {d['expected_max_null_sharpe'] * np.sqrt(tc.DAYS_PER_YEAR):.2f}, "
            f"family {len(d['registered_variants'])})"
        )
    for label in ("full", "post_design"):
        lines.append(
            f"- White reality check p ({label}): {st[f'reality_check_{label}']['p_value']}"
        )
    lines.append(f"- CSCV PBO: {st['pbo'].get('pbo')}")
    lines += [
        "",
        f"## In-sample-best variant: `{best}` (BTC beta {r['in_sample_best']['btc_beta']:+.3f})",
        head,
        *[row(str(y), v) for y, v in r["in_sample_best"]["by_year"].items()],
        "",
        "## Family",
        "| variant | full SR | IS SR | post-design SR |\n|---|---|---|---|",
        *[
            f"| {k} | {v['full_sharpe']:+.2f} | {v['in_sample_sharpe']:+.2f} | "
            f"{v['post_design_sharpe']:+.2f} |"
            for k, v in r["family"].items()
        ],
        "",
        "## Limitations",
        "- Universe chosen with present-day knowledge (survivorship bias).",
        "- Fees/slippage are a declared assumption; fills at the daily close; no book data.",
        "- Post-design window was observed during design (not a sealed holdout).",
        "- Simulated constant-capital returns; not venue cash settlement. NO_ECONOMIC_CLAIM.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", type=Path, default=ROOT / "research/tape/vision-um-20/raw")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/trend-carry-edge")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--first-month", default="2020-01")
    ap.add_argument("--last-month", default="2026-09")
    ap.add_argument("--cost", type=float, default=0.0007)
    args = ap.parse_args(argv)
    if args.download:
        print(download(args.raw, args.first_month, args.last_month), file=sys.stderr)
    if not any(args.raw.glob("*.zip")):
        print(f"no archives under {args.raw}; pass --download", file=sys.stderr)
        return 2
    report = run(args.raw, args.cost)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (args.out / "REPORT.md").write_text(render_markdown(report))
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
