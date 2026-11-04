#!/usr/bin/env python
"""Controlled (MECHANICS ONLY) probes for three gate-verdict defects.

* G3 mixes absolute-USDT realized PnL with dimensionless open-position MTM in
  the same equity/drawdown series. The same 50% loss PASSes open and BLOCKs
  closed.
* G7 passes a candidate with zero exposure, and a candidate that is wrong on
  every observed bar. The pass band ``0.01 <= e < 20`` includes strong evidence
  against the candidate.
* G8 returns PASS/LIVE_VENUE_SETTLED for a local JSONL file when the caller
  merely labels it ``authenticated_venue_statement``; no signature or account
  reconciliation is required.

These monkeypatch ``run_expert_strategy_backtest`` only to hold the candidate's
behaviour fixed while the accounting/gate logic is exercised. No economic claim.

Run: uv run --project v8-next python v8-next/audit_out/bug_hunt_2026-11-03/probe_gates.py
"""

from __future__ import annotations

import json
import tempfile
from decimal import Decimal
from pathlib import Path

import v8_next.evaluation.gate_resolution as gr
from v8_next.domain.market import Candle
from v8_next.evaluation.gate_resolution import WindowBinding

H = 3_600_000_000_000
BASE_NS = 1_700_000_000_000_000_000


def candle(index: int, price: float) -> Candle:
    value = Decimal(str(round(price, 4)))
    start = BASE_NS + index * H
    return Candle(
        "BTCUSDT-PERP.BINANCE",
        start,
        start + H,
        value,
        value,
        value,
        value,
        Decimal("1"),
        start + H,
        start + H,
        "probe",
    )


def g3_probe() -> dict[str, object]:
    regimes = {name: [candle(i, 50)] for i, name in enumerate(["bull", "bear", "chop", "vol"])}
    position = {"position_id": "P", "avg_px_open": "100", "side": "LONG"}

    def open_loss(_candles, _cfg):
        return {
            "opened_positions": [position],
            "closed_positions": [],
            "account": {"balance_total": "10000 USDT"},
        }

    def closed_loss(_candles, _cfg):
        return {
            "opened_positions": [position],
            "closed_positions": [{"position_id": "P", "realized_pnl": "-5000 USDT"}],
            "account": {"balance_total": "5000 USDT"},
        }

    original = gr.run_expert_strategy_backtest
    try:
        gr.run_expert_strategy_backtest = open_loss
        open_state, open_metrics = gr.evaluate_g3_scenario_robustness(regimes)
        gr.run_expert_strategy_backtest = closed_loss
        closed_state, closed_metrics = gr.evaluate_g3_scenario_robustness(regimes)
    finally:
        gr.run_expert_strategy_backtest = original
    return {
        "same_50pct_loss_open_position": {
            "state": open_state.value,
            "max_drawdown": open_metrics["max_observed_drawdown"],
        },
        "same_50pct_loss_realized": {
            "state": closed_state.value,
            "max_drawdown": closed_metrics["max_observed_drawdown"],
        },
        "result": "FAIL"
        if open_state.value == "PASS" and closed_state.value == "BLOCKED"
        else "PASS",
    }


def g7_probe() -> dict[str, object]:
    shadow = tuple(candle(1000 + i, 100 * (0.9995**i)) for i in range(100))
    scored = tuple(candle(i, 100) for i in range(50))
    decisions = [
        {"action": "ENTER", "consensus_supported": True, "opportunity": {"direction": "LONG"}}
        for _ in range(100)
    ]

    def always_wrong(_candles, _cfg):
        return {
            "decisions": decisions,
            "opened_positions": [],
            "closed_positions": [],
            "account": {"balance_total": "10000 USDT"},
        }

    window = WindowBinding.from_candles(shadow, origin="probe")
    original = gr.run_expert_strategy_backtest
    with tempfile.TemporaryDirectory() as tmp:
        try:
            gr.run_expert_strategy_backtest = always_wrong
            wrong_state, wrong_metrics = gr.evaluate_g7_prospective_shadow(
                scored,
                None,
                Path(tmp),
                shadow_stream=shadow,
                shadow_origin="probe",
                shadow_window=window,
            )
            gr.run_expert_strategy_backtest = lambda _c, _g: {
                "decisions": [],
                "opened_positions": [],
                "closed_positions": [],
                "account": {"balance_total": "10000 USDT"},
            }
            idle_state, idle_metrics = gr.evaluate_g7_prospective_shadow(
                scored,
                None,
                Path(tmp),
                shadow_stream=shadow,
                shadow_origin="probe",
                shadow_window=window,
            )
        finally:
            gr.run_expert_strategy_backtest = original
    return {
        "always_wrong_candidate": {
            "state": wrong_state.value,
            "e_process_raw": wrong_metrics["final_e_process_raw"],
            "drift": wrong_metrics["final_drift"],
            "exposure_bars": wrong_metrics["candidate_exposure_bars"],
        },
        "zero_exposure_candidate": {
            "state": idle_state.value,
            "e_process_raw": idle_metrics["final_e_process_raw"],
            "exposure_bars": idle_metrics["candidate_exposure_bars"],
        },
        "result": "FAIL"
        if wrong_state.value == "PASS" or idle_state.value == "PASS"
        else "PASS",
    }


def g8_probe() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        fills = Path(tmp) / "fills.jsonl"
        fills.write_text(
            json.dumps(
                {
                    "fill_id": "f1",
                    "instrument": "BTCUSDT",
                    "price": 100,
                    "qty": 1,
                    "side": "BUY",
                    "venue_time_ns": 1,
                    "order_id": "o1",
                }
            )
            + "\n"
        )
        state, metrics = gr.evaluate_g8_live_realization(
            fills,
            provenance="authenticated_venue_statement",
            account_id="account-from-nowhere",
            account=None,
        )
    return {
        "state": state.value,
        "mode": metrics.get("mode"),
        "authority": metrics.get("authority"),
        "account_reconciled": metrics.get("account_reconciled"),
        "result": "FAIL" if state.value == "PASS" else "PASS",
    }


def main() -> None:
    payload = {"g3": g3_probe(), "g7": g7_probe(), "g8": g8_probe()}
    payload["overall"] = (
        "FAIL"
        if any(payload[key]["result"] == "FAIL" for key in ("g3", "g7", "g8"))
        else "PASS"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
