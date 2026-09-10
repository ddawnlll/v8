"""MECHANICS ONLY: cost-source and component-conservation checks."""

from decimal import Decimal
from pathlib import Path

from v8_next.evaluation.costs import (
    OperatingExpense,
    VenueFillCost,
    calibrate_venue_cost,
    compute_operating_net,
)
from v8_next.evaluation.parity import ArtifactBinding


def _artifact(tmp_path: Path, name: str) -> ArtifactBinding:
    path = tmp_path / name
    path.write_bytes(b"physical test artifact")
    return ArtifactBinding.from_file("test", path)


def test_operating_net_requires_physical_cost_sources(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path, "fills.jsonl")
    calibration = calibrate_venue_cost(
        (
            VenueFillCost(
                quantity=Decimal("2"),
                fee=Decimal("0.2"),
                fill_price=Decimal("101"),
                reference_mid=Decimal("100"),
            ),
        ),
        artifact,
    )
    assert calibration.status == "CALIBRATED"
    assert calibration.fill_vs_mid_bps is not None


def test_operating_net_separates_strategy_and_fixed_cost(tmp_path: Path) -> None:
    expense = OperatingExpense(
        amount=Decimal("10"),
        currency="USDT",
        period_start_ns=1,
        period_end_ns=2,
        source_artifact=_artifact(tmp_path, "invoice.json"),
    )
    result = compute_operating_net(
        transaction_pnl=Decimal("100"),
        funding=Decimal("-2"),
        explicit_fees=Decimal("3"),
        expenses=(expense,),
        currency="USDT",
    )
    assert result.strategy_net == Decimal("95")
    assert result.operating_net == Decimal("85")
    assert result.status == "NO_ECONOMIC_CLAIM"
