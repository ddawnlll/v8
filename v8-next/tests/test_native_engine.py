"""Synthetic qualification only: these fixtures never enter product reports."""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model import (
    AccountType,
    CryptoPerpetual,
    Currency,
    FundingRateUpdate,
    InstrumentId,
    Money,
    OmsType,
    Price,
    Quantity,
    QuoteTick,
    Symbol,
    Venue,
)

from v8_next.adapters.campaign import PaperCampaign, PaperCampaignAdapter
from v8_next.adapters.engine_state import economic_state, reconcile_replay


def run_qualified_engine(
    close=False,
    strategy=None,
    offset=0,
    funding_delay=0,
    final_replay=False,
    expect_entry=True,
    quote_prices=None,
    standard_assertions=True,
    bar_data=None,
    quote_times=None,
):
    usdt = Currency.from_str("USDT")
    instrument_id = InstrumentId(Symbol("BTCUSDT-PERP"), Venue("BINANCE"))
    instrument = CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=Symbol("BTCUSDT"),
        base_currency=Currency.from_str("BTC"),
        quote_currency=usdt,
        settlement_currency=usdt,
        is_inverse=False,
        price_precision=2,
        size_precision=3,
        price_increment=Price(0.01, 2),
        size_increment=Quantity(0.001, 3),
        min_quantity=Quantity(0.001, 3),
        max_quantity=Quantity(100, 3),
        min_notional=Money(1, usdt),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal("1"),
        margin_maint=Decimal("0.05"),
        maker_fee=Decimal("0.001"),
        taker_fee=Decimal("0.001"),
    )

    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True))
    try:
        engine.add_venue(
            Venue("BINANCE"),
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money(10000, usdt)],
            default_leverage=Decimal(1),
        )
        engine.add_instrument(instrument)
        engine.add_strategy(
            strategy
            or PaperCampaignAdapter(
                (
                    PaperCampaign(
                        "qualification-campaign",
                        "qualification-opportunity",
                        str(instrument_id),
                        "LONG",
                        Decimal("0.010"),
                        1_000_000_000,
                        5_000_000_000,
                    ),
                )
            )
        )
        engine.add_data(
            bar_data
            if bar_data is not None
            else [
                QuoteTick(
                    instrument_id,
                    Price(quote_prices[index] if quote_prices else 10000, 2),
                    Price(quote_prices[index] if quote_prices else 10000, 2),
                    Quantity(1, 3),
                    Quantity(1, 3),
                    t + offset,
                    t + offset,
                )
                for index, t in enumerate(
                    quote_times
                    or (
                        (1_000_000_000, 2_000_000_000, 4_000_000_000, 6_000_000_000)
                        if close
                        else (1_000_000_000, 2_000_000_000, 4_000_000_000)
                    )
                )
            ]
        )
        funding = FundingRateUpdate(
            instrument_id,
            Decimal("0.01"),
            3_000_000_000 + offset,
            3_000_000_000 + offset + funding_delay,
            next_funding_ns=3_000_000_000 + offset,
        )
        if final_replay:
            from v8_next.adapters.settlements import FinalFunding

            record = FinalFunding(
                str(instrument_id),
                3_000_000_000 + offset,
                3_000_000_000 + offset + funding_delay,
                Decimal("0.01"),
                Decimal(10000),
                "test-only",
            )
            mark, funding = record.execution_replay_events(record.received_ns)
            engine.add_data([mark])
        engine.add_data([funding, funding])
        engine.run()
        if not standard_assertions:
            return economic_state(engine, Venue("BINANCE"), usdt)
        if not expect_entry:
            assert not engine.cache.positions()
            assert not engine.cache.orders()
            assert engine.cache.account_for_venue(Venue("BINANCE")).balance_total(
                usdt
            ).as_decimal() == Decimal(10000)
            return economic_state(engine, Venue("BINANCE"), usdt)
        assert len(engine.cache.positions_open()) == (0 if close else 1), [
            (d["reason"], d["stance"]["reason"]) for d in getattr(strategy, "decisions", [])
        ]
        assert len(engine.cache.orders()) == (2 if close else 1)
        assert engine.cache.orders()[0].ts_init > 1_000_000_000
        account = engine.cache.account_for_venue(Venue("BINANCE"))
        if funding_delay == 0:
            assert account.balance_total(usdt).as_decimal() == Decimal(
                "9998.8" if close else "9998.9"
            )
        return economic_state(engine, Venue("BINANCE"), usdt)
    finally:
        engine.dispose()


