"""Evaluation: gold sets, discovery/cost/audit metrics."""

from .audit_metrics import CompletionGateResult, check_discovery_recall, check_mandatory_coverage, check_resolution, completion_gate
from .cost_metrics import BaselineResult, compare_to_baselines, cost_per_high_value_finding, cost_per_verified_finding
from .discovery_metrics import (
    GoldFinding,
    architecture_challenge_recall,
    composition_recall,
    discovery_recall,
    retrieval_recall,
    weighted_discovery_utility,
)
from .gold import Adjudication, HumanReading, adjudicate

__all__ = [
    "Adjudication",
    "BaselineResult",
    "CompletionGateResult",
    "GoldFinding",
    "HumanReading",
    "adjudicate",
    "architecture_challenge_recall",
    "check_discovery_recall",
    "check_mandatory_coverage",
    "check_resolution",
    "compare_to_baselines",
    "completion_gate",
    "composition_recall",
    "cost_per_high_value_finding",
    "cost_per_verified_finding",
    "discovery_recall",
    "retrieval_recall",
    "weighted_discovery_utility",
]
