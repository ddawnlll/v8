# V8 Roadmap

**Status:** PROVISIONAL_DECISION. This roadmap is the build plan for the full
V8 system, executed phase by phase. Every phase has a definition of done; the
gated components (router, scorer, ranker, learned execution) are on the
roadmap but are built **only when their evidence gate passes** — a gate is a
preregistered, costed, frozen-OOS comparison, never a calendar date
(`V8_CONSTITUTION` rules 5-6, 14).

System versions map to phases: v0.1 = Phase 0-4 foundation; each later phase
that admits a component bumps the version.

## Phase 0 — Foundation (DONE 2026-08-01)

- Corpus restored and restructured (`docs/`, `site/`, `research/`, `tools/`,
  `src/`); reproducible monograph build (EN + TR).
- Contracts: MARKET_STATE, EXPERT_PROTOCOL, CANDIDATE_LIFECYCLE, DATASET,
  FEED_INGESTION, PERSISTENCE_REPLAY, RUNTIME_SCHEDULER, SIMULATION_TRUTH,
  HYPOTHESIS_LAB, OPERATIONS, LEARNING_PROTOCOL; constitution rules 1-17.
- Phase-2 vertical slice (`src/v8/`): tape -> MarketState -> experts ->
  candidate lifecycle -> canonical simulator -> hash-bound lab report.
  **DoD:** slice tests green; monographs build byte-identically.

## Phase 1 — Data plane

- `tools/vision_backfill.py`: Binance Vision download (monthly/daily), checksum
  verification, CSV -> PIT tape (JSONL) with three clocks.
- Tape audit: monotonicity, gap detection, row counts vs source checksums.
- Materializations: `market_states.parquet` + candidate views (compile-once
  discipline, `DATASET_SPEC` section 5).
- **DoD:** BTCUSDT 1h tape loads; audit passes; tape hash reproducible.
- **Gate (O-011):** tape quality audit against the declared universe; extend
  venues only on binding coverage failure.

## Phase 2 — State engine and feature graph

- MarketState builder on real tape; feature groups (trend, volatility,
  location, participation, response) with `requires:` declarations.
- Feature versions + lineage hashes; PIT tests (future rejection,
  bar-not-closed, revision replay).
- **DoD:** features on real data; state hashes reproducible.

## Phase 3 — Pilot experts

- `trend_pullback_continuation_v1`, `failed_breakout_reentry_v1`,
  `liquidity_sweep_reclaim_v1` (backlog: breakout retest, capitulation —
  `DATA_BLOCKED` until derivatives tape).
- Registry entries with `mechanism_family_id`, `behavior_family_id`,
  `variant_id`; status lifecycle (PROPOSED -> FORMALIZED -> SCREENING ->
  REPLICATION -> SHADOW -> PROMOTED; REJECTED/MERGED/QUARANTINED/
  DATA_BLOCKED).
- **DoD:** experts run on real tape; contract tests green.

## Phase 4 — Measurement and first evidence (first program gate)

- Canonical simulator v1 with Binance cost model (`binance_usdm_costs_v1`).
- Preregistered experiment #1 (`v8_slice_001`): both pilot experts on frozen
  chronological OOS vs no-trade baseline, family-level multiplicity control.
- **DoD:** pipeline correctness on real data (determinism, PIT, cost, ledger
  hash); first after-cost OOS estimates produced — not claims.
- **Program gate:** if neither family shows after-cost signal, the falsification
  program stops here; gated components are never built without a surviving
  family (`V8_CONSTITUTION` rule 12).

## Phase 5 — Gated components (only on surviving evidence)

- Candidate Scorer challenger (logistic -> shallow GBDT) vs deterministic
  evidence score at matched coverage (O-005).
- Ranker evaluation only when exposure conflicts are frequent and material
  (O-012); router only when self-gating violates a declared budget (O-004).
- **DoD per component:** beats its immediately simpler baseline on frozen OOS,
  or is rejected.

## Phase 6 — Ops and hardening

- Data-quality monitoring (schema checks, staleness/gap alerts), structured
  logging, CI with golden-backtest regression, fail-closed tests.
- Simulation authority certification renewal path (`OPERATIONS_SPEC`
  section 1); shadow/paper status automation.
- **DoD:** operator tests green; certification record updated.

## Phase 7 — Learning plane (only after certified edge)

- Path/time models (hazard/quantile), execution challengers (heuristic ->
  contextual bandit -> conservative offline RL), per `LEARNING_PROTOCOL`.
- **DoD:** every learned component enters through the ExpertContract and a
  registry decision; no online mutation (rule 15).

## Cross-cutting rules

- Versions evolve by challenger + frozen-OOS + registry, never in place
  (`LEARNING_PROTOCOL` section 1).
- Every change lands in `CHANGELOG.md`; every bump in `DECISION_REGISTER`.
- One moving part at a time; complexity budget is a hard cap (rule 14).
