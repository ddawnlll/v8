#!/usr/bin/env python3
"""End-to-End Deterministic Reproduction & Audit Harness for Rust v8-core.

Performs an exact, 100% reproducible audit pipeline:
1. Builds the optimized release v8-core binary.
2. Runs the evaluation and analysis stages over the certified tape.
3. Renders the full deep-forensic HTML audit report.
4. Executes an independent verification pass to verify bit-level determinism
   (Byte-Identity / Zero-Jitter guarantee).
5. Outputs a cryptographic reproduction certificate with SHA-256 digests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAPE = ROOT / "research" / "tape" / "btcusdt-1h-12m" / "tape.jsonl"
DEFAULT_OUT = ROOT / ".audit" / "rust_audit_current"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_command(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def run_pipeline(binary: Path, tape_path: Path, out_dir: Path, threads: int = 4) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    req_path = out_dir / "request_evaluate.json"
    
    req = {
        "tape_path": str(tape_path.resolve()),
        "universe": ["BTCUSDT"],
        "out_dir": str(out_dir.resolve()),
        "history_depth": 32,
        "threads": threads,
        "engine": "cpu",
    }
    req_path.write_text(json.dumps(req, indent=2), encoding="utf-8")

    # 1. Run v8-core evaluate
    t0 = time.perf_counter()
    code, out_eval, err_eval = run_command([str(binary), "evaluate", str(req_path)])
    eval_duration = time.perf_counter() - t0
    if code != 0:
        raise RuntimeError(f"v8-core evaluate failed:\nSTDOUT: {out_eval}\nSTDERR: {err_eval}")
    eval_meta = json.loads(out_eval)

    # 2. Run v8-core analysis
    t1 = time.perf_counter()
    code, out_ana, err_ana = run_command([str(binary), "analysis", str(req_path)])
    ana_duration = time.perf_counter() - t1
    if code != 0:
        raise RuntimeError(f"v8-core analysis failed:\nSTDOUT: {out_ana}\nSTDERR: {err_ana}")
    ana_meta = json.loads(out_ana)

    # 3. Render HTML Report
    render_script = ROOT / "tools" / "render_rust_audit_html.py"
    html_out = out_dir / "report.html"
    code, out_rend, err_rend = run_command([sys.executable, str(render_script), "--audit-dir", str(out_dir), "--out", str(html_out)])
    if code != 0:
        raise RuntimeError(f"render_rust_audit_html failed:\n{err_rend or out_rend}")

    # Compute Artifact Fingerprints
    artifacts = {
        "candidates.jsonl": sha256_file(out_dir / "candidates.jsonl"),
        "candidate-transitions.jsonl": sha256_file(out_dir / "candidate-transitions.jsonl"),
        "evaluations.jsonl": sha256_file(out_dir / "evaluations.jsonl"),
        "cube-reduced.v82": sha256_file(out_dir / "cube-reduced.v82"),
        "analysis.jsonl": sha256_file(out_dir / "analysis.jsonl"),
    }

    return {
        "eval_duration_sec": eval_duration,
        "ana_duration_sec": ana_duration,
        "total_duration_sec": eval_duration + ana_duration,
        "eval_meta": eval_meta,
        "ana_meta": ana_meta,
        "artifacts": artifacts,
        "html_report": html_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tape", type=Path, default=DEFAULT_TAPE, help="Path to input tape JSONL")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Target output audit directory")
    parser.add_argument("--threads", type=int, default=4, help="Worker threads")
    parser.add_argument("--verify-determinism", action="store_true", default=True,
                        help="Run an isolated second pass to verify bit-level determinism")
    args = parser.parse_args()

    tape = args.tape.resolve()
    out = args.out.resolve()

    if not tape.exists():
        print(f"Error: Tape file {tape} does not exist.")
        return 1

    print("=" * 70)
    print("V8.2 RUST AUDIT REPRODUCTION & DETERMINISM VERIFICATION")
    print("=" * 70)
    print(f"Target Tape: {tape}")
    print(f"Output Path: {out}")
    print(f"Worker Threads: {args.threads}")

    # 1. Compile Release Binary
    print("\n[1/4] Compiling release v8-core binary...")
    code, out_cargo, err_cargo = run_command(["cargo", "build", "--release"], cwd=ROOT / "v8-core")
    if code != 0:
        print(f"Cargo build failed:\n{err_cargo or out_cargo}")
        return 1
    binary = ROOT / "v8-core" / "target" / "release" / "v8-core"
    print(f"Binary verified: {binary}")

    # 2. Execute Primary Pipeline Pass
    print("\n[2/4] Executing primary audit pipeline...")
    pass1 = run_pipeline(binary, tape, out, threads=args.threads)
    n_evals = pass1["eval_meta"].get("n_evaluations", 0)
    speed = n_evals / max(pass1["eval_duration_sec"], 0.001)
    print(f"  -> Processed {n_evals:,} evaluations in {pass1['eval_duration_sec']:.2f}s ({speed:,.0f} evals/sec)")
    print(f"  -> Analysis completed in {pass1['ana_duration_sec']:.2f}s")
    print(f"  -> Generated HTML report: {pass1['html_report']}")

    # 3. Determinism Verification Pass (if enabled)
    if args.verify_determinism:
        print("\n[3/4] Running independent verification pass (Checking Zero-Jitter Bit-Identity)...")
        tmp_dir = ROOT / ".audit" / "rust_repro_verify_tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        try:
            pass2 = run_pipeline(binary, tape, tmp_dir, threads=args.threads)
            
            # Compare every artifact SHA-256
            mismatches = []
            for name, h1 in pass1["artifacts"].items():
                h2 = pass2["artifacts"].get(name)
                if h1 != h2:
                    mismatches.append((name, h1, h2))

            if mismatches:
                print("FATAL: Determinism violation detected!")
                for name, h1, h2 in mismatches:
                    print(f"  Mismatch in {name}:\n    Pass 1: {h1}\n    Pass 2: {h2}")
                return 1
            else:
                print("  ✓ 100% BIT-EXACT DETERMINISM VERIFIED across all generated ledgers.")
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    # 4. Print Cryptographic Certificate
    print("\n[4/4] Cryptographic Reproduction Certificate:")
    print("-" * 70)
    for name, digest in pass1["artifacts"].items():
        print(f"  {name:<28} SHA-256: {digest}")
    print("-" * 70)
    print(f"STATUS: REPRODUCED & CERTIFIED PASS (Total Time: {pass1['total_duration_sec']:.2f}s)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
