"""The V8 assumption registry.

Converts existing V8 architectural propositions into a queryable registry.
This module owns no discovery logic -- it is populated once from the project's
own contracts (see `tools/seed_assumptions.py`) and updated only by attaching
finding ids to the relevant list.
"""

from __future__ import annotations

from ..contracts.enums import AssumptionStatus
from ..contracts.v8_impact import V8Assumption


def new_assumption(
    statement: str,
    status: AssumptionStatus,
    component_ids: list[str] | None = None,
) -> V8Assumption:
    return V8Assumption(
        assumption_id=V8Assumption.make_id(statement),
        statement=statement,
        status=status,
        component_ids=component_ids or [],
    )


_RELATION_TO_LIST = {
    "SUPPORTS": "supporting_finding_ids",
    "CHALLENGES": "challenging_finding_ids",
    "NARROWS": "narrowing_finding_ids",
    "REVEALS_MISSING_VARIABLE": "missing_variable_finding_ids",
    "REVEALS_UNTESTED_INTERACTION": "untested_interaction_finding_ids",
}


def attach_finding(assumption: V8Assumption, finding_id: str, relation: str) -> V8Assumption:
    """Append a finding id to the list matching its impact relation.

    Relations without a dedicated list (REQUIRES_EXTENSION,
    REVEALS_INVALID_ABSTRACTION, SUGGESTS_NEW_COMPONENT,
    SUGGESTS_COMPONENT_REMOVAL, NO_IMPACT) are recorded only via the
    V8Impact edge, not on the assumption itself -- the assumption's own lists
    track only the relations that directly bear on its truth.
    """
    field_name = _RELATION_TO_LIST.get(relation)
    if field_name is None:
        return assumption
    target = getattr(assumption, field_name)
    if finding_id not in target:
        target.append(finding_id)
    return assumption
