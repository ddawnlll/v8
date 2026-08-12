"""S7 parity gate — verdict statistics + report/audit artifacts
(COMPUTE_CORE_SPEC §8 S7).

Gate: the `verdict` subcommand's statistics match the frozen oracle
`src/v8/statistics.py` bit-for-bit on a fixed episode series + seed; the
report artifact round-trips through the V8.2 reader; and the S7 audit flags a
report artifact that references an older tape (issue #123 freshness).

The oracle is the frozen Python library itself: `v8.statistics` has no
single "verdict" function, so the harness composes the same calls the Rust
driver makes and compares every value field emitted by the verdict JSON.
Identity/configuration strings are exact; floats compare by IEEE-754 bit
pattern (PARITY_AND_IDENTITY_SPEC §3).
"""
from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from tools.v82_reader import read as read_artifact

from .runner import ParityFailure

# The six S7 audit check names exactly as the binary prints them.
S7_AUDIT_TESTS = ("freshness", "round-trip", "header-completeness",
                  "tier-honesty", "no-decimal-floats", "retention")


def _bits(x) -> bytes:
    return struct.pack("<d", float(x))


def _run(v8_core_binary, subcommand: str, request: dict, tmp_path: Path):
    req_path = tmp_path / f"{subcommand}-req.json"
    req_path.write_text(json.dumps(request))
    proc = subprocess.run([str(v8_core_binary), subcommand, str(req_path)],
                          capture_output=True, text=True)
    return proc


