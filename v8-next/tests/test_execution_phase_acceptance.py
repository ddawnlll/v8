"""Acceptance measurements for F3 (#402), F4 (#403) and F5 (#404).

Each test is the *measurement* its issue asks for, run on the real BTC tape
(120 real 1h bars, skips when absent) with the engine standing in for the venue:

* **F3** — maker/taker split and the rebate effect read off the raw fill rows, for
  LIMIT vs MARKET entry.
* **F4** — sliced (TWAP) vs single-print implementation shortfall on the same
  bars, with the child-order count that produced it.
* **F5** — a proven brake: the same strategy with a notional cap below the order
  size must deny the order and open nothing, and the same run with the cap above
  it must open. A cap that never fires is not a brake.

Nothing here asserts economic performance.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from v8_next.adapters.expert_strategy import (
    ExpertStrategyConfig,
    run_expert_strategy_backtest,
)

BTC_TAPE = Path("/Users/hootie/src/v8/research/tape/btcusdt-1h-12m/tape.jsonl")
MAKER_FEE = Decimal("0.0002")
TAKER_FEE = Decimal("0.0005")


def _candles(limit: int = 120):
    if not BTC_TAPE.exists():
        pytest.skip(f"single-asset real tape absent at {BTC_TAPE}")
    from v8_next.evaluation.gate_resolution import load_tape_candles

    out = load_tape_candles(BTC_TAPE, limit=limit)
    if not out:
        pytest.skip("tape loaded no candles")
    return tuple(out)


def _cfg(**overrides: object) -> ExpertStrategyConfig:
    base: dict[str, object] = {
        "min_support_quorum": 1,
        "max_contradiction_tolerance": 28,
        "bracket_stop_pct": Decimal("0.02"),
        "bracket_target_pct": Decimal("0.04"),
    }
    base.update(overrides)
    return ExpertStrategyConfig(**base)  # type: ignore[arg-type]


def _run(**overrides: object) -> dict:
    return run_expert_strategy_backtest(
        _candles(), _cfg(**overrides), execution_profile="realistic"
    )


def _fill_split(result: dict) -> dict[str, object]:
    """Maker/taker split and the fee actually implied by the fill rows."""
    maker_qty = taker_qty = Decimal(0)
    maker_notional = taker_notional = Decimal(0)
    maker_fills = taker_fills = 0
    for row in result["fill_records"]:
        side = str(row.get("liquidity_side") or "UNKNOWN").upper()
        qty = Decimal(str(row.get("filled_qty") or "0"))
        px = Decimal(str(row.get("avg_px") or "0"))
        if side == "MAKER":
            maker_fills += 1
            maker_qty += qty
            maker_notional += qty * px
        elif side == "TAKER":
            taker_fills += 1
            taker_qty += qty
            taker_notional += qty * px
    total = maker_fills + taker_fills
    charged = maker_notional * MAKER_FEE + taker_notional * TAKER_FEE
    all_taker = (maker_notional + taker_notional) * TAKER_FEE
    return {
        "fills": total,
        "maker_fills": maker_fills,
        "taker_fills": taker_fills,
        "maker_ratio": round(maker_fills / total, 4) if total else None,
        "maker_notional": f"{maker_notional:.2f}",
        "taker_notional": f"{taker_notional:.2f}",
        "fee_charged_usdt": f"{charged:.6f}",
        "fee_if_all_taker_usdt": f"{all_taker:.6f}",
        "rebate_effect_usdt": f"{all_taker - charged:.6f}",
    }


def test_f3_maker_taker_split_and_rebate_are_readable_per_order_type() -> None:
    limit = _run(entry_order_type="LIMIT")
    market = _run(entry_order_type="MARKET")
    limit_split = _fill_split(limit)
    market_split = _fill_split(market)
    assert limit_split["fills"] > 0 and market_split["fills"] > 0
    # MARKET entry takes liquidity by construction; LIMIT may rest.
    assert market_split["maker_fills"] == 0
    assert limit_split["taker_fills"] + limit_split["maker_fills"] == limit_split["fills"]
    print(
        "\n[F3] LIMIT "
        + str(limit_split)
        + "\n[F3] MARKET "
        + str(market_split)
        + f"\n[F3] market actions={sum(1 for d in market['decisions'] if 'SUBMITTED' in d['action'])} "
        f"limit actions={sum(1 for d in limit['decisions'] if 'SUBMITTED' in d['action'])}"
    )


def test_f4_sliced_vs_single_print_shortfall() -> None:
    single = _run(execution_algo="NONE")
    sliced = _run(execution_algo="TWAP", twap_slices=4)
    single_exec = single["execution"]
    sliced_exec = sliced["execution"]
    sliced_children = [d for d in sliced["decisions"] if d["action"].startswith("TWAP_CHILD_")]
    single_children = [d for d in single["decisions"] if "TWAP" in d["action"]]
    assert sliced_children and not single_children
    assert sliced_exec["fills_count"] >= single_exec["fills_count"]
    assert sliced_exec["slippage_samples"] > 0 and single_exec["slippage_samples"] > 0
    print(
        f"\n[F4] single: fills={single_exec['fills_count']} "
        f"shortfall_bps={single_exec['slippage_bps_mean']} "
        f"samples={single_exec['slippage_samples']} | "
        f"sliced: fills={sliced_exec['fills_count']} "
        f"shortfall_bps={sliced_exec['slippage_bps_mean']} "
        f"samples={sliced_exec['slippage_samples']} children={len(sliced_children)}"
    )


def test_f5_notional_cap_brake_engages_and_releases() -> None:
    # The per-leg notional is 1000 USDT at this configuration; a 50 USDT cap is a
    # certain breach and a 100000 USDT cap cannot bind.
    breached = _run(max_notional_per_order=Decimal("50"))
    permitted = _run(max_notional_per_order=Decimal("100000"))
    denied = [d for d in breached["decisions"] if d["action"] == "DENIED_MAX_NOTIONAL"]
    assert denied, "cap below the order size did not deny anything"
    assert breached["opened_positions"] == []
    assert breached["execution"]["fills_count"] == 0
    assert permitted["opened_positions"], "cap above the order size stopped the run"
    print(
        f"\n[F5] cap=50 -> denied={len(denied)} opened={len(breached['opened_positions'])} "
        f"fills={breached['execution']['fills_count']} | "
        f"cap=100000 -> opened={len(permitted['opened_positions'])} "
        f"fills={permitted['execution']['fills_count']}"
    )


def test_f5_risk_fraction_sizing_changes_the_order_size() -> None:
    flat = _run()
    sized = _run(risk_fraction=Decimal("0.01"))
    flat_positions = flat["opened_positions"]
    sized_positions = sized["opened_positions"]
    assert flat_positions and sized_positions
    # The sizer must actually reach the engine: the same window, a different size.
    assert sized_positions[0]["quantity"] != flat_positions[0]["quantity"]
    print(
        f"\n[F5] flat qty={[p['quantity'] for p in flat_positions]} "
        f"sized qty={[p['quantity'] for p in sized_positions]}"
    )
