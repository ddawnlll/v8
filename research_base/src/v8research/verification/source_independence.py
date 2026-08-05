"""Source independence and finding materialisation.

Popularity is not evidence strength (rule 13): raw source count and
independent lineage count are always reported as a pair, and
`materialize_finding` is the only place a Finding is constructed.
"""

from __future__ import annotations

from ..contracts.claim import Claim, Verification
from ..contracts.finding import Finding
from ..contracts.enums import FindingStatus
from ..ingest.lineage import LineageGraph


def source_independence_score(source_ids: list[str], graph: LineageGraph) -> float:
    raw, independent = graph.counts(source_ids)
    return round(independent / raw, 4) if raw else 0.0


def verification_quality(verifications: list[Verification]) -> float:
    if not verifications:
        return 0.0
    passed = sum(1 for v in verifications if v.passed)
    return round(passed / len(verifications), 4)


def materialize_finding(
    finding_statement: str,
    claims: list[Claim],
    verifications: list[Verification],
    *,
    lineage_graph: LineageGraph,
    preregistered_value: int = 1,
    known_counterevidence_ids: tuple[str, ...] = (),
    decision_relevance_without_v8: str = "",
) -> Finding | None:
    """Only claims with a passing verification may enter a Finding.

    Returns None rather than a low-quality Finding when nothing passed --
    callers should route the claims to CONTESTED/REJECTED handling instead.
    """
    passing_claim_ids = {v.claim_id for v in verifications if v.passed}
    used_claims = [c for c in claims if c.claim_id in passing_claim_ids]
    if not used_claims:
        return None

    source_ids = sorted({c.source_id for c in used_claims})
    independence = source_independence_score(source_ids, lineage_graph)
    quality = verification_quality([v for v in verifications if v.claim_id in passing_claim_ids])

    status = FindingStatus.VERIFIED if quality >= 1.0 else FindingStatus.PROVISIONAL
    claim_ids = tuple(sorted(c.claim_id for c in used_claims))
    finding = Finding(
        finding_id=Finding.make_id(finding_statement, claim_ids),
        finding_statement=finding_statement,
        claim_ids=claim_ids,
        source_ids=tuple(source_ids),
        independent_lineage_ids=tuple(lineage_graph.independent_lineages(source_ids)),
        decision_relevance_without_v8=decision_relevance_without_v8,
        verification_quality=quality,
        source_independence=independence,
        preregistered_value=preregistered_value,
        known_counterevidence_ids=known_counterevidence_ids,
        status=status,
    )
    return finding.with_hash()
