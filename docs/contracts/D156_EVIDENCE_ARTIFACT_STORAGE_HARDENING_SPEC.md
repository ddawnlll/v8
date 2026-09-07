# D-156 Evidence, Artifact, Statistical, Benchmark, and Cache Hardening Specification

**Status:** `PROVISIONAL_DECISION`

**Date:** 2026-09-06

**Issue set:** #318, #319, #320, #321, #322, #323, #324

**Normative relationship:** This document is the complete authoritative specification for the hardening work represented by issues #318 through #324. It operationalizes D-118 f64 invariant governance and the existing V8 evidence, economic-claim, persistence, and benchmark decisions. It does not replace those decisions, reopen frozen economic evidence, or authorize a predictive-profitability claim.

**Implementation branch:** `audit/research-validity-20260906`

**Related PR:** #331, `fix: harden ledger artifacts, statistics, cache, and benchmark inputs`

This document is intentionally complete. The decision register, changelog, implementation layout, PR description, and monographs are summaries and must link to this file rather than becoming independent specifications.

## 1. Purpose

The work item set addresses a single integrity boundary: V8 must not turn missing, malformed, synthetic, proxy, or unregistered evidence into a plausible-looking economic artifact.

The boundary covers:

1. finite and explicitly absent floating-point values;
2. append-only candidate, cashflow, evidence, and checkpoint persistence;
3. physical artifact identity and replay compatibility;
4. scenario ruin, Monte Carlo resampling, and Slippage-at-Risk absence semantics;
5. standard Parquet publication instead of JSON bytes hidden behind a `.parquet` suffix;
6. statistical kernels that distinguish a diagnostic proxy from a registered estimator;
7. benchmark execution that consumes declared physical inputs and refuses to fabricate a receipt;
8. durable production cache storage with content-addressed validation and migration from legacy JSONL;
9. a complete audit trail for every blocked or admitted path.

The governing principle is:

> Missing authority or missing data is an explicit state. It is never a numeric placeholder, an invented artifact, or an implied economic claim.

## 2. Issue traceability

### 2.1 #318: D-118 f64 invariant governance

D-118 remains the governing source for floating-point identity and invariant policy. D-156 applies that policy at the artifact and evaluation boundaries:

- values exposed as quantitative observations must be finite when present;
- `NaN`, positive infinity, negative infinity, and invalid input series are rejected or converted to an explicit blocked state;
- absence is represented with `Option<T>`, an explicit status, or a typed error;
- a proxy value cannot occupy a field whose name or contract denotes a certified estimator;
- serializers must preserve IEEE-754 `f64` values where a finite scalar is part of the physical artifact contract;
- no consumer may infer zero, false, or a successful gate from an absent value.

D-156 does not introduce a new floating-point tolerance or silently change an existing tolerance. A tolerance change remains a separate decision and must be registered independently.

### 2.2 #319: ledger, checkpoint, and V8.2 artifact hardening

The candidate registry, cashflow ledger, evidence artifacts, retention records, and simulation checkpoints remain append-only or content-addressed at their respective boundaries. Checkpoints are version-bound and tape-hash-bound. V8.2-compatible evidence headers retain their declared generator, version, tier, hash encoding, and run constants. The Python implementation remains frozen and is not reactivated by this work.

### 2.3 #320: scenario Monte Carlo, ruin, and SaR fallback semantics

Scenario simulation may resample only a supplied physical trade population. It may not manufacture a baseline population, offset observations, or use a hardcoded result to make a report appear complete. If trade returns are absent, empty, non-finite, or the replication request is invalid, ruin estimates remain absent and the report is `NO_ECONOMIC_CLAIM`. SaR remains unresolved unless physical liquidity/slippage inputs are supplied.

### 2.4 #321: physical Parquet artifact production

Every output whose contract says Parquet must be a standard, readable Parquet file. The writer publishes atomically, records source-order row indices, preserves canonical source rows in `row_json`, writes nullable typed scalar columns, and records schema and provenance metadata. A file merely containing JSON bytes with a `.parquet` name is invalid.

