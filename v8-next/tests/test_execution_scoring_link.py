"""MECHANICS ONLY (no tape) + one real-tape discrimination test.

No economic claim is made anywhere in this file. The mechanics section pins how
the ExecutionFidelity domain decides between *measured* execution evidence and
the legacy PnL-Sharpe proxy, which measured statistic it reads, and what it
publishes about that choice. The last section runs the shared portfolio engine
over the real quad tape — it is evaluative, skips when the tape is absent, and
asserts only that the published dimension follows the measured shortfall instead
of reporting a constant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from v8_next.evaluation.scoring import (
    EXECUTION_FIDELITY_REFERENCE_BPS,
    EXECUTION_FIDELITY_SHORTFALL_FIELD,
    compute_capability_breakdown,
)

PNL = [0.01, -0.005, 0.02, -0.01, 0.015]


def _breakdown(execution=None):
    return compute_capability_breakdown(
        pnl_series=PNL,
        total_bars=500,
        total_trades=len(PNL),
        abstain_rate=0.0,
        execution=execution,
    )


def test_without_execution_evidence_the_source_is_declared_as_the_proxy() -> None:
    out = _breakdown(None)
    assert out["execution_fidelity_source"] == "PNL_SHARPE_PROXY"
    assert out["execution_fidelity_reference_bps"] == EXECUTION_FIDELITY_REFERENCE_BPS


def test_zero_samples_do_not_count_as_measured_execution() -> None:
    out = _breakdown({"slippage_samples": 0, "slippage_bps_mean": 0.0})
    assert out["execution_fidelity_source"] == "PNL_SHARPE_PROXY"


def test_measured_shortfall_is_used_when_samples_exist() -> None:
    out = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 6.0})
    assert out["execution_fidelity_source"] == "MEASURED_IMPLEMENTATION_SHORTFALL"
    # 1 - 6/10 = 0.40
    assert out["domains"]["ExecutionFidelity"]["score"] == pytest.approx(40.0)
    # the measured input the score came from is published, not just the score
    assert out["execution_fidelity_shortfall_bps"] == pytest.approx(6.0)


def _declared_score(shortfall_bps: float) -> float:
    """Published ExecutionFidelity for a measured shortfall of that magnitude."""
    out = _breakdown(
        {
            "slippage_samples": 3,
            "slippage_bps_mean": shortfall_bps,
            EXECUTION_FIDELITY_SHORTFALL_FIELD: shortfall_bps,
        }
    )
    assert out["execution_fidelity_source"] == "MEASURED_IMPLEMENTATION_SHORTFALL"
    assert out["execution_fidelity_shortfall_bps"] == pytest.approx(shortfall_bps)
    return out["domains"]["ExecutionFidelity"]["score"]


def test_declared_range_is_monotone_to_the_top_at_zero_and_zero_at_the_reference() -> None:
    """The declared mapping is 1 - bps/10 over [0, 1]: monotone, no hidden ceiling.

    0 bps is the upper bound of the declared range and the 10 bps reference is
    zero — the convention the same module states one line above the mapping.
    """
    magnitudes = [0.0, 0.25, 1.0, 2.5, 5.0, 7.5, 9.9, 10.0]
    scores = [_declared_score(m) for m in magnitudes]

    assert all(
        lower > higher for lower, higher in zip(scores, scores[1:], strict=False)
    )
    assert scores[0] == pytest.approx(100.0)
    assert scores[-1] == pytest.approx(0.0)
    for magnitude, score in zip(magnitudes, scores, strict=True):
        expected = max(0.0, 1.0 - magnitude / EXECUTION_FIDELITY_REFERENCE_BPS) * 100.0
        assert score == pytest.approx(round(expected, 1))
    # past the reference the domain sits on its declared floor, never below it
    assert _declared_score(1e6) == pytest.approx(0.0)


def test_opposite_signed_fills_do_not_cancel_away_the_measured_deviation() -> None:
    """The mechanism behind the reported "baseline 0.0 vs realistic 0.0004 bps".

    Two fills that both landed 0.05 bps away from their decision price, on
    opposite sides, average to 0.0 bps in the signed mean — the statistic that
    made every published fidelity a constant. The magnitude statistic the
    convention names must not cancel them, and the published score must not read
    as untouched execution.
    """
    out = _breakdown(
        {"slippage_samples": 2, "slippage_bps_mean": 0.0,
         EXECUTION_FIDELITY_SHORTFALL_FIELD: 0.05}
    )
    assert out["execution_fidelity_source"] == "MEASURED_IMPLEMENTATION_SHORTFALL"
    assert out["execution_fidelity_shortfall_bps"] == pytest.approx(0.05)
    assert out["domains"]["ExecutionFidelity"]["score"] == pytest.approx(99.5)


def test_shortfall_sign_does_not_matter_only_magnitude() -> None:
    adverse = _breakdown(
        {"slippage_samples": 3, EXECUTION_FIDELITY_SHORTFALL_FIELD: 6.0}
    )
    favourable = _breakdown(
        {"slippage_samples": 3, EXECUTION_FIDELITY_SHORTFALL_FIELD: -6.0}
    )
    assert (
        adverse["domains"]["ExecutionFidelity"]["score"]
        == favourable["domains"]["ExecutionFidelity"]["score"]
        == pytest.approx(40.0)
    )


def test_a_block_predating_the_magnitude_field_keeps_its_measurement() -> None:
    """A persisted block from before the magnitude field keeps its measured link.

    |signed mean| is the same quantity minus the cancellation, so such a block
    stays bound to the evidence it has instead of silently downgrading to the
    PnL proxy.
    """
    legacy = _breakdown({"slippage_samples": 3, "slippage_bps_mean": -2.0})
    assert legacy["execution_fidelity_source"] == "MEASURED_IMPLEMENTATION_SHORTFALL"
    assert legacy["execution_fidelity_shortfall_bps"] == pytest.approx(2.0)
    assert legacy["domains"]["ExecutionFidelity"]["score"] == pytest.approx(80.0)


def test_negligible_deviation_is_the_top_of_the_range_not_the_old_ceiling() -> None:
    """Rescoped from the removed ``_documented_saturation_when_the_model_is_negligible``.

    That test pinned a zero-friction and a near-zero-friction model at a 0.50
    ceiling which contradicted the declared convention in the same file. Under
    the declared mapping both sit at the top of the range: a deviation that real
    but five orders of magnitude below the 10 bps reference is indistinguishable
    at the published resolution *by that scale's design*, and the reference that
    sets the scale is published next to every score.
    """
    zero = _breakdown(
        {"slippage_samples": 3, "slippage_bps_mean": 0.0,
         EXECUTION_FIDELITY_SHORTFALL_FIELD: 0.0}
    )
    tiny = _breakdown(
        {"slippage_samples": 3, "slippage_bps_mean": 0.000404,
         EXECUTION_FIDELITY_SHORTFALL_FIELD: 0.000404}
    )
    assert zero["domains"]["ExecutionFidelity"]["score"] == pytest.approx(100.0)
    assert tiny["domains"]["ExecutionFidelity"]["score"] == pytest.approx(100.0)
    assert zero["domains"]["ExecutionFidelity"]["score"] != pytest.approx(50.0)
    assert tiny["execution_fidelity_reference_bps"] == EXECUTION_FIDELITY_REFERENCE_BPS


def test_telemetry_publishes_the_statistic_the_declared_convention_reads() -> None:
    """MECHANICS ONLY: producer/consumer agreement on the declared statistic.

    Synthetic fills with zero evaluative weight, crafted so the two statistics
    disagree: a buy and a sell both landing 100.01 against a 100.00 decision
    price deviate ~1 bps each, and cancel in the signed mean.
    """
    from v8_next.adapters.execution_models import PROFILES
    from v8_next.adapters.execution_telemetry import execution_telemetry

    block = execution_telemetry(
        PROFILES["baseline"],
        [],
        "TEST",
        [
            {"instrument_id": "X", "side": "BUY", "avg_px_open": 100.01, "event_ns": 10},
            {"instrument_id": "X", "side": "SELL", "avg_px_open": 100.01, "event_ns": 20},
        ],
        [
            {"instrument_id": "X", "decision_ns": 1, "close": 100.0},
            {"instrument_id": "X", "decision_ns": 11, "close": 100.0},
        ],
    )
    assert block["slippage_samples"] == 2
    assert block["slippage_bps_mean"] == pytest.approx(0.0)
    assert block[EXECUTION_FIDELITY_SHORTFALL_FIELD] == pytest.approx(1.0)

    out = _breakdown(block)
    assert out["execution_fidelity_source"] == "MEASURED_IMPLEMENTATION_SHORTFALL"
    assert out["domains"]["ExecutionFidelity"]["score"] == pytest.approx(90.0)


def test_no_trades_keeps_an_empty_domain_set_and_names_the_reason() -> None:
    out = compute_capability_breakdown(
        pnl_series=[], total_bars=500, total_trades=0, abstain_rate=0.0,
        execution={"slippage_samples": 3, "slippage_bps_mean": 1.0},
    )
    assert out["domains"] == {}
    # NX08.R1: with no trades the aggregate is missing, not zero, and the reason
    # is named; the coverage factor is derived (trade domains abstained).
    assert out["aggregate"] is None
    assert out["aggregate_status"] == "MISSING_NO_TRADES"
    assert out["coverage_source"] == "DERIVED_FROM_MEASURED_DOMAINS"
    assert out["coverage"]["statuses"]["ExecutionFidelity"] == "ABSTAINED"
    assert out["coverage"]["numerator"] < out["coverage"]["denominator"]
    assert out["execution_fidelity_source"] == "NO_TRADES"
    # no domain was scored, so no measured input may be published as if one was
    assert out["execution_fidelity_shortfall_bps"] is None


# ------------------------------------------------- telemetry -> utility inputs


def test_execution_telemetry_artifact_round_trips_and_detects_tampering(tmp_path) -> None:
    from v8_next.adapters.execution_telemetry import (
        load_execution_telemetry,
        persist_execution_telemetry,
    )

    block = {
        "profile": "realistic",
        "digest": "abc123",
        "fills_count": 5,
        "slippage_samples": 3,
        "slippage_bps_mean": 2.0,
        "commission_total": 1.5,
    }
    path = persist_execution_telemetry(tmp_path / "execution_telemetry.json", block)
    assert load_execution_telemetry(path) == block

    # tampering is detected by the artifact's own digest
    import json

    tampered = dict(block)
    tampered["slippage_bps_mean"] = 999.0
    path.write_text(json.dumps({**tampered, "sha256": json.loads(path.read_text())["sha256"]}))
    assert load_execution_telemetry(path) == {}


def test_absent_or_malformed_artifact_yields_nothing(tmp_path) -> None:
    from v8_next.adapters.execution_telemetry import load_execution_telemetry

    assert load_execution_telemetry(tmp_path / "missing.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_execution_telemetry(bad) == {}


def test_friction_inputs_only_report_measured_values() -> None:
    from v8_next.adapters.execution_telemetry import execution_friction_inputs

    assert execution_friction_inputs({}) == {}
    # no samples -> no slippage field at all (the caller's None must survive)
    no_samples = execution_friction_inputs({"slippage_samples": 0, "commission_total": 1.5})
    assert "slippage" not in no_samples
    assert no_samples["fees"] == pytest.approx(1.5)

    measured = execution_friction_inputs(
        {
            "profile": "realistic",
            "digest": "d" * 64,
            "slippage_samples": 3,
            "slippage_bps_mean": -2.0,
            "commission_total": 1.5,
        }
    )
    assert measured["slippage"] == pytest.approx(2.0 / 1e4)
    assert measured["fees"] == pytest.approx(1.5)
    assert measured["calibration_receipt"] == f"execution_profile:realistic:{'d' * 64}"


def test_partially_measured_friction_still_fails_closed() -> None:
    """Only fees and slippage are measured, so spread and funding stay None.

    UtilityInputs.net() requires every friction term, so admission must keep
    rejecting on missing calibration rather than treating unmeasured terms as
    free. This pins that the wiring does not accidentally open the gate.
    """
    from decimal import Decimal

    from v8_next.adapters.execution_telemetry import execution_friction_inputs
    from v8_next.economics.decisions import UtilityInputs, utility_admission

    friction = execution_friction_inputs(
        {"profile": "realistic", "digest": "d" * 64, "slippage_samples": 3,
         "slippage_bps_mean": 2.0, "commission_total": 1.5}
    )
    inputs = UtilityInputs(
        gross_edge=Decimal("10"),
        fees=Decimal(str(friction["fees"])),
        spread=None,
        slippage=Decimal(str(friction["slippage"])),
        funding_cost=None,
        uncertainty=Decimal("0.5"),
        calibration_receipt=friction["calibration_receipt"],
    )
    assert utility_admission(inputs) == "REJECTED_MISSING_CALIBRATION"


def test_fully_measured_friction_lets_the_admission_evaluate() -> None:
    """With every friction term measured the decision evaluates, not rejects."""
    from decimal import Decimal

    from v8_next.economics.decisions import UtilityInputs, utility_admission

    def inputs(gross_edge: str) -> UtilityInputs:
        return UtilityInputs(
            gross_edge=Decimal(gross_edge),
            fees=Decimal("1"),
            spread=Decimal("1"),
            slippage=Decimal("1"),
            funding_cost=Decimal("1"),
            uncertainty=Decimal("0.5"),
            calibration_receipt="execution_profile:realistic:" + "d" * 64,
        )

    assert utility_admission(inputs("10")) == "UTILITY_ELIGIBLE"
    assert utility_admission(inputs("2")) == "REJECTED_SUB_FRICTION"


# --------------------------------------------- real tape: does it discriminate
#
# Everything below runs the shared portfolio engine over the real quad tape.
# It is evaluative (it asserts a property of a published dimension), it never
# uses synthetic candles, and it skips when the tape is absent. 120 bars is the
# window the defect report itself used — no full scan is needed to see whether
# the dimension responds to measured execution.

QUAD_TAPE = Path("/Users/hootie/src/v8/research/tape/quad-1h-12m")
QUAD_BARS = 120


def _quad_run(profile: str) -> dict[str, Any]:
    from decimal import Decimal

    from v8_next.adapters.portfolio_backtest import (
        SleeveSpec,
        run_portfolio_backtest,
    )
    from v8_next.evaluation.multitape import load_multitape

    if not (QUAD_TAPE / "tape.jsonl").exists():
        pytest.skip(f"quad tape absent at {QUAD_TAPE}")
    tape = load_multitape(QUAD_TAPE, limit=QUAD_BARS)
    return run_portfolio_backtest(
        tape.candles,
        (SleeveSpec("incumbent", 1, 28, 1.0),),
        tape.funding,
        per_leg_notional=Decimal("1000"),
        taker_fee=Decimal("0.0005"),
        initial_balance=Decimal("10000"),
        funding_dropped=tape.funding_dropped,
        execution_profile=profile,
    )


def _realized_pnl(run: dict[str, Any]) -> list[float]:
    return [
        float(str(c.get("realized_pnl", "0").split()[0]))
        for c in run.get("closed_positions", [])
        if isinstance(c, dict) and c.get("realized_pnl")
    ]


def _published_fidelity(profile: str) -> float:
    """Run one profile over the real tape and publish its ExecutionFidelity."""
    run = _quad_run(profile)
    block = run["execution"]
    if block["slippage_samples"] == 0:
        pytest.skip(f"{profile}: this window measured no fill shortfall")
    assert EXECUTION_FIDELITY_SHORTFALL_FIELD in block, (
        f"{profile}: the telemetry no longer publishes "
        f"{EXECUTION_FIDELITY_SHORTFALL_FIELD}, the statistic the declared "
        "convention reads; the domain would silently fall back to the signed "
        "mean that cancels between adverse and favourable fills"
    )
    pnl = _realized_pnl(run)
    if not pnl:
        pytest.skip(f"{profile}: this window closed no positions to score against")

    out = compute_capability_breakdown(
        pnl_series=pnl,
        total_bars=QUAD_BARS,
        total_trades=len(run["opened_positions"]),
        abstain_rate=0.0,
        execution=block,
    )
    assert out["execution_fidelity_source"] == "MEASURED_IMPLEMENTATION_SHORTFALL"
    measured = block[EXECUTION_FIDELITY_SHORTFALL_FIELD]
    # the published score must be the declared mapping of THIS block's measured
    # shortfall, not a fixed value that happens to be non-zero
    assert out["execution_fidelity_shortfall_bps"] == pytest.approx(measured)
    expected = max(0.0, 1.0 - measured / EXECUTION_FIDELITY_REFERENCE_BPS) * 100.0
    assert out["domains"]["ExecutionFidelity"]["score"] == pytest.approx(
        round(expected, 1)
    )
    return float(out["domains"]["ExecutionFidelity"]["score"])


def test_real_tape_published_fidelity_follows_measured_execution_evidence() -> None:
    """The dimension responds to measured execution instead of publishing a constant.

    Three execution profiles that model different frictions are run over the same
    120-bar quad window: their published ExecutionFidelity values are their own
    measured shortfalls under the declared mapping, the profile that models no
    slippage cannot score below the ones that do, and the value is no longer the
    constant 0.50 every run used to publish.
    """
    scores = {
        profile: _published_fidelity(profile)
        for profile in ("baseline", "realistic", "volume_aware")
    }
    assert len(set(scores.values())) > 1, f"still a constant: {scores}"
    assert scores["baseline"] == max(scores.values()), scores
    assert 50.0 not in scores.values(), scores
