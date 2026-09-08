# Repository performance audit — 2026-09-08

## 1. Executive summary

**The measured problem is primarily compilation plus duplicated simulation work, not test discovery.** At audited commit `7840520e`, the unmodified full Rust suite does not compile: its consolidated integration target has 13 errors. After two temporary, semantics-preserving compile repairs, the README-style warm command took **11.14 and 10.85 seconds**. A clean offline test build took **104.19 seconds**, excluding execution. These are different cache states, not contradictory measurements.

The library and CLI independently compile shared source modules and execute **443 identically named tests twice**. The library has 475 tests; the CLI has 443. In a serial library run, four tests consumed **78.2%** of measured test-body time; 24 tests (5.1%) consumed **96.9%**. The biggest test runs five full historical simulations. Removing duplicate execution while retaining one copy of every assertion is the strongest demonstrated warm-loop opportunity. Compilation has a broader dependency and crate-boundary problem.

Several apparent speedups are false: running binaries from the repository root silently bypasses three historical simulation tests; absent local market data does the same; warm Cargo no-op checks say nothing about a source edit; shared output directories can reuse stale cashflows. These conditions must be controlled before comparing results.

**Expected improvement:** eliminating the CLI's duplicated suite could remove approximately 4–5 seconds from the measured warm loop, subject to preserving CLI coverage. Sharing immutable feature stores across five simulation arms saves approximately 0.28–0.30 seconds of repeated loading, not several seconds. A 5–7 second warm full-loop target is plausible from these measured removable costs, but is not a validated optimized implementation. No defensible large cold-build speedup is established yet.

The largest architectural problem is dual ownership of the same Rust modules by library and executable crates. Test taxonomy and isolation are also defective. Runtime costs are highly localized; compile cost is distributed across dependencies and duplicate crate compilation.

## 2. Baseline and experimental conditions

- Host reports 11 logical CPUs and 19,327,352,832 bytes RAM (18 GiB); macOS arm64. Rust `1.96.0-nightly (562dee482 2026-03-21)`, Cargo `1.96.0-nightly`.
- Other applications and agent processes were active. Some snapshots showed unrelated processes consuming whole cores; filesystem activity and free disk space changed during the audit. No unrelated process was stopped. These are workstation observations, not quiet-machine benchmark guarantees.
- Initial working tree was clean; later concurrent edits are documented below. No Python source or test files were changed. Temporary Rust probe and compile repairs were restored after measurement.
- First build: 13 compile errors, 26.86 seconds wall, 80.38 user, 5.95 system. Eight invalid inner doc comments in `tests/suites/causal_future_shock.rs`, five obsolete `CapabilityScorer` references in `tests/suites/d153_benchmark_fabric_sabotage.rs`.
- Repairs used for measurement only: inner doc comments converted to ordinary comments; obsolete type name replaced with existing `CapabilityScoreCalculator`. No tests/assertions were removed. All successful full-suite figures are conditional on those repairs.
- `cold` means an empty Cargo target directory with the registry already available and `--offline`. It does **not** mean empty OS page cache, fresh network downloads, or a reboot. First-seen existing-target numbers are explicitly distinguished from cold numbers.
- `/usr/bin/time -l` measured wall/user/system time and resource counters. Nightly libtest JSON with `--report-time` measured test bodies. Cargo HTML timing data measured compilation units. A two-second macOS `sample` capture profiled the slowest simulation test.
- Direct harness runs use `v8-core/` as working directory to match Cargo. Early root-directory runs are excluded from canonical runtime rankings because they silently skipped work.
- Warm root-command build fingerprint has `rustflags: []`. From `v8-core/`, Cargo configuration reports `-C llvm-args=--fp-contract=off`. Root invocation with `--manifest-path` does not read the nested Cargo config. Canonical-config measurements below are separate.

### Existing-target workflows, root invocation

Times are seconds. Typecheck is `cargo check`; lint is `cargo clippy --all-targets`. First-seen is not a clean build.