### 2.5 #322: statistical kernel and proxy DSR/PBO/SPA corrections

The statistical layer must distinguish:

- a genuine estimator with a registered method and authority receipt;
- a diagnostic proxy that can be displayed only as a proxy;
- an underpowered or missing-data result;
- a conservation or lineage failure.

A proxy DSR value is not a genuine DSR result. A multiplicity ledger with no registered PBO/DSR estimator has `None` for those fields and remains `NO_ECONOMIC_CLAIM`. No WRC, genuine DSR, or Hansen SPA certification is generated by implication.

### 2.6 #323: data-backed BenchmarkRunner

`BenchmarkRunner` must validate the declared `BenchmarkEvidenceManifest` and every physical artifact before any evaluator can emit a receipt. It must not synthesize observations, scores, dates, gates, statistical values, population rows, or authority receipts. The current runner deliberately stops with `BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED` after physical input validation because a registered data-backed evaluator and its evidence schema are not yet ratified.

This is a fail-closed completion of the boundary, not permission to restore the historical hardcoded benchmark implementation.

### 2.7 #324: production cache storage adapter

The production cache uses the durable `redb` backend with a versioned canonical key, content-addressed digest, transactional publication, read-back validation, compaction, and guarded migration from valid legacy JSONL records. Malformed, stale, mismatched, or unsupported-version entries are not admitted as cache hits.

## 3. Authority and non-goals

### 3.1 Authority precedence

The following order applies:

1. V8 Constitution and registered D-series decisions;
2. this full-text D-156 specification;
3. the existing Rust type and module contracts listed below;
4. the implementation layout and changelog;
5. tests, reports, and human-readable summaries.

If an implementation conflicts with a higher authority, the implementation fails review. A summary cannot override this specification.

### 3.2 Non-goals

D-156 does not:

- certify profitability or predictive edge;
- promote a diagnostic, synthetic, counterfactual, or proxy result to `SUPPORTED_EDGE`;
- reopen a burned diagnostic tape or frozen holdout;
- introduce a new economic estimator without a separate registered authority receipt;
- reactivate `src/v8/`, root `tests/`, or any deprecated Python runtime;
- add a new hidden cache protocol, artifact format, or benchmark population;
- treat a successful compile as evidence of economic validity;
- use a synthetic fixture in a production, evaluation, findings-ledger, or report-generation path.

## 4. Existing types, traits, and contracts to reuse

The implementation must reuse the following contracts. New parallel types are prohibited unless a later decision explicitly authorizes them.

| Concern | Canonical contract | Required use |
| --- | --- | --- |
| Artifact identity | `v8-core/src/evidence.rs::Artifact`, `RunConstants`, `ArtifactTier`, `RetentionStore` | Preserve hash encoding, tier semantics, run constants, retention resolution, and byte-stable read-back. |
| Candidate persistence | `v8-core/src/candidate.rs::CandidateRegistry`, `TransitionRecord` | Append legal transitions, preserve sequence and event hashes, and fail closed on replay divergence. |
| Cashflow persistence | `v8-core/src/cashflow.rs::CashflowLedger`, `EconomicCashflow` | Preserve conservation checks and physical-ledger provenance. |
| Checkpoint persistence | `v8-core/src/checkpoint.rs::SimulationCheckpoint`, `CheckpointHeader` | Use versioned, tape-bound, atomically published checkpoints. |
| Physical Parquet | `v8-core/src/parquet_artifact.rs::write_json_rows`, `verify_parquet`, `ParquetArtifactReceipt` | Produce and verify actual Parquet files, not disguised JSON. |
| Scenario outputs | `v8-core/src/usdm_sim/scenario_ruin.rs::ScenarioRuinReport`, `SlippageAtRiskReport` | Preserve explicit absence and `NO_ECONOMIC_CLAIM`. |
| Statistics | `v8-core/src/evaluation/statistics.rs` | Reuse `BootstrapResult`, `NullModelResult`, `PermutationResult`, and `ProxyStatistic`; preserve `Result` and `Option` semantics. |
| Multiplicity | `v8-core/src/evaluation/multiple_testing.rs::ResearchMultiplicityLedger`, `MultipleTestingSummary` | Track complete search lineage and trial conservation; do not populate estimator fields without a registered estimator. |
| Benchmark input declaration | `v8-core/src/benchmark/case.rs::BenchmarkCase`, `BenchmarkEvidenceManifest` | Require non-empty case identity and declared physical evidence paths. |
| Benchmark boundary | `v8-core/src/benchmark/runner.rs::BenchmarkRunner` | Validate physical evidence, then fail closed until the evaluator is registered. |
| Cache storage | `v8-core/src/cache.rs::CacheStore`, `CacheEntry`, `canonical_key`, `key_digest` | Use versioned content-addressed redb storage and validated reads. |
| Economic firewall | Constitution Rule 12 and existing claim/status fields | Keep all unresolved, proxy, diagnostic, and unregistered outputs at `NO_ECONOMIC_CLAIM`. |

