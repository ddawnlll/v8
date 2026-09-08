"""Read-only native exposure projection for linear quote-currency instruments."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from v8_next.adapters.stop_exposure import native_stop_exposure
from v8_next.domain.campaign import PaperCampaign
from v8_next.risk.admission import RiskSnapshot
from v8_next.risk.sizing import StopExposure


@dataclass(frozen=True)
class PortfolioRisk:
    snapshots: dict[str, RiskSnapshot]
    stop_exposure: StopExposure


def native_portfolio_risk(
    cache: Any,
    campaigns: tuple[PaperCampaign, ...],
    *,
    pending_ids: frozenset[str],
    instrument_exposures: dict[str, str],
    marks: dict[str, tuple[Decimal, int]],
    equity: Decimal,
    accounting_reconciled: bool,
    observed_ns: int,
) -> PortfolioRisk | None:
    """Caller supplies reconciled quote-currency equity and linear instrument map.

    Run synchronously on the native event thread. Marks must be known at the
    observation clock. Missing marks/protection or in-flight entries return
    absence. This does not compute funding equity or support inverse contracts.
    """
    if not accounting_reconciled:
        return None
    if not equity.is_finite() or equity < 0:
        raise ValueError("invalid reconciled equity")
    stop = native_stop_exposure(
        cache,
        campaigns,
        pending_campaigns=bool(pending_ids),
        pending_ids=pending_ids,
        observed_ns=observed_ns,
    )
    if stop is None:
        return None
    gross = {exposure: Decimal(0) for exposure in instrument_exposures.values()}
    reserved = dict(gross)
    for position in cache.positions_open():
        instrument = str(position.instrument_id)
        if instrument not in instrument_exposures or instrument not in marks:
            return None
        price, known_ns = marks[instrument]
        if known_ns != observed_ns:
            return None
        if not price.is_finite() or price <= 0:
            raise ValueError("invalid portfolio mark")
        gross[instrument_exposures[instrument]] += position.quantity.as_decimal() * price
    for campaign in campaigns:
        if campaign.campaign_id not in pending_ids:
            continue
        if campaign.instrument_id not in instrument_exposures:
            return None
        if campaign.stop_price is None or campaign.target_price is None:
            return None
        reserved[instrument_exposures[campaign.instrument_id]] += campaign.quantity * max(
            campaign.stop_price, campaign.target_price
        )
    total_gross = sum(gross.values(), Decimal(0))
    total_reserved = sum(reserved.values(), Decimal(0))
    return PortfolioRisk(
        {
            exposure: RiskSnapshot(
                equity, total_gross, amount, total_reserved, observed_ns, True, reserved[exposure]
            )
            for exposure, amount in gross.items()
        },
        stop,
    )
