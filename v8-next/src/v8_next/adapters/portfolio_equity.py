"""Native multi-instrument equity projection at an explicit observation boundary."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from nautilus_trader.model import Currency, Price, Venue


@dataclass(frozen=True)
class EquityMark:
    price: Price
    observed_ns: int


def native_equity(
    cache: Any,
    marks: dict[str, EquityMark],
    *,
    venue: Venue,
    currency: Currency,
    observed_ns: int,
    max_mark_age_ns: int,
) -> tuple[Decimal, Decimal] | None:
    """Return cash and native unrealized PnL, or absence if coverage is incomplete.

    Caller freezes native state at a chosen evaluation phase. This read-only
    projection does not settle funding, infer FX rates or align event callbacks.
    """
    if observed_ns < 0 or max_mark_age_ns < 0:
        raise ValueError("invalid equity observation clock policy")
    account = cache.account_for_venue(venue)
    if account is None:
        return None
    balance = account.balance_total(currency)
    if balance is None:
        return None
    cash = balance.as_decimal()
    unrealized = Decimal(0)
    for position in cache.positions_open():
        if position.instrument_id.venue != venue:
            continue
        mark = marks.get(str(position.instrument_id))
        if mark is None or not 0 <= observed_ns - mark.observed_ns <= max_mark_age_ns:
            return None
        if mark.price.as_decimal() <= 0:
            raise ValueError("nonpositive equity mark")
        pnl = position.unrealized_pnl(mark.price)
        if pnl.currency != currency:
            return None
        unrealized += pnl.as_decimal()
    if not cash.is_finite() or not unrealized.is_finite():
        raise ValueError("non-finite native equity")
    return cash, unrealized