def test_verdict_matches_python_statistics(v8_core_binary, tmp_path):
    """Every value field of the verdict JSON is bit-identical to the frozen
    oracle on the same inputs."""
    import v8.statistics as s

    tmp_path = Path(tmp_path)
    net_r = [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2]
    seed = 42
    n_resamples = 2000
    closes = [100.0, 102.0, 101.5, 105.0, 103.0, 107.5, 106.0, 110.0, 109.0, 112.0]
    moves = [0.001, -0.0005, 0.002, -0.001, 0.0008, -0.0003, 0.0015, -0.0009]
    dirs = [1, -1, 1, -1, 1, 1, -1, 1]

    req = {
        "net_r": net_r,
        "config": "v1",
        "seed": seed,
        "n_resamples": n_resamples,
        "closes": closes,
        "long_share": 0.65,
        "horizon_bars": 3,
        "risk_unit_frac": 0.01,
        "n_placebo": 8,
        "moves": moves,
        "directions": {"v1": dirs},
        "n_permutations": 50,
        "ci": 0.90,
        "max_hold_bars": 8,
        "slice_bars": 3,
        "min_net_r": 0.05,
        "min_trades": 8,
        "alpha": 0.05,
        "n_rules": 2,
        "search_universe_size": 28,
    }
    proc = _run(v8_core_binary, "verdict", req, tmp_path)
    if proc.returncode != 0:
        raise ParityFailure(
            f"verdict rc={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    # The §9 mechanical rule must auto-select the same block size on both
    # sides (no explicit block_size in the request — the full pipeline is
    # under test).
    block_size = s.select_block_size(net_r)
    assert block_size == 4, block_size

    # METH: Reality-Check (issue #128)
    rc = s.reality_check_p_value({"v1": net_r}, block_size, n_resamples, seed)
    got = out["reality_check"]
    if got["argmax_config"] != rc.argmax_config:
        raise ParityFailure(f"argmax_config py={rc.argmax_config!r} rust={got['argmax_config']!r}")
    if got["block_size"] != rc.block_size or got["n_resamples"] != rc.n_resamples:
        raise ParityFailure(f"rc sizes py=({rc.block_size},{rc.n_resamples}) rust=({got['block_size']},{got['n_resamples']})")
    if _bits(got["observed_max"]) != _bits(rc.observed_max):
        raise ParityFailure(f"observed_max py={rc.observed_max!r} rust={got['observed_max']!r}")
    if _bits(got["p_value"]) != _bits(rc.p_value):
        raise ParityFailure(f"p_value py={rc.p_value!r} rust={got['p_value']!r}")

    # Detrended null / Appendix A placebo invariant (issue #124)
    inv = s.appendix_a_invariant(closes, long_share=0.65, horizon_bars=3,
                                 risk_unit_frac=0.01, n_episodes=8, seed=seed)
    det = out["detrended_null"]
    if det["run"] is not True:
        raise ParityFailure("detrended_null not run with closes supplied")
    if _bits(det["placebo_mean_raw"]) != _bits(inv.placebo_mean_raw):
        raise ParityFailure(f"placebo_mean_raw py={inv.placebo_mean_raw!r} rust={det['placebo_mean_raw']!r}")
    if _bits(det["placebo_mean_detrended"]) != _bits(inv.placebo_mean_detrended):
        raise ParityFailure(f"placebo_mean_detrended py={inv.placebo_mean_detrended!r} rust={det['placebo_mean_detrended']!r}")
    if det["holds"] != inv.holds:
        raise ParityFailure(f"holds py={inv.holds!r} rust={det['holds']!r}")

    # METH-3: Monte-Carlo permutation Reality-Check
    pr = s.monte_carlo_permutation_p_value(moves, {"v1": dirs}, {"v1": net_r},
                                           n_permutations=50, seed=seed)
    perm = out["permutation"]
    if perm["run"] is not True:
        raise ParityFailure("permutation not run with moves/directions supplied")
    if _bits(perm["observed_max"]) != _bits(pr.observed_max):
        raise ParityFailure(f"perm observed_max py={pr.observed_max!r} rust={perm['observed_max']!r}")
    if perm["argmax_config"] != pr.argmax_config:
        raise ParityFailure(f"perm argmax py={pr.argmax_config!r} rust={perm['argmax_config']!r}")
    if _bits(perm["p_value"]) != _bits(pr.p_value):
        raise ParityFailure(f"perm p_value py={pr.p_value!r} rust={perm['p_value']!r}")

    # METH-4: bootstrap CI + effective independent episodes
    lo, hi = s.bootstrap_ci(net_r, block_size, n_resamples, seed, ci=0.90)
    ci = out["bootstrap_ci"]
    if _bits(ci["lower"]) != _bits(lo):
        raise ParityFailure(f"ci lower py={lo!r} rust={ci['lower']!r}")
    if _bits(ci["upper"]) != _bits(hi):
        raise ParityFailure(f"ci upper py={hi!r} rust={ci['upper']!r}")
    eff = s.effective_independent_episodes(len(net_r), 8)
    if _bits(out["effective_independent_episodes"]) != _bits(eff):
        raise ParityFailure(f"eff_n py={eff!r} rust={out['effective_independent_episodes']!r}")

    # METH-5: regime slices, streak-vs-null, practical significance
    slices = s.regime_slices(net_r, 3)
    got_slices = out["regime_slices"]
    if len(got_slices) != len(slices):
        raise ParityFailure(f"regime slice count py={len(slices)} rust={len(got_slices)}")
    for i, (g, p) in enumerate(zip(got_slices, slices)):
        if (g["start_idx"], g["end_idx"], g["n"]) != (p.start_idx, p.end_idx, p.n):
            raise ParityFailure(f"slice[{i}] geometry py=({p.start_idx},{p.end_idx},{p.n}) rust=({g['start_idx']},{g['end_idx']},{g['n']})")
        if _bits(g["mean_net_r"]) != _bits(p.mean_net_r):
            raise ParityFailure(f"slice[{i}] mean py={p.mean_net_r!r} rust={g['mean_net_r']!r}")
    streak = s.streak_vs_null(net_r, block_size, n_resamples, seed)
    got_streak = out["streak_vs_null"]
    if got_streak["observed_streak"] != streak.observed_streak:
        raise ParityFailure(f"streak py={streak.observed_streak} rust={got_streak['observed_streak']}")
    if _bits(got_streak["p_value"]) != _bits(streak.p_value):
        raise ParityFailure(f"streak p py={streak.p_value!r} rust={got_streak['p_value']!r}")
    meets, note = s.practical_significance(net_r, 0.05, 8)
    ps = out["practical_significance"]
    if ps["meets"] != meets:
        raise ParityFailure(f"practical meets py={meets!r} rust={ps['meets']!r}")
    if ps["note"] != note:
        raise ParityFailure(f"practical note py={note!r} rust={ps['note']!r}")

    # METH-6 / METH-2
    if _bits(out["expected_false_positives"]) != _bits(s.expected_false_positives(2, 0.05)):
        raise ParityFailure(f"efp py={s.expected_false_positives(2, 0.05)!r} rust={out['expected_false_positives']!r}")
    if out["effective_search_size"] != s.effective_search_size(1, 28):
        raise ParityFailure(f"ess py={s.effective_search_size(1, 28)!r} rust={out['effective_search_size']!r}")
    if out["multiplicity_undercounted"] is not True:
        raise ParityFailure("search 28 > evaluated 1 must report multiplicity_undercounted")

    # The top-level claim: no economic claim without an authority receipt
    # (rule 12), and the family metadata is exact.
    if out["verdict"] != "NO_ECONOMIC_CLAIM":
        raise ParityFailure(f"verdict claim {out['verdict']!r} violates rule 12")
    if out["source"] != "net_r" or out["seed"] != seed:
        raise ParityFailure(f"source/seed: {out['source']!r}/{out['seed']!r}")
    if out["family"]["configs"] != ["v1"] or out["family"]["n_episodes"] != 8:
        raise ParityFailure(f"family {out['family']!r}")


def test_report_artifact_round_trips(v8_core_binary, tmp_path):
    """The report driver writes report.v82, the V8.2 reader reads it back
    with the full header + slice row, and every S7 audit check passes on the
    freshly-written artifact."""
    tmp_path = Path(tmp_path)
    tape = tmp_path / "tape.jsonl"
    tape.write_text(json.dumps({"bar": 1}) + "\n")
    out_dir = tmp_path / "out"
    proc = _run(v8_core_binary, "report",
                {"tape_path": str(tape), "out_dir": str(out_dir),
                 "universe": ["SOLUSDT"]}, tmp_path)
    if proc.returncode != 0:
        raise ParityFailure(
            f"report rc={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    if summary["audit_pass"] is not True:
        raise ParityFailure(f"audit_pass {summary['audit_pass']!r}")
    for name in S7_AUDIT_TESTS:
        if f"report-audit: {name}: PASS" not in proc.stdout:
            raise ParityFailure(f"missing audit PASS for {name}:\n{proc.stdout}")

    art = read_artifact(Path(summary["artifact"]))
    if art.kind != "report":
        raise ParityFailure(f"kind {art.kind!r}")
    if art.tier != "VALUES":
        raise ParityFailure(f"tier {art.tier!r}")
    rc = art.run_constants
    if rc["verdict"] != "NO_ECONOMIC_CLAIM":
        raise ParityFailure(f"verdict run-constant {rc['verdict']!r}")
    if rc["ledger_hash"] != "ledger-absent":
        raise ParityFailure(f"ledger binding {rc['ledger_hash']!r}")
    for k in ("candidate_count", "n_gap_computed", "n_gap_abstained",
              "n_gap_not_applicable", "sum_gap"):
        if k not in rc:
            raise ParityFailure(f"report missing run-constant {k}")
    rows = list(art.rows())
    if len(rows) != 1:
        raise ParityFailure(f"row count {len(rows)}")
    row = rows[0]
    if row["slice_key"] != "SOLUSDT":
        raise ParityFailure(f"slice_key {row['slice_key']!r}")
    if row["slice_n"] != 0:
        raise ParityFailure(f"slice_n {row['slice_n']!r}")
    if _bits(row["slice_sum_gap"]) != _bits(0.0):
        raise ParityFailure(f"slice_sum_gap {row['slice_sum_gap']!r}")


def test_report_audit_flags_a_stale_artifact(v8_core_binary, tmp_path):
    """A report built against tape T1 is stale once the tape at the same path
    is replaced: auditing the on-disk report against the current tape flags
    the freshness violation and the driver fails closed (issue #123)."""
    tmp_path = Path(tmp_path)
    tape = tmp_path / "tape.jsonl"
    tape.write_text(json.dumps({"bar": 1}) + "\n")
    out_dir = tmp_path / "out"
    proc = _run(v8_core_binary, "report",
                {"tape_path": str(tape), "out_dir": str(out_dir)}, tmp_path)
    if proc.returncode != 0:
        raise ParityFailure(f"first report rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")
    report_path = out_dir / "report.v82"
    if not report_path.is_file():
        raise ParityFailure("report.v82 not written")

    # Replace the tape at the same path: the report on disk now references an
    # older tape.
    tape.write_text(json.dumps({"bar": 2, "changed": True}) + "\n")

    proc = _run(v8_core_binary, "report", {
        "tape_path": str(tape),
        "out_dir": str(out_dir),
        "audit_report": str(report_path),
    }, tmp_path)
    if proc.returncode != 1:
        raise ParityFailure(
            f"stale audit must fail closed, rc={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    output = proc.stdout + proc.stderr
    if "report-audit: freshness: FAIL" not in output:
        raise ParityFailure(f"freshness not flagged stale:\n{output}")
    if "older than current" not in output:
        raise ParityFailure(f"stale detail missing:\n{output}")
    if "report-audit: round-trip: PASS" not in output:
        raise ParityFailure(f"non-freshness checks still pass:\n{output}")
