"""S1 gate — FeatureStore + StateView (COMPUTE_CORE_SPEC §8).

Gate: value-level parity on EVERY bar, EVERY feature, on the fixture set
(PARITY_AND_IDENTITY_SPEC §5). The oracle is `build_state`'s cached path
(the one the lab uses, pinned byte-identical to the uncached reference by
tests/test_state_cache_identity.py).

Parity compares the non-hash FeatureValue fields: value, dtype,
feature_version, max_input_available_time, quality, null_reason, group.
Hashes (input_lineage_hash, lineage_hash, state_id) are excluded by §3 but
the V8.2 identities are exercised separately (mutation test).
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.v82_reader import read as read_artifact

from v8.marketstate import (HISTORY_DEPTH_DEFAULT, build_bar_series,
                            build_state)
from v8.schema import FEATURE_TO_GROUP, TapeRow
from v8.synth import make_synthetic_tape

from . import runner
from .runner import ParityFailure, compare_value

REPO_ROOT = runner.REPO_ROOT

# The declared feature vocabulary (FEATURE_GROUPS in schema.py) — the parity
# comparison is only sound over one set of names.
_FEATURE_NAMES = sorted(FEATURE_TO_GROUP.keys())
assert len(_FEATURE_NAMES) == 77, len(_FEATURE_NAMES)


# ---------------------------------------------------------------------------
# oracle helpers
# ---------------------------------------------------------------------------

def _build_oracle(rows, sym):
    """The per-symbol BarSeries, exactly as the lab builds it (with the
    kline==closed aliasing build_bar_series performs)."""
    klines = [r for r in rows if r.instrument == sym and r.channel == "kline"]
    closed = [b for b in klines if b.payload.get("closed") is True]
    funding = [r for r in rows if r.instrument == sym and r.channel == "funding"]
    oi = [r for r in rows if r.instrument == sym and r.channel == "open_interest"]
    return build_bar_series(closed, klines, funding, oi)


def _oracle_state(rows, sym, series, as_of):
    """The Python state at one decision clock (cached path, single symbol)."""
    return build_state(rows, as_of, (sym,), "v1", HISTORY_DEPTH_DEFAULT,
                       series={sym: series})


def _bars_of(rows, sym):
    """Closed kline bars in available order — the decision clocks."""
    bars = [r for r in rows
            if r.instrument == sym and r.channel == "kline"
            and r.payload.get("closed") is True]
    bars.sort(key=lambda r: r.available_time)
    return bars


def _compare_state_rows(art, oracle_features_by_bar, sym, state_quality_by_bar):
    """Compare the Rust state artifact rows against the Python oracle."""
    art_rows = list(art.rows())
    n = art.row_count
    if n != len(oracle_features_by_bar):
        raise ParityFailure(f"bar count mismatch: artifact {n} vs oracle {len(oracle_features_by_bar)}")
    checked = 0
    for i in range(n):
        arow = art_rows[i]
        py_feats = oracle_features_by_bar[i]
        py_quality = state_quality_by_bar[i]
        if arow["state_quality"] != py_quality:
            raise ParityFailure(f"bar {i}: state_quality py={py_quality!r} rust={arow['state_quality']!r}")
        for name in _FEATURE_NAMES:
            fv = py_feats.get(f"{sym}.{name}")
            rust_q = arow[f"{name}.quality"]
            if fv is None:
                if rust_q is not None:
                    raise ParityFailure(f"bar {i} feature {name}: absent in oracle, emitted by compute")
                continue
            if rust_q is None:
                raise ParityFailure(f"bar {i} feature {name}: emitted by oracle, absent in compute")
            # value (bit-compared; None-on-both for degraded features)
            if fv.value is None:
                if arow[f"{name}.value"] is not None:
                    raise ParityFailure(f"bar {i} feature {name}: oracle value None, compute {arow[f'{name}.value']!r}")
            else:
                if arow[f"{name}.value"] is None:
                    raise ParityFailure(f"bar {i} feature {name}: compute value absent")
                rust_val = arow[f"{name}.value"]
                if isinstance(rust_val, str):
                    rust_val = json.loads(rust_val)
                compare_value(f"bar {i} {sym}.{name}", fv.value, rust_val)
            # metadata: exact
            if arow[f"{name}.quality"] != fv.quality:
                raise ParityFailure(f"bar {i} {name}: quality py={fv.quality!r} rust={arow[f'{name}.quality']!r}")
            if arow[f"{name}.null_reason"] != (fv.null_reason or None):
                raise ParityFailure(f"bar {i} {name}: null_reason py={fv.null_reason!r} rust={arow[f'{name}.null_reason']!r}")
            if arow[f"{name}.group"] != fv.group:
                raise ParityFailure(f"bar {i} {name}: group py={fv.group!r} rust={arow[f'{name}.group']!r}")
            if arow[f"{name}.version"] != fv.feature_version:
                raise ParityFailure(f"bar {i} {name}: version py={fv.feature_version!r} rust={arow[f'{name}.version']!r}")
            if arow[f"{name}.dtype"] != fv.dtype:
                raise ParityFailure(f"bar {i} {name}: dtype py={fv.dtype!r} rust={arow[f'{name}.dtype']!r}")
            if arow[f"{name}.max_available"] != fv.max_input_available_time:
                raise ParityFailure(
                    f"bar {i} {name}: clock py={fv.max_input_available_time} rust={arow[f'{name}.max_available']}")
            checked += 1
    return checked


def _run_and_compare(v8_core_binary, tmp_path, rows, sym, history_depth=32):
    """Run the compute plane and compare every bar x feature with the oracle.
    Returns the number of (bar, feature) instances the oracle emitted — the
    gate is the per-feature comparison itself, which raises on any mismatch
    and covers every emitted feature on every bar (warmup-absent features are
    compared for absence)."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _summary, artifacts = runner.run_features(v8_core_binary, tape,
                                              tmp_path / "out", [sym],
                                              history_depth=history_depth)
    art = read_artifact(artifacts[sym])
    # oracle
    series = _build_oracle(rows, sym)
    bars = _bars_of(rows, sym)
    feats_by_bar = []
    quality_by_bar = []
    oracle_emitted = 0
    for bar in bars:
        st = _oracle_state(rows, sym, series, bar.available_time)
        feats_by_bar.append(st.features)
        quality_by_bar.append(st.quality)
        oracle_emitted += len(st.features)
    checked = _compare_state_rows(art, feats_by_bar, sym, quality_by_bar)
    assert checked == oracle_emitted, (
        f"compared {checked} but oracle emitted {oracle_emitted}")
    return checked


