"""Benchmark CLI command (D-153 End-to-End Benchmark Runner & Report).

Usage:
    python -m v8_next.app.benchmark [--case-id ID] [--output-dir DIR] [--html-out PATH] [--all-pass]
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from v8_next.adapters.expert_strategy import ExpertStrategyConfig
from v8_next.domain.market import Candle
from v8_next.evaluation.gate_resolution import DEFAULT_TAPE_PATH, load_tape_candles
from v8_next.evaluation.report import generate_forensic_html_report
from v8_next.evaluation.runner import BenchmarkCase, BenchmarkRunner


def build_synthetic_benchmark_dataset() -> list[Candle]:
    """Build a deterministic causal market sequence for benchmark evaluation."""
    hour_ns = 3600 * 10**9
    candles = [
        Candle(
            "BTCUSDT-PERP.BINANCE",
            i * hour_ns,
            (i + 1) * hour_ns,
            Decimal("100"),
            Decimal("100.5"),
            Decimal("99.5"),
            Decimal("100"),
            Decimal("100"),
            (i + 1) * hour_ns,
            (i + 1) * hour_ns,
            "benchmark-feed",
        )
        for i in range(48)
    ]
    # Breakout candles
    candles.append(
        Candle(
            "BTCUSDT-PERP.BINANCE",
            48 * hour_ns,
            49 * hour_ns,
            Decimal("101"),
            Decimal("122"),
            Decimal("100"),
            Decimal("120"),
            Decimal("500"),
            49 * hour_ns,
            49 * hour_ns,
            "benchmark-feed",
        )
    )
    candles.append(
        Candle(
            "BTCUSDT-PERP.BINANCE",
            49 * hour_ns,
            50 * hour_ns,
            Decimal("120"),
            Decimal("125"),
            Decimal("119"),
            Decimal("123"),
            Decimal("200"),
            50 * hour_ns,
            50 * hour_ns,
            "benchmark-feed",
        )
    )
    return candles


def main() -> int:
    parser = argparse.ArgumentParser(description="V8.5 Benchmark Fabric Runner")
    parser.add_argument("--case-id", default="BC-D153-CANONICAL-01", help="Benchmark Case ID")
    parser.add_argument("--policy-id", default="pol_28_expert_ensemble", help="Target Policy ID")
    parser.add_argument("--output-dir", default="artifacts/benchmarks", help="Output artifact directory")
    parser.add_argument("--html-out", default="artifacts/benchmarks/forensic_report.html", help="HTML report output path")
    parser.add_argument("--all-pass", action="store_true", help="Force all-pass state for certification test")
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
    if tape_file.exists() and args.resolve_gates:
        print(f"[+] Loading verified real Binance market tape from {tape_file}...")
        candles = load_tape_candles(tape_file, limit=500)
        print(f"[+] Loaded {len(candles)} real hourly bars.")
    else:
        candles = build_synthetic_benchmark_dataset()

    result = runner.run(
        case,
        candles,
        all_pass_mode=args.all_pass,
        resolve_gates=args.resolve_gates,
        tape_path=tape_file if tape_file.exists() else None,
        live_fills_path=Path(args.live_fills) if args.live_fills else None,
    )
    print(f"[+] Nautilus Backtest Completed: {result.total_bars} bars, {result.total_trades} trades")
    print(f"[+] Capability Score: {result.capability_score:.1f} / 100")
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
