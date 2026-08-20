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

    # 3. Run v8-core Target Oracle (O0-O3) representational coverage & evidence bundle
    t2 = time.perf_counter()
    grammar_candidates = []
    seen = set()
    cands_file = out_dir / "candidates.jsonl"
    if cands_file.exists():
        with cands_file.open("r", encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                if c.get("to_state") == "DETECTED":
                    cid = c.get("candidate_id")
                    if cid and cid not in seen:
                        seen.add(cid)
                        params = {}
                        geom = c.get("risk_geometry") or {}
                        for k, v in geom.items():
                            if isinstance(v, (int, float, bool, str)):
                                params[k] = v
                        expert_id = c.get("expert_id", "generic")
                        grammar_candidates.append({
                            "grammar_candidate_id": f"gc-{cid[:16]}",
                            "universe_id": "universe-btcusdt-1h-v1",
                            "template_id": f"template-{expert_id}",
                            "instrument": c.get("instrument", "BTCUSDT"),
                            "timeframe": "1h",
                            "direction": "Long" if c.get("direction") == "LONG" else "Short",
                            "decision_time": c.get("knowledge_time", 0) // 1_000_000,
                            "parameters": params,
                        })

    oracle_bundle_dir = out_dir / "oracle_bundle"
    oracle_req = {
        "universe": {
            "universe_id": "universe-btcusdt-1h-v1",
            "version": "1",
            "parent_universe_id": None,
            "instrument_universe": ["BTCUSDT"],
            "timeframe_set": ["1h"],
            "information_contract_id": "pit-feature-v1",
            "primitive_registry_hash": "prim-reg-v1-sha1-7a8f9b",
            "predicate_ir_version": "predicate-ir-v1",
            "behavior_template_registry_hash": "templ-reg-v1-sha1-3b4c5d",
            "parameter_grid_hash": "grid-v1-sha1-1e2f3a",
            "tradability_rule_id": "tradability-d024-v1",
            "support_rule_id": "canonical-l1-support-v1",
            "authority_contract_id": "l1-authority-v1",
            "search_universe_size": len(grammar_candidates),
            "complexity_budget": 28,
            "created_at": 1751400000,
            "code_hash": "code-v8core-v0.2.0",
            "execution_mode_id": "canonical-l1",
        },
        "candidates": grammar_candidates,
        "utility_contract_id": "after-cost-net-utility-v1",
        "lineage_id": "lineage-btcusdt-1h-audit-2026",
        "requested_authority": "L1",
        "out_dir": str(oracle_bundle_dir.resolve()),
    }
    oracle_req_path = out_dir / "request_oracle_coverage.json"
    oracle_req_path.write_text(json.dumps(oracle_req, indent=2), encoding="utf-8")

    code, out_oracle, err_oracle = run_command([str(binary), "oracle-coverage", str(oracle_req_path)])
    oracle_duration = time.perf_counter() - t2
    if code != 0:
        raise RuntimeError(f"v8-core oracle-coverage failed:\nSTDOUT: {out_oracle}\nSTDERR: {err_oracle}")
    
    oracle_receipt_path = out_dir / "oracle_coverage_receipt.json"
    oracle_meta = json.loads(out_oracle)
    oracle_receipt_path.write_text(json.dumps(oracle_meta, indent=2), encoding="utf-8")

    # 4. Run v8-core usdm-sim Capital-Constrained Portfolio Simulation (Issue #164)
    t3 = time.perf_counter()
    code, out_usdm, err_usdm = run_command([
        str(binary), "usdm-sim",
        "--tape", str(tape_path.resolve()),
        "--out", str(out_dir.resolve()),
        "--initial-balance", "1000.0",
        "--risk-fraction", "0.005",
        "--leverage", "10",
    ])
    usdm_duration = time.perf_counter() - t3
    if code != 0:
        raise RuntimeError(f"v8-core usdm-sim failed:\nSTDOUT: {out_usdm}\nSTDERR: {err_usdm}")
    usdm_meta = json.loads(out_usdm)

    # 5. Render HTML Report
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
        "oracle_coverage_receipt.json": sha256_file(out_dir / "oracle_coverage_receipt.json"),
        "portfolio_receipt.json": sha256_file(out_dir / "portfolio_receipt.json"),
        "economic-cashflow.jsonl": sha256_file(out_dir / "economic-cashflow.jsonl"),
    }
    if (out_dir / "oracle_bundle" / "authority_surface.parquet").exists():
        artifacts["oracle_bundle/authority_surface.parquet"] = sha256_file(out_dir / "oracle_bundle" / "authority_surface.parquet")
    if (out_dir / "oracle_bundle" / "unknown_reasons.json").exists():
        artifacts["oracle_bundle/unknown_reasons.json"] = sha256_file(out_dir / "oracle_bundle" / "unknown_reasons.json")
    if (out_dir / "oracle_bundle" / "power_materiality.json").exists():
        artifacts["oracle_bundle/power_materiality.json"] = sha256_file(out_dir / "oracle_bundle" / "power_materiality.json")

    return {
        "eval_duration_sec": eval_duration,
        "ana_duration_sec": ana_duration,
        "oracle_duration_sec": oracle_duration,
        "usdm_duration_sec": usdm_duration,
        "total_duration_sec": eval_duration + ana_duration + oracle_duration + usdm_duration,
        "eval_meta": eval_meta,
        "ana_meta": ana_meta,
        "oracle_meta": oracle_meta,
        "usdm_meta": usdm_meta,
        "artifacts": artifacts,
        "html_report": html_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tape", type=Path, default=DEFAULT_TAPE, help="Path to input tape JSONL")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Target output audit directory")
    parser.add_argument("--threads", type=int, default=4, help="Worker threads")
    parser.add_argument("--binary", type=Path, default=None, help="Explicit path to v8-core binary")
    parser.add_argument("--skip-build", action="store_true", help="Skip release compilation if binary exists")
    parser.add_argument("--verify-determinism", action="store_true", default=True,
                        help="Run an isolated second pass to verify bit-level determinism")
    args = parser.parse_args()

    tape = args.tape.resolve()
    out = args.out.resolve()

    if not tape.exists():
        print(f"Error: Tape file {tape} does not exist.")
        return 1

    print("=" * 70)
    print("V8.2 RUST AUDIT REPRODUCTION & TARGET ORACLE EVIDENCE VERIFICATION")
    print("=" * 70)
    print(f"Target Tape: {tape}")
    print(f"Output Path: {out}")
    print(f"Worker Threads: {args.threads}")

    # 1. Compile Release Binary or Locate
    binary = args.binary
    if not binary:
        binary = ROOT / "v8-core" / "target" / "release" / "v8-core"
        if sys.platform == "win32":
            binary = binary.with_suffix(".exe")

    if not args.skip_build:
        print("\n[1/4] Compiling release v8-core binary...")
        cargo_bin = shutil.which("cargo")
        if not cargo_bin and sys.platform == "win32":
            default_cargo = Path(os.environ.get("USERPROFILE", "")) / ".cargo" / "bin" / "cargo.exe"
            if default_cargo.exists():
                cargo_bin = str(default_cargo)
        cargo_cmd = [cargo_bin or "cargo", "build", "--release"]
        code, out_cargo, err_cargo = run_command(cargo_cmd, cwd=ROOT / "v8-core")
        if code != 0:
            print(f"Cargo build failed:\n{err_cargo or out_cargo}")
            return 1
        if not binary.exists() and binary.with_suffix(".exe").exists():
            binary = binary.with_suffix(".exe")
    else:
        print("\n[1/4] Using pre-compiled release v8-core binary...")

    print(f"Binary verified: {binary}")

    # 2. Execute Primary Pipeline Pass
    print("\n[2/4] Executing primary audit & oracle pipeline...")
    pass1 = run_pipeline(binary, tape, out, threads=args.threads)
    n_evals = pass1["eval_meta"].get("n_evaluations", 0)
    speed = n_evals / max(pass1["eval_duration_sec"], 0.001)
    print(f"  -> Processed {n_evals:,} evaluations in {pass1['eval_duration_sec']:.2f}s ({speed:,.0f} evals/sec)")
    print(f"  -> Regret Analysis completed in {pass1['ana_duration_sec']:.2f}s")
    print(f"  -> Target Oracle Coverage completed in {pass1['oracle_duration_sec']:.2f}s (Receipt: {pass1['oracle_meta'].get('receipt_id')})")
    print(f"  -> USD-M Capital Simulation completed in {pass1['usdm_duration_sec']:.2f}s (Trades Admitted: {pass1['usdm_meta'].get('n_trades_admitted')})")
    print(f"  -> Generated HTML report: {pass1['html_report']}")

    # 3. Determinism Verification Pass (if enabled)
    if args.verify_determinism:
        print("\n[3/4] Running independent verification pass (Checking Zero-Jitter Bit-Identity across S0-S7 & Oracle)...")
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
                print("  [OK] 100% BIT-EXACT DETERMINISM VERIFIED across all generated ledgers and Oracle receipts.")
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    # 4. Print Cryptographic Certificate
    print("\n[4/4] Cryptographic Reproduction Certificate:")
    print("-" * 70)
    for name, digest in pass1["artifacts"].items():
        print(f"  {name:<30} SHA-256: {digest}")
    print("-" * 70)
    print(f"STATUS: REPRODUCED & CERTIFIED PASS (Total Time: {pass1['total_duration_sec']:.2f}s)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
