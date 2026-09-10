"""Real-tape execution integration: determinism and honest reporting.

These are evaluative tests: they run the shared Nautilus account over the real
quad tape and assert execution-semantics invariants. They skip when the tape is
absent. Synthetic data is never used to make an execution claim here.

What is asserted:
  * the same profile, run twice, executes bit-identical fills and positions
    (this is the determinism evidence G2 asks for, produced by the engine);
  * the recorded execution block names and digests the profile that actually
    ran, so a receipt cannot silently cite semantics it did not use;
  * a profile that models slippage/latency is distinguishable from the baseline;
  * the block never presents modelled fills as venue truth.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from v8_next.adapters.portfolio_backtest import (
    SleeveSpec,
    run_portfolio_backtest,
    trade_signature,
)

QUAD_TAPE = Path("/Users/hootie/src/v8/research/tape/quad-1h-12m")
BARS = 120

SLEEVES_P = (SleeveSpec("incumbent", 1, 28, 1.0),)


def _load():
    if not (QUAD_TAPE / "tape.jsonl").exists():
        pytest.skip(f"quad tape absent at {QUAD_TAPE}")
    from v8_next.evaluation.multitape import load_multitape

    return load_multitape(QUAD_TAPE, limit=BARS)


def _run(profile: str):
    tape = _load()
    return run_portfolio_backtest(
        tape.candles,
        SLEEVES_P,
        tape.funding,
        per_leg_notional=Decimal("1000"),
        taker_fee=Decimal("0.0005"),
        initial_balance=Decimal("10000"),
        funding_dropped=tape.funding_dropped,
        execution_profile=profile,
    )


def test_same_profile_executes_identical_fills_and_positions() -> None:
    first = _run("realistic")
    second = _run("realistic")

    assert first["fill_signature"] == second["fill_signature"]
    assert trade_signature(first) == trade_signature(second)
    assert first["decisions_count"] == second["decisions_count"]
    assert first["opened_positions"] == second["opened_positions"]
    assert first["closed_positions"] == second["closed_positions"]
    assert first["account"] == second["account"]


def test_execution_block_names_and_digests_the_profile_that_ran() -> None:
    from v8_next.adapters.execution_models import profile_digest

    result = _run("realistic")
    block = result["execution"]

    assert block["profile"] == "realistic"
    assert block["digest"] == profile_digest("realistic")
    assert block["fill_model"] == "one_tick_slippage"
    assert block["fill_model_slipped"] is True
    assert block["fee_model"] == "maker_taker"
    assert block["evidence_class"] == "MODELLED_EXECUTION_ASSUMPTION_NOT_VENUE_TRUTH"
    # latency model was configured, so latency must be visible, not implicit
    assert block["latency_nanos"]["base"] == 1_000_000


def test_profiles_are_distinguishable_in_the_recorded_evidence() -> None:
    from v8_next.adapters.execution_models import profile_digest

    baseline = _run("baseline")["execution"]
    realistic = _run("realistic")["execution"]

    assert baseline["digest"] != realistic["digest"]
    assert baseline["digest"] == profile_digest("baseline")
    assert baseline["fill_model_slipped"] is False
    assert realistic["fill_model_slipped"] is True
    # the baseline deliberately models no latency; the realistic one does
    assert baseline["latency_nanos"]["base"] == 0
    assert realistic["latency_nanos"]["base"] > 0


def test_measured_frictions_are_consistent_never_invented() -> None:
    block = _run("realistic")["execution"]

    if block["slippage_samples"] == 0:
        assert block["slippage_bps_mean"] is None
        assert block["slippage_bps_max"] is None
        assert block["slippage_bps_min"] is None
    else:
        assert block["slippage_bps_mean"] is not None
        assert block["slippage_bps_max"] >= block["slippage_bps_mean"]
        assert block["slippage_bps_min"] <= block["slippage_bps_mean"]
    assert block["fills_count"] >= 0
    assert block["fills_report_type"] not in (None, "")
    # shortfall is in basis points of the decision price; a cross-instrument
    # mismatch would blow this up by orders of magnitude
    if block["slippage_bps_mean"] is not None:
        assert abs(block["slippage_bps_mean"]) < 1000.0


def test_commissions_are_attributed_to_their_currency() -> None:
    block = _run("realistic")["execution"]
    totals = block["commission_totals_by_currency"]
    assert isinstance(totals, dict)
    if totals:
        assert all(isinstance(cur, str) and amt >= 0 for cur, amt in totals.items())
        # a single-currency run may publish one total; multi-currency must not
        if len(totals) == 1:
            assert block["commission_total"] == pytest.approx(next(iter(totals.values())))
        else:
            assert block["commission_total"] is None


def test_latency_is_never_published_as_measured_zero_when_configured() -> None:
    """Bar execution stamps fills at the bar time; that must be stated, not hidden."""
    block = _run("realistic")["execution"]
    assert block["configured_latency_nanos"] > 0
    if block["decision_to_position_event_ns_mean"] == 0:
        assert block["latency_observability"] == "BAR_EXECUTION_STAMPS_FILLS_AT_BAR_TIME"
    else:
        assert block["latency_observability"] in (
            "MEASURED_ORDER_LIFETIME",
            "NOT_OBSERVABLE",
        )


def test_slippage_model_actually_changes_fill_prices_on_real_tape() -> None:
    """If the fill model were ignored, both profiles would fill identically."""
    baseline = _run("baseline")
    realistic = _run("realistic")
    if realistic["execution"]["fills_count"] == 0:
        pytest.skip("no fills on this window; cannot compare fill prices")
    if realistic["execution"]["slippage_bps_mean"] == 0:
        pytest.skip("this window produced no slipped fills")
    assert baseline["fill_signature"] != realistic["fill_signature"]


def test_fill_records_are_json_safe_and_match_the_reported_count() -> None:
    import json

    result = _run("baseline")
    records = result["fill_records"]
    assert isinstance(records, list)
    assert len(records) == result["execution"]["fills_count"]
    for rec in records:
        assert isinstance(rec, dict)
        for value in rec.values():
            assert value is None or isinstance(value, (bool, int, float, str, list))
        # must survive a strict JSON round-trip (no NaN/Inf leaking through)
        json.dumps(rec, allow_nan=False)
