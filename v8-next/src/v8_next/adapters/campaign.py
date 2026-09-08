"""Native simulated execution of pre-admitted campaigns; no economic decisions."""

from decimal import Decimal

from nautilus_trader.model import ClientOrderId, InstrumentId, OrderSide, Quantity, QuoteTick
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
        self.campaigns = campaigns
        self.submitted: set[str] = set()
        self.expired: set[str] = set()
        self.exit_requested: set[str] = set()

    def on_start(self) -> None:
        for instrument in sorted({c.instrument_id for c in self.campaigns}):
            self.subscribe_quotes(InstrumentId.from_str(instrument))

    def on_quote(self, quote: QuoteTick) -> None:
        for campaign in self.campaigns:
            if campaign.instrument_id != str(quote.instrument_id):
                continue
            if campaign.campaign_id in self.submitted:
                if (
                    quote.ts_init >= campaign.expires_ns
                    and campaign.campaign_id not in self.exit_requested
                ):
                    # Initial netting scope: the owning app must admit at most one
                    # active campaign per instrument. Engine owns close execution.
                    self.cancel_all_orders(quote.instrument_id)
                    self.close_all_positions(quote.instrument_id, reduce_only=True)
                    self.exit_requested.add(campaign.campaign_id)
                continue
            if campaign.campaign_id in self.expired:
                continue
            if quote.ts_init >= campaign.expires_ns:
                self.expired.add(campaign.campaign_id)
                continue
            if quote.ts_init <= campaign.decision_ns:
                continue
            client_id = ClientOrderId(campaign.campaign_id)
            if self.cache.order(client_id) is not None:
                self.submitted.add(campaign.campaign_id)
                continue
            instrument = self.cache.instrument(quote.instrument_id)
            if instrument is None:
                raise ValueError("campaign instrument missing")
            quantity_text = format(campaign.quantity, f".{instrument.size_precision}f")
            if Decimal(quantity_text) != campaign.quantity:
                raise ValueError("campaign quantity exceeds venue precision")
            order = self.order_factory.market(
                instrument_id=quote.instrument_id,
                order_side=OrderSide.BUY if campaign.direction == "LONG" else OrderSide.SELL,
                quantity=Quantity.from_str(quantity_text),
                client_order_id=client_id,
            )
            self.submit_order(order)
            self.submitted.add(campaign.campaign_id)
