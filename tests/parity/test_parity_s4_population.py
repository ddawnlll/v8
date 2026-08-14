"""S4 gate — candidate-population parity (issue #102).

The gate: the `evaluate` loop's candidate population matches the Python lab
on the fixture set. Both run over the SAME synthetic tape (seed 7, 120 bars,
all 28 registered experts) and the three comparisons are:

(a) per-bar evaluations bit-identical — for every (knowledge_time, expert_id)
    record: applicability, decision, and on CANDIDATE the draft's direction,
    birth_time, risk_geometry (IEEE-754 bit compare via compare_value),
    setup_fingerprint and setup_anchor_event_id;
(b) the D-026 episode-key population — the set of DETECTED episode-key inputs
    (expert_id, expert_version, instrument, direction, setup_anchor_event_id,
    structural geometry) is identical, and the suppressed_duplicate set is
    identical;
(c) the loop's summary reconciles with the lab — n_suppressed equals the
    lab's suppressed_duplicate count, and the DETECTED population
    (n_candidates + n_rejected) equals the lab's candidate_count.

Identity strings (candidate_id, geometry_version, event_hash) are V8.2
bit-encoded (D-079) and excluded from the value comparison by
PARITY_AND_IDENTITY_SPEC §3: the episode-key comparison is over the key's
VALUE inputs, never the hash text.

Known structural divergence (surfaced by this gate, documented in
reports/parity/S4.md): the loop admits at DETECTION — it runs the D-024 mask
and the RiskGate on the detection bar and never releases exposure slots (no
position lifecycle), so its PENDING/REJECTED split differs from the lab's
trigger-time admission. The DETECTED population and the suppression are
identical; that is what this gate pins.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

from . import runner
from .runner import ParityFailure, compare_value

REPO_ROOT = runner.REPO_ROOT

# expert_id -> Python class (frozen oracle; EXPERT_PROTOCOL §3).
EXPERT_CLASSES = {
    "bollinger_breakout": "BollingerBreakoutExpert",
    "bollinger_reversion": "BollingerReversionExpert",
    "breakout_retest": "BreakoutRetestExpert",
    "candlestick_reversal": "CandlestickReversalExpert",
    "divergence_12_setups": "Divergence12SetupsExpert",
    "donchian_breakout": "DonchianBreakoutExpert",
    "failed_breakout": "FailedBreakoutExpert",
    "failed_breakout_2b": "FailedBreakout2BExpert",
    "fib_projection_reversal": "FibProjectionReversalExpert",
    "fib_retracement_continuation": "FibRetracementContinuationExpert",
    "fib_rsi_bb_confluence": "FibRsiBbConfluenceExpert",
    "floor_trader_pivot": "FloorTraderPivotExpert",
    "funding_crowding_reversal": "FundingCrowdingReversalExpert",
    "gap_exhaustion": "GapExhaustionExpert",
    "ichimoku_cloud": "IchimokuCloudExpert",
    "liquidity_sweep_reclaim": "LiquiditySweepReclaimExpert",
    "macd_stoch_trend": "MacdStochTrendExpert",
    "market_profile_value_area": "MarketProfileValueAreaExpert",
    "obv_adl_regime": "ObvAdlRegimeExpert",
    "open_interest_divergence": "OpenInterestDivergenceExpert",
    "pandf_breakout": "PandfBreakoutExpert",
    "pattern_measuring_objective": "PatternMeasuringObjectiveExpert",
    "range_breakout_1to1": "RangeBreakout1To1Expert",
    "rsi_stoch_reversion": "RsiStochReversionExpert",
    "trend_pullback": "TrendPullbackExpert",
    "trend_pullback_depth": "TrendPullbackDepthExpert",
    "volume_climax_reversal": "VolumeClimaxReversalExpert",
    "volume_confirmed_breakout": "VolumeConfirmedBreakoutExpert",
}
ALL_EXPERTS = sorted(EXPERT_CLASSES)

# Structural geometry keys excluded from episode identity (geometry_version) —
# they move with the market and must not change a stable setup's key
# (src/v8/lab.py `_geometry_version`; v8-core candidate.rs EXCLUDED_GEOMETRY_KEYS).
_GEOM_EXCLUDED = {"atr_ref", "prior_high_ref", "prior_low_ref",
                  "lower_3sd_ref", "upper_3sd_ref", "stop_ref", "stop_r"}


def _pilots(expert_ids: list[str]):
    import v8.experts as ex
    return [getattr(ex, EXPERT_CLASSES[eid])() for eid in expert_ids]


def _run_lab(tmp_path, rows, expert_ids):
    """The Python oracle: a fresh Lab over the fixture, `expert_ids` sorted by
    expert_id (lab.run PHASE 3 canonical order). Returns the LabReport, the
    evaluations by (knowledge_time, expert_id), the parsed candidates.jsonl
    rows, and the closed bars."""
    lab = Lab(tmp_path)
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: r.available_time)
    manifest = ExperimentManifest(
        experiment_id="s4-pop", code_hash="", data_hash="",
        universe=("SOLUSDT",), start_ns=bars[0].available_time,
        end_ns=bars[-1].available_time)
    report = lab.run(manifest, _pilots(expert_ids))
    evals = {}
    for line in (tmp_path / "evaluations.jsonl").read_text().splitlines():
        rec = json.loads(line)
        evals[(rec["knowledge_time"], rec["expert_id"])] = rec
    cands = [json.loads(l) for l in
             (tmp_path / "candidates.jsonl").read_text().splitlines()]
    return report, evals, cands, bars


def _run_loop(v8_core_binary, tmp_path, rows):
    """The compute plane: `v8-core evaluate <request.json>` over the same
    tape (runloop::run request format: tape_path, universe, history_depth,
    experts — empty = the full 28-expert dispatch table —, max_heat). Returns
    the loop summary and the emitted evaluations/candidates rows."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    req = {
        "tape_path": str(tape),
        "universe": ["SOLUSDT"],
        "out_dir": str(tmp_path / "out"),
        "history_depth": 32,
        "experts": [],
        "max_heat": 3.0,
        "max_cluster_heat": 2.0,
        "base_interval": "1h",
        # The D-024 frozen manifest constants, matching ExperimentManifest's
        # defaults (the lab side of this gate runs those defaults).
        "manifest": {"max_bar_range_frac": 0.05, "funding_window_bars": 1},
    }
    req_path = tmp_path / "req.json"
    req_path.write_text(json.dumps(req))
    proc = subprocess.run([str(v8_core_binary), "evaluate", str(req_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"evaluate failed (rc={proc.returncode}): {proc.stderr}")
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    evals = {}
    for line in Path(summary["evaluations"]).read_text().splitlines():
        rec = json.loads(line)
        evals[(rec["knowledge_time"], rec["expert_id"])] = rec
    cands = [json.loads(l) for l in
             Path(summary["candidates"]).read_text().splitlines()]
    return summary, evals, cands


def _transitions(cands):
    return [r for r in cands if "to_state" in r]


def _suppressed(cands):
    return [r for r in cands if r.get("kind") == "suppressed_duplicate"]


def _structural(g: dict) -> dict:
    return {k: v for k, v in sorted(g.items()) if k not in _GEOM_EXCLUDED}


def _episode_fp(ev) -> tuple:
    """The D-026 episode-key inputs of a CANDIDATE evaluation as a hashable
    fingerprint: (expert_id, expert_version, instrument, direction,
    setup_anchor_event_id) plus the canonical JSON text of the structural
    geometry (the geometry_version input). Distinct episodes can share the
    first five with different geometry content, so the geometry is part of the
    key. The candidate_id / geometry_version hash TEXT itself is a D-079
    identity and is excluded (PARITY_AND_IDENTITY_SPEC §3)."""
    d = ev["draft"]
    geom = json.dumps(_structural(d["risk_geometry"]), sort_keys=True,
                      separators=(",", ":"), default=str)
    return (d["expert_id"], d["expert_version"], d["instrument"],
            d["direction"], d["setup_anchor_event_id"], geom)


def _episode_keys(transitions, evals):
    """{episode-key fingerprint} of every DETECTED transition, cross-checked
    against the eval that produced it — a transition can never disagree with
    the evaluation it names."""
    keys = set()
    for r in transitions:
        if r["to_state"] != "DETECTED":
            continue
        ev = evals[(r["knowledge_time"], r["expert_id"])]
        assert ev["decision"] == "CANDIDATE", (
            f"DETECTED {r['candidate_id']} without a CANDIDATE evaluation")
        d = ev["draft"]
        assert d["expert_version"] == r["expert_version"], r["candidate_id"]
        assert d["instrument"] == r["instrument"], r["candidate_id"]
        assert d["direction"] == r["direction"], r["candidate_id"]
        assert d["setup_anchor_event_id"] == r["setup_anchor_event_id"], (
            r["candidate_id"])
        keys.add(_episode_fp(ev))
    return keys


def _run_both(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=7, n_bars=120, continuous=True)
    report, lab_evals, lab_cands, bars = _run_lab(
        tmp_path / "lab", rows, ALL_EXPERTS)
    summary, rust_evals, rust_cands = _run_loop(
        v8_core_binary, tmp_path / "rust", rows)
    return (bars, report, lab_evals, lab_cands,
            summary, rust_evals, rust_cands)


def test_oracle_tree_hash_pinned(oracle_tree_hash):
    """The frozen oracle (git rev-parse HEAD:src/v8) is unchanged since the
    S0..S3 gates; if it moves, every recorded parity result is invalidated
    (PARITY_AND_IDENTITY_SPEC §7.5)."""
    assert oracle_tree_hash == "2854f8c30fe59a25ef617d0357cd2fc71faa9b0b"


def test_evaluations_bit_identical(v8_core_binary, tmp_path):
    """(a) every per-bar evaluation matches the lab bit-for-bit: applicability,
    decision, and on CANDIDATE the draft's direction, birth_time,
    risk_geometry (IEEE-754 bit compare), setup_fingerprint and
    setup_anchor_event_id."""
    (bars, report, lab_evals, lab_cands,
     summary, rust_evals, rust_cands) = _run_both(v8_core_binary, tmp_path)

    assert len(lab_evals) == len(rust_evals) == len(bars) * len(ALL_EXPERTS)
    assert set(lab_evals) == set(rust_evals), (
        "(knowledge_time, expert_id) key sets differ")

    n_candidate = 0
    for key in sorted(lab_evals):
        py, rs = lab_evals[key], rust_evals[key]
        assert rs["applicability"] == py["applicability"], key
        assert rs["decision"] == py["decision"], key
        if py["decision"] != "CANDIDATE":
            assert (rs["draft"] is None) == (py["draft"] is None), key
            continue
        n_candidate += 1
        pd, rd = py["draft"], rs["draft"]
        assert rd is not None, key
        assert rd["direction"] == pd["direction"], key
        assert rd["birth_time"] == pd["birth_time"], key
        compare_value(f"{key} risk_geometry", pd["risk_geometry"],
                      rd["risk_geometry"])
        assert rd["setup_fingerprint"] == pd["setup_fingerprint"], key
        assert rd["setup_anchor_event_id"] == pd["setup_anchor_event_id"], key
    assert n_candidate > 0, "fixture produced no candidate evaluations"


def test_episode_key_population_identical(v8_core_binary, tmp_path):
    """(b) the D-026 episode-key population: every DETECTED episode on the
    Rust side is the same (expert_id, version, instrument, direction, anchor,
    structural geometry) as on the lab side, and the count equals the lab's
    candidate_count. The candidate_id / geometry_version hash TEXT differs by
    the D-079 encoding and is excluded (PARITY_AND_IDENTITY_SPEC §3)."""
    (bars, report, lab_evals, lab_cands,
     summary, rust_evals, rust_cands) = _run_both(v8_core_binary, tmp_path)

    lab_keys = _episode_keys(_transitions(lab_cands), lab_evals)
    rust_keys = _episode_keys(_transitions(rust_cands), rust_evals)

    assert len(lab_keys) == len(rust_keys) == report.candidate_count
    assert lab_keys == rust_keys, (
        f"episode-key input sets differ: "
        f"only-lab {len(lab_keys - rust_keys)}, "
        f"only-rust {len(rust_keys - lab_keys)}")
    # The lab's own count is over distinct DETECTED candidate_ids; dedup means
    # no key is DETECTED twice, so the episode-key cardinality must agree with
    # the DETECTED transition count as well.
    assert len({r["candidate_id"] for r in _transitions(lab_cands)}) == \
        report.candidate_count
    assert len([r for r in _transitions(lab_cands)
                if r["to_state"] == "DETECTED"]) == len(lab_keys)


def test_suppressed_duplicate_set_identical(v8_core_binary, tmp_path):
    """(b) the suppressed_duplicate set: same count, same (birth_time,
    expert_id) identity per row, and the same D-026 episode-key inputs
    (deduced from the eval at the suppressed row's birth bar). candidate_id is
    the D-079 hash and excluded."""
    (bars, report, lab_evals, lab_cands,
     summary, rust_evals, rust_cands) = _run_both(v8_core_binary, tmp_path)

    lab_sup = _suppressed(lab_cands)
    rust_sup = _suppressed(rust_cands)
    assert len(lab_sup) == len(rust_sup)
    lab_sig = {(r["birth_time"], r["expert_id"]) for r in lab_sup}
    rust_sig = {(r["birth_time"], r["expert_id"]) for r in rust_sup}
    assert lab_sig == rust_sig

    # every suppressed row is a re-detection of an episode that was ALREADY
    # DETECTED at an earlier bar — the dedup fires on the detected set, never
    # on a future or non-existent episode (checked on both sides).
    lab_detected = _episode_keys(_transitions(lab_cands), lab_evals)
    rust_detected = _episode_keys(_transitions(rust_cands), rust_evals)
    lab_sup_keys = set()
    rust_sup_keys = set()
    for r in lab_sup:
        ev = lab_evals[(r["birth_time"], r["expert_id"])]
        assert ev["decision"] == "CANDIDATE", (
            f"suppressed {r['candidate_id']} without a CANDIDATE evaluation")
        key = _episode_fp(ev)
        assert key in lab_detected, (
            f"lab suppressed {r['candidate_id']} duplicates a never-detected "
            "episode")
        lab_sup_keys.add(key)
    for r in rust_sup:
        ev = rust_evals[(r["birth_time"], r["expert_id"])]
        assert ev["decision"] == "CANDIDATE", (
            f"suppressed {r['candidate_id']} without a CANDIDATE evaluation")
        key = _episode_fp(ev)
        assert key in rust_detected, (
            f"rust suppressed {r['candidate_id']} duplicates a never-detected "
            "episode")
        rust_sup_keys.add(key)
    # the suppressed episode-key populations are the same on both sides
    assert lab_sup_keys == rust_sup_keys, (
        f"suppressed episode-key sets differ: "
        f"only-lab {len(lab_sup_keys - rust_sup_keys)}, "
        f"only-rust {len(rust_sup_keys - lab_sup_keys)}")


def test_summary_reconciles_with_lab_population(v8_core_binary, tmp_path):
    """(c) the loop's summary reconciles with the lab: n_suppressed equals the
    lab's suppressed_duplicate count, and the DETECTED population
    (n_candidates + n_rejected) equals the lab's candidate_count. Each side's
    counters are also checked against its own candidates.jsonl, so a summary
    can never drift from the ledger it reports."""
    (bars, report, lab_evals, lab_cands,
     summary, rust_evals, rust_cands) = _run_both(v8_core_binary, tmp_path)

    assert summary["subcommand"] == "evaluate"
    assert summary["n_suppressed"] == len(_suppressed(lab_cands)), (
        "suppressed_duplicate count differs from the lab")
    assert summary["n_candidates"] + summary["n_rejected"] == \
        report.candidate_count, (
        "the loop's DETECTED population (n_candidates + n_rejected) does not "
        "equal the lab's candidate_count")
    assert summary["n_evaluations"] == len(lab_evals)

    rust_trans = _transitions(rust_cands)
    assert sum(1 for r in rust_trans if r["to_state"] == "PENDING") == \
        summary["n_candidates"]
    assert sum(1 for r in rust_trans if r["to_state"] == "REJECTED") == \
        summary["n_rejected"]
    assert sum(1 for r in rust_trans if r["to_state"] == "DETECTED") == \
        report.candidate_count
    assert sum(1 for r in rust_trans if r["to_state"] == "DETECTED") == \
        summary["n_candidates"] + summary["n_rejected"]
