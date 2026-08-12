"""FILL_AT_LIMIT fixture parity (issue #104).

FILL_AT_LIMIT is ported in both simulators (src/v8/simulator.py
SUPPORTED_FILL_POLICIES; v8-core/src/simulator.rs FillPolicy::Limit) but no
registered expert declares `limit_price`, so the fill path is unexercised.
This fixture hand-crafts a candidate whose risk_geometry declares
`limit_price` and replays it through both sides under the manifest
`fill_policy: "FILL_AT_LIMIT"`:

- the release binary's `replay` subcommand (candidate batch,
  COMPUTE_CORE_SPEC §4), and
- the Python oracle `CanonicalSimulator.run` with
  `fill_policy='FILL_AT_LIMIT'` (src/v8/simulator.py EXEC-4).

Covered behaviors, mirroring the oracle:
- price touches the limit -> fills at the limit exactly (entry_price == limit);
- price gaps through the limit -> still fills at the limit (conservative limit
  semantics);
- price never reaches the limit -> never enters (EXPIRY / NOT_EXECUTED);
- SHORT mirrors the LONG rules with high >= limit;
- a missing `limit_price` fails closed identically on both sides (G6).

Every compared field is asserted bit-identical (PARITY_AND_IDENTITY_SPEC §3):
the fill outcome is endpoint / label_status / entry_price, and the exit-loop
fields (net_r, mae_r, mfe_r, ...) must match too because the exit policy is
shared. `expiry_bars` is declared large so the kernel read window equals the
tape (`end = min(window_end, start + expiry + 1)`), matching the oracle's
whole-tail fill scan.
"""
from __future__ import annotations

import json
import struct
import subprocess
import tempfile
from pathlib import Path

from v8.schema import CandidateDraft
from v8.simulator import CanonicalSimulator

from . import runner
from .runner import ParityFailure

FIXED_EPOCH_NS = 1_750_000_000_000_000_000
HOUR_NS = 3_600_000_000_000

# Manifest declared for every fixture: flat R cost, no funding settlements
# (funding_hours=100000 => no 8h boundary is ever crossed), and the barrier
# fill policy under test.
MANIFEST = {
    "round_trip_cost_r": 0.07,
    "funding_rate_r": 0.0,
    "funding_hours": 100000,
    "fill_policy": "FILL_AT_LIMIT",
}


def _bar(i: int, o: float, h: float, l: float, c: float) -> dict:
    """One closed kline TapeRow dict (the write_tape round-trip format)."""
    return {
        "source": "binance-um",
        "channel": "kline",
        "instrument": "SOLUSDT",
        "event_time": FIXED_EPOCH_NS + i * HOUR_NS + HOUR_NS - 1_000_000,
        "available_time": FIXED_EPOCH_NS + i * HOUR_NS
                          + HOUR_NS - 1_000_000 + 1_000_000_000,
        "ingested_time": FIXED_EPOCH_NS + i * HOUR_NS + HOUR_NS,
        "venue_sequence": i + 1,
        "event_id": f"b{i + 1}",
        "payload": {"open": o, "high": h, "low": l, "close": c,
                    "volume": 1.0, "closed": True},
    }


def _geometry(limit_price: float) -> dict:
    """The risk_geometry: the declared barrier plus the exit-loop geometry the
    oracle's step() indexes directly (target_r/stop_r/expiry_bars) and the
    R unit (atr_ref)."""
    return {"limit_price": limit_price, "target_r": 1.0, "stop_r": 1.0,
            "expiry_bars": 1000, "atr_ref": 5.0}


def _oracle(direction: str, limit_price: float, rows, entry_idx: int = 0):
    """Python oracle: CanonicalSimulator.run under FILL_AT_LIMIT on the same
    input the compute plane ingests (payloads + available times of the tail)."""
    tail = rows[entry_idx:]
    draft = CandidateDraft(
        expert_id="fill_limit_fixture", expert_version="v1",
        instrument="SOLUSDT", direction=direction, setup_fingerprint="x",
        risk_geometry=_geometry(limit_price), birth_time=0)
    sim = CanonicalSimulator(round_trip_cost_r=0.07, funding_rate_r=0.0,
                             funding_hours=100000, fill_policy="FILL_AT_LIMIT")
    return sim.run(draft, [r["payload"] for r in tail],
                   times=[r["available_time"] for r in tail])


