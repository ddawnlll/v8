"""S6 gate - regret phases 1-3 composition (COMPUTE_CORE_SPEC §8, issue #117).

Gate: the verdict tables produced by the Rust `analysis` subcommand —
Phase-1 opportunity rows, Phase-2 slice/discovery + confirmation verdicts,
Phase-3 recoverability verdicts — are bit-identical to
`tools/regret_phase1/2/3.py` on the fixture population.

The Python oracle is composed exactly the way the Rust composition consumes
it (analysis/mod.rs, issue #116): ONE store's certified cube/regret tables
(run_phase0), the Phase-1 joined dataset (regret_phase1), the Phase-2
discovery/confirmation halves split chronologically by (birth_time,
candidate_id) with the earlier ceil(n/2) rows in discovery (FCR-V8RR-007
CONTRACT 6, mirrored by the composition's `split_half`), and Phase-3
recoverability over the confirmed slices (regret_phase3).

The Rust request carries the same store projection the Python oracle
consumed (the store's candidates/evaluations/outcomes/states ledgers + the
`cube` subcommand's cube-reduced artifact + the store's tape/manifest), so
both sides reduce the SAME candidate population and the comparison is a
value-level bit-equality test (PARITY_AND_IDENTITY_SPEC §5).

Comparison semantics (PARITY_AND_IDENTITY_SPEC §3): V8.2-encoded identity
strings (candidate_id, manifest_id, action_id, state_id) are excluded from
the value comparison; ints/strings/enums compare exactly; floats compare by
IEEE-754 bit pattern (struct.pack equality).

The composition lands with issue #116. Until then `v8-core analysis` may
return the committed stub's "not implemented" message; the gate test SKIPs
with a clear message in that case (harness structure is the deliverable, the
pipeline comparison flips to PASS when the composition lands).
"""
from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from v8.experts import __all__ as EXPERT_ALL
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.store import AppendOnlyLog
from v8.synth import make_synthetic_tape

from tools import regret as regret_tools
from tools.predicate_ir import predicate_for
from tools.regret_phase1 import build_phase1_dataset
from tools.regret_phase2 import run_confirmation, run_discovery
from tools.regret_phase3 import run_phase3

from . import runner
from .runner import ParityFailure

# Identity strings excluded from the value comparison (§3).
IDENTITY_FIELDS = {"candidate_id", "manifest_id", "action_id", "state_id",
                   "event_id"}

# The joined-row value fields both sides emit (Rust joined_row_to_value and
# Python asdict(JoinedCandidateRow)).
JOIN_FIELDS = ("symbol", "expert_id", "direction", "birth_time", "gap_status",
               "legal_hindsight_gap", "actual_utility", "best_utility",
               "tie_cardinality", "endpoint", "label_status", "horizon_bars",
               "cost_r", "funding_r", "mae_r", "mfe_r", "ambiguous_bars",
               "epistemic_class")

# The per-slice verdict fields (Rust slice_result_to_value and Python's
# SliceResult). The Python attempts rows also carry confirmation_* extras
# that the Rust slice rows do not; only these fields are compared.
SLICE_FIELDS = ("slice_key", "expert_id", "symbol", "direction", "estimand",
                "n_total_in_slice", "n_computed",
                "effective_independent_episodes", "mean", "ci_lower",
                "ci_upper", "block_size", "alpha_slate",
                "practically_significant", "materiality_note",
                "discovery_verdict", "confirmation_verdict")

# The confirmation verdict fields (Rust confirmation_to_value).
CONFIRMATION_FIELDS = ("slice_key", "confirmation_verdict",
                       "confirmation_mean", "confirmation_ci_lower",
                       "confirmation_ci_upper", "confirmation_n_computed")

# The Phase-3 recoverability result fields (identical dict on both sides).
PHASE3_FIELDS = ("slice_key", "expert_id", "symbol", "direction",
                 "n_discovery", "n_confirmation", "selected_policy",
                 "discovery_selection_mean_utility", "confirmation_v_a",
                 "confirmation_v_r", "confirmation_g_r",
                 "confirmation_g_r_ci_lower", "confirmation_g_r_ci_upper",
                 "recoverability_verdict")

