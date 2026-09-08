"""Ordered economic admission. This module does not mint evidence authority."""

from dataclasses import dataclass
from decimal import Decimal

from v8_next.domain.campaign import PaperCampaign
from v8_next.economics.decisions import (
    Opportunity,
    Stance,
    UtilityInputs,
    reconcile,
    utility_admission,
)
from v8_next.risk.admission import RiskLimits, RiskSnapshot, admit


@dataclass(frozen=True)
class InstrumentConstraints:
    step: Decimal
    min_quantity: Decimal
    max_quantity: Decimal
    min_notional: Decimal


@dataclass(frozen=True)
class CampaignDecision:
    reason: str
    campaign: PaperCampaign | None = None


def decide_campaign(
    opportunity: Opportunity,
    stances: tuple[Stance, ...],
    utility: UtilityInputs,
    snapshot: RiskSnapshot,
    limits: RiskLimits,
    constraints: InstrumentConstraints,
    decision_ns: int,
    price: Decimal,
    requested_notional: Decimal,
    already_allocated: frozenset[str],
    *,
    calibration_verified: bool,
) -> CampaignDecision:
    """Caller must verify calibration provenance and reserve admitted risk atomically.

    A true verification flag is not a certificate or a way to promote economic
    claims. The app must supply it only from the calibration verification boundary.
    Until that boundary exists, production callers must leave it false.
    """
    if opportunity.identity_status != "CANONICAL" or opportunity.direction not in {"LONG", "SHORT"}:
        return CampaignDecision("UNRESOLVED_OPPORTUNITY_IDENTITY")
    if opportunity.opportunity_id in already_allocated:
        return CampaignDecision("DUPLICATE_OPPORTUNITY")
    if decision_ns < opportunity.anchor_ns:
        return CampaignDecision("FUTURE_OPPORTUNITY")
    if decision_ns >= opportunity.expires_ns:
        return CampaignDecision("EXPIRED")
    if any(s.decision_ns > decision_ns for s in stances):
        return CampaignDecision("FUTURE_EVIDENCE")
    reconciled = reconcile(opportunity, stances)
    if reconciled != "SUPPORTED_OBSERVATION":
        return CampaignDecision(reconciled)
    if not calibration_verified:
        return CampaignDecision("UNVERIFIED_CALIBRATION")
    utility_result = utility_admission(utility)
    if utility_result != "UTILITY_ELIGIBLE":
        return CampaignDecision(utility_result)
    admitted = admit(
        snapshot,
        limits,
        decision_ns,
        price,
        requested_notional,
        constraints.step,
        constraints.min_quantity,
        constraints.max_quantity,
        constraints.min_notional,
    )
    if admitted.quantity is None:
        return CampaignDecision(admitted.reason)
    return CampaignDecision(
        "PAPER_CAMPAIGN_ADMITTED",
        PaperCampaign(
            "paper-" + opportunity.opportunity_id,
            opportunity.opportunity_id,
            opportunity.instrument_id,
            opportunity.direction,
            admitted.quantity,
            decision_ns,
            opportunity.expires_ns,
        ),
    )
