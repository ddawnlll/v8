"""S2 gate — Predicate IR + ReplayKernel (COMPUTE_CORE_SPEC §8).

Gate: outcome parity on the V8.0 candidate population, plus the predicate
equivalence gates of PREDICATE_IR_SPEC §6:

- E1 differential grid: compiled predicate == Python still_valid on every
  generated (direction, geometry, feature-value) input, present/absent/None
  for every operand;
- E2 absence handling exercised explicitly (missing, None, present);
- E3 both directions, including the boundary where the frozen ref equals the
  live value;
- E4 replay parity on the V8.0 candidate population: endpoint, net_r, horizon,
  label_status bit-identical (same exit policy);
- E5 the eleven-name vocabulary is closed.
"""
from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from v8.experts import __all__ as EXPERT_ALL
from v8.lab import Lab
from v8.marketstate import (HISTORY_DEPTH_DEFAULT, build_bar_series,
                            build_state)
from v8.schema import (CandidateDraft, ExperimentManifest, FeatureValue,
                       MarketState, TapeRow)
from v8.simulator import CanonicalSimulator
from v8.synth import make_synthetic_tape

from tools import regret as regret_tools
from tools.predicate_ir import emit, predicate_for

from . import runner
from .runner import ParityFailure

REPO_ROOT = runner.REPO_ROOT

VOCABULARY = {"close", "ema_fast", "ema_slow", "rsi14", "stoch_k", "cci20",
              "macd", "prior_high", "history", "window_high_", "window_low_"}


def _experts():
    out = []
    for name in EXPERT_ALL:
        if name == "Expert":
            continue
        out.append(getattr(__import__("v8.experts", fromlist=[name]), name)())
    return out


# ---------------------------------------------------------------------------
# E1..E3: the compiled predicate must equal the Python still_valid
# ---------------------------------------------------------------------------

def _ir_surface(ir, geom_keys, live_names, window_names, history_needed):
    """Collect the geometry keys and live features a predicate reads."""
    if isinstance(ir, dict):
        t = ir.get("type")
        if t == "ref":
            geom_keys.add(ir["key"])
        elif t == "ref_dir":
            geom_keys.add(ir["long_key"])
            geom_keys.add(ir["short_key"])
        elif t == "live":
            live_names.add(ir["name"])
        elif t == "live_window_dir":
            window_names.update([ir["long"], ir["short"]])
        elif t == "window_agg":
            history_needed[0] = True
        elif t == "window_agg_dir":
            history_needed[0] = True
        elif t == "dispatch":
            for case in ir["cases"]:
                geom_keys.add(case["key"])
                _ir_surface(case["rule"], geom_keys, live_names, window_names, history_needed)
            _ir_surface(ir["default"], geom_keys, live_names, window_names, history_needed)
        else:
            for v in ir.values():
                _ir_surface(v, geom_keys, live_names, window_names, history_needed)
    elif isinstance(ir, list):
        for v in ir:
            _ir_surface(v, geom_keys, live_names, window_names, history_needed)


def _grid(expert, ir):
    """Generate (python_input, rust_input) grid points for one expert."""
    geom_keys, live_names, window_names = set(), set(), set()
    history_needed = [False]
    _ir_surface(ir, geom_keys, live_names, window_names, history_needed)

    sym = "SOLUSDT"
    ref_val = 100.0
    typical = {"close": 101.0, "ema_fast": 101.0, "ema_slow": 100.0,
               "rsi14": 50.0, "stoch_k": 50.0, "cci20": 0.0, "macd": 0.5,
               "prior_high": 102.0}
    geometry_bases = []

    def geom_with(variant_extra=None, absent=()):
        g = {k: ref_val for k in sorted(geom_keys)}
        for k in absent:
            g.pop(k, None)
        if variant_extra:
            g.update(variant_extra)
        return g

    geometry_bases.append(geom_with())
    for k in sorted(geom_keys):
        geometry_bases.append(geom_with(absent=[k]))
    # variant-dispatch experts
    if "variant" in geom_keys:
        for v in ("a", "b", "c"):
            geometry_bases.append(geom_with(variant_extra={"variant": v}))
    if "channel_n" in geom_keys:
        geometry_bases.append(geom_with(variant_extra={"channel_n": 20}))

    def live_with(present=None, none=()):
        live = {n: typical.get(n, 50.0) for n in sorted(live_names)
                if n in typical or True}
        if present is not None:
            live.update(present)
        for n in none:
            live.pop(n, None)
        return live

    live_bases = [live_with()]
    for n in sorted(live_names):
        live_bases.append(live_with(none=[n]))

    def history_grid():
        if not history_needed[0]:
            return [None]
        # a 28-bar window with high/low extremes the aggregates can discriminate
        rows = []
        for i in range(28):
            rows.append([100.0 + i * 0.1, 101.0 + i * 0.1, 99.0 + i * 0.1,
                         100.5 + i * 0.1, 0.0, 0.0])
        return [rows, None]

    points = []
    for direction in ("LONG", "SHORT"):
        for g in geometry_bases:
            for live in live_bases:
                for hist in history_grid():
                    py_live = dict(live)
                    if hist is not None:
                        py_live["history"] = tuple(
                            (f"e{i}", *row) for i, row in enumerate(hist))
                    points.append({
                        "direction": direction,
                        "geometry": g,
                        "live": py_live,
                        "history": hist,
                    })
    # boundary: live value equals the frozen ref (E3)
    if "close" in live_names:
        for direction in ("LONG", "SHORT"):
            for g in geometry_bases:
                for live in live_bases:
                    live2 = dict(live)
                    live2["close"] = ref_val
                    points.append({"direction": direction, "geometry": g,
                                   "live": live2, "history": None})
    return points


