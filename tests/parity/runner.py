"""Parity-harness runner: fixture tapes, binary invocation, bit-level compare.

Comparison semantics follow PARITY_AND_IDENTITY_SPEC §3:
- floats compare by IEEE-754 bit pattern (struct.pack equality): `-0.0` is
  distinct from `0.0` and any NaN payload difference is a failure;
- ints/strings/bools/enums compare exactly;
- set-like fields compare after the canonical sort each side already applies;
- absence (a missing key / null cell) is never equal to a numeric zero.
"""
from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from tools.v82_reader import fingerprint as artifact_fingerprint
from tools.v82_reader import read as read_artifact

REPO_ROOT = Path(__file__).resolve().parents[2]
BINARY = REPO_ROOT / "v8-core" / "target" / "release" / "v8-core"


class ParityFailure(AssertionError):
    pass


def f64_bits(v: float) -> bytes:
    return struct.pack("<d", v)


def bit_equal(a: float, b: float) -> bool:
    return f64_bits(a) == f64_bits(b)


def compare_value(tag: str, py, rust) -> None:
    """Recursively compare a Python-oracle value against a Rust-emitted value."""
    if isinstance(py, bool):
        if rust is None or py != rust:
            raise ParityFailure(f"{tag}: bool mismatch py={py!r} rust={rust!r}")
        return
    if isinstance(py, int):
        if rust is None or py != rust:
            raise ParityFailure(f"{tag}: int mismatch py={py!r} rust={rust!r}")
        return
    if isinstance(py, float):
        if rust is None or not isinstance(rust, float) or not bit_equal(py, rust):
            raise ParityFailure(
                f"{tag}: f64 mismatch py={py!r}({f64_bits(py).hex()}) "
                f"rust={rust!r}({f64_bits(rust).hex() if isinstance(rust, float) else '?'})")
        return
    if isinstance(py, str):
        if rust is None or py != rust:
            raise ParityFailure(f"{tag}: str mismatch py={py!r} rust={rust!r}")
        return
    if isinstance(py, list):
        if rust is None or not isinstance(rust, list) or len(py) != len(rust):
            raise ParityFailure(f"{tag}: list mismatch py={py!r} rust={rust!r}")
        for i, (a, b) in enumerate(zip(py, rust)):
            compare_value(f"{tag}[{i}]", a, b)
        return
    if isinstance(py, tuple):
        compare_value(tag, list(py), rust)
        return
    if isinstance(py, dict):
        if rust is None or not isinstance(rust, dict):
            raise ParityFailure(f"{tag}: dict mismatch py={py!r} rust={rust!r}")
        if sorted(py.keys()) != sorted(rust.keys()):
            raise ParityFailure(f"{tag}: dict keys differ py={sorted(py)} rust={sorted(rust)}")
        for k in sorted(py.keys()):
            compare_value(f"{tag}.{k}", py[k], rust[k])
        return
    raise ParityFailure(f"{tag}: unsupported type {type(py).__name__}")


def write_tape(rows, path: Path) -> Path:
    """Serialize TapeRow objects (or plain dicts) to a Python-written JSONL
    tape — the format the compute plane ingests."""
    with open(path, "w") as fh:
        for r in rows:
            if hasattr(r, "source"):
                r = {
                    "source": r.source,
                    "channel": r.channel,
                    "instrument": r.instrument,
                    "event_time": r.event_time,
                    "available_time": r.available_time,
                    "ingested_time": r.ingested_time,
                    "venue_sequence": r.venue_sequence,
                    "event_id": r.event_id,
                    "payload": r.payload,
                }
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    return path


def tape_dicts(path: Path):
    """The tape as parsed plain dicts (the V8.0 oracle view)."""
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_request(tape_path: Path, out_dir: Path, threads: int = 1,
                  tier: str = "VALUES") -> dict:
    return {
        "tape_path": str(tape_path),
        "out_dir": str(out_dir),
        "threads": threads,
        "engine": "cpu",
        "tier": tier,
    }


def write_request_file(request: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    req_path = out_dir / "request.json"
    req_path.write_text(json.dumps(request))
    return req_path


def run_ingest(binary: Path, tape_path: Path, out_dir: Path,
               threads: int = 1, tier: str = "VALUES"):
    """Invoke `v8-core ingest`; returns (summary, artifact, stderr)."""
    request = build_request(tape_path, out_dir, threads, tier)
    req_path = write_request_file(request, out_dir)
    proc = subprocess.run([str(binary), "ingest", str(req_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"ingest failed (rc={proc.returncode}): {proc.stderr}")
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    artifact = out_dir / "dataset.v82"
    return summary, artifact, proc.stderr


def oracle_rows_from_tape(tape_path: Path):
    """The oracle's replay-order rows: sorted by (event, available, sequence),
    mirroring `AppendOnlyLog.replay_tape`."""
    rows = tape_dicts(tape_path)
    rows.sort(key=lambda r: (r["event_time"], r["available_time"],
                             r["venue_sequence"]))
    return rows


def compare_artifact_to_oracle(artifact_path: Path, oracle_rows) -> int:
    """Bit-compare every artifact row to the oracle rows in order. Returns the
    number of rows compared (G2: every record, not a sample)."""
    art = read_artifact(artifact_path)
    if art.row_count != len(oracle_rows):
        raise ParityFailure(
            f"row count mismatch: artifact {art.row_count} vs oracle {len(oracle_rows)}")
    for i, (orow, arow) in enumerate(zip(oracle_rows, art.rows())):
        # identity/clocks: exact
        for f in ("source", "channel", "instrument", "event_time",
                  "available_time", "ingested_time", "venue_sequence", "event_id"):
            if arow[f] is None or arow[f] != orow[f]:
                raise ParityFailure(f"row {i} field {f}: py={orow[f]!r} rust={arow[f]!r}")
        # payload: parse the Rust text and compare values bit-wise
        rust_payload = json.loads(arow["payload"])
        compare_value(f"row {i}.payload", orow["payload"], rust_payload)
    return art.row_count


def fingerprint_of(path) -> str:
    """SHA-1 (hex) over the raw artifact bytes (G4 byte-stability)."""
    return artifact_fingerprint(path)


def run_features(binary: Path, tape_path: Path, out_dir: Path, universe,
                 history_depth: int = 32, threads: int = 1, tier: str = "VALUES"):
    """Invoke `v8-core features`; returns (summary, per-symbol artifact dict)."""
    request = {
        "tape_path": str(tape_path),
        "out_dir": str(out_dir),
        "universe": list(universe),
        "base_interval": "1h",
        "history_depth": history_depth,
        "threads": threads,
        "engine": "cpu",
        "tier": tier,
    }
    req_path = write_request_file(request, out_dir)
    proc = subprocess.run([str(binary), "features", str(req_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"features failed (rc={proc.returncode}): {proc.stderr}")
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    artifacts = {}
    for a in summary["artifacts"]:
        artifacts[a["symbol"]] = Path(a["artifact"])
    return summary, artifacts


def load_real_tape(name: str, limit: int | None = None):
    """Load a real verified tape from research/tape/ as parsed dicts."""
    path = REPO_ROOT / "research" / "tape" / name / "tape.jsonl"
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows
