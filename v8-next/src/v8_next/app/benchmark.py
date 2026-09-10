"""Benchmark CLI command (D-153 End-to-End Benchmark Runner & Report).

Usage:
    python -m v8_next.app.benchmark [--case-id ID] [--output-dir DIR] [--html-out PATH]
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from v8_next.adapters.expert_strategy import ExpertStrategyConfig
from v8_next.evaluation.gate_resolution import DEFAULT_TAPE_PATH, load_tape_candles
from v8_next.evaluation.report import generate_forensic_html_report
from v8_next.evaluation.runner import BenchmarkCase, BenchmarkRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="V8.5 Benchmark Fabric Runner")
    parser.add_argument("--case-id", default="BC-D153-CANONICAL-01", help="Benchmark Case ID")
    parser.add_argument("--policy-id", default="pol_28_expert_ensemble", help="Target Policy ID")
    parser.add_argument("--output-dir", default="artifacts/benchmarks", help="Output artifact directory")
    parser.add_argument("--html-out", default="artifacts/benchmarks/forensic_report.html", help="HTML report output path")
    parser.add_argument(
        "--resolve-gates",
        action="store_true",
        default=True,
        help="Execute empirical gate resolution battery for G3-G9 (default: True)",
    )
    parser.add_argument(
        "--diagnostic-only",
        dest="resolve_gates",
        action="store_false",
        help="Run single diagnostic cell only without resolving G3-G9",
    )
    parser.add_argument(
        "--tape-path",
        default=str(DEFAULT_TAPE_PATH),
        help="Path to real market tape (default: research/tape/btcusdt-1h-12m/tape.jsonl)",
    )
    parser.add_argument(
        "--live-fills",
        default=None,
        help="Optional path to venue-settled fills.jsonl for G8 verification",
    )
    parser.add_argument(
        "--execution-profile",
        default=None,
        help=(
            "Nautilus simulated-execution profile (baseline | realistic | "
            "volume_aware): fill model, fee model, latency model plus the "
            "liquidity/queue knobs. Omit to keep engine defaults; the receipt "
            "then reports no declared execution semantics instead of implying one."
        ),
    )
    parser.add_argument(
        "--determinism-rerun",
        action="store_true",
        help=(
            "Re-execute the engine and compare fill signatures, turning G2 from "
            "UNRUN into measured evidence. Doubles engine runtime."
        ),
    )
    args = parser.parse_args()

    print(f"=== Starting D-153 Benchmark Execution: {args.case_id} ===")
    case = BenchmarkCase(
        case_id=args.case_id,
        policy_id=args.policy_id,
        dataset_name="BTCUSDT-1H-PERP",
        strategy_config=ExpertStrategyConfig(
            min_support_quorum=1,
            max_contradiction_tolerance=28,
            bracket_stop_pct=Decimal("0.02"),
            bracket_target_pct=Decimal("0.04"),
        ),
    )

    runner = BenchmarkRunner(output_dir=args.output_dir)

    tape_file = Path(args.tape_path)
    if not tape_file.exists():
        print(
            f"error: real tape not found at {tape_file}; synthetic fallback is "
            "banned for benchmark runs (full D-153 rule).",
            file=sys.stderr,
        )
        return 2
    print(f"[+] Loading verified real Binance market tape from {tape_file}...")
    candles = load_tape_candles(tape_file, limit=500)
    print(f"[+] Loaded {len(candles)} real hourly bars.")

    result = runner.run(
        case,
        candles,
        resolve_gates=args.resolve_gates,
        tape_path=tape_file if tape_file.exists() else None,
        live_fills_path=Path(args.live_fills) if args.live_fills else None,
        execution_profile=args.execution_profile,
        measure_determinism=args.determinism_rerun,
    )
    execution = result.gate_metrics.get("execution") if result.gate_metrics else None
    if execution:
        print(
            f"[+] Execution profile: {execution.get('profile')} "
            f"(digest {str(execution.get('digest'))[:12]}) | "
            f"fills={execution.get('fills_count')} "
            f"shortfall_bps={execution.get('slippage_bps_mean')} "
            f"samples={execution.get('slippage_samples')} | "
            f"evidence={execution.get('evidence_class')}"
        )
    g2 = (result.gate_metrics or {}).get("g2", {})
    print(f"[+] G2 determinism: {g2.get('status')} ({g2.get('reason')})")
    print(f"[+] Nautilus Backtest Completed: {result.total_bars} bars, {result.total_trades} trades")
    print(f"[+] Capability Score: {result.capability_score:.1f} / 100")
    if result.domain_scores:
        print("[+] Per-domain breakdown (loop engineering: lowest first):")
        for name, d in sorted(result.domain_scores.items(), key=lambda kv: kv[1]["score"]):
            print(
                f"    {name:<28} {d['score']:>5.1f}  "
                f"band[{d['band_low']:.1f},{d['band_high']:.1f}]  "
                f"w={d['weight']:.2f}  n={d['sample_size']}"
            )
    else:
        print("[+] Per-domain breakdown: absent (no trades — nothing to decompose)")
    if result.gate_metrics:
        print("[+] Gate metric deltas:")
        for gname in sorted(result.gate_metrics):
            m = result.gate_metrics[gname]
            if isinstance(m, dict):
                keys = ", ".join(f"{k}={m[k]}" for k in list(m)[:6])
                print(f"    {gname}: {keys}")
    elif args.resolve_gates:
        print("[+] Gate metric deltas: battery ran but emitted no metrics")
    else:
        print("[+] Gates G3-G9 unresolved (diagnostic cell); re-run without --diagnostic-only")
    print(f"[+] Ledger Entry Hash: {result.ledger_entry_hash[:16]}...{result.ledger_entry_hash[-8:]}")
    print(f"[+] Bound Artifact: {result.native_ledger_binding.path} (SHA: {result.native_ledger_binding.sha256_hex[:12]}...)")

    if result.claim_record is not None:
        print(f"[+] Statutory Claim Record Minted: {result.claim_record.claim_id[:16]}... ({result.claim_record.claim_class})")

    # Render Terminal ASCII Policy Certificate
    print()
    print(result.certificate.render_ascii())

    # Generate forensic HTML report
    report_path = Path(args.html_out)
    is_valid = generate_forensic_html_report(result.receipt, report_path)
    print(f"[+] Forensic HTML Report Generated: {report_path} (Valid: {is_valid})")

    # Verify ledger chain
    chain_valid, chain_msg = runner.ledger.verify_chain()
    print(f"[+] Benchmark Ledger Cryptographic Chain: {'VERIFIED' if chain_valid else 'BROKEN'} ({chain_msg})")

    return 0 if chain_valid else 1


if __name__ == "__main__":
    sys.exit(main())