def _py_eval(expert, sym, direction, geometry, live):
    features = {}
    for name, val in live.items():
        if name == "history" and isinstance(val, tuple):
            features[f"{sym}.{name}"] = FeatureValue(
                f"{sym}.{name}", val, "history", "v2", 0, quality="COMPLETE")
            continue
        fv_val = None if val is None else float(val)
        features[f"{sym}.{name}"] = FeatureValue(
            f"{sym}.{name}", fv_val, "float", "v1", 0,
            quality="COMPLETE" if fv_val is not None else "DEGRADED")
    state = MarketState(state_id="x", as_of=0, universe=(sym,),
                        features=features, lineage_hash="x")
    draft = CandidateDraft(expert_id=expert.expert_id, expert_version=expert.version,
                           instrument=sym, direction=direction,
                           setup_fingerprint="x", risk_geometry=dict(geometry),
                           birth_time=0)
    return bool(expert.still_valid(state, draft))


def _rust_eval(binary, ir, rust_inputs):
    """Batch predicate-check; returns a list of bools aligned with rust_inputs."""
    cases = {"cases": rust_inputs}
    import tempfile
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
        return [line.strip() == "true" for line in proc.stdout.strip().splitlines()]


def test_e1_e2_e3_compiled_predicates_match_still_valid(v8_core_binary):
    total_points = 0
    for expert in _experts():
        ir = predicate_for(expert)
        points = _grid(expert, ir)
        rust_inputs = []
        expected = []
        for p in points:
            rust_inputs.append({
                "direction": p["direction"],
                "geometry": p["geometry"],
                "live": {k: v for k, v in p["live"].items()
                         if k != "history" and v is not None},
                "history": p["history"],
            })
            expected.append(_py_eval(expert, "SOLUSDT", p["direction"],
                                     p["geometry"], p["live"]))
        got = _rust_eval(v8_core_binary, ir, rust_inputs)
        assert len(got) == len(expected), f"{expert.expert_id}: {len(got)} vs {len(expected)}"
        for i, (e, g) in enumerate(zip(expected, got)):
            if e != g:
                raise ParityFailure(
                    f"{expert.expert_id} point {i}: python={e} rust={g}\n"
                    f"  inputs={json.dumps(rust_inputs[i])[:200]}")
        total_points += len(points)
    assert total_points > 500, f"grid too small: {total_points}"


def test_e5_vocabulary_closed():
    for expert in _experts():
        ir = predicate_for(expert)
        live_names, window_names, hist = set(), set(), [False]
        _ir_surface(ir, set(), live_names, window_names, hist)
        for n in live_names:
            assert n in VOCABULARY, f"{expert.expert_id}: {n} outside vocabulary"
        for n in window_names:
            assert n in {"window_high_", "window_low_", "window_high", "window_low"}, \
                f"{expert.expert_id}: {n}"
        if expert.expert_id == "ichimoku_cloud":
            assert hist[0], "ichimoku_cloud must compile to a history aggregate"


# ---------------------------------------------------------------------------
# E4: replay parity on the V8.0 candidate population
# ---------------------------------------------------------------------------

def _lab_population(tmp_path, rows, experts):
    lab = Lab(tmp_path)
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: (r.event_time, r.available_time, r.venue_sequence))
    times = [b.available_time for b in bars]
    manifest = ExperimentManifest(experiment_id="s2", code_hash="", data_hash="",
                                  universe=tuple(sorted({b.instrument for b in bars})),
                                  start_ns=times[0], end_ns=times[-1])
    lab.run(manifest, experts)
    return lab, bars, times


