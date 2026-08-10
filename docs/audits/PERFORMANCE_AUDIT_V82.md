# V8.2 Performance Audit — measured evidence for the compute-core decision

**Status:** PROJECT_EVIDENCE_SUPPORTED for every number in sections 2-8 (each
is real command output from one measurement session); DESIGN_INFERENCE for the
extrapolations in section 9, which are labelled as such inline. This audit
records **what was measured**, not what should be built; the decisions it
supports are D-077 .. D-085 in the register. It adds no economic claim
(`V8_CONSTITUTION` rule 12).

## 1. Why this audit exists

A single evaluation cell — one symbol, one base interval, one year of 1h bars —
took ~26-32 s. The program's own falsification criterion asks whether
evaluation cost still supports controlled iteration at research scale
(100 symbols x 15m..1w). Before choosing a remedy (algorithmic, native,
GPU, or architectural) the cost had to be attributed rather than assumed.

The headline finding is that **the decision-path arithmetic is a minority of
the run**. Roughly half the measured time is data-access waste and audit
plumbing, and the single largest storage cost carries ~2% information.

### 1.1 Measurement environment

| | |
|---|---|
| Platform | macOS arm64 (Darwin 25.1.0) |
| Python | CPython 3.14.0 (`uv`-managed `.venv`) |
| Rust (section 8 only) | rustc 1.96.0-nightly |
| Tape | `synth.make_synthetic_tape(seed=11, n_bars=..., continuous=True)` |
| Universe | `SOLUSDT`, single symbol, 1h base interval |
| Harness | `tools/_perf_probe.py` (scratch profiling harness, not shipped tooling) |
| Expert set | the 27 classes in `_perf_probe.ALL`; the registry holds 28 expert modules (`fib_rsi_bb_confluence`, D-076, is not in the probe list) |

Every figure below is reproducible with the command shown next to it. Numbers
are single-run, not averaged over repetitions; run-to-run variance of ~5% was
observed on the wall-clock totals (16.11 s / 16.9 s / 17.13 s for the same
3-expert 8760-bar configuration across three invocations).

## 2. Wall-clock baseline

```bash
.venv/bin/python tools/_perf_probe.py all   8760    # 27 experts
.venv/bin/python tools/_perf_probe.py pilot 8760    # 3 experts
```

| Configuration | Elapsed | Candidates |
|---|---|---|
| 27 experts, 8760 bars | **32.32 s** | 22,444 |
| 3 experts, 8760 bars | **16.11 s** | 1,837 |

The 24 additional experts add 16.2 s and 20,607 candidates — about **0.79 ms of
marginal cost per candidate**, which covers expert evaluation, lifecycle,
simulation and three ledger appends. A fixed floor of ~14-16 s is present
regardless of expert count.

## 3. Scaling exponent

```bash
for n in 1095 2190 4380 8760; do .venv/bin/python tools/_perf_probe.py pilot $n; done
```

| Bars | Elapsed | Ratio vs previous |
|---|---|---|
| 1,095 | 1.55 s | — |
| 2,190 | 3.28 s | 2.12x |
| 4,380 | 6.89 s | 2.10x |
| 8,760 | 17.13 s | 2.49x |

Doubling the bar count costs more than double at the top of the range. Over the
full 8x span the exponent is ~1.16; over the last doubling alone it is ~1.32.
The pipeline is therefore **super-linear and drifting toward quadratic** as N
grows — consistent with an O(N^2) term that is still small at 1,095 bars and
dominant well before 35,040 (one year of 15m bars).

## 4. Profile attribution

```bash
.venv/bin/python tools/_perf_probe.py profile 8760
```

302,010,172 function calls in 64.658 s (cProfile inflates wall-clock ~2x and
over-weights call-heavy code; ratios are indicative, absolute values are not).
Selected rows, cumulative time:

| Function | ncalls | cumtime |
|---|---|---|
| `lab.run` | 1 | 65.700 |
| `marketstate.build_multi_state` | 8,760 | 19.174 |
| `marketstate.build_state` | 8,760 | 18.467 (tottime 7.428) |
| `schema.record_dict` | 360,253 | 8.503 |
| `json.dumps` | 989,041 | 8.223 |
| `store.append` | 376,890 | 7.623 |
| `schema._asdict_fast` | 13,626,352 / 360,253 | 6.309 |
| `schema.sha1_hex` | 594,629 | 5.927 |
| `store.hash` | **5** | 5.510 |
| `equity.risk_of_ruin` | 1 | 4.967 |
| `builtins.id` | **77,925,592** | 3.668 (tottime) |
| `json.loads` | 385,650 | 3.189 |
| `posix.stat` | 753,791 | 1.872 |
| `TextIOWrapper.flush` | 376,890 | 1.422 |

