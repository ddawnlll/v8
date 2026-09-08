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
            [
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
                    (
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