def _snapshots_with_entry(lab, bars, times):
    store = regret_tools.load_store(lab.dir)
    snapshots = regret_tools.build_snapshots(store)
    idx_by_time = {t: i for i, t in enumerate(times)}
    out = []
    for snap in snapshots:
        if snap.binding_status != "BOUND" or snap.entry_bar_available_time is None:
            continue
        i = idx_by_time.get(snap.entry_bar_available_time)
        if i is None:
            continue
        out.append((snap, i))
    return out


def _python_oracle_outcome(expert, draft, bars, times, entry_idx):
    """sim.run with the Python still_valid closure — the E4 reference."""
    sim = CanonicalSimulator()
    # build the state at each stepped clock for the thesis closure
    series = build_bar_series(
        [b for b in bars if b.instrument == draft.instrument],
        [b for b in bars if b.instrument == draft.instrument],
        [], [])
    states = {}
    for i in range(entry_idx, len(bars)):
        states[times[i]] = build_state(
            bars, times[i], (draft.instrument,), "v1", HISTORY_DEPTH_DEFAULT,
            series={draft.instrument: series})

    def thesis_ok(t_ns, _payload):
        st = states.get(t_ns)
        if st is None:
            return True
        return bool(expert.still_valid(st, draft))

    tail = [b.payload for b in bars[entry_idx:]]
    return sim.run(draft, tail, times=times[entry_idx:], thesis_valid=thesis_ok)


