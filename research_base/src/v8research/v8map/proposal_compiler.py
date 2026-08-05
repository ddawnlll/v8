"""Research output compilation.

A verified finding may produce zero or more proposals. Every proposal binds
its supporting findings and stays separate from active runtime code: this
module never writes to `src/v8/`, only to the research registry.
"""

from __future__ import annotations

from ..contracts.enums import ImpactRelation, ProposalKind
from ..contracts.finding import Finding
from ..contracts.v8_impact import ResearchProposal, V8Impact

#: An impact relation that plausibly warrants each proposal kind. Advisory --
#: compile_proposals still requires the caller to supply the actual kind and
#: falsifiable prediction; this only prevents an obviously-mismatched pairing.
_PLAUSIBLE_RELATIONS: dict[ProposalKind, frozenset[ImpactRelation]] = {
    ProposalKind.EXPERT_HYPOTHESIS: frozenset({ImpactRelation.SUGGESTS_NEW_COMPONENT}),
    ProposalKind.RISK_RULE: frozenset({ImpactRelation.NARROWS, ImpactRelation.CHALLENGES}),
    ProposalKind.MARKETSTATE_OBSERVABLE: frozenset({ImpactRelation.REVEALS_MISSING_VARIABLE}),
    ProposalKind.CROSS_STRATEGY_INTERACTION: frozenset(
        {ImpactRelation.REVEALS_UNTESTED_INTERACTION}
    ),
    ProposalKind.ARCHITECTURE_CHALLENGE: frozenset(
        {ImpactRelation.REVEALS_INVALID_ABSTRACTION, ImpactRelation.CHALLENGES}
    ),
    ProposalKind.EXPERIMENT_PREREGISTRATION: frozenset(ImpactRelation),
    ProposalKind.NO_CURRENT_V8_COMPILATION: frozenset({ImpactRelation.NO_IMPACT}),
}


def compile_proposal(
    kind: ProposalKind,
    title: str,
    body: str,
    finding: Finding,
    impact: V8Impact,
    *,
    falsifiable_prediction: str = "",
    required_observables: list[str] | None = None,
) -> ResearchProposal:
    allowed = _PLAUSIBLE_RELATIONS.get(kind)
    if allowed is not None and impact.relation not in allowed:
        raise ValueError(
            f"{kind} is not a plausible proposal for impact relation {impact.relation}"
        )
    return ResearchProposal(
        proposal_id=ResearchProposal.make_id(kind, title),
        kind=kind,
        title=title,
        body=body,
        supporting_finding_ids=[finding.finding_id],
        related_assumption_ids=[impact.assumption_id],
        falsifiable_prediction=falsifiable_prediction,
        required_observables=required_observables or [],
    )


def no_compilation(finding: Finding, impact: V8Impact) -> ResearchProposal:
    """The explicit "we looked, and there is nothing to propose" record."""
    return compile_proposal(
        ProposalKind.NO_CURRENT_V8_COMPILATION,
        title=f"No V8 compilation for {finding.finding_id}",
        body=impact.rationale or "No current runtime implication identified.",
        finding=finding,
        impact=impact,
    )
