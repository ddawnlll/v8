# V8.2 Compute Core Specification

**Status:** PROVISIONAL_DECISION (D-077). This is the system contract for the
V8.2 compute plane: what owns data, what may call what, and where the boundary
between the research interface and the engine runs. No component described here
exists yet; everything about the engine's behaviour is DESIGN_INFERENCE until
its parity gate passes (`PARITY_AND_IDENTITY_SPEC` §5). It adds no economic
claim (`V8_CONSTITUTION` rule 12) and changes no decision semantics.

## 1. What changes and what does not

V8.2 changes the **implementation substrate** of the evaluation path. It does
not change the decision ontology. The following stay exactly as specified in
V8.0 and are restated here because a substrate change is the easiest place to
lose them:

- An Expert is deterministic and self-gating (`EXPERT_PROTOCOL` §2).
- A Candidate is an immutable proposal, never an order (D-001).
- Future data can never be a decision feature; the three clocks are never
  collapsed (`MARKET_STATE_CONTRACT` §1).
- Replay output is MODEL_DERIVED (`SIMULATION_TRUTH_SPEC`).
- The evaluator may not invent a Candidate
  (`RECOVERABLE_REGRET_PROTOCOL` §2).
- Router, learned scorer, ranker, learned execution and online learning remain
  absent by default (`ARCHITECTURE_SPEC` §4; rules 6, 14).

A substrate that reproduces the values but breaks one of these is not a faster
V8; it is a different system.

## 2. System boundary

```text
┌─────────────────────────────────────────┐
│ PYTHON CONTROL PLANE                    │
│   experiment specs, manifests,          │
│   preregistration, hypothesis defs      │
└────────────────┬────────────────────────┘
                 │  compiled evaluation request (one call)
                 ▼
┌─────────────────────────────────────────┐
│ RUST COMPUTE PLANE  (one process,       │
│                      one memory model)  │
│   dataset · features · state · experts  │
│   candidates · lifecycle · replay       │
│   cube · regret reduction · cache       │
│   ledger writing · CPU/GPU scheduling   │
└────────────────┬────────────────────────┘
                 │  artifact files (columnar) + reduced tables
                 ▼
┌─────────────────────────────────────────┐
│ PYTHON ANALYSIS PLANE                   │
│   statistics on reduced tables,         │
│   reports, monograph, plots, diagnostics│
└─────────────────────────────────────────┘
```

The compute plane is a single process with a single owner of every buffer. The
control and analysis planes never hold long-lived numeric data; they hold
requests, handles, and reduced tables.

## 3. The no-callback invariant (D-078)

> **Once an evaluation request enters the compute plane, control does not
> return to Python until the request completes.**

No Python callback, no Python object, no Python-owned buffer may be reachable
from inside the compute plane. The prohibited shape is:

```text
Rust kernel → candidate → Python predicate → Rust kernel → next bar
```

Violating it forfeits batching, cache locality, and any GPU backend, and it
re-couples the scheduler to Python's execution semantics.

The one place V8.0 requires such a callback is the post-entry thesis check
(`still_valid`), which `tools/regret.py` passes into the simulator as a
closure. That surface was measured and is small: 28 implementations,
~560 lines, over an 11-feature vocabulary; 19 of the 28 read only `close`
alongside the frozen `risk_geometry`
(`PERFORMANCE_AUDIT_V82` §10; full table in `PREDICATE_IR_SPEC` §2). It is
therefore compiled ahead of the kernel rather than called from inside it —
see `PREDICATE_IR_SPEC`.

**Consequence for future work:** any new Expert-supplied hook that the replay
path must consult is subject to the same rule. It must be expressible in the
predicate IR, or it does not enter the replay path.

## 4. Layer map

| Layer | Owns | Consumes | Contract |
|---|---|---|---|
| `Dataset` | columnar OHLCV + the three clocks, one allocation per symbol | verified tape | `DATASET_SPEC`, `FEED_INGESTION_SPEC` |
| `FeatureStore` | precomputed series (EMA/ATR/RSI/ADX/pivots/…) | `&Dataset` | `MARKET_STATE_CONTRACT` |
| `StateView` | per-clock feature columns + identity | `&FeatureStore` | `MARKET_STATE_CONTRACT` |
| `ExpertPlane` | evaluations, candidate drafts | `&StateView` | `EXPERT_PROTOCOL` |
| `CandidateBuffer` | immutable candidate records, lifecycle transitions | `ExpertPlane` output | `CANDIDATE_LIFECYCLE_SPEC` |
| `ReplayKernel` | one outcome per (candidate, action) | `&Dataset`, compiled predicates | `SIMULATION_TRUTH_SPEC` |
| `CubeReducer` | streaming regret accumulators | `ReplayKernel` output | `OUTCOME_CUBE_SPEC` |
| `EvidenceStore` | columnar ledgers, content-addressed DAG cache | all of the above | `LEDGER_FORMAT_SPEC`, `PERSISTENCE_REPLAY_SPEC` |

Data flows one way. No layer mutates a layer below it. The only mutable
long-lived state is the DAG cache, which is content-addressed and therefore
append-only in effect.

## 5. Representation rule

> **A layer receives a borrowed view of data it does not own. Copying a window
> out of an owned buffer is a defect unless the copy is the output.**

This rule exists because its violation was measured three times independently
in V8.0 — state lineage, cube replay, and ledger hashing each performed bounded
work over unbounded data (`PERFORMANCE_AUDIT_V82` §10). Rust's ownership model
makes the correct form (`&bars[start..end]`) the natural one and the incorrect
form (`.to_vec()`) explicit, but the rule is normative independently of the
language: a Rust implementation that clones windows reproduces the same defect.

