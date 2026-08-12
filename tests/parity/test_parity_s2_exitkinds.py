"""S2 exit-kind coverage — donchian responsive / significant_extreme (issue #103).

The E1 differential grid in test_parity_s2 iterates the exported registry
(`EXPERT_ALL`). The donchian `responsive` (variant e) and `significant_extreme`
(variant f) exit kinds live in module-local subclasses (`DonchianBreakoutE` /
`DonchianBreakoutF` in src/v8/experts/donchian_breakout.py) that the registry
does not export, so `predicate_for` compiles them
(tools/predicate_ir.py `DONCHIAN_EXIT_KIND`) but no equivalence gate exercises
them. This file closes that gap:

1. proves the gap is real — the kinds compile, the registry never exports them;
2. runs the E1-E3 differential grid (PREDICATE_IR_SPEC §6) for both exit kinds
   against the frozen Python `still_valid` via the `predicate-check`
   subcommand, over directions, geometry, present/None/absent close, and
   history windows (underfull, boundary, monotonic, and discriminating);
3. evaluates real donchian candidates produced by a synthetic tape at every
   stepped bar, comparing the compiled predicate to the Python oracle.

PARITY FINDING (verified on this fixture, do not "fix" silently): the compiled
IR for both exit kinds DIFFERS from the Python oracle on discriminating inputs.

- tools/predicate_ir.py lowers the Python window `hist[-(m+1):-1]`
  (m = RESPONSIVE_EXIT_N = 5 / SIGNIFICANT_EXTREME_N = 3 bars, half-open slice
  so m bars) to `window_agg_dir(..., n=m+1, end="EXCLUSIVE")`, which the kernel
  aggregates as `hist[len-1-n : len-1]` = m+1 bars. The extra (older) bar moves
  the band, so a close sitting between the m-band and the (m+1)-band is judged
  valid by the kernel and invalidated by the oracle (or vice versa).
- Python fails OPEN when `len(hist) < m + 1`; the WindowAgg evaluator encodes no
  length guard (it fails open only on an empty slice), so for histories of
  length 2..m the oracle yields True while the kernel evaluates the window.

Both defects surface below: the grid (test 2) and the seed-5/seed-9
synthetic-tape candidates (test 3) produce closes where the two disagree. The
fix is NOT made here (test-only): predicate_ir.py should compile n = m (5 / 3)
and the kernel's WindowAgg should fail open on an underfull window
(len < n+1 for an EXCLUSIVE end) — `window_agg_dir` needs the same underfull
guard `live_window_feature` already has.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from v8.experts import __all__ as EXPERT_ALL
from v8.experts.donchian_breakout import (DonchianBreakoutE,
                                          DonchianBreakoutF)
from v8.marketstate import (HISTORY_DEPTH_DEFAULT, build_bar_series,
                            build_state)
from v8.schema import CandidateDraft, FeatureValue, MarketState
from v8.synth import make_synthetic_tape

from tools.predicate_ir import emit, predicate_for

from . import runner
from .runner import ParityFailure

SYM = "SOLUSDT"

# --- the two module-local exit-kind experts under test ----------------------
EXIT_KIND_EXPERTS = (DonchianBreakoutE(), DonchianBreakoutF())
EXIT_KIND_M = {"responsive": 5, "significant_extreme": 3}
IR_N = {"responsive": 6, "significant_extreme": 4}  # as compiled today


# ---------------------------------------------------------------------------
# oracle + kernel helpers (mirror test_parity_s2)
# ---------------------------------------------------------------------------

def _py_eval(expert, direction, geometry, live, history):
    """The frozen Python still_valid over a hand-built state."""
    features = {}
    for name, val in live.items():
        fv = None if val is None else float(val)
        features[f"{SYM}.{name}"] = FeatureValue(
            f"{SYM}.{name}", fv, "float", "v1", 0,
            quality="COMPLETE" if fv is not None else "DEGRADED")
    if history is not None:
        features[f"{SYM}.history"] = FeatureValue(
            f"{SYM}.history", history, "history", "v2", 0,
            quality="COMPLETE")
    state = MarketState(state_id="x", as_of=0, universe=(SYM,),
                        features=features, lineage_hash="x")
    draft = CandidateDraft(expert_id=expert.expert_id,
                           expert_version=expert.version, instrument=SYM,
                           direction=direction, setup_fingerprint="x",
                           risk_geometry=dict(geometry), birth_time=0)
    return bool(expert.still_valid(state, draft))


def _rust_evals(binary, ir, rust_inputs):
    """Batch predicate-check; one bool per input, aligned with rust_inputs."""
    cases = {"cases": rust_inputs}
    with tempfile.TemporaryDirectory() as td:
        ir_path = Path(td) / "ir.json"
        cases_path = Path(td) / "cases.json"
        ir_path.write_text(emit(ir))
        cases_path.write_text(json.dumps(cases))
        proc = subprocess.run([str(binary), "predicate-check",
                               str(ir_path), str(cases_path)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise ParityFailure(f"predicate-check failed: {proc.stderr}")
        return [line.strip() == "true"
                for line in proc.stdout.strip().splitlines()]


def _rust_input(expert, direction, geometry, live, history):
    return {
        "direction": direction,
        "geometry": geometry,
        "live": {k: v for k, v in live.items() if v is not None},
        "history": history,
    }


# ---------------------------------------------------------------------------
# test 1: the coverage gap of issue #103 is real
# ---------------------------------------------------------------------------

def test_exit_kinds_compile_but_are_not_registry_covered():
    """predicate_for compiles both exit kinds, yet neither class is exported —
    the E1 grid in test_parity_s2 can never exercise them."""
    ir_e = predicate_for(DonchianBreakoutE())
    assert ir_e["rhs"]["type"] == "window_agg_dir"
    assert ir_e["rhs"]["n"] == IR_N["responsive"]
    assert ir_e["rhs"]["end"] == "EXCLUSIVE"
    ir_f = predicate_for(DonchianBreakoutF())
    assert ir_f["rhs"]["type"] == "window_agg_dir"
    assert ir_f["rhs"]["n"] == IR_N["significant_extreme"]
    # The registry (EXPERT_ALL) exports only the base channel-exit class.
    names = {c.__name__ for c in (DonchianBreakoutE, DonchianBreakoutF)}
    assert not names & set(EXPERT_ALL), \
        f"exit-kind classes leaked into the registry: {names & set(EXPERT_ALL)}"


# ---------------------------------------------------------------------------
# test 2: E1-E3 differential grid for both exit kinds
# ---------------------------------------------------------------------------

def _window_rows(n, low=100.0, high=102.0):
    return [[high - 1.0, high, low, low + 0.5, 0.0, 0.0] for _ in range(n)]


def _monotonic_rows(n=10):
    return [[100.0 + i * 0.1, 101.0 + i * 0.1, 99.0 + i * 0.1,
             100.5 + i * 0.1, 0.0, 0.0] for i in range(n)]


def _py_band(expert, direction, rows):
    """The Python oracle's band for a history of 6-float rows, or None when
    the oracle fails open (len < m+1)."""
    m = EXIT_KIND_M[expert.exit_kind]
    if rows is None or len(rows) < m + 1:
        return None
    prev = rows[-(m + 1):-1]
    if direction == "LONG":
        return min(float(r[2]) for r in prev)   # low
    return max(float(r[1]) for r in prev)       # high


def _grid_points(expert):
    """(direction, geometry, live, history, py_history) grid points for one
    exit-kind expert: E2 (present/None/absent close, missing history) and E3
    (both directions, close == band boundary) plus discriminating windows."""
    m = EXIT_KIND_M[expert.exit_kind]
    extra_idx = 10 - m - 2  # the (m+1)-th-oldest bar in a 10-bar window

    # history variants: key -> (rows or None)
    hist_variants = {"none": None, "empty": []}
    for L in range(1, m + 1):               # underfull -> oracle fails open
        hist_variants[f"short_{L}"] = _window_rows(L)
    hist_variants["boundary"] = _window_rows(m + 1)
    hist_variants["normal"] = _monotonic_rows(10)
    # discriminating: the extra bar the kernel aggregates has an outlier
    # extreme, so the kernel band differs from the oracle band.
    disc_long = _monotonic_rows(10)
    disc_long[extra_idx][2] = 80.0                 # low outlier (LONG band)
    hist_variants["disc_long"] = disc_long
    disc_short = _monotonic_rows(10)
    disc_short[extra_idx][1] = 200.0               # high outlier (SHORT band)
    hist_variants["disc_short"] = disc_short

    def closes(direction, rows):
        band = _py_band(expert, direction, rows)
        if band is None:
            return [1.0, 50.0, 150.0]
        out = [band - 5.0, band - 0.5, band, band + 0.5, band + 5.0]
        # gap closes between the kernel's outlier band and the oracle band
        if direction == "LONG":
            out += [81.0, 90.0]
        else:
            out += [150.0, 102.0]
        return sorted(set(out))

    points = []
    for direction in ("LONG", "SHORT"):
        for geometry in ({}, {"channel_n": 20}):
            for name, rows in hist_variants.items():
                py_history = None
                if rows is not None:
                    py_history = tuple((f"e{i}", *r) for i, r in enumerate(rows))
                for close in closes(direction, rows):
                    live = {"close": close}
                    points.append((direction, geometry, live, rows, py_history))
            # E2: close absent / None (oracle and kernel both fail open)
            for live in ({"close": None}, {}):
                points.append((direction, geometry, live, None, None))
    return points


def test_exit_kind_grid_matches_python(v8_core_binary):
    """E1-E3 for the exit kinds: compiled predicate == Python still_valid on
    every generated (direction, geometry, feature, window) input."""
    for expert in EXIT_KIND_EXPERTS:
        ir = predicate_for(expert)
        points = _grid_points(expert)
        rust_inputs = []
        expected = []
        for direction, geometry, live, rows, py_history in points:
            rust_inputs.append(_rust_input(expert, direction, geometry, live,
                                           rows))
            expected.append(_py_eval(expert, direction, geometry, live,
                                     py_history))
        got = _rust_evals(v8_core_binary, ir, rust_inputs)
        assert len(got) == len(expected), \
            f"{expert.variant_id}: {len(got)} vs {len(expected)} results"
        mismatches = []
        for i, (e, g) in enumerate(zip(expected, got)):
            if e != g:
                mismatches.append((i, e, g, rust_inputs[i]))
        if mismatches:
            head = "\n".join(
                f"  point {i}: python={e} rust={g} "
                f"inputs={json.dumps(ri)[:220]}"
                for i, e, g, ri in mismatches[:10])
            raise ParityFailure(
                f"{expert.variant_id} ({expert.exit_kind}): "
                f"{len(mismatches)}/{len(points)} grid points disagree\n"
                f"{head}")


# ---------------------------------------------------------------------------
# test 3: synthetic-tape fixture — real donchian candidates at stepped bars
# ---------------------------------------------------------------------------

# Pinned seeds: seed 5 produces a responsive (e) LONG candidate at bar 32;
# seed 9 a significant_extreme (f) SHORT candidate at bar 30. Both kinds are
# reachable on synthetic tapes for every seed scanned (1..40), so no skip is
# expected; the pins make the fixture deterministic.
FIXTURE_SEEDS = {"responsive": 5, "significant_extreme": 9}


def _fixture_candidate(seed, expert):
    rows = make_synthetic_tape(seed=seed, n_bars=200, continuous=True)
    bars = sorted([r for r in rows if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: (r.available_time, r.venue_sequence))
    times = [b.available_time for b in bars]
    series = build_bar_series(bars, bars, [], [])
    for i in range(21, len(bars)):
        st = build_state(bars, times[i], (SYM,), "v1", HISTORY_DEPTH_DEFAULT,
                         series={SYM: series})
        ev = expert.evaluate(st)
        if ev.applicability == "APPLICABLE" and ev.decision == "CANDIDATE" \
                and ev.draft is not None:
            return ev.draft, i, bars, times, series
    return None, None, bars, times, series


def _stepped_disagreements(v8_core_binary, expert, draft, entry_idx, bars,
                           times, series):
    """Compare the oracle still_valid and the compiled predicate at every
    stepped bar entry+1..entry+expiry (the bars the thesis is consulted on).
    Returns a list of (bar_index, close, python, rust)."""
    ir = predicate_for(expert)
    expiry = int(draft.risk_geometry.get("expiry_bars", 8))
    out = []
    for j in range(entry_idx + 1, min(entry_idx + 1 + expiry, len(bars))):
        st = build_state(bars, times[j], (SYM,), "v1", HISTORY_DEPTH_DEFAULT,
                         series={SYM: series})
        close = st.features[f"{SYM}.close"].value
        hist = st.features[f"{SYM}.history"].value
        py = bool(expert.still_valid(st, draft))
        # identical live values through the kernel's predicate-check
        rust_input = {
            "direction": draft.direction,
            "geometry": dict(draft.risk_geometry),
            "live": {"close": close},
            "history": [[b[1], b[2], b[3], b[4], b[5], b[6]] for b in hist],
        }
        ru = _rust_evals(v8_core_binary, ir, [rust_input])[0]
        if py != ru:
            out.append((j, close, py, ru))
    return out


def test_synthetic_tape_candidate_still_valid_parity(v8_core_binary):
    """A synthetic tape produces a real donchian candidate for each exit kind;
    at every stepped bar the compiled predicate must agree with the Python
    still_valid the oracle evaluated the position under."""
    for expert in EXIT_KIND_EXPERTS:
        seed = FIXTURE_SEEDS[expert.exit_kind]
        draft, entry_idx, bars, times, series = _fixture_candidate(seed, expert)
        if draft is None:
            pytest.skip(f"{expert.variant_id}: no donchian candidate on "
                        f"synthetic tape seed {seed} — exit kind not reachable")
        disagree = _stepped_disagreements(v8_core_binary, expert, draft,
                                          entry_idx, bars, times, series)
        if disagree:
            head = "\n".join(
                f"  bar {j}: close={c:.6f} python={py} rust={ru}"
                for j, c, py, ru in disagree[:10])
            raise ParityFailure(
                f"{expert.variant_id} ({expert.exit_kind}) seed {seed} "
                f"entry {entry_idx} {draft.direction}: "
                f"{len(disagree)} stepped bars disagree (oracle exits where "
                f"the kernel holds, or vice versa)\n{head}")
