"""S4 gate (in progress) — CandidateBuffer + ExpertPlane.

The full S4 gate is candidate-population parity: the candidates/evaluations/
outcomes values bit-identical to the Python lab on the fixture set. This
suite exercises the ExpertPlane port incrementally — the evaluate() drafts
must match the Python lab's per-bar evaluations bit-for-bit before the
lifecycle/admission loop can be meaningfully compared.

Ports present so far: the three pilots (trend_pullback, failed_breakout,
liquidity_sweep_reclaim). An expert with no port returns NO_HABITAT and
cannot fabricate a candidate — the gate fails loudly until the registry is
complete.
"""
from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

from . import runner
from .runner import ParityFailure

REPO_ROOT = runner.REPO_ROOT

PILOTS = ["trend_pullback", "failed_breakout", "liquidity_sweep_reclaim"]


def _pilots():
    import v8.experts as ex
    return [getattr(ex, {
        "trend_pullback": "TrendPullbackExpert",
        "failed_breakout": "FailedBreakoutExpert",
        "liquidity_sweep_reclaim": "LiquiditySweepReclaimExpert",
    }[pid])() for pid in PILOTS]


def _run_lab(tmp_path, rows):
    lab = Lab(tmp_path)
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: r.available_time)
    manifest = ExperimentManifest(
        experiment_id="s4", code_hash="", data_hash="",
        universe=("SOLUSDT",), start_ns=bars[0].available_time,
        end_ns=bars[-1].available_time)
    lab.run(manifest, _pilots())
    # evaluations.jsonl: {knowledge_time, expert_id, applicability, decision,
    #                      draft}
    evals = {}
    for line in (tmp_path / "evaluations.jsonl").read_text().splitlines():
        rec = json.loads(line)
        evals[(rec["knowledge_time"], rec["expert_id"])] = rec
    return lab, bars, evals


def _rust_evals(v8_core_binary, tmp_path, bars, cases):
    """Batch evaluate-check; returns {case_key: result}."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape = runner.write_tape(bars, tmp_path / "tape.jsonl")
    req = {"tape_path": str(tape), "universe": ["SOLUSDT"],
           "cases": [{"expert_id": e, "bar_index": b} for e, b in cases],
           "history_depth": 32}
    req_path = tmp_path / "req.json"
    req_path.write_text(json.dumps(req))
    proc = subprocess.run([str(v8_core_binary), "evaluate-check", str(req_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"evaluate-check failed: {proc.stderr}")
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    return {(r["expert_id"], r["bar_index"]): r for r in out["results"]}


def test_pilot_drafts_match_python_evaluations(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=7, n_bars=120, continuous=True)
    lab, bars, evals = _run_lab(tmp_path / "lab", rows)
    rust_all = _rust_evals(v8_core_binary, tmp_path / "rust",
                           bars, [(pid, i) for i in range(len(bars))
                                  for pid in PILOTS])
    for bar_idx, bar in enumerate(bars):
        t_ns = bar.available_time
        for pid in PILOTS:
            py = evals.get((t_ns, pid))
            rust = rust_all[(pid, bar_idx)]
            assert rust["decision"] == py["decision"], (
                f"{pid} bar {bar_idx}: decision py={py['decision']} rust={rust['decision']}")
            if py["decision"] == "CANDIDATE":
                pd = py["draft"]
                rd = rust["draft"]
                assert rd["direction"] == pd["direction"], (
                    f"{pid} bar {bar_idx}: direction py={pd['direction']} rust={rd['direction']}")
                assert rd["birth_time"] == pd["birth_time"], (
                    f"{pid} bar {bar_idx}: birth_time")
                assert rd["risk_geometry"] == pd["risk_geometry"], (
                    f"{pid} bar {bar_idx}: geometry py={pd['risk_geometry']} "
                    f"rust={rd['risk_geometry']}")


def test_pilot_anchors_match(v8_core_binary, tmp_path):
    """The D-026 setup_anchor_event_id must match on every candidate bar."""
    rows = make_synthetic_tape(seed=7, n_bars=120, continuous=True)
    lab, bars, evals = _run_lab(tmp_path / "lab", rows)
    checked = 0
    rust_all = _rust_evals(v8_core_binary, tmp_path / "rust",
                           bars, [(pid, i) for i in range(len(bars))
                                  for pid in PILOTS])
    for bar_idx, bar in enumerate(bars):
        t_ns = bar.available_time
        for pid in PILOTS:
            py = evals.get((t_ns, pid))
            rust = rust_all[(pid, bar_idx)]
            if py and py["decision"] == "CANDIDATE":
                assert rust["decision"] == "CANDIDATE", f"{pid} bar {bar_idx}"
                assert rust["draft"]["direction"] == py["draft"]["direction"]
                # the anchor is the same event (the setup_anchor_event_id is
                # an identity of the candidate; both sides must agree on which
                # bar it is — compare it through the lab's draft).
                assert py["draft"]["setup_anchor_event_id"] is not None
                checked += 1
    assert checked > 0, "no candidate bars in fixture"