## 5. Normative requirements

The following requirements are binding.

### R156-01: finite-present invariant

A present quantitative scalar must be finite. Any non-finite scalar entering a statistical, scenario, benchmark, cache, or artifact boundary must be rejected or mapped to an explicit blocked state. The implementation must not silently serialize a non-finite value as a valid observation.

### R156-02: absence preservation

Missing trade populations, missing episode durations, missing regimes, missing liquidity inputs, missing evidence manifests, and missing estimator receipts must remain absent. `None`, a blocked status, and a structured error are valid outcomes. Zero, an empty success receipt, or a fabricated default is not a valid substitute.

### R156-03: no synthetic production input

Synthetic fixtures are permitted only in Rust test modules under `#[cfg(test)]`. Production and evaluation paths must consume physical data or fail closed. Resampling realized input trades for a scenario diagnostic is allowed only when the input population is physically supplied and the resulting output remains `NO_ECONOMIC_CLAIM`.

### R156-04: no hardcoded statistical or economic claim

P-values, effect sizes, PBO values, confidence values, expected improvements, Sharpe-based certification, and profitability conclusions must be computed by a registered estimator over real inputs. Hardcoded values and historical constants cannot be used to satisfy a gate or populate a receipt.

### R156-05: V8.2 artifact lineage

A V8.2-compatible ledger artifact must retain its physical header and identity contract, including generator/version, hash encoding, tier, and run constants. Artifacts with missing or inconsistent headers do not resolve as valid evidence. Frozen Python files remain a parity oracle only and are not modified.

### R156-06: append-only candidate and cashflow persistence

Candidate transitions and physical cashflows must preserve order, legal state transitions, event identity, hash identity, and conservation. A replay mismatch, duplicate inconsistent publication, or malformed record is a hard failure. A later projection cannot rewrite an earlier physical record.

### R156-07: atomic checkpoint publication

A checkpoint writer must create its parent directory, write to a temporary file in the target directory, flush and synchronize the temporary file, atomically rename it into place, and synchronize the containing directory where supported. A checkpoint reader must reject an unsupported version or a tape-hash mismatch.

### R156-08: standard Parquet

`write_json_rows` must produce a file readable by standard Parquet readers. The artifact must include source-order `row_index`, a canonical `row_json` provenance column, nullable typed columns for scalar values, and metadata for artifact kind, row order, f64 encoding, schema manifest, and provenance. Empty or null values must not be converted into an invented zero.

### R156-09: atomic Parquet publication and verification

The Parquet file must be written to a temporary sibling and published atomically. The returned receipt must include the path, row count, column count, byte length, and a verification result. `verify_parquet` must reject an unreadable file and must verify physical row-count readability before a benchmark consumer accepts it.

### R156-10: scenario ruin input boundary

The scenario ruin simulator may consume only the caller-supplied finite `trade_net_rs` population. Empty input, zero replications, or non-finite input produces `DATA_BLOCKED_MISSING_OR_INVALID_TRADE_INPUT`. The baseline builder must not invent a trade tape.

### R156-11: SaR epistemic boundary

