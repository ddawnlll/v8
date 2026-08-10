"""S0 gate — parity harness + Dataset ingest (COMPUTE_CORE_SPEC §8).

Gate: the tape round-trips and the three clocks (event / available / ingested)
are preserved, on every row of every fixture (PARITY_AND_IDENTITY_SPEC §5):

- G1  value-level bit parity on every emitted record
- G2  every bar/row, not a sample
- G3  at least one synthetic fixture and one real verified tape
- G4  two Rust runs of the same request are byte-identical
- G5  values identical across thread count
- G6  failure modes agree (fail-closed inputs classify identically)
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from v8.lab import Lab
from v8.schema import TapeRow
from v8.synth import make_synthetic_tape

from . import runner
from .runner import compare_artifact_to_oracle, oracle_rows_from_tape, run_ingest

REPO_ROOT = runner.REPO_ROOT

# Float *rendering* differs across runtimes (PERFORMANCE_AUDIT_V82 §8: 7 of 8
# values render differently between CPython and Rust) — the audit exists
# precisely because this is not portable. G6 compares *classification*, so the
# error-message comparison normalizes numeric tokens to a placeholder; the
# category and the row identity must match exactly.
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _classify(msg: str) -> str:
    return _NUM.sub("N", msg)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ingest(v8_core_binary, tmp_path, rows, threads=1, tier="VALUES"):
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    out = tmp_path / "out"
    summary, artifact, _ = run_ingest(v8_core_binary, tape, out,
                                      threads=threads, tier=tier)
    return tape, artifact, summary


def _expect_fail_closed(v8_core_binary, tmp_path, rows):
    """G6: an input the oracle refuses must be refused by the compute plane
    with the same classification. Returns the shared classification message."""
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")

    # Python oracle side: Lab.ingest raises ValueError with the classification.
    py_msg = None
    lab = Lab(tmp_path / "pylab")
    try:
        lab.ingest([TapeRow(**r) for r in runner.tape_dicts(tape)])
    except ValueError as exc:
        py_msg = str(exc)
    assert py_msg is not None, "oracle did NOT fail closed — test fixture is wrong"

    # Rust side: the binary must exit non-zero with the same message.
    out = tmp_path / "rustout"
    req_path = runner.write_request_file(runner.build_request(tape, out), out)
    proc = subprocess.run([str(v8_core_binary), "ingest", str(req_path)],
                          capture_output=True, text=True)
    assert proc.returncode != 0, "compute plane did NOT fail closed"
    assert proc.stderr.startswith("error: "), proc.stderr
    rust_msg = proc.stderr[len("error: "):].strip()
    assert _classify(rust_msg) == _classify(py_msg), (
        f"classification mismatch:\n  oracle: {py_msg}\n  compute: {rust_msg}")
    return py_msg


# ---------------------------------------------------------------------------
# G1 + G2 + G3: synthetic fixtures, every row
# ---------------------------------------------------------------------------

def test_synthetic_golden_tape_every_row(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=7, n_bars=160)
    tape, artifact, _ = _ingest(v8_core_binary, tmp_path, rows)
    n = compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape))
    assert n == 160, "every synthetic row must be compared"


def test_synthetic_continuous_tape_every_row(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=11, n_bars=320, continuous=True)
    tape, artifact, _ = _ingest(v8_core_binary, tmp_path, rows)
    n = compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape))
    assert n == 320


def test_synthetic_multiple_seeds(v8_core_binary, tmp_path):
    for seed in (1, 13, 42):
        rows = make_synthetic_tape(seed=seed, n_bars=90)
        tape, artifact, _ = _ingest(v8_core_binary, tmp_path / f"s{seed}", rows)
        n = compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape))
        assert n == 90


def test_degenerate_short_tape_single_bar(v8_core_binary, tmp_path):
    # One closed bar: warmup-absence territory; must still round-trip.
    rows = make_synthetic_tape(seed=3, n_bars=1)
    tape, artifact, _ = _ingest(v8_core_binary, tmp_path, rows)
    n = compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape))
    assert n == 1


def test_degenerate_empty_tape(v8_core_binary, tmp_path):
    rows = []
    tape, artifact, summary = _ingest(v8_core_binary, tmp_path, rows)
    assert summary["rows"] == 0
    assert compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape)) == 0


# ---------------------------------------------------------------------------
# G3: real verified tapes
# ---------------------------------------------------------------------------

def test_real_btcusdt_dev_tape(v8_core_binary, tmp_path):
    # The certified single-symbol dev tape (D-041): 9,948 rows incl. funding.
    raw = runner.load_real_tape("btcusdt-1h-12m")
    rows = [TapeRow(**r) for r in raw]
    tape, artifact, _ = _ingest(v8_core_binary, tmp_path, rows)
    n = compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape))
    assert n == len(rows), "every real-tape row must be compared"


def test_real_multi_symbol_tape(v8_core_binary, tmp_path):
    # The certified multi-symbol dataset (multi-1h-4y): a trimmed slice keeps
    # the gate fast while still covering several symbols and both channels.
    raw = runner.load_real_tape("multi-1h-4y", limit=25_000)
    rows = [TapeRow(**r) for r in raw]
    symbols = {r.instrument for r in rows}
    assert len(symbols) > 1, "fixture must be multi-symbol"
    assert any(r.channel == "kline" for r in rows), "fixture must carry klines"
    assert any(r.channel == "funding" for r in rows), "fixture must carry funding"
    tape, artifact, _ = _ingest(v8_core_binary, tmp_path, rows)
    n = compare_artifact_to_oracle(artifact, oracle_rows_from_tape(tape))
    assert n == len(rows)


# ---------------------------------------------------------------------------
# G4: two Rust runs of the same request are byte-identical
# ---------------------------------------------------------------------------

def test_two_runs_byte_identical(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=19, n_bars=240, continuous=True)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _, art1, _ = run_ingest(v8_core_binary, tape, tmp_path / "out1")
    _, art2, _ = run_ingest(v8_core_binary, tape, tmp_path / "out2")
    assert art1.read_bytes() == art2.read_bytes(), "G4: two runs must be byte-identical"
    assert runner.fingerprint_of(art1) == runner.fingerprint_of(art2)


# ---------------------------------------------------------------------------
# G5: thread-count invariance
# ---------------------------------------------------------------------------

def test_thread_count_invariance(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=23, n_bars=180)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _, art1, _ = run_ingest(v8_core_binary, tape, tmp_path / "out1", threads=1)
    _, art8, _ = run_ingest(v8_core_binary, tape, tmp_path / "out8", threads=8)
    assert art1.read_bytes() == art8.read_bytes(), "G5: thread count must not change bytes"


# ---------------------------------------------------------------------------
# G6: fail-closed classifications agree
# ---------------------------------------------------------------------------

def _bad_row(channel, **payload_overrides):
    base = {
        "source": "binance-um",
        "channel": channel,
        "instrument": "SOLUSDT",
        "event_time": 1_000_000_000,
        "available_time": 2_000_000_000,
        "ingested_time": 3_000_000_000,
        "venue_sequence": 1,
        "event_id": "bad:1",
    }
    if channel == "kline":
        base["payload"] = {"open": 100.0, "high": 101.0, "low": 99.0,
                           "close": 100.5, "volume": 1.0, "closed": True}
    else:
        base["payload"] = {"funding_rate": 0.0001}
    base["payload"].update(payload_overrides)
    return base


def test_fail_closed_ohlc_invariant(v8_core_binary, tmp_path):
    # high < max(open, close) — an impossible bar.
    _expect_fail_closed(v8_core_binary, tmp_path, [_bad_row("kline", high=99.0)])


def test_fail_closed_non_positive_ohlc(v8_core_binary, tmp_path):
    _expect_fail_closed(v8_core_binary, tmp_path, [_bad_row("kline", open=0.0)])


def test_fail_closed_missing_ohlc_key(v8_core_binary, tmp_path):
    _expect_fail_closed(v8_core_binary, tmp_path, [_bad_row("kline", open=None)])


def test_fail_closed_negative_volume(v8_core_binary, tmp_path):
    _expect_fail_closed(v8_core_binary, tmp_path, [_bad_row("kline", volume=-1.0)])


def test_fail_closed_implausible_funding_rate(v8_core_binary, tmp_path):
    _expect_fail_closed(v8_core_binary, tmp_path, [_bad_row("funding", funding_rate=0.5)])


def test_fail_closed_missing_funding_rate(v8_core_binary, tmp_path):
    _expect_fail_closed(v8_core_binary, tmp_path, [_bad_row("funding", funding_rate=None)])


def test_fail_closed_non_finite_ohlc(v8_core_binary, tmp_path):
    # json.dumps writes NaN as a bare literal (Python json is lenient); the
    # lenient parser must classify it "non-finite OHLC" exactly as the oracle.
    rows = [_bad_row("kline")]
    tape_path = tmp_path / "nan_tape.jsonl"
    with open(tape_path, "w") as fh:
        fh.write(json.dumps(rows[0]).replace("100.5", "NaN") + "\n")
    py_msg = None
    lab = Lab(tmp_path / "pylab")
    try:
        lab.ingest([TapeRow(**r) for r in runner.tape_dicts(tape_path)])
    except ValueError as exc:
        py_msg = str(exc)
    assert py_msg and "non-finite" in py_msg, py_msg
    out = tmp_path / "rustout"
    req_path = runner.write_request_file(runner.build_request(tape_path, out), out)
    proc = subprocess.run([str(v8_core_binary), "ingest", str(req_path)],
                          capture_output=True, text=True)
    assert proc.returncode != 0
    assert proc.stderr.startswith("error: ")
    assert _classify(proc.stderr[len("error: "):].strip()) == _classify(py_msg)
