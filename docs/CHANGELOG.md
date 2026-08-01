# V8 Changelog

Format: dated, brief, reversible. This log records document and architecture
decisions — never economics. Each entry names the artifacts it changed.

## 2026-08-01 — Adversarial-audit fixes on Phase 2-4 code (14 findings, 6 fixed)

A four-dimension adversarial review (correctness / contract / determinism /
runner) confirmed 14 findings; the real ones are fixed here.

- **`src/v8/lab.py` (medium)** — the pre-entry invalidation now uses the
  expert's FROZEN windowed prior ref (`prior_low_ref` / `prior_high_ref` in
  the draft geometry) instead of the all-bars state feature, which diverges
  from the thesis ref (an old spike outside the 32-bar window pins it). A
  dead-thesis candidate no longer triggers and enters, polluting the executed
  population. Dev trigger count 3,295 -> 2,939; golden terminal distribution
  changes (deliberate re-pin).
- **`src/v8/marketstate.py` (low ×2)** — `max_input_available_time` is now
  the consumed-derived clock (prior_high/prior_low never claim the newest bar,
  which is not their input); the history feature's `input_lineage_hash` now
  covers the full close series (its EMA columns depend on it).
- **`tools/run_experiment.py` (medium ×2, low)** — prereg §9 mechanical
  block-size rule implemented (24 by default; 168 when the lag-1
  autocorrelation of episode net_R exceeds 0.10); family scores are NOT
  reported when the D-027 gate fires ATTRIBUTION_UNSAFE_* (§11 "not scored");
  the holdout hash is REQUIRED (fail closed on an un-pinned holdout, §16);
  the frozen OOS window must start strictly after the 2026-07-01 anchor (§13);
  `h0_rejected` is now the composite §11/§12 test (lower bound > 0 AND
  n_f >= 30).
- **Runner bootstrap percentile fix** (caught by the dev-tape smoke run) — the
  2.5th-percentile LOWER bound was indexed at the 97.5th percentile; a
  negative-mean family could falsely report h0_rejected.
- 5 new regression tests; suite 148 -> 152. Dev materialization re-pinned
  (`adad594a…`, views4); prereg §6/§15 updated (execution_share 0.4662,
  KS 0.1028 — diagnostics only; thresholds unchanged).

## 2026-08-01 — Dev materialization re-pin (three pilots, D-042)

- Dev tape re-materialized with the third pilot (`liquidity_sweep_reclaim`)
  and the Phase-2/Phase-4a code: candidate_count 2,786 -> 3,323, ledger_hash
  `40d4f23a…` (fresh `views3` dir, compile-once; code_hash `fec878c5…`).
- Prereg §6 derived outputs and §15 12-month diagnostics updated: with three
  pilots the D-027 populations are `n_executed` 1,415 / `n_portfolio_rejected`
  1,476, execution_share 0.4895, KS 0.0932 — **diagnostics only**, the
  ratified thresholds 0.25/0.20 are unchanged (O-017).
- Monograph rebuilt; suite 147 tests green.

## 2026-08-01 — Phase 4b: v8_slice_001 experiment runner

- **`tools/run_experiment.py`** — the preregistered `v8_slice_001` runner:
  validates the frozen manifest (experiment_id, universe BTCUSDT, interval
  1h), verifies the pre-recorded holdout tape hash before any evaluation
  (fail closed on mismatch or absent holdout — never fabricates a verdict),
  runs the two pilot families on the frozen OOS, computes family-level
  one-sided tests with a deterministic block bootstrap (block 24, fixed seed)
  and Bonferroni multiplicity control (alpha_f = 0.025), and surfaces the
  D-027 attribution statistics. Authority blocks first (no receipt ->
  NO_ECONOMIC_CLAIM). The RUN is gated on the frozen holdout existing (first
  two published months after 2026-07-01 + 9-bar extension, prereg §13).
- 5 tests (fail-closed absent holdout, frozen-constant validation, holdout
  hash recorded-before-evaluation, hash mismatch fail-closed, bootstrap
  determinism/one-sidedness). Suite 142 -> 147.

## 2026-08-01 — Phase 3: third pilot + DATA_BLOCKED backlog (D-042)

- **`src/v8/experts/liquidity_sweep_reclaim.py`** — `LiquiditySweepReclaimExpert`
  (`liquidity_sweep_reclaim` / `sweep_reclaim`, variant `a`): LONG after a
  sweep of the windowed prior low that closes back above it, SHORT after a
  prior-high sweep reclaimed by the close; `prior_low_ref`/`prior_high_ref`
  frozen at detection (failed_breakout pattern) and excluded from
  `geometry_version` (`src/v8/lab.py`). Re-exported; added to
  `tools/materialize_views.py` PILOTS.
