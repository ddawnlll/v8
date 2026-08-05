"""Cost/quality frontier comparisons against the specification's baselines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaselineResult:
    name: str
    recall: float
    cost_per_finding: float
    human_review_minutes: float


def cost_per_verified_finding(total_cost: float, verified_finding_count: int) -> float:
    return round(total_cost / verified_finding_count, 4) if verified_finding_count else float("inf")


def cost_per_high_value_finding(
    total_cost: float, findings: list[dict], value_threshold: int = 5
) -> float:
    high_value = sum(1 for f in findings if f.get("preregistered_value", 0) >= value_threshold)
    return round(total_cost / high_value, 4) if high_value else float("inf")


def compare_to_baselines(system_result: BaselineResult, baselines: list[BaselineResult]) -> dict:
    return {
        "system": system_result,
        "baselines": baselines,
        "recall_delta": {
            b.name: round(system_result.recall - b.recall, 4) for b in baselines
        },
        "cost_delta": {
            b.name: round(system_result.cost_per_finding - b.cost_per_finding, 4) for b in baselines
        },
    }
