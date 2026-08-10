# V8 Architecture Specification

**Status:** PROVISIONAL_DECISION. This is the system-level build contract: it
names the components, the data flow between them, and the technology
baseline. It adds no economic claim; every component beyond the baseline
pipeline stays gated (`V8_CONSTITUTION` rules 6, 14).

## 1. System boundary

The V8 research runtime is a single-process, deterministic, hash-bound
replayer for research. It contains no order-sending, no credentials, and no
live path (`FEED_INGESTION_SPEC` §1; `OPERATIONS_SPEC` §1). Live status is
unreachable until the simulation authority is independently renewed (D-016;
rule 12).

## 2. Component map and data flow

```text
versioned point-in-time tape (JSONL)
  -> MarketState builder              (MARKET_STATE_CONTRACT)
  -> deterministic self-gating Experts (EXPERT_PROTOCOL; 2-3)
  -> candidate transition log          (CANDIDATE_LIFECYCLE_SPEC)
  -> deterministic acceptance + RiskGate (CANDIDATE_LIFECYCLE_SPEC §6; D-018, D-023)
  -> canonical Level-1 simulator       (SIMULATION_TRUTH_SPEC)
  -> preregistered lab runner          (HYPOTHESIS_LAB_PROTOCOL)
  -> hash-bound LabReport              (D-010, D-027)
```

A second, read-only **evaluation plane** sits on top of the completed run and
never feeds back into it (`RECOVERABLE_REGRET_PROTOCOL` §1):

```text
completed Lab store
  -> CandidateSnapshot join + PIT lineage assertion
  -> ledger reconciliation                (Replay(C, a_actual, M) == observed)
  -> LegalActionManifest                  (OUTCOME_CUBE_SPEC §2)
  -> Outcome Cube                         (OUTCOME_CUBE_SPEC)
  -> legal hindsight gap -> systematicity -> recoverability gate
```

| Stage | Owning contract | Admissible outputs | Gate |
|---|---|---|---|
| Tape (raw evidence) | FEED_INGESTION_SPEC §2 | immutable `TapeRow` with three clocks | future rows fail closed |
| MarketState | MARKET_STATE_CONTRACT | immutable `S(D, U, C)`; features carry max availability | `max_input_available_time <= D` asserted |
| Experts | EXPERT_PROTOCOL §2 | `ExpertEvaluation` (CANDIDATE / NOT_APPLICABLE) + `CandidateDraft` | baseline: full self-gating |
| Candidate lifecycle | CANDIDATE_LIFECYCLE_SPEC §2 | append-only `CandidateTransition` | legal transitions only; no reactivation |
| Acceptance / risk | CANDIDATE_LIFECYCLE_SPEC §6 | ACCEPTED or REJECTED with reason code | one exposure per (instrument, direction); heat cap |
| Simulator | SIMULATION_TRUTH_SPEC | `CounterfactualOutcome` (R-multiples, excursions) | fill-at-close, STOP_FIRST, gap semantics |
| Lab runner | HYPOTHESIS_LAB_PROTOCOL | `LabReport` with `ledger_hash`, `execution_share` | absent authority receipt blocks a verdict |

The stepped execution ledger is a second path inside the same simulator
(`step()` vs `run()`), per CANDIDATE_LIFECYCLE_SPEC §6: accepted candidates
live as `OpenPosition`s across decision clocks; portfolio-rejected candidates
keep a `NOT_EXECUTED` batch counterfactual. Attribution and execution are
separate paths by design, so the executed-vs-rejected selection-bias
population stays measurable (D-009, D-027).

## 3. Technology baseline (D-031)

- **Language/runtime:** Python >= 3.11, stdlib-first. The decision-path core
  (`src/v8/` minus `simtruth/`) has no third-party runtime dependency;
  `numpy` is confined to the vendored reference simulator and research
  tooling, never the decision path.
- **Process topology:** single process; components are modules with interface
  contracts, not services (D-015; RUNTIME_SCHEDULER_SPEC §3). No hidden
  shared mutable state; all cross-component information flows through
  `MarketState` values and append-only logs.
- **Clock driver:** bar-driven decision clock by default; event-driven mode
  is gated on a preregistered incremental-value experiment (D-014;
  RUNTIME_SCHEDULER_SPEC §1).
- **Storage mapping** (D-013; PERSISTENCE_REPLAY_SPEC §1): raw evidence in
  immutable Parquet; decision/execution/outcome ledgers as append-only JSONL
  at slice scale; derived and research stores in DuckDB rebuilt from a pinned
  `ExperimentManifest`. The small transition log may be SQLite (WAL) or plain
  JSONL — the slice keeps plain JSONL (`AppendOnlyLog`).
- **Determinism:** integer nanosecond clocks; no wall clock inside replay;
  canonical `sha1_hex` for every hash; replay order is
  `(event_time, available_time, venue_sequence)`, never ingestion order
  (PERSISTENCE_REPLAY_SPEC §4).
