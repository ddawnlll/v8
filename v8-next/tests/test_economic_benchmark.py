"""Economic benchmark tests.

MECHANICS ONLY synthetic section: arithmetic/validator unit coverage with zero
evaluative weight. No test here asserts economic performance on synthetic data.

Evaluative section: real-tape BenchmarkCase via the economic fabric; skips when
the tape is absent. Synthetic candles are banned there.
"""

import json
import math
from pathlib import Path
from typing import Any

import pytest

from v8_next.evaluation import economic_benchmark as eb

# ---------------------------------------------------------------------------
# MECHANICS ONLY (synthetic fixtures, arithmetic/validator coverage)
# ---------------------------------------------------------------------------


def _synth_bars(n: int = 120, drift: float = 0.001, noise: float = 0.0, seed: int = 3) -> list[eb.BarView]:
    import numpy as np

    bars: list[eb.BarView] = []
    rng = np.random.default_rng(seed)
    px = 100.0
    shocks = rng.standard_normal(n) * noise
    for i in range(n):
        o = px
        c = px * (1.0 + drift + float(shocks[i]))
        bars.append(
            eb.BarView(
                end_ns=(i + 1) * 3_600_000_000_000,
                open=o,
                high=max(o, c) * 1.001,
                low=min(o, c) * 0.999,
                close=c,
            )
        )
        px = c
    return bars


def test_mechanics_cash_is_flat() -> None:
    bars = _synth_bars()
    fams = eb.compute_benchmark_family(bars, 10000.0, 0.0005)
    assert all(v == 10000.0 for v in fams["cash"]["equity"])
    assert fams["cash"]["turnover"] == 0.0


def test_mechanics_buy_hold_construction() -> None:
    bars = _synth_bars()
    fams = eb.compute_benchmark_family(bars, 10000.0, 0.0005)
    eq: list[float] = fams["btc_buy_hold"]["equity"]
    assert eq[0] == pytest.approx(10000.0 * (1.0 - 0.0005))
    assert eq[-1] / eq[0] == pytest.approx(bars[-1].close / bars[0].close)


def test_mechanics_vol_target_trailing_only() -> None:
    bars = _synth_bars(noise=0.004)
    fams = eb.compute_benchmark_family(bars, 10000.0, 0.0005)
    exp: list[float] = fams["vol_target"]["exposure"]
    assert exp[0] == 0.0  # no lookback yet: flat by construction
    assert any(e > 0 for e in exp[1:])


def test_mechanics_chronology_validator_catches_defects() -> None:
    bars = _synth_bars()
    ok, _ = eb.validate_chronology(bars)
    assert ok is True
    bad = list(bars)
    bad[5] = bars[4]  # duplicate timestamp
    ok2, note = eb.validate_chronology(bad)
    assert ok2 is False and "MONOTONIC" in note
    leak_ok, _ = eb.detect_future_leak(bars)
    assert leak_ok is True
    leak_bad, _ = eb.detect_future_leak(bars, closes_shift=1)
    assert leak_bad is False


def test_mechanics_controls_behave() -> None:
    pos = eb.positive_control_known_effect()
    assert pos["scope"] == "SYNTHETIC_CONTROL"
    assert pos["detected"] is True and pos["expected"] is True
    neg = eb.negative_control_shuffled([0.01, -0.01] * 200, seed=11)
    assert neg["scope"] == "SYNTHETIC_CONTROL"
    assert neg["declares_winner"] is False


def test_mechanics_metrics_and_capacity() -> None:
    bars = _synth_bars()
    fams = eb.compute_benchmark_family(bars, 10000.0, 0.0005)
    eq: list[float] = fams["btc_buy_hold"]["equity"]
    m = eb.metrics_for_curve(eq, fams["btc_buy_hold"]["exposure"], 1.0, 5.0, None, "ANALYTIC_MODEL", eq, 1)
    assert m.net_return > 0 and m.max_drawdown <= 0.0
    rows = eb.capacity_table(0.05, 2.0, 10000.0, 0.0005)
    assert rows[0]["breakeven_extra_cost_bp"] == pytest.approx(0.05 * 10000.0 / 20000.0 * 1e4)


def test_mechanics_degenerate_sharpe_flagged() -> None:
    flat = [10000.0] * 100
    flat[50] += 1.0  # single nonzero bar
    m = eb.metrics_for_curve(flat, [0.0] * 100, 0.0, 0.0, None, "ANALYTIC_MODEL", flat, 0)
    assert m.sharpe_degenerate is True
    noisy = list(10000.0 + float(i) % 7 - 3.0 for i in range(100))
    m2 = eb.metrics_for_curve(noisy, [1.0] * 100, 1.0, 5.0, None, "ANALYTIC_MODEL", noisy, 1)
    assert m2.sharpe_degenerate is False


