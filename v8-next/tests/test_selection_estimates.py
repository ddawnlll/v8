from copy import deepcopy

import pytest

from v8_next.evaluation.selection_estimates import estimate_selection_cash


def test_selection_estimate_keeps_nonentries_in_denominator_and_rejects_missing_cash():
    source = dict(
        reconciliation="CLOSED_CASH_RECONCILED",
        native_cash_change="6",
        selection_cash_scorecard=dict(
            status="COMPLETE_SELECTED_COHORT",
            initial_capital="100",
            mean_cash_return_per_selection="0.015",
        ),
        rows=[
            dict(
                campaign_id=str(i),
                decision_ns=i,
                economic_policy_sha256="a" * 64,
                status="TERMINAL_WITHOUT_ENTRY" if i == 0 else "CLOSED_UNDER_NATIVE_MODEL",
                native_net_pnl=None if i == 0 else str(i),
            )
            for i in range(4)
        ],
    )
    plan = dict(block_size=2, reps=99, seed=7)
    result = estimate_selection_cash(source, **plan)
    assert result == estimate_selection_cash(source, **plan)
    assert result["sample_count"] == 4
    assert result["estimate"]["mean"] == pytest.approx(0.015)
    assert result["estimate"]["mean_standard_error"] > 0
    assert result["eligible_for_utility"] is False
    missing = deepcopy(source)
    missing["rows"][0]["status"] = "NO_CLOSED_NATIVE_OUTCOME"
    assert estimate_selection_cash(missing, **plan)["estimate"] is None
    bad = deepcopy(source)
    bad["native_cash_change"] = "7"
    with pytest.raises(ValueError, match="reconcile"):
        estimate_selection_cash(bad, **plan)
    mixed = deepcopy(source)
    mixed["rows"][0]["economic_policy_sha256"] = "b" * 64
    assert estimate_selection_cash(mixed, **plan)["estimate"] is None
