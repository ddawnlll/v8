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
            "200",
            "--output-dir",
            str(tmp_path / "econ"),
            "--primary",
            "btc_buy_hold",
        ]
    )
    assert rc == 0
    import json

    receipt = json.loads((tmp_path / "econ" / "economic_receipt.json").read_text())
    assert receipt["claim_status"] == "NO_ECONOMIC_CLAIM"
    assert receipt["verdicts"]["capital"] == "NOT_AUTHORIZED"
    assert receipt["verdicts"]["statistical"] in ("SUPPORTED", "UNDERPOWERED", "UNSUPPORTED")
    # No invented universal PASS: statistical support never flips economic/capital.
    assert set(receipt["metrics"]) >= {"incumbent", "challenger", "btc_buy_hold", "cash"}
    assert (tmp_path / "econ" / "economic_report.md").is_file()
    assert (tmp_path / "econ" / "incumbent_trades.jsonl").is_file()
    # Missing-data honesty: funding stays missing, live stays unrun.
    assert receipt["metrics"]["incumbent"]["funding_cost"] is None
    assert receipt["shadow_live"]["model_vs_real_fills"] == "UNRUN"