def _mechanics_return_path(
    n: int = 500, drift: float = 0.0004, vol: float = 0.01, seed: int = 13
) -> list[float]:
    """MECHANICS ONLY: seeded per-bar returns with zero evaluative weight."""
    import numpy as np

    rng = np.random.default_rng(seed)
    return [float(v) for v in drift + vol * rng.standard_normal(n)]


def _mechanics_equity(rets: list[float], start: float = 10000.0) -> list[float]:
    """MECHANICS ONLY: compound a synthetic return path into an equity curve."""
    eq = [start]
    for r in rets:
        eq.append(eq[-1] * (1.0 + r))
    return eq


def test_mechanics_sharpe_ci_stored_annualized() -> None:
    """#388 acceptance (1): the STORED sharpe_ci_* are annualized.

    The block bootstrap resamples per-bar returns, so its percentiles are
    per-bar Sharpe values. Stored beside the annualized point estimate they must
    first be scaled by sqrt(HOURS_PER_YEAR); this ratio is 1.0 pre-fix.
    """
    eq = _mechanics_equity(_mechanics_return_path())
    m = eb.metrics_for_curve(eq, [1.0] * len(eq), 1.0, 5.0, None, "ANALYTIC_MODEL", eq, 1)
    # Exactly the array metrics_for_curve derived from `eq`: same bootstrap input.
    per_bar_lo, per_bar_hi = eb.block_bootstrap_ci(eb.per_bar_returns(eq))
    assert per_bar_lo is not None and per_bar_hi is not None
    root = math.sqrt(eb.HOURS_PER_YEAR)
    assert eb.SHARPE_ANNUALIZATION == pytest.approx(root, rel=1e-15)
    assert m.sharpe_ci_low is not None and m.sharpe_ci_high is not None
    assert m.sharpe_ci_low == pytest.approx(per_bar_lo * root, rel=1e-12)
    assert m.sharpe_ci_high == pytest.approx(per_bar_hi * root, rel=1e-12)
    assert m.sharpe_ci_low / per_bar_lo == pytest.approx(root, rel=1e-9)
    assert m.sharpe_ci_high / per_bar_hi == pytest.approx(root, rel=1e-9)
    assert m.sharpe_ci_low == pytest.approx(
        eb.sharpe_ci_annualized(eb.per_bar_returns(eq))[0], rel=1e-12
    )


def test_mechanics_sharpe_ci_brackets_its_own_point() -> None:
    """#388 acceptance (2): ci_low <= sharpe_annualized <= ci_high on sound rows."""
    eq = _mechanics_equity(_mechanics_return_path())
    m = eb.metrics_for_curve(eq, [1.0] * len(eq), 1.0, 5.0, None, "ANALYTIC_MODEL", eq, 1)
    assert m.sharpe_degenerate is False
    assert m.sharpe_ci_low is not None and m.sharpe_ci_high is not None
    assert m.sharpe_ci_low <= m.sharpe_annualized <= m.sharpe_ci_high
    # Discriminator: the per-bar interval (the pre-fix publication) cannot
    # contain an annualized point of this magnitude, so this pins the fix.
    per_bar_lo, per_bar_hi = eb.block_bootstrap_ci(eb.per_bar_returns(eq))
    assert per_bar_lo is not None and per_bar_hi is not None
    assert per_bar_hi < m.sharpe_annualized
    assert not (per_bar_lo <= m.sharpe_annualized <= per_bar_hi)


def _mechanics_oos_metric(*, degenerate: bool, sharpe_annualized: float) -> eb.MetricSet:
    """Render-path fixture: a metric row with an explicit degeneracy flag.

    MECHANICS ONLY. No evaluative weight: these are not measured returns.
    """
    return eb.MetricSet(
        net_return=0.0047,
        excess_vs_primary=-0.001,
        sharpe_per_bar=sharpe_annualized / (365.0 * 24.0) ** 0.5,
        sharpe_annualized=sharpe_annualized,
        sharpe_ci_low=None,
        sharpe_ci_high=None,
        sharpe_degenerate=degenerate,
        max_drawdown=-0.01,
        tail_mean_5pct=-0.001,
        avg_exposure=1.0,
        concentration=1.0,
        turnover_notional_over_capital=0.5,
        commission_cost=1.0,
        funding_cost=None,
        cost_basis="ANALYTIC_MODEL+OOS_SLICE",
        n_bars=150,
        n_trades=1,
    )


