"""Central v8-next command entry point (single binding for all app commands).

Usage:
    python -m v8_next.app.cli status [--output-dir DIR]
    python -m v8_next.app.benchmark ...        # full benchmark battery
    python -m v8_next.app.cli benchmark [--case-id ID] [--output-dir DIR]
        [--html-out PATH] [--all-pass] [--diagnostic-only]
        [--tape-path PATH] [--live-fills PATH]

`status` is the project dashboard: git revision, tape inventory, code/test
footprint, and the latest benchmark receipt rendered as the canonical
readiness table. It runs no engine and never mints claims.
`benchmark` delegates to the D-153 end-to-end runner (v8_next.app.benchmark).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from v8_next.evaluation.benchmark_receipt import BenchmarkLedger
from v8_next.evaluation.certificate import PolicyCertificate

DEFAULT_OUTPUT_DIR = "artifacts/benchmarks"
DEFAULT_TAPE_ROOT = "research/tape"


def _git_info() -> dict[str, str]:
    def run(*args: str) -> str:
        try:
            out = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return out.stdout.strip() if out.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    dirty = run("status", "--porcelain")
    return {
        "rev": run("rev-parse", "--short", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": "yes" if dirty and dirty != "unknown" else ("unknown" if dirty == "unknown" else "no"),
    }


def _tape_inventory(root: Path) -> list[tuple[str, int]]:
    if not root.is_dir():
        return []
    rows = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            files = [f for f in child.iterdir() if f.is_file()]
            rows.append((child.name, sum(f.stat().st_size for f in files)))
    return rows


def _code_footprint(src_root: Path) -> tuple[int, int]:
    src = src_root / "src" / "v8_next"
    tests = src_root / "tests"
    n_src = sum(1 for _ in src.rglob("*.py")) if src.is_dir() else 0
    n_tests = sum(1 for _ in tests.glob("test_*.py")) if tests.is_dir() else 0
    return n_src, n_tests


def cmd_status(args: argparse.Namespace) -> int:
    out_dir = Path(args.output_dir)
    print("=== v8-next status ===")
    git = _git_info()
    print(f"rev: {git['rev']}  branch: {git['branch']}  dirty: {git['dirty']}")

    package_root = Path(__file__).resolve().parents[3]
    n_src, n_tests = _code_footprint(package_root)
    print(f"source files: {n_src}  test files: {n_tests}")

    tapes: list[tuple[str, int]] = []
    for root in (package_root.parent, package_root):
        tapes = _tape_inventory(root / DEFAULT_TAPE_ROOT)
        if tapes:
            break
    if tapes:
        print("tapes:")
        for name, size in tapes:
            print(f"  {name}  ({size / 1e6:.1f} MB)")
    else:
        print("tapes: none found")

    ledger_path = out_dir / "benchmark_ledger.jsonl"
    if not ledger_path.is_file():
        print(f"benchmark: no ledger at {ledger_path} — run `cli benchmark` first")
        return 0
    ledger = BenchmarkLedger.load_jsonl(ledger_path)
    chain_ok, chain_msg = ledger.verify_chain()
    print(f"ledger: {len(ledger)} entries  chain: {'VERIFIED' if chain_ok else 'BROKEN'} ({chain_msg})")
    if not ledger.entries:
        return 0
    last = ledger.entries[-1].receipt
    print(f"latest: case={last.case_id} policy={last.policy_id} capability={last.capability_score:.1f}")
    print()
    print(PolicyCertificate.generate(last).render_ascii())
    return 0


def cmd_benchmark(argv: list[str]) -> int:
    from v8_next.app import benchmark as benchmark_mod

    old_argv = sys.argv
    sys.argv = ["v8_next.app.benchmark", *argv]
    try:
        return benchmark_mod.main()
    finally:
        sys.argv = old_argv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="v8-next",
        description="Central v8-next command entry point.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Project dashboard + latest readiness table.")
    p_status.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p_status.set_defaults(func=cmd_status)

    p_bench = sub.add_parser("benchmark", help="Run the D-153 benchmark battery.")
    p_bench.add_argument("--case-id", default="BC-D153-CANONICAL-01")
    p_bench.add_argument("--policy-id", default="pol_28_expert_ensemble")
    p_bench.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p_bench.add_argument("--html-out", default=f"{DEFAULT_OUTPUT_DIR}/forensic_report.html")
    p_bench.add_argument("--all-pass", action="store_true")
    p_bench.add_argument("--resolve-gates", action="store_true", default=True)
    p_bench.add_argument("--diagnostic-only", dest="resolve_gates", action="store_false")
    p_bench.add_argument("--tape-path", default=None)
    p_bench.add_argument("--live-fills", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, rest = parser.parse_known_args(argv)
    if args.command == "status":
        if rest:
            parser.error(f"unexpected args for status: {' '.join(rest)}")
        return args.func(args)
    if args.command == "benchmark":
        from v8_next.evaluation.gate_resolution import DEFAULT_TAPE_PATH

        if not args.tape_path and not DEFAULT_TAPE_PATH.exists():
            print(
                f"error: real tape not found at {DEFAULT_TAPE_PATH}; "
                "synthetic fallback is banned for benchmark runs.",
                file=sys.stderr,
            )
            return 2
        passthrough = []
        if args.case_id != "BC-D153-CANONICAL-01":
            passthrough += ["--case-id", args.case_id]
        if args.policy_id != "pol_28_expert_ensemble":
            passthrough += ["--policy-id", args.policy_id]
        passthrough += ["--output-dir", args.output_dir, "--html-out", args.html_out]
        if args.all_pass:
            passthrough.append("--all-pass")
        passthrough.append("--resolve-gates" if args.resolve_gates else "--diagnostic-only")
        if args.tape_path:
            passthrough += ["--tape-path", args.tape_path]
        if args.live_fills:
            passthrough += ["--live-fills", args.live_fills]
        passthrough += rest
        return cmd_benchmark(passthrough)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