The SaR report must retain `Option<f64>` for baseline and tail values when physical liquidity inputs are unavailable. Missing liquidity input produces `UNRESOLVED_MISSING_LIQUIDITY_INPUT`, authority `UNRESOLVED`, and claim `NO_ECONOMIC_CLAIM`. The implementation must not infer slippage from a nominal constant.

### R156-12: genuine estimator distinction

A proxy DSR must carry an explicit proxy status, method version, and `NO_ECONOMIC_CLAIM`. The genuine DSR entry point must refuse execution until a genuine estimator and authority receipt are registered. A proxy cannot be serialized under a genuine-estimator field or consumed by a promotion gate.

### R156-13: multiplicity conservation

The multiplicity ledger must preserve the trial accounting identity `total = survived + pruned + falsified`. It must retain complete family and variant lineage. If there is no search lineage, the status is `DATA_BLOCKED_NO_SEARCH_LINEAGE`. If the lineage is valid but no genuine estimator has consumed it, the status is `MULTIPLICITY_LEDGER_VALID_GENUINE_ESTIMATOR_REQUIRED` and the claim remains `NO_ECONOMIC_CLAIM`.

### R156-14: benchmark physical evidence declaration

A benchmark case must have a non-empty case identifier, case hash, evidence manifest, and evidence paths. Every declared path must physically exist and be readable. A Parquet path must pass the standard Parquet verifier. Other artifact paths must pass filesystem metadata validation.

### R156-15: benchmark evaluator fail-closed boundary

After evidence validation, `BenchmarkRunner` must return `BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED` until a separately registered evaluator consumes the declared data, emits its own receipt, and satisfies the applicable D-series authority. The runner must not call historical synthetic-world helpers or materialize default metrics.

### R156-16: durable cache identity

The cache key must include the version prefix, candidate identity, action identity, simulator hash, and data hash. The digest must be derived only from the canonical key. A cache read is valid only when the stored key, stored digest, requested key, and recomputed digest all agree.

### R156-17: transactional cache publication

Durable cache inserts must be committed in one redb write transaction. A partial write must not become visible as a valid cache hit. Compaction may reduce storage but must not change identity or outcome bytes.

### R156-18: guarded legacy migration

When opening a legacy JSONL cache, the adapter may migrate only valid, supported-version, digest-consistent records into a sibling redb database. Malformed, stale, or mismatched records are skipped and the source JSONL remains available as an audit source. Migration is not a license to reinterpret an entry.

### R156-19: no claim escalation

All D-156 scenario, statistical, benchmark, cache, and artifact outputs are engineering or diagnostic evidence. They cannot render `SUPPORTED_EDGE`, predictive profitability, or production approval. Economic promotion remains governed by the existing WRC, genuine DSR, Hansen SPA, holdout, ledger, and authority requirements.

### R156-20: physical reference integrity

A report, receipt, changelog entry, or specification may reference an artifact path only when the path is a contract path, an explicitly declared input path, or a physically produced and verified output. A fictitious Parquet, ledger, receipt, or table reference is a contract violation.

## 6. Artifact contracts

### 6.1 Evidence artifacts

Evidence artifacts remain governed by `Artifact` and `RunConstants`. The artifact header binds the data, code, configuration, simulator, risk gate, evaluator version, hash encoding, and tier. Readers validate the header before consuming rows. The retention store must resolve the referenced tape hash before the artifact is treated as retained evidence.

### 6.2 Candidate and cashflow ledgers

The candidate registry persists legal transitions and their event hashes. The cashflow ledger persists physical cashflows after the existing conservation checks. These ledgers are not benchmark score stores. A diagnostic or counterfactual value must not be inserted into a realized cashflow field.

### 6.3 Checkpoints

`SimulationCheckpoint` contains a versioned header, bar index, tape hash, and serialized payload. The file publication protocol is temporary write, synchronization, atomic rename, and directory synchronization. Loading with an unexpected version or tape hash returns a checkpoint error. A checkpoint is replay state, not economic evidence.

### 6.4 Parquet

A Parquet artifact has two layers:

1. typed nullable columns for interoperable scalar access;
2. `row_json` for canonical source-row provenance and nested values.

