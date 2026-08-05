"""Discovery, retrieval, and composition recall against a gold set.

Separates the four evaluation views the specification names: retrieval gold
(can the system recover the right evidence range for a *known* finding),
discovery gold (can it find the finding *without being told*), composition
gold (multi-section reconstruction), and architecture-challenge gold.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GoldFinding:
    gold_id: str
    node_ids: list[str]
    description: str
    is_composition: bool = False
    is_architecture_challenge: bool = False


def retrieval_recall(gold: list[GoldFinding], recovered_node_ids: set[str]) -> dict:
    """Given the true node ids, did the system's marks/rereads touch them?"""
    hits = sum(1 for g in gold if set(g.node_ids) & recovered_node_ids)
    total = len(gold)
    return {"hits": hits, "total": total, "recall": round(hits / total, 4) if total else 0.0}


def discovery_recall(gold: list[GoldFinding], produced_finding_texts: list[str]) -> dict:
    """Crude containment check: did any produced finding statement overlap the gold text?"""
    blob = " ".join(t.lower() for t in produced_finding_texts)
    hits = sum(1 for g in gold if g.description.lower()[:40] in blob)
    total = len(gold)
    return {"hits": hits, "total": total, "recall": round(hits / total, 4) if total else 0.0}


def composition_recall(gold: list[GoldFinding], produced_finding_texts: list[str]) -> dict:
    composition_gold = [g for g in gold if g.is_composition]
    return discovery_recall(composition_gold, produced_finding_texts)


def architecture_challenge_recall(gold: list[GoldFinding], produced_finding_texts: list[str]) -> dict:
    challenge_gold = [g for g in gold if g.is_architecture_challenge]
    return discovery_recall(challenge_gold, produced_finding_texts)


def weighted_discovery_utility(
    findings: list[dict], machine_cost: float, human_time_cost: float
) -> float:
    """spec formula: Sigma(value * verification_quality * source_independence *
    discovery_credit) / (machine_cost + human_time_cost).

    Each finding dict carries preregistered_value, verification_quality,
    source_independence, and discovery_credit (1.0 unless split credit across
    multiple channels that found it independently).
    """
    numerator = sum(
        f["preregistered_value"]
        * f["verification_quality"]
        * f["source_independence"]
        * f.get("discovery_credit", 1.0)
        for f in findings
    )
    denominator = machine_cost + human_time_cost
    return round(numerator / denominator, 6) if denominator else 0.0
