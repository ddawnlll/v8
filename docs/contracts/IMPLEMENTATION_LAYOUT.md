# V8 Implementation Layout — file family v0.1

**Status:** PROVISIONAL_DECISION. This contract predetermines every file in
the research runtime — its responsibility, its public interface, and the
contract it implements — before that file is written. A new file, rename, or
interface change is a registry decision with a CHANGELOG entry; the layout
evolves by challenger, never in place (D-032).

## 1. Package layout

```text
src/v8/
  __init__.py        package boundary + version
  schema.py          canonical records + canonical hashing
  store.py           AppendOnlyLog (JSONL, idempotent, replayable)
  marketstate.py     MarketState builder (availability-gated)
  experts/           one behavior family per file (D-033); 28 modules
    __init__.py          expert registry (re-exports)
    base.py              Expert base + _need + still_valid contract
    trend_pullback.py            failed_breakout.py
    liquidity_sweep_reclaim.py   failed_breakout_2b.py
    trend_pullback_depth.py      range_breakout_1to1.py
    candlestick_reversal.py      rsi_stoch_reversion.py
    macd_stoch_trend.py          divergence_12_setups.py
    bollinger_breakout.py        bollinger_reversion.py
    donchian_breakout.py         breakout_retest.py
    fib_retracement_continuation.py  fib_projection_reversal.py
    pattern_measuring_objective.py   volume_confirmed_breakout.py
    volume_climax_reversal.py    obv_adl_regime.py
    ichimoku_cloud.py            floor_trader_pivot.py
    market_profile_value_area.py gap_exhaustion.py
    open_interest_divergence.py  funding_crowding_reversal.py
    pandf_breakout.py            fib_rsi_bb_confluence.py  (D-076)
  lifecycle.py       transition legality, CandidateRegistry, episode_key,
                     ExposureBook
  risk.py            RiskGate (deterministic admission)
  interval.py        base-interval aggregation + derivability (D-053)
  simulator.py       CanonicalSimulator (step/run), OpenPosition, risk_unit
  equity.py          RiskState, drawdown ladder, risk-of-ruin estimate (O-016)
  lab.py             Lab runner (3-phase loop) + recursive code hash
  statistics.py      within-family Reality-Check multiplicity test (D-044),
                     block bootstrap, effective-episode and multiplicity
                     estimators (reused verbatim by the evaluator, D-072);
                     S7 port target (D-091) — verdict statistics move to
                     statistics.rs, this file becomes the parity oracle
  fast.py            content-addressed run / state / evaluation caches (D-085)
  synth.py           deterministic synthetic tape
  simtruth/          vendored V7 lab — engineering only, authority NOT
                     renewed (D-022)
tools/
  build_monograph.py            docs corpus -> site/index.html, site/tr.html
  data.py                       Binance archive -> verified canonical dataset
                                (download + SHA-256 + Parquet + DuckDB audit)
  artifact_status.py            artifact freshness reporting
  download_v8_reading_list.py   research manifest downloader
  index_handbook_pdf.py, extract_handbook_sections.py,
  extract_handbook_endmatter.py, build_handbook_review.py,
  build_full_handbook_review.py, render_visual_previews.py
                                research-corpus tooling (no decision path)
tests/
  test_vertical_slice.py        pipeline contract tests (pytest)
  test_state_cache_identity.py  cached vs uncached MarketState, every bar
  test_expert_<family>.py       one suite per registered Expert (28 families)
  test_expert_registry.py       registry consistency
  test_tape_audit.py            offline tape audit
  test_data_pipeline.py         data.py planning/checksum
  test_materialize_views.py     materialization roundtrip + fail-closed
  test_reality_check.py         within-family multiplicity (D-044)
  test_detrended_null.py        position-bias reproduction + detrending (D-045)
  test_regret_phase0.py         evaluator reconciliation + cube (D-071)
  test_regret_faults.py         evaluator fault injection (D-071)
  test_regret_reference.py      reference-walk agreement (D-071)
  test_fast_cache.py            content-addressed cache behaviour (D-085)
  test_golden_backtest.py       pinned states/ledger hash regression
```

Planned, not yet present: further Expert modules land under
`src/v8/experts/` only after registry admission (the `capitulation` backlog
family is registered DATA_BLOCKED until derivatives tape — no code module
until then).

