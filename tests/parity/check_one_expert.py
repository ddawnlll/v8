"""Standalone per-expert S4 parity check for the port agents.

Usage (after building with your own target dir to stay parallel-safe):

    CARGO_TARGET_DIR=$CLAUDE_JOB_DIR/tmp/target-<id> cargo build --release
    .venv/bin/python tests/parity/check_one_expert.py <expert_id> \
        $CLAUDE_JOB_DIR/tmp/target-<id>/release/v8-core

Prints PASS <expert_id> (N candidate bars) or FAIL with the first mismatch.
Exit 0 on pass, 1 on fail. Does not touch any committed test file.
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


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_one_expert.py <expert_id> <v8-core-binary>", file=sys.stderr)
        return 2
    eid, binary = sys.argv[1], Path(sys.argv[2])
    if eid not in EXPERT_CLASSES:
        print(f"unknown expert {eid}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rows = make_synthetic_tape(seed=7, n_bars=120, continuous=True)
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
            print(f"FAIL {eid}: evaluate-check rc={proc.returncode}: {proc.stderr[:400]}", file=sys.stderr)
            return 1
        rust_all = {r["bar_index"]: r for r in json.loads(proc.stdout.strip().splitlines()[-1])["results"]}

        candidates = 0
        for bar_idx, bar in enumerate(bars):
            py = evals.get((bar.available_time, eid))
            rust = rust_all[bar_idx]
            if py is None:
                print(f"FAIL {eid}: bar {bar_idx}: no Python evaluation", file=sys.stderr)
                return 1
            if rust["decision"] != py["decision"]:
                print(f"FAIL {eid}: bar {bar_idx}: decision py={py['decision']} rust={rust['decision']}", file=sys.stderr)
                return 1
            if py["decision"] == "CANDIDATE":
                candidates += 1
                pd, rd = py["draft"], rust["draft"]
                for field in ("direction", "birth_time"):
                    if rd[field] != pd[field]:
                        print(f"FAIL {eid}: bar {bar_idx}: {field} py={pd[field]} rust={rd[field]}", file=sys.stderr)
                        return 1
                if rd["risk_geometry"] != pd["risk_geometry"]:
                    print(f"FAIL {eid}: bar {bar_idx}: geometry py={pd['risk_geometry']} rust={rd['risk_geometry']}", file=sys.stderr)
                    return 1
                if rust["setup_fingerprint"] != pd.get("setup_fingerprint"):
                    print(f"FAIL {eid}: bar {bar_idx}: fingerprint py={pd.get('setup_fingerprint')} rust={rust['setup_fingerprint']}", file=sys.stderr)
                    return 1
                if rust["setup_anchor_event_id"] != pd.get("setup_anchor_event_id"):
                    print(f"FAIL {eid}: bar {bar_idx}: anchor py={pd.get('setup_anchor_event_id')} rust={rust['setup_anchor_event_id']}", file=sys.stderr)
                    return 1
        if candidates == 0:
            print(f"FAIL {eid}: no candidate bars in fixture (is the setup ever true?)", file=sys.stderr)
            return 1
        print(f"PASS {eid} ({candidates} candidate bars, {len(bars)} bars)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
