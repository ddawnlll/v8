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


def safe_rmtree(path: Path, max_retries: int = 5, delay: float = 0.2) -> None:
    if not path.exists():
        return
    for i in range(max_retries):
        try:
            shutil.rmtree(path)
            return
        except Exception:
            if i == max_retries - 1:
                shutil.rmtree(path, ignore_errors=True)
            else:
                time.sleep(delay)


def run_pipeline(binary: Path, tape_path: Path, out_dir: Path, threads: int = 4, render_html: bool = True, verbose: bool = True) -> dict:
    safe_rmtree(out_dir)
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
    if verbose:
        print(f"  -> [1/5] Running S4 evaluate loop ({threads} threads)...", end="", flush=True)
    t0 = time.perf_counter()
    code, out_eval, err_eval = run_command([str(binary), "evaluate", str(req_path)])
    eval_duration = time.perf_counter() - t0
    if code != 0:
        if verbose:
            print(" FAILED")
        raise RuntimeError(f"v8-core evaluate failed:\nSTDOUT: {out_eval}\nSTDERR: {err_eval}")
    eval_meta = json.loads(out_eval)
    n_evals = eval_meta.get("n_evaluations", 0)
    speed = n_evals / max(eval_duration, 0.001)
    if verbose:
        print(f" DONE ({n_evals:,} evals in {eval_duration:.2f}s, {speed:,.0f} evals/sec)")

    # 2. Run v8-core analysis
    if verbose:
        print("  -> [2/5] Running S6 regret analysis...", end="", flush=True)
    t1 = time.perf_counter()
    code, out_ana, err_ana = run_command([str(binary), "analysis", str(req_path)])
    ana_duration = time.perf_counter() - t1
    if code != 0:
        if verbose:
            print(" FAILED")
        raise RuntimeError(f"v8-core analysis failed:\nSTDOUT: {out_ana}\nSTDERR: {err_ana}")
    ana_meta = json.loads(out_ana)
    if verbose:
        print(f" DONE ({ana_duration:.2f}s)")

    # 3. Run v8-core Target Oracle (O0-O3) representational coverage & evidence bundle
    if verbose:
        print("  -> [3/5] Running Target Oracle (O0-O3) coverage...", end="", flush=True)
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
        if verbose:
            print(" FAILED")
        raise RuntimeError(f"v8-core oracle-coverage failed:\nSTDOUT: {out_oracle}\nSTDERR: {err_oracle}")
    
    oracle_receipt_path = out_dir / "oracle_coverage_receipt.json"
    oracle_meta = json.loads(out_oracle)
    oracle_receipt_path.write_text(json.dumps(oracle_meta, indent=2), encoding="utf-8")
    if verbose:
        print(f" DONE ({oracle_duration:.2f}s, Receipt: {oracle_meta.get('receipt_id', '')[:16]}...)")

    # 4. Run v8-core usdm-sim Capital-Constrained Portfolio Simulation (Issue #164)
    if verbose:
        print("  -> [4/5] Running USD-M Capital Simulation & Allegory Suite...", end="", flush=True)
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
        if verbose:
            print(" FAILED")
        raise RuntimeError(f"v8-core usdm-sim failed:\nSTDOUT: {out_usdm}\nSTDERR: {err_usdm}")
    usdm_meta = json.loads(out_usdm)

    # 4b. Run v8-core allegory-audit Historical Market Archetype Suite (D-125 / ALLEGORY-001)
    allegory_out = out_dir / "allegory_scorecard.json"
    code, out_allegory, err_allegory = run_command([
        str(binary), "allegory-audit",
        "--tape", str(tape_path.resolve()),
        "--out", str(allegory_out.resolve()),
    ])
    if code != 0:
        if verbose:
            print(" FAILED")
        raise RuntimeError(f"v8-core allegory-audit failed:\nSTDOUT: {out_allegory}\nSTDERR: {err_allegory}")
    if verbose:
        print(f" DONE ({usdm_duration:.2f}s, Admitted: {usdm_meta.get('n_trades_admitted')})")

    # 5. Render HTML Report
    html_out = out_dir / "report.html"
    if render_html:
        if verbose:
            print("  -> [5/5] Rendering deep-forensic HTML audit report...", end="", flush=True)
        t4 = time.perf_counter()
        render_script = ROOT / "tools" / "render_rust_audit_html.py"
        code, out_rend, err_rend = run_command([sys.executable, str(render_script), "--audit-dir", str(out_dir), "--out", str(html_out)])
        rend_duration = time.perf_counter() - t4
        if code != 0:
            if verbose:
                print(" FAILED")
            raise RuntimeError(f"render_rust_audit_html failed:\n{err_rend or out_rend}")
        if verbose:
            print(f" DONE ({rend_duration:.2f}s)")

    # Compute Artifact Fingerprints
    artifacts = {
        "candidates.jsonl": sha256_file(out_dir / "candidates.jsonl"),
        "candidate-transitions.jsonl": sha256_file(out_dir / "candidate-transitions.jsonl"),
        "evaluations.jsonl": sha256_file(out_dir / "evaluations.jsonl"),
        "cube-reduced.v82": sha256_file(out_dir / "cube-reduced.v82"),
        "analysis.jsonl": sha256_file(out_dir / "analysis.jsonl"),
        "oracle_coverage_receipt.json": sha256_file(out_dir / "oracle_coverage_receipt.json"),
        "portfolio_receipt.json": sha256_file(out_dir / "portfolio_receipt.json"),
        "allegory_scorecard.json": sha256_file(out_dir / "allegory_scorecard.json"),
        "economic-cashflow.jsonl": sha256_file(out_dir / "economic-cashflow.jsonl"),
    }
    if (out_dir / "oracle_bundle" / "authority_surface.parquet").exists():
        artifacts["oracle_bundle/authority_surface.parquet"] = sha256_file(out_dir / "oracle_bundle" / "authority_surface.parquet")
    if (out_dir / "oracle_bundle" / "unknown_reasons.json").exists():
        artifacts["oracle_bundle/unknown_reasons.json"] = sha256_file(out_dir / "oracle_bundle" / "unknown_reasons.json")
    if (out_dir / "oracle_bundle" / "power_materiality.json").exists():
        artifacts["oracle_bundle/power_materiality.json"] = sha256_file(out_dir / "oracle_bundle" / "power_materiality.json")
    if (out_dir / "oracle_bundle" / "population_lineage.jsonl").exists():
        artifacts["oracle_bundle/population_lineage.jsonl"] = sha256_file(out_dir / "oracle_bundle" / "population_lineage.jsonl")
    if (out_dir / "oracle_bundle" / "cohort_manifest.json").exists():
        artifacts["oracle_bundle/cohort_manifest.json"] = sha256_file(out_dir / "oracle_bundle" / "cohort_manifest.json")
    if (out_dir / "oracle_bundle" / "report_reconciliation.json").exists():
        artifacts["oracle_bundle/report_reconciliation.json"] = sha256_file(out_dir / "oracle_bundle" / "report_reconciliation.json")
    if (out_dir / "oracle_bundle" / "report_cell_provenance.parquet").exists():
        artifacts["oracle_bundle/report_cell_provenance.parquet"] = sha256_file(out_dir / "oracle_bundle" / "report_cell_provenance.parquet")
    if (out_dir / "oracle_bundle" / "oracle_independence_receipt.json").exists():
        artifacts["oracle_bundle/oracle_independence_receipt.json"] = sha256_file(out_dir / "oracle_bundle" / "oracle_independence_receipt.json")
    if (out_dir / "oracle_bundle" / "negative_control_universe.parquet").exists():
        artifacts["oracle_bundle/negative_control_universe.parquet"] = sha256_file(out_dir / "oracle_bundle" / "negative_control_universe.parquet")
    if (out_dir / "temporal_noninterference_receipt.json").exists():
        artifacts["temporal_noninterference_receipt.json"] = sha256_file(out_dir / "temporal_noninterference_receipt.json")
    if (out_dir / "oracle_bundle" / "temporal_noninterference_receipt.json").exists():
        artifacts["oracle_bundle/temporal_noninterference_receipt.json"] = sha256_file(out_dir / "oracle_bundle" / "temporal_noninterference_receipt.json")
    if (out_dir / "implementation_risk.json").exists():
        artifacts["implementation_risk.json"] = sha256_file(out_dir / "implementation_risk.json")
    if (out_dir / "differential_economic_ledger.jsonl").exists():
        artifacts["differential_economic_ledger.jsonl"] = sha256_file(out_dir / "differential_economic_ledger.jsonl")
    if (out_dir / "multiple_testing.json").exists():
        artifacts["multiple_testing.json"] = sha256_file(out_dir / "multiple_testing.json")
    if (out_dir / "research_family_ledger.jsonl").exists():
        artifacts["research_family_ledger.jsonl"] = sha256_file(out_dir / "research_family_ledger.jsonl")
    if (out_dir / "oracle_bundle" / "multiple_testing.json").exists():
        artifacts["oracle_bundle/multiple_testing.json"] = sha256_file(out_dir / "oracle_bundle" / "multiple_testing.json")
    if (out_dir / "oracle_bundle" / "research_family_ledger.jsonl").exists():
        artifacts["oracle_bundle/research_family_ledger.jsonl"] = sha256_file(out_dir / "oracle_bundle" / "research_family_ledger.jsonl")
    if (out_dir / "null_world_falsification.json").exists():
        artifacts["null_world_falsification.json"] = sha256_file(out_dir / "null_world_falsification.json")
    if (out_dir / "oracle_bundle" / "null_world_falsification.json").exists():
        artifacts["oracle_bundle/null_world_falsification.json"] = sha256_file(out_dir / "oracle_bundle" / "null_world_falsification.json")
    if (out_dir / "oracle_bundle" / "o4_regret_decomposition.parquet").exists():
        artifacts["oracle_bundle/o4_regret_decomposition.parquet"] = sha256_file(out_dir / "oracle_bundle" / "o4_regret_decomposition.parquet")
    if (out_dir / "oracle_bundle" / "regret_assumption_ledger.json").exists():
        artifacts["oracle_bundle/regret_assumption_ledger.json"] = sha256_file(out_dir / "oracle_bundle" / "regret_assumption_ledger.json")
    if (out_dir / "oracle_bundle" / "veto_attribution.parquet").exists():
        artifacts["oracle_bundle/veto_attribution.parquet"] = sha256_file(out_dir / "oracle_bundle" / "veto_attribution.parquet")
    if (out_dir / "oracle_bundle" / "veto_attribution_summary.json").exists():
        artifacts["oracle_bundle/veto_attribution_summary.json"] = sha256_file(out_dir / "oracle_bundle" / "veto_attribution_summary.json")
    if (out_dir / "oracle_bundle" / "dedup_regret.json").exists():
        artifacts["oracle_bundle/dedup_regret.json"] = sha256_file(out_dir / "oracle_bundle" / "dedup_regret.json")
    if (out_dir / "oracle_bundle" / "scheduler_rename_sensitivity.json").exists():
        artifacts["oracle_bundle/scheduler_rename_sensitivity.json"] = sha256_file(out_dir / "oracle_bundle" / "scheduler_rename_sensitivity.json")
    if (out_dir / "oracle_bundle" / "expert_joint_regime.parquet").exists():
        artifacts["oracle_bundle/expert_joint_regime.parquet"] = sha256_file(out_dir / "oracle_bundle" / "expert_joint_regime.parquet")
    if (out_dir / "oracle_bundle" / "regime_interactions.json").exists():
        artifacts["oracle_bundle/regime_interactions.json"] = sha256_file(out_dir / "oracle_bundle" / "regime_interactions.json")
    if (out_dir / "oracle_bundle" / "funding_clock.parquet").exists():
        artifacts["oracle_bundle/funding_clock.parquet"] = sha256_file(out_dir / "oracle_bundle" / "funding_clock.parquet")
    if (out_dir / "oracle_bundle" / "drift_monitor.jsonl").exists():
        artifacts["oracle_bundle/drift_monitor.jsonl"] = sha256_file(out_dir / "oracle_bundle" / "drift_monitor.jsonl")
    if (out_dir / "oracle_bundle" / "capital_viability_surface.parquet").exists():
        artifacts["oracle_bundle/capital_viability_surface.parquet"] = sha256_file(out_dir / "oracle_bundle" / "capital_viability_surface.parquet")
    if (out_dir / "oracle_bundle" / "capital_viability_meta.json").exists():
        artifacts["oracle_bundle/capital_viability_meta.json"] = sha256_file(out_dir / "oracle_bundle" / "capital_viability_meta.json")
    if (out_dir / "oracle_bundle" / "path_to_ruin.json").exists():
        artifacts["oracle_bundle/path_to_ruin.json"] = sha256_file(out_dir / "oracle_bundle" / "path_to_ruin.json")
    if (out_dir / "oracle_bundle" / "maker_identifiability_receipt.json").exists():
        artifacts["oracle_bundle/maker_identifiability_receipt.json"] = sha256_file(out_dir / "oracle_bundle" / "maker_identifiability_receipt.json")
    if (out_dir / "oracle_bundle" / "markouts.parquet").exists():
        artifacts["oracle_bundle/markouts.parquet"] = sha256_file(out_dir / "oracle_bundle" / "markouts.parquet")
    if (out_dir / "oracle_bundle" / "scenario_ruin_distribution.parquet").exists():
        artifacts["oracle_bundle/scenario_ruin_distribution.parquet"] = sha256_file(out_dir / "oracle_bundle" / "scenario_ruin_distribution.parquet")
    if (out_dir / "oracle_bundle" / "scenario_ruin_meta.json").exists():
        artifacts["oracle_bundle/scenario_ruin_meta.json"] = sha256_file(out_dir / "oracle_bundle" / "scenario_ruin_meta.json")
    if (out_dir / "oracle_bundle" / "slippage_at_risk.json").exists():
        artifacts["oracle_bundle/slippage_at_risk.json"] = sha256_file(out_dir / "oracle_bundle" / "slippage_at_risk.json")
    if (out_dir / "oracle_bundle" / "recoverability_chain.parquet").exists():
        artifacts["oracle_bundle/recoverability_chain.parquet"] = sha256_file(out_dir / "oracle_bundle" / "recoverability_chain.parquet")
    if (out_dir / "oracle_bundle" / "recoverable_gap_waterfall.json").exists():
        artifacts["oracle_bundle/recoverable_gap_waterfall.json"] = sha256_file(out_dir / "oracle_bundle" / "recoverable_gap_waterfall.json")

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
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 4, help="Worker threads")
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
    print(f"Target Tape:    {tape}")
    print(f"Output Path:    {out}")
    print(f"Worker Threads: {args.threads}")

    # 1. Compile Release Binary or Locate
    binary = args.binary
    if not binary:
        binary = ROOT / "v8-core" / "target" / "release" / "v8-core"
        if sys.platform == "win32":
            binary = binary.with_suffix(".exe")

    if not args.skip_build:
        print("\n[1/4] Compiling release v8-core binary...", end="", flush=True)
        cargo_bin = shutil.which("cargo")
        if not cargo_bin and sys.platform == "win32":
            default_cargo = Path(os.environ.get("USERPROFILE", "")) / ".cargo" / "bin" / "cargo.exe"
            if default_cargo.exists():
                cargo_bin = str(default_cargo)
        cargo_cmd = [cargo_bin or "cargo", "build", "--release"]
        t_build = time.perf_counter()
        code, out_cargo, err_cargo = run_command(cargo_cmd, cwd=ROOT / "v8-core")
        build_dur = time.perf_counter() - t_build
        if code != 0:
            print(" FAILED")
            print(f"Cargo build failed:\n{err_cargo or out_cargo}")
            return 1
        print(f" DONE ({build_dur:.2f}s)")
        if not binary.exists() and binary.with_suffix(".exe").exists():
            binary = binary.with_suffix(".exe")
    else:
        print("\n[1/4] Using pre-compiled release v8-core binary...")

    print(f"Binary verified: {binary}")

    # 2. Execute Primary Pipeline Pass
    print("\n[2/4] Executing primary audit & oracle pipeline...")
    pass1 = run_pipeline(binary, tape, out, threads=args.threads, render_html=True, verbose=True)
    print(f"  -> Pipeline Pass 1 complete in {pass1['total_duration_sec']:.2f}s")
    print(f"  -> Generated HTML report: {pass1['html_report']}")

    # 3. Determinism Verification Pass (if enabled)
    if args.verify_determinism:
        print("\n[3/4] Running independent verification pass (Zero-Jitter Bit-Identity Check)...", flush=True)
        tmp_dir = ROOT / ".audit" / "rust_repro_verify_tmp"
        safe_rmtree(tmp_dir)
        try:
            pass2 = run_pipeline(binary, tape, tmp_dir, threads=args.threads, render_html=False, verbose=False)
            
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
            safe_rmtree(tmp_dir)

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