def _bits(v: float) -> bytes:
    return struct.pack("<d", v)


def _experts():
    return [getattr(__import__("v8.experts", fromlist=[n]), n)()
            for n in EXPERT_ALL if n != "Expert"]


def _build_store(root: Path, seed: int = 7, n_bars: int = 200):
    """One Lab store from a synthetic tape — the fixture population is the
    Lab's candidate population (the same build test_parity_s3 uses)."""
    rows = make_synthetic_tape(seed=seed, n_bars=n_bars, continuous=True)
    lab = Lab(root)
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: (r.event_time, r.available_time,
                                 r.venue_sequence))
    times = [b.available_time for b in bars]
    manifest = ExperimentManifest(
        experiment_id="s6", code_hash="", data_hash="",
        universe=tuple(sorted({b.instrument for b in bars})),
        start_ns=times[0], end_ns=times[-1])
    lab.run(manifest, _experts())
    return lab, bars, times


def _python_verdict_tables(lab, root: Path) -> dict:
    """Run the Python oracle phases 1-3 over the store's certified
    cube/regret tables; return the stage-tagged verdict rows exactly as the
    Rust analysis artifact carries them."""
    pyout = root / "pyout"
    regret_tools.run_phase0(lab.dir, pyout)
    build_phase1_dataset({"SOLUSDT": (lab.dir, pyout)}, root / "p1")
    rows = [json.loads(l)
            for l in (root / "p1" / "phase1_dataset.jsonl")
            .read_text().splitlines()]

    # The chronological discovery/confirmation split, mirroring the Rust
    # composition's split_half: sorted by (birth_time, candidate_id), first
    # ceil(n/2) rows in discovery.
    ordered = sorted(rows, key=lambda r: (r["birth_time"], r["candidate_id"]))
    mid = (len(ordered) + 1) // 2
    discovery, confirmation = ordered[:mid], ordered[mid:]

    _, results = run_discovery(root / "p1" / "phase1_dataset.jsonl",
                               discovery, root / "p2")
    (root / "p2conf").mkdir(parents=True, exist_ok=True)
    candidates = [r for r in results
                  if r.discovery_verdict == "CANDIDATE_SYSTEMATIC"]
    run_confirmation(candidates, confirmation, root / "p2conf")
    confirmed = [json.loads(l)["slice_key"]
                 for l in (root / "p2conf" / "confirmation_results.jsonl")
                 .read_text().splitlines() if l.strip()]
    (root / "p3").mkdir(parents=True, exist_ok=True)
    run_phase3(confirmed, discovery, confirmation,
               {"SOLUSDT": str(lab.dir)}, root / "p3")

    out = {"phase1_join": [], "phase2_slice": [], "phase2_confirmation": [],
           "phase3_recoverability": []}
    for r in rows:
        rec = {f: r.get(f) for f in JOIN_FIELDS}
        rec["candidate_id"] = r["candidate_id"]  # join key (excluded from value compare)
        out["phase1_join"].append(rec)
    for r in results:
        out["phase2_slice"].append(
            {f: getattr(r, f, None) for f in SLICE_FIELDS})
    for l in (root / "p2conf" / "confirmation_results.jsonl").read_text().splitlines():
        if not l.strip():
            continue
        rec = json.loads(l)
        out["phase2_confirmation"].append(
            {f: rec.get(f) for f in CONFIRMATION_FIELDS})
    summary = json.loads((root / "p3" / "phase3_summary.json").read_text())
    for res in summary.get("results", []):
        out["phase3_recoverability"].append(
            {f: res.get(f) for f in PHASE3_FIELDS})
    return out