- **`docs/EXPERTS_REGISTRY.yaml`** — third pilot at FORMALIZED; `breakout_retest`
  and `capitulation` backlog families registered DATA_BLOCKED until
  derivatives tape (no code module — ROADMAP Phase 3 backlog).
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md`** — tree + file table + planned
  note updated; **`D-042`** registered (D-032 file-family rule).
- Registry/artifact tests amended for the third pilot + DATA_BLOCKED entries.
  4 new expert tests; suite 139 -> 142. The dev materialization is re-pinned
  (see the materialization entry below).

## 2026-08-01 — D-027 attribution-validity gating in LabReport (Phase 4a)

- **`src/v8/schema.py`** — LabReport gains `n_executed` / `n_portfolio_rejected`
  / `execution_share` / `divergence_ks` (two-sample KS on executed vs
  portfolio-state-rejected net_R) and the verdict vocabulary
  NO_ECONOMIC_CLAIM | CERTIFIED_AVAILABLE | ATTRIBUTION_UNSAFE_LOW_COVERAGE |
  ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE. Authority blocks first (receipt
  None -> NO_ECONOMIC_CLAIM regardless); thresholds are the ratified O-017
  numbers (0.25 / 0.20), fixed forever.
- **`src/v8/lab.py`** — stdlib-pure `_two_sample_ks` (scipy/numpy banned in the
  decision path, D-031), `_d027_verdict`, and the epilogue computation of both
  populations. Verified to reproduce the prereg §15 12-month diagnostics
  exactly (execution_share 0.4576, KS 0.1044, n=1111/1317) on the dev tape.
  Hash-neutral (statistics derive from ledgers already inside ledger_hash) —
  no golden re-pin.
- **Prereg §15** — the 12-month diagnostics corrected to the
  label_status-based population definition (n_executed 1,111 — the earlier
  draft counted INVALIDATED_BEFORE_TRIGGER as executed); the lab's own
  D-027 computation is now the source of these numbers.
- 9 new tests; suite 127 -> 136.

## 2026-08-01 — Phase 2 completion: per-feature input lineage + state provenance

- **`src/v8/schema.py`** — `FeatureValue` gains `input_lineage_hash` (identity
  of the raw rows that produced the feature) and `calculation_time`;
  `FEATURE_GRAPH_VERSION` (hash of the FEATURE_GROUPS declaration);
  `MarketState` gains a `provenance` block
  {raw_manifest_hash, feature_graph_version, code_version}.
- **`src/v8/marketstate.py`** — build_state binds each feature's input lineage
  (payload_hash when the tape computes it, else the payload — synthetic tapes
  carry no payload_hash) and fills the provenance block. These are audit
  metadata: they do NOT join the identity hashes (a raw revision that does not
  change a value must not fabricate a new state identity).
- **Golden re-pin (deliberate, PERSISTENCE_REPLAY_SPEC 4):** the persisted
  state records gain the new fields, so `GOLDEN_STATES_HASH` and
  `GOLDEN_LEDGER_HASH` move; `GOLDEN_DATA_HASH`, candidate count 21 and the
  terminal distribution are unchanged (feature values are identical — expert
  behavior is byte-identical).
- 3 new tests (per-feature lineage + calculation clock, revision-without-
  value-change lineage, provenance determinism). Suite 136 -> 139.

## 2026-08-01 — 12-month dev materialization + pinned rebuild (D-041)

- **12-month dev tape built and audited clean** — BTCUSDT 1h 2025-07-01..
  2026-07-01: 8,760 klines + 1,188 funding rows (incl. the `2026-07` coverage
  horizon) = 9,948 rows, tape hash `4c8e5888…`, 25 SHA-256-verified Vision
  archives. Audit: 0 gaps, 0 duplicates, payload hashes OK; the old 3-month
  tape still audits clean.
- **`research/tape/btcusdt-1h-12m/manifest_dev.json`** — `experiment_id
  v8-dev-12m-btcusdt`, code_hash `ea8db9e2…`, data_hash `4c8e5888…`.
  Materialized in a fresh store/views dir (compile-once): market_states 8760,
  candidate_birth/outcomes 2786, candidate_trigger 2779,
  execution_trajectories 11684; ledger `c78bf43a…`, verdict
  `NO_ECONOMIC_CLAIM` (no authority receipt).
- **Prereg pins updated** — §6 manifest + derived outputs, §13 dev hash, §15
  12-month diagnostics appended (execution_share 0.4596, KS 0.1067) **as
  diagnostics only**; O-017 thresholds 0.25/0.20 unchanged. DATASET_SPEC
  §6.1/§6.2/§6.4 measured rows updated.
- Monograph rebuilt; suite untouched (127 tests).

## 2026-08-01 — Tape-driven funding wiring (D-041) + golden re-pin (sim v5)

- **`src/v8/simulator.py`** — `CanonicalSimulator` gains `funding_schedule`
  ((boundary_time_ns, rate) pairs); a non-empty schedule settles each crossed
  boundary at `entry_price × rate / risk_unit` (DATASET_SPEC 6.4) and fails
  closed on a missing boundary; the empty schedule keeps the legacy scalar
  path byte-identical. Sim hash bumps to `canonical-sim-v5`; schedule values
  are tape data bound by `data_hash`, never by `sim.hash()`.
- **`src/v8/lab.py`** — `Lab.run` builds the schedule from the tape's
  `funding` rows and passes it to the simulator; `_validate_tape_rows` gains
  the funding branch (non-finite / |rate| > 0.10 fail closed).
- **Golden re-pin (PERSISTENCE_REPLAY_SPEC 4, deliberate):** the only moved
  pin is `GOLDEN_LEDGER_HASH` (outcomes' `simulator_hash` changed via the sim
  source hash + v5); `GOLDEN_DATA_HASH`, `GOLDEN_STATES_HASH`, candidate
  count 21 and the terminal distribution are unchanged — the synthetic tape
  carries no funding rows, so the event stream is byte-identical.
- Tests: 4 schedule-driven funding tests + 1 lab-level schedule wiring test;
  sim-hash canaries re-pinned to v5. Full suite 122 -> 127.

## 2026-08-01 — D-041: 12-month dev window + tape-driven funding (owner)

- **D-041 registered** — the declared dev dataset expands from 3 to 12 months
  (BTCUSDT 1h, `2025-07-01`..`2026-07-01`, ~8,760 bars) and the `funding`
  channel is ingested into the PIT tape with tape-driven settlement
  (`funding_settled_r = entry_price × rate / risk_unit`), per DATASET_SPEC
  §6.4. O-017 thresholds 0.25/0.20 are **not** touched; the 12-month baseline
  updates prereg §15 diagnostics only. Funding coverage horizon `2026-07`
  declared so end-of-dev positions settle across the 2026-07-01 boundary.
  Dev end stays strictly before the holdout anchor.
- **`docs/PREREGISTRATION_V8_SLICE_001.md`** — §8 funding baseline becomes
  tape-schedule-driven (scalar retained as no-funding-tape fallback); §13 dev
  window 12 months + coverage horizon; §15 diagnostics note (thresholds
  fixed); §6 dev-tape hash marked pending the rebuild.
- **`docs/contracts/DATASET_SPEC.md`** — §6.1 channels/dev-window rows, §6.2
  scale expectations, §6.4 funding status, §6.5 declared list updated.
- **`docs/decisions/DECISION_REGISTER.md`** — D-041 row.
- No code or test changed in this pass. Monograph rebuilt; suite untouched
  (112 tests).

## 2026-08-01 — Full-program target (D-040, owner)

- **D-040 registered** — the v0.1-only framing is retired; the program target
  is the full 8-phase roadmap with the evidence gates unchanged (rules 5-6,
  12, 14). Build priority completes Phases 0-4 first; the critical path is the
  Phase-4 `v8_slice_001` experiment runner + D-027 verdict gating. Phases 5/7
  are built only when their gate passes — never on a calendar date.
- **`docs/PLAN_V8_FULL.md` added** — sprint breakdown (Sprint A: Phase-4
  runner; Sprint B: Phase 2/3 completion; Sprint C: Phase 6 ops;
  data-blocked: derivatives tape, holdout window). Planning artifact, not
  registered in the monograph NAMES list (no TR mirror).
- **`docs/ROADMAP.md` updated** — the versioning line no longer frames the
  program as "v0.1 = Phase 0-4 foundation"; the full roadmap is the target.
- No code, contract, or test changed in this pass. Monograph rebuilt; suite
  untouched (112 tests).

## 2026-08-01 — Session-6 bugfix pass (adversarial audit fixes)

Adversarial bug hunt (11 class-scoped finders + per-finding verification) on
`src/v8/` + `tools/` confirmed 26 findings; this pass fixes them. Decision-path
changes move the golden ledger hash (outcome-label change) and are re-pinned in
`tests/test_golden_backtest.py`; candidate counts and terminal distribution are
unchanged. New regression tests: `tests/test_bugfix_pass.py` (11 tests). Full
suite 86 → 97.

- **`src/v8/lab.py`** — closed-only bars in the decision loop (open klines no
  longer drive entries/stops); multi-instrument tapes fail closed (H1/M5);
  duplicate decision clocks fail closed (M6); pre-entry invalidation re-checked
  on the entry bar (H3); `INVALIDATED_BEFORE_TRIGGER` relabelled `NOT_EXECUTED`
  (H5); counterfactual now applies the owning Expert's `still_valid` via a
  per-clock state map (H2); `prior_low/prior_high` fail closed instead of
  defaulting to 0/inf (M10); `_INTERVAL_NS` fails closed on unknown intervals
  (M12); `excess_cost` threshold promoted to named `EXCESS_COST_THRESHOLD_R`.
- **`src/v8/simulator.py`** — `run()` gains `thesis_valid(bar_time, payload)`
  so the batch counterfactual exits `THESIS_INVALIDATED` like the executed path;
  every returned outcome carries `label_available_time` (exit clock), the
  DATASET_SPEC section 4.5 embargo primitive.
- **`src/v8/schema.py` / `tools/materialize_views.py`** — `CounterfactualOutcome`
  and the `candidate_outcomes` view now expose `label_available_time`, so a
  training consumer can refuse labels whose availability overlaps its
  validation window (M4).
- **`src/v8/risk.py`** — D-024 funding-window veto measures boundaries on
  absolute wall-clock hours (`funding_hours * HOUR_NS`), matching
  `simulator._boundaries_crossed`; on non-1h tapes the old period missed
  imminent-boundary entries (H4).
- **`src/v8/marketstate.py`** — a universe symbol with zero emitted features
  degrades the state (DEGRADED), closing the missing-symbol quality gap (M2).
- **`src/v8/lifecycle.py`** — `any terminal -> ARCHIVED` added to `LEGAL`
  (CANDIDATE_LIFECYCLE_SPEC), making ARCHIVED reachable (M9).
- **`tools/monitor_tape.py`** — OHLC type/finiteness/invariant + volume checks
  (booleans, NaN/±inf, high<low, negative volume all fail); staleness measures
  kline rows only (M1/M7/L3).
- **`tools/vision_backfill.py`** — `audit_tape` gains OHLC/volume/finiteness
  invariants; `check_archive_revision` also guards legacy single-month
  `source.json` (M1/M8).
- **`tools/data.py`** — `_validate_price_rows` fails closed on NaN/±inf prices
  (M1).
- **`tools/materialize_views.py`** — `views_manifest.json` now carries a
  `views_pin` binding view SQL + manifest economics + code hash + views_dir;
  a recompile with a changed pin fails closed instead of silently replacing
  the "pinned" views (M11).

## 2026-08-01 — Session-6 second-level audit fixes (post-fix classes)

Second adversarial pass on the POST-FIX codebase (8 class-scoped finders:
alternative paths, boundary matrix, fail-open, hash canary, state coverage,
feature contamination, zero-trade provenance, reconciliation; 29 agents).
Confirmed 13 findings; this entry fixes them. Suite 104 → 108 (new regression
tests in `tests/test_bugfix_pass.py`); golden re-pinned (candidate_count
24 → 21: failed_breakout now gates on a windowed prior-high reference).

- **`src/v8/experts/failed_breakout.py`** — gate and anchor now share ONE
  prior-high reference (the history-window max excluding the newest bar). The
  old gate used the state's ALL-BARS prior_high, which an old spike outside the
  window pinned forever: the draft fired every bar, the anchor slid, and
  episode-key dedup silently produced a new DETECTED episode per bar. The
  post-entry thesis (`still_valid`) now uses a FROZEN `prior_high_ref`
  (excluded from episode identity like `atr_ref`), so a reversal that re-crosses
  the entry-time breakout level invalidates instead of drifting with the
  adverse move.
- **`src/v8/lab.py`** — `Lab.run` fails closed on a non-empty manifest
  `code_hash`/`data_hash` that does not match the live code/tape (the
  composition root no longer reports a stale or forged pin; materialize_views
  already checked, Lab.run is the authority). `terminal_distribution` is now
  candidate-counted (a `CLOSED -> ARCHIVED` candidate appears once) and the
  report adds `rejection_distribution` (D-024 vs risk vs excess-cost), `tooling_hash`
  (tools/*.py, outside the decision-path hash), and the excess-cost/tape-end
  `label_available_time` fallback to `last_as_of` (the 0-sentinel leak).
- **`src/v8/risk.py`** — the D-024 FUNDING_WINDOW veto fires whenever
  `window >= period` (a boundary always books funding on the first post-entry
  step; the old `window < period` guard silently disabled the check, so e.g.
  1d bars with funding_hours=8 admitted entries that settled 3x). The veto
  clock basis is the entry FILL time (available), matching simulator settlement.
- **`src/v8/schema.py`** — `LabReport.rejection_distribution`, `tooling_hash`.
- **`src/v8/experts/`** — no other changes; the trend_pullback thesis remains
  a live trend reference (correct by design).

## 2026-08-01 — Session-6 provenance + performance fixes (B1-B4, P1-P3)

Follow-up audit (parallel session) confirmed 4 ledger/provenance bugs + 3
structural performance items; this entry fixes them. The ledger hash now binds
the run configuration, so the golden re-pins. Suite 108 → 112.

- **`src/v8/lab.py`** — B1: a TRIGGERED candidate with no entry bar before tape
  end records `INVALIDATED_BEFORE_TRIGGER`/`NOT_EXECUTED`/0.0 (label knowable at
  tape end) instead of the fabricated empty-tail counterfactual
  (`EXPIRY`/`RIGHT_CENSORED`/0.0 with a fake simulator hash) — a non-trade no
  longer merges into the censored population (B5 naming aligned with the
  INVALIDATED terminal). B2/B3: the manifest is persisted to
  `<store>/manifest.json` and the ledger hash binds `config_hash =
  sha1_hex(asdict(manifest))` — different economics AND an authority receipt
  added later both move the ledger hash (no silent re-labelling). P1: the
  per-bar state build is O(N) incremental (moving pointer over the replay-sorted
  tape) instead of the O(N²) rescan that dominated run time.
- **`src/v8/lifecycle.py`** — B4: `CandidateRegistry` replay validates every
  `(from_state, to_state)` against LEGAL and raises on an illegal transition in
  a corrupt log (mutation-campaign fail-closed).
- **`src/v8/store.py`** — P2: `AppendOnlyLog` opens the append handle once and
  flushes per record (per-record open/close was ~half the profiled append cost);
  crash-loss policy stays bounded to the current record.
- **`src/v8/simulator.py`** — P3: `_boundaries_crossed` is O(1)
  (`floor(t/P) - floor(entry/P)`), byte-identical over the 144-case boundary
  matrix vs the per-hour loop.
- **`src/v8/marketstate.py`** — P1: the 5/20 EMA series are computed once and
  shared by the trend features and the history tuples (was computed twice per
  state).

## 2026-08-01 — Declared dataset v0.1 (operator)

- **D-039 — `DATASET_SPEC` §6 "Declared dataset v0.1" added.** The corpus had
  no declaration of what the dataset is or at what scale; this closes it.
  Declares: universe BTCUSDT (O-011 lock), 1h interval, channels `kline`
  (ingested) + `funding` (**declared, ingestion pending**), dev window
  2026-04..06 (hash `8b12707e…`), frozen OOS = first two published months
  after 2026-07-01 + 9-bar label extension (downloaded only at experiment
  time). Scale expectations table is measured (1h tape is small by
  construction: ~640 B/row; full history ~33 MB; 30 symbols ~1 GB; Tier-A/S
  gated by O-010). "More data" is now a register decision, never a silent
  download.
- **Funding gap made explicit and actionable:** simulator funding plumbing
  exists but `funding_rate_r = 0.0` (dev manifest + preregistration §8) — the
  channel is now declared with ingestion pending; next step is
  `GET /fapi/v1/fundingRate` backfill -> `funding` tape rows ->
  `funding_settled_r = entry_price × rate / risk_unit` -> preregistration §8
  revision, all before the holdout is opened (§16).
- Rebuilt `site/index.html` (32 sections — new probe baseline for the next
  session).

## 2026-08-01 — O-017 ratification + preregistration promoted (operator)

- **O-017 resolved by operator ratification** (2026-08-01):
  `execution_share` floor = **0.25** (60% of the dev-window 0.4156) and
  population-divergence threshold = **two-sample KS on `net_R` ≤ 0.20**
  (~2.7× the dev-window 0.073). Both were derived pre-holdout from the
  session-2 baseline (`v8-dev-2026q2-btcusdt`) and are fixed forever — never
  revisable after a verdict. Moved from the open list to a Resolved section
  in `OPEN_DECISIONS.md`; D-027 register entry updated.
- **`PREREGISTRATION_V8_SLICE_001.md` status RATIFIED** (was "frozen content
  for operator approval"); §16(a) marked DONE. The document is now registered
  in `tools/build_monograph.py` NAMES and appears in the monograph (section
  count 31 -> 32).
- The experiment is still **not run**: the frozen holdout does not exist
  until experiment time, no authority receipt exists, and every run's verdict
  stays `NO_ECONOMIC_CLAIM` (rules 8-9, 12).
- Rebuilt `site/index.html` (new probe baseline for the next session).

## 2026-08-01 — Session-2 closure: Phase 1 real data + preregistration (operator pass)

Session 2 (commits `3436248`..`91396fe`) executed Phase 1 on real data and
wrote the `v8_slice_001` preregistration; all 5 steps DONE, suite 42 -> 50
tests, monograph probe byte-identical to the session-2 baseline
(`ea5b7705…`) at every step, corpus untouched (verified independently on
re-review). This operator pass closes the pins the agent left.

- **D-038 registered** — Phase-1 tooling deps (polars/pyarrow/
  pandera[polars]/duckdb) admitted as the `tooling` extra for `tools/data.py`
  + `tools/materialize_views.py`; decision path stays stdlib-only. Resolves
  the session-2 open pin 1.
- **IMPLEMENTATION_LAYOUT updated** — `tools/vision_backfill.py` and
  `tools/materialize_views.py` moved from "planned" into the file family
  (tree + file table); five test files listed.
- **Real tape pinned** — BTCUSDT 1h 2026-04..06 (2184 rows, tape hash
  `8b12707e…`), verified via `data.py`; JSONL PIT tape audit clean;
  materializations + lab run deterministic (ledger `2c1e0fd8…`,
  `NO_ECONOMIC_CLAIM`). Derived artifacts live under `research/tape/`
  (gitignored, reproducible — never committed).
- **`v8_slice_001` preregistration** (`docs/PREREGISTRATION_V8_SLICE_001.md`)
  written with all HYPOTHESIS_LAB_PROTOCOL fields; O-017 proposal (share
  floor 0.25, KS threshold 0.20) derived pre-holdout from the dev baseline
  (execution_share 0.4156, KS 0.073); adversarial review (1 blocker + 7
  warnings) incorporated. **Not yet in the monograph** — it is frozen content
  awaiting operator ratification (§16); holdout not downloaded, experiment
  not run.
- **Carry-forwards (operator + Phase 4):** D-027 verdict gating
  (`execution_share`/divergence/`ATTRIBUTION_UNSAFE_*` in `LabReport`)
  remains code-pending; it lands with the Phase-4 experiment runner. The
  preregistration's §16 operator actions (ratify thresholds; record holdout
  tape hash at download time; authority receipt before any verdict) are
  unperformed by design.
- Rebuilt `site/index.html` (31 sections — the three edited corpus files are
  all monograph sections; the probe baseline for the next session changes).

## 2026-08-01 — Autonomous build session closure (operator pass)

The Phase 0-3 autonomous build (commits `4f34abe`..`f2f8bf2`) completed all
7 runbook steps: the vertical-slice suite grew 15 -> 42 tests, the monograph
probe rebuild was byte-identical to the baseline hash at every step, and the
`docs/` corpus was untouched by the agent (verified independently on
re-review). This operator pass closes the artifacts the agent was not
authorized to write.

- **IMPLEMENTATION_LAYOUT §4 divergence rows closed** with their commits:
  episode_key anchor (D-026, `4f34abe`), funding settlement
  (SIMULATION_TRUTH_SPEC §5/§7, `760e6cc`), D-024 mask (`778ceb1`). The D-026
  key-stability cheap test is now part of the suite (§5 item 4 updated).
- **D-037 registered** — resolves the Step-4 OPEN_PIN: the stdlib mirror of
  `tools/data.py` contracts in `tools/vision_backfill.py` is accepted;
  literal reuse deferred until Phase-1 parquet materialization admits the
  heavy deps. `pyyaml>=6` dev-extra noted (environment, not decision path).
- **`docs/EXPERTS_REGISTRY.yaml` registered in the monograph build** (section
  count 30 -> 31): the Phase-3 expert registry now has a visible home next to
  CLAIMS/EXPERIMENT registries; the agent could not add it to NAMES (docs
  freeze).
- Rebuilt `site/index.html`; runbook Step 3's funding-window interpretation
  and the seed-7 epoch artifact remain recorded in `RUNLOG.md` and
  `docs/STATUS_REPORT.md` (session artifacts, not corpus).

## 2026-08-01 — Autonomous build handoff (design + tooling line)

Design line only; no runtime code changed in this pass.

- **`docs/AGENT_RUNBOOK.md` added** — execution contract for a ~2h
  autonomous build (Phase 0-3). Seven timeboxed steps (D-026 anchor, funding
  settlement, D-024 mask, `vision_backfill.py` + tape audit, feature
  groups/lineage, expert metadata + registry, status report) each with
  owning files, DoD commands, gates, and commit messages. Hard rules: spec
  freeze (agent never edits `docs/` except RUNLOG/STATUS_REPORT), forbidden
  components (rules 6/14), no experiment runs, no frozen-OOS opening,
  tests-as-contract-probes, no `--amend`, no `git add -A`.
- **Anti-drift gate:** every step re-probes the monograph build and requires
  byte-identity with the pre-flight hash — a contract edit would change the
  hash and fail the gate.
- **D-034/035/036 registered** — implementation pins for D-026 (anchor =
  first bar of the setup run via a new 32-bar `history` feature group; key
  drops birth timestamp; `is_duplicate` becomes anchor-key equality),
  funding (`funding_rate_r`/`funding_hours` manifest fields,
  `SETTLEMENT_BEFORE_ORDERS`, `canonical-sim-v4`), and D-024 mask
  (declared constants, `TRADABILITY_MASK_VETO`). The agent implements the
  pins; it does not revisit them.
- `tools/build_monograph.py` NAMES extended (29 -> 30 sections);
  `site/index.html` rebuilt. `RUNLOG.md` template at repo root (session
  artifact, not corpus).

## 2026-08-01 — File-family restructure (code + layout)

- **D-033 — `src/v8/experts/` subpackage.** `experts.py` split into one file
  per behavior family: `experts/base.py` (Expert base + `_need` +
  `still_valid` contract), `experts/trend_pullback.py`,
  `experts/failed_breakout.py`; `experts/__init__.py` re-exports the pilot set
  so `from v8.experts import ...` is unchanged for consumers.
- **`marketstate.py` retained.** The proposed `state.py` rename was rejected
  by the owner — the file mirrors the `MarketState` record name.
- **`lab._code_hash` now recursive (`rglob('*.py')`).** The flat glob missed
  `experts/*.py`, so an Expert change would not have bound the report (D-010).
  Relative path keys keep the hash stable across checkouts.
- `IMPLEMENTATION_LAYOUT.md` §1/§2/§3 updated to the new tree; file-family
  table now covers `experts/` per file. Tests: 15/15 green after the move.

## 2026-08-01 — Architecture + implementation-layout contracts (design line)

Design-line only; no runtime code changed in this pass.

- **`docs/contracts/ARCHITECTURE_SPEC.md` added.** The monograph claimed to be
  an architecture specification but carried only the 5-line minimum-coherent
  diagram. The new contract names the full component map (tape -> MarketState
  -> Experts -> candidate log -> acceptance/RiskGate -> canonical simulator ->
  lab runner -> hash-bound report), the owning contract and gate of every
  stage, the stepped vs counterfactual execution split (D-009/D-027), and the
  absent-by-default list. Registered as **D-031** (technology baseline).
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md` added.** The file family was
  never designed: `src/v8/` files emerged from the vertical slice, and three
  code/spec divergences followed (episode_key, funding, D-024). The contract
  predetermines every file's responsibility, public interface, and owning
  contract; layering rules (acyclic one-way imports, composition root =
  `lab.py`, no wall clock, stdlib-only decision path); a tracked-divergence
  table; and cheap tests including a kept-red D-026 key-stability gate.
  Registered as **D-032**.
- **O-009 scoped:** the storage-engine *design* is resolved by D-031 (Parquet
  archive + JSONL ledgers + DuckDB derived tables per PERSISTENCE_REPLAY_SPEC
  §1); only the scale-validation experiment remains open.
- `tools/build_monograph.py` NAMES extended (27 -> 29 sections);
  `site/index.html` rebuilt. `docs/tr/` remains a partial mirror and skips the
  new sections, consistent with the existing TR lag.

## 2026-08-01 — R-unit correction, excursions, thesis exit (code + design)

- **D-028 — the simulator was not producing R.** `stop_r`/`target_r` were
  applied as fractional price moves (`entry * (1 + target_r)`, so the shipped
  `target_r = 1.0` meant a +100% price target) and `net_r` was a fractional
  return with an R-calibrated cost constant subtracted from it. Measured before
  the fix: a target hit returned −0.0500 and a stop-out −0.0800 — a winning
  trade booked a loss, and every trade was negative regardless of outcome, so
  no Expert could ever have passed. Risk was also invisible: two positions with
  10× different stop width returned identical numbers. R is now an explicit
  declared price distance (`simulator.risk_unit`, from `atr_ref` or a declared
  `risk_frac`), non-positive units fail closed, and the same measurements now
  return +1.9300 / −1.0700 / identical-across-widths. This defect sat under
  D-023: heat summed a quantity that was not risk.
- **D-030 — excursions and ambiguity restored.** `OpenPosition` and
  `CounterfactualOutcome` carry `mae_r`, `mfe_r` and `ambiguous_bars`. The
  vendored V7 simulator (`simtruth/sim.py`) already had `mae_r`/`mfe_r`; the
  V8 canonical simulator had dropped them — a regression on precisely the
  quantity V7 measured as most predictable (ICs +0.124/+0.152 vs +0.015). Same-
  bar stop+target ambiguity was being resolved by `STOP_FIRST` but never
  recorded, contrary to `SIMULATION_TRUTH_SPEC`. O-013 is now answerable and
  the ambiguity bracket measurable.
- **D-029 — post-entry thesis invalidation.** `Expert.still_valid(state, draft)`
  is evaluated on closed bars while a position is `EXECUTED`; a dead thesis
  closes at that bar's close with `THESIS_INVALIDATED`, distinct from `STOP`.
  Implemented for both shipped Experts (trend gone / breakout succeeded after
  all). Deterministic, inside the frozen spec, no new lifecycle state, no
  learned component; fails open when inputs are unobservable.
- Simulator hash bumped to `canonical-sim-v3`; pre-fix ledgers can no longer
  compare equal to post-fix ones.
- Tests: 7 → 15. New golden tests pin stop-out to exactly −1R − cost, target to
  +target_r − cost, R-invariance across 10× risk width, excursion values,
  ambiguity counting with STOP_FIRST, fail-closed risk unit, and the thesis
  exit. Full suite green.
- Not done: funding is still absent from the simulator while
  `SIMULATION_TRUTH_SPEC` §5/§7 mandate `SETTLEMENT_BEFORE_ORDERS` and
  boundary golden tests — material for perps (~3 settlements per 24×1h hold)
  and the V7 audit's one caught defect. `episode_key` still implements the
  D-026 defective form. D-024 tradability mask remains spec-only.

## 2026-08-01 — Attribution validity gate + episode identity (design line)

Design-line only; no code changed in this pass.

- **D-026 — episode identity contradiction resolved.** `episode_key` was
  defined three ways at once: `CANDIDATE_LIFECYCLE_SPEC` §1 (birth timestamp),
  `EXPERT_PROTOCOL` §2 (`setup_anchor_event_id`), and `src/v8/lifecycle.py`
  (birth timestamp). The clock-anchored form is a defect, not a variant: the
  same setup on consecutive bars hashes differently, so the suppression window
  can never match and deduplication silently never fires — confirmed by direct
  execution against `CandidateRegistry.is_duplicate`. §1 is now the single
  normative definition, anchored to `setup_anchor_event_id`; `EXPERT_PROTOCOL`
  references it instead of restating it, and a key-stability cheap test was
  added. **Follow-up: `src/v8/lifecycle.py:36` still implements the defective
  form; spec and code are knowingly divergent until that lands.**
- **D-027 — attribution validity gate (new).** V8 failed closed on data and on
  authority but not on whether the measured population was the traded one. With
  the exposure rule and heat cap enforced against a stepped ledger, rejection is
  the designed outcome for most simultaneous Candidates, so counterfactual
  domination is structural rather than accidental. `LabReport` now carries
  `execution_share` (portfolio-state rejections only in the denominator — cost
  and invalidation rejections are the hypothesis, not bias) plus an
  executed-vs-rejected divergence statistic; breaching either declared bound
  yields `ATTRIBUTION_UNSAFE_LOW_COVERAGE` / `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE`
  rather than a net-utility figure. Refusal, not correction: OPE needs
  propensities a deterministic admission rule cannot produce (rejected
  Candidates have probability 0, the deficient-support case), and two
  independent literature searches returned no admissible finance application.
  Adds no decision-path component; complexity budget (rule 14) untouched.
- **O-014 rewritten, O-017 opened.** O-014's admission condition previously
  called for an OPE correction layer that the evidence does not support; it now
  routes divergence to D-027 instead. O-017 carries the two gate thresholds,
  which must be set from the observed rejection rate before the frozen slice is
  opened.
- Rebuilt `site/index.html` from the corpus. `docs/tr/` remains a partial
  mirror (11 of 27 sections) and does not yet carry D-026/D-027.

## 2026-08-01 — Production-readiness pass

- Repo restructured: `docs/` (corpus, single source of truth), `site/`
  (generated EN/TR monographs), `research/` (papers, text, manifest), `tools/`,
  `src/` (Phase-2 vertical slice). Git initialized.
- Corpus restored from `/tmp` backup (EN + TR); build made reproducible
  (`tools/build_monograph.py`, `site/index.html` and
  `site/tr.html`).
- 42 duplicate PDFs removed (md5-verified), ~88 MB freed.
- New plane specs: `FEED_INGESTION_SPEC`, `PERSISTENCE_REPLAY_SPEC`,
  `RUNTIME_SCHEDULER_SPEC`, `OPERATIONS_SPEC`; decision register extended
  (D-011..D-016).
- Phase-2 vertical slice (`src/v8/`): tape -> MarketState -> experts ->
  candidate lifecycle -> canonical simulator -> hash-bound lab report;
  synthetic-data tests passing.
- Ontology levels + identity metadata adopted (`V8_CONSTITUTION` rule 13;
  `EXPERT_PROTOCOL` section 1); feature-group `requires:` declarations added.
- Exposure-aware acceptance adopted (rule 16; `CANDIDATE_LIFECYCLE_SPEC`
  section 6); `ExposureBook` guard in the vertical slice.
- `LEARNING_PROTOCOL.md` added; online mutation forbidden (rule 15).
- Complexity budget adopted (rule 14).
- Tape compilation discipline adopted (`DATASET_SPEC` section 5; rule 17).
- V7 `lab/` vendored into `src/v8/simtruth/` (canonical reference simulation
  truth; only import paths rewritten) and V7 `tools/data.py` copied to
  `tools/` (canonical Binance archive -> verified tape builder).
  ENGINEERING-ONLY: V8's simulation authority is not renewed by the copy
  (D-022; OPERATIONS_SPEC section 1).
- Project venv via uv (`.venv`, numpy + pytest); 7/7 tests green.
- Roadmap added (`docs/ROADMAP.md`, Phases 0-7 with evidence gates).
- Agentic-coding pass: `CLAUDE.md` at repo root (read order, commands,
  non-negotiable rules); monograph build now emits a table of contents
  (`<nav id="toc">`) with per-section anchors; `site/archive/` removed
  (backed up); `tools/` reorganized (`build_monograph.py`, `heads/`).
- Stepped runtime (CANDIDATE_LIFECYCLE_SPEC section 6 conformance):
  `CanonicalSimulator` split into `step()` (execution ledger — positions live
  across decision clocks) and `run()` (batch counterfactual); `lab.run()`
  drives a 3-phase loop (enter -> step -> trigger -> evaluate); exposure
  conflicts now fire naturally; rejected candidates keep `NOT_EXECUTED`
  counterfactual outcomes — the executed-vs-rejected selection-bias dataset
  is now measurable; `RiskGate` skeleton added (`src/v8/risk.py`), heat
  policy is an open decision.
- Design-phase encoding (index.html only; code paused at user request):
  `CANDIDATE_LIFECYCLE_SPEC` section 6 extended — two-path execution (batch
  counterfactual attribution vs stepped execution ledger, positions live
  across decision clocks), portfolio heat cap (stop-risk R, fixed clusters,
  reject-not-downsize, D-023), mechanical tradability mask (D-024),
  fractional Kelly cap (D-025); open decisions O-013..O-016 (position
  management, selection bias, learned regime veto, drawdown sizing); evidence
  matrix citation verification (two arXiv ID corrections against the reading
  list; four converging literature gaps).
