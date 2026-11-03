#!/usr/bin/env python
"""Real-tape reproduction of the swing-adapter stale-bracket-leg bug.

Runs the unmodified product path (``run_swing_engine``, ``plain_swing``) over the
real multi-instrument tape and reconciles the fills against the campaign events.

It reports, for the run:
* bracket campaigns whose stop AND target both filled;
* bracket-leg fills that arrive after their campaign already closed;
* the fill-derived net position versus the adapter's tracked campaigns.

Usage:
  uv run --project v8-next python v8-next/audit_out/bug_hunt_2026-11-03/probe_swing_real_tape.py \
      --tape /Users/hootie/src/v8/research/tape/multi-1h-4y/tape.jsonl

Exit code 0 when no stale leg is found, 3 when the bug reproduces.
"""

from __future__ import annotations

import argparse
import datetime
import json
from decimal import Decimal
from pathlib import Path

from v8_next.adapters.swing_engine import SwingEngineConfig, run_swing_engine
from v8_next.economics.grammar import POLICY_REQUIRED_BARS
from v8_next.economics.swing_baseline import policy_spec
from v8_next.evaluation.gate_resolution import load_tape_candles

HOUR_MS = 3_600_000


def ms(value: str) -> int:
    return int(
        datetime.datetime.fromisoformat(value).replace(tzinfo=datetime.timezone.utc).timestamp()
        * 1000
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tape", type=Path, default=None)
    parser.add_argument("--instrument", default="BTCUSDT")
    parser.add_argument("--start", default="2022-07-01")
    parser.add_argument("--end", default="2025-12-31")
    args = parser.parse_args()
    tape = args.tape
    if tape is None:
        tape = Path("/Users/hootie/src/v8/research/tape/multi-1h-4y/tape.jsonl")
    if not tape.is_file():
        print(json.dumps({"status": "TAPE_ABSENT", "tape": str(tape)}))
        return 2

    candles = load_tape_candles(
        tape,
        instrument=args.instrument,
        start_ms=ms(args.start),
        end_ms=ms(args.end),
    )
    spec = policy_spec("plain_swing")
    warmup = int(POLICY_REQUIRED_BARS[spec.grammar_policy])
    instrument_id = candles[0].instrument_id
    cfg = SwingEngineConfig(
        policy_id="plain_swing",
        instrument_id=instrument_id,
        bar_type_str=f"{instrument_id}-1-HOUR-LAST-EXTERNAL",
    )
    run = run_swing_engine(tuple(candles), cfg, warmup_bars=warmup)
    events = run["events"]

    # Campaign intervals from the adapter's own records.
    closed_at: dict[str, int] = {}
    for record in events["positions_closed"]:
        closed_at[str(record["position_id"])] = int(record["ts_event"])
    brackets = [
        d["bracket_submitted"]
        for d in events["decisions"]
        if isinstance(d, dict) and "bracket_submitted" in d
    ]

    both_legs: list[dict[str, object]] = []
    stale_legs: list[dict[str, object]] = []
    for bracket in brackets:
        stop_id = str(bracket.get("stop_client_order_id"))
        target_id = str(bracket.get("target_client_order_id"))
        stop_fills = [f for f in events["fills"] if f["client_order_id"] == stop_id]
        target_fills = [f for f in events["fills"] if f["client_order_id"] == target_id]
        if stop_fills and target_fills:
            both_legs.append(
                {
                    "entry_bar_ns": bracket.get("entry_bar_ns"),
                    "direction": bracket.get("direction"),
                    "stop_fill_ns": stop_fills[0]["ts_event"],
                    "target_fill_ns": target_fills[0]["ts_event"],
                    "stop_id": stop_id,
                    "target_id": target_id,
                }
            )
        for leg_name, fills in (("stop", stop_fills), ("target", target_fills)):
            sibling_fills = target_fills if leg_name == "stop" else stop_fills
            if not sibling_fills:
                continue
            first_sibling_ns = int(sibling_fills[0]["ts_event"])
            for fill in fills:
                if int(fill["ts_event"]) > first_sibling_ns + 24 * HOUR_MS * 1_000_000:
                    stale_legs.append(
                        {
                            "leg": leg_name,
                            "client_order_id": fill["client_order_id"],
                            "fill_ns": fill["ts_event"],
                            "other_leg_first_fill_ns": first_sibling_ns,
                            "gap_hours": round(
                                (int(fill["ts_event"]) - first_sibling_ns) / (HOUR_MS * 1e6), 1
                            ),
                            "entry_bar_ns": bracket.get("entry_bar_ns"),
                        }
                    )

    net = Decimal(0)
    for fill in events["fills"]:
        quantity = Decimal(str(fill["last_qty"]))
        net += quantity if fill["side"] in ("BUY", "LONG") else -quantity
    opened = len(events["positions_opened"])
    closed = len(events["positions_closed"])
    payload = {
        "status": "FAIL" if stale_legs else "PASS",
        "tape": str(tape),
        "candles": len(candles),
        "decision_records": len(events["decisions"]),
        "bracket_campaigns": len(brackets),
        "both_legs_filled": both_legs,
        "stale_leg_fills": stale_legs,
        "fills": len(events["fills"]),
        "positions_opened": opened,
        "positions_closed": closed,
        "fill_derived_net_position": str(net),
        "open_position_at_end": run["open_position_at_end"],
        "orders_open_at_end": run["orders_open_at_end"],
    }
    print(json.dumps(payload, indent=2, default=str))
    return 3 if stale_legs else 0


if __name__ == "__main__":
    raise SystemExit(main())