def test_native_fee_funding_and_position():
    run_qualified_engine()


def test_late_funding_requires_execution_only_boundary_replay():
    timely = run_qualified_engine(close=True)
    assert timely["balance_total"] == "9998.80000000 USDT"
    # The pinned engine fails closed, rather than settling against the wrong
    # position. Ordinary late REST receipt cannot be fed as an online settlement.
    with pytest.raises(RuntimeError, match="Late funding boundary"):
        run_qualified_engine(close=True, funding_delay=4_000_000_000)
    revised = run_qualified_engine(close=True, funding_delay=4_000_000_000, final_replay=True)
    reconcile_replay(timely, revised)


def test_fresh_engine_replay_reconciles_account_orders_and_positions():
    expected = run_qualified_engine()
    recovered = run_qualified_engine()
    reconcile_replay(expected, recovered)


def test_process_restart_replays_native_state(tmp_path):
    fixture = Path(__file__).resolve()
    script = (
        "import json,runpy,sys; from pathlib import Path; "
        "state=runpy.run_path(sys.argv[1])['run_qualified_engine'](); "
        "Path(sys.argv[2]).write_text(json.dumps(state))"
    )
    states = []
    for index in range(2):
        output = tmp_path / f"state-{index}.json"
        subprocess.run(
            [sys.executable, "-c", script, str(fixture), str(output)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        states.append(json.loads(output.read_text()))
    reconcile_replay(states[0], states[1])
    states[1]["balance_total"] = "9999.90000000 USDT"
    with pytest.raises(ValueError, match="diverged"):
        reconcile_replay(states[0], states[1])


def test_expiry_closes_native_position_and_charges_exit_fee():
    state = run_qualified_engine(close=True)
    position = state["positions"][0]
    assert position["is_closed"] is True
    assert position["opened_ns"] < position["closed_ns"]
    assert Decimal(position["peak_quantity"]) == Decimal("0.010")
    assert Decimal(position["average_open_price"]) == Decimal(10000)
    assert Decimal(position["average_close_price"]) == Decimal(10000)


@pytest.mark.parametrize("observer", ["squeeze", "breakout_baseline", "families:donchian-breakout"])
@pytest.mark.parametrize("verified", [True, False])
@pytest.mark.parametrize("grammar", ["range-breakout-48-v1", "trend-continuation-v2"])
def test_observer_through_admission_to_native_fill(observer, verified, grammar):
    from v8_next.adapters.economic_paper import EconomicPaperAdapter
    from v8_next.domain.market import Candle, frame_at
    from v8_next.economics.controller import InstrumentConstraints
    from v8_next.economics.decisions import UtilityInputs
    from v8_next.risk.admission import RiskLimits

    hour = 3600 * 10**9
    candles = []
    for index in range(69):
        close = (
            Decimal(100 + (10 if index % 2 else -10))
            if index < 20
            else Decimal(100) + Decimal(index) / 100
        )
        candles.append(
            Candle(
                "BTCUSDT-PERP.BINANCE",
                index * hour,
                (index + 1) * hour,
                close,
                close + Decimal("0.001"),
                close - Decimal("0.001"),
                close,
                Decimal(3 if index == 68 else 1),
                (index + 1) * hour,
                (index + 1) * hour,
                "synthetic-test-only",
            )
        )
    decision_ns = 69 * hour + 10**9
    if observer == "breakout_baseline":
        candles = candles[-49:]  # Baseline requires grammar warmup, not squeeze warmup.
    frame = frame_at("BTCUSDT-PERP.BINANCE", decision_ns, tuple(candles))

    # Test-only calibrated evidence. Product does not load this fixture or mint a receipt.
    def calibration(opportunity, timestamp):
        return UtilityInputs(
            Decimal(10), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1), "test-only"
        ), True

    strategy = EconomicPaperAdapter(
        {decision_ns: frame},
        RiskLimits(Decimal(1), Decimal("0.1"), Decimal(100), 0),
        InstrumentConstraints(Decimal("0.001"), Decimal("0.001"), Decimal(1), Decimal(1)),
        Decimal(100),
        calibration if verified else None,
        observer=observer,
        grammar=grammar,
    )
    state = run_qualified_engine(strategy=strategy, offset=69 * hour, expect_entry=verified)
    assert len(state["orders"]) == int(verified)
    assert strategy.decisions[0]["reason"] == (
        "PAPER_CAMPAIGN_ADMITTED" if verified else "UNVERIFIED_CALIBRATION"
    )
    assert strategy.decisions[0]["observer_policy"] == observer


@pytest.mark.parametrize("close", [False, True])
def test_native_order_callbacks_survive_store_restart_and_evaluation(tmp_path, close):
    import hashlib
    import json

    from v8_next.app.evaluate import evaluate
    from v8_next.evaluation.store import ResearchStore, canonical

    strategy = PaperCampaignAdapter(
        (
            PaperCampaign(
                "callback-test",
                "callback-opportunity",
                "BTCUSDT-PERP.BINANCE",
                "LONG",
                Decimal("0.010"),
                1_000_000_000,
                5_000_000_000,
            ),
        )
    )
    state = run_qualified_engine(strategy=strategy, close=close)
    fills = [e for e in strategy.order_events if e["event_type"] == "OrderFilled"]
    assert len(fills) == (2 if close else 1)
    assert Decimal(fills[0]["fill_quantity"]) == Decimal("0.010")
    assert Decimal(fills[0]["fill_price"]) == Decimal(10000)
    assert fills[0]["event_ns"] > 1_000_000_000

    observations = strategy.campaign_observations(state)
    assert observations[0]["entry_order"]["status"] == "FILLED"
    assert len(observations[0]["exit_orders"]) == int(close)
    if close:
        assert observations[0]["exit_orders"][0]["status"] == "FILLED"
        exit_fills = [e for e in observations[0]["exit_events"] if e["event_type"] == "OrderFilled"]
        assert len(exit_fills) == 1
        assert exit_fills[0]["client_order_id"] != "callback-test"
        assert exit_fills[0]["event_ns"] >= 5_000_000_000
    observed_ns = 6_000_000_000 if close else 4_000_000_000
    policy = {"test_only": True}
    policy_hash = hashlib.sha256(canonical(policy).encode()).hexdigest()
    (tmp_path / "policy.json").write_text(
        json.dumps({"policy": policy, "policy_hash": policy_hash})
    )
    store = ResearchStore(tmp_path / "research.sqlite")
    try:
        for observation in observations:
            store.record_campaign_observation(observation["campaign_id"], observed_ns, observation)
    finally:
        store.close()
    # Open a new connection as a restarted process would; duplicate replay is a no-op.
    recovered = ResearchStore(tmp_path / "research.sqlite")
    try:
        for observation in observations:
            recovered.record_campaign_observation(
                observation["campaign_id"], observed_ns, observation
            )
    finally:
        recovered.close()
    report = evaluate(tmp_path)
    history = report["campaign_history"]["observations"]
    assert len(history) == 1
    assert history[0]["entry_events"] == observations[0]["entry_events"]
    assert history[0]["exit_events"] == observations[0]["exit_events"]
    assert history[0]["realization"] == "SIMULATED"
    assert report["claim_status"] == "NO_ECONOMIC_CLAIM"


def test_closed_native_cash_return_includes_fees_and_funding_once():
    from v8_next.evaluation.cash_return import terminal_cash_return

    state = run_qualified_engine(close=True)
    state["accounting_as_of_ns"] = 8_000_000_000
    state["funding_query_windows"] = [
        {
            "instrument_id": "BTCUSDT-PERP.BINANCE",
            "start_inclusive_ns": 0,
            "end_inclusive_ns": 7_000_000_000,
            "received_ns": 8_000_000_000,
            "source_sha256": "test-only",
        }
    ]
    state["missing_announced_settlements"] = []
    result = terminal_cash_return(state, Decimal(10000))
    assert Decimal(result["return"]) == Decimal("-0.00012")
    assert result["claim_status"] == "NO_ECONOMIC_CLAIM"
    state["funding_query_windows"] = []
    assert terminal_cash_return(state, Decimal(10000))["return"] is None
    open_state = run_qualified_engine()
    open_state["accounting_as_of_ns"] = 4_000_000_000
    assert (
        terminal_cash_return(open_state, Decimal(10000))["status"]
        == "OPEN_POSITION_REQUIRES_EQUITY_MARK"
    )


@pytest.mark.parametrize(
    "direction,stop,target,final_price,filled",
    [
        ("LONG", 9900, 10100, 10120, "target"),
        ("LONG", 9900, 10100, 9880, "stop"),
        ("SHORT", 10100, 9900, 9880, "target"),
        ("SHORT", 10100, 9900, 10120, "stop"),
    ],
)
def test_native_bracket_closes_and_cancels_sibling(direction, stop, target, final_price, filled):
    campaign = PaperCampaign(
        "bracket",
        "opportunity",
        "BTCUSDT-PERP.BINANCE",
        direction,
        Decimal(".010"),
        10**9,
        10 * 10**9,
        Decimal(stop),
        Decimal(target),
    )
    strategy = PaperCampaignAdapter((campaign,))
    state = run_qualified_engine(
        strategy=strategy, quote_prices=[10000, 10000, final_price], standard_assertions=False
    )
    orders = {o["client_order_id"]: o for o in state["orders"]}
    assert len(orders) == 3
    assert orders["bracket"]["status"] == "FILLED"
    assert orders["bracket-" + filled]["status"] == "FILLED"
    assert orders["bracket-" + ("stop" if filled == "target" else "target")]["status"] == "CANCELED"
    assert len(state["positions"]) == 1 and state["positions"][0]["is_closed"]
    observations = strategy.campaign_observations(state)
    assert len(observations[0]["exit_orders"]) == 2
    assert any(e["event_type"] == "OrderFilled" for e in observations[0]["exit_events"])
    assert PaperCampaign.from_record(campaign.to_record()) == campaign


def test_bracket_timeout_cancels_protection_and_replays_identically():
    campaign = PaperCampaign(
        "timeout-bracket",
        "opportunity",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal(".010"),
        10**9,
        5 * 10**9,
        Decimal(9900),
        Decimal(10100),
    )
    states = []
    for _ in range(2):
        strategy = PaperCampaignAdapter((campaign,))
        state = run_qualified_engine(strategy=strategy, close=True, standard_assertions=False)
        orders = {o["client_order_id"]: o for o in state["orders"]}
        assert len(orders) == 4
        assert orders["timeout-bracket-stop"]["status"] == "CANCELED"
        assert orders["timeout-bracket-target"]["status"] == "CANCELED"
        assert state["positions"][0]["is_closed"]
        assert len(strategy.campaign_observations(state)[0]["exit_orders"]) == 3
        states.append(state)
    reconcile_replay(*states)


def test_entry_gap_invalidates_bracket_without_any_order():
    campaign = PaperCampaign(
        "gap-bracket",
        "opportunity",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal(".010"),
        10**9,
        10 * 10**9,
        Decimal(9900),
        Decimal(10100),
    )
    strategy = PaperCampaignAdapter((campaign,))
    state = run_qualified_engine(
        strategy=strategy, quote_prices=[10000, 10200, 10000], standard_assertions=False
    )
    assert not state["orders"] and not state["positions"]
    observation = strategy.campaign_observations(state)[0]
    assert observation["invalidated_before_submission"]
    assert not observation["expired_before_submission"]


@pytest.mark.parametrize("verified", [True, False])
@pytest.mark.parametrize("requested", ["1.05", "1.13"])
def test_pandf_geometry_through_economic_admission_to_native_bracket(verified, requested):
    from v8_next.adapters.economic_paper import EconomicPaperAdapter
    from v8_next.domain.market import Candle, CausalFrame
    from v8_next.economics.controller import InstrumentConstraints
    from v8_next.economics.decisions import UtilityInputs
    from v8_next.risk.admission import RiskLimits

    second = 10**9
    prices = [100] * 20 + [104, 100, 105]
    candles = tuple(
        Candle(
            "BTCUSDT-PERP.BINANCE",
            i * second,
            (i + 1) * second,
            Decimal(p),
            Decimal(p) + Decimal(".5"),
            Decimal(p) - Decimal(".5"),
            Decimal(p),
            Decimal(1),
            (i + 1) * second,
            (i + 1) * second,
            "synthetic-test-only",
        )
        for i, p in enumerate(prices)
    )
    frame = CausalFrame("BTCUSDT-PERP.BINANCE", 23 * second, candles)

    def calibration(*_):
        return UtilityInputs(
            Decimal(10), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1), "test-only"
        ), True

    strategy = EconomicPaperAdapter(
        {frame.decision_ns: frame},
        RiskLimits(Decimal(1), Decimal(1), Decimal(100), 0),
        InstrumentConstraints(Decimal(".001"), Decimal(".001"), Decimal(1), Decimal(1)),
        Decimal(requested),
        calibration if verified else None,
        observer="families:pandf-breakout",
        grammar="volatility-extreme-v2",
        campaign_policy="pandf:a:v2",
    )
    state = run_qualified_engine(
        strategy=strategy,
        offset=22 * second,
        quote_prices=[105, 105, 120],
        standard_assertions=False,
    )
    record = strategy.decisions[0]
    assert Decimal(record["protection"]["stop_price"]) == 101
    assert Decimal(record["protection"]["target_price"]) == 113
    if not verified:
        assert record["reason"] == "UNVERIFIED_CALIBRATION"
        assert not state["orders"]
        return
    if requested == "1.05":
        assert record["reason"] == "BELOW_VENUE_MINIMUM"
        assert not state["orders"]
        return
    assert strategy.campaigns[0].quantity * Decimal(113) <= Decimal(requested)
    assert record["reason"] == "PAPER_CAMPAIGN_ADMITTED"
    assert len(state["orders"]) == 3 and state["positions"][0]["is_closed"]
    assert strategy.campaigns[0].stop_price == 101
    assert strategy.campaigns[0].target_price == 113
    assert strategy.campaigns[0].expires_ns == 31 * second
    assert any(
        o["client_order_id"].endswith("-target") and o["status"] == "FILLED"
        for o in state["orders"]
    )