# ---------------------------------------------------------------------------
# G1 + G2 + G3: synthetic and real fixtures, every bar x every feature
# ---------------------------------------------------------------------------

def test_feature_names_match_oracle_vocabulary(v8_core_binary, tmp_path):
    """The Rust artifact's feature column set must equal the Python declared
    vocabulary, so the S1 comparison runs over one set of names."""
    rows = make_synthetic_tape(seed=5, n_bars=40)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _summary, artifacts = runner.run_features(v8_core_binary, tape,
                                              tmp_path / "out", ["SOLUSDT"])
    art = read_artifact(artifacts["SOLUSDT"])
    rust_names = {c.name[:-len(".value")] for c in art.columns if c.name.endswith(".value")}
    assert rust_names == set(_FEATURE_NAMES), (
        f"vocabulary mismatch: only-in-rust={sorted(rust_names - set(_FEATURE_NAMES))} "
        f"only-in-python={sorted(set(_FEATURE_NAMES) - rust_names)}")


def test_synthetic_golden_tape(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=7, n_bars=160)
    n = _run_and_compare(v8_core_binary, tmp_path, rows, "SOLUSDT")
    assert n > 0


def test_synthetic_continuous_tape(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=11, n_bars=320, continuous=True)
    n = _run_and_compare(v8_core_binary, tmp_path, rows, "SOLUSDT")
    assert n > 0