def _mechanics_receipt(metrics: dict[str, eb.MetricSet]) -> eb.EconomicReceipt:
    """Minimal render-only receipt (MECHANICS ONLY: no tape, no evaluative claim)."""
    run = eb.RunIdentity(
        dataset=eb.DatasetIdentity(
            tape_path="MECHANICS_ONLY",
            tape_sha256="0" * 64,
            universe=("MECHANICS_ONLY",),
            period_start_ns=0,
            period_end_ns=3_600_000_000_000,
            n_bars=500,
            source_hashes=(),
        ),
        code=eb.CodeIdentity(
            git_rev="0" * 40,
            git_dirty="no",
            config_sha256="0" * 64,
            estimator_versions={},
        ),
        seed=0,
        primary_benchmark="cash",
        diagnostic_benchmarks=(),
        strategy_family=("MECHANICS_ONLY",),
        capital=10000.0,
        taker_fee=0.0005,
        opex_monthly_usd=0.0,
    )
    verdicts = eb.EvidenceVerdicts(
        research_validity="INVALID",
        research_note="MECHANICS_ONLY",
        economic="NEGATIVE",
        economic_note="MECHANICS_ONLY",
        statistical="UNSUPPORTED",
        statistical_note="MECHANICS_ONLY",
        portfolio="NOT_HELPFUL",
        portfolio_note="MECHANICS_ONLY",
        execution="EXECUTION_UNPROVEN",
        execution_note="MECHANICS_ONLY",
        capital="NOT_AUTHORIZED",
        capital_note="MECHANICS_ONLY",
    )
    return eb.EconomicReceipt(
        receipt_id="mechanics-only",
        run=run,
        metrics=metrics,
        oos_metrics=metrics,
        verdicts=verdicts,
        statistics={},
        controls={},
        portfolio_mix={},
        capacity_scenarios=[],
        parity={},
        shadow_live={},
        limitations=[],
    )


def _render_section(report: str, heading: str, next_heading: str) -> str:
    return report.split(heading, 1)[1].split(next_heading, 1)[0]


def test_mechanics_oos_section_flags_degenerate_variance() -> None:
    """#387: an explosive OOS Sharpe must never print unflagged.

    The chronological OOS block must carry the same DEGENERATE-VARIANCE marker
    the in-sample table already emits for the same `sharpe_degenerate` flag.
    """
    token = "DEGENERATE-VARIANCE"
    degenerate = _mechanics_oos_metric(
        degenerate=True, sharpe_annualized=68940.776  # observed in the #387 receipt
    )
    sound = _mechanics_oos_metric(degenerate=False, sharpe_annualized=1.443)
    report = eb.render_report(_mechanics_receipt({"challenger": degenerate, "incumbent": sound}))

    table = _render_section(report, "## Metrics (cost-adjusted, shared basis)", "## Chronological OOS")
    table_rows = {ln.split(" |", 1)[0][2:]: ln for ln in table.splitlines() if ln.startswith("| ")}
    assert token in table_rows["challenger"]  # established in-sample behaviour
    assert token not in table_rows["incumbent"]

    oos = _render_section(report, "## Chronological OOS", "## Statistics")
    oos_rows = {ln.split(":", 1)[0][2:]: ln for ln in oos.splitlines() if ln.startswith("- ")}
    assert "68940.776" in oos_rows["challenger"]
    assert token in oos_rows["challenger"]
    assert token not in oos_rows["incumbent"]
    assert eb.DEGENERATE_VARIANCE_MARKER == token  # one render token, both sections


def test_mechanics_report_publishes_aligned_sharpe_ci() -> None:
    """#388 acceptance (3): both Sharpe cells publish the CI on the point scale.

    In-sample table and chronological OOS block must carry the same annualized
    interval, disclose the scale, and keep honest absence where no interval was
    computed. MECHANICS ONLY: the row is synthetic arithmetic, not performance.
    """
    eq = _mechanics_equity(_mechanics_return_path())
    m = eb.metrics_for_curve(eq, [1.0] * len(eq), 1.0, 5.0, None, "ANALYTIC_MODEL", eq, 1)
    assert m.sharpe_ci_low is not None and m.sharpe_ci_high is not None
    assert m.sharpe_ci_low <= m.sharpe_annualized <= m.sharpe_ci_high
    cell = eb.sharpe_ci_cell(m)
    assert cell == f"[{m.sharpe_ci_low:.3f},{m.sharpe_ci_high:.3f}]"
    report = eb.render_report(_mechanics_receipt({"incumbent": m}))

    table = _render_section(
        report, "## Metrics (cost-adjusted, shared basis)", "## Chronological OOS"
    )
    assert "annualized" in table  # the scale claim is on the page, not implied
    row = next(ln for ln in table.splitlines() if ln.startswith("| incumbent |"))
    assert f"{m.sharpe_annualized:.3f} {cell}" in row  # point and CI, one scale

    oos = _render_section(report, "## Chronological OOS", "## Statistics")
    oos_row = next(ln for ln in oos.splitlines() if ln.startswith("- incumbent:"))
    assert f"Sharpe_ann {m.sharpe_annualized:.3f} CI {cell}" in oos_row

    # A row whose CI was not computed publishes no interval: absence stays absent.
    absent = eb.render_report(
        _mechanics_receipt(
            {"challenger": _mechanics_oos_metric(degenerate=True, sharpe_annualized=1.443)}
        )
    )
    absent_oos = _render_section(absent, "## Chronological OOS", "## Statistics")
    assert "CI [" not in absent_oos and "n/a" not in absent_oos


