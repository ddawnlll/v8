"""Read native protective-order coverage; never maintain a second position ledger."""

from decimal import Decimal
from typing import Any

from nautilus_trader.model import OrderSide, PositionSide, StopMarketOrder

from v8_next.domain.campaign import PaperCampaign
from v8_next.risk.sizing import StopExposure


def native_stop_exposure(
    cache: Any,
    campaigns: tuple[PaperCampaign, ...],
    *,
    pending_campaigns: bool,
    observed_ns: int,
) -> StopExposure | None:
    """Return absence for unpriced reservations or incomplete native protection.

    Current scope is native netting positions with campaign-owned stop-market
    orders. Nominal absolute entry-to-stop risk matches the legacy heat rule;
    no profit offset, gap guarantee or funding reconciliation is implied.
    """
    if pending_campaigns:
        return None
    owners = {c.campaign_id: c for c in campaigns}
    if len(owners) != len(campaigns):
        raise ValueError("duplicate campaign ownership")
    orders = {str(o.client_order_id): o for o in cache.orders_open()}
    recognized = set()
    total = Decimal(0)
    positions = cache.positions_open()
    for position in positions:
        owner_id = str(position.opening_order_id)
        owner = owners.get(owner_id)
        stop = orders.get(owner_id + "-stop")
        if owner is None or stop is None or not isinstance(stop, StopMarketOrder):
            return None
        expected_side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        if (
            position.side not in {PositionSide.LONG, PositionSide.SHORT}
            or str(position.instrument_id) != owner.instrument_id
            or stop.instrument_id != position.instrument_id
            or not stop.is_reduce_only
            or stop.side != expected_side
            or stop.leaves_qty.as_decimal() < position.quantity.as_decimal()
            or owner.stop_price is None
            or stop.trigger_price.as_decimal() != owner.stop_price
        ):
            return None
        entry = Decimal(str(position.avg_px_open))
        quantity = position.quantity.as_decimal()
        if not entry.is_finite() or entry <= 0 or quantity <= 0:
            raise ValueError("invalid native position valuation")
        total += quantity * abs(entry - stop.trigger_price.as_decimal())
        recognized.add(owner_id + "-stop")
        target_id = owner_id + "-target"
        if target_id in orders:
            target = orders[target_id]
            if (
                not target.is_reduce_only
                or target.side != expected_side
                or target.instrument_id != position.instrument_id
            ):
                return None
            recognized.add(target_id)
    if set(orders) - recognized:
        return None  # Entry/unknown reservations need a separate authoritative risk bound.
    return StopExposure(total, len(positions), observed_ns, True)
