"""S4 real-tape coverage — multi-symbol evaluate parity (issue #106).

The candidate/cube parity fixtures are single-symbol synthetic tapes; the
certified real tapes (btcusdt-1h-12m, multi-1h-4y) were only exercised at
S0/S1. This fixture runs the S4 evaluate-check over a LIMITED slice of the
real multi-symbol tape (multi-1h-4y) and asserts bit-identical decisions
against the Python lab on the same slice, per symbol, for four ported
experts.

Two things this exercises that the synthetic S4 fixtures cannot:

1. D-053 projection + symbol prefix on a NON-SOLUSDT tape (issue #101
   regression): the Rust evaluate-check passes the request symbol through
   the FeatMap, and the Python oracle must be built with `Lab(universe=(sym,))`
   — the lab's MarketState carries the Lab's universe (default 'SOLUSDT'), so
   a plain `Lab(dir)` against a BTCUSDT tape yields an empty view and every
   expert NO_HABITATs. The parity comparison would fail loudly on either side
   hardcoding 'SOLUSDT'.
2. Multi-symbol Dataset ingestion: the Rust side reads the FULL slice (10
   symbols, both kline and funding channels) and picks the per-symbol store
   via the request `universe`, exactly as the S0/S1 real-tape gates do.

The Python oracle is a per-symbol `lab.run` over the symbol's rows only —
lab.run is bar-driven and fails closed on multi-instrument tapes (O-011), so
there is one Lab store per symbol, mirroring build_stores' per-symbol stores.

Comparison follows PARITY_AND_IDENTITY_SPEC §3: every (symbol, bar, expert)
decision/applicability must match exactly, and on CANDIDATE bars the draft
(direction, birth_time), the risk_geometry (float bit-pattern compare via
compare_value) and the D-026 anchor + setup fingerprint must be bit-identical.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from v8.lab import Lab
from v8.schema import ExperimentManifest, TapeRow

from . import runner
from .runner import ParityFailure, compare_value

REPO_ROOT = runner.REPO_ROOT

# The four ported experts exercised on the real multi-symbol tape. All four
# are PORTED (checked into the binary's registry subcommand); they span the
# pilot trend family and three independent behavior families, and each reads
# the {symbol}.history feature so the projection's history withholding is
# exercised per symbol.
EXPERT_CLASSES = {
    "trend_pullback": "TrendPullbackExpert",
    "volume_climax_reversal": "VolumeClimaxReversalExpert",
    "bollinger_breakout": "BollingerBreakoutExpert",
    "failed_breakout_2b": "FailedBreakout2BExpert",
}
PILOT_EXPERTS = sorted(EXPERT_CLASSES)

# A LIMITED slice of the certified multi-symbol tape keeps the gate fast
# while still covering all ten symbols and both channels (kline + funding).
_TAPE_LIMIT = 2000


def _pilots(expert_ids: list[str]):
    import v8.experts as ex
    return [getattr(ex, EXPERT_CLASSES[eid])() for eid in expert_ids]


def _symbols_with_bars(raw_rows):
    return sorted({r["instrument"] for r in raw_rows
                   if r["channel"] == "kline"
                   and r["payload"].get("closed") is True})


def _run_lab_per_symbol(tmp_path, raw_rows, sym, expert_ids):
    """The Python oracle for one symbol: a fresh Lab over the symbol's rows
    only, with `universe=(sym,)` — the lab's MarketState carries the Lab's
    universe, so a non-SOLUSDT tape must declare it or every view is empty
    (issue #101). Returns (bars, {knowledge_time -> ExpertEvaluation})."""
    rows = [TapeRow(**r) for r in raw_rows if r["instrument"] == sym]
    lab = Lab(tmp_path, universe=(sym,))
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: r.available_time)
    manifest = ExperimentManifest(
        experiment_id="s4-real", code_hash="", data_hash="",
        universe=(sym,), start_ns=bars[0].available_time,
        end_ns=bars[-1].available_time)
    lab.run(manifest, _pilots(expert_ids))
    # evaluations.jsonl: {knowledge_time, expert_id, applicability, decision,
    #                      draft}
    evals = {}
    for line in (tmp_path / "evaluations.jsonl").read_text().splitlines():
        rec = json.loads(line)
        evals[(rec["knowledge_time"], rec["expert_id"])] = rec
    return bars, evals