- **Testing:** pytest via uv; contract tests prove the pipeline runs and is
  reproducible, never economics (rule 10).
- **Versioning:** the simulator hash is part of every outcome; the code hash
  binds the `LabReport`; a code change that alters the event stream requires
  a manifest/version bump (PERSISTENCE_REPLAY_SPEC §4).

## 3.1 V8.2 substrate revision (D-077)

D-031's single-language baseline above is **revised, not retired**: it remains
normative for `src/v8/`, which V8.2 freezes as the parity oracle
(`PARITY_AND_IDENTITY_SPEC` §2). V8.2 splits the runtime into two planes:

- **Python control/analysis plane** — experiment specs, manifests,
  preregistration, hypothesis definitions, verdict statistics on reduced
  tables, reports, diagnostics, monograph.
- **Rust compute plane** — dataset, features, state, experts, candidates,
  lifecycle, replay, cube, regret reduction, DAG cache, ledger writing, CPU/GPU
  scheduling. One process, one memory model, one owner per buffer.

Three rules make the split normative rather than descriptive:

1. **No callback** — once a request enters the compute plane, control does not
   return to Python until it completes (D-078; `COMPUTE_CORE_SPEC` §3). An
   Expert-supplied post-entry thesis reaches the kernel as a compiled predicate
   (`PREDICATE_IR_SPEC`), never as a closure.
2. **The boundary is an artifact file, not an FFI call** — the compute plane
   writes columnar ledgers (`LEDGER_FORMAT_SPEC`); the analysis plane reads
   them.
3. **Scheduling cannot change a value** — backend and thread count are
   implementation details precisely because backend invariance is gated
   (`COMPUTE_SCHEDULING_SPEC` §5; `PARITY_AND_IDENTITY_SPEC` G5).

Storage mapping is superseded for the compute plane by `LEDGER_FORMAT_SPEC`
(columnar, tiered); `PERSISTENCE_REPLAY_SPEC` remains normative for replay
semantics. Canonical hashing changes encoding at the version boundary
(D-079) — V8.2 identities are not comparable to V8.0 identities, by design.

Nothing in this revision changes the decision ontology: Expert determinism,
Candidate immutability, the three clocks, MODEL_DERIVED replay output, and the
absent-by-default list below are unaffected.

## 4. Absent by default

Router, learned scorer, ranker, learned execution, and online learning are
absent from this architecture. Each enters only through its registry
experiment and must beat its immediately simpler baseline on frozen OOS
(rules 5-6, 14; O-004 / O-005 / O-006 / O-008). Complexity budget: the runtime
Expert count is unbounded — determinism and the compute budget are the only
limits — while the preregistered cap applies to the behavior families
simultaneously carrying a claim on one frozen-OOS evaluation, with at most one
learned component per pipeline position (rule 14).

## 5. File mapping

The module/file layout is a separate contract, `IMPLEMENTATION_LAYOUT.md`
(one file, one responsibility, one owning contract). This spec is normative
for the pipeline; that one is normative for the code layout; neither may
silently drift from the other.

V8.2 adds five contracts beneath this one, each normative for its own surface:
`COMPUTE_CORE_SPEC` (planes, layers, representation rule),
`PARITY_AND_IDENTITY_SPEC` (oracle, parity gates, hash encoding),
`LEDGER_FORMAT_SPEC` (what persists and in what form),
`OUTCOME_CUBE_SPEC` (action universe, cell status, streaming reduction),
`PREDICATE_IR_SPEC` (compiled post-entry thesis) and
`COMPUTE_SCHEDULING_SPEC` (kernels, backends, determinism). The evaluation
plane's own contract is `RECOVERABLE_REGRET_PROTOCOL`.

## 6. Cheap executable tests

1. Two identical `lab.run()` invocations from a fresh store reproduce every
   hash (already in `tests/test_vertical_slice.py`).
2. Injecting a future row anywhere in the pipeline fails closed
   (`FutureRowError`).
3. Import-boundary test: no `src/v8/` module references a venue endpoint or
   an order path.
4. Shuffling the evaluation order of independent experts produces identical
   stored events (RUNTIME_SCHEDULER_SPEC §5).
5. A run with an absent authority receipt yields `NO_ECONOMIC_CLAIM`.

## 7. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** the runnable vertical-slice gate is the
  response to the V7 audit, which caught nine unexecuted campaign/simulation
  paths (`PROJECT_EVIDENCE_AUDIT` §2). A declared workflow is not evidence
  that the workflow runs.
- **LITERATURE_SUPPORTED:** DuckDB ACID/single-writer semantics and SQLite
  WAL fit the single-writer, replay-heavy research store
  (PERSISTENCE_REPLAY_SPEC §6).
- **DESIGN_INFERENCE:** the component map, the technology baseline, and the
  absent-by-default list are V8 choices that make the contracts testable; no
  source is cited as proof of edge.