| Workflow | Cold | First seen | Warm repeat | Notes |
|---|---:|---:|---:|---|
| Full test command | Not measured as one cold command | 11.14 | 10.85 | After repairs; no compiler flags; 1,180 passing executions |
| Test compilation only | 104.19 | 26.86 failed; 2.89 repaired target | 0.33 / 0.20 | Cold build uses empty target and offline registry |
| Library unit/component bodies | Not OS-cold | 4.354 | 4.587 | Normal parallel, correct cwd; 475 tests |
| CLI duplicated unit bodies | Not OS-cold | 4.424 | 4.331 | 443 tests; all names also in library |
| Integration bodies | Not OS-cold | 0.622 | 0.055 | 262 tests across ten integration targets |
| Typecheck | Not clean-target in this table | 0.17 | 0.16 | Existing metadata; not edit latency |
| Dev build | Not clean-target in this table | 24.21 | 0.09 | First invocation rebuilt local crate; dependencies cached |
| All-target lint | Not clean-target in this table | 11.93 | 0.14 | First invocation checked local targets |
| Python boundary audit | Not measured | 0.11 | — | Pass |
| Synthetic-leakage audit | Not measured | 0.15 | — | Pass |
| Economic-claim audit | Not measured | 0.15 | — | Pass |
| Forbidden-name audit | Not measured | 0.21 | — | Pass |
| Legacy Python collection | Unavailable | 0.05 failure | — | `.venv/bin/python` has no pytest; no test timing claim |

The complete measured concurrency/suite dataset is in `suite-timings.csv`; serial per-test observations are in `serial-test-timings.json`. Those raw names distinguish library, CLI, and integration targets.

### Canonical compiler configuration

The canonical clean offline test build took **91.82 s wall / 668.77 user / 29.10 system**. This is a second clean build with different flags, later in the session; the difference from 104.19 s is **not** a measured flag optimization.

| Canonical workflow | First execution / compile | Notes |
|---|---:|---|
| Clean test build | 91.82 s | Empty separate target; required FP flags |
| Incremental test build after external registry-test edit | 21.78 s | Source changed; not a no-op warm run |
| Full tests, prebuilt new executables | 15.45 s | 476 library + 444 CLI + 262 integration executions pass; first-launch overhead included |
| First metadata typecheck | 19.94 s | Includes dependency metadata work in new target |
| First dev build | 19.89 s | Test artifacts existed; dev-profile local code rebuilt |
| First all-target clippy | 16.33 s | New target lint pass |

**Concurrent source changes:** while the later canonical measurements were running, another actor added a registry test, changed CI, then edited `state.rs` and `usdm_sim.rs` funding logic. The next supposedly warm no-run command therefore rebuilt for 50.47 s. It is excluded from warm/no-change claims. No later mixed-revision results are used to infer baseline speedups. Initial root-config repeated timings and serial rankings precede these edits; the cold-built original executable was retained for the final fresh-output equivalence check. These concurrent edits remain untouched.


### Reproduction

```sh
# Audited original revision: fails in integration_tests.
cargo test --manifest-path v8-core/Cargo.toml --no-run
# Correct compiler-policy lookup:
(cd v8-core && cargo -Z unstable-options config get build.rustflags)
# Run from v8-core with documented compile-only repairs when reproducing this audit:
(cd v8-core && /usr/bin/time -l cargo test --offline)
# Build separately and collect executable paths:
(cd v8-core && cargo test --no-run --message-format=json)
# Each test executable, cwd=v8-core:
/path/to/test-binary -Z unstable-options --format json --report-time --test-threads 1
# Repeat with 2, 4, 11 and without --test-threads.
# Cold compilation, preserving existing target cache:
(cd v8-core && /usr/bin/time -l cargo test --offline --no-run --target-dir /tmp/v8-audit-clean --timings)
```

Do not treat the temporary probe's filtered execution as full validation. The probe ran only real tape prefixes within `#[cfg(test)]`, wrote into an isolated audit directory, and was removed.

## 3. Runtime breakdown

The 10.85-second warm root-command run includes compilation freshness checks, test processes, test work, and rustdoc startup. The paired instrumented harness sweep took 8.972 seconds of summed **suite elapsed time**; it is a separate run and cannot be subtracted to manufacture exact overhead percentages. Parallel per-test times overlap and must not be summed into a wall-time pie chart.

Within one serial library run, where per-test sums are meaningful:

| Category | Sum of test-body time | Share of 7.087-second measured bodies |
|---|---:|---:|
| Three USD-M historical simulation tests | 4.794 s | 67.6% |
| Runloop component/storage tests | 1.062 s | 15.0% |
| H4 historical diagnostic/report generator | 0.748 s | 10.5% |
| All remaining library bodies | 0.483 s | 6.8% |

The serial library harness reports 7.108 seconds, leaving approximately 0.021 seconds inside the harness outside measured bodies. Setup and teardown **inside each test** are included in body timings. No independent global setup hook exists in the Rust harness. Destructors, file cleanup, fixture construction, assertions and computation cannot all be separated from existing libtest data; the high-level probe below provides that separation only for simulation setup.

