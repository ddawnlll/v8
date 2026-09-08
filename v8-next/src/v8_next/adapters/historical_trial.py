"""Offline policy experiment. Never a calibrated economic admission path."""

from dataclasses import asdict, replace
from decimal import Decimal
from typing import Any

from nautilus_trader.model import Bar, BarType, Currency, Venue

from v8_next.adapters.campaign import PaperCampaignAdapter
from v8_next.adapters.portfolio_equity import EquityMark, native_equity
from v8_next.domain.campaign import PaperCampaign
from v8_next.domain.config import PaperConfig
from v8_next.domain.market import Candle, frame_at
from v8_next.economics.decisions import reconcile
from v8_next.economics.grammar import grammar_opportunity
from v8_next.economics.observer_policy import policy_stances
from v8_next.economics.protection import protection_at
from v8_next.risk.admission import RiskLimits, RiskSnapshot, admit
from v8_next.risk.sizing import StopExposure, stop_budget_notional


class HistoricalTrial(PaperCampaignAdapter):
    """Counterfactual policy application to native real-bar replay, not edge authority.

    Positions are experimental responses to a frozen rule. No utility estimate,
    calibration receipt, quote or synthetic market input is fabricated. Missing
    historical availability and microstructure keep results diagnostic only.
    """

    def __new__(cls, *args: object, **kwargs: object) -> "HistoricalTrial":
        return super().__new__(cls)

    def __init__(self, source: tuple[Candle, ...], policy: PaperConfig) -> None:
        super().__init__(())
        self.source = {c.end_ns: c for c in source}
        if len(self.source) != len(source):
            raise ValueError("duplicate trial candle boundary")
        self.prefix: list[Candle] = []
        self.policy = policy
        self.decisions: list[dict[str, Any]] = []
        self.equity_marks: list[dict[str, Any]] = []
        self.failure: str | None = None

    def on_start(self) -> None:
        self.subscribe_bars(BarType.from_str("BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"))

    def on_bar(self, bar: Bar) -> None:
        if self.failure is not None:
            return
        try:
            self.process_bar(bar)
        except Exception as error:
            self.failure = f"{type(error).__name__}: {error}"
            raise

    def process_bar(self, bar: Bar) -> None:
        self.mark_equity(bar)
        candle = self.source[bar.ts_event]
        self.prefix.append(replace(candle, available_ns=candle.end_ns))
        frame = frame_at(candle.instrument_id, bar.ts_init, tuple(self.prefix))
        self.observe_validity(frame)
        # Prior decisions execute no earlier than the NEXT real bar close. The
        # native bar model supplies fills; no synthetic QuoteTick is constructed.
        self.advance_campaigns(
            bar.bar_type.instrument_id, bar.ts_init, bar.close.as_decimal(), bar.close.as_decimal()
        )
        opportunity = grammar_opportunity(frame, self.policy.grammar_policy)
        record: dict[str, Any] = {
            "decision_ns": bar.ts_init,
            "opportunity": asdict(opportunity) if opportunity else None,
            "authority": "OFFLINE_COUNTERFACTUAL",
            "claim_status": "NO_ECONOMIC_CLAIM",
        }
        self.decisions.append(record)
        if (
            opportunity is None
            or opportunity.identity_status != "CANONICAL"
            or opportunity.direction not in {"LONG", "SHORT"}
        ):
            record["reason"] = "NO_CANONICAL_DIRECTIONAL_OPPORTUNITY"
            return
        stances = policy_stances(frame, opportunity, self.policy.observer_policy)
        record["stances"] = [asdict(s) for s in stances]
        result = reconcile(opportunity, stances)
        if result != "SUPPORTED_OBSERVATION":
            record["reason"] = result
            return
        pending = any(
            c.campaign_id not in self.submitted | self.expired | self.invalidated
            for c in self.campaigns
        )
        if self.cache.positions_open() or self.cache.orders_open() or pending:
            record["reason"] = "EXPERIMENT_EXPOSURE_OCCUPIED"
            return
        instrument = self.cache.instrument(bar.bar_type.instrument_id)
        account = self.cache.account_for_venue(Venue("BINANCE"))
        if instrument is None or account is None:
            raise ValueError("native trial instrument/account missing")
        protection = protection_at(
            frame, opportunity, self.policy.campaign_policy, instrument.price_increment.as_decimal()
        )
        if self.policy.campaign_policy != "timeout-only-v1" and protection is None:
            record["reason"] = "MISSING_CAMPAIGN_GEOMETRY"
            return
        snapshot = RiskSnapshot(
            account.balance_total(Currency.from_str("USDT")).as_decimal(),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            bar.ts_init,
            True,
        )
        valuation_price = (
            max(protection.stop_price, protection.target_price)
            if protection is not None
            else bar.close.as_decimal()
        )
        requested = self.policy.max_notional
        if self.policy.stop_budget is not None:
            if protection is None:
                record["reason"] = "MISSING_STOP_RISK_INPUTS"
                return
            sized, reason = stop_budget_notional(
                snapshot,
                StopExposure(Decimal(0), 0, bar.ts_init, True),
                self.policy.stop_budget,
                price=bar.close.as_decimal(),
                stop=protection.stop_price,
                direction=opportunity.direction,
                decision_ns=bar.ts_init,
            )
            if sized is None:
                record["reason"] = reason
                return
            # Match protected paper allocation: reserve the full unsubmitted
            # band, not a predicted close-price fill.
            band = abs(protection.target_price - protection.stop_price)
            requested = min(
                requested,
                snapshot.equity * self.policy.stop_budget.risk_fraction / band * valuation_price,
            )
        admission = admit(
            snapshot,
            RiskLimits(Decimal(1), self.policy.max_exposure_fraction, self.policy.max_notional, 0),
            bar.ts_init,
            valuation_price,
            requested,
            instrument.size_increment.as_decimal(),
            instrument.min_quantity.as_decimal(),
            instrument.max_quantity.as_decimal(),
            instrument.min_notional.as_decimal(),
        )
        if admission.quantity is None:
            record["reason"] = admission.reason
            return
        if admission.quantity * bar.close.as_decimal() < instrument.min_notional.as_decimal():
            record["reason"] = "BELOW_VENUE_MINIMUM"
            return
        campaign = PaperCampaign(
            "trial-" + opportunity.opportunity_id,
            opportunity.opportunity_id,
            candle.instrument_id,
            opportunity.direction,
            admission.quantity,
            bar.ts_init,
            protection.expires_ns if protection else opportunity.expires_ns,
            protection.stop_price if protection else None,
            protection.target_price if protection else None,
            protection.close_invalidation_price if protection else None,
            protection.live_channel_bars if protection else None,
            protection.validity_indicator if protection else None,
            protection.close_breach_price if protection else None,
        )
        self.campaigns += (campaign,)
        record["reason"] = "COUNTERFACTUAL_POLICY_SELECTED_NOT_UTILITY_ADMITTED"
        record["campaign_id"] = campaign.campaign_id

    def mark_equity(self, bar: Bar) -> None:
        """Native cash plus native position valuation, before callback actions.

        This is not end-of-timestamp equity: orders submitted by this callback
        and subsequent same-clock events can still change cash and exposure.
        """
        candle = self.source[bar.ts_event]
        if candle.instrument_id != str(bar.bar_type.instrument_id):
            raise ValueError("equity source instrument mismatch")
        if self.equity_marks and bar.ts_event <= self.equity_marks[-1]["end_ns"]:
            raise ValueError("equity boundaries must increase")
        projected = native_equity(
            self.cache,
            {str(bar.bar_type.instrument_id): EquityMark(bar.close, bar.ts_event, bar.ts_init)},
            venue=Venue("BINANCE"),
            currency=Currency.from_str("USDT"),
            observed_ns=bar.ts_init,
            max_mark_age_ns=0,
        )
        if projected is None:
            raise ValueError("incomplete native equity valuation")
        cash, unrealized = projected
        positions = self.cache.positions_open()
        self.equity_marks.append(
            {
                "end_ns": bar.ts_event,
                "observed_ns": bar.ts_init,
                "phase": "PRE_STRATEGY_BAR_CALLBACK",
                "currency": "USDT",
                "cash": str(cash),
                "unrealized_pnl": str(unrealized),
                "equity": str(cash + unrealized),
                "open_positions": len(positions),
                "close_price": str(bar.close.as_decimal()),
                "source_hash": candle.source_hash,
            }
        )