def test_mechanics_allocator_mix_shape() -> None:
    import numpy as np

    rng = np.random.default_rng(9)
    inc = list(0.001 + 0.002 * rng.standard_normal(200))
    ch = [0.0] * 200
    mix = eb.allocator_mix(inc, ch)
    assert mix["scope"] == "ALLOCATOR_LEVEL_NOT_ENGINE_JOINT"
    assert mix["incremental_net"] < mix["p_net"]  # dead challenger sleeve drags


# ---------------------------------------------------------------------------
# Error-path separation: bad data must never mint an economic verdict,
# and no statistical state may ever flip capital.
# ---------------------------------------------------------------------------


def test_mechanics_invalid_data_yields_no_economic_verdict() -> None:
    stats = {
        "dsr": {"verdict": "SUPPORTED_DESCRIPTIVE"},
        "pbo": {"verdict": "SUPPORTED_DESCRIPTIVE"},
        "spa": {"verdict": "SUPPORTED_DESCRIPTIVE"},
    }
    v = eb.build_verdicts(
        chrono_ok=False,
        chrono_note="NON_MONOTONIC_TIME_7",
        excess=0.05,  # positive excess must NOT leak through invalid data
        excess_ci=(0.01, 0.09),
        stats=stats,
        mix={"incremental_net": 0.01},
        cost_basis_ok=True,
        funding_missing=False,
        live_fills_present=True,
        parity_ok=True,
    )
    assert v.research_validity == "INVALID"
    assert v.economic == "INCONCLUSIVE"
    assert v.capital == "NOT_AUTHORIZED"


def test_mechanics_failed_estimators_stay_unsuccessful() -> None:
    stats = {
        "dsr": {"verdict": "UNDERPOWERED", "reason": "boom"},
        "pbo": {"verdict": "UNDERPOWERED", "reason": "boom"},
        "spa": {"verdict": "UNSUPPORTED", "reason": "arch absent"},
    }
    v = eb.build_verdicts(
        chrono_ok=True,
        chrono_note="OK",
        excess=0.05,
        excess_ci=(0.01, 0.09),
        stats=stats,
        mix={"incremental_net": 0.01},
        cost_basis_ok=True,
        funding_missing=True,
        live_fills_present=False,
        parity_ok=True,
    )
    assert v.statistical in ("UNDERPOWERED", "UNSUPPORTED")
    assert v.statistical != "SUPPORTED"
    assert v.economic == "POSITIVE_DESCRIPTIVE"  # descriptive only
    assert v.capital == "NOT_AUTHORIZED"
    assert "NO_ECONOMIC_CLAIM" == eb.EconomicReceipt.__pydantic_fields__["claim_status"].default


def test_mechanics_rules_fire_only_on_registrations() -> None:
    base = {
        "chrono_ok": True, "chrono_note": "OK", "excess": -0.02,
        "mix": {"incremental_net": 0.0}, "cost_basis_ok": True,
        "funding_missing": False, "live_fills_present": False, "parity_ok": True,
    }
    computed = {
        "dsr": {"verdict": "COMPUTED", "dsr_confidence": 0.5,
                "selected_sharpe_nonannualized": -0.1, "selected_variant": "x"},
        "pbo": {"verdict": "COMPUTED"},
        "spa": {"verdict": "COMPUTED", "pvalues": {"consistent": 0.4}},
        "variant_excess_vs_baseline": -0.01,
    }
    v = eb.build_verdicts(**base, excess_ci=(-0.05, 0.03), stats=dict(computed))
    assert v.statistical == "INCONCLUSIVE"
    v = eb.build_verdicts(**base, excess_ci=(-0.05, -0.01), stats=dict(computed))
    assert v.statistical == "SUPPORTS_UNDERPERFORMANCE"
    edge_spa = dict(computed)
    edge_spa["variant_excess_vs_baseline"] = 0.02
    edge_spa["spa"] = {"verdict": "COMPUTED", "pvalues": {"consistent": 0.01}}
    v = eb.build_verdicts(**base, excess_ci=(-0.05, 0.03), stats=edge_spa)
    assert v.statistical == "SUPPORTS_EDGE"
    edge_dsr = dict(computed)
    edge_dsr["dsr"] = {"verdict": "COMPUTED", "dsr_confidence": 0.97,
                       "selected_sharpe_nonannualized": 0.4, "selected_variant": "y"}
    v = eb.build_verdicts(**base, excess_ci=(-0.05, 0.03), stats=edge_dsr)
    assert v.statistical == "SUPPORTS_EDGE"


# ---------------------------------------------------------------------------
# Evaluative: real tape only
# ---------------------------------------------------------------------------