The clean build consumed 703.21 user + 33.44 system seconds over 104.19 wall seconds: approximately seven CPU cores of aggregate work. Maximum resident size reported by `time` was 1.81 GB; this is not total simultaneous process-tree memory. The library warm run consumed 6.48 user + 0.36 system over 4.59 wall seconds. Neither result supports describing the main cost as network waiting.

Discovery is Rust's compiled list, not recursive test-source interpretation. Direct `--list` costs were at hundredth-second timer resolution for the initial warm executables. Cargo discovers test targets from `Cargo.toml` and immediate integration files, then launches binaries; it does not traverse `research/`, `.worktrees/`, or all build artifacts to discover tests. Process startup occasionally had first-launch spikes (the new integration binary took 0.34 seconds externally but only 0.012 seconds inside its harness); that spike is observed, but attribution to dyld/security scanning is unproven.

## 4. Slowest components

Rankings use serial runs to avoid attributing contention to intrinsic test work. Canonical source filenames are shown for module groups; source files shared by the library and CLI are executed twice. Files beyond the dominant handful are too small to justify individual optimization.

Top 20 named tests, summing repeated executions across targets:

| Rank | Test | Serial seconds | Executions |
|---|---|---:|---:|
| 1 | `usdm_sim::tests::test_a0_vs_a1_breakeven_challenger_comparative_receipt` | 6.769 | 2 |
| 2 | `usdm_sim::tests::test_v83_comprehensive_economic_loss_anatomy` | 1.607 | 2 |
| 3 | `opportunity::funnel::tests::test_h4_conflict_source_decomposition` | 1.568 | 2 |
| 4 | `usdm_sim::tests::test_usdm_sim_execution_on_certified_tape` | 1.357 | 2 |
| 5 | `runloop::tests::cube_reduced_is_byte_identical_across_thread_counts` | 0.662 | 2 |
| 6 | `runloop::tests::candidate_count_matches_direct_evaluate` | 0.307 | 2 |
| 7 | `runloop::tests::lifecycle_admission_releases_closed_exposure_after_expiry` | 0.211 | 2 |
| 8 | `runloop::tests::isolated_tracks_admits_all_candidates_without_contention` | 0.202 | 2 |
| 9 | `oracle::coverage::tests::acceptance_test_6_g4_g5_determinism_and_bundle_artifacts` | 0.167 | 2 |
| 10 | `runloop::tests::duplicate_setup_yields_one_candidate_one_suppressed` | 0.163 | 2 |
| 11 | `runloop::tests::second_same_direction_candidate_is_rejected` | 0.155 | 2 |
| 12 | `runloop::tests::slot_conflict_resolves_by_declared_hash_order_not_alphabetical` | 0.098 | 2 |
| 13 | `cache::tests::durable_store_round_trips_across_reopen` | 0.097 | 2 |
| 14 | `runloop::tests::pre_entry_invalidation_fires_on_windowed_prior_extreme` | 0.093 | 2 |
| 15 | `runloop::tests::warmup_boundary_bb_experts_no_usize_underflow` | 0.083 | 2 |
| 16 | `runloop::tests::test_portfolio_allocation_records_emitted` | 0.082 | 2 |
| 17 | `evidence::tests::headers_carry_required_run_constants_for_all_kinds` | 0.065 | 2 |
| 18 | `evidence::tests::ledger_battery_all_six_cheap_tests_pass` | 0.059 | 2 |
| 19 | `cache::tests::stale_or_corrupt_entries_are_not_cache_hits` | 0.054 | 2 |
| 20 | `runloop::tests::standalone_cube_candidate_without_entry_is_reduced_by_shared_producer` | 0.043 | 2 |


Top 20 source files, summing their executed test bodies across targets (paths relative to v8-core):

| Rank | File | Serial seconds | Executions |
|---|---|---:|---:|
| 1 | `src/usdm_sim.rs` | 9.733 | 6 |
| 2 | `src/runloop.rs` | 2.131 | 44 |
| 3 | `src/opportunity/funnel.rs` | 1.568 | 2 |
| 4 | `src/evidence.rs` | 0.287 | 30 |
| 5 | `src/cache.rs` | 0.173 | 14 |
| 6 | `src/oracle/coverage.rs` | 0.168 | 24 |
| 7 | `src/report.rs` | 0.133 | 16 |
| 8 | `src/shadow.rs` | 0.058 | 8 |
| 9 | `src/experiment.rs` | 0.026 | 22 |
| 10 | `src/statistics/mod.rs` | 0.023 | 18 |
| 11 | `src/analysis/mod.rs` | 0.021 | 2 |
| 12 | `tests/d153_parity_adapters_policy_bound.rs` | 0.02 | 50 |
| 13 | `tests/v86_cli_request_envelopes.rs` | 0.017 | 3 |
| 14 | `tests/d153_receipt_ledger_selfverify.rs` | 0.016 | 40 |
| 15 | `src/analysis/phase2.rs` | 0.014 | 22 |
| 16 | `src/parquet_artifact.rs` | 0.01 | 2 |
| 17 | `src/analysis/phase3.rs` | 0.009 | 16 |
| 18 | `tests/d153_minerva_and_dashboard_test.rs` | 0.008 | 3 |
| 19 | `src/evaluation/regime_cube.rs` | 0.008 | 2 |
| 20 | `src/candidate.rs` | 0.007 | 8 |