Concrete obligations:

1. A replay cell reads at most `expiry_bars + 1` bars and is passed
   `(&Dataset, start, end)`, never a materialized window.
2. Per-state identity maps and other whole-tape indices are built **once per
   dataset**, never per clock.
3. Cumulative digests advance incrementally; a digest is never recomputed over
   a full prefix on the hot path.
4. Any hot-path allocation is either pooled or hoisted out of the loop.

## 6. Module layout

One workspace, one binary, modules — not micro-crates. Splitting is deferred
until a boundary is proven stable.

```text
v8-core/
  src/
    main.rs         CLI entry; one evaluation request per invocation
    data.rs         Dataset: columnar OHLCV + event/available/ingested clocks
    state.rs        FeatureStore, StateView, feature identity
    experts/        one behaviour family per module (mirrors D-033)
      mod.rs        registry
      predicate.rs  compiled still_valid IR (PREDICATE_IR_SPEC)
    candidate.rs    CandidateBuffer, lifecycle transitions, ExposureBook
    simulator.rs    ReplayKernel (step/run), risk unit, fill policies
    regret.rs       LegalActionManifest, CubeReducer, gap accumulators
    statistics.rs   reductions only; verdict statistics stay in Python (§7)
    cache.rs        content-addressed DAG cache
    evidence.rs     columnar ledger writer (LEDGER_FORMAT_SPEC)
    compute/        kernels + backend selection (COMPUTE_SCHEDULING_SPEC)
  tests/
    parity.rs       value-level parity against the V8.0 Python oracle
```

The Python file family (`IMPLEMENTATION_LAYOUT` §1) is unchanged by this spec;
V8.0 is frozen as the parity oracle, not deleted.

## 7. What stays in Python, and why the boundary is a file

The control and analysis planes stay in Python. The crossing between planes is
**an artifact file, not an FFI call**: the compute plane writes columnar
ledgers and reduced tables, and the analysis plane reads them. This choice
removes FFI schemas, lifetime negotiation across the boundary, GIL
interaction, and duplicate domain types from the design.

A component may remain in Python when all three hold:

1. it is called O(1) times per evaluation, not per bar or per cell;
2. it consumes and produces batches, not scalars;
3. it is not inside a hot loop.

Verdict statistics qualify. After `CubeReducer` runs, the data crossing the
boundary is aggregates — order 10^4-10^6 numbers per run, not the 10^7 cube
cells that produced them — so block bootstrap, family corrections and
systematicity gates remain Python at negligible cost, and remain transparent,
which the evaluator protocol prefers
(`RECOVERABLE_REGRET_PROTOCOL` §6). This is a consequence of streaming
reduction (`OUTCOME_CUBE_SPEC` §4): without it, the same components would be
reading gigabytes and would not qualify.

## 8. Migration order

The port is staged so that a working research instrument exists at every point.

| Stage | Content | Gate |
|---|---|---|
| S0 | Parity harness + `Dataset` ingest | tape round-trips; clocks preserved |
| S1 | `FeatureStore` + `StateView` | value-level parity on every bar, every feature |
| S2 | Predicate IR + `ReplayKernel` | outcome parity on the V8.0 candidate population |
| S3 | `CubeReducer` + streaming regret | reduced tables match the Python evaluator |
| S4 | `CandidateBuffer` + `ExpertPlane` | candidate population parity |
| S5 | `EvidenceStore` + DAG cache | ledger identity stable across cache hit/miss |

Between S3 and S4 the control plane still produces candidates in Python and
hands the compute plane one compiled batch per request. That is a valid
resting point, not a hybrid to be maintained indefinitely: the no-callback
invariant already holds at S2, because the predicate IR — not a Python
closure — is what the kernel consults.

Whether S4 must be pulled forward depends on an open question: if
expert-variant sweeps enter V8.2's scope, experts are inside the hot loop by
definition and must be native from S1 (`OPEN_DECISIONS`).

## 9. Cheap executable tests

1. **No-callback:** the compute plane binary links no Python runtime; a build
   configuration that would allow an embedded interpreter fails the build.
2. **Single ownership:** a test asserts `Dataset` is constructed once per
   symbol per request (allocation counter), not once per clock.
3. **Bounded windows:** a replay cell instrumented with a read counter never
   touches more than `expiry_bars + 1` bars.
4. **Parity:** every stage gate in §8 is a value-level bit-equality test
   against the V8.0 oracle (`PARITY_AND_IDENTITY_SPEC` §5).
5. **Determinism:** two identical requests produce byte-identical artifacts;
   the same request under a different backend or thread count produces
   identical values (`COMPUTE_SCHEDULING_SPEC` §5).
6. **Absence:** no module named for a gated component (router, scorer, ranker)
   exists in the tree.

## 10. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** the representation-rule motivation in §5 —
  three measured sites of bounded work over unbounded data, with per-unit costs
  (`PERFORMANCE_AUDIT_V82` §§5-7).
- **PROJECT_EVIDENCE_SUPPORTED:** the predicate surface cited in §3 — 28
  implementations, ~560 lines, 11 features, extracted from
  `src/v8/experts/*.py` by AST.
- **DESIGN_INFERENCE:** the plane split, the layer map, the module layout, the
  artifact-file boundary and the migration order. These are V8.2 choices that
  make the contracts testable; no source is cited as proof of edge, and none of
  them is evidence that the engine is faster until measured.
- **Not claimed:** that this substrate is required by the program's
  falsification criterion. `PERFORMANCE_AUDIT_V82` §10 records the opposite —
  research scale is reachable in Python once the defect class in §5 is removed.
  V8.2 is justified by ownership, representation and evaluator-capability
  arguments, not by necessity.
