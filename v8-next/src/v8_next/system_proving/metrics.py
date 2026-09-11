"""14-metric system robustness vector — port of v8-core/src/system_proving/metrics.rs
(D-147, D-149, M3).

Field names are the Rust ones. The Rust invariant is carried over verbatim: the cashflow
discrepancy must be zero for valid double-entry reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass

DOUBLE_ENTRY_EPSILON = 1e-6


@dataclass(frozen=True)
class SystemRobustnessVector:
    scenario_failure_fraction: float
    tail_capture_efficiency: float
    friction_retention_ratio: float
    recovery_horizon_bars: int
    max_adverse_excursion_pct: float
    ruin_margin_pct: float
    slippage_fragility_score: float
    turnover_efficiency: float
    capital_utilization_pct: float
    funding_drag_ratio: float
    regime_stability_score: float
    habitat_selectivity_score: float
    expert_displacement_rate: float
    cashflow_discrepancy_usdt: float

    def is_double_entry_reconciled(self) -> bool:
        """Invariant: cashflow discrepancy must be zero for valid reconciliation."""
        return abs(self.cashflow_discrepancy_usdt) < DOUBLE_ENTRY_EPSILON

    def as_dict(self) -> dict[str, float | int]:
        return {
            field: getattr(self, field)
            for field in (
                "scenario_failure_fraction",
                "tail_capture_efficiency",
                "friction_retention_ratio",
                "recovery_horizon_bars",
                "max_adverse_excursion_pct",
                "ruin_margin_pct",
                "slippage_fragility_score",
                "turnover_efficiency",
                "capital_utilization_pct",
                "funding_drag_ratio",
                "regime_stability_score",
                "habitat_selectivity_score",
                "expert_displacement_rate",
                "cashflow_discrepancy_usdt",
            )
        }


def metrics_from_campaigns(
    *,
    campaigns: int,
    failures: int,
    gross_return_sum: float,
    fee_cost_sum: float,
    funding_cost_sum: float,
    max_drawdown_pct: float,
    bars: int,
    cashflow_discrepancy_usdt: float = 0.0,
) -> SystemRobustnessVector:
    """The Rust runner's own formulas, applied to a real run's totals.

    ``tail_capture_efficiency`` and ``friction_retention_ratio`` are the Rust expressions
    ((gross - fees)/gross, clamped) extended with funding, which the Rust side did not feed;
    the extension is declared here rather than silently folded into the fee number.
    """
    total = float(campaigns)
    fails = float(failures)
    fail_fraction = fails / total if total > 0 else 0.0
    net = gross_return_sum - fee_cost_sum - funding_cost_sum
    tce = (net / gross_return_sum) if abs(gross_return_sum) > DOUBLE_ENTRY_EPSILON else 0.0
    tce = min(1.0, max(0.0, tce))
    retention = (
        (gross_return_sum - fee_cost_sum - funding_cost_sum) / gross_return_sum
        if gross_return_sum > 0
        else 0.0
    )
    return SystemRobustnessVector(
        scenario_failure_fraction=fail_fraction,
        tail_capture_efficiency=tce,
        friction_retention_ratio=retention,
        recovery_horizon_bars=0,
        max_adverse_excursion_pct=max_drawdown_pct,
        ruin_margin_pct=max(0.0, 100.0 - max_drawdown_pct),
        slippage_fragility_score=min(1.0, max(0.0, net / (total * 100.0))) if total > 0 else 0.0,
        turnover_efficiency=min(1.0, total / max(1, bars)),
        capital_utilization_pct=min(100.0, abs(fee_cost_sum) * 100.0),
        funding_drag_ratio=min(1.0, abs(funding_cost_sum) / max(abs(gross_return_sum), DOUBLE_ENTRY_EPSILON)),
        regime_stability_score=min(1.0, max(0.0, 1.0 - fail_fraction)) if total > 0 else 1.0,
        habitat_selectivity_score=min(1.0, total / max(1, bars)),
        expert_displacement_rate=0.0,
        cashflow_discrepancy_usdt=cashflow_discrepancy_usdt,
    )
