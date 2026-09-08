"""Native simulated execution of pre-admitted campaigns; no economic decisions."""

from decimal import Decimal
from typing import Any

from nautilus_trader.model import (
    ClientOrderId,
    InstrumentId,
    OrderSide,
    OrderType,
    Price,
    Quantity,
    QuoteTick,
)
from nautilus_trader.trading import Strategy

from v8_next.domain.campaign import PaperCampaign


class PaperCampaignAdapter(Strategy):
    """Use only in BacktestEngine. App must validate receipts before construction.

    Orders wait for a quote strictly after decision time. Deterministic client IDs
    and engine-cache checks prevent duplicate submission during replay. No private
    venue client is configured by this package. Restart must replay engine state;
    this adapter's in-memory state is not itself a recovery mechanism.
    """

    def __init__(self, campaigns: tuple[PaperCampaign, ...]) -> None:
        super().__init__()
        unique = {c.campaign_id: c for c in campaigns}
        if len(unique) != len(campaigns):
            raise ValueError("duplicate campaign identity")
        if len({c.opportunity_id for c in campaigns}) != len(campaigns):
            raise ValueError("duplicate opportunity allocation")
        for index, campaign in enumerate(campaigns):
            for other in campaigns[index + 1 :]:
                if campaign.instrument_id == other.instrument_id and (
                    max(campaign.decision_ns, other.decision_ns)
                    < min(campaign.expires_ns, other.expires_ns)
                ):
                    raise ValueError("overlapping netting campaigns are outside initial scope")
        self.order_events: list[dict[str, Any]] = []
        self.campaigns = campaigns
        self.submitted: set[str] = set()
        self.expired: set[str] = set()
        self.invalidated: set[str] = set()
        self.exit_requested: set[str] = set()
        self.exit_order_ids: dict[str, set[str]] = {}

    def on_order_event(self, event: Any) -> None:
        """Observe native transitions; do not infer fills from submission flags."""
        self.order_events.append(
            {
                "event_type": type(event).__name__,
                "client_order_id": str(event.client_order_id),
                "instrument_id": str(event.instrument_id),
                "event_ns": event.ts_event,
                "received_ns": event.ts_init,
                "fill_price": str(event.last_px) if hasattr(event, "last_px") else None,
                "fill_quantity": str(event.last_qty) if hasattr(event, "last_qty") else None,
                "commission": str(event.commission) if hasattr(event, "commission") else None,
            }
        )

    def campaign_observations(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        """Project native entry evidence; submission alone is never a fill."""
        return [
            {
                "campaign_id": c.campaign_id,
                "opportunity_id": c.opportunity_id,
                "entry_events": [
                    e for e in self.order_events if e["client_order_id"] == c.campaign_id
                ],
                "exit_events": [
                    e
                    for e in self.order_events
                    if e["client_order_id"] in self.exit_order_ids.get(c.campaign_id, set())
                ],
                "exit_orders": [
                    o
                    for o in state["orders"]
                    if o["client_order_id"] in self.exit_order_ids.get(c.campaign_id, set())
                ],
                "submitted": c.campaign_id in self.submitted,
                "invalidated_before_submission": c.campaign_id in self.invalidated,
                "expired_before_submission": c.campaign_id in self.expired,
                "exit_requested": c.campaign_id in self.exit_requested,
                "entry_order": next(
                    (o for o in state["orders"] if o["client_order_id"] == c.campaign_id), None
                ),
                "realization": "SIMULATED",
            }
            for c in self.campaigns
        ]

    def on_start(self) -> None:
        for instrument in sorted({c.instrument_id for c in self.campaigns}):
            self.subscribe_quotes(InstrumentId.from_str(instrument))

    def on_quote(self, quote: QuoteTick) -> None:
        self.advance_campaigns(
            quote.instrument_id,
            quote.ts_init,
            quote.ask_price.as_decimal(),
            quote.bid_price.as_decimal(),
        )

    def advance_campaigns(
        self,
        instrument_id: InstrumentId,
        observed_ns: int,
        buy_reference: Decimal,
        sell_reference: Decimal,
    ) -> None:
        """Advance at a native callback; references validate entry, never manufacture fills."""
        for campaign in self.campaigns:
            if campaign.instrument_id != str(instrument_id):
                continue
            if campaign.campaign_id in self.submitted:
                # A native filled exit terminates this campaign's exit authority.
                # Otherwise its later timeout could close a successor netting position.
                if any(
                    (order := self.cache.order(ClientOrderId(exit_id))) is not None
                    and str(order.status) == "FILLED"
                    for exit_id in self.exit_order_ids.get(campaign.campaign_id, set())
                ):
                    continue
                if (
                    observed_ns >= campaign.expires_ns
                    and campaign.campaign_id not in self.exit_requested
                ):
                    # Initial netting scope: the owning app must admit at most one
                    # active campaign per instrument. Engine owns close execution.
                    self.cancel_all_orders(instrument_id)
                    exit_tag = f"v8-campaign-exit:{campaign.campaign_id}"
                    self.close_all_positions(instrument_id, reduce_only=True, tags=[exit_tag])
                    # Native-generated IDs remain authoritative. Tags bind intent
                    # without guessing ownership from instrument or fill time.
                    self.exit_order_ids.setdefault(campaign.campaign_id, set()).update(
                        {
                            str(order.client_order_id)
                            for order in self.cache.orders()
                            if exit_tag in (order.tags or [])
                        }
                    )
                    self.exit_requested.add(campaign.campaign_id)
                continue
            if campaign.campaign_id in self.expired or campaign.campaign_id in self.invalidated:
                continue
            if observed_ns >= campaign.expires_ns:
                self.expired.add(campaign.campaign_id)
                continue
            if observed_ns <= campaign.decision_ns:
                continue
            client_id = ClientOrderId(campaign.campaign_id)
            if self.cache.order(client_id) is not None:
                self.submitted.add(campaign.campaign_id)
                continue
            instrument = self.cache.instrument(instrument_id)
            if instrument is None:
                raise ValueError("campaign instrument missing")
            quantity_text = format(campaign.quantity, f".{instrument.size_precision}f")
            if Decimal(quantity_text) != campaign.quantity:
                raise ValueError("campaign quantity exceeds venue precision")
            if campaign.stop_price is not None and campaign.target_price is not None:
                prices = [campaign.stop_price, campaign.target_price]
                if any(p % instrument.price_increment.as_decimal() != 0 for p in prices):
                    raise ValueError("campaign protection violates venue price increment")
                entry_price = buy_reference if campaign.direction == "LONG" else sell_reference
                sign = 1 if campaign.direction == "LONG" else -1
                if (entry_price - campaign.stop_price) * sign <= 0 or (
                    campaign.target_price - entry_price
                ) * sign <= 0:
                    self.invalidated.add(campaign.campaign_id)
                    continue
                stop_id = ClientOrderId(campaign.campaign_id + "-stop")
                target_id = ClientOrderId(campaign.campaign_id + "-target")
                self.exit_order_ids[campaign.campaign_id] = {str(stop_id), str(target_id)}
                orders = self.order_factory.bracket(
                    instrument_id=instrument_id,
                    order_side=OrderSide.BUY if campaign.direction == "LONG" else OrderSide.SELL,
                    quantity=Quantity.from_str(quantity_text),
                    entry_order_type=OrderType.MARKET,
                    entry_client_order_id=client_id,
                    sl_trigger_price=Price.from_str(
                        format(campaign.stop_price, f".{instrument.price_precision}f")
                    ),
                    sl_client_order_id=stop_id,
                    tp_price=Price.from_str(
                        format(campaign.target_price, f".{instrument.price_precision}f")
                    ),
                    tp_post_only=False,
                    tp_client_order_id=target_id,
                )
                self.submit_order_list(orders)
                self.submitted.add(campaign.campaign_id)
                continue
            order = self.order_factory.market(
                instrument_id=instrument_id,
                order_side=OrderSide.BUY if campaign.direction == "LONG" else OrderSide.SELL,
                quantity=Quantity.from_str(quantity_text),
                client_order_id=client_id,
            )
            self.submit_order(order)
            self.submitted.add(campaign.campaign_id)
