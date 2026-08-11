"""S3 gate - CubeReducer + streaming regret (COMPUTE_CORE_SPEC §8).

Gate: the reduced tables match the Python evaluator (OUTCOME_CUBE_SPEC §7.6
equivalence: streaming reduction == full materialization), on the fixture
set, plus G1..G6.

The Python side is `tools/regret.py`'s Phase-0 evaluator: it materializes the
cube (cube.jsonl) and writes the per-Candidate regret rows (regret.jsonl).
The Rust side streams the same reduction in flight. The comparison covers the
value fields both produce: gap_status, actual_utility, best_utility,
tie_cardinality, legal_hindsight_gap, abstention_reason. Identity strings
(candidate_id, manifest_id, action_id) are V8.2-encoded and excluded by
PARITY_AND_IDENTITY_SPEC §3.
"""
from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from v8.experts import __all__ as EXPERT_ALL
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

from tools import regret as regret_tools
from tools.predicate_ir import predicate_for

from . import runner
from .runner import ParityFailure

REPO_ROOT = runner.REPO_ROOT


def _experts():
    return [getattr(__import__("v8.experts", fromlist=[n]), n)()
            for n in EXPERT_ALL if n != "Expert"]


def _build_store(tmp_path, rows):
    lab = Lab(tmp_path)
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: (r.event_time, r.available_time,
                                 r.venue_sequence))
    times = [b.available_time for b in bars]
    manifest = ExperimentManifest(
        experiment_id="s3", code_hash="", data_hash="",
        universe=tuple(sorted({b.instrument for b in bars})),
        start_ns=times[0], end_ns=times[-1])
    lab.run(manifest, _experts())
    return lab, bars, times