def test_economic_benchmark_real_tape_end_to_end(tmp_path: Path) -> None:
    from v8_next.app import economic as econ_mod
    from v8_next.evaluation.gate_resolution import DEFAULT_TAPE_PATH

    if not DEFAULT_TAPE_PATH.exists():
        pytest.skip(f"Real tape not found at {DEFAULT_TAPE_PATH}")
    rc = econ_mod.main(
        [
            "--tape-path",
            str(DEFAULT_TAPE_PATH),
            "--bars",
            "500",
            "--output-dir",
            str(tmp_path / "econ"),
            "--primary",
            "btc_buy_hold",
        ]
    )
    assert rc == 0
    import json

    receipts = sorted((tmp_path / "econ").glob("economic_receipt_*.json"))
    assert receipts, "tagged economic receipt missing"
    receipt = json.loads(receipts[0].read_text())
    assert receipt["claim_status"] == "NO_ECONOMIC_CLAIM"
    assert receipt["verdicts"]["capital"] == "NOT_AUTHORIZED"
    assert receipt["verdicts"]["statistical"] in ("SUPPORTS_EDGE", "SUPPORTS_UNDERPERFORMANCE", "INCONCLUSIVE", "UNDERPOWERED", "UNSUPPORTED")
    # No invented universal PASS: statistical support never flips economic/capital.
    assert set(receipt["metrics"]) >= {"incumbent", "challenger", "btc_buy_hold", "cash"}
    assert list((tmp_path / "econ").glob("economic_report_*.md")), "tagged economic report missing"
    report = next(iter((tmp_path / "econ").glob("economic_report_*.md"))).read_text(encoding="utf-8")
    # #387: a frozen split that actually produced an OOS slice must be covered.
    if receipt["run"]["dataset"]["n_bars"] >= eb.OOS_FIT_BARS + 48:
        assert receipt["oos_metrics"], "OOS slice missing: flagged render path untested"
    # #387: every OOS row must carry the marker iff its MetricSet is flagged.
    for name, m in receipt["oos_metrics"].items():
        row = f"- {name}: "
        line = next((ln for ln in report.splitlines() if ln.startswith(row)), None)
        assert line is not None, f"OOS row missing for {name}"
        assert (eb.DEGENERATE_VARIANCE_MARKER in line) == bool(m["sharpe_degenerate"]), line
    assert list((tmp_path / "econ").glob("incumbent_trades_*.jsonl"))
    # Missing-data honesty: funding stays missing, live stays unrun.
    assert receipt["metrics"]["incumbent"]["funding_cost"] is None
    assert receipt["shadow_live"]["model_vs_real_fills"] == "UNRUN"


# ---------------------------------------------------------------------------
# #397 — turnover and commission must be one fill set, in the declared fee
# convention (`taker_fee` on traded notional). Entry AND exit legs.
# ---------------------------------------------------------------------------


def _mechanics_engine_result() -> dict[str, Any]:
    """MECHANICS ONLY synthetic engine result: one campaign, entry + exit.

    Ledger arithmetic with zero evaluative weight: two fills at known prices and
    the two position records the engine emits for them. No market data, no
    performance claim.
    """
    end_ns = [(i + 1) * 3_600_000_000_000 for i in range(6)]
    return {
        "opened_positions": [
            {
                "position_id": "MECH-1",
                "instrument_id": "MECH-PERP.BINANCE",
                "side": "LONG",
                "quantity": "2",
                "avg_px_open": "100",
                "event_ns": end_ns[1],
            }
        ],
        "closed_positions": [
            {
                "position_id": "MECH-1",
                "instrument_id": "MECH-PERP.BINANCE",
                "realized_pnl": "4 USDT",
                "avg_px_close": "102",
                "event_ns": end_ns[3],
            }
        ],
        "account": {
            "balance_total": "10004 USDT",
            "orders": [
                {"status": "FILLED", "filled_qty": "2", "average_price": "100"},
                {"status": "FILLED", "filled_qty": "2", "average_price": "102"},
            ],
            "positions": [],
        },
        "_end_ns": end_ns,
    }


def test_mechanics_engine_turnover_counts_entry_and_exit_fills() -> None:
    """#397 (G1, mechanics): one campaign, both legs, one fee convention.

    A campaign that opens 2 @ 100 and closes 2 @ 102 trades 404 USDT of
    notional, so turnover must be 404/capital and the commission estimate
    404 * taker_fee. Pre-fix the close was carried as a zero-notional event:
    turnover stopped at 200/capital while the commission still charged both
    fills, publishing an implied fee ~2x the declared taker fee.
    """
    engine_result = _mechanics_engine_result()
    end_ns = engine_result.pop("_end_ns")
    capital, fee = 10000.0, 0.0005
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]

    ser = eb.portfolio_series_from_engine(
        engine_result, {"MECH-PERP.BINANCE": closes}, end_ns, capital, fee
    )

    assert ser["commission"] == pytest.approx(404.0 * fee, rel=1e-12)
    assert ser["turnover"] == pytest.approx(404.0 / capital, rel=1e-12)
    # The published pair prices at exactly the declared fee.
    assert ser["commission"] == pytest.approx(ser["turnover"] * capital * fee, rel=1e-12)

    notional = ser["cost_reconciliation"]["turnover_notional"]
    assert notional["entry_notional_usdt"] == pytest.approx(200.0, rel=1e-12)
    assert notional["exit_notional_usdt"] == pytest.approx(204.0, rel=1e-12)
    assert notional["total_notional_usdt"] == pytest.approx(404.0, rel=1e-12)
    assert notional["entry_fills"] == 1 and notional["exit_fills"] == 1
    assert notional["exit_price_source"] == {"engine_avg_px_close": 1, "bar_close_proxy": 0}
    assert notional["fills_notional_usdt"] == pytest.approx(404.0, rel=1e-12)
    assert notional["fills_notional_unattributed_usdt"] == pytest.approx(0.0, abs=1e-9)