## 1.1 V8.2 compute core (present — S0..S7 gates passed, D-087..D-095)

The Rust workspace is a **second implementation**, not a replacement of §1:
`src/v8/` is frozen as the parity oracle for the duration of the migration
(`PARITY_AND_IDENTITY_SPEC` §2). One workspace, one binary, modules rather than
micro-crates; splitting is deferred until a boundary is proven stable. The
tree below is the **as-built** layout (approximately 32,258 Rust lines, 62
source files); §4 tracks
where it diverges from `COMPUTE_CORE_SPEC` §6's originally designed module
table.

```text
v8-core/
  src/
    main.rs         CLI entry; one evaluation request per invocation
    data.rs         Dataset: columnar OHLCV + event/available/ingested clocks
    state.rs        FeatureStore, StateView, feature identity
    oracle/         O0–O3 Target Oracle contracts, deterministic grammar,
                    support/authority classification, representational coverage
                    reconciliation, and v8.eval.v1 evidence bundle persistence
      taxonomy.rs    three-role taxonomy, authority/value/refusal vocabulary
      utility.rs     versioned after-cost UtilityContract + hard validation
      information.rs PIT FeatureStore adapter and InformationSet boundary
      opportunity.rs registered primitive/template/grid grammar Candidates
      support.rs     SupportRule and SupportClassifier (O2)
      authority.rs   CounterfactualAuthority and OracleOutcome (O2)
      coverage.rs    Representational coverage reconciliation & bundle receipts (O3)
      artifacts.rs   OpportunityUniverseVersion and OracleEvaluationRecord
    evaluation/     v8.eval.v1 evidence system and Target Oracle coverage support
      allegory.rs    12 market archetypes (A01-A12), negative controls & scorecard (D-125)
      authority_surface.rs 4-axis taxonomy and authority reconciliation
      lineage.rs     population lineage DAG and cross-source reconciliation
      temporal.rs    PIT temporal fault injection and non-interference
      multiple_testing.rs zero-alloc multiple testing & corrections
      agents.rs      typed finding records and deterministic evaluation helpers
      schema_cache.rs evidence-table schema summaries used by coverage receipts
    features.rs     D-053 feature-group projection (Expert FeatMap closure) —
                     not in the original §6 table (§4)
    experts/
      mod.rs        registry
      base.rs       shared Expert contract (mirrors experts/base.py)
      predicate.rs  compiled still_valid IR (PREDICATE_IR_SPEC)
      <28 files>    one behaviour family per module (mirrors D-033),
                     all 28 registered Experts ported (D-092)
    candidate.rs    CandidateBuffer, lifecycle transitions, ExposureBook
    runloop.rs      S4 per-bar composition: ExpertPlane -> candidates -> the
                     `evaluate` subcommand — not in the original §6 table (§4)
    simulator.rs    ReplayKernel (step/run), risk unit, fill policies
    regret.rs       LegalActionManifest, CubeReducer, gap accumulators
    statistics/     verdict statistics — DIRECTORY, not the single
                     `statistics.rs` §6 named (§4)
      mod.rs        the `verdict` subcommand
      reality_check.rs  block-bootstrap Reality-Check (D-044)
      detrended.rs      detrended null, placebo family, Appendix A invariant
      remaining.rs      METH-2..6 surface (D-095)
    analysis/       regret phases 1-3 — DIRECTORY, not the single
                     `analysis.rs` §6 named (§4)
      mod.rs        the `analysis` subcommand
      outcome.rs    per-candidate outcome accounting
      phase1.rs     candidate-local opportunity join
      phase2.rs     72-slice discovery/confirmation family
      phase3.rs     recoverability
      reconcile.rs  CandidateSnapshot join + PIT lineage (D-094)
    report.rs       verdict report artifacts, ledger audit checks (hash-bound)
    cache.rs        content-addressed DAG cache
    evidence.rs     columnar ledger writer (LEDGER_FORMAT_SPEC)
    hash.rs         V8.2 canonical bit encoding (D-079) + BLAKE3/SHA-256 (D-120)
    jsonx.rs        Python-json-compatible tape parser (NaN/Infinity literals)
    mt19937.rs      bit-exact CPython Mersenne Twister — not in the original
                     §6 table (§4)
    error.rs        strongly-typed V8CoreError taxonomy (D-119, #208)
    path_security.rs path sanitization & traversal defense (D-120, #209)
    telemetry.rs    tracing & metrics facades (D-120, #209)
    checkpoint.rs   atomic simulation checkpoint & resume engine (D-122, #211)
    authority.rs    3D Authority Tensor (Evidence, Decision, Realization) & ClaimValue<T> (D-132)
    claims.rs       6 statutory claim classes, ClaimRegistry & RendererFirewall (D-132)
    audit/          Central Constitutional Audit Kernel & 8 Sabotage Invariants (D-132)
      mod.rs        audit plane boundary
      authority.rs  authority monotonicity & receipt verification
      lineage.rs    Point-In-Time zero future-leakage audit
      cashflow.rs   double-entry conservation invariant
      reconciliation.rs witness Merkle root & clone collapse verification
      independence.rs dual-key implementer != auditor separation
      sabotage.rs   8-point automated audit-of-audit sabotage suite
    backend/        ReplayKernel boundary + scalar, CPU/SIMD, optional GPU and
                    ExecutionBackend venue physics instruments (D-098, D-132)
      execution.rs  ExecutionBackend trait & BinanceUsdmExecutionBackend physics instrument
    kaizen/         Sovereign Kaizen research, experiment & verdict engine (D-132)
      controller.rs KaizenController orchestrating hypotheses, ledger & claims
      verdict.rs    KaizenVerdictEngine (sole source of normative verdicts)
    judiciary/      Judicial Review, Execution Oversight & Accountability Plane (D-134)
      mod.rs        Judiciary plane boundary & re-exports
      mandate.rs    Typestate ExecutionMandate, MobilizationTier, TaskLease & Capability Scopes
      veto.rs       VetoProof, JudicialVetoGate, No-Naked-Veto & ExpeditedAppealEngine
      oversight.rs  ProceduralCommissioner, TechnicalCommissioner, BlindAuditBundle & GovernanceReceipt
      kaizen_boundary.rs External Constitutional Audit & Dual-Key separation for Kaizen
      tests.rs      Comprehensive unit and property tests
    shadow.rs       Hash-bound prospective shadow manifest, cutoff gate, and
                    canonical artifact bundle verifier (D-138)
    opportunity/    V8.3 Opportunity Sovereignty plane (D-128, D-129, D-130, D-132)
      mod.rs        7 canonical primitives & OpportunityBook interface
      exposure.rs   EconomicExposureStructure, ExposureResolver, false-collapse defense
      book.rs       OpportunityEpisode & OpportunityBook
      grammar.rs    Point-in-Time causal OpportunityGrammar
      evidence.rs   ObserverEvidence, typed stances & 9D WitnessScorecard
      reconcile.rs  Dependence-aware EvidenceReconciler, ReconciliationReceipt & N_eff collapse
      utility.rs    SelectiveUtility & cost/friction hurdle filtering
      campaign.rs   ExecutionCampaign & PortfolioFeasibilityEngine
      runloop.rs    V8.3 end-to-end Opportunity Runloop & ledger emission
      harness_t1_t12.rs Constitutional Invariant Harness T1–T12
      funnel.rs     Opportunity Capture Funnel & Attrition Diagnostic Engine (Phase II)
    scheduler.rs    deterministic task scheduling/chunking, evaluate_typed (D-119)
    runloop.rs      S4 per-bar composition and runtime dispatch wiring
  tests/            empty — parity is proven by #[cfg(test)] unit tests
                     embedded in each src/*.rs module plus the Python-side
                     harness at repo-root tests/parity/*.py, not a Rust
                     tests/parity.rs integration file as §6 originally named
```