def test_completed_bracket_cannot_timeout_a_successor_position():

    class Successor(PaperCampaignAdapter):
        def on_quote(self, quote):
            super().on_quote(quote)
            if quote.ts_init == 4 * 10**9:
                self.campaigns += (
                    PaperCampaign(
                        "successor",
                        "next",
                        "BTCUSDT-PERP.BINANCE",
                        "LONG",
                        Decimal(".010"),
                        quote.ts_init,
                        20 * 10**9,
                    ),
                )

    campaign = PaperCampaign(
        "first",
        "first-o",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal(".010"),
        10**9,
        5 * 10**9,
        Decimal(9900),
        Decimal(10100),
    )
    strategy = Successor((campaign,))
    state = run_qualified_engine(
        strategy=strategy,
        close=True,
        quote_prices=[10000, 10000, 10120, 10120],
        standard_assertions=False,
    )
    assert not strategy.exit_requested
    assert any(
        o["client_order_id"] == "successor" and o["status"] == "FILLED" for o in state["orders"]
    )


def test_historical_trial_uses_next_bar_and_future_suffix_cannot_change_prior_decisions():
    from dataclasses import replace

    from nautilus_trader.model import Bar, BarType

    from v8_next.adapters.historical_trial import HistoricalTrial
    from v8_next.domain.config import PaperConfig
    from v8_next.domain.market import Candle

    hour = 3600 * 10**9
    prices = [100] * 24 + [104, "104.25", 106, 107, 108, 109]
    candles = tuple(
        Candle(
            "BTCUSDT-PERP.BINANCE",
            i * hour,
            (i + 1) * hour,
            Decimal(p),
            Decimal(p) + Decimal(".5"),
            Decimal(p) - Decimal(".5"),
            Decimal(p),
            Decimal(10),
            100 * hour,
            None,
            "fixture",
        )
        for i, p in enumerate(prices)
    )
    policy = PaperConfig(
        maker_fee=".001",
        taker_fee=".001",
        initial_balance="10000",
        max_notional="100",
        max_exposure_fraction=".1",
        observer_policy="families:donchian-breakout",
        grammar_policy="trend-continuation-v2",
        campaign_policy="donchian:a:v2",
    )

    def run(source, selected_policy=policy):
        trial = HistoricalTrial(source, selected_policy)
        bars = [
            Bar(
                BarType.from_str("BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"),
                Price.from_str(format(c.open, ".2f")),
                Price.from_str(format(c.high, ".2f")),
                Price.from_str(format(c.low, ".2f")),
                Price.from_str(format(c.close, ".2f")),
                Quantity.from_str(format(c.volume, ".3f")),
                c.end_ns,
                c.end_ns,
            )
            for c in source
        ]
        state = run_qualified_engine(strategy=trial, bar_data=bars, standard_assertions=False)
        return trial, state

    first, state = run(candles)
    assert first.campaigns
    assert first.failure is None
    assert len(first.equity_marks) == len(candles)
    assert Decimal(first.equity_marks[0]["equity"]) == Decimal(10000)
    assert all(
        Decimal(mark["equity"]) == Decimal(mark["cash"]) + Decimal(mark["unrealized_pnl"])
        for mark in first.equity_marks
    )
    entry_events = [
        event
        for event in first.order_events
        if event["client_order_id"] == first.campaigns[0].campaign_id
        and event["event_type"] == "OrderFilled"
    ]
    assert entry_events[0]["event_ns"] > first.campaigns[0].decision_ns
    changed = candles[:27] + tuple(
        replace(c, open=c.open * 2, high=c.high * 2, low=c.low * 2, close=c.close * 2)
        for c in candles[27:]
    )
    second, _ = run(changed)
    assert first.decisions[:27] == second.decisions[:27]
    assert first.equity_marks[:27] == second.equity_marks[:27]
    assert all(c.available_ns is None for c in candles)
    assert state["claim_status"] == "NO_ECONOMIC_CLAIM"
    held, _ = run(candles, policy.model_copy(update={"campaign_policy": "timeout-only-v1"}))
    assert held.failure is None
    marks = [m for m in held.equity_marks if m["open_positions"]]
    assert marks
    assert any(Decimal(m["unrealized_pnl"]) > 0 for m in marks)
    assert Decimal(marks[-1]["equity"]) > Decimal(marks[-1]["cash"])

    from v8_next.risk.sizing import StopBudget

    sized, _ = run(
        candles,
        policy.model_copy(update={"stop_budget": StopBudget(Decimal(".00001"), Decimal(".01"), 1)}),
    )
    assert sized.failure is None
    assert sized.campaigns
    assert sized.campaigns[0].quantity < first.campaigns[0].quantity
    first_sized = sized.campaigns[0]
    entry_reference = candles[24].close
    assert first_sized.quantity * (entry_reference - first_sized.stop_price) <= Decimal(".1")