The schema metadata records the artifact kind, source row order, IEEE-754 f64 encoding, a serialized schema manifest, and optional provenance. The adapter does not claim that a Parquet file is authoritative merely because it is readable. Authority comes from the producing contract and receipt.

## 7. Statistical and scenario semantics

### 7.1 Input validation

Statistical functions validate minimum population size, finite values, and requested resampling parameters. Invalid inputs return a `Result` error. Underpowered or unavailable null models return an explicit unresolved result rather than a fabricated statistic.

### 7.2 Null models

The null-model suite can record absent episode duration, absent regime information, or absent benchmark data as unresolved. The absence is part of the result and must be rendered as such. A null-model row cannot be silently dropped and cannot be replaced with a convenient p-value.

### 7.3 DSR, PBO, and SPA

`compute_proxy_deflated_sharpe_ratio` is a mathematical diagnostic with status `PROXY_NOT_GENUINE_DSR`, method version `D153_PROXY_DSR_V1`, and claim `NO_ECONOMIC_CLAIM`. `compute_deflated_sharpe_ratio` returns `BLOCKED_GENUINE_DSR_ESTIMATOR_AND_RECEIPT_REQUIRED` until the genuine estimator is registered.

`MultipleTestingSummary` exposes PBO and family DSR values as `Option<f64>`. They are populated only after a registered estimator consumes complete lineage and emits its own authority receipt. The ledger itself proves trial conservation, not economic significance.

D-156 does not silently implement or certify WRC or Hansen SPA. Those estimators remain separate obligations under Rule 12.

### 7.4 Scenario ruin and SaR

Scenario ruin resamples the supplied realized fractional net-return population. Its status and claim make clear that it is a scenario diagnostic. If no population exists, `build_baseline_scenario_ruin` produces explicit absence. SaR fields remain `None` without physical liquidity inputs. The absence is not a zero-slippage assumption.

## 8. Benchmark execution topology

The intended topology is:

```text
BenchmarkCase
  -> BenchmarkEvidenceManifest
  -> physical path validation
  -> Parquet verification where applicable
  -> registered evaluator boundary
  -> evaluator-owned receipt
  -> ledger / report projection
```

The current implementation stops after physical path validation because the registered evaluator boundary is not present. This is intentional. A future evaluator must be added as a separately reviewed Rust implementation, must have a full-text specification and D-series registration, and must expose its evidence inputs and failure semantics before it can emit a `BenchmarkReceipt`.

The historical implementation that populated hardcoded metrics or synthetic worlds is not an acceptable fallback.

## 9. Cache topology

The cache path is:

```text
canonical key
  -> key version validation
  -> content digest
  -> redb transactional insert
  -> validated read-back
  -> artifact/report consumer
```

The in-memory adapter remains available for unit-level behavior. Production paths opened with `CacheStore::open` use redb. Legacy JSONL migration is one-way into a sibling redb file and does not delete the source audit log.

## 10. Canonical failure semantics

The following strings are stable integration signals and must not be changed silently:

| Boundary | Failure or unresolved state |
| --- | --- |
| Benchmark case | `BLOCKED_INVALID_BENCHMARK_CASE` |
| Missing benchmark manifest | `DATA_BLOCKED_NO_VERIFIED_BENCHMARK_EVIDENCE` |
| Empty benchmark manifest | `DATA_BLOCKED_EMPTY_BENCHMARK_EVIDENCE_MANIFEST` |
| Missing benchmark file | `DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT` |
| Invalid Parquet | `DATA_BLOCKED_INVALID_PARQUET_ARTIFACT` |
| Unreadable benchmark file | `DATA_BLOCKED_UNREADABLE_BENCHMARK_ARTIFACT` |
| Missing evaluator | `BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED` |
| Ruin input | `DATA_BLOCKED_MISSING_OR_INVALID_TRADE_INPUT` |
| Missing liquidity | `UNRESOLVED_MISSING_LIQUIDITY_INPUT` |
| Missing search lineage | `DATA_BLOCKED_NO_SEARCH_LINEAGE` |
| Valid lineage without estimator | `MULTIPLICITY_LEDGER_VALID_GENUINE_ESTIMATOR_REQUIRED` |
| Genuine DSR unavailable | `BLOCKED_GENUINE_DSR_ESTIMATOR_AND_RECEIPT_REQUIRED` |
| Proxy DSR | `PROXY_NOT_GENUINE_DSR` |
| Claim status | `NO_ECONOMIC_CLAIM` |