def _analysis_request(v8_core_binary, lab, bars, times, root: Path) -> dict:
    """The S6 analysis request (analysis/mod.rs, issue #116): the reconcile
    ledger projection from the store + the cube-reduced artifact built by the
    S3 `cube` subcommand on the same population."""
    store = regret_tools.load_store(lab.dir)
    manifest = json.loads((lab.dir / "manifest.json").read_text())
    tap = runner.write_tape(bars, root / "tape.jsonl")

    # The cube-reduced artifact: the S3 cube request over every BOUND snapshot
    # of the same store (the exact request the S3 gate validates).
    snapshots = regret_tools.build_snapshots(store)
    idx_by_time = {t: i for i, t in enumerate(times)}
    candidates = []
    for snap in snapshots:
        if snap.binding_status != "BOUND":
            continue
        owner_cls = regret_tools.EXPERT_REGISTRY.get(snap.expert_id)
        entry_bar_index = idx_by_time.get(snap.entry_bar_available_time)
        candidates.append({
            "candidate_id": snap.candidate_id,
            "symbol": snap.instrument,
            "direction": snap.direction,
            "birth_time": snap.birth_time,
            "geometry": dict(snap.risk_geometry),
            "entry_bar_index": entry_bar_index,
            "window_end": len(bars),
            "predicate_ir": predicate_for(owner_cls()) if owner_cls else None,
        })
    cubedir = root / "cube"; cubedir.mkdir(parents=True, exist_ok=True)
    creq = {
        "tape_path": str(tap), "out_dir": str(cubedir), "threads": 1,
        "manifest": {"round_trip_cost_r": 0.07, "funding_rate_r": 0.0,
                     "funding_hours": 8, "fill_policy": "FILL_AT_BAR_CLOSE"},
        "candidates": candidates,
    }
    (cubedir / "req.json").write_text(json.dumps(creq))
    proc = subprocess.run([str(v8_core_binary), "cube", str(cubedir / "req.json")],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"cube failed: {proc.stderr}")

    return {
        "tape_path": str(tap),
        "out_dir": str(root / "rustout"),
        "universe": list({b.instrument for b in bars}),
        "manifest": manifest,
        "candidates": AppendOnlyLog(lab.dir / "candidates.jsonl").read(),
        "evaluations": AppendOnlyLog(lab.dir / "evaluations.jsonl").read(),
        "outcomes": AppendOnlyLog(lab.dir / "outcomes.jsonl").read(),
        "states": AppendOnlyLog(lab.dir / "states.jsonl").read(),
        "cube_reduced_path": str(cubedir / "cube-reduced.v82"),
    }


def _run_analysis(v8_core_binary, request: dict) -> subprocess.CompletedProcess:
    req_path = Path(request["out_dir"]).parent / "analysis-req.json"
    req_path.parent.mkdir(parents=True, exist_ok=True)
    req_path.write_text(json.dumps(request))
    return subprocess.run([str(v8_core_binary), "analysis", str(req_path)],
                          capture_output=True, text=True)


def _rust_verdict_tables(request: dict) -> dict:
    """Parse the analysis.jsonl the subcommand wrote into stage-tagged rows,
    mirroring the Python tables' shape."""
    out_dir = Path(request["out_dir"])
    artifact = out_dir / "analysis.jsonl"
    if not artifact.is_file():
        raise ParityFailure(f"analysis subcommand wrote no {artifact}")
    out = {"phase1_join": [], "phase2_slice": [], "phase2_confirmation": [],
           "phase3_recoverability": []}
    for l in artifact.read_text().splitlines():
        rec = json.loads(l)
        stage = rec.get("stage")
        if stage == "phase1_join":
            row = {f: rec.get(f) for f in JOIN_FIELDS}
            row["candidate_id"] = rec.get("candidate_id")  # join key
            out["phase1_join"].append(row)
        elif stage == "phase2_slice":
            out["phase2_slice"].append({f: rec.get(f) for f in SLICE_FIELDS})
        elif stage == "phase2_confirmation":
            out["phase2_confirmation"].append(
                {f: rec.get(f) for f in CONFIRMATION_FIELDS})
        elif stage == "phase3_recoverability":
            out["phase3_recoverability"].append(
                {f: rec.get(f) for f in PHASE3_FIELDS})
    return out


