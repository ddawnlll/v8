from copy import deepcopy

import pytest

from v8_next.evaluation.component_estimates import estimate_components


def sample():
    return dict(
        reconciliation="CLOSED_CASH_RECONCILED",
        rows=[
            dict(
                campaign_id=str(i),
                instrument_id="BTCUSDT-PERP.BINANCE",
                direction="LONG",
                status="CLOSED_UNDER_NATIVE_MODEL",
                opened_ns=i + 1,
                closed_ns=i + 10,
                observed_ns=20,
                entry_notional="1",
                native_price_pnl=str(i),
                observed_commissions="1",
                observed_funding_pnl="0",
                observed_other_adjustment_pnl="0",
                native_net_pnl=str(i - 1),
                price_return_on_entry_notional=str(i),
                commission_fraction="1",
                funding_return_on_entry_notional="0",
                other_adjustment_return_on_entry_notional="0",
                net_return_on_entry_notional=str(i - 1),
            )
            for i in range(4)
        ],
    )


def test_joint_components_preserve_cost_relation_and_deterministic_uncertainty():
    a = estimate_components(sample(), decision_ns=30, block_size=2, reps=99, seed=7)
    assert a == estimate_components(sample(), decision_ns=30, block_size=2, reps=99, seed=7)
    estimates = a["estimates"]
    assert estimates["price_return_on_entry_notional"]["mean"] == 1.5
    assert estimates["net_return_on_entry_notional"]["mean"] == 0.5
    assert estimates["commission_fraction"]["mean_standard_error"] == 0
    assert (
        estimates["price_return_on_entry_notional"]["mean_standard_error"]
        == estimates["net_return_on_entry_notional"]["mean_standard_error"]
    )
    assert a["eligible_for_utility"] is False


def test_incomplete_sample_and_unreconciled_fractions_cannot_supply_estimate():
    data = sample()
    data["rows"][0]["status"] = "NO_CLOSED_NATIVE_OUTCOME"
    assert (
        estimate_components(data, decision_ns=30, block_size=2, reps=99, seed=7)["estimates"]
        is None
    )
    data = deepcopy(sample())
    data["rows"][0]["net_return_on_entry_notional"] = "999"
    with pytest.raises(ValueError, match="fractions"):
        estimate_components(data, decision_ns=30, block_size=2, reps=99, seed=7)
    with pytest.raises(ValueError, match="future"):
        estimate_components(sample(), decision_ns=20, block_size=2, reps=99, seed=7)


@pytest.mark.parametrize(
    "change",
    [{"instrument_id": "ETHUSDT-PERP.BINANCE"}, {"direction": "SHORT"}, {"direction": None}],
)
def test_component_estimates_do_not_pool_unlike_or_unknown_cohorts(change):
    data = sample()
    data["rows"][0].update(change)
    report = estimate_components(data, decision_ns=30, block_size=2, reps=99, seed=7)
    assert report["estimates"] is None
    assert report["reason"] in {
        "EXPLICIT_COHORT_CONDITIONING_REQUIRED",
        "COHORT_IDENTITY_UNAVAILABLE",
    }