def test_mechanics_engine_turnover_falls_back_to_bar_close_when_unpriced() -> None:
    """#397 (G1, mechanics): a missing engine close price is NOT a free exit.

    The bar-close fill proxy is used and disclosed, so the exit still carries
    turnover instead of silently dropping out of the denominator.
    """
    engine_result = _mechanics_engine_result()
    end_ns = engine_result.pop("_end_ns")
    engine_result["closed_positions"][0]["avg_px_close"] = ""
    capital, fee = 10000.0, 0.0005
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]

    ser = eb.portfolio_series_from_engine(
        engine_result, {"MECH-PERP.BINANCE": closes}, end_ns, capital, fee
    )

    # Exit at the bar-3 close (103), not at zero notional.
    assert ser["turnover"] == pytest.approx((2 * 100 + 2 * 103) / capital, rel=1e-12)
    notional = ser["cost_reconciliation"]["turnover_notional"]
    assert notional["exit_notional_usdt"] == pytest.approx(206.0, rel=1e-12)
    assert notional["exit_price_source"] == {"engine_avg_px_close": 0, "bar_close_proxy": 1}


def _quad_tape_dir() -> Path | None:
    """The quad tape from the repo root, else the canonical checkout, else None."""
    for candidate in (
        Path(__file__).resolve().parents[2] / "research" / "tape" / "quad-1h-12m",
        Path("/Users/hootie/src/v8/research/tape/quad-1h-12m"),
    ):
        if (candidate / "tape.jsonl").exists():
            return candidate
    return None


def _btc_tape_file() -> Path | None:
    """The single-instrument tape: env/honoured default, then the repo root."""
    from v8_next.evaluation.gate_resolution import DEFAULT_TAPE_PATH

    for candidate in (
        DEFAULT_TAPE_PATH,
        Path(__file__).resolve().parents[2] / "research" / "tape" / "btcusdt-1h-12m" / "tape.jsonl",
        Path("/Users/hootie/src/v8/research/tape/btcusdt-1h-12m/tape.jsonl"),
    ):
        if candidate.exists():
            return candidate
    return None


def _persisted_fill_pairs(out_dir: Path) -> tuple[float, float, int]:
    """Re-derive entry/exit notional from the run's persisted fill records.

    Uses the same chronological per-slot pairing contract the series uses, so
    the aggregate is an independent recomputation, not a restatement.
    """
    opens_raw = [
        json.loads(line)
        for line in sorted(out_dir.glob("portfolio_P_trades_*.jsonl"))[0].read_text().splitlines()
        if line.strip()
    ]
    closed_raw = [
        json.loads(line)
        for line in sorted(out_dir.glob("portfolio_closed_*.jsonl"))[0].read_text().splitlines()
        if line.strip()
    ]
    opens = [
        {
            "position_id": o["trade_id"],
            "instrument_id": o["instrument_id"],
            "side": o["side"],
            "quantity": o["quantity"],
            "avg_px_open": o["avg_px_open"],
            "event_ns": o["fill_time_ns"],
        }
        for o in opens_raw
    ]
    closes = [
        {
            "position_id": c["position_id"],
            "instrument_id": c["instrument_id"],
            "avg_px_close": c["avg_px_close"],
            "event_ns": c["fill_time_ns"],
        }
        for c in closed_raw
    ]
    pairs = eb.pair_positions(opens, closes)
    entry = sum(abs(float(o["quantity"])) * float(o["avg_px_open"]) for o, _ in pairs)
    exit_ = sum(
        abs(float(o["quantity"])) * float(str(c["avg_px_close"]))
        for o, c in pairs
        if c is not None and c.get("avg_px_close")
    )
    return entry, exit_, len(closes)