Compile-unit timings are overlapping elapsed times, not additive critical-path percentages:

| Compilation unit | Elapsed |
|---|---:|
| v8-core library test crate | 31.06 s |
| v8-core CLI test crate | 25.57 s |
| v8-core library | 25.42 s |
| syn 2.0.119 | 23.36 s |
| redb 2.6.3 | 21.79 s |
| syn 3.0.3 | 20.81 s |
| v8-core normal CLI | 20.66 s |
| clap_builder | 18.21 s |
| parquet | 14.96 s |

The CLI test crate starts at 78.58 seconds and finishes at 104.15, the end of the measured build. The library test crate finishes at 92.10. This is evidence that duplicated CLI compilation is on the observed tail, but removing it changes scheduling; 25.57 seconds is not a proven cold-build saving. Full unit data is in `cold-build-units.json`.

## 5. Root causes and discriminating experiments

### R1 — Shared modules compiled and tested twice

**Observed:** `src/main.rs` declares 47 module roots rather than using only the library. `src/lib.rs` exposes most of the same modules. All 443 CLI test names also occur in the 475-test library suite. CLI suite elapsed time is approximately 4–5 seconds, including the historical simulations. Cargo compiled separate library-test, CLI-test, normal-library and normal-CLI units.

**Mechanism:** independent crate roots instantiate the same modules and `#[cfg(test)]` blocks. A shared-source edit invalidates multiple crate compilations; default `cargo test` runs both copies sequentially at target level.

**Impact/confidence:** high confidence in duplicate execution and approximately 4–5 seconds of removable warm work. Compile savings are likely but not measured after refactoring.

**Possible fix:** make the CLI depend on public library APIs; retain process-level CLI tests and one copy of every unique assertion. Compare test inventories, feature combinations, CLI error behavior, and determinism before/after. Do not simply set `test=false` and claim CLI validation is preserved.

**Risk:** medium: visibility boundaries and crate-relative types must remain coherent. No refactor was applied.

### R2 — Historical simulation/report workloads masquerade as unit tests

**Observed:** `usdm_sim.rs` tests read `../research/tape/btcusdt-1h-12m/tape.jsonl`, return success when missing, and run 1 + 5 + 1 simulations. The anatomy test reloads and rebuilds the dataset again. The tape contains 9,948 input rows, including 8,760 price bars, and is approximately 5.5 MB. H4 independently loads it and writes `site/h4_decomposition.txt`; its test body has no assertions. The five-arm test has only two validity assertions per arm, and its comment about deterministic output is not backed by a rerun/byte comparison.

**Experiment:** direct binaries from root versus Cargo-compatible `v8-core/` cwd. Root harness sweep was approximately 2 seconds warm; correct-cwd sweep approximately 9 seconds. The three USD-M tests silently bypassed work from root. H4 has its own fallback path and still ran.

**Impact/confidence:** high. The four slowest library tests account for 78.2% of serial body time and are duplicated in the CLI.

**Possible fix:** explicitly classify data-required simulations and diagnostic reports, pin their real input identity, fail or explicitly mark unavailable data, and preserve their required coverage in a named validation workflow. Keep meaningful simulation acceptance tests. Moving diagnostics changes the default validation contract and must be disclosed.

**Risk:** silently skipping data, reducing tape length, or removing historical validation would produce false performance wins. Prefix measurements below are scaling experiments only.

### R3 — Repeated immutable setup exists, but is not the dominant simulation cost

**Experiment:** temporary test-only Rust probe loaded the real tape, built the dataset and feature stores once, then ran all five original exit arms through existing `run_simulation_with_stores`. Two repetitions; prefixes at 2,222 / 4,444 / 8,760 bars. No synthetic rows entered the probe.

