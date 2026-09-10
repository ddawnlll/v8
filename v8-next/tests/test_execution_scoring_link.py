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
    assert out["aggregate"] == 0.0
    assert out["execution_fidelity_source"] == "NO_TRADES"