def test_economic_portfolio_turnover_matches_commission_fill_set(tmp_path: Path) -> None:
    """#397 (G1/G2) on the canonical quad engine path. Real tape; skips if absent.

    Reproduces the canonical 385-bar quad window and checks the published pair:
    ``commission_cost == turnover_notional_over_capital * capital * taker_fee``
    within the 1% fill-price tolerance, turnover re-derived independently from
    the persisted entry/exit fills, and implied fee 5.0 bps for P and P+E.
    """
    tape = _quad_tape_dir()
    if tape is None:
        pytest.skip("quad tape absent")
    from v8_next.app import portfolio as port_mod

    out_dir = tmp_path / "port"
    rc = port_mod.main(
        [
            "--tape-path",
            str(tape),
            "--bars",
            "385",
            "--output-dir",
            str(out_dir),
            "--primary",
            "equal_weight",
        ]
    )
    assert rc == 0
    receipt = json.loads(
        sorted(out_dir.glob("economic_receipt_*.json"))[0].read_text(encoding="utf-8")
    )
    capital = receipt["run"]["capital"]
    fee = receipt["run"]["taker_fee"]

    for name in ("portfolio_P", "portfolio_PE"):
        m = receipt["metrics"][name]
        traded = m["turnover_notional_over_capital"] * capital
        assert traded > 0.0
        assert m["commission_cost"] == pytest.approx(traded * fee, rel=0.01)
        assert m["commission_cost"] / traded * 1e4 == pytest.approx(fee * 1e4, abs=0.1)

    entry, exit_, n_closes = _persisted_fill_pairs(out_dir)
    assert n_closes > 0, "window produced no exits: the check would be vacuous"
    p_traded = receipt["metrics"]["portfolio_P"]["turnover_notional_over_capital"] * capital
    assert p_traded == pytest.approx(entry + exit_, rel=0.01)
    # The defect this pins: entry-only notional priced the same commission at 2x.
    assert p_traded > entry
    assert receipt["claim_status"] == "NO_ECONOMIC_CLAIM"


def test_economic_incumbent_turnover_and_capacity_breakeven(tmp_path: Path) -> None:
    """#397 (G1/G3) on the engine-backed single-instrument path. Skips without tape.

    The incumbent/challenger rows are engine-backed: their published turnover
    must price at the declared fee, the capacity breakeven must be derived from
    that corrected notional, and no claim may be minted by the fix.
    """
    tape = _btc_tape_file()
    if tape is None:
        pytest.skip("Real tape not found")
    from v8_next.app import economic as econ_mod

    rc = econ_mod.main(
        [
            "--tape-path",
            str(tape),
            "--bars",
            "500",
            "--output-dir",
            str(tmp_path / "econ"),
            "--primary",
            "btc_buy_hold",
        ]
    )
    assert rc == 0
    receipt = json.loads(
        sorted((tmp_path / "econ").glob("economic_receipt_*.json"))[0].read_text(encoding="utf-8")
    )
    capital = receipt["run"]["capital"]
    fee = receipt["run"]["taker_fee"]

    for name in ("incumbent", "challenger"):
        m = receipt["metrics"][name]
        traded = m["turnover_notional_over_capital"] * capital
        assert traded > 0.0
        assert m["commission_cost"] == pytest.approx(traded * fee, rel=0.01)
        assert m["commission_cost"] / traded * 1e4 == pytest.approx(fee * 1e4, abs=0.1)

    inc = receipt["metrics"]["incumbent"]
    breakeven = receipt["capacity_scenarios"][0]["breakeven_extra_cost_bp"]
    # G3: breakeven is the excess over the notional the receipt publishes.
    assert breakeven == pytest.approx(
        inc["excess_vs_primary"] / inc["turnover_notional_over_capital"] * 1e4, abs=1e-6
    )
    assert receipt["capacity_scenarios"][0]["assumed_fee_bp"] == pytest.approx(fee * 1e4)
    assert receipt["claim_status"] == "NO_ECONOMIC_CLAIM"


# ---------------------------------------------------------------------------
# #396 — `excess_ci_low/high` is the interval of the EXCESS RETURN it is
# attached to. A per-bar Sharpe ratio is a different estimand and must never be
# published as a return interval (it does not even contain its own point).
# ---------------------------------------------------------------------------

CANONICAL_RECEIPT_588D668B_REL = "artifacts/benchmarks/economic_receipt_588d668b.json"


def _canonical_receipt_path() -> Path | None:
    """Frozen #396 evidence receipt: this checkout, else the shared main checkout.

    Evidence artifacts live outside git (worktrees do not carry them), so the
    worktree falls back to the parent checkout. Absence skips: never synthesize.
    """
    root = Path(__file__).resolve().parents[2]
    for candidate in (root / CANONICAL_RECEIPT_588D668B_REL,
                      root.parent.parent / CANONICAL_RECEIPT_588D668B_REL):
        if candidate.is_file():
            return candidate
    return None


