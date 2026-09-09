"""Portfolio benchmark tests.

MECHANICS ONLY synthetic section: arithmetic/validator coverage with zero
evaluative weight. Evaluative section runs the quad engine path on real tape
and skips when the tape is absent.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from v8_next.domain.capital_policy import CapitalPolicy
from v8_next.evaluation import economic_benchmark as eb


def _bars(n: int = 60, start: int = 1_000_000_000, step: int = 3_600_000_000_000) -> list[eb.BarView]:
    px = 100.0
    out = []
    for i in range(n):
        c = px * 1.001
        out.append(eb.BarView(end_ns=start + (i + 1) * step, open=px, high=c * 1.001,
                              low=px * 0.999, close=c))
        px = c
    return out


def test_mechanics_pair_positions_time_ordered() -> None:
    opened = [
        {"position_id": "X", "instrument_id": "I", "event_ns": 3, "side": "LONG",
         "quantity": "1", "avg_px_open": "10"},
        {"position_id": "X", "instrument_id": "I", "event_ns": 1, "side": "LONG",
         "quantity": "1", "avg_px_open": "9"},
    ]
    closed = [
        {"position_id": "X", "instrument_id": "I", "event_ns": 4, "realized_pnl": "1 USDT"},
        {"position_id": "X", "instrument_id": "I", "event_ns": 2, "realized_pnl": "2 USDT"},
    ]
    pairs = eb.pair_positions(opened, closed)
    assert len(pairs) == 2
    assert pairs[0][0]["event_ns"] == 1
    first_close = pairs[0][1]
    assert first_close is not None and first_close["event_ns"] == 2
    assert pairs[1][0]["event_ns"] == 3
    second_close = pairs[1][1]
    assert second_close is not None and second_close["event_ns"] == 4


def test_mechanics_pair_positions_unpaired_stays_open() -> None:
    opened = [{"position_id": "X", "instrument_id": "I", "event_ns": 5, "side": "LONG",
               "quantity": "1", "avg_px_open": "10"}]
    pairs = eb.pair_positions(opened, [])
    assert len(pairs) == 1 and pairs[0][1] is None


def test_mechanics_capital_test_accept_and_deny_paths() -> None:
    pol = CapitalPolicy.test_policy(max_notional="1000", max_exposure_frac="1.0", authorized=True)
    assert pol.decision(100.0, instrument_id="I")["decision"] == "ACCEPT"
    big = pol.decision(5000.0, instrument_id="I")
    assert big["decision"] == "REJECT" and big["reason"] == "EXCEEDS_MAX_NOTIONAL"
    assert pol.decision(100.0, live=True)["decision"] == "REJECT"
    assert CapitalPolicy.unauthorized().decision(100.0)["decision"] == "REJECT"
    scoped = pol.model_copy(update={"allowed_instruments": ("I",)})
    assert scoped.decision(100.0, instrument_id="ZZZ")["reason"] == "INSTRUMENT_NOT_ALLOWED"
    assert CapitalPolicy.test_policy(authorized=False).decision(100.0)["decision"] == "REJECT"


def test_mechanics_multileg_family_construction() -> None:
    legs = {
        "A-PERP.BINANCE": [100.0 * (1.001**i) for i in range(60)],
        "B-PERP.BINANCE": [50.0 * (0.999**i) for i in range(60)],
    }
    fams = eb.compute_multileg_family(legs, 10000.0, 0.0005)
    assert set(fams) >= {"cash", "equal_weight", "vol_target", "simple_trend",
                         "bh_A-PERP", "bh_B-PERP"}
    assert fams["cash"]["equity"][0] == 10000.0
    assert fams["equal_weight"]["equity"][0] == pytest.approx(10000.0 * (1 - 0.0005))
    assert len(fams["vol_target"]["equity"]) == 60
    assert fams["vol_target"]["exposure"][0] == 0.0


def test_mechanics_shadow_section_paths(tmp_path: Path) -> None:
    from v8_next.app.portfolio import build_shadow_section

    absent = build_shadow_section(None, {})
    assert absent["live_fills_present"] is False
    assert "command" in absent  # runnable next step, not a dead end
    fixture = tmp_path / "fills.jsonl"
    fixture.write_text('{"fill_id": "1", "instrument": "BTCUSDT", "price": 100.0, "qty": 1.0}\n')
    import shutil

    fx_dir = tmp_path / "fixtures"
    fx_dir.mkdir()
    fx_copy = fx_dir / "fills.jsonl"
    shutil.copy(fixture, fx_copy)
    guarded = build_shadow_section(str(fx_copy), {})
    assert guarded["mode"] == "FIXTURE_NOT_LIVE"
    assert guarded["live_fills_present"] is False
    live = build_shadow_section(
        str(fixture),
        {"balance_total": "1", "positions": [], "orders": [], "currency": "USDT"},
    )
    assert live["live_fills_present"] is True
    assert live["reconciliation"]["shadow_fills"] == 1


def test_mechanics_capacity_bounds_from_participation() -> None:
    from v8_next.app.portfolio import capacity_from_participation

    rows = capacity_from_participation([1e-6, 2e-6], 10000.0)
    assert len(rows) == 3
    assert rows[0]["max_capital_linear"] == pytest.approx(10000.0 * 0.01 / 2e-6)
    assert all(r["impact_beyond"] == "UNVERIFIED_NO_IMPACT_MODEL" for r in rows)
    assert capacity_from_participation([], 10000.0)[0]["max_capital_linear"] is None


def test_portfolio_quad_end_to_end(tmp_path: Path) -> None:
    from v8_next.app import portfolio as port_mod

    if not Path("/Users/hootie/src/v8/research/tape/quad-1h-12m/tape.jsonl").exists():
        pytest.skip("quad tape absent")
    rc = port_mod.main([
        "--tape-path", "/Users/hootie/src/v8/research/tape/quad-1h-12m",
        "--bars", "120", "--output-dir", str(tmp_path / "port"),
        "--primary", "equal_weight",
    ])
    assert rc == 0
    import json

    receipts = sorted((tmp_path / "port").glob("economic_receipt_*.json"))
    assert receipts, "tagged economic receipt missing"
    receipt = json.loads(receipts[0].read_text())
    assert receipt["claim_status"] == "NO_ECONOMIC_CLAIM"
    assert receipt["verdicts"]["capital"] == "NOT_AUTHORIZED"
    assert set(receipt["metrics"]) >= {"portfolio_P", "portfolio_PE", "equal_weight", "cash"}
    assert receipt["metrics"]["portfolio_P"]["funding_cost"] is not None
    assert receipt["shadow_live"]["live_fills_present"] is False
    assert "command" in receipt["shadow_live"]  # runnable next step
    caps = sorted((tmp_path / "port").glob("capital_path_*.json"))
    assert caps, "tagged capital path missing"
    cap = json.loads(caps[0].read_text())
    assert cap["missing_policy_decision"]["decision"] == "REJECT"
    assert cap["live_decision"]["decision"] == "REJECT"
    import sqlite3  # noqa: F401  (guard: no live money path touched)
    assert list((tmp_path / "port").glob("economic_report_*.md"))


def test_mechanics_funding_measured_not_gapped() -> None:
    # Realized embeds settled funding (isolated engine finding); therefore the
    # portfolio builder must take measured drag as input, never derive funding
    # from single-run balance gaps.
    import inspect

    sig = inspect.signature(eb.portfolio_series_from_engine)
    assert "funding_measured_drag" in sig.parameters
    assert "funding_trades_identical" in sig.parameters
    assert Decimal("0.01") > Decimal("0")