| Full-tape phase | Rep 1 | Rep 2 |
|---|---:|---:|
| Read + parse all 9,948 rows | 0.053828 s | 0.052648 s |
| Dataset construction | 0.017061 s | 0.015683 s |
| Feature-store construction | 0.003633 s | 0.003472 s |
| Five simulations on shared stores | 2.946724 s | 2.964010 s |
| Total one-setup/five-arm work | 3.021246 s | 3.035813 s |

Baseline serial five-arm test was 3.354630 seconds; a separately sampled baseline was 3.52 seconds. The setup-elimination estimate is four times 0.0718–0.0745 seconds = **0.287–0.298 seconds**, consistent with the observed approximately 0.32–0.33-second difference from the serial baseline. This is modest, not a multi-second initialization bottleneck. A final rerun of the original cold-built baseline in a fresh TMPDIR produced byte-identical cashflow JSONL and portfolio receipts for all five arms compared with the shared-store probe (10 files; every cmp exit code zero). This validates this narrow reuse boundary on this tape, not arbitrary global caching.

**Profiling:** on the test worker, 781 of 933 sampled stacks were under `run_simulation`'s `run_simulation_with_stores` call. The stack includes `state_features`, feature-group projection, history cloning, allocation/free and `fsum`. The main harness thread waited for its worker; that wait is not evidence of an application global lock. This is sample evidence, not exact phase accounting or allocated-byte measurement.

**Scaling:** one baseline arm took 0.153 / 0.302 / 0.596 seconds at 2,222 / 4,444 / 8,760 bars in repetition 1. Approximately doubling bars approximately doubled simulation time on this range. No quadratic blow-up was observed in this dominant workload. Full prefix timings are retained in `phase-measurements.txt`.

**Possible fix/risk:** share immutable stores inside this one test across arms; allocate fresh account, portfolio, ledger and outputs per simulation. Suite-global mutable state is not justified. Any broader cache must include tape content, schema, feature algorithm/parameters and build identity in invalidation. State/history projection could be optimized only after differential checks; causality and floating-point order are sensitive.

### R4 — Test output directories retain stale ledger state

**Observed:** simulation tests use fixed `std::env::temp_dir()` names with no cleanup. `cashflow.rs:122` reads existing JSONL records, verifies them, deduplicates exact serialized records, then appends new records and calls `sync_data`. An old A0 output contained 208 rows; a fresh probe contained 116. All 116 fresh rows existed in the old file, plus 92 stale rows. Summary receipt bytes matched even though cashflow file bytes did not.

**Mechanism:** historical runs with changed simulation behavior accumulate in the same append-only test output. Anatomy reads the whole ledger, so its analysis can include stale data. Concurrent invocations can also race on fixed paths.

**Impact/confidence:** confirmed isolation/semantic defect. No large timing gain demonstrated at the observed approximately 100 KB/file scale. Repeated full ledger parse scales with retained history and may grow, but is not today's primary waiting cost.

**Possible fix:** test-owned unique temporary output per invocation, cleaned up on success/failure. Preserve append-only semantics in dedicated persistence tests and production. Compare fresh output artifacts when validating fixture reuse.

**Risk:** do not truncate production ledgers or weaken durability to accelerate tests.

### R5 — Command-dependent compiler configuration and expensive cache misses

**Observed:** root `cargo ... --manifest-path v8-core/Cargo.toml` has no rustflags; inside `v8-core/`, `build.rustflags` contains FP contraction policy. CI uses the latter. README documents the former. Test profile uses opt-level 1; dev uses 0; both compile third-party dependencies at opt-level 2. Release uses opt-level 3, thin LTO and one codegen unit. Initial target directory was 9.6 GB; incremental cache later measured 8.5 GB before external disk changes.

**Mechanism:** Cargo fingerprints depend on compiler, profile, flags and features. Different invocations create distinct compilation work and cache populations. Multiple optimizing local crate roots and optimized dependencies explain why clean builds are materially more expensive than execution.

**Impact/confidence:** high for configuration divergence and measured cold/warm gap; no measured hit rate across the user's work history.

**Possible fix:** standardize invocation/config discovery first, retain the required FP policy, pin toolchain and cache identity. Then test a thin CLI refactor and profile tradeoffs with clean and incremental measurements. `cargo clean` is not a speed fix.

**Risk:** dropping FP flags or changing optimization profile can alter numeric parity or overflow coverage. Lower compilation settings must be benchmarked against runtime and correctness, not assumed beneficial.

## 6. Architectural and toolchain findings

