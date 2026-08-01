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
  experts/           one behavior family per file (D-033)
    __init__.py          pilot expert registry (re-exports)
    base.py              Expert base + _need + still_valid contract
    trend_pullback.py    TrendPullbackExpert
    failed_breakout.py   FailedBreakoutExpert
    liquidity_sweep_reclaim.py  LiquiditySweepReclaimExpert
  lifecycle.py       transition legality, CandidateRegistry, episode_key,
                     ExposureBook
  risk.py            RiskGate (deterministic admission)
  simulator.py       CanonicalSimulator (step/run), OpenPosition, risk_unit
  lab.py             Lab runner (3-phase loop) + recursive code hash
  synth.py           deterministic synthetic tape
  simtruth/          vendored V7 lab — engineering only, authority NOT
                     renewed (D-022)
tools/
  build_monograph.py            docs corpus -> site/index.html, site/tr.html
  data.py                       Binance archive -> verified canonical dataset
                                (download + SHA-256 + Parquet + DuckDB audit)
  vision_backfill.py            Vision monthly klines -> JSONL PIT tape + audit
  materialize_views.py          DATASET_SPEC §5 parquet views (DuckDB,
                                pinned manifest, fail-closed hashes)
  download_v8_reading_list.py   research manifest downloader
tests/
  test_vertical_slice.py        contract tests (pytest)
  test_tape_audit.py            offline tape audit tests
  test_expert_registry.py       registry consistency tests
  test_data_pipeline.py         offline data.py planning/checksum tests
  test_materialize_views.py     materialization roundtrip + fail-closed tests
```

Planned, not yet present: further Expert modules land under
`src/v8/experts/` only after registry admission (the `breakout_retest` and
`capitulation` backlog families are registered DATA_BLOCKED until derivatives
tape — no code module until then); `tools/run_experiment.py` (the
`v8_slice_001` preregistration runner) is the Phase-4 build target.

## 2. File-by-file contract

| File | Responsibility | Public interface | Owning contract |
|---|---|---|---|
| `__init__.py` | package docstring, `__version__` | — | — |
| `schema.py` | canonical frozen dataclasses; `sha1_hex`, `record_dict` | `sha1_hex(obj)`; dataclasses `TapeRow` .. `LabReport` | DATASET_SPEC §1 |
| `store.py` | append-only JSONL log; inbox dedup; canonical replay order | `AppendOnlyLog.append/read/replay_tape/hash` | PERSISTENCE_REPLAY_SPEC §3-4 |
| `marketstate.py` | availability-gated state for decision clock D | `build_state(rows, as_of, universe)`; `FutureRowError` | MARKET_STATE_CONTRACT §1, §6 |
| `experts/__init__.py` | pilot expert registry; stable re-export surface | `from v8.experts import Expert, TrendPullbackExpert, FailedBreakoutExpert, LiquiditySweepReclaimExpert` | EXPERT_PROTOCOL §3 |
| `experts/base.py` | Expert base contract; post-entry thesis predicate | `Expert.evaluate`, `Expert.still_valid`, `Expert._need` | EXPERT_PROTOCOL §2; D-029 |
| `experts/trend_pullback.py` | trend-pullback-continuation family | `TrendPullbackExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `experts/failed_breakout.py` | failed-breakout-reentry family | `FailedBreakoutExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `experts/liquidity_sweep_reclaim.py` | liquidity-sweep-reclaim family (third pilot, D-042) | `LiquiditySweepReclaimExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `lifecycle.py` | legal transitions; registry projection; episode identity; exposure book | `CandidateRegistry.apply/is_duplicate`, `episode_key`, `ExposureBook` | CANDIDATE_LIFECYCLE_SPEC §2; D-018, D-026 |
| `risk.py` | deterministic admission; heat cap | `RiskGate.admit/release`; `RiskVerdict` | CANDIDATE_LIFECYCLE_SPEC §6; D-023 |
| `simulator.py` | canonical Level-1 simulator; R units; excursions; two execution modes | `CanonicalSimulator.step/run/hash`, `risk_unit`, `OpenPosition` | SIMULATION_TRUTH_SPEC; D-028, D-030 |
| `lab.py` | preregistered run: tape -> report; 3-phase loop; composition root; recursive code hash over the whole package | `Lab.ingest/run`; `_code_hash` | HYPOTHESIS_LAB_PROTOCOL; D-010, D-027, D-033 |
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