def test_native_close_sample_reconciles_funding_and_fees_once():
    from v8_next.evaluation.outcomes import observed_outcomes

    campaign = PaperCampaign(
        "sample", "o", "BTCUSDT-PERP.BINANCE", "LONG", Decimal(".010"), 10**9, 5 * 10**9
    )
    strategy = PaperCampaignAdapter((campaign,))
    state = run_qualified_engine(strategy=strategy, close=True)
    sample = observed_outcomes(
        [campaign.to_record()], list(strategy.position_closures.values()), state, Decimal(10000)
    )
    assert sample["reconciliation"] == "CLOSED_CASH_RECONCILED"
    assert sample["native_closed_net_pnl"] == "-1.20000000"
    row = sample["rows"][0]
    assert row["observed_commissions"] == "0.20000000"
    assert row["observed_funding_pnl"] == "-1.00000000"
    assert Decimal(row["net_return_on_entry_notional"]) == Decimal("-.012")
    assert not sample["calibration_eligible"]


def test_reused_netting_id_keeps_each_campaign_closure():
    from v8_next.evaluation.outcomes import observed_outcomes

    first = PaperCampaign(
        "sample-first", "first-o", "BTCUSDT-PERP.BINANCE", "LONG", Decimal(".010"), 10**9, 3 * 10**9
    )
    second = PaperCampaign(
        "sample-second",
        "second-o",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal(".010"),
        4 * 10**9,
        20 * 10**9,
    )
    strategy = PaperCampaignAdapter((first, second))
    state = run_qualified_engine(strategy=strategy, close=True, standard_assertions=False)
    sample = observed_outcomes(
        [c.to_record() for c in strategy.campaigns],
        list(strategy.position_closures.values()),
        state,
        Decimal(10000),
    )
    assert sample["closed_outcome_count"] == 1 and sample["missing_outcome_count"] == 1
    assert sample["rows"][0]["status"] == "CLOSED_UNDER_NATIVE_MODEL"
    assert sample["rows"][1]["net_return_on_entry_notional"] is None
    assert sample["conditional_mean_closed_return"] is None
    assert sample["reconciliation"] == "OPEN_OR_UNRECONCILED"