- One Cargo package, not a Rust workspace monorepo. 240 Rust source files were found. `tests/integration_tests.rs` aggregates 14 modules, but four similarly named top-level integration files still execute 47 overlapping named cases (causal shock 5, gate vector 15, sabotage 24, Minerva 3). Copies have drifted enough to cause the current build failure. Runtime savings from these tiny cases are small; maintenance and link work are the concern. Do not delete a copy without comparing assertions.
- Pure unit tests include arithmetic, schemas, authority checks and many expert contracts. Filesystem/component tests include runloop evaluation, candidate persistence, evidence, cache and reporting. Storage tests exercise redb transactions and durable artifacts. Process tests cover real CLI parsing/error exits. Simulations include the historical USD-M tests and H4. Causal future-shock tests are property-style finite adversarial loops; Minerva's Monte Carlo test is a small simulation, approximately milliseconds here. There is no default Rust network/API service bootstrap identified.
- Rust subprocess search found two CLI test call sites. One spawns one CLI; the request-envelope test loops over subcommands. They invoke the built executable directly, not shell → package manager → runtime chains. The legacy parity fixture builds a release binary once per Python session if source mtimes are newer, and other parity tests spawn that binary; this can hide compilation inside fixture setup.
- `tests/parity/conftest.py` cache freshness watches only Rust source mtimes. Changes to lockfile, Cargo config, toolchain or feature selection can escape that manual check. The frozen harness was not edited; use Cargo freshness validation in the active Rust workflow rather than copying this key scheme.
- No default coverage instrumentation found in Cargo configuration or CI. A with/without coverage comparison is not applicable to the observed default loop. GPU/release timings are not inferred from the default feature build.
- No Rust artificial sleeps/retry loops found in the tested paths. Optional GPU code has device polling with `timeout: None`; it is outside the default-feature measurements. Download tooling has up to four 60-second network attempt timeouts plus 7–7.75 seconds backoff, and read-list tooling uses 45-second request timeouts and a 0.15-second inter-download sleep. These are not called by default Rust tests; actual network wait was not measured. Cleanup retry helper allows four 0.2-second waits before its last attempt, at most 0.8 seconds; no observed contribution to the measured loop.
- Filesystem audits are source-scoped. `forbidden_names.py` recursively enumerates its source trees before filtering excluded segments, so exclusion does not prune traversal; measured total was only 0.21 seconds. Synthetic/economic audits were 0.15 seconds each. No evidence that repository-wide discovery, archives or target traversal dominate these measured commands.
- Durable cache keys include version, candidate, action, simulator and data hash. Memory and redb backends exist; warm/cold and corrupt-entry semantics have dedicated tests. Redb inserts each commit a transaction. Batching might help large write workloads, but was not validated here and can change crash/durability semantics. Application cache hit rates were not instrumented; Cargo cache reuse is a separate concern.
- Scheduler constructs Rayon pools per `evaluate`/`parallel_map` call; Monte Carlo uses Rayon too. Combined test and application parallelism can multiply threads. Yet the actual concurrency sweep favors parallel tests. Pool reuse is a hypothesis, not a measured major bottleneck.

## 7. Ranked optimization candidates

| ID | Priority | Optimization | Expected gain | Confidence | Risk | Effort |
|---|---|---|---|---|---|---|
| O1 | P1 | Thin CLI using library; one copy of shared tests | ~4–5 s warm suite; cold gain unquantified | High execution, medium compile | Medium | Medium |
| O2 | P1 | Standardize Cargo invocation and FP config; avoid unnecessary clean/profile/feature churn | Avoid measured ~100 s class clean rebuilds when reuse is valid; frequency unknown | High mechanism | Low if policy preserved | Small |
| O3 | P1 correctness | Unique simulation output dirs and explicit missing-data behavior | No large speed claim; prevents misleading benchmarks and stale evidence | High | Low/medium workflow impact | Small |
| O4 | P2 | Share immutable stores across five arms | ~0.29 s per five-arm test; duplicated today | High phase estimate | Low after fresh artifact equivalence | Small |
| O5 | P2 | Make diagnostic/report workloads explicit; retain required simulation checks | Up to measured diagnostic costs in chosen inner loop, not full validation | High cost, validation contract changes | Medium | Medium |
| O6 | P2 | Consolidate drifted integration copies after assertion comparison | Tiny execution gain; compile/link gain not established | High duplication | Medium | Small/medium |
| O7 | P2 investigation | Reduce feature projection/history allocations in simulation | Unknown; sampled hotspot only | Medium | High numerical/causality sensitivity | Medium/large |
| O8 | P3 | Persistent Rayon pools or batched durable transactions | Unknown; no experiment proving major gain | Low | Medium/high | Medium |