An error wrapper may add a path or contextual detail after a colon. The semantic prefix must remain machine-detectable.

## 11. Verification contract

The implementation is acceptable only when all applicable checks are run against the isolated PR worktree:

1. `cargo check --manifest-path v8-core/Cargo.toml`;
2. `cargo test --manifest-path v8-core/Cargo.toml`;
3. `cargo clippy --manifest-path v8-core/Cargo.toml`;
4. `.venv/bin/python tools/audit_python_boundary.py`;
5. `python3 tools/audit_synthetic_leakage.py`;
6. `python3 tools/audit_economic_claim.py`;
7. `git diff --check`;
8. standard Parquet read-back and row-count verification tests;
9. checkpoint version and tape-hash rejection tests;
10. cache key, digest, transaction, migration, and stale-entry rejection tests;
11. statistical finite-input, absence, proxy-status, and genuine-estimator blocking tests;
12. benchmark evidence-manifest and evaluator fail-closed tests.

Tests that use synthetic fixtures must remain inside Rust `#[cfg(test)]` modules and must never write production findings, receipts, or reports.

## 12. OPEN_PINs

### OPEN_PIN-156-1: registered data-backed benchmark evaluator

Issue #323 names a data-backed `BenchmarkRunner`, but the repository does not yet contain a ratified evaluator schema that maps physical evidence rows to each benchmark domain, gate, receipt, and authority class. The current runner therefore validates inputs and fails closed. Resolving this pin requires a new full-text evaluator specification, D-series decision, implementation-layout entry, and evidence-backed tests. It must not be resolved by restoring hardcoded metrics or synthetic inputs.

### OPEN_PIN-156-2: genuine multiple-testing estimator receipts

PBO, genuine DSR, WRC, and Hansen SPA remain separate statistical obligations. Their receipt schemas, estimator versions, data-role rules, and authority boundaries must be registered before any value can drive a promotion gate.

### OPEN_PIN-156-3: physical liquidity input contract for SaR

The current SaR output is intentionally unresolved without physical liquidity/slippage observations. A future liquidity provider must define time alignment, venue identity, units, missingness, and authority before the fields can become numeric.

### OPEN_PIN-156-4: D-118 tolerance amendments

D-156 applies existing f64 invariants but does not choose new tolerance values. Any change to tolerance, rounding, or bit-identity semantics requires a separate decision and full-text specification.

## 13. Change and migration rules

- Rust changes belong under `v8-core/`.
- `src/v8/` and root `tests/` are frozen and must not be modified.
- New artifact formats require a D-series decision and a migration or rejection rule.
- New evaluator or estimator code must not share a module path with a proxy implementation in a way that permits type confusion.
- Existing legacy artifacts may be read only through an explicit compatibility adapter with validation.
- Documentation changes require both monographs to be rebuilt.
- The PR may be updated, but no agent may merge it or push directly to `main`.

## 14. Acceptance statement

D-156 is accepted as a provisional hardening decision when:

1. the Rust implementation satisfies the requirements in Section 5;
2. physical Parquet, checkpoint, evidence, ledger, scenario, statistics, benchmark, and cache tests pass;
3. the mandated audits pass without Python-boundary changes or synthetic leakage;
4. the English and Turkish decision registers link to this full-text specification;
5. the implementation layout lists all affected modules and the known evaluator OPEN_PIN;
6. the English and Turkish monographs are regenerated from the synchronized documentation;
7. the PR contains the traceability from issues #318 through #324 to implementation and verification;
8. no receipt or report claims economic support beyond the registered authority actually present.

The unresolved benchmark evaluator and genuine estimator obligations are deliberate, visible, and fail closed. They are not silently marked complete.
