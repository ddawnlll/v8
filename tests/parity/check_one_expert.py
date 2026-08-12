"""Standalone per-expert S4 parity check for the port agents.

Usage (after building with your own target dir to stay parallel-safe):

    CARGO_TARGET_DIR=$CLAUDE_JOB_DIR/tmp/target-<id> cargo build --release
    .venv/bin/python tests/parity/check_one_expert.py <expert_id> \
        $CLAUDE_JOB_DIR/tmp/target-<id>/release/v8-core [--seed N] [--max-seed M]

A seed sweep (--seed .. --max-seed) runs every seed in range; PASS requires
every bar's decision to match the Python oracle on every seed. Zero candidate
bars is NOT a failure when the oracle also produced zero — it is parity (the
setup is simply rare on that seed). Exit 0 on pass, 1 on fail. Does not touch
any committed test file.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

from tests.parity import runner
from tests.parity.test_parity_s4 import EXPERT_CLASSES, _pilots

REPO_ROOT = Path(__file__).resolve().parents[2]


class Mismatch(Exception):
    pass


def _check_seed(eid: str, binary: Path, seed: int) -> tuple[int, int, int]:
    """One seed: (decisions_checked, py_candidates, rust_candidates).
    Raises Mismatch on any decision divergence."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rows = make_synthetic_tape(seed=seed, n_bars=120, continuous=True)
        lab = Lab(tmp / "lab")
        lab.ingest(rows)
        tape = lab.tape_log.replay_tape()
        bars = sorted([r for r in tape if r.channel == "kline"
                       and r.payload.get("closed") is True],
                      key=lambda r: r.available_time)
        manifest = ExperimentManifest(
            experiment_id="s4", code_hash="", data_hash="",
            universe=("SOLUSDT",), start_ns=bars[0].available_time,
            end_ns=bars[-1].available_time)
        lab.run(manifest, _pilots([eid]))
        evals = {}
        for line in (tmp / "lab" / "evaluations.jsonl").read_text().splitlines():
            rec = json.loads(line)
            evals[(rec["knowledge_time"], rec["expert_id"])] = rec

        tape_path = runner.write_tape(bars, tmp / "tape.jsonl")
        req = {"tape_path": str(tape_path), "universe": ["SOLUSDT"],
               "cases": [{"expert_id": eid, "bar_index": i} for i in range(len(bars))],
               "history_depth": 32}
        req_path = tmp / "req.json"
        req_path.write_text(json.dumps(req))
        proc = subprocess.run([str(binary), "evaluate-check", str(req_path)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise Mismatch(f"evaluate-check rc={proc.returncode}: {proc.stderr[:400]}")
        rust_all = {r["bar_index"]: r for r in json.loads(proc.stdout.strip().splitlines()[-1])["results"]}

        checked, py_cand = 0, 0
        for bar_idx, bar in enumerate(bars):
            py = evals.get((bar.available_time, eid))
            rust = rust_all[bar_idx]
            if py is None:
                raise Mismatch(f"bar {bar_idx}: no Python evaluation")
            checked += 1
            if rust["decision"] != py["decision"]:
                raise Mismatch(
                    f"bar {bar_idx}: decision py={py['decision']} rust={rust['decision']}")
            if py["decision"] == "CANDIDATE":
                py_cand += 1
                pd, rd = py["draft"], rust["draft"]
                for field in ("direction", "birth_time"):
                    if rd[field] != pd[field]:
                        raise Mismatch(
                            f"bar {bar_idx}: {field} py={pd[field]} rust={rd[field]}")
                if rd["risk_geometry"] != pd["risk_geometry"]:
                    raise Mismatch(
                        f"bar {bar_idx}: geometry py={pd['risk_geometry']} rust={rd['risk_geometry']}")
                if rust["setup_fingerprint"] != pd.get("setup_fingerprint"):
                    raise Mismatch(
                        f"bar {bar_idx}: fingerprint py={pd.get('setup_fingerprint')} rust={rust['setup_fingerprint']}")
                if rust["setup_anchor_event_id"] != pd.get("setup_anchor_event_id"):
                    raise Mismatch(
                        f"bar {bar_idx}: anchor py={pd.get('setup_anchor_event_id')} rust={rust['setup_anchor_event_id']}")
        return checked, py_cand, py_cand


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2:
        print("usage: check_one_expert.py <expert_id> <v8-core-binary> "
              "[--seed N] [--max-seed M]", file=sys.stderr)
        return 2
    eid, binary = args[0], Path(args[1])
    seed, max_seed = 7, 7
    rest = args[2:]
    if "--seed" in rest:
        seed = int(rest[rest.index("--seed") + 1])
    if "--max-seed" in rest:
        max_seed = int(rest[rest.index("--max-seed") + 1])
    if eid not in EXPERT_CLASSES:
        print(f"unknown expert {eid}", file=sys.stderr)
        return 2

    total_checked, total_py, total_rust = 0, 0, 0
    for s in range(seed, max_seed + 1):
        try:
            c, p, r = _check_seed(eid, binary, s)
        except Mismatch as e:
            print(f"FAIL {eid} seed {s}: {e}", file=sys.stderr)
            return 1
        total_checked += c
        total_py += p
        total_rust += r
    if total_checked == 0:
        print(f"FAIL {eid}: no bars checked", file=sys.stderr)
        return 1
    print(f"PASS {eid} (seeds {seed}..{max_seed}, {total_checked} bars, "
          f"py {total_py} / rust {total_rust} candidate bars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
