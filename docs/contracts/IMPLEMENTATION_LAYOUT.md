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
  vision_backfill.py            Vision monthly klines -> JSONL PIT tape + audit
  build_multi_tape.py           multi-symbol dev tape assembly
  monitor_tape.py               tape integrity monitoring
  materialize_views.py          DATASET_SPEC §5 parquet views (DuckDB,
                                pinned manifest, fail-closed hashes)
  run_experiment.py             preregistration runner (v8_slice_001)
  diagnostics.py                consolidated report centre (single report file;
                                diagnostic.py / diagnostic_report.py /
                                multi_diagnostic.py / forensics.py are shims);
                                S7 port target (D-091) — report/audit artifacts
                                move to report.rs, this file is retired
  diagnose_experts_dev.py       dev-window expert diagnosis
  run_fib_rsi_bb_confluence.py  D-076 dev-window experiment runner
  equity_analysis.py            external-instrument analysis (research only)
  regret.py                     evaluator Phase 0: snapshots, reconciliation,
                                LegalActionManifest, Outcome Cube, gap (D-071);
                                Phase-0 reduction ported as regret.rs (S3),
                                reconciliation stays as S6 parity reference
  regret_reference.py           independent reference walk (parity oracle)
  regret_phase1.py              Candidate-local opportunity accounting (D-072);
                                S6 port target (D-091) — moves to analysis.rs
  regret_phase2.py              systematicity discovery (D-072);
                                S6 port target (D-091) — moves to analysis.rs
  regret_phase3.py              recoverability evaluation (D-073);
                                S6 port target (D-091) — moves to analysis.rs
  artifact_status.py            artifact freshness reporting
  download_v8_reading_list.py   research manifest downloader
  index_handbook_pdf.py, extract_handbook_sections.py,
  extract_handbook_endmatter.py, build_handbook_review.py,
  build_full_handbook_review.py, render_visual_previews.py
                                research-corpus tooling (no decision path)
  _perf_probe.py                scratch profiling harness (not shipped tooling;
                                PERFORMANCE_AUDIT_V82)
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

## 1.1 V8.2 compute core (planned, not yet present)

The Rust workspace is a **second implementation**, not a replacement of §1:
`src/v8/` is frozen as the parity oracle for the duration of the migration
(`PARITY_AND_IDENTITY_SPEC` §2). One workspace, one binary, modules rather than
micro-crates; splitting is deferred until a boundary is proven stable.

```text
v8-core/
  src/
    main.rs         CLI entry; one evaluation request per invocation
    data.rs         Dataset: columnar OHLCV + event/available/ingested clocks
    state.rs        FeatureStore, StateView, feature identity
    experts/
      mod.rs        registry
      predicate.rs  compiled still_valid IR (PREDICATE_IR_SPEC)
    candidate.rs    CandidateBuffer, lifecycle transitions, ExposureBook
    simulator.rs    ReplayKernel (step/run), risk unit, fill policies
    regret.rs       LegalActionManifest, CubeReducer, gap accumulators
    statistics.rs   reductions + verdict statistics (block-bootstrap
                    Reality-Check, detrended null, placebo family; D-044)
    analysis.rs     regret phases 1-3: systematicity, recoverability
    report.rs       verdict report artifacts, ledger audit checks (hash-bound)
    cache.rs        content-addressed DAG cache
    evidence.rs     columnar ledger writer (LEDGER_FORMAT_SPEC)
    compute/        kernels K1..K6 + backend selection
  tests/
    parity.rs       value-level parity against the V8.0 oracle
```

The same file-family rule applies (D-032): a new module, rename, or interface
change is a registry decision with a CHANGELOG entry. Owning contracts are
`COMPUTE_CORE_SPEC` (layers and representation),
`COMPUTE_SCHEDULING_SPEC` (kernels and backends),
`LEDGER_FORMAT_SPEC` (evidence.rs), `OUTCOME_CUBE_SPEC` (regret.rs),
`PREDICATE_IR_SPEC` (experts/predicate.rs) and
`PARITY_AND_IDENTITY_SPEC` (tests/parity.rs).

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
| `tools/vision_backfill.py` | Vision monthly klines -> JSONL PIT tape (three clocks) + audit | CLI `--symbol --interval --month --out [--audit]` | FEED_INGESTION_SPEC §4-5 |
| `tools/materialize_views.py` | DATASET_SPEC §5 parquet views from a pinned manifest; fails closed on hash mismatch | CLI `--manifest --store` | DATASET_SPEC §5; compile-once (rule 17) |
| `tests/test_vertical_slice.py` | runnable contract gates (vertical slice) | pytest | audit gate; PROJECT_EVIDENCE_AUDIT |

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

Divergences are closed by code change; closure is recorded here with the
closing commit and in the CHANGELOG — never by editing this table alone.

## 5. Cheap executable tests

1. Import-boundary test: every `src/v8/` module imports only from its own
   layer or below (§3).
2. No `src/v8/` module references `time.` or `datetime.now`.
3. Two identical `lab.run()` invocations from a fresh store reproduce every
   hash (already in `tests/test_vertical_slice.py`).
4. A D-026 key-stability test (one unchanged setup on two consecutive
   decision clocks yields the same `episode_key`) is part of the suite
   (`tests/test_vertical_slice.py`, build Step 1).