def test_two_closed_campaigns_survive_same_native_netting_id_and_reconcile():
    from copy import deepcopy

    from v8_next.evaluation.outcomes import observed_outcomes

    campaigns = (
        PaperCampaign(
            "one", "o1", "BTCUSDT-PERP.BINANCE", "LONG", Decimal(".010"), 10**9, 3 * 10**9
        ),
        PaperCampaign(
            "two", "o2", "BTCUSDT-PERP.BINANCE", "LONG", Decimal(".010"), 4 * 10**9, 7 * 10**9
        ),
    )
    strategy = PaperCampaignAdapter(campaigns)
    state = run_qualified_engine(
        strategy=strategy,
        standard_assertions=False,
        quote_times=tuple(t * 10**9 for t in (1, 2, 4, 6, 8)),
    )
    closures = list(strategy.position_closures.values())
    assert len(closures) == 2 and len({c["position_id"] for c in closures}) == 1
    records = [c.to_record() for c in campaigns]
    sample = observed_outcomes(records, closures, state, Decimal(10000))
    assert sample["closed_outcome_count"] == 2
    assert sample["reconciliation"] == "CLOSED_CASH_RECONCILED"
    assert Decimal(sample["native_closed_net_pnl"]) == Decimal("-1.4")
    corrupted = deepcopy(closures)
    corrupted[0]["realized_pnl"] = "-2.00000000 USDT"
    bad = observed_outcomes(records, corrupted, state, Decimal(10000))
    assert (
        bad["reconciliation"] == "OPEN_OR_UNRECONCILED"
        and bad["conditional_mean_closed_return"] is None
    )
    with pytest.raises(ValueError, match="repeated"):
        observed_outcomes(records, closures + closures[:1], state, Decimal(10000))
    corrupted = deepcopy(closures)
    corrupted[0]["opened_ns"] = campaigns[0].decision_ns
    with pytest.raises(ValueError, match="timing"):
        observed_outcomes(records, corrupted, state, Decimal(10000))


