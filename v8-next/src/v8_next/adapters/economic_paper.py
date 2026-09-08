"""Thin quote-to-economic-controller adapter for the local native paper engine."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Callable

from nautilus_trader.model import Currency, InstrumentId, QuoteTick, Venue

from v8_next.adapters.campaign import PaperCampaignAdapter
from v8_next.domain.market import CausalFrame
from v8_next.domain.positioning import PositioningReading
from v8_next.economics.controller import InstrumentConstraints, decide_campaign
from v8_next.economics.decisions import (
    Opportunity,
    UtilityInputs,
)
from v8_next.economics.grammar import POLICIES, grammar_opportunity
from v8_next.economics.observer_policy import policy_stances, validate_observer_policy
from v8_next.economics.protection import PROTECTION_POLICIES, protection_at
from v8_next.risk.admission import RiskLimits, RiskSnapshot
from v8_next.risk.sizing import StopBudget, StopExposure

CalibrationProvider = Callable[[Opportunity, int], tuple[UtilityInputs, bool]]


class EconomicPaperAdapter(PaperCampaignAdapter):
    def __new__(cls, *args: object, **kwargs: object) -> EconomicPaperAdapter:
        # The native Strategy allocator accepts only its engine config; domain
        # constructor arguments belong to Python __init__, not the native base.
        return super().__new__(cls)

    def __init__(
        self,
        frames: dict[int, CausalFrame],
        limits: RiskLimits,
        constraints: InstrumentConstraints,
        requested_notional: Decimal,
        calibration: CalibrationProvider | None = None,
        *,
        observer: str = "squeeze",
        grammar: str = "range-breakout-48-v1",
        campaign_policy: str = "timeout-only-v1",
        stop_budget: StopBudget | None = None,
        positioning_readings: tuple[PositioningReading, ...] = (),
    ) -> None:
        super().__init__(())
        self.observer = validate_observer_policy(observer)
        if grammar not in POLICIES:
            raise ValueError("unknown opportunity grammar")
        self.grammar = grammar
        if campaign_policy not in PROTECTION_POLICIES:
            raise ValueError("unknown campaign policy")
        self.campaign_policy = campaign_policy
        self.stop_budget = stop_budget
        self.positioning_readings = positioning_readings
        self.frames = frames
        self.limits = limits
        self.constraints = constraints
        self.requested_notional = requested_notional
        self.calibration = calibration
        self.decisions: list[dict[str, object]] = []
        self.allocated: set[str] = set()

    def on_start(self) -> None:
        self.subscribe_quotes(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))

    def on_quote(self, quote: QuoteTick) -> None:
        if self.callback_failure is not None:
            return
        try:
            self.process_economic_quote(quote)
        except Exception as error:
            if self.callback_failure is None:
                self.callback_failure = f"{type(error).__name__}: {error}"
            raise

    def process_economic_quote(self, quote: QuoteTick) -> None:
        super().on_quote(quote)
        if self.callback_failure is not None:
            return
        frame = self.frames.get(quote.ts_init)
        if frame is None:
            return
        opportunity = grammar_opportunity(frame, self.grammar)
        resolved = (
            opportunity
            if opportunity
            and opportunity.identity_status == "CANONICAL"
            and opportunity.direction in {"LONG", "SHORT"}
            else None
        )
        stances = policy_stances(frame, resolved, self.observer, readings=self.positioning_readings)
        stance = stances[0]
        record: dict[str, object] = {
            "decision_ns": quote.ts_init,
            "stance": asdict(stance),
            "stances": [asdict(s) for s in stances],
            "observer_policy": self.observer,
            "campaign_policy": self.campaign_policy,
            "opportunity": asdict(opportunity) if opportunity else None,
            "claim_status": "NO_ECONOMIC_CLAIM",
        }
        if not frame.candles or quote.ts_init - frame.candles[-1].end_ns > 2 * 3600 * 10**9:
            record["reason"] = "STALE_DATA"
        elif opportunity is None:
            record["reason"] = stance.reason
        elif resolved is None:
            record["reason"] = "UNRESOLVED_OPPORTUNITY_IDENTITY"
        elif (
            self.cache.positions_open()
            or self.cache.orders_open()
            or any(
                c.campaign_id not in self.submitted | self.expired | self.invalidated
                for c in self.campaigns
            )
        ):
            record["reason"] = "ONE_ACTIVE_EXPOSURE_LIMIT"
        elif self.cache.positions():
            # Closed positions can still have late funding liabilities. The online
            # account is not reconciled by the separate revised-accounting view.
            record["reason"] = "UNRECONCILED_FUNDING_AFTER_EXPOSURE"
        else:
            account = self.cache.account_for_venue(Venue("BINANCE"))
            if account is None:
                raise ValueError("native paper account unavailable")
            # Initial scope permits only one open campaign. Entry is considered
            # only when positions/orders are empty, so exposure and reservations
            # are observed zero, not guessed missing portfolio values.
            snapshot = RiskSnapshot(
                account.balance_total(Currency.from_str("USDT")).as_decimal(),
                Decimal(0),
                Decimal(0),
                Decimal(0),
                quote.ts_init,
                True,
            )
            utility, verified = (
                self.calibration(opportunity, quote.ts_init)
                if self.calibration
                else (UtilityInputs(None, None, None, None, None, None, None), False)
            )
            protection = None
            if self.campaign_policy != "timeout-only-v1":
                instrument = self.cache.instrument(quote.instrument_id)
                if instrument is None:
                    raise ValueError("protection instrument metadata missing")
                protection = protection_at(
                    frame,
                    opportunity,
                    self.campaign_policy,
                    instrument.price_increment.as_decimal(),
                )
                record["protection"] = (
                    {
                        k: str(v) if isinstance(v, Decimal) else v
                        for k, v in asdict(protection).items()
                    }
                    if protection
                    else None
                )
            decision = decide_campaign(
                opportunity,
                stances,
                utility,
                snapshot,
                self.limits,
                self.constraints,
                quote.ts_init,
                quote.ask_price.as_decimal()
                if opportunity.direction == "LONG"
                else quote.bid_price.as_decimal(),
                self.requested_notional,
                frozenset(self.allocated),
                calibration_verified=verified,
                protection=protection,
                protection_required=self.campaign_policy != "timeout-only-v1",
                stop_budget=self.stop_budget,
                stop_exposure=StopExposure(Decimal(0), 0, quote.ts_init, True)
                if self.stop_budget is not None
                else None,
            )
            record["reason"] = decision.reason
            if decision.campaign is not None:
                self.allocated.add(opportunity.opportunity_id)
                self.campaigns += (decision.campaign,)
                record["campaign_id"] = decision.campaign.campaign_id
        self.decisions.append(record)
