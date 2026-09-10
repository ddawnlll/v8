"""MECHANICS ONLY: microstructure capacity refuses missing inputs."""

from v8_next.evaluation.capacity import (
    CapacityScenario,
    MicrostructureObservation,
    measure_capacity,
)


def test_capacity_missing_microstructure_is_data_blocked() -> None:
    result = measure_capacity((), CapacityScenario(scale=1.0, requested_multiplier=1.0))
    assert result.status == "DATA_BLOCKED"
    assert result.impact_bps is None


def test_capacity_reports_observed_fill_and_impact_separately() -> None:
    rows = (
        MicrostructureObservation(
            timestamp_ns=1,
            instrument_id="BTCUSDT-PERP.BINANCE",
            mid=100.0,
            spread=1.0,
            adv_qty=1_000.0,
            requested_qty=10.0,
            filled_qty=8.0,
            fill_price=100.5,
        ),
    )
    result = measure_capacity(rows, CapacityScenario(scale=2.0, requested_multiplier=2.0))
    assert result.status == "NO_ECONOMIC_CLAIM"
    assert result.fill_ratio == 0.8
    assert result.impact_bps is not None
    assert result.spread_cost_bps is not None
