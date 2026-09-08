"""Closed exposure cannot make an unreconciled online account eligible again."""

from types import SimpleNamespace

from v8_next.adapters import economic_paper
from v8_next.economics.decisions import Opportunity, Stance, StanceKind


def test_closed_position_blocks_calibration_and_readmission(monkeypatch):
    opportunity = Opportunity("next", "exposure", "BTCUSDT-PERP.BINANCE", "LONG", 1, 100)
    stance = Stance("observer", "group", StanceKind.SUPPORT, "test", "next", 10)
    monkeypatch.setattr(economic_paper, "grammar_opportunity", lambda *_: opportunity)
    monkeypatch.setattr(economic_paper, "policy_stances", lambda *_: (stance,))
    monkeypatch.setattr(economic_paper.PaperCampaignAdapter, "on_quote", lambda *_: None)

    def forbidden_calibration(*_):
        raise AssertionError("unreconciled account must not reach calibration/admission")

    adapter = SimpleNamespace(
        frames={10: SimpleNamespace(candles=[SimpleNamespace(end_ns=9)])},
        cache=SimpleNamespace(
            positions_open=lambda: [],
            orders_open=lambda: [],
            positions=lambda: [SimpleNamespace(is_closed=True)],
        ),
        calibration=forbidden_calibration,
        decisions=[],
    )

    # Native Strategy instances are required for super(); use a real adapter and
    # replace only its cache boundary with the controlled closed-position view.
    class Harness(economic_paper.EconomicPaperAdapter):
        @property
        def cache(self):
            return adapter.cache

    from decimal import Decimal

    from v8_next.economics.controller import InstrumentConstraints
    from v8_next.risk.admission import RiskLimits

    subject = Harness(
        adapter.frames,
        RiskLimits(Decimal(1), Decimal(1), Decimal(100), 0),
        InstrumentConstraints(Decimal(1), Decimal(1), Decimal(1), Decimal(1)),
        Decimal(100),
        forbidden_calibration,
    )
    subject.on_quote(SimpleNamespace(ts_init=10))
    assert subject.decisions[-1]["reason"] == "UNRECONCILED_FUNDING_AFTER_EXPOSURE"
    assert not subject.campaigns
