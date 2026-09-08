"""Ordered economic allocation over one reconciled portfolio snapshot.

Caller supplies explicit priority and owns atomic application of the returned
reservations. This module neither executes orders nor invents calibrated utility.
"""

from dataclasses import dataclass, replace
from decimal import Decimal

from v8_next.economics.controller import CampaignDecision, InstrumentConstraints, decide_campaign
from v8_next.economics.decisions import Opportunity, Stance, UtilityInputs
from v8_next.economics.protection import CampaignProtection
from v8_next.risk.admission import RiskLimits, RiskSnapshot


@dataclass(frozen=True)
class AllocationProposal:
    opportunity: Opportunity
    stances: tuple[Stance, ...]
    utility: UtilityInputs
    calibration_verified: bool
    constraints: InstrumentConstraints
    price: Decimal
    requested_notional: Decimal
    protection: CampaignProtection


def allocate_ordered(
    proposals: tuple[AllocationProposal, ...],
    snapshots: dict[str, RiskSnapshot],
    limits: RiskLimits,
    *,
    decision_ns: int,
    already_allocated: frozenset[str],
) -> tuple[CampaignDecision, ...]:
    """Input order is the declared priority, never implicitly sorted by votes.

    Exposure snapshots share one global account state. Initial scalar reservation
    semantics conservatively charge all existing reservations to every exposure;
    newly accepted notional is likewise charged globally before the next proposal.
    Native multi-instrument execution still requires separate qualification.
    """
    used = set(already_allocated)
    reserved = Decimal(0)
    results = []
    account_state = None
    for proposal in proposals:
        exposure = proposal.opportunity.exposure_id
        if exposure not in snapshots:
            raise ValueError("missing exposure snapshot")
        snapshot = snapshots[exposure]
        identity = (
            snapshot.equity,
            snapshot.gross_notional,
            snapshot.reserved_notional,
            snapshot.as_of_ns,
            snapshot.reconciled,
        )
        if account_state is None:
            account_state = identity
        elif identity != account_state:
            raise ValueError("allocation snapshots disagree on global account state")
        decision = decide_campaign(
            proposal.opportunity,
            proposal.stances,
            proposal.utility,
            replace(snapshot, reserved_notional=snapshot.reserved_notional + reserved),
            limits,
            proposal.constraints,
            decision_ns,
            proposal.price,
            proposal.requested_notional,
            frozenset(used),
            calibration_verified=proposal.calibration_verified,
            protection=proposal.protection,
            protection_required=True,
        )
        results.append(decision)
        if decision.campaign is not None:
            reserved += decision.campaign.quantity * proposal.price
            used.add(proposal.opportunity.opportunity_id)
    return tuple(results)
