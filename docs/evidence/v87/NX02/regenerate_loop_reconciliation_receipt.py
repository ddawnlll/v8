#!/usr/bin/env python3
"""#436 — regenerate the loop-reconciliation receipt over a real tape window.

Evidence tooling, not runtime: it exists so the receipt committed next to it
(`loop_reconciliation_436.json`) can be re-measured instead of trusted. It runs
ONE real funded portfolio window (the same dual funding/nofunding engine runs
`v8_next.app.portfolio` performs) and records, side by side:

* the engine closed-loop residual `(balance_total - capital) - sum_realized_pnl
  + open_entry_commissions` -- recomputed here independently of the series, so
  the same number is available in a phase where the series does not publish it;
* the funding reconciliation (measured dual-run drag vs the analytic
  expectation from the real funding rows);
* the `loop_err` conjunction, the declared graft, and the published field set.

Nothing is synthesized: a missing tape fails the run. The script must be run
once per code phase (`--phase before` on the pre-fix revision, `--phase after`
on the fixed one) and the two measurements composed with `--compose`.

Usage (from the repository root)::

    uv run --project v8-next --extra dev \\
        python docs/evidence/v87/NX02/regenerate_loop_reconciliation_receipt.py \\
        --phase after --tape /Users/hootie/src/v8/research/tape/btcusdt-1h-12m \\
        --bars 500 --out /tmp/loop_after.json \\
        --bound-receipt <path to the run's economic_receipt_*.json>

    uv run --project v8-next --extra dev \\
        python docs/evidence/v87/NX02/regenerate_loop_reconciliation_receipt.py \\
        --compose /tmp/loop_before.json /tmp/loop_after.json \\
        --out docs/evidence/v87/NX02/loop_reconciliation_436.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from v8_next.adapters.portfolio_backtest import (
    SleeveSpec,
    run_portfolio_backtest,
    trade_signature,
)
from v8_next.evaluation import economic_benchmark as eb
from v8_next.evaluation.multitape import load_multitape

CAPITAL = 10000.0
TAKER_FEE = 0.0005
PER_LEG_NOTIONAL = 1000.0
DEFAULT_TAPE = "/Users/hootie/src/v8/research/tape/btcusdt-1h-12m"
SCRIPT_REL = "docs/evidence/v87/NX02/regenerate_loop_reconciliation_receipt.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _independent_engine_residual(
    engine_result: dict[str, Any], balance_total: float, capital: float
) -> dict[str, float]:
    """Recompute the closed-loop identity from the engine result, independently.

    Same inputs the series uses, but computed here so a phase whose artifact does
    not publish the residual still reports it (that is the point of #436).
    """
    sum_realized = 0.0
    for close_record in engine_result.get("closed_positions", []):
        if isinstance(close_record, dict) and close_record.get("realized_pnl"):
            try:
                sum_realized += float(str(close_record["realized_pnl"]).split()[0])
            except (ValueError, TypeError):
                pass
    pairs = eb.pair_positions(
        [p for p in engine_result.get("opened_positions", []) if isinstance(p, dict)],
        [c for c in engine_result.get("closed_positions", []) if isinstance(c, dict)],
    )
    open_entry_comm = 0.0
    for position, close_record in pairs:
        if close_record is not None:
            continue
        try:
            open_entry_comm += (
                abs(float(position.get("quantity") or 0))
                * float(position.get("avg_px_open") or 0)
                * TAKER_FEE
            )
        except (ValueError, TypeError):
            continue
    return {
        "balance_delta": balance_total - capital,
        "sum_realized_pnl": sum_realized,
        "open_entry_commissions_of_open_positions": open_entry_comm,
        "residual_usdt": (balance_total - capital) - sum_realized + open_entry_comm,
    }


def _bound_receipt_block(receipt_path: Path, copy_to: Path | None = None) -> dict[str, Any]:
    """The canonical bound receipt this reconciliation explains (read-only).

    ``copy_to`` stores a durable copy beside the receipt so the evidence is
    self-contained instead of pointing at a scratch directory.
    """
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {}).get("portfolio_P", {})
    verdicts = payload.get("verdicts", {})
    recorded_path = receipt_path
    if copy_to is not None:
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        copy_to.write_bytes(receipt_path.read_bytes())
        recorded_path = copy_to
    return {
        "path": str(recorded_path),
        "source_path": str(receipt_path),
        "sha256": _sha256(recorded_path),
        "receipt_id": payload.get("receipt_id"),
        "claim_status": payload.get("claim_status"),
        "cost_basis": metrics.get("cost_basis"),
        "net_return": metrics.get("net_return"),
        "commission_cost": metrics.get("commission_cost"),
        "funding_cost": metrics.get("funding_cost"),
        "n_bars": metrics.get("n_bars"),
        "verdicts": {
            "economic": verdicts.get("economic"),
            "execution": verdicts.get("execution"),
            "statistical": verdicts.get("statistical"),
        },
        "cost_reconciliation_present_in_receipt": "cost_reconciliation" in payload,
    }


def measure(args: argparse.Namespace) -> dict[str, Any]:
    tape_path = Path(args.tape)
    if not tape_path.exists():
        raise SystemExit(f"[#436] FAIL: real tape absent at {tape_path}")

    tape = load_multitape(str(tape_path), limit=args.bars, offset=args.offset)
    end_ns = [c.end_ns for c in tape.candles[tape.instruments[0]]]
    sleeves = (SleeveSpec("incumbent", 1, 28, 1.0),)
    engine_kwargs: dict[str, Any] = {
        "per_leg_notional": Decimal(str(PER_LEG_NOTIONAL)),
        "taker_fee": Decimal(str(TAKER_FEE)),
        "initial_balance": Decimal(str(CAPITAL)),
    }
    funded = run_portfolio_backtest(
        tape.candles, sleeves, tape.funding, funding_dropped=tape.funding_dropped, **engine_kwargs
    )
    unfunded = run_portfolio_backtest(
        tape.candles, sleeves, (), funding_dropped=tape.funding_dropped, **engine_kwargs
    )
    identical = trade_signature(unfunded) == trade_signature(funded)
    if not identical:
        raise SystemExit("[#436] FAIL: funding feed changed the trade signature; measurement invalid")
    drag = float(str(unfunded["account"]["balance_total"]).split()[0]) - float(
        str(funded["account"]["balance_total"]).split()[0]
    )
    closes = {f"{k}-PERP.BINANCE": [float(c.close) for c in v] for k, v in tape.candles.items()}
    quote_volumes = {f"{k}-PERP.BINANCE": list(v) for k, v in tape.quote_volumes.items()}
    series = eb.portfolio_series_from_engine(
        funded, closes, end_ns, CAPITAL, TAKER_FEE, quote_volumes, tape.funding, drag, True
    )
    recon = series.get("cost_reconciliation") or {}
    balance_total = float(recon.get("balance_total", CAPITAL))
    identity = _independent_engine_residual(funded, balance_total, CAPITAL)
    funding_expected = float(series.get("funding_expected") or 0.0)
    funding_residual = drag - (-funding_expected)

    measurement = {
        "phase": args.phase,
        "git_rev": eb.git_info()["rev"],
        "git_dirty": eb.git_info()["dirty"],
        "source_sha256": eb.source_sha256(),
        "generator_command": " ".join(sys.argv),
        "window": {
            "tape": str(tape_path),
            "tape_sha256": tape.tape_sha256,
            "bars": len(end_ns),
            "offset": args.offset,
            "instruments": list(tape.instruments),
            "funding_rows": len(tape.funding),
            "funding_dropped": tape.funding_dropped,
            "first_bar_end_ns": end_ns[0],
            "last_bar_end_ns": end_ns[-1],
            "capital_usdt": CAPITAL,
            "taker_fee": TAKER_FEE,
            "trade_signature_identical": identical,
        },
        "ledger": {
            "n_opened_positions": len(funded.get("opened_positions", [])),
            "n_closed_positions": len(funded.get("closed_positions", [])),
            "balance_total": balance_total,
        },
        # Recomputed here in EVERY phase: the number existed before the fix, it
        # was simply never published.
        "generator_recomputed_engine_closed_loop": identity,
        "engine_closed_loop": {
            "balance_total": balance_total,
            "balance_delta": recon.get("balance_delta"),
            "sum_realized_pnl": recon.get("sum_realized_pnl"),
            "open_entry_commissions_of_open_positions": recon.get(
                "open_entry_commissions_of_open_positions"
            ),
            "residual_usdt": recon.get("engine_series_residual_usdt"),
            "residual_measured": recon.get("engine_series_residual_measured"),
            "tolerance_usdt": recon.get("engine_series_tolerance_usdt"),
            "ok": recon.get("engine_series_ok"),
        },
        "funding_reconciliation": {
            "measured_dual_run_drag_usdt": drag,
            "expected_from_real_funding_rows_usdt": funding_expected,
            "residual_usdt": funding_residual,
            "residual_published_usdt": recon.get("funding_residual_usdt"),
            "tolerance_usdt": recon.get("funding_tolerance_usdt"),
            "ok": series.get("funding_reconciled"),
            "boundaries_held": series.get("funding_boundaries_held"),
        },
        "loop": {
            "loop_err_is_conjunction": recon.get("loop_err_is_conjunction"),
            "engine_series_residual_abs_usdt": recon.get("engine_series_residual_abs_usdt"),
            "funding_residual_abs_usdt": (recon.get("loop_err_components_usdt") or {}).get(
                "funding_residual_abs"
            ),
            "components_usdt": recon.get("loop_err_components_usdt"),
            "closed_loop_error": recon.get("closed_loop_error"),
            "loop_ok": recon.get("loop_ok"),
            "cost_basis": series.get("cost_basis"),
        },
        "graft": {
            "equity_construction": series.get("equity_construction"),
            "equity_terminal": series["equity"][-1],
            "raw_equity_terminal": series["raw_equity"][-1],
            "measured_graft_total_usdt": series["equity"][-1] - series["raw_equity"][-1],
            "declared_adjustment_per_bar_usdt": series.get("reconciliation_adjustment_per_bar"),
            "declared_adjustment_total_usdt": recon.get("reconciliation_adjustment_total_usdt"),
            "equity_mtm_gap_usdt": recon.get("equity_mtm_gap_usdt"),
        },
        "published": {
            "series_keys": sorted(series.keys()),
            "cost_reconciliation_fields": sorted(recon.keys()),
            "cost_basis": series.get("cost_basis"),
            "fail_closed": not str(series.get("cost_basis", "")).startswith("VERIFIED"),
        },
    }
    if args.bound_receipt:
        copy_to = (
            Path(args.copy_bound_receipt_to) / f"bound_receipt_{args.phase}.json"
            if args.copy_bound_receipt_to
            else None
        )
        measurement["bound_receipt"] = _bound_receipt_block(Path(args.bound_receipt), copy_to)
    return measurement


def compose(before_path: Path, after_path: Path, out_path: Path) -> dict[str, Any]:
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))
    composed = {
        "issue": "#436",
        "title": "Portfolio equity grafts balance, loop residual unreported",
        "claim_status": "NO_ECONOMIC_CLAIM",
        "note": (
            "Mechanics/accounting reconciliation over a real tape window. The two "
            "phases are two runs of the SAME generator command on two code "
            "revisions (pre-fix and fixed); both measurements are recorded, not "
            "asserted. No economic claim is made or implied."
        ),
        "generator": {
            "script": SCRIPT_REL,
            "before_command": before.get("generator_command"),
            "after_command": after.get("generator_command"),
            "compose_command": " ".join(sys.argv),
        },
        "window": after["window"],
        "engine_closed_loop": after["engine_closed_loop"],
        "funding_reconciliation": after["funding_reconciliation"],
        "loop": after["loop"],
        "graft": after["graft"],
        "before": {
            "source_sha256": before.get("source_sha256"),
            "git_rev": before.get("git_rev"),
            "generator_recomputed_engine_closed_loop": before[
                "generator_recomputed_engine_closed_loop"
            ],
            "engine_closed_loop": before["engine_closed_loop"],
            "funding_reconciliation": before["funding_reconciliation"],
            "loop": before["loop"],
            "graft": before["graft"],
            "published": before["published"],
            "bound_receipt": before.get("bound_receipt"),
        },
        "after": {
            "source_sha256": after.get("source_sha256"),
            "git_rev": after.get("git_rev"),
            "generator_recomputed_engine_closed_loop": after[
                "generator_recomputed_engine_closed_loop"
            ],
            "engine_closed_loop": after["engine_closed_loop"],
            "funding_reconciliation": after["funding_reconciliation"],
            "loop": after["loop"],
            "graft": after["graft"],
            "published": after["published"],
            "bound_receipt": after.get("bound_receipt"),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(composed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return composed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "after"))
    parser.add_argument("--tape", default=DEFAULT_TAPE)
    parser.add_argument("--bars", type=int, default=500)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--bound-receipt", default=None)
    parser.add_argument(
        "--copy-bound-receipt-to",
        default=None,
        help="directory to store a durable copy of the bound receipt beside the evidence",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--compose", nargs=2, metavar=("BEFORE", "AFTER"))
    args = parser.parse_args(argv)

    if args.compose:
        payload = compose(Path(args.compose[0]), Path(args.compose[1]), Path(args.out))
        print(json.dumps({k: payload[k] for k in ("issue", "claim_status")}))
        return 0
    if not args.phase:
        parser.error("--phase is required unless --compose is given")
    measurement = measure(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(measurement, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"[#436:{args.phase}] cost_basis={measurement['published']['cost_basis']} "
        f"publishes_residual="
        f"{'engine_series_residual_usdt' in measurement['published']['cost_reconciliation_fields']} "
        f"recomputed_residual={measurement['generator_recomputed_engine_closed_loop']['residual_usdt']:.3e} "
        f"loop_err={measurement['loop']['closed_loop_error']!r} "
        f"-> {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