def _mechanics_excess_paths(
    n: int = 300, gap: float = -0.002, seed: int = 21
) -> tuple[list[float], list[float]]:
    """MECHANICS ONLY: a strategy path and a primary path with a known window gap.

    Zero evaluative weight: seeded arithmetic, no market data, no claim. The
    strategy loses `gap` per bar to the primary on average, so the window excess
    is large enough to be excluded by a per-bar Sharpe interval.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    primary = [float(v) for v in 0.0005 + 0.01 * rng.standard_normal(n)]
    strat = [p + gap + float(v) for p, v in zip(primary, 0.002 * rng.standard_normal(n), strict=True)]
    return strat, primary


def test_mechanics_excess_ci_is_return_interval_not_sharpe() -> None:
    """#396 (G1): the stored `excess_ci_*` is the CI of the excess RETURN.

    Pre-fix the interval was the block-bootstrap Sharpe of the per-bar return
    difference, so it was on a ratio scale, equal to that Sharpe interval by
    construction, and could exclude the `excess_vs_primary` it was published
    beside. The module's `EXCESS_CI_RULE` text must name the statistic the code
    actually applies.
    """
    strat, primary = _mechanics_excess_paths()
    eq = _mechanics_equity(strat)
    p_eq = _mechanics_equity(primary)
    m = eb.metrics_for_curve(eq, [1.0] * len(eq), 1.0, 5.0, None, "ANALYTIC_MODEL", p_eq, 1)

    assert m.excess_vs_primary is not None
    assert m.excess_ci_low is not None and m.excess_ci_high is not None
    # (1) the interval contains the point estimate it belongs to.
    assert m.excess_ci_low <= m.excess_vs_primary <= m.excess_ci_high

    # (2) it is NOT the diff series' bootstrap Sharpe statistic (the pre-fix value).
    sharpe_lo, sharpe_hi = eb.block_bootstrap_ci(
        [a - b for a, b in zip(eb.per_bar_returns(eq), eb.per_bar_returns(p_eq), strict=False)]
    )
    assert sharpe_lo is not None and sharpe_hi is not None
    assert (m.excess_ci_low, m.excess_ci_high) != (sharpe_lo, sharpe_hi)
    # Discriminator: the Sharpe interval cannot hold a window-scale return.
    assert not (sharpe_lo <= m.excess_vs_primary <= sharpe_hi)

    # (3) the applied estimator is the return-scale one, and the rule names it.
    assert (m.excess_ci_low, m.excess_ci_high) == pytest.approx(
        eb.period_excess_ci(eq, p_eq), rel=0, abs=0
    )
    rule = eb.EXCESS_CI_RULE
    assert "EXCESS RETURN" in rule
    assert "RETURN scale" in rule
    assert "per-bar excess" not in rule.lower()
    import inspect

    assert "period_excess_ci" in inspect.getsource(eb.metrics_for_curve)
    # The pre-fix Sharpe primitive must not be reachable from the excess block.
    assert "excess_ci = block_bootstrap_ci(diff)" not in inspect.getsource(eb.metrics_for_curve)


def test_mechanics_excess_rule_sign_test_survives_on_return_interval() -> None:
    """#396 (G3): verdict semantics are unchanged — the rule stays a sign test.

    `EXCESS_CI_RULE` still fires SUPPORTS_UNDERPERFORMANCE iff the published
    interval is entirely below zero, on the return scale, for the canonical
    point estimate recorded in the bound receipt; the fix mints no claim.
    """
    receipt_path = _canonical_receipt_path()
    if receipt_path is None:
        pytest.skip("canonical #396 receipt not present in this checkout")
    assert receipt_path is not None  # narrowed for the type checker
    recorded = json.loads(receipt_path.read_text(encoding="utf-8"))
    inc = recorded["metrics"]["portfolio_P"]
    point = inc["excess_vs_primary"]
    # The recorded (pre-fix) interval published a Sharpe statistic and excludes
    # its own point estimate: exactly the defect this card closes.
    assert not (inc["excess_ci_low"] <= point <= inc["excess_ci_high"])

    computed_stats = {
        "dsr": {"verdict": "COMPUTED", "dsr_confidence": 0.5,
                "selected_sharpe_nonannualized": -0.1, "selected_variant": "portfolio_P"},
        "pbo": {"verdict": "COMPUTED"},
        "spa": {"verdict": "COMPUTED", "pvalues": {"consistent": 0.4}},
        "variant_excess_vs_baseline": -0.01,
    }
    base = {
        "chrono_ok": True, "chrono_note": "OK; leak_probe=OK", "excess": point,
        "mix": {"incremental_net": -0.0038}, "cost_basis_ok": True,
        "funding_missing": False, "live_fills_present": False, "parity_ok": True,
    }
    # Return-scale interval around the same point: below zero => same verdict.
    v = eb.build_verdicts(
        **base, excess_ci=(point - 0.15, point + 0.15), stats=dict(computed_stats)
    )
    assert v.statistical == "SUPPORTS_UNDERPERFORMANCE"
    assert "EXCESS_CI_RULE" in v.statistical_note
    assert eb.EconomicReceipt.__pydantic_fields__["claim_status"].default == "NO_ECONOMIC_CLAIM"
    assert recorded["claim_status"] == "NO_ECONOMIC_CLAIM"
    assert recorded["verdicts"]["statistical"] == "SUPPORTS_UNDERPERFORMANCE"
    assert "EXCESS_CI_RULE" in recorded["verdicts"]["statistical_note"]