def test_native_open_position_stop_risk_projection():
    from v8_next.adapters.stop_exposure import native_stop_exposure

    class Observing(PaperCampaignAdapter):
        samples = None

        def on_quote(self, quote):
            super().on_quote(quote)
            if self.samples is None:
                self.samples = []
            if self.cache.positions_open():
                from types import SimpleNamespace

                incomplete = SimpleNamespace(
                    positions_open=self.cache.positions_open,
                    orders_inflight=self.cache.orders_inflight,
                    orders_open=lambda: [
                        o
                        for o in self.cache.orders_open()
                        if not str(o.client_order_id).endswith("-stop")
                    ],
                )
                assert (
                    native_stop_exposure(
                        incomplete,
                        self.campaigns,
                        pending_campaigns=False,
                        observed_ns=quote.ts_init,
                    )
                    is None
                )
                from v8_next.adapters.portfolio_risk import native_portfolio_risk

                projection = native_portfolio_risk(
                    self.cache,
                    self.campaigns,
                    pending_ids=frozenset(),
                    instrument_exposures={str(quote.instrument_id): "btc"},
                    marks={str(quote.instrument_id): (quote.ask_price.as_decimal(), quote.ts_init)},
                    equity=Decimal(10000),
                    accounting_reconciled=True,
                    observed_ns=quote.ts_init,
                )
                assert projection is not None
                assert projection.snapshots["btc"].gross_notional == sum(
                    p.quantity.as_decimal() * quote.ask_price.as_decimal()
                    for p in self.cache.positions_open()
                )
                assert projection.snapshots["btc"].reserved_notional == 0
            pending_ids = frozenset(
                c.campaign_id
                for c in self.campaigns
                if c.campaign_id not in self.submitted | self.expired | self.invalidated
            )
            if pending_ids:
                reserved = native_stop_exposure(
                    self.cache,
                    self.campaigns,
                    pending_campaigns=True,
                    pending_ids=pending_ids,
                    observed_ns=quote.ts_init,
                )
                assert reserved is not None
                assert reserved.open_and_reserved_risk == Decimal(2)
            self.samples.append(
                native_stop_exposure(
                    self.cache,
                    self.campaigns,
                    pending_campaigns=any(
                        c.campaign_id not in self.submitted | self.expired | self.invalidated
                        for c in self.campaigns
                    ),
                    observed_ns=quote.ts_init,
                )
            )

    campaign = PaperCampaign(
        "risk",
        "risk-opp",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal(".010"),
        10**9,
        10 * 10**9,
        Decimal(9900),
        Decimal(10100),
    )
    subject = Observing((campaign,))
    run_qualified_engine(strategy=subject, standard_assertions=False)
    valid = [s for s in subject.samples if s is not None and s.active_and_reserved_campaigns]
    assert valid
    assert valid[-1].open_and_reserved_risk == Decimal(1)
    assert (
        native_stop_exposure(
            subject.cache, subject.campaigns, pending_campaigns=True, observed_ns=10**10
        )
        is None
    )