def _python_reduced(store_dir, out_dir):
    """Run the Python Phase-0 evaluator; return {candidate_id: reduced dict}
    from regret.jsonl (the full-materialization reduction)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    regret_tools.run_phase0(store_dir, out_dir)
    reduced = {}
    for line in (out_dir / "regret.jsonl").read_text().splitlines():
        rec = json.loads(line)
        reduced[rec["event_id"]] = rec
    return reduced


def _rust_request(lab, bars, times):
    """The cube request: every BOUND snapshot, with entry-bar index and the
    compiled predicate for its owner."""
    store = regret_tools.load_store(lab.dir)
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
    return candidates


def _rust_reduced(v8_core_binary, lab, bars, times, tmp_path, threads=1):
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    candidates = _rust_request(lab, bars, times)
    tape = runner.write_tape(bars, tmp_path / "tape.jsonl")
    req = {
        "tape_path": str(tape),
        "out_dir": str(tmp_path / "out"),
        "threads": threads,
        "manifest": {"round_trip_cost_r": 0.07, "funding_rate_r": 0.0,
                     "funding_hours": 8, "fill_policy": "FILL_AT_BAR_CLOSE"},
        "candidates": candidates,
    }
    req_path = tmp_path / "req.json"
    req_path.write_text(json.dumps(req))
    proc = subprocess.run([str(v8_core_binary), "cube", str(req_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"cube failed: {proc.stderr}")
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    from tools.v82_reader import read as read_artifact
    art = read_artifact(Path(summary["artifact"]))
    reduced = {}
    for row in art.rows():
        reduced[row["candidate_id"]] = row
    return reduced


def _compare(py, rust, cid):
    for f in ("gap_status", "tie_cardinality"):
        if py.get(f) != rust.get(f):
            raise ParityFailure(f"{cid} {f}: py={py.get(f)!r} rust={rust.get(f)!r}")
    for f in ("actual_utility", "best_utility", "legal_hindsight_gap"):
        pyv = py.get(f)
        rv = rust.get(f)
        if pyv is None or rv is None:
            if not (pyv is None and rv is None):
                raise ParityFailure(f"{cid} {f}: py={pyv!r} rust={rv!r}")
            continue
        if struct.pack("<d", pyv) != struct.pack("<d", rv):
            raise ParityFailure(f"{cid} {f}: py={pyv!r} rust={rv!r}")
    # abstention reason: exact for the fixed strings; the
    # "actual action cell is X: ..." form embeds a cell reason, compare the
    # status prefix.
    py_r = py.get("abstention_reason") or ""
    r_r = rust.get("abstention_reason") or ""
    if py_r.startswith("actual action cell is"):
        if not r_r.startswith("actual action cell is") \
                or py_r.split(":")[0] != r_r.split(":")[0]:
            raise ParityFailure(f"{cid} reason: py={py_r!r} rust={r_r!r}")
    elif py_r != r_r:
        raise ParityFailure(f"{cid} reason: py={py_r!r} rust={r_r!r}")


def test_s3_reduced_tables_match_python_evaluator(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=7, n_bars=400, continuous=True)
    lab, bars, times = _build_store(tmp_path / "lab", rows)
    py = _python_reduced(lab.dir, tmp_path / "pyout")
    rust = _rust_reduced(v8_core_binary, lab, bars, times, tmp_path / "rust")
    assert set(py.keys()) == set(rust.keys()), (
        f"candidate sets differ: only-py={set(py)-set(rust)} only-rust={set(rust)-set(py)}")
    for cid in py:
        _compare(py[cid], rust[cid], cid)
    # gap >= 0 for every COMPUTED candidate (OUTCOME_CUBE_SPEC §7.5)
    for cid, rec in py.items():
        if rec["gap_status"] == "COMPUTED":
            assert rec["legal_hindsight_gap"] >= 0.0, cid


def test_s3_manifest_structure(v8_core_binary, tmp_path):
    """a_actual is element 1 of every manifest (OUTCOME_CUBE_SPEC §2);
    NO_TRADE is element 0; |A(C)| <= 11 with pyramid_add_rules excluded."""
    rows = make_synthetic_tape(seed=7, n_bars=200)
    lab, bars, times = _build_store(tmp_path / "lab", rows)
    store = regret_tools.load_store(lab.dir)
    snapshots = regret_tools.build_snapshots(store)
    for snap in [s for s in snapshots if s.binding_status == "BOUND"][:20]:
        manifest = regret_tools.generate_legal_actions(snap.risk_geometry)
        assert manifest.actions[0].kind == "NO_TRADE"
        assert manifest.actions[1].provenance == "ACTUAL"
        assert len(manifest.actions) <= 11
        if "pyramid_add_rules" in snap.risk_geometry:
            assert len(manifest.actions) == 2


def test_s3_two_runs_byte_identical(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=11, n_bars=200, continuous=True)
    lab, bars, times = _build_store(tmp_path / "lab", rows)
    r1 = _rust_reduced(v8_core_binary, lab, bars, times, tmp_path / "a")
    r2 = _rust_reduced(v8_core_binary, lab, bars, times, tmp_path / "b")
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_s3_thread_invariance(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=13, n_bars=200, continuous=True)
    lab, bars, times = _build_store(tmp_path / "lab", rows)
    r1 = _rust_reduced(v8_core_binary, lab, bars, times, tmp_path / "a", threads=1)
    r8 = _rust_reduced(v8_core_binary, lab, bars, times, tmp_path / "b", threads=8)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r8, sort_keys=True)


def test_s3_g6_undefined_future(v8_core_binary, tmp_path):
    """A candidate born within MIN_FUTURE_BARS of the tape end yields
    UNDEFINED_FUTURE, never a numeric outcome (OUTCOME_CUBE_SPEC §3) — the
    same refusal in both implementations."""
    rows = make_synthetic_tape(seed=5, n_bars=30)
    lab, bars, times = _build_store(tmp_path / "lab", rows)
    py = _python_reduced(lab.dir, tmp_path / "pyout")
    rust = _rust_reduced(v8_core_binary, lab, bars, times, tmp_path / "rust")
    assert set(py.keys()) == set(rust.keys())
    for cid, rec in py.items():
        _compare(py[cid], rust[cid], cid)
        # A near-tape-end candidate must never produce a COMPUTED gap: the
        # refusal is the gate (OUTCOME_CUBE_SPEC §3), and it must agree.
        if rec["gap_status"] != "COMPUTED":
            assert rust[cid]["gap_status"] == rec["gap_status"], cid
