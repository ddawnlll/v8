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

## 4. Absent by default

Router, learned scorer, ranker, learned execution, and online learning are
absent from this architecture. Each enters only through its registry
experiment and must beat its immediately simpler baseline on frozen OOS
(rules 5-6, 14; O-004 / O-005 / O-006 / O-008). Complexity budget: at most 3
active Experts and at most one learned component, never both at once
(rule 14).

## 5. File mapping

The module/file layout is a separate contract, `IMPLEMENTATION_LAYOUT.md`
(one file, one responsibility, one owning contract). This spec is normative
for the pipeline; that one is normative for the code layout; neither may
silently drift from the other.

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