Three rows are structurally anomalous and are examined below: 77.9M `id()`
calls (section 5), 5 calls to `store.hash` costing 5.5 s (section 7), and
753,791 `stat` calls for 376,890 appends (section 7).

## 5. Finding 1 — an O(N^2) residue inside the cached "fast path"

`src/v8/marketstate.py` builds a row-identity map **per state, per symbol, per
interval**:

```python
id_map = {id(b): i for i, b in enumerate(s.closed)}
```

At 8,760 states over 8,760 rows this is 76.7M dictionary insertions; the
profile's 77,925,592 `id()` calls confirm the arithmetic. Isolated measurement,
without the profiler:

```python
rows = [R() for _ in range(8760)]
for _ in range(8760):
    m = {id(b): i for i, b in enumerate(rows)}
# 4.93 s
```

Measured cost: **4.93 s**. Independently, the state layer in isolation:

```python
# build_bar_series once, then build_multi_state for every bar,
# no persistence, no experts
# 7.74 s for 8,760 states; 74 features per state
```

So roughly **63% of the state-building layer is this one line**. The remaining
~2.8 s covers 8,760 x 74 = 648,240 feature computations, i.e. ~4.3 us per
feature.

The `BarSeries` precompute (D-054) removed the O(N^2) from the *feature*
recurrences but left it in the *lineage* path. The map is a pure function of
`s.closed`, which does not change during a run.

## 6. Finding 2 — the same class of defect on the cube path

`tools/regret.py` builds each Outcome Cube cell from the entire remaining tape:

```python
tail = bars[i:]
...
out = sim.run(draft, [b.payload for b in tail], times=[...], thesis_valid=thesis_ok)
```

Measured at mid-tape (4,380 bars remaining), 2,000 iterations each:

| Operation | Cost per cell |
|---|---|
| `tail` slice + payload/time rebuild | **71.8 us** |
| `sim.run` over a bounded 60-bar window | **6.4 us** |
| `sim.run` over the full 4,380-bar tail | 15.7 us |

A cell whose geometry declares `expiry_bars <= 48` can never read more than
~48 bars, so **the slice is ~11x the arithmetic it feeds**. With
|A(C)| = 11 actions (`NO_TRADE` + the actual action + a 3x3
`target_r` x `expiry_bars` grid, `tools/regret.py:CONTINUOUS_AXIS_GRID`) and
22,444 candidates, one symbol-year is 246,884 cells:

| Path | Per symbol-year |
|---|---|
| As implemented (slice + full-tail run) | 21.6 s |
| Index-bounded window (arithmetic only) | 1.6 s |

## 7. Finding 3 — audit plumbing and per-record I/O

**Ledger volume.** One 8,760-bar, single-symbol, 3-expert run writes:

| File | Size |
|---|---|
| `states.jsonl` | **271.8 MB** |
| `evaluations.jsonl` | 10.5 MB |
| `candidates.jsonl` | 5.0 MB |
| `outcomes.jsonl` | 0.9 MB |
| `tape.jsonl` (the input) | 3.5 MB |

The audit trail is ~78x the evidence it describes.