def test_e4_replay_parity_on_candidate_population(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=7, n_bars=400, continuous=True)
    experts = _experts()
    lab, bars, times = _lab_population(tmp_path, rows, experts)
    seen = 0
    for snap, entry_idx in _snapshots_with_entry(lab, bars, times):
        owner_cls = regret_tools.EXPERT_REGISTRY.get(snap.expert_id)
        if owner_cls is None:
            continue
        owner = owner_cls()
        draft = CandidateDraft(**snap.raw_draft)
        py_out = _python_oracle_outcome(owner, draft, bars, times, entry_idx)

        # Rust kernel with the compiled predicate
        ir = predicate_for(owner)
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tape = runner.write_tape(bars, Path(td) / "tape.jsonl")
            req = {
                "tape_path": str(tape),
                "out_dir": str(Path(td) / "out"),
                "manifest": {"round_trip_cost_r": 0.07, "funding_rate_r": 0.0,
                             "funding_hours": 8, "fill_policy": "FILL_AT_BAR_CLOSE"},
                "candidates": [{
                    "symbol": draft.instrument,
                    "direction": draft.direction,
                    "birth_time": draft.birth_time,
                    "geometry": dict(draft.risk_geometry),
                    "entry_bar_index": entry_idx,
                    "window_end": len(bars),
                    "predicate_ir": ir,
                }],
            }
            req_path = Path(td) / "req.json"
            req_path.write_text(json.dumps(req))
            proc = subprocess.run([str(v8_core_binary), "replay", str(req_path)],
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                raise ParityFailure(f"replay failed: {proc.stderr}")
            res = json.loads(proc.stdout.strip().splitlines()[-1])["results"][0]

        assert res["endpoint"] == py_out.endpoint, snap.candidate_id
        assert res["label_status"] == py_out.label_status, snap.candidate_id
        assert res["horizon_bars"] == py_out.horizon_bars, snap.candidate_id
        assert res["ambiguous_bars"] == py_out.ambiguous_bars, snap.candidate_id
        for f in ("net_r", "mae_r", "mfe_r", "entry_price", "risk_unit_price",
                  "market_move_r"):
            if struct.pack("<d", res[f]) != struct.pack("<d", getattr(py_out, f)):
                raise ParityFailure(
                    f"{snap.candidate_id} {f}: py={getattr(py_out, f)!r} "
                    f"rust={res[f]!r}")
        seen += 1
    assert seen > 0, "fixture produced no BOUND candidates with an entry bar"


# ---------------------------------------------------------------------------
# G4/G5: replay determinism
# ---------------------------------------------------------------------------

def test_replay_two_runs_byte_identical(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=9, n_bars=200, continuous=True)
    labs = []
    for i in range(2):
        l, bars, times = _lab_population(tmp_path / f"lab{i}", rows,
                                         [_experts()[0]])
        labs.append((l, bars, times))
    # run the same single candidate twice
    outs = []
    for (l, bars, times) in labs:
        snaps = _snapshots_with_entry(l, bars, times)
        if not snaps:
            continue
        snap, entry_idx = snaps[0]
        outs.append(_replay_one(v8_core_binary, bars, snap, entry_idx))
    assert len(outs) == 2
    assert outs[0] == outs[1]


def _replay_one(binary, bars, snap, entry_idx):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tape = runner.write_tape(bars, Path(td) / "tape.jsonl")
        req = {
            "tape_path": str(tape),
            "out_dir": str(Path(td) / "out"),
            "manifest": {"round_trip_cost_r": 0.07, "funding_rate_r": 0.0,
                         "funding_hours": 8, "fill_policy": "FILL_AT_BAR_CLOSE"},
            "candidates": [{
                "symbol": snap.instrument,
                "direction": snap.direction,
                "birth_time": snap.birth_time,
                "geometry": dict(snap.risk_geometry),
                "entry_bar_index": entry_idx,
                "window_end": len(bars),
                "predicate_ir": predicate_for(
                    regret_tools.EXPERT_REGISTRY.get(snap.expert_id)()),
            }],
        }
        req_path = Path(td) / "req.json"
        req_path.write_text(json.dumps(req))
        proc = subprocess.run([str(binary), "replay", str(req_path)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise ParityFailure(f"replay failed: {proc.stderr}")
        return json.dumps(json.loads(proc.stdout.strip().splitlines()[-1]),
                          sort_keys=True)


def test_replay_thread_invariance(v8_core_binary, tmp_path):
    """G5: the same replay request at 1 and 8 threads produces identical
    results (scheduling never enters a value)."""
    rows = make_synthetic_tape(seed=41, n_bars=200, continuous=True)
    lab, bars, times = _lab_population(tmp_path / "lab", rows, [_experts()[0]])
    snaps = _snapshots_with_entry(lab, bars, times)
    assert snaps, "fixture produced no candidate"
    snap, entry_idx = snaps[0]
    import tempfile
    outs = []
    for threads in (1, 8):
        with tempfile.TemporaryDirectory() as td:
            tape = runner.write_tape(bars, Path(td) / "tape.jsonl")
            req = {
                "tape_path": str(tape),
                "out_dir": str(Path(td) / "out"),
                "threads": threads,
                "manifest": {"round_trip_cost_r": 0.07, "funding_rate_r": 0.0,
                             "funding_hours": 8, "fill_policy": "FILL_AT_BAR_CLOSE"},
                "candidates": [{
                    "symbol": snap.instrument,
                    "direction": snap.direction,
                    "birth_time": snap.birth_time,
                    "geometry": dict(snap.risk_geometry),
                    "entry_bar_index": entry_idx,
                    "window_end": len(bars),
                    "predicate_ir": predicate_for(
                        regret_tools.EXPERT_REGISTRY.get(snap.expert_id)()),
                }],
            }
            req_path = Path(td) / "req.json"
            req_path.write_text(json.dumps(req))
            proc = subprocess.run([str(v8_core_binary), "replay", str(req_path)],
                                  capture_output=True, text=True)
            assert proc.returncode == 0, proc.stderr
            outs.append(json.loads(proc.stdout.strip().splitlines()[-1])["results"][0])
    assert outs[0] == outs[1]


def test_g6_replay_fails_closed(v8_core_binary, tmp_path):
    """A degenerate geometry (non-positive target_r) must fail closed in both
    the Python oracle and the compute plane."""
    rows = make_synthetic_tape(seed=13, n_bars=60)
    bars = sorted([r for r in rows if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: r.available_time)
    draft = CandidateDraft(expert_id="t", expert_version="v1", instrument="SOLUSDT",
                           direction="LONG", setup_fingerprint="x",
                           risk_geometry={"target_r": -1.0, "stop_r": 1.0,
                                          "expiry_bars": 8, "atr_ref": 10.0},
                           birth_time=0)
    py_raises = False
    try:
        CanonicalSimulator().run(draft, [b.payload for b in bars])
    except ValueError:
        py_raises = True
    assert py_raises, "oracle did NOT fail closed on degenerate geometry"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tape = runner.write_tape(bars, Path(td) / "tape.jsonl")
        req = {
            "tape_path": str(tape),
            "out_dir": str(Path(td) / "out"),
            "manifest": {},
            "candidates": [{
                "symbol": "SOLUSDT", "direction": "LONG", "birth_time": 0,
                "geometry": dict(draft.risk_geometry),
                "entry_bar_index": 0, "window_end": len(bars),
            }],
        }
        req_path = Path(td) / "req.json"
        req_path.write_text(json.dumps(req))
        proc = subprocess.run([str(v8_core_binary), "replay", str(req_path)],
                              capture_output=True, text=True)
        assert proc.returncode != 0, "compute plane did NOT fail closed"
