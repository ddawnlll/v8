"""Economic benchmark tests.

MECHANICS ONLY synthetic section: arithmetic/validator unit coverage with zero
evaluative weight. No test here asserts economic performance on synthetic data.

Evaluative section: real-tape BenchmarkCase via the economic fabric; skips when
the tape is absent. Synthetic candles are banned there.
"""

from pathlib import Path

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