@pytest.mark.parametrize("pending", [False, True])
def test_thesis_invalidation_cancels_pending_or_closes_native_position(pending):
    from v8_next.domain.market import Candle, CausalFrame

    second = 10**9
    decision = second if pending else 0
    campaign = PaperCampaign(
        "thesis",
        "op",
        "BTCUSDT-PERP.BINANCE",
        "LONG",
        Decimal(".01"),
        decision,
        100 * second,
        Decimal(9900),
        Decimal(10100),
        Decimal(9995),
    )
    strategy = PaperCampaignAdapter((campaign,))
    candle = Candle(
        "BTCUSDT-PERP.BINANCE",
        second,
        2 * second,
        Decimal(9995),
        Decimal(9996),
        Decimal(9994),
        Decimal(9995),
        Decimal(1),
        2 * second,
        2 * second,
        "test-only",
    )
    strategy.validity_frames = {
        ("BTCUSDT-PERP.BINANCE", 2 * second): CausalFrame(
            "BTCUSDT-PERP.BINANCE", 2 * second, (candle,)
        ),
        ("ETHUSDT-PERP.BINANCE", 2 * second): CausalFrame("ETHUSDT-PERP.BINANCE", 2 * second, ()),
    }
    state = run_qualified_engine(strategy=strategy, standard_assertions=False)
    assert strategy.callback_failure is None
    assert strategy.thesis_invalidated == {"thesis": 2 * second}
    restored = PaperCampaignAdapter((PaperCampaign.from_record(campaign.to_record()),))
    restored.validity_frames = dict(strategy.validity_frames)
    replay = run_qualified_engine(strategy=restored, standard_assertions=False)
    reconcile_replay(state, replay)
    assert restored.thesis_invalidated == strategy.thesis_invalidated
    if pending:
        assert not state["orders"]
        assert "thesis" in strategy.invalidated
    else:
        assert strategy.exit_requested == {"thesis"}
        assert len(state["positions"]) == 1
        assert state["positions"][0]["is_closed"]
        assert state["positions"][0]["closed_ns"] < campaign.expires_ns