def _rust(v8_core_binary, rows, direction: str, limit_price: float,
          entry_idx: int = 0) -> dict:
    """The `replay` subcommand on the same candidate; returns results[0]."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tape = runner.write_tape(rows, td / "tape.jsonl")
        req = {
            "tape_path": str(tape),
            "out_dir": str(td / "out"),
            "manifest": MANIFEST,
            "candidates": [{
                "symbol": "SOLUSDT",
                "direction": direction,
                "birth_time": 0,
                "geometry": _geometry(limit_price),
                "entry_bar_index": entry_idx,
                "window_end": len(rows),
            }],
        }
        req_path = td / "req.json"
        req_path.write_text(json.dumps(req))
        proc = subprocess.run([str(v8_core_binary), "replay", str(req_path)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise ParityFailure(f"replay failed: {proc.stderr}")
        return json.loads(proc.stdout.strip().splitlines()[-1])["results"][0]


def _assert_fill_parity(tag: str, py, rust: dict) -> None:
    """Bit-compare the full outcome record (fill outcome + shared exit loop)."""
    for f in ("endpoint", "label_status", "horizon_bars",
              "label_available_time", "ambiguous_bars"):
        if getattr(py, f) != rust[f]:
            raise ParityFailure(f"{tag} {f}: py={getattr(py, f)!r} "
                                f"rust={rust[f]!r}")
    for f in ("net_r", "mae_r", "mfe_r", "entry_price", "risk_unit_price",
              "market_move_r"):
        pv, rv = getattr(py, f), rust[f]
        if struct.pack("<d", pv) != struct.pack("<d", rv):
            raise ParityFailure(
                f"{tag} {f}: py={pv!r}({struct.pack('<d', pv).hex()}) "
                f"rust={rv!r}({struct.pack('<d', rv).hex()})")


def _filled_at_limit(py, limit_price: float, tag: str) -> None:
    """A fill means entry_price is the limit exactly and the label is not
    NOT_EXECUTED."""
    if struct.pack("<d", py.entry_price) != struct.pack("<d", limit_price):
        raise ParityFailure(f"{tag}: fill price py={py.entry_price!r} "
                            f"expected the limit {limit_price!r}")
    if py.label_status == "NOT_EXECUTED":
        raise ParityFailure(f"{tag}: expected a fill, got NOT_EXECUTED")


def _not_filled(py, tag: str) -> None:
    """Never-entered convention: EXPIRY / 0.0 / NOT_EXECUTED."""
    if py.endpoint != "EXPIRY" or py.label_status != "NOT_EXECUTED" \
            or py.entry_price != 0.0 or py.net_r != 0.0:
        raise ParityFailure(
            f"{tag}: expected never-entered (EXPIRY/NOT_EXECUTED/0.0), "
            f"got endpoint={py.endpoint!r} label={py.label_status!r} "
            f"entry={py.entry_price!r} net_r={py.net_r!r}")


# ---------------------------------------------------------------------------
# price touches the limit -> fills at the limit exactly
# ---------------------------------------------------------------------------

def test_long_price_touches_limit_fills(v8_core_binary):
    """Bar 0 low == limit (100.0): the resting order fills at the limit on the
    entry bar. Post-fill bars stay flat, so the episode is right-censored at
    the tape end."""
    rows = [_bar(0, 101.0, 103.0, 100.0, 102.0)]
    rows += [_bar(i, 102.0, 102.0, 102.0, 102.0) for i in range(1, 10)]
    limit = 100.0
    py = _oracle("LONG", limit, rows)
    rust = _rust(v8_core_binary, rows, "LONG", limit)
    _filled_at_limit(py, limit, "touch")
    _assert_fill_parity("touch", py, rust)


def test_short_price_touches_limit_fills(v8_core_binary):
    """Bar 0 high == limit (100.0): a SHORT limit fill mirrors LONG (high >=
    limit)."""
    rows = [_bar(0, 99.0, 100.0, 98.0, 99.5)]
    rows += [_bar(i, 99.5, 99.5, 99.5, 99.5) for i in range(1, 10)]
    limit = 100.0
    py = _oracle("SHORT", limit, rows)
    rust = _rust(v8_core_binary, rows, "SHORT", limit)
    _filled_at_limit(py, limit, "short_touch")
    _assert_fill_parity("short_touch", py, rust)


# ---------------------------------------------------------------------------
# price gaps through the limit -> still fills at the limit
# ---------------------------------------------------------------------------

def test_long_price_gaps_through_limit_fills_at_limit(v8_core_binary):
    """Bar 0 gaps below the limit (low 95.0 vs limit 100.0): conservative limit
    semantics — the fill price is the limit exactly, not the gap low."""
    rows = [_bar(0, 101.0, 102.0, 95.0, 96.0)]
    rows += [_bar(i, 102.0, 102.0, 102.0, 102.0) for i in range(1, 10)]
    limit = 100.0
    py = _oracle("LONG", limit, rows)
    rust = _rust(v8_core_binary, rows, "LONG", limit)
    _filled_at_limit(py, limit, "gap")
    if struct.pack("<d", py.entry_price) == struct.pack("<d", 95.0):
        raise ParityFailure("gap: filled at the gap low instead of the limit")
    _assert_fill_parity("gap", py, rust)


def test_short_price_gaps_through_limit_fills_at_limit(v8_core_binary):
    """Bar 0 gaps above the limit (high 101.0 vs limit 100.0): SHORT fills at
    the limit."""
    rows = [_bar(0, 99.0, 101.0, 98.0, 100.5)]
    rows += [_bar(i, 99.0, 99.0, 99.0, 99.0) for i in range(1, 10)]
    limit = 100.0
    py = _oracle("SHORT", limit, rows)
    rust = _rust(v8_core_binary, rows, "SHORT", limit)
    _filled_at_limit(py, limit, "short_gap")
    _assert_fill_parity("short_gap", py, rust)


# ---------------------------------------------------------------------------
# the limit fills on a later bar, not the entry bar (resting order)
# ---------------------------------------------------------------------------

def test_limit_fills_on_later_bar(v8_core_binary):
    """The entry bar starts at index 3; bars 3 and 4 stay above the limit, bar
    5 gaps through it. The order rests until the first bar whose range trades
    through, and the exit loop starts on the bar AFTER the fill bar (the entry
    bar is inspected for a FILL only — SIMULATION_TRUTH_SPEC)."""
    rows = [_bar(i, 105.0, 106.0, 104.0, 105.0) for i in range(3)]
    rows += [_bar(3, 104.0, 104.0, 102.0, 103.0),
             _bar(4, 103.0, 103.0, 102.0, 102.5),
             _bar(5, 101.0, 102.0, 99.5, 100.5)]
    rows += [_bar(i, 102.0, 102.0, 102.0, 102.0) for i in range(6, 12)]
    limit = 100.0
    py = _oracle("LONG", limit, rows, entry_idx=3)
    rust = _rust(v8_core_binary, rows, "LONG", limit, entry_idx=3)
    _filled_at_limit(py, limit, "late_fill")
    _assert_fill_parity("late_fill", py, rust)


# ---------------------------------------------------------------------------
# price never reaches the limit -> the order never enters
# ---------------------------------------------------------------------------

def test_long_price_never_reaches_limit_never_enters(v8_core_binary):
    """The limit (90.0) sits below every bar's low: no bar trades through, so
    the candidate never enters (EXPIRY / 0.0 / NOT_EXECUTED, knowable at the
    tape end)."""
    rows = [_bar(i, 102.0, 103.0, 101.0, 102.0) for i in range(10)]
    limit = 90.0
    py = _oracle("LONG", limit, rows)
    rust = _rust(v8_core_binary, rows, "LONG", limit)
    _not_filled(py, "never_long")
    _assert_fill_parity("never_long", py, rust)


def test_short_price_never_reaches_limit_never_enters(v8_core_binary):
    """The limit (110.0) sits above every bar's high: never fills for a
    SHORT."""
    rows = [_bar(i, 100.0, 102.0, 99.0, 101.0) for i in range(10)]
    limit = 110.0
    py = _oracle("SHORT", limit, rows)
    rust = _rust(v8_core_binary, rows, "SHORT", limit)
    _not_filled(py, "never_short")
    _assert_fill_parity("never_short", py, rust)


# ---------------------------------------------------------------------------
# G6: a missing limit_price fails closed identically
# ---------------------------------------------------------------------------

def test_missing_limit_price_fails_closed(v8_core_binary):
    """FILL_AT_LIMIT with no declared barrier must fail closed on both sides
    (the oracle raises ValueError; the compute plane exits non-zero with the
    same classification text)."""
    rows = [_bar(0, 101.0, 103.0, 100.0, 102.0)]
    rows += [_bar(i, 102.0, 102.0, 102.0, 102.0) for i in range(1, 10)]
    draft = CandidateDraft(
        expert_id="fill_limit_fixture", expert_version="v1",
        instrument="SOLUSDT", direction="LONG", setup_fingerprint="x",
        risk_geometry={"target_r": 1.0, "stop_r": 1.0, "expiry_bars": 1000,
                       "atr_ref": 5.0}, birth_time=0)
    sim = CanonicalSimulator(round_trip_cost_r=0.07, funding_rate_r=0.0,
                             funding_hours=100000, fill_policy="FILL_AT_LIMIT")
    py_raised = False
    try:
        sim.run(draft, [r["payload"] for r in rows],
                times=[r["available_time"] for r in rows])
    except ValueError as e:
        py_raised = "limit_price" in str(e)
    assert py_raised, "oracle did NOT fail closed on a missing limit_price"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tape = runner.write_tape(rows, td / "tape.jsonl")
        req = {
            "tape_path": str(tape),
            "out_dir": str(td / "out"),
            "manifest": MANIFEST,
            "candidates": [{
                "symbol": "SOLUSDT", "direction": "LONG", "birth_time": 0,
                "geometry": {"target_r": 1.0, "stop_r": 1.0,
                             "expiry_bars": 1000, "atr_ref": 5.0},
                "entry_bar_index": 0, "window_end": len(rows),
            }],
        }
        req_path = td / "req.json"
        req_path.write_text(json.dumps(req))
        proc = subprocess.run([str(v8_core_binary), "replay", str(req_path)],
                              capture_output=True, text=True)
        assert proc.returncode != 0, "compute plane did NOT fail closed"
        assert "limit_price" in proc.stderr, proc.stderr
