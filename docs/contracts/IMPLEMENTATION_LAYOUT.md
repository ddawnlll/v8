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
  data.py                       V7 Binance archive -> verified tape builder
  download_v8_reading_list.py   research manifest downloader
tests/
  test_vertical_slice.py        contract tests (pytest)
```

Planned, not yet present: `tools/vision_backfill.py` (Phase 1, ROADMAP);
materialization scripts for the `DATASET_SPEC` §5 parquet views (Phase 2);
additional Expert modules land under `src/v8/experts/` only after registry
admission (Phase 3).

## 2. File-by-file contract

| File | Responsibility | Public interface | Owning contract |
|---|---|---|---|
| `__init__.py` | package docstring, `__version__` | — | — |
| `schema.py` | canonical frozen dataclasses; `sha1_hex`, `record_dict` | `sha1_hex(obj)`; dataclasses `TapeRow` .. `LabReport` | DATASET_SPEC §1 |
| `store.py` | append-only JSONL log; inbox dedup; canonical replay order | `AppendOnlyLog.append/read/replay_tape/hash` | PERSISTENCE_REPLAY_SPEC §3-4 |
| `marketstate.py` | availability-gated state for decision clock D | `build_state(rows, as_of, universe)`; `FutureRowError` | MARKET_STATE_CONTRACT §1, §6 |
| `experts/__init__.py` | pilot expert registry; stable re-export surface | `from v8.experts import Expert, TrendPullbackExpert, FailedBreakoutExpert` | EXPERT_PROTOCOL §3 |
| `experts/base.py` | Expert base contract; post-entry thesis predicate | `Expert.evaluate`, `Expert.still_valid`, `Expert._need` | EXPERT_PROTOCOL §2; D-029 |
| `experts/trend_pullback.py` | trend-pullback-continuation family | `TrendPullbackExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `experts/failed_breakout.py` | failed-breakout-reentry family | `FailedBreakoutExpert` | EXPERT_PROTOCOL; ROADMAP Phase 3 |
| `lifecycle.py` | legal transitions; registry projection; episode identity; exposure book | `CandidateRegistry.apply/is_duplicate`, `episode_key`, `ExposureBook` | CANDIDATE_LIFECYCLE_SPEC §2; D-018, D-026 |
| `risk.py` | deterministic admission; heat cap | `RiskGate.admit/release`; `RiskVerdict` | CANDIDATE_LIFECYCLE_SPEC §6; D-023 |
| `simulator.py` | canonical Level-1 simulator; R units; excursions; two execution modes | `CanonicalSimulator.step/run/hash`, `risk_unit`, `OpenPosition` | SIMULATION_TRUTH_SPEC; D-028, D-030 |
| `lab.py` | preregistered run: tape -> report; 3-phase loop; composition root; recursive code hash over the whole package | `Lab.ingest/run`; `_code_hash` | HYPOTHESIS_LAB_PROTOCOL; D-010, D-027, D-033 |
| `synth.py` | deterministic synthetic tape — contracts only, not economics | `make_synthetic_tape(seed, n_bars, symbol, base)` | rule 10 |
| `simtruth/` | vendored V7 reference simulation | import-only rewrite (`sim.py`, `market.py`, `features.py`, `events.py`, `indicators.py`, `evaluate.py`) | D-022; authority stays FAIL |
| `tools/build_monograph.py` | reproducible EN/TR monograph build | CLI `--lang --docs --out` | CHANGELOG build rule |
| `tools/data.py` | V7 Binance archive -> verified tape builder | CLI | FEED_INGESTION_SPEC §5 |
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
| `episode_key` still hashes `birth_time` (clock-anchored form); D-026 requires `setup_anchor_event_id`. The key-stability cheap test in CANDIDATE_LIFECYCLE_SPEC §5 cannot pass until this lands. | `lifecycle.py:36-40` | OPEN — CHANGELOG follow-up |
| Funding settlement absent from the simulator; SIMULATION_TRUTH_SPEC §5/§7 mandate `SETTLEMENT_BEFORE_ORDERS` and boundary golden tests | `simulator.py` | OPEN |
| D-024 mechanical tradability mask is spec-only | — | OPEN (spec-only) |

Divergences are recorded in CHANGELOG entries and are closed by code change
or explicitly rejected — never by editing this table alone.

## 5. Cheap executable tests

1. Import-boundary test: every `src/v8/` module imports only from its own
   layer or below (§3).
2. No `src/v8/` module references `time.` or `datetime.now`.
3. Two identical `lab.run()` invocations from a fresh store reproduce every
   hash (already in `tests/test_vertical_slice.py`).
4. A D-026 key-stability test (one unchanged setup on two consecutive
   decision clocks yields the same `episode_key`) stays pending and red until
   the anchor form lands, so the divergence cannot go quiet.