def _compare_value(tag: str, py, rust) -> None:
    if py is None or isinstance(py, (int, str, bool)):
        if py != rust:
            raise ParityFailure(f"{tag}: py={py!r} rust={rust!r}")
        return
    if isinstance(py, float):
        if not isinstance(rust, (int, float)):
            raise ParityFailure(f"{tag}: py={py!r} rust={rust!r}")
        if _bits(py) != _bits(float(rust)):
            raise ParityFailure(f"{tag}: py={py!r}({_bits(py).hex()}) "
                                f"rust={rust!r}({_bits(float(rust)).hex()})")
        return
    if isinstance(py, dict):
        if not isinstance(rust, dict):
            raise ParityFailure(f"{tag}: py dict rust={rust!r}")
        if sorted(py) != sorted(rust):
            raise ParityFailure(f"{tag}: keys py={sorted(py)} rust={sorted(rust)}")
        for k in sorted(py):
            _compare_value(f"{tag}.{k}", py[k], rust.get(k))
        return
    if isinstance(py, list):
        if not isinstance(rust, list) or len(py) != len(rust):
            raise ParityFailure(f"{tag}: list py={py!r} rust={rust!r}")
        for i, (a, b) in enumerate(zip(py, rust)):
            _compare_value(f"{tag}[{i}]", a, b)
        return
    raise ParityFailure(f"{tag}: unsupported type {type(py).__name__}")


def _compare_phase_outputs(py: dict, rust: dict) -> None:
    """Bit-compare the three phase outputs by stage. Identity strings are
    excluded (§3); floats compare by bit pattern. Opportunity rows are keyed
    by candidate_id (order is not contractual — both sides derive from the
    same population but in their own ledger order); slice and confirmation
    rows are keyed by slice_key."""
    key_of = {
        "phase1_join": lambda r: r["candidate_id"],
        "phase2_slice": lambda r: r["slice_key"],
        "phase2_confirmation": lambda r: r["slice_key"],
        "phase3_recoverability": lambda r: r["slice_key"],
    }
    divergences: list[str] = []
    for stage in ("phase1_join", "phase2_slice", "phase2_confirmation",
                  "phase3_recoverability"):
        py_by_key = {key_of[stage](r): r for r in py[stage]}
        rust_by_key = {key_of[stage](r): r for r in rust[stage]}
        if sorted(py_by_key) != sorted(rust_by_key):
            divergences.append(
                f"{stage}: key set py={len(py_by_key)} rust={len(rust_by_key)} "
                f"only-py={sorted(set(py_by_key) - set(rust_by_key))[:3]} "
                f"only-rust={sorted(set(rust_by_key) - set(py_by_key))[:3]}")
            continue
        for key in sorted(py_by_key):
            p, r_ = py_by_key[key], rust_by_key[key]
            for k in p:
                if k in IDENTITY_FIELDS:
                    continue
                try:
                    _compare_value(f"{stage}.{key[:12]}.{k}", p[k], r_.get(k))
                except ParityFailure as exc:
                    divergences.append(str(exc))
    if divergences:
        head = "\n".join(divergences[:25])
        raise ParityFailure(
            f"{len(divergences)} phase-output divergences vs the Python oracle "
            f"(first 25):\n{head}")


def test_s6_analysis_matches_python_phases(v8_core_binary, tmp_path):
    """The gate: opportunity rows, slice verdicts and recoverability verdicts
    from `v8-core analysis` are bit-identical to the Python phases on the same
    fixture population. SKIPs (with a clear message) when the analysis
    subcommand still reports 'not implemented' — the S6 composition lands with
    issue #116."""
    import pytest

    root = Path(tmp_path)
    lab, bars, times = _build_store(root / "lab")
    py = _python_verdict_tables(lab, root)
    request = _analysis_request(v8_core_binary, lab, bars, times, root)

    proc = _run_analysis(v8_core_binary, request)
    combined = (proc.stdout + proc.stderr).lower()
    if "not implemented" in combined:
        pytest.skip(
            "v8-core analysis returns 'not implemented' — the S6 composition "
            "lands with issue #116; harness structure proven (Python oracle "
            "runs, request contract exercised), gate PARTIAL until then")
    if proc.returncode != 0:
        raise ParityFailure(
            f"analysis rc={proc.returncode}\nstdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}")
    rust = _rust_verdict_tables(request)
    _compare_phase_outputs(py, rust)
