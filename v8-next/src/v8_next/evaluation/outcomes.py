"""Observed native campaign outcomes, not estimated edge or a calibration receipt."""

import hashlib
from decimal import Decimal
from typing import Any

import numpy as np
from nautilus_trader.model import Money

from v8_next.evaluation.store import canonical


def observed_outcomes(
    campaigns: list[dict[str, Any]],
    closures: list[dict[str, Any]],
    account: dict[str, Any],
    initial_balance: Decimal,
    *,
    economic_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Caller verifies/replays sources. Native net PnL already includes costs.

    Closed-position events retain separate campaigns when a netting cache ID is
    reused. Unfilled/open selections are kept as missing returns, never zeros.
    """
    if not initial_balance.is_finite() or initial_balance <= 0:
        raise ValueError("positive initial capital required")
    if account.get("currency") != "USDT" or account.get("realization") != "SIMULATED":
        raise ValueError("unsupported outcome account")
    by_id = {c["campaign_id"]: c for c in campaigns}
    if len(by_id) != len(campaigns):
        raise ValueError("duplicate outcome campaign")
    closed = {}
    for event in closures:
        key = event["campaign_id"]
        if key not in by_id or key in closed:
            raise ValueError("unknown or repeated campaign closure")
        campaign = by_id[key]
        if (
            event["instrument_id"] != campaign["instrument_id"]
            or event["opening_order_id"] != key
            or event["entry_side"] != ("BUY" if campaign["direction"] == "LONG" else "SELL")
            or not campaign["decision_ns"]
            < event["opened_ns"]
            <= event["closed_ns"]
            <= event["observed_ns"]
        ):
            raise ValueError("closure ownership or timing mismatch")
        closed[key] = event

    def cash(value: str) -> Decimal:
        money = Money.from_str(value)
        if str(money.currency) != "USDT":
            raise ValueError("outcome currency mismatch")
        return money.as_decimal()

    policy_hash = (
        hashlib.sha256(canonical(economic_policy).encode()).hexdigest() if economic_policy else None
    )
    rows, returns = [], []
    net_total = Decimal(0)
    for key, campaign in by_id.items():
        row: dict[str, Any] = {
            "campaign_id": key,
            "economic_policy_sha256": policy_hash,
            "opportunity_id": campaign["opportunity_id"],
            "decision_ns": campaign["decision_ns"],
            "instrument_id": campaign["instrument_id"],
            "direction": campaign["direction"],
            "status": "NO_CLOSED_NATIVE_OUTCOME",
            "net_return_on_entry_notional": None,
            "initial_filled_stop_risk": None,
            "net_r": None,
            "r_status": "NO_CLOSED_PROTECTED_OUTCOME",
        }
        outcome = closed.get(key)
        if outcome is not None:
            notional = Decimal(outcome["average_open_price"]) * Decimal(outcome["peak_quantity"])
            if not notional.is_finite() or notional <= 0:
                raise ValueError("invalid native entry notional")
            net = cash(outcome["realized_pnl"])
            fees = sum((cash(c) for c in outcome["commissions"]), Decimal(0))
            funding = sum(
                (
                    cash(a["pnl_change"])
                    for a in outcome["adjustments"]
                    if a["adjustment_type"] == "FUNDING" and a["pnl_change"] is not None
                ),
                Decimal(0),
            )
            other_adjustments = sum(
                (
                    cash(a["pnl_change"])
                    for a in outcome["adjustments"]
                    if a["adjustment_type"] != "FUNDING" and a["pnl_change"] is not None
                ),
                Decimal(0),
            )
            funding_known = all(
                a["pnl_change"] is not None
                for a in outcome["adjustments"]
                if a["adjustment_type"] == "FUNDING"
            )
            other_known = all(
                a["pnl_change"] is not None
                for a in outcome["adjustments"]
                if a["adjustment_type"] != "FUNDING"
            )
            components_known = funding_known and other_known
            price_pnl = net + fees - funding - other_adjustments if components_known else None
            value = net / notional
            returns.append(float(value))
            net_total += net
            if campaign.get("stop_price") is not None:
                stop = Decimal(campaign["stop_price"])
                entry = Decimal(outcome["average_open_price"])
                quantity = Decimal(outcome["peak_quantity"])
                distance = (entry - stop) * (1 if campaign["direction"] == "LONG" else -1)
                if not stop.is_finite() or stop <= 0:
                    raise ValueError("invalid original campaign stop")
                if distance > 0:
                    risk = distance * quantity
                    row.update(
                        initial_filled_stop_risk=str(risk),
                        net_r=str(net / risk),
                        r_status="COMPUTED_FROM_FILLED_ENTRY_AND_ORIGINAL_STOP",
                    )
                else:
                    row["r_status"] = "ENTRY_AT_OR_BEYOND_ORIGINAL_STOP"
            else:
                row["r_status"] = "ORIGINAL_STOP_UNAVAILABLE"

            row.update(
                status="CLOSED_UNDER_NATIVE_MODEL",
                entry_notional=str(notional),
                native_net_pnl=str(net),
                observed_commissions=str(fees),
                observed_funding_pnl=str(funding) if funding_known else None,
                observed_other_adjustment_pnl=str(other_adjustments) if other_known else None,
                native_price_pnl=str(price_pnl) if price_pnl is not None else None,
                price_return_on_entry_notional=str(price_pnl / notional)
                if price_pnl is not None
                else None,
                commission_fraction=str(fees / notional),
                funding_return_on_entry_notional=str(funding / notional) if funding_known else None,
                other_adjustment_return_on_entry_notional=str(other_adjustments / notional)
                if other_known
                else None,
                component_status="DECOMPOSED_NATIVE_PNL"
                if components_known
                else "MISSING_ADJUSTMENT_PNL",
                net_return_on_entry_notional=str(value),
                opened_ns=outcome["opened_ns"],
                closed_ns=outcome["closed_ns"],
                observed_ns=outcome["observed_ns"],
            )
        rows.append(row)
    cash_change = cash(account["balance_total"]) - initial_balance
    residual = cash_change - net_total
    terminal = all(p["is_closed"] for p in account["positions"]) and all(
        o["status"] in {"FILLED", "CANCELED", "REJECTED", "DENIED", "EXPIRED"}
        for o in account["orders"]
    )
    reconciled = terminal and residual == 0
    risk_values = [Decimal(row["net_r"]) for row in rows if row["net_r"] is not None]
    risk_complete = bool(rows) and len(risk_values) == len(rows) and reconciled

    return {
        "rows": rows,
        "selected_campaign_count": len(rows),
        "risk_unit_scorecard": {
            "mean_net_r": str(sum(risk_values, Decimal(0)) / len(risk_values))
            if risk_complete
            else None,
            "observed_r_count": len(risk_values),
            "missing_r_count": len(rows) - len(risk_values),
            "status": "COMPLETE_SELECTED_COHORT"
            if risk_complete
            else "INCOMPLETE_OR_UNRECONCILED_COHORT",
            "weighting": "equal_per_selected_campaign",
            "basis": "actual_filled_entry_to_original_stop",
            "scope": "DESCRIPTIVE_REALIZED_MODEL_R_NOT_EXPECTED_EDGE",
        },
        "closed_outcome_count": len(returns),
        "missing_outcome_count": len(rows) - len(returns),
        "native_closed_net_pnl": str(net_total),
        "native_cash_change": str(cash_change),
        "cash_reconciliation_residual": str(residual),
        "reconciliation": "CLOSED_CASH_RECONCILED" if reconciled else "OPEN_OR_UNRECONCILED",
        "conditional_mean_closed_return": float(np.mean(returns))
        if returns and reconciled
        else None,
        "calibration_eligible": False,
        "claim_status": "NO_ECONOMIC_CLAIM",
        "scope": "DESCRIPTIVE_NATIVE_MODEL_OUTCOMES_NOT_POLICY_EDGE",
        "limitations": [
            "closed_sample_conditions_on_execution_and_completion",
            "correlated_or_overlapping_samples_not_independent",
            "observed_funding_is_not_venue_finality",
            "native_execution_assumptions_not_measured_costs",
        ],
    }