No P0 performance fix was proved. Fixing the compile errors is a correctness prerequisite, not an optimization. No speed claims are attached to speculative dependency removal or caches.

## 8. Quick wins

1. Correct the two stale integration-source problems and unify the documented Cargo invocation with the required compiler flags. The temporary repair made the suite measurable, but was restored for an audit-only deliverable.
2. Use the already-supported targeted Rust test filters for actual inner-loop work. Preserve the full gate at milestones; avoid running a full simulation diagnostic after unrelated schema edits.
3. Give simulation tests fresh output ownership. This is primarily a correctness improvement and a prerequisite for trustworthy measurements.
4. Reuse a feature store across the five arms only after fresh-directory artifact comparisons. The existing `run_simulation_with_stores` API provides the boundary; there is no need for a global cache.

## 9. Structural fixes

Make the library the sole owner of engine modules; keep executable command dispatch thin. Audit CLI-specific behavior before removing duplicate test targets. Replace copied integration sources with one maintained source location. Separate report production from assertions and turn historical acceptance data requirements into explicit configuration. Retain byte comparisons, causality tests, storage durability tests, and checked-arithmetic versus release validation where their semantics require distinct runs.

The profile shows expensive per-bar state projection and allocation; investigate typed/borrowed views or request-scoped immutable reuse with exact parity tests. Do not precompute any future-dependent state into earlier decision views, reorder floating-point reductions casually, or reuse mutable simulation state across arms.

## 10. Proposed test strategy and parallelism

Observed sum of harness suite elapsed times (all 14 targets, sequential target launch; no compilation):

| Test workers per binary | Total body/harness time |
|---|---:|
| 1 | 14.555 s |
| 2 | 10.079 s |
| 4 | 9.297 s |
| default, repetition 1 | 9.400 s |
| default, repetition 2 | 8.972 s |
| 11 | 8.351 s |

The default is logical-CPU-count parallelism in this environment; explicit 11 and default are effectively the same policy. The small differences do not justify claiming 11 is a different superior scheduler setting. More than 11 was not justified or tested. Serial is substantially slower. Exact optimal concurrency remains sensitive to background workloads. The test with five serial simulation arms limits the critical path even when other tests run concurrently.

- **Fastest loop:** canonical cwd/config, affected library filter; include CLI integration tests when command behavior changes. Warm build freshness is subsecond, but an engine edit can still trigger a multi-second compiler pass.
- **Targeted validation:** affected unit/component plus storage/process/causality cases; use normal parallelism. Do not serialize everything to avoid addressing output races.
- **Full validation:** all Rust targets plus policy audits after milestone/risk-boundary changes; explicitly require historical input when simulation coverage is expected.
- **CI:** current workflow runs default tests, GPU check/tests, all-target clippy, Linux GPU check, release tests, Python registry and parity tests, and monograph probe. It repeats most default tests in GPU/release configurations. Checked arithmetic, GPU feature integration and release parity are distinct properties; retain them until a coverage map establishes safe redundancy removal.
- **CI cache:** registry/git/target are cached by runner OS and Cargo lock/manifest/config hashes, but the toolchain is installed as moving `stable` and not part of the explicit key. Cargo prevents unsafe reuse through fingerprints, but stale-cache restore size and rebuild frequency were not measured. On `ubuntu-latest` x86_64, the explicit x86_64 Linux target check appears to repeat the host GPU check in a separate target namespace; confirm actual runner architecture and compiler units before consolidation.
- **Exhaustive workflows:** release/GPU/parity/historical report generation belong to explicit validation scopes already present in the repository, not a newly invented benchmark gate. No recommendation to disable meaningful tests or coverage.

No measured developer activity log exists. Consequently the report identifies dominant costs **within measured workflows**, not an invented statement that a workflow accounts for 80% of the user's total working-day waiting time.

## 11. Falsification and open questions

| Uncertainty | Confirm/refute with |
|---|---|
| Actual save from thin CLI refactor | Compare identical test inventories/artifacts, 3 warm runs, 2 clean builds, and shared-source edit builds |
| Best concurrency on idle hardware | Randomized repeated 1/2/4/11-worker runs with background CPU and memory-pressure capture |
| Cold build improvement from profile settings | Separate target dirs, compiler unit timings and unchanged numerical/overflow gates; measure execution tradeoff |
| Allocation bytes and per-function CPU fractions | Instruments Allocations/Time Profiler or equivalent, with the same real tape and fixed build flags |
| Production-scale complexity beyond 8,760 bars | Real datasets at larger sizes/symbol counts, fixed strategies, separated parse/projection/simulation/output phases |
| Exact storage syscall and fsync contribution | Per-process filesystem/syscall tracing, preserving durability; no inference from source count alone |
| CI delay distribution | Download actual CI step durations/cache logs for repeated runs; none were available in this local audit |
| GPU and release build/test cost | Run on intended supported hardware/toolchain and capture complete profiles; not extrapolated from default build |
| Python legacy full-suite timing | Provision compatible frozen-oracle environment separately; current venv has no pytest. Do not revive it as default runtime gate |
| Startup first-launch spikes | Repeated new-vs-warm executable launch with dyld/security tracing; current evidence cannot identify cause |
| Monograph/dependency-install/network latency | Time those exact CI steps in an isolated environment; not part of measured local runtime baseline |

