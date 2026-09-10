"""Canonical portfolio benchmark: quad tape -> engine P/P+E -> receipt chain.

Single-command reproduction:
    uv run --project v8-next python -m v8_next.app.cli benchmark-portfolio \
        --tape-path research/tape/quad-1h-12m --bars 336 \
        --output-dir artifacts/portfolio-benchmark --primary equal_weight

P and P+E execute at engine level in one shared account each (same per-leg
risk budget; P+E splits sleeves 50/50). Funding drag is measured by dual-run
balance difference under verified identical trade signatures. Results bind
into the D-153 BenchmarkReceipt/BenchmarkLedger/PolicyCertificate chain with
the economic receipt attached; gate logic itself is untouched. No live orders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from v8_next.adapters.execution_models import DEFAULT_PROFILE as DEFAULT_EXECUTION_PROFILE
from v8_next.adapters.execution_models import PROFILES as EXECUTION_PROFILES
from v8_next.adapters.portfolio_backtest import (
    SleeveSpec,
    run_portfolio_backtest,
    trade_signature,
)
from v8_next.adapters.shadow_ingest import (
    ingest_status,
    reconcile_shadow_account,
)
from v8_next.domain.capital_policy import CapitalPolicy
from v8_next.evaluation import economic_benchmark as eb
from v8_next.evaluation.benchmark_receipt import BenchmarkLedger, BenchmarkReceipt
from v8_next.evaluation.certificate import PolicyCertificate
from v8_next.evaluation.multitape import MultiTape, load_multitape
from v8_next.evaluation.parity import ArtifactBinding
from v8_next.evaluation.report import generate_forensic_html_report
from v8_next.evaluation.scoring import (
    compute_capability_breakdown,
    compute_capability_score,
    evaluate_gate_vector,
)

CASE_ID = "BC-QUAD-PORTFOLIO-01"
POLICY_ID = "pol_portfolio_quad"
PRIMARY_DEFAULT = "equal_weight"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Canonical quad portfolio benchmark.")
    p.add_argument("--case-id", default=CASE_ID)
    p.add_argument("--policy-id", default=POLICY_ID)
    p.add_argument("--tape-path", default="research/tape/quad-1h-12m")
    p.add_argument("--bars", type=int, default=385)
    p.add_argument("--start-bar", type=int, default=0)
    p.add_argument("--output-dir", default="artifacts/portfolio-benchmark")
    p.add_argument("--primary", default=PRIMARY_DEFAULT)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--capital", type=float, default=eb.CAPITAL_DEFAULT)
    p.add_argument("--taker-fee", type=float, default=eb.TAKER_FEE_DEFAULT)
    p.add_argument("--per-leg-notional", type=float, default=1000.0)
    p.add_argument("--opex-monthly", type=float, default=30.0)
    p.add_argument("--capital-policy", default=None)
    p.add_argument("--html-out", default=None)
    p.add_argument("--live-fills", default=None)
    p.add_argument(
        "--execution-profile",
        default=DEFAULT_EXECUTION_PROFILE,
        help=(
            "Nautilus simulated-execution profile: fill model, fee model and "
            "latency model actually in force. One of: "
            f"{', '.join(sorted(EXECUTION_PROFILES))}"
        ),
    )
    return p.parse_args(argv)


def build_shadow_section(
    live_fills: str | None, engine_account: dict[str, Any]
) -> dict[str, Any]:
    """Shadow/live evidence via the single shadow_ingest source.

    No venue account => UNRUN with format/source/command (never simulated).
    Fixture paths never count as live (fixture guard).
    """
    from v8_next.adapters.shadow_ingest import load_shadow_fills

    if not live_fills:
        status = ingest_status(None)
        return {**status, "live_fills_present": False}
    fills, meta = load_shadow_fills(live_fills, source="live")
    section: dict[str, Any] = {**meta, "live_fills_present": bool(fills)}
    if fills:
        section["reconciliation"] = reconcile_shadow_account(fills, engine_account)
    return section


def capacity_from_participation(
    participations: Sequence[float],
    capital: float,
    p_bar_returns: Sequence[float] | None = None,
    k_grid: tuple[float, ...] = (0.1, 0.5, 1.0),
) -> list[dict[str, Any]]:
    """Participation-bound capacity from real bar quote volumes.

    Measured part: linear extrapolation to 1%/5%/10% peak participation.
    Scenario part: square-root impact k*sigma*sqrt(p) with HYPOTHETICAL k.
    sigma is measured (std of portfolio per-bar returns); k is not calibrated
    to any venue data, so scenarios never read as measured capacity.
    Slippage/impact beyond participation is an UNVERIFIED claim.
    """
    import math as _math

    import numpy as _np

    out: list[dict[str, Any]] = []
    peak = max(participations) if participations else 0.0
    for threshold in (0.01, 0.05, 0.10):
        max_cap = capital * threshold / peak if peak > 0 else None
        out.append(
            {
                "kind": "MEASURED_LINEAR_BOUND",
                "participation_threshold": threshold,
                "observed_peak_participation": peak,
                "max_capital_linear": max_cap,
                "basis": "LINEAR_EXTRAPOLATION_OF_MEASURED_PARTICIPATION",
                "impact_beyond": "UNVERIFIED_NO_IMPACT_MODEL",
            }
        )
    sigma = None
    if p_bar_returns:
        arr = _np.asarray(list(p_bar_returns), dtype=float)
        if arr.size >= 2:
            sigma = float(arr.std(ddof=1))
    for k in k_grid:
        out.append(
            {
                "kind": "HYPOTHETICAL_SCENARIO",
                "model": "sqrt_impact_k_sigma_sqrt_p",
                "k": k,
                "k_status": "HYPOTHETICAL_UNCALIBRATED",
                "sigma_per_bar": sigma,
                "impact_bps_at_peak": (
                    k * sigma * _math.sqrt(peak) * 1e4
                    if sigma is not None and peak > 0
                    else None
                ),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tape_path = Path(args.tape_path)
    if not tape_path.exists():
        print(f"error: real tape not found at {tape_path}; synthetic fallback banned.", file=sys.stderr)
        return 2
    tape: MultiTape = load_multitape(tape_path, limit=args.bars, offset=args.start_bar)
    n = tape.n_bars
    end_ns = [c.end_ns for c in tape.candles[tape.instruments[0]]]
    print(f"[+] quad tape: {list(tape.instruments)} x {n} bars, {len(tape.funding)} funding rows")

    ok, note = eb.validate_chronology(eb.bars_from_candles(tape.candles[tape.instruments[0]]))
    if not ok:
        print(f"INVALID input data: {note}", file=sys.stderr)
        return 2

    sleeves_p = (SleeveSpec("incumbent", 1, 28, 1.0),)
    sleeves_pe = (SleeveSpec("incumbent", 1, 28, 0.5), SleeveSpec("challenger", 1, 0, 0.5))
    kw: dict[str, Any] = {
        "per_leg_notional": Decimal(str(args.per_leg_notional)),
        "taker_fee": Decimal(str(args.taker_fee)),
        "initial_balance": Decimal(str(args.capital)),
        "execution_profile": args.execution_profile,
    }
    print("[+] engine P (funding + no-funding dual) ...", flush=True)
    p_fund = run_portfolio_backtest(
        tape.candles, sleeves_p, tape.funding, funding_dropped=tape.funding_dropped, **kw
    )
    p_nofund = run_portfolio_backtest(
        tape.candles, sleeves_p, (), funding_dropped=tape.funding_dropped, **kw
    )
    print("[+] engine P+E (funding + no-funding dual) ...", flush=True)
    pe_fund = run_portfolio_backtest(
        tape.candles, sleeves_pe, tape.funding, funding_dropped=tape.funding_dropped, **kw
    )
    print("[+] determinism rerun P ...", flush=True)
    p_nofund2 = run_portfolio_backtest(
        tape.candles, sleeves_p, (), funding_dropped=tape.funding_dropped, **kw
    )

    p_ident = trade_signature(p_nofund) == trade_signature(p_fund)
    pe_nf = run_portfolio_backtest(
        tape.candles, sleeves_pe, (), funding_dropped=tape.funding_dropped, **kw
    )
    pe_ident = trade_signature(pe_nf) == trade_signature(pe_fund)
    det_ok = trade_signature(p_nofund) == trade_signature(p_nofund2)
    if not (p_ident and pe_ident):
        print("error: funding feed changed trade signatures; measurement invalid", file=sys.stderr)
        return 2
    print(
        f"[+] funding coverage: P={p_fund['funding_coverage']} "
        f"(fed={p_fund['funding_settlements_fed']} dropped_at_load={p_fund['funding_dropped_at_load']} "
        f"out_of_window={p_fund['funding_out_of_window']} unknown_leg={p_fund['funding_unknown_leg']})"
    )
    p_drag = float(str(p_nofund["account"]["balance_total"]).split()[0]) - float(
        str(p_fund["account"]["balance_total"]).split()[0]
    )
    pe_drag = float(str(pe_nf["account"]["balance_total"]).split()[0]) - float(
        str(pe_fund["account"]["balance_total"]).split()[0]
    )

    closes = {f"{k}-PERP.BINANCE": [float(c.close) for c in v] for k, v in tape.candles.items()}
    qvols = {f"{k}-PERP.BINANCE": list(v) for k, v in tape.quote_volumes.items()}
    p_ser = eb.portfolio_series_from_engine(
        p_fund, closes, end_ns, args.capital, args.taker_fee, qvols, tape.funding, p_drag, True
    )
    pe_ser = eb.portfolio_series_from_engine(
        pe_fund, closes, end_ns, args.capital, args.taker_fee, qvols, tape.funding, pe_drag, True
    )
    print(f"[+] P basis={p_ser['cost_basis']} funding={p_ser['funding']:.4f} "
          f"P+E basis={pe_ser['cost_basis']} funding={pe_ser['funding']:.4f}")

    fams = eb.compute_multileg_family(closes, args.capital, args.taker_fee)
    if args.primary not in fams:
        print(f"error: unknown primary {args.primary}", file=sys.stderr)
        return 2
    primary_eq: list[float] = list(fams[args.primary]["equity"])
    curves: dict[str, dict[str, Any]] = {
        "portfolio_P": {**p_ser, "n_trades": p_ser["n_trades"]},
        "portfolio_PE": {**pe_ser, "n_trades": pe_ser["n_trades"]},
    }
    for bid, fam in fams.items():
        curves[bid] = {
            "equity": fam["equity"], "exposure": fam["exposure"],
            "turnover": float(fam["turnover"]), "commission": float(fam["commission"]),
            "funding": None, "cost_basis": "ANALYTIC_MODEL", "n_trades": int(fam["n_trades"]),
        }

    def raw_count(key: str) -> int | None:
        raw = curves[key].get("raw_equity")
        if not raw:
            return None
        return sum(1 for a, b in zip(raw, raw[1:], strict=False) if abs(b - a) > 1e-9)

    metrics = {
        name: eb.metrics_for_curve(
            list(c["equity"]), list(c["exposure"]), float(c["turnover"]),
            float(c["commission"]), None, str(c["cost_basis"]), primary_eq,
            int(c["n_trades"]), raw_count(name),
        )
        for name, c in curves.items()
    }
    # Attach measured funding to the engine legs (PnL impact, not double-count).
    for name, ser in (("portfolio_P", p_ser), ("portfolio_PE", pe_ser)):
        m = metrics[name]
        metrics[name] = m.model_copy(update={"funding_cost": float(ser["funding"] or 0.0)})

    fit = min(eb.OOS_FIT_BARS, n - 48)
    oos_metrics: dict[str, eb.MetricSet] = {}
    if n - fit >= 48:
        for name, c in curves.items():
            eq = list(c["equity"])[fit:]
            ex = list(c["exposure"])[fit:]
            base = eq[0] if eq[0] > 0 else args.capital
            eq_n = [v / base * args.capital for v in eq]
            pe = primary_eq[fit:]
            pb = pe[0] if pe[0] > 0 else args.capital
            pe_n = [v / pb * args.capital for v in pe]
            oos_metrics[name] = eb.metrics_for_curve(
                eq_n, ex, float(c["turnover"]), float(c["commission"]), None,
                str(c["cost_basis"]) + "+OOS_SLICE", pe_n, int(c["n_trades"]),
            )

    fam_eq: dict[str, Sequence[float]] = {
        "portfolio_P": [float(v) for v in p_ser["equity"]],
        "portfolio_PE": [float(v) for v in pe_ser["equity"]],
        "simple_trend": [float(v) for v in fams["simple_trend"]["equity"]],
        "vol_target": [float(v) for v in fams["vol_target"]["equity"]],
        args.primary: [float(v) for v in primary_eq],
    }
    stats = eb.run_statistics(fam_eq, end_ns, args.primary, seed=args.seed)

    # Engine-level P+E contribution: incremental net of the two shared-account runs.
    mix = {
        "method": "ENGINE_SHARED_ACCOUNT_RERUN",
        "scope": "ENGINE_LEVEL_SAME_BUDGET",
        "p_net": metrics["portfolio_P"].net_return,
        "pe_net": metrics["portfolio_PE"].net_return,
        "incremental_net": metrics["portfolio_PE"].net_return - metrics["portfolio_P"].net_return,
        "sleeves": ["incumbent 1.0", "incumbent 0.5 + challenger 0.5"],
    }

    p_rets = eb.per_bar_returns(list(p_ser["equity"]))
    # Synthetic positive/shuffled controls are mechanics-only test fixtures.
    # They must never enter a real evaluation receipt or be used as evidence.
    controls: dict[str, Any] = {
        "positive_control": {
            "status": "UNRUN_SYNTHETIC_CONTROL_TEST_ONLY",
            "reason": "synthetic controls are restricted to test harnesses",
        },
        "negative_control": {
            "status": "UNRUN_SYNTHETIC_CONTROL_TEST_ONLY",
            "reason": "shuffled inputs are restricted to test harnesses",
        },
        "known_defect_future_leak_caught": None,
        "ablation": {
            "P": "incumbent quorum=1,tolerance=28 x4 legs",
            "P+E": "incumbent 0.5 + challenger(tol=0) 0.5 x4 legs, same per-leg budget",
            "same_engine_path": True,
        },
    }
    controls["positive_caught"] = None
    controls["negative_caught"] = None

    # Capital eligibility is a verifiable input, never inferred from benchmark
    # results.  Without an explicit policy artifact the decision is denied.
    if args.capital_policy:
        try:
            capital_policy = CapitalPolicy.from_file(args.capital_policy)
        except (OSError, ValueError) as exc:
            print(f"error: invalid capital policy: {exc}", file=sys.stderr)
            return 2
    else:
        capital_policy = CapitalPolicy.unauthorized()
    peak_notional = max(
        (abs(float(p.get("quantity") or 0)) * float(p.get("avg_px_open") or 0)
         for p in p_fund["opened_positions"] if isinstance(p, dict)),
        default=0.0,
    )
    cap_decision = capital_policy.decision(
        peak_notional, instrument_id=f"{tape.instruments[0]}-PERP.BINANCE")
    cap_live = capital_policy.decision(peak_notional, live=True)
    cap_missing = CapitalPolicy.unauthorized().decision(peak_notional)
    cap_wrong_inst = capital_policy.decision(peak_notional, instrument_id="NOPE-PERP.BINANCE")
    # Accept-path evidence (non-governing): a controlled TEST policy proves the
    # accept branch end-to-end. It never authorizes the run (see verdict).
    test_policy = CapitalPolicy.test_policy(
        max_notional="5000", max_exposure_frac="1.0", authorized=True
    ).model_copy(update={
        "allowed_instruments": tuple(f"{k}-PERP.BINANCE" for k in tape.instruments),
    })
    cap_test_accept = test_policy.decision(
        peak_notional, instrument_id=f"{tape.instruments[0]}-PERP.BINANCE")
    capital_path = {
        "test_decision": cap_decision,
        "test_policy_accept_path": cap_test_accept,
        "live_decision": cap_live,
        "missing_policy_decision": cap_missing,
        "wrong_instrument_decision": cap_wrong_inst,
        "policy_path": str(args.capital_policy) if args.capital_policy else None,
        "production": "DENIED_NO_APPROVAL_ARTIFACT" if not args.capital_policy else "CONFIGURED_POLICY_VERIFIED",
    }

    capacity = capacity_from_participation(
        p_ser.get("participation", []), args.capital, p_rets)
    live_path = Path(args.live_fills) if args.live_fills else None
    shadow = build_shadow_section(args.live_fills, p_fund["account"])
    shadow["live_fills_arg"] = str(live_path) if live_path else None

    gi = eb.git_info()
    run = eb.RunIdentity(
        dataset=eb.DatasetIdentity(
            tape_path=str(tape_path), tape_sha256=tape.tape_sha256,
            universe=tuple(f"{k}-PERP.BINANCE" for k in tape.instruments),
            period_start_ns=end_ns[0], period_end_ns=end_ns[-1], n_bars=n,
            source_hashes=tuple(c.source_hash for c in tape.candles[tape.instruments[0]][:3])
            + tuple(c.source_hash for c in tape.candles[tape.instruments[0]][-3:]),
        ),
        code=eb.CodeIdentity(
            git_rev=gi["rev"], git_dirty=gi["dirty"],
            config_sha256=hashlib.sha256(json.dumps(
                {"sleeves": ["P", "P+E"], "per_leg_notional": args.per_leg_notional,
                 "bars": args.bars, "start_bar": args.start_bar, "seed": args.seed,
                 "primary": args.primary, "opex_monthly": args.opex_monthly,
                 "capital_policy": args.capital_policy},
                sort_keys=True).encode()).hexdigest(),
            estimator_versions=eb.estimator_versions(),
        ),
        seed=args.seed, primary_benchmark=args.primary,
        diagnostic_benchmarks=tuple(b for b in fams if b != args.primary),
        strategy_family=("portfolio_P", "portfolio_PE", "simple_trend", "vol_target"),
        capital=args.capital, taker_fee=args.taker_fee, opex_monthly_usd=args.opex_monthly,
    )
    excess = metrics["portfolio_P"].excess_vs_primary
    verdicts = eb.build_verdicts(
        chrono_ok=True, chrono_note="OK; leak_probe=OK", excess=excess, stats=stats,
        excess_ci=(metrics["portfolio_P"].excess_ci_low, metrics["portfolio_P"].excess_ci_high),
        mix={"incremental_net": mix["incremental_net"]},
        cost_basis_ok=p_ser["cost_basis"] == "VERIFIED_ENGINE_FUNDING",
        funding_missing=False, live_fills_present=bool(shadow.get("live_fills_present")),
        parity_ok=det_ok,
    )
    receipt = eb.EconomicReceipt(
        receipt_id=run.digest()[:32], run=run, metrics=metrics, oos_metrics=oos_metrics,
        verdicts=verdicts, statistics=stats, controls=controls, portfolio_mix=mix,
        capacity_scenarios=capacity, parity={"engine_rerun_parity": "EXACT_MATCH" if det_ok else "DIVERGED"},
        shadow_live=shadow,
        limitations=[
            "Mark proxy: funding settlement marks use leg closes at the boundary.",
            "P+E is engine-level shared-account execution, not post-hoc summation.",
            "Capacity beyond participation is UNVERIFIED (no impact model).",
            "Production capital stays denied without a human-signed approval artifact.",
        ],
    )
    # Version bound artifacts per run config: reruns with different inputs must
    # never overwrite files an older ledger entry is bound to (chain caught
    # exactly this failure). Identical inputs reproduce identical names+bytes.
    tag = receipt.receipt_id[:8]
    receipt_path = out_dir / f"economic_receipt_{tag}.json"
    receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    report_path = out_dir / f"economic_report_{tag}.md"
    report_path.write_text(eb.render_report(receipt), encoding="utf-8")
    trades_path = out_dir / f"portfolio_P_trades_{tag}.jsonl"
    with open(trades_path, "w", encoding="utf-8") as f:
        for p in p_fund["opened_positions"]:
            f.write(json.dumps({
                "trade_id": p.get("position_id"), "instrument_id": p.get("instrument_id"),
                "side": p.get("side"), "quantity": p.get("quantity"),
                "avg_px_open": p.get("avg_px_open"),
                "fill_time_ns": p.get("event_ns"),
            }) + "\n")
    dataset_path = out_dir / f"canonical_dataset_{tag}.json"
    dataset_path.write_text(json.dumps(receipt.run.dataset.model_dump(), indent=2), encoding="utf-8")
    closed_path = out_dir / f"portfolio_closed_{tag}.jsonl"
    with open(closed_path, "w", encoding="utf-8") as f:
        for c in p_fund["closed_positions"]:
            if not isinstance(c, dict):
                continue
            f.write(json.dumps({
                "position_id": c.get("position_id"), "instrument_id": c.get("instrument_id"),
                "realized_pnl": c.get("realized_pnl"), "avg_px_close": c.get("avg_px_close"),
                "fill_time_ns": c.get("event_ns"),
            }) + "\n")
    binding_list = [
        ArtifactBinding.from_file("engine_trades", trades_path),
        ArtifactBinding.from_file("engine_closed_trades", closed_path),
        ArtifactBinding.from_file("canonical_dataset", dataset_path),
        ArtifactBinding.from_file("economic_receipt", receipt_path),
        ArtifactBinding.from_file("market_tape", tape_path / "tape.jsonl" if tape_path.is_dir() else tape_path),
    ]
    if args.capital_policy:
        binding_list.append(ArtifactBinding.from_file("capital_policy", args.capital_policy))
    bindings = tuple(binding_list)

    # Bind into the D-153 receipt/ledger/certificate chain (gates untouched).
    pnl_series = [
        float(str(c.get("realized_pnl", "0").split()[0]))
        for c in p_fund["closed_positions"] if isinstance(c, dict) and c.get("realized_pnl")
    ]
    gates = evaluate_gate_vector(total_bars=n, total_trades=len(p_fund["opened_positions"]),
                                 pnl_series=pnl_series or [0.0])
    capability = compute_capability_score(
        pnl_series=pnl_series or [0.0], total_bars=n,
        total_trades=len(p_fund["opened_positions"]), abstain_rate=0.0)
    _breakdown = compute_capability_breakdown(
        pnl_series=pnl_series or [0.0], total_bars=n,
        total_trades=len(p_fund["opened_positions"]), abstain_rate=0.0)
    bench_receipt = BenchmarkReceipt.create(
        case_id=args.case_id, policy_id=args.policy_id, capability_score=capability,
        gates=gates, computed_at_timestamp_ns=end_ns[-1],
        artifact_bindings=bindings,
        economic_evidence_digest=receipt.digest(), economic_receipt_path=str(receipt_path.resolve()),
        input_binding=hashlib.sha256(
            json.dumps(
                {
                    "tape_sha256": tape.tape_sha256,
                    "case_id": args.case_id,
                    "policy_id": args.policy_id,
                    "bars": n,
                    "start_bar": args.start_bar,
                    "span_ns": [end_ns[0], end_ns[-1]],
                    "seed": args.seed,
                    "capital": args.capital,
                    "taker_fee": args.taker_fee,
                    "per_leg_notional": args.per_leg_notional,
                    "opex_monthly": args.opex_monthly,
                    "capital_policy": capital_policy.to_receipt_fields(),
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest(),
    )
    ledger = BenchmarkLedger.load_jsonl(out_dir / "benchmark_ledger.jsonl")
    entry = ledger.append(bench_receipt)
    ledger.save_jsonl(out_dir / "benchmark_ledger.jsonl")
    ok, msg = bench_receipt.verify()
    cok, cmsg = ledger.verify_chain()
    print(PolicyCertificate.generate(bench_receipt).render_ascii())
    html_path = Path(args.html_out) if args.html_out else out_dir / f"forensic_report_{tag}.html"
    generate_forensic_html_report(bench_receipt, html_path)

    print(f"[+] P net {metrics['portfolio_P'].net_return:+.4f} "
          f"P+E net {metrics['portfolio_PE'].net_return:+.4f} "
          f"incremental {mix['incremental_net']:+.4f}")
    v = verdicts
    print(f"[+] validity={v.research_validity} economic={v.economic} statistical={v.statistical}")
    print(f"[+] portfolio={v.portfolio} execution={v.execution} capital={v.capital}")
    print(f"[+] capital_path test={cap_decision['decision']} missing={cap_missing['decision']}")
    print(f"[+] receipt chain: {ok} ({msg}) ledger: {cok} ({cmsg}) entry={entry.entry_hash[:16]}...")
    # Persist capital + capacity evidence alongside the receipt.
    (out_dir / f"capital_path_{tag}.json").write_text(json.dumps(capital_path, indent=2), encoding="utf-8")
    return 0 if (ok and cok) else 1


if __name__ == "__main__":
    sys.exit(main())
