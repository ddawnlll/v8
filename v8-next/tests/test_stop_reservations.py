from decimal import Decimal as D
from types import SimpleNamespace

from v8_next.adapters.stop_exposure import native_stop_exposure
from v8_next.domain.campaign import PaperCampaign


def test_pending_band_risk_counts_without_inventing_fill():
    cache = SimpleNamespace(orders_open=lambda: [], positions_open=lambda: [], order_ids=lambda: [])
    campaigns = (
        PaperCampaign("a", "a", "BTC", "LONG", D(2), 10, 100, D(90), D(110)),
        PaperCampaign("b", "b", "ETH", "SHORT", D(3), 10, 100, D(50), D(40)),
    )
    snapshot = native_stop_exposure(
        cache, campaigns, pending_campaigns=True, pending_ids=frozenset({"a", "b"}), observed_ns=20
    )
    assert snapshot.open_and_reserved_risk == D(70)
    assert snapshot.active_and_reserved_campaigns == 2


def test_unprotected_or_already_submitted_pending_is_not_zero_risk():
    cache = SimpleNamespace(orders_open=lambda: [], positions_open=lambda: [], order_ids=lambda: [])
    campaign = PaperCampaign("a", "a", "BTC", "LONG", D(2), 10, 100)
    assert (
        native_stop_exposure(
            cache, (campaign,), pending_campaigns=True, pending_ids=frozenset({"a"}), observed_ns=20
        )
        is None
    )
    protected = PaperCampaign("a", "a", "BTC", "LONG", D(2), 10, 100, D(90), D(110))
    cache.order_ids = lambda: ["a"]
    assert (
        native_stop_exposure(
            cache,
            (protected,),
            pending_campaigns=True,
            pending_ids=frozenset({"a"}),
            observed_ns=20,
        )
        is None
    )


def test_native_portfolio_pending_projection_preserves_exposure_budgets():
    from v8_next.adapters.portfolio_risk import native_portfolio_risk

    cache = SimpleNamespace(orders_open=lambda: [], positions_open=lambda: [], order_ids=lambda: [])
    campaigns = (
        PaperCampaign("a", "a", "BTC", "LONG", D(2), 10, 100, D(90), D(110)),
        PaperCampaign("b", "b", "ETH", "SHORT", D(3), 10, 100, D(50), D(40)),
    )
    kwargs = dict(
        pending_ids=frozenset({"a", "b"}),
        instrument_exposures={"BTC": "btc", "ETH": "eth"},
        marks={},
        equity=D(1000),
        accounting_reconciled=True,
        observed_ns=20,
    )
    result = native_portfolio_risk(cache, campaigns, **kwargs)
    assert result.snapshots["btc"].reserved_notional == D(370)
    assert result.snapshots["btc"].exposure_reserved_notional == D(220)
    assert result.snapshots["eth"].exposure_reserved_notional == D(150)
    assert result.stop_exposure.open_and_reserved_risk == D(70)
    assert (
        native_portfolio_risk(cache, campaigns, **(kwargs | {"accounting_reconciled": False}))
        is None
    )
    assert (
        native_portfolio_risk(
            cache, campaigns, **(kwargs | {"instrument_exposures": {"BTC": "btc"}})
        )
        is None
    )