def _rust_evals(v8_core_binary, tmp_path, tape_path, sym, bars, expert_ids):
    """Batch evaluate-check on the FULL slice tape, one symbol's store via
    `universe`; returns {(expert_id, bar_index): result}."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    cases = [(e, i) for i in range(len(bars)) for e in expert_ids]
    req = {"tape_path": str(tape_path), "universe": [sym],
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


def _assert_candidate_parity(sym, bar_idx, eid, py, rust, checked):
    """Bit-level parity of one CANDIDATE bar's draft and identity."""
    assert rust["decision"] == "CANDIDATE", f"{sym} {eid} bar {bar_idx}"
    pd, rd = py["draft"], rust["draft"]
    assert rd["direction"] == pd["direction"], (
        f"{sym} {eid} bar {bar_idx}: direction py={pd['direction']} rust={rd['direction']}")
    assert rd["birth_time"] == pd["birth_time"], (
        f"{sym} {eid} bar {bar_idx}: birth_time")
    compare_value(f"{sym} {eid} bar {bar_idx} risk_geometry",
                  pd["risk_geometry"], rd["risk_geometry"])
    assert rust["setup_anchor_event_id"] == pd.get("setup_anchor_event_id"), (
        f"{sym} {eid} bar {bar_idx}: anchor py={pd.get('setup_anchor_event_id')} "
        f"rust={rust['setup_anchor_event_id']}")
    assert rust["setup_fingerprint"] == pd.get("setup_fingerprint"), (
        f"{sym} {eid} bar {bar_idx}: fingerprint py={pd.get('setup_fingerprint')} "
        f"rust={rust['setup_fingerprint']}")
    return checked + 1


def test_s4_decisions_match_python_on_multi_symbol_real_tape(
        v8_core_binary, tmp_path):
    """The D-053 projection + symbol prefix on a NON-SOLUSDT real tape
    (issue #101 regression): every (symbol, bar, expert) decision matches the
    Python lab bit-for-bit."""
    raw = runner.load_real_tape("multi-1h-4y", limit=_TAPE_LIMIT)
    symbols = _symbols_with_bars(raw)
    assert len(symbols) > 1, "fixture must be multi-symbol"
    assert any(s != "SOLUSDT" for s in symbols), (
        "fixture must exercise a non-SOLUSDT symbol (issue #101)")
    assert any(r["channel"] == "funding" for r in raw), (
        "fixture must carry funding rows")
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape_path = runner.write_tape(raw, tmp_path / "tape.jsonl")

    total_candidates = 0
    total_checked = 0
    for sym in symbols:
        bars, evals = _run_lab_per_symbol(tmp_path / f"lab-{sym}", raw, sym,
                                          PILOT_EXPERTS)
        rust_all = _rust_evals(v8_core_binary, tmp_path / f"rust-{sym}",
                               tape_path, sym, bars, PILOT_EXPERTS)
        for bar_idx, bar in enumerate(bars):
            t_ns = bar.available_time
            for eid in PILOT_EXPERTS:
                py = evals.get((t_ns, eid))
                assert py is not None, f"{sym} {eid} bar {bar_idx}: no oracle eval"
                rust = rust_all[(eid, bar_idx)]
                assert rust["decision"] == py["decision"], (
                    f"{sym} {eid} bar {bar_idx}: decision "
                    f"py={py['decision']} rust={rust['decision']}")
                assert rust["applicability"] == py["applicability"], (
                    f"{sym} {eid} bar {bar_idx}: applicability "
                    f"py={py['applicability']} rust={rust['applicability']}")
                if py["decision"] == "CANDIDATE":
                    total_candidates += 1
                    total_checked = _assert_candidate_parity(
                        sym, bar_idx, eid, py, rust, total_checked)
    assert total_checked > 0, "no candidate bars on the real tape slice"
    assert total_candidates > 0, "no candidate bars on the real tape slice"