The same file-family rule applies (D-032): a new module, rename, or interface
change is a registry decision with a CHANGELOG entry. Owning contracts are
`COMPUTE_CORE_SPEC` (layers and representation),
`COMPUTE_SCHEDULING_SPEC` (kernels and backends),
`LEDGER_FORMAT_SPEC` (evidence.rs), `OUTCOME_CUBE_SPEC` (regret.rs),
`PREDICATE_IR_SPEC` (experts/predicate.rs) and
`PARITY_AND_IDENTITY_SPEC` (tests/parity/*.py).

## 2. File-by-file contract

| File | Responsibility | Public interface | Owning contract |
|---|---|---|---|
| `__init__.py` | package docstring, `__version__` | — | — |
| `schema.py` | canonical frozen dataclasses; `sha1_hex`, `record_dict` | `sha1_hex(obj)`; dataclasses `TapeRow` .. `LabReport` | DATASET_SPEC §1 |
| `store.py` | append-only JSONL log; inbox dedup; canonical replay order | `AppendOnlyLog.append/read/replay_tape/hash` | PERSISTENCE_REPLAY_SPEC §3-4 |
| `marketstate.py` | availability-gated state for decision clock D | `build_state(rows, as_of, universe)`; `FutureRowError` | MARKET_STATE_CONTRACT §1, §6 |
| `experts/__init__.py` | expert registry; stable re-export surface (3 pilots + 24 extraction families, D-050) | `from v8.experts import Expert, <28 Expert classes>` | EXPERT_PROTOCOL §3; D-042, D-050 |
| `experts/base.py` | Expert base contract; post-entry thesis predicate | `Expert.evaluate`, `Expert.still_valid`, `Expert._need` | EXPERT_PROTOCOL §2; D-029 |
| `experts/trend_pullback.py` | trend-pullback-continuation family | `TrendPullbackExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `experts/failed_breakout.py` | failed-breakout-reentry family | `FailedBreakoutExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `experts/liquidity_sweep_reclaim.py` | liquidity-sweep-reclaim family (third pilot, D-042) | `LiquiditySweepReclaimExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `lifecycle.py` | legal transitions; registry projection; episode identity; exposure book | `CandidateRegistry.apply/is_duplicate`, `episode_key`, `ExposureBook` | CANDIDATE_LIFECYCLE_SPEC §2; D-018, D-026 |
| `risk.py` | deterministic admission; size-aware heat (`size*stop_r`); equity drawdown ladder; trade-unit/min-trades gates | `RiskGate.admit/release`; `RiskVerdict`; `equity.RiskState` | CANDIDATE_LIFECYCLE_SPEC §6; D-023, D-048 |
| `equity.py` | deterministic fixed-fractional equity + drawdown ladder (RM-06/O-016 challenger) and trade-unit budget (RM-07) | `RiskState`, `DRAWDOWN_BANDS`, `trade_units_for` | CANDIDATE_LIFECYCLE_SPEC §6; D-048 |
| `simulator.py` | canonical Level-1 simulator; R units; excursions; breakeven/trail/scale-out/pyramid/FILL_AT_LIMIT/TIME_EXIT (EXEC-1..6); two execution modes | `CanonicalSimulator.step/run/hash`, `risk_unit`, `OpenPosition`; sim.hash() v7 | SIMULATION_TRUTH_SPEC; D-028, D-030, D-047 |
| `lab.py` | preregistered run: tape -> report; 3-phase loop; composition root; recursive code hash over the whole package | `Lab.ingest/run`; `_code_hash` | HYPOTHESIS_LAB_PROTOCOL; D-010, D-027, D-033 |
| `statistics.py` | (a) block-bootstrap Reality-Check max-statistic test over a family's `variants_evaluated` episode series (White 2000 Procedure RC); stdlib-only, explicit seed, aligned-episode-grid inputs only (cross-family pooling deferred, O-021). (b) the detrended null: same-exposure passive benchmark per episode, the zero-skill placebo family, and the Appendix A invariant check. `invariant_holds` is intentionally unimplemented and raises — its tolerance is a preregistered constant awaiting an operator choice | `reality_check_p_value`, `select_block_size`, `EpisodeExposure`, `mean_log_drift_per_bar`, `passive_benchmark_r`, `detrend_net_r`, `placebo_exposures`, `appendix_a_invariant` | PREREGISTRATION_V8_SLICE_001 §11; D-044, D-045 |
| `synth.py` | deterministic synthetic tape — contracts only, not economics | `make_synthetic_tape(seed, n_bars, symbol, base)` | rule 10 |
| `simtruth/` | vendored V7 reference simulation | import-only rewrite (`sim.py`, `market.py`, `features.py`, `events.py`, `indicators.py`, `evaluate.py`) | D-022; authority stays FAIL |
| `tools/build_monograph.py` | reproducible EN/TR monograph build | CLI `--lang --docs --out` | CHANGELOG build rule |
| `tools/data.py` | Binance archive -> verified canonical dataset (download + SHA-256 + Parquet + DuckDB audit) | CLI `build/verify/audit/load` | FEED_INGESTION_SPEC §5; DATASET_SPEC §1 |
| `tests/test_vertical_slice.py` | runnable contract gates (vertical slice) | pytest | audit gate; PROJECT_EVIDENCE_AUDIT |
| `v8-core/src/error.rs` | Strongly-typed central runtime error taxonomy (`V8CoreError`) | `V8CoreError` enum + error conversions | COMPUTE_CORE_SPEC §4; D-119 |
| `v8-core/src/path_security.rs` | Path sanitization & traversal defense | `sanitize_path` | FEED_INGESTION_SPEC §5; D-120 |
| `v8-core/src/telemetry.rs` | Structured tracing & metrics facades | `init_telemetry`, `record_duration_metric` | OPERATIONS_SPEC §2; D-120 |
| `v8-core/src/checkpoint.rs` | Atomic simulation state checkpoint & resume | `SimulationCheckpoint.save_to_file/load_from_file` | PERSISTENCE_REPLAY_SPEC §4; D-122 |
| `v8-core/src/evaluation/allegory.rs` | 12 market archetypes, negative control calibration, zero-hindsight regret evaluation & scorecard | `AllegoryFamily`, `ArchetypeId`, `AllegoryScorecard`, `evaluate_allegory_suite` | TARGET_ORACLE_SPEC §9; D-125 |
| `v8-core/src/opportunity/` | V8.3 Challenger Opportunity Sovereignty Engine (7-primitive space, evidence reconciliation, selective utility, basis protection) | `OpportunityGrammar`, `OpportunityBook`, `ExpertWitness`, `EvidenceReconciler`, `ExposureStructure` | V8_CONSTITUTION v0.2 Rules 18–27; D-128..D-130; CC-RES-V8.3-GL-001 |
| `v8-core/src/judiciary/emergency.rs` | Emergency Mainline Execution Authority, Scope Firewall & `EmergencyMergeWarrant` Protocol | `EmergencyMergeWarrant`, `WarrantLifecycleState`, `MainlineHeadStatus`, `EmergencyIncidentReason` | V8_CONSTITUTION v0.2 Rule 43; D-135; CC-BILL-V8.3-D135 |
| `v8-core/src/shadow.rs` | Non-economic prospective shadow boundary; seals code/config/dataset/authority/freeze identities, enforces strict future-only observations, writes allocation-neutral receipts, binds declared diagnostic bundles, and rejects mixed/divergent output bundles | `ProspectiveShadowManifest`, `ShadowRequest`, `ShadowReceipt`, `ArtifactIndexRequest`, `CanonicalArtifactIndex`, `verify_output_bundle`, `index_artifacts` | `OPERATIONS_SPEC` §1, §4–§6; `PERSISTENCE_REPLAY_SPEC` §4, §8; D-138; Issues #256/#258 |


## 3. Layering rules

- Import direction is acyclic and one-way:
  `schema <- store <- marketstate <- experts <- lifecycle <- risk <- simulator <- lab`.
  `lab.py` is the composition root; nothing imports it. `simtruth/` is a leaf
  used only by research tooling and differential tests, never by the
  decision path.
- A module imports only from its own layer or below; violations are caught by
  an import-boundary test, not by convention. Expert files import only
  `experts/base.py` and `schema.py`; they never import lifecycle, risk,
  simulator, or lab.
- No module reads the wall clock; all clocks are integer nanoseconds carried
  on tape rows and decision artifacts (PERSISTENCE_REPLAY_SPEC §4).
- The decision path (`src/v8/` minus `simtruth/`) is stdlib-only; `numpy`
  never crosses that boundary.

## 4. Known code/spec divergences (tracked, never silent)

| Divergence | Location | Status |
|---|---|---|
| `episode_key` clock-anchored form (D-026) | `lifecycle.py` | **CLOSED** — `4f34abe` (build Step 1): anchor = first bar of the setup run via the `history` group; key drops the birth timestamp; `is_duplicate` = anchor-key equality |
| Funding settlement absent (SIMULATION_TRUTH_SPEC §5/§7) | `simulator.py` | **CLOSED** — `760e6cc` (build Step 2): `funding_rate_r`/`funding_hours` manifest fields, `SETTLEMENT_BEFORE_ORDERS`, boundary goldens, `canonical-sim-v4` |
| D-024 mechanical tradability mask spec-only | `risk.py` + `lab.py` | **CLOSED** — `778ceb1` (build Step 3): declared constants, `TRADABILITY_MASK_VETO`, `NOT_EXECUTED` counterfactual |
| `statistics.rs`/`analysis.rs` designed as single files (`COMPUTE_CORE_SPEC` §6) | `v8-core/src/statistics/` (4 files, 2,373 lines), `v8-core/src/analysis/` (6 files, 5,030 lines) | **DOCUMENTED, not reversed** — `17e506a`/`5accfc6` (S4-S7 Waves): each surface grew past a comfortable single file during the S6/S7 port (D-091's bounded-surface estimate — `regret_phase1/2/3.py` ≈27 KB, `statistics.py` 767 lines — held for total scope but not for single-file ergonomics); split by pipeline stage (`phase1`/`phase2`/`phase3`/`reconcile`/`outcome` under `analysis/`, `reality_check`/`detrended`/`remaining` under `statistics/`) rather than left as one growing file. Functionally equivalent to the spec's module list; `COMPUTE_CORE_SPEC` §6 itself is left as the original design record, not rewritten |
| `features.rs`, `runloop.rs`, `mt19937.rs` absent from `COMPUTE_CORE_SPEC` §6's module table | `v8-core/src/features.rs`, `runloop.rs`, `mt19937.rs` | **DOCUMENTED, not reversed** — `17e506a` (`features.rs`, `mt19937.rs`) / `5accfc6` (`runloop.rs`): the S4-S7 design pass discovered three roles the original 12-module table did not name — the D-053 per-Expert feature-group projection (distinct from `FeatureStore`/`StateView`'s whole-tape feature computation), the S4 per-bar composition loop binding `ExpertPlane` output into `CandidateBuffer` (the `evaluate` subcommand's own logic, not reducible to either), and bit-exact CPython RNG reproduction required for S7 verdict-statistics parity. None replaces a named module; each is additive (D-092/D-095) |
| `tests/parity.rs` designed as a Rust integration-test file (`COMPUTE_CORE_SPEC` §6) | `v8-core/tests/` is empty; parity is proven by `#[cfg(test)]` unit tests inside each `src/*.rs` module plus the Python-side harness `tests/parity/*.py` at the repo root | **DOCUMENTED, not reversed** — `17e506a` onward: every stage gate (S0..S7) is driven from the Python side because the oracle (`src/v8/`) it compares against is Python; a Rust-only `tests/parity.rs` would need to re-embed or shell out to the oracle for no benefit over the existing harness. `PARITY_AND_IDENTITY_SPEC` §5.2 already specifies the Python-driven harness; §6's `tests/parity.rs` line predates that specification |
| Core modernization modules (`error.rs`, `path_security.rs`, `telemetry.rs`, `checkpoint.rs`, `Dataset::from_mmap_path`) | `v8-core/src/{error, path_security, telemetry, checkpoint, data}.rs` | **DOCUMENTED, not reversed** — D-119..D-122 (Issue #208..#211): Added strongly-typed error taxonomy, path sanitization, metrics/tracing facades, atomic simulation checkpointing, and zero-copy mmap streaming to harden core production runtime |

Divergences are closed by code change; closure is recorded here with the
closing commit and in the CHANGELOG — never by editing this table alone.
Divergences that are accepted architecture rather than defects awaiting a fix
are marked **DOCUMENTED, not reversed** instead of CLOSED — the code is not
expected to change to match the spec; the spec's original text is left as the
historical design record and this table is the correction layer.

## 5. Cheap executable tests

1. Import-boundary test: every `src/v8/` module imports only from its own
   layer or below (§3).
2. No `src/v8/` module references `time.` or `datetime.now`.
3. Two identical `lab.run()` invocations from a fresh store reproduce every
   hash (already in `tests/test_vertical_slice.py`).
4. A D-026 key-stability test (one unchanged setup on two consecutive
   decision clocks yields the same `episode_key`) is part of the suite
   (`tests/test_vertical_slice.py`, build Step 1).
