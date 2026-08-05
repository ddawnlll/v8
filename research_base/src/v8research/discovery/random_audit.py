"""Channel F: stratified random audit.

v2's fatal gap: its "audit" was position-stratified but *deterministic*, so it
could not estimate silent misses -- deterministic sampling always hits the
same kind of passage. This module uses genuine randomness (seeded only for
run-to-run reproducibility of a given audit, per the determinism rule), spread
proportionally across the requested strata.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from ..contracts.structure import DocumentNode


@dataclass
class AuditSample:
    node_id: str
    stratum: str
    source_id: str


def stratify(nodes: list[DocumentNode], key: str) -> dict[str, list[DocumentNode]]:
    groups: dict[str, list[DocumentNode]] = defaultdict(list)
    for node in nodes:
        if key == "source":
            groups[node.source_id].append(node)
        elif key == "chapter":
            groups[node.parent_id or node.node_id].append(node)
        elif key == "page_bucket":
            page = node.page_start or 0
            groups[str(page // 20)].append(node)
        else:
            groups["_all"].append(node)
    return groups


def sample_audit(
    nodes: list[DocumentNode],
    *,
    run_id: str,
    fraction: float = 0.1,
    min_per_stratum: int = 1,
    strata_keys: tuple[str, ...] = ("source", "page_bucket"),
) -> list[AuditSample]:
    """Sample a fraction of nodes from every stratum, seeded by run_id.

    Genuinely randomised within a run (unlike v2's fixed positions), but
    reproducible across a replay of the same run_id -- satisfying both "random
    enough to estimate misses" and "queue replay reproduces task identity".
    """
    samples: list[AuditSample] = []
    seen: set[str] = set()
    for key in strata_keys:
        groups = stratify(nodes, key)
        for stratum, members in groups.items():
            rng = random.Random(f"{run_id}:{key}:{stratum}")
            count = max(min_per_stratum, int(len(members) * fraction))
            picked = rng.sample(members, k=min(count, len(members)))
            for node in picked:
                if node.node_id in seen:
                    continue
                seen.add(node.node_id)
                samples.append(AuditSample(node.node_id, f"{key}:{stratum}", node.source_id))
    return samples


def miss_rate(audited: list[AuditSample], missed_node_ids: set[str]) -> dict:
    total = len(audited)
    missed = sum(1 for s in audited if s.node_id in missed_node_ids)
    rate = missed / total if total else 0.0
    # A Wilson-ish crude bound; enough to report uncertainty without a stats dep.
    uncertainty = (rate * (1 - rate) / total) ** 0.5 if total else 0.0
    return {
        "audited": total,
        "missed": missed,
        "miss_rate": round(rate, 4),
        "uncertainty": round(uncertainty, 4),
    }
