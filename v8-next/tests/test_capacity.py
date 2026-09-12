"""MECHANICS ONLY: microstructure capacity refuses missing or unscalable inputs."""

import pytest

from v8_next.evaluation.capacity import (
    CapacityScenario,
    MicrostructureObservation,
    measure_capacity,
)


def _row(**overrides: object) -> MicrostructureObservation:
    fields: dict[str, object] = {
        "timestamp_ns": 1,
        "instrument_id": "BTCUSDT-PERP.BINANCE",
        "mid": 100.0,
        "spread": 1.0,
        "adv_qty": 1_000.0,
        "requested_qty": 10.0,
        "filled_qty": 8.0,
        "fill_price": 100.5,
    }
    fields.update(overrides)
    return MicrostructureObservation(**fields)  # type: ignore[arg-type]


def test_capacity_missing_microstructure_is_data_blocked() -> None:
    result = measure_capacity((), CapacityScenario(scale=1.0, requested_multiplier=1.0))
    assert result.status == "DATA_BLOCKED"
    assert result.impact_bps is None
    assert result.reason == "NO_MICROSTRUCTURE_OBSERVATIONS"


def test_capacity_reports_observed_fill_and_impact_at_the_observed_scale() -> None:
    rows = (_row(),)
    result = measure_capacity(rows, CapacityScenario(scale=1.0, requested_multiplier=1.0))
    assert result.status == "NO_ECONOMIC_CLAIM"
    assert result.fill_ratio == 0.8
    assert result.impact_bps == pytest.approx(0.5 / 100.0 * 10_000.0)
    assert result.spread_cost_bps == pytest.approx(1.0 / 100.0 * 10_000.0)
    assert result.participation == pytest.approx(10.0 / 1_000.0)
    assert result.projected_participation is None
    assert result.reason is None


def test_capacity_counterfactual_scale_stays_unresolved() -> None:
    """Observed fills are 1x fills; a 2x scenario is not a measurement of 2x."""

    result = measure_capacity((_row(),), CapacityScenario(scale=2.0, requested_multiplier=2.0))
    assert result.status == "UNRESOLVED"
    assert result.reason == "OBSERVED_FILLS_AT_OTHER_SCALE"
    # measured participation stays the observed quantity; the counterfactual is
    # published as a labelled projection instead of overwriting it.
    assert result.participation == pytest.approx(10.0 / 1_000.0)
    assert result.projected_participation == pytest.approx(2.0 * 10.0 / 1_000.0)
    assert result.fill_ratio == 0.8
    assert result.impact_bps is not None


def test_capacity_rejects_unsequenced_observations() -> None:
    rows = (_row(timestamp_ns=5), _row(timestamp_ns=5))
    with pytest.raises(ValueError, match="UNSEQUENCED_MICROSTRUCTURE_OBSERVATIONS"):
        measure_capacity(rows, CapacityScenario(scale=1.0, requested_multiplier=1.0))


def test_capacity_rejects_mixed_instruments() -> None:
    rows = (_row(timestamp_ns=1), _row(timestamp_ns=2, instrument_id="ETHUSDT-PERP.BINANCE"))
    with pytest.raises(ValueError, match="UNSINGLE_INSTRUMENT_OBSERVATIONS"):
        measure_capacity(rows, CapacityScenario(scale=1.0, requested_multiplier=1.0))
