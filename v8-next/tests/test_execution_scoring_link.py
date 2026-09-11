"""MECHANICS ONLY — ExecutionFidelity's link to measured execution.

No tape, no economic claim: these tests pin how the domain decides between
*measured* execution evidence and the legacy PnL-Sharpe proxy, and what it
publishes about that choice. Evaluative behaviour on the real tape lives in
``test_execution_integration.py``.
"""

from __future__ import annotations

import pytest

from v8_next.evaluation.scoring import (
    EXECUTION_FIDELITY_REFERENCE_BPS,
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


def test_larger_shortfall_lowers_fidelity_monotonically() -> None:
    low = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 2.0})
    mid = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 6.0})
    high = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 9.5})
    scores = [
        b["domains"]["ExecutionFidelity"]["score"] for b in (low, mid, high)
    ]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > scores[1] > scores[2]


def test_shortfall_sign_does_not_matter_only_magnitude() -> None:
    adverse = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 6.0})
    favourable = _breakdown({"slippage_samples": 3, "slippage_bps_mean": -6.0})
    assert (
        adverse["domains"]["ExecutionFidelity"]["score"]
        == favourable["domains"]["ExecutionFidelity"]["score"]
    )


def test_fidelity_is_clamped_inside_the_domain_band() -> None:
    # absurd friction must not push the domain below its declared floor
    worst = _breakdown({"slippage_samples": 1, "slippage_bps_mean": 1e6})
    assert worst["domains"]["ExecutionFidelity"]["score"] == pytest.approx(5.0)


def test_documented_saturation_when_the_model_is_negligible() -> None:
    """Both a zero-friction and a near-zero-friction model saturate at the ceiling.

    The observed consequence on the real tape: ``baseline`` (0.0 bps) and
    ``realistic`` (0.0004 bps) both score the 0.50 ceiling, so ExecutionFidelity
    cannot separate them until the 10 bps reference is calibrated to the
    friction scale actually being modelled. Pinned here so the saturation is a
    known, tested property rather than a silent surprise.
    """
    zero = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 0.0})
    tiny = _breakdown({"slippage_samples": 3, "slippage_bps_mean": 0.000404})
    assert zero["domains"]["ExecutionFidelity"]["score"] == pytest.approx(50.0)
    assert tiny["domains"]["ExecutionFidelity"]["score"] == pytest.approx(50.0)
    # the evidence that explains the saturation is still published
    assert tiny["execution_fidelity_reference_bps"] == EXECUTION_FIDELITY_REFERENCE_BPS


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
