"""Constrained reread selection.

Reread scheduling is a constrained selection problem, not a single weighted
score. This module implements the objective and constraints from the
specification's CONSTRAINED_REREAD_SELECTION section as a greedy knapsack:
optimal ILP is not worth the dependency for a queue this shape, and a greedy
pass that respects every floor/ceiling is auditable, which matters more here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.reread import RereadTask


@dataclass
class SelectionConstraints:
    token_budget: int
    min_book_coverage: dict[str, int] = field(default_factory=dict)  # source_id -> min tasks
    min_random_audit_share: float = 0.10
    min_rare_share: float = 0.10
    min_contradiction_share: float = 0.10
    max_single_cluster_share: float = 0.20


@dataclass
class Scored:
    task: RereadTask
    source_id: str
    cluster_id: str
    is_random_audit: bool
    is_rare: bool
    is_contradiction: bool
    expected_value: float


def score(
    *,
    resolution_probability: float,
    finding_value_if_resolved: float,
    source_independence: float,
    downstream_experiment_value: float,
    expected_machine_cost: float,
    expected_human_review_cost: float,
) -> float:
    """spec formula, verbatim."""
    return (
        resolution_probability
        * finding_value_if_resolved
        * source_independence
        * downstream_experiment_value
        - expected_machine_cost
        - expected_human_review_cost
    )


def select(candidates: list[Scored], constraints: SelectionConstraints) -> list[RereadTask]:
    """Greedy selection that fills protected quotas first, then value order.

    This estimate orders work; it never defines completion (spec) -- the
    caller is responsible for treating an empty or partial selection as
    PAUSED_RESOURCE_LIMIT, not COMPLETE.
    """
    if not candidates:
        return []

    budget = constraints.token_budget
    selected: list[Scored] = []
    remaining = sorted(candidates, key=lambda c: -c.expected_value)
    cluster_tokens: dict[str, int] = {}
    total_tokens_target = max(1, sum(c.task.estimated_tokens for c in candidates))

    def cost(item: Scored) -> int:
        return max(1, item.task.estimated_tokens)

    def cluster_cap_ok(item: Scored) -> bool:
        used = cluster_tokens.get(item.cluster_id, 0)
        cap = constraints.max_single_cluster_share * total_tokens_target
        return used + cost(item) <= cap or used == 0

    # Pass 1: protected quotas (random audit, rare, contradiction), cheapest-
    # value-per-token first within each quota so protection does not waste
    # the whole budget on one expensive item.
    quotas = [
        (constraints.min_random_audit_share, lambda c: c.is_random_audit),
        (constraints.min_rare_share, lambda c: c.is_rare),
        (constraints.min_contradiction_share, lambda c: c.is_contradiction),
    ]
    spent = 0
    picked_ids: set[str] = set()
    for share, predicate in quotas:
        quota_budget = int(budget * share)
        quota_spent = 0
        pool = [c for c in remaining if predicate(c) and c.task.reread_id not in picked_ids]
        pool.sort(key=lambda c: -c.expected_value)
        for item in pool:
            if quota_spent + cost(item) > quota_budget:
                continue
            if not cluster_cap_ok(item):
                continue
            selected.append(item)
            picked_ids.add(item.task.reread_id)
            quota_spent += cost(item)
            spent += cost(item)
            cluster_tokens[item.cluster_id] = cluster_tokens.get(item.cluster_id, 0) + cost(item)

    # Pass 2: minimum per-source coverage.
    by_source: dict[str, list[Scored]] = {}
    for item in remaining:
        by_source.setdefault(item.source_id, []).append(item)
    for source_id, minimum in constraints.min_book_coverage.items():
        have = sum(1 for s in selected if s.source_id == source_id)
        pool = sorted(
            (c for c in by_source.get(source_id, []) if c.task.reread_id not in picked_ids),
            key=lambda c: -c.expected_value,
        )
        for item in pool:
            if have >= minimum:
                break
            if spent + cost(item) > budget or not cluster_cap_ok(item):
                continue
            selected.append(item)
            picked_ids.add(item.task.reread_id)
            spent += cost(item)
            cluster_tokens[item.cluster_id] = cluster_tokens.get(item.cluster_id, 0) + cost(item)
            have += 1

    # Pass 3: remaining budget by pure value order.
    for item in remaining:
        if item.task.reread_id in picked_ids:
            continue
        if spent + cost(item) > budget:
            continue
        if not cluster_cap_ok(item):
            continue
        selected.append(item)
        picked_ids.add(item.task.reread_id)
        spent += cost(item)
        cluster_tokens[item.cluster_id] = cluster_tokens.get(item.cluster_id, 0) + cost(item)

    return [s.task for s in selected]