The `sample` profile is one short observation. OS-cache coldness, detailed memory-pressure history, network download time, coverage overhead, and post-refactor performance are not established. No unsupported percentages have been assigned to these phases.

## 12. Target state and performance budgets

These are evidence-based acceptance targets for future work, not measured optimized results:

| Workflow | Target / interpretation |
|---|---|
| No-change check/lint/build | <0.5 s on comparable warm host; already observed 0.09–0.20 s in root-config runs |
| Targeted prebuilt pure-unit test | <0.1 s; small source-file groups are milliseconds; compilation budget separate |
| Full warm tests after deduplication | Approximately 5–7 s, preserving every unique assertion and real-data simulation coverage |
| Five-arm simulation | Approximately 3.0–3.2 s at current data size via one immutable setup; measured probe ~3.02–3.04 s |
| Full original warm command | Approximately 10–12 s under observed machine conditions; build must first be repaired |
| Cold test build | Approximately 100-second class observed; no verified improved ceiling yet |
| Engine source edit | Expect seconds to tens of seconds until compile graph is changed; temporary probe rebuild took 15.48 s |
| Full release/GPU/CI validation | No numerical budget without measuring those profiles and CI installation/cache steps |

The theoretical lower bound is constrained by the slowest retained test (~3+ seconds serial arms) plus remaining targets, launch overhead and compiler freshness. If the five arms were parallelized with isolated outputs, latency might drop further, but scheduling, semantics and contention were not tested. A subsecond **full** suite is not supported by the current evidence.

### Additional startup, scope and cleanup evidence

Fifty launches of the original compiled library test binary with `--list` took 0.52 and 0.46 seconds in total, or approximately **10.4 and 9.2 ms per launch**, including shell/process overhead. There are 14 libtest executables in the baseline. The CLI process-level tests spawn three application processes total (one full-audit argument check, two request-envelope domain-failure checks). A first help launch took 0.62 seconds despite <0.01 seconds reported CPU; 50 subsequent help launches took 0.16 seconds total (3.2 ms each), as recorded in `workflow-resources.tsv`. This distinguishes a first-launch wait from recurring argument-parser work; its OS cause is unproven.

The ranked source-file table includes setup, assertions and teardown contained in each body, not only assertion evaluation. Across two matching parallel library runs, the dominant five-arm test was 3.62 and 3.81 seconds; a small sample does not establish a variance distribution. Millisecond tests and newly launched binaries have noisier ratios and should not drive prioritization.

The report describes the initial CI snapshot. Concurrent work replaced its Python registry gate with a Rust registry test, then changed additional CI/source files and added `tests/runnable_main.rs`; these changes were neither implemented nor performance-certified by this audit. Canonical clean-build timing data, default-config serial rankings, and post-edit first-profile timings must not be treated as a single unchanged version.

Temporary Rust instrumentation and compile repairs were removed. The H4 generated report's tie-order-only change was restored. No substantive optimization, Python edit, dependency installation, or test deletion was retained. Isolated cold targets and probe outputs were removed after extracting compact evidence. Existing application temp directories and unrelated work were preserved.

Late concurrency note: HEAD advanced from `7840520e` to `e1481afd` during this session, independently untracking large oracle-coverage dumps (commit message reports approximately 950,000 lines). Another actor also applied a distinct doc-attribute repair and the scorer-type rename after this audit restored its temporary versions. Those later repairs are preserved; the initial 13-error result is historical baseline evidence, not a claim that the final concurrently edited checkout still fails. Large tracked generated outputs may affect Git/UI workflows, but no timing experiment here quantifies that effect.

Final observed HEAD was `07f183cc` (`fix: establish runnable Rust baseline and reconcile funding cashflows`), committed independently during report cleanup. The working tree then contained only this untracked audit-report directory. This report does not certify performance of that new revision; its source changes require a fresh baseline before claiming an improvement over the initial measurements.