def test_two_native_instruments_keep_timeout_and_brackets_isolated():
    usdt = Currency.from_str("USDT")
    venue = Venue("BINANCE")
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True))
    campaigns = tuple(
        PaperCampaign(
            symbol,
            symbol,
            f"{symbol}USDT-PERP.BINANCE",
            "LONG",
            Decimal("0.010"),
            10**9,
            expiry * 10**9,
            Decimal(90),
            Decimal(110),
        )
        for symbol, expiry in (("BTC", 3), ("ETH", 10))
    )
    adapter = PaperCampaignAdapter(campaigns)
    try:
        engine.add_venue(
            venue,
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money(10000, usdt)],
            default_leverage=Decimal(1),
        )
        for symbol in ("BTC", "ETH"):
            identity = InstrumentId.from_str(f"{symbol}USDT-PERP.BINANCE")
            engine.add_instrument(
                CryptoPerpetual(
                    instrument_id=identity,
                    raw_symbol=Symbol(f"{symbol}USDT"),
                    base_currency=Currency.from_str(symbol),
                    quote_currency=usdt,
                    settlement_currency=usdt,
                    is_inverse=False,
                    price_precision=2,
                    size_precision=3,
                    price_increment=Price(0.01, 2),
                    size_increment=Quantity(0.001, 3),
                    maker_fee=Decimal("0.001"),
                    taker_fee=Decimal("0.001"),
                    ts_event=0,
                    ts_init=0,
                )
            )
            engine.add_data(
                [
                    QuoteTick(
                        identity,
                        Price(100, 2),
                        Price(100, 2),
                        Quantity(1, 3),
                        Quantity(1, 3),
                        t * 10**9,
                        t * 10**9,
                    )
                    for t in (1, 2, 3, 4, 5)
                ]
            )
        engine.add_strategy(adapter)
        engine.run()
        assert adapter.callback_failure is None
        assert adapter.submitted == {"BTC", "ETH"}
        assert adapter.exit_requested == {"BTC"}
        opened = engine.cache.positions_open()
        assert len(opened) == 1
        assert str(opened[0].instrument_id) == "ETHUSDT-PERP.BINANCE"
        assert {str(o.client_order_id) for o in engine.cache.orders_open()} == {
            "ETH-stop",
            "ETH-target",
        }
        assert len(adapter.position_closures) == 1
        assert (
            next(iter(adapter.position_closures.values()))["instrument_id"]
            == "BTCUSDT-PERP.BINANCE"
        )
    finally:
        engine.dispose()