**Composition of one state record** (record #5,000; 74 features; 31,091 bytes):

| Component | Bytes | Share |
|---|---|---|
| JSON key names (`"calculation_time":` etc., x74) | ~10,360 | 33% |
| `history` feature (last 32 bars' OHLC) | 4,567 | 15% |
| `input_lineage_hash` (40 hex x 74) | 2,960 | 10% |
| feature names (map key + `name` field, stored twice) | 2,724 | 9% |
| timestamps (`calculation_time` + `max_input_available_time`) | 2,812 | 9% |
| `dtype` / `feature_version` / `quality` / `group` | 1,846 | 6% |
| **the 74 float values themselves** | **~590** | **2%** |

The key-name share is computed from key lengths rather than measured directly
(+/-3%); every other row is a direct measurement. The `history` feature is a
32-bar window of OHLC that already exists in `tape.jsonl`, so each bar's OHLC
is additionally written into 32 consecutive state records.

Serializing one state (`record_dict` + `json.dumps`) costs 0.29 ms, i.e.
**~2.5 s per run** for `states.jsonl` alone.

**Per-append syscalls.** `store.AppendOnlyLog.append` performs
`path.exists()` + `path.stat()` (hardlink detach check) + `write` + `flush` on
every record: 753,791 `stat` calls and 376,890 `flush` calls per run.

**Whole-ledger re-hashing.** `AppendOnlyLog.hash` re-serializes the entire
parsed ledger; five calls cost 5.5 s of profiled time.

## 8. Finding 4 — float formatting is not portable across runtimes

Every identity in V8 is `sha1_hex(json.dumps(obj, sort_keys=True,
separators=(',', ':'), default=str))`. The decimal rendering of a float is
therefore part of `state_id`, `lineage_hash`, and every downstream hash.
CPython's `json` encoder and Rust's default `f64` `Display` disagree:

| Value | CPython `json.dumps` | Rust `{}` |
|---|---|---|
| `1.0` | `1.0` | `1` |
| `1e16` | `1e+16` | `10000000000000000` |
| `1e-5` | `1e-05` | `0.00001` |
| `0.1 + 0.2` | `0.30000000000000004` | `0.30000000000000004` |
| `-0.0` | `-0.0` | `-0` |
| `1e22` | `1e+22` | `10000000000000000000000` |
| `123456789012345678.0` | `1.2345678901234568e+17` | `123456789012345680` |
| `1e-323` | `1e-323` | `0.000…001` (323 decimals) |

**Seven of eight test values differ.** Both renderings are shortest-roundtrip
correct; they differ in the exponent-notation thresholds. A second
implementation that reproduces V8 values exactly would still produce different
hashes unless CPython's `float_repr` and encoder thresholds are reimplemented
verbatim. See `PARITY_AND_IDENTITY_SPEC` for the resolution.

## 9. Extrapolations (DESIGN_INFERENCE — not measured)

These project the measured per-unit costs onto the research target
(100 symbols, 15m base, one year, five intervals). They are arithmetic on
measured units, not observed runs, and should be re-measured before being
relied upon.

| Quantity | Basis | Projection |
|---|---|---|
| Bars per symbol-year at 15m | calendar | 35,040 |
| `id_map` term at 35,040 bars | O(N) per state x N states | ~78 s/symbol |
| Cube cells with 4x candidates and 10x interventions | 246,884 x 40 | ~9.9M/symbol |
| Cube at 6.4 us/cell, index-bounded | 9.9M x 6.4 us | ~63 s/symbol; ~1.75 h for 100 symbols single-core |
| `states.jsonl` at 15m x 5 intervals | ~370 features x ~150 KB/state | ~5.3 GB/symbol; ~530 GB for 100 |
| `OutcomeCubeRow` as JSONL | 35 fields x 9.9M rows | ~6 GB/symbol; ~600 GB for 100 |
| Target state record after tiering | design target, not measured | ~350 B/bar (~90x reduction) |

The 4x candidate multiplier for 15m and the 10x intervention multiplier are
assumptions carried from the evaluator design, not measurements. `contexts`,
`chronological partitions` and `symbols` are groupings of existing cells and do
**not** multiply the replay count.

## 10. What this audit does and does not establish

**Establishes.** (a) At least three independent sites — state lineage
(`id_map`), cube replay (`tail = bars[i:]`), and ledger hashing
(`AppendOnlyLog.hash`) — perform bounded work over unbounded data; this is one
defect class, not three incidents. (b) The persisted state ledger carries ~2%
information. (c) The Outcome Cube's arithmetic is cheap (6.4 us/cell); its
present cost is ~92% data movement. (d) Decimal float rendering is not portable
between CPython and Rust and therefore cannot be the basis of a cross-runtime
identity.

**Does not establish.** (a) That any specific remedy is correct — the audit
measures cost, it does not choose an architecture. (b) That the projections in
section 9 hold; they are arithmetic, not runs. (c) Anything about economic
performance. No number here is an outcome, a return, or an edge.

**Explicitly not claimed.** That a native rewrite is *required* by the
program's falsification criterion. On these measurements the index-bounded
cube path plus per-symbol process parallelism reaches research scale inside
tens of minutes without leaving Python; the compute-core decision (D-077) rests
on architecture and representation-ownership grounds, which are argued in
`COMPUTE_CORE_SPEC`, not on a necessity claim derived from this audit.

## 11. Reproduction

```bash
.venv/bin/python tools/_perf_probe.py all     8760      # section 2
.venv/bin/python tools/_perf_probe.py pilot   8760      # section 2
.venv/bin/python tools/_perf_probe.py profile 8760      # section 4
```

Sections 5-8 were measured with ad-hoc scripts against the same synthetic tape;
each snippet appears inline above and is self-contained apart from
`sys.path.insert(0, 'src')`.