def test_synthetic_with_funding_channel(v8_core_binary, tmp_path):
    # A tape carrying funding rows exercises the positioning channel.
    rows = make_synthetic_tape(seed=23, n_bars=200, continuous=True)
    # append a funding row before bar 50's clock
    fund = TapeRow(source="binance-um", channel="funding", instrument="SOLUSDT",
                   event_time=rows[50].event_time, available_time=rows[50].available_time,
                   ingested_time=rows[50].available_time,
                   venue_sequence=999999, event_id="SOLUSDT:funding:1",
                   payload={"funding_rate": 0.0001})
    rows.insert(50, fund)
    n = _run_and_compare(v8_core_binary, tmp_path, rows, "SOLUSDT")
    assert n > 0


def test_real_btcusdt_dev_tape(v8_core_binary, tmp_path):
    raw = runner.load_real_tape("btcusdt-1h-12m")
    rows = [TapeRow(**r) for r in raw]
    n = _run_and_compare(v8_core_binary, tmp_path, rows, "BTCUSDT")
    assert n > 0


def test_real_multi_symbol_slice(v8_core_binary, tmp_path):
    raw = runner.load_real_tape("multi-1h-4y", limit=20_000)
    rows = [TapeRow(**r) for r in raw]
    symbols = sorted({r.instrument for r in rows
                      if r.channel == "kline" and r.payload.get("closed")})
    assert len(symbols) >= 2
    total = 0
    for sym in symbols:
        n = _run_and_compare(v8_core_binary, tmp_path / sym, rows, sym)
        total += n
    assert total > 0


# ---------------------------------------------------------------------------
# G4/G5: determinism and thread invariance of the state artifact
# ---------------------------------------------------------------------------

def test_two_runs_byte_identical(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=19, n_bars=240, continuous=True)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _, a1 = runner.run_features(v8_core_binary, tape, tmp_path / "out1", ["SOLUSDT"])
    _, a2 = runner.run_features(v8_core_binary, tape, tmp_path / "out2", ["SOLUSDT"])
    assert a1["SOLUSDT"].read_bytes() == a2["SOLUSDT"].read_bytes()


def test_thread_count_invariance(v8_core_binary, tmp_path):
    rows = make_synthetic_tape(seed=31, n_bars=180)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _, a1 = runner.run_features(v8_core_binary, tape, tmp_path / "out1", ["SOLUSDT"], threads=1)
    _, a8 = runner.run_features(v8_core_binary, tape, tmp_path / "out8", ["SOLUSDT"], threads=8)
    assert a1["SOLUSDT"].read_bytes() == a8["SOLUSDT"].read_bytes()


# ---------------------------------------------------------------------------
# Identity semantics: V8.2 state_id mutation property
# ---------------------------------------------------------------------------

def _state_ids(v8_core_binary, tmp_path, rows, sym):
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape = runner.write_tape(rows, tmp_path / "tape.jsonl")
    _, artifacts = runner.run_features(v8_core_binary, tape, tmp_path / "out", [sym])
    art = read_artifact(artifacts[sym])
    return [r["state_id"] for r in art.rows()], len(list(art.rows()))


def test_state_id_changes_only_for_consuming_states(v8_core_binary, tmp_path):
    """Mutating one OHLC digit changes the V8.2 state_id for every state that
    consumed that bar, and no other (PARITY_AND_IDENTITY_SPEC §7.2)."""
    rows = make_synthetic_tape(seed=7, n_bars=160)
    # Bar 60's close feeds every state t >= 61 (all features consume it via
    # the newest bar) — so states 61..160 change; states 1..60 do not.
    mutant = [TapeRow(**{**r.__dict__, "payload": dict(r.payload)}) for r in rows]
    mutant[60] = TapeRow(**{**mutant[60].__dict__,
                            "payload": {**mutant[60].payload, "close": mutant[60].payload["close"] + 1e-6}})
    ids_a, n_a = _state_ids(v8_core_binary, tmp_path / "a", rows, "SOLUSDT")
    ids_b, n_b = _state_ids(v8_core_binary, tmp_path / "b", mutant, "SOLUSDT")
    assert n_a == n_b == 160
    changed = [i for i in range(160) if ids_a[i] != ids_b[i]]
    assert changed == list(range(60, 160)), (
        f"expected states 60..159 to change, got {changed[:5]}...{changed[-5:] if changed else []}")
