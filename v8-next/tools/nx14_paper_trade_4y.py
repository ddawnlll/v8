#!/usr/bin/env python
"""Four-year simulated paper-trade report with v8-core attribution (P2 of the locked benchmark).

Runs the pre-registered swing family over the four-year tape, then reports it the way the
ported audit kernel requires:

* every losing campaign is charged to exactly one of the **7 disjoint failure domains**
  (``system_proving.attribution``) and the conservation invariant is verified;
* the run is summarised as the **14-metric robustness vector** and sealed in a
  ``SystemProvingGroundReceipt`` with its digest;
* every field of that vector carries its own basis and every field this producer cannot
  measure is published as ``null`` with a named reason (#457) — a published name is a claim
  about what was measured;
* costs stay in separate columns (measured fee, measured funding, modelled slippage) and the
  measured execution shortfall stays absent.

Nothing here is an economic claim: it is a diagnostic report over real bars.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from v8_next.adapters.swing_engine import SwingEngineConfig, SwingEngineStrategy
from v8_next.economics.grammar import POLICY_REQUIRED_BARS
from v8_next.economics.swing_baseline import (
    SHARED_CONTRACT,
    policy_spec,
    replay_bracket,
    swing_signal,
)
from v8_next.economics.swing_costs import (
    EXECUTION_SHORTFALL_MISSING,
    SlippageModel,
    campaign_cost,
)
from v8_next.evaluation.multitape import load_multitape
from v8_next.system_proving import (
    FailureAttributionBreakdown,
    SystemProvingGroundReceipt,
)
from v8_next.system_proving.attribution import classify_exit_failure
from v8_next.system_proving.metrics import DRAWDOWN_BASIS, metrics_from_campaigns

HOUR_NS = 3_600 * 10**9
SLIPPAGE_FRACTIONS = (0.0, 0.05, 0.10)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--tape", default="research/tape/multi-1h-4y/tape.jsonl")
    parser.add_argument("--instrument", default="BTCUSDT")
    parser.add_argument("--policies", default="plain_swing,causal_trend")
    parser.add_argument("--out", default="docs/evidence/v87-r3/PAPER_4Y")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tape_path = (repo_root / args.tape).resolve()

    tape = load_multitape(tape_path)
    series = list(tape.candles[args.instrument])
    instrument_id = series[0].instrument_id
    funding_rows = tuple(row for row in tape.funding if row.instrument == args.instrument)
    taker = Decimal(SHARED_CONTRACT["taker_fee"])

    # one pass of decision frames, then replay each policy over them
    cfg = SwingEngineConfig(
        policy_id="plain_swing", instrument_id=instrument_id,
        bar_type_str=f"{instrument_id}-1-HOUR-LAST-EXTERNAL",
    )
    source = {index: candle for index, candle in enumerate(series)}
    framing = SwingEngineStrategy(cfg, source, warmup_bars=10**9)
    frames = []
    for index, candle in enumerate(series):
        framing.on_bar(SimpleNamespace(ts_event=index))  # type: ignore[arg-type]
        frames.append(framing._decision_frame(candle))

    report: dict[str, Any] = {
        "pillar": "P2_paper_trade_4y",
        "claim_status": "NO_ECONOMIC_CLAIM",
        "evidence_class": (
            "DECISION_PLANE_DIAGNOSTIC over four years of real bars: real taker fee and real "
            "funding settlement rows; not engine fills, not a venue settlement; slippage is a "
            "declared assumption and the measured execution shortfall is absent"
        ),
        "tape": {"path": str(tape_path.relative_to(repo_root)), "sha256": tape.tape_sha256,
                 "bars": len(series), "instrument_id": instrument_id},
        "families": {},
    }

    for policy_id in [name.strip() for name in args.policies.split(",") if name.strip()]:
        spec = policy_spec(policy_id)
        warmup = int(POLICY_REQUIRED_BARS[spec.grammar_policy])
        has_bracket_policy = spec.protection_policy not in (None, "timeout-only-v1")
        breakdown = FailureAttributionBreakdown()
        trades: list[dict[str, Any]] = []
        index = warmup
        while index < len(series) - 1:
            decision = swing_signal(frames[index], spec, bar_ns=HOUR_NS)
            if decision is None:
                index += 1
                continue
            outcome = replay_bracket(
                decision, series[index + 1 :], bar_ns=HOUR_NS, bps_fee=taker,
                has_bracket=has_bracket_policy,
            )
            bracketless = Decimal(decision.stop_price) == Decimal(decision.entry_reference)
            per_fraction = {}
            for fraction in SLIPPAGE_FRACTIONS:
                per_fraction[fraction] = campaign_cost(
                    decision=decision, outcome=outcome, funding_rows=funding_rows,
                    slippage=SlippageModel(model="entry_bar_range_fraction", range_fraction=fraction),
                    entry_bar_low=series[index].low, entry_bar_high=series[index].high,
                    dropped_rows_in_tape=tape.funding_dropped,
                )
            measured = per_fraction[0.0]
            domain = None
            if measured.net_return_measured_only < 0:
                domain = classify_exit_failure(
                    exit_kind=outcome.exit_kind,
                    net_return=measured.net_return_measured_only,
                    has_bracket=has_bracket_policy and not bracketless,
                )
                breakdown.record_failure(domain)
            trades.append({
                "decision_identity": decision.identity(),
                "exit_kind": outcome.exit_kind,
                "bars_held": outcome.bars_held,
                "bracketless": bracketless,
                "gross_return": outcome.gross_return,
                "fee_cost_return": -abs(outcome.fee_cost_return),
                "funding_cost_return": measured.funding_cost_return,
                "funding_status": measured.funding_status,
                "net_measured": measured.net_return_measured_only,
                "net_with_modelled_slippage_05": per_fraction[0.05].net_return_with_modelled_slippage,
                "net_with_modelled_slippage_10": per_fraction[0.10].net_return_with_modelled_slippage,
                "execution_shortfall_measured": None,
                "execution_shortfall_status": EXECUTION_SHORTFALL_MISSING,
                "failure_domain": None if domain is None else domain.value,
            })
            index += max(1, outcome.bars_held) + 1

        nets = [row["net_measured"] for row in trades]
        wins = sum(1 for value in nets if value > 0)
        gross = sum(row["gross_return"] for row in trades)
        fees = sum(row["fee_cost_return"] for row in trades)
        funding = sum(row["funding_cost_return"] for row in trades)
        net_with_modelled_slippage_10 = sum(
            row["net_with_modelled_slippage_10"] for row in trades
        )
        # #457: the drawdown, the recovery horizon and the slippage degradation are read off
        # the per-campaign columns this producer actually measured — the vector derives them
        # itself instead of the tool hand-feeding a number under another field's name.
        metrics = metrics_from_campaigns(
            campaigns=len(trades), failures=breakdown.total_failures, gross_return_sum=gross,
            fee_cost_sum=abs(fees), funding_cost_sum=abs(funding),
            bars=len(series),
            campaign_net_returns=nets,
            campaign_bars_held=[int(row["bars_held"]) for row in trades],
            net_with_modelled_slippage_sum=net_with_modelled_slippage_10,
        )
        receipt = SystemProvingGroundReceipt.new(
            world_id=f"{tape_path.parent.name}:{instrument_id}",
            policy_id=policy_id,
            total_trades=len(trades),
            total_campaigns=len(trades),
            metrics=metrics,
            attribution=breakdown,
            exercises_full_pipeline=False,
            timestamp_ns=int(series[-1].end_ns),
        )
        report["families"][policy_id] = {
            "grammar_policy": spec.grammar_policy,
            "protection_policy": spec.protection_policy,
            "warmup_bars": warmup,
            "campaigns": len(trades),
            "win_rate_pct": round(100.0 * wins / len(trades), 2) if trades else None,
            "gross_return_sum": round(gross, 8),
            "fee_cost_return_sum": round(fees, 8),
            "funding_cost_return_sum": round(funding, 8),
            "net_measured_sum": round(sum(nets), 8),
            "net_with_modelled_slippage_10_sum": round(net_with_modelled_slippage_10, 8),
            "failure_attribution": breakdown.as_dict(),
            "conservation_verified": breakdown.verify_conservation(),
            "robustness_vector": metrics.as_dict(),
            # #457: the vector's provenance travels with it — every field names its own basis
            # and every null names the input this producer does not carry.
            "robustness_vector_basis": metrics.field_reports(),
            "robustness_vector_unmeasured": metrics.unmeasured_fields(),
            "drawdown_basis": DRAWDOWN_BASIS,
            "double_entry_reconciled": metrics.is_double_entry_reconciled(),
            "system_proving_receipt": receipt.as_dict(),
            "trades": trades,
        }

    path = out_dir / "paper_trade_4y.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")

    for policy_id, entry in report["families"].items():
        print(f"[PAPER-4Y] {policy_id}: kampanya={entry['campaigns']} "
              f"kazanma={entry['win_rate_pct']}% net(measured)={entry['net_measured_sum']:+.8f}")
        print(f"           fee={entry['fee_cost_return_sum']:+.8f} funding={entry['funding_cost_return_sum']:+.8f} "
              f"net(+slip10)={entry['net_with_modelled_slippage_10_sum']:+.8f}")
        print(f"           attribution: {entry['failure_attribution']['counts_by_domain']} "
              f"conservation={entry['conservation_verified']}")
        print(f"           receipt: {entry['system_proving_receipt']['receipt_id']} "
              f"double_entry={entry['double_entry_reconciled']}")
        unmeasured = ", ".join(item["field"] for item in entry["robustness_vector_unmeasured"])
        print(f"           robustness vector: every measured field carries its own basis; "
              f"null (unmeasured) = {unmeasured or 'none'}")
    print(f"[PAPER-4Y] artifact sha256:{_sha256(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
