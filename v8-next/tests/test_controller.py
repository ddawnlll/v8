from dataclasses import replace
from decimal import Decimal as D

from v8_next.economics.controller import InstrumentConstraints, decide_campaign
from v8_next.economics.decisions import Opportunity, Stance, StanceKind, UtilityInputs
from v8_next.risk.admission import RiskLimits, RiskSnapshot


def decision(*, verified=True, allocated=frozenset(), stance_ns=10, expires=100):
    opportunity = Opportunity("o", "btc", "BTCUSDT-PERP.BINANCE", "LONG", 1, expires)
    stance = Stance("observer", "group", StanceKind.SUPPORT, "setup", "o", stance_ns)
    return decide_campaign(
        opportunity,
        (stance, replace(stance, observer_id="clone")),
        UtilityInputs(D(10), D(1), D(1), D(1), D(1), D(1), "test-only"),
        RiskSnapshot(D(1000), D(0), D(0), D(0), 10, True),
        RiskLimits(D(1), D("0.5"), D(100), 10),
        InstrumentConstraints(D("0.01"), D("0.01"), D(100), D(10)),
        10,
        D(100),
        D(100),
        allocated,
        calibration_verified=verified,
    )


def test_complete_admission_chain_creates_one_campaign():
    result = decision()
    assert result.campaign.quantity == D(1)
    assert result.campaign.opportunity_id == "o"
    assert decision(allocated=frozenset({"o"})).reason == "DUPLICATE_OPPORTUNITY"


def test_missing_authority_future_evidence_and_expiry_reject():
    assert decision(verified=False).reason == "UNVERIFIED_CALIBRATION"
    assert decision(stance_ns=11).reason == "FUTURE_EVIDENCE"
    assert decision(expires=10).reason == "EXPIRED"
