# Performance changes — 2026-09-08

This is implementation guidance, not release or economic certification. The owner
has authorized retiring USD-M simulator tests because production execution is
being transferred to NautilusTrader in a separate task. Runtime execution
migration is not implemented or certified by this performance change.

## Boundaries and retained checks

- `main.rs` imports engine modules from the library instead of declaring a
  second copy. Public `PendingCandidate` and `write_cube_reduced` expose the
  existing shared S3 request boundary to the CLI. CLI argument/error process
  tests remain. No default `test=false` switch hides executable coverage.
- Four copied integration files were removed after comparing them to the
  suites already included by `integration_tests.rs`. They had the same 47
  test bodies, apart from comments and renamed local variables.
- The 11 USD-M module tests and its explicit `runnable_main` historical
  acceptance test are retired by owner authorization, rather than marked
  ignored. This is a deliberate validation-scope change. Shared cashflow,
  risk, authority, temporal and execution-lane contract tests remain.
- The H4 report generator had no assertions. It is now the explicit command
  `h4-decomposition --tape PATH --out PATH`; input/output paths are required,
  missing/invalid/empty data fails, and normal tests never generate the report
  or depend on a local historical tape. The caller chooses its output path.
  Equal-count report rows sort by name, so repeated output is deterministic.
- `.cargo/config.toml` at repository root supplies the same mandatory FP
  contraction policy to both root `--manifest-path` commands and commands
  started inside `v8-core`. The nested duplicate configuration was moved,
  not copied. The separately added pinned Rust toolchain remains authoritative.

## Allocation and scheduling changes

`FeatMap.history` is an immutable borrowed slice with the same lifetime as the
feature view. Runloop constructs history once per bar, and each expert either
borrows it or receives an empty slice according to the existing feature closure.
Opportunity witnesses and legacy simulator consumers also borrow instead of
cloning history/event strings. No history extends past the existing availability
boundary; feature masks, expert code, floating-point reductions and assertions
remain unchanged. The H4 real-tape report was compared against the prior output.

The scheduler retains one Rayon pool per caller thread, keyed only by worker
count. A new worker count replaces the retained pool, and thread exit releases
it. No input, output, candidate or domain state is cached. The RefCell borrow is
released before installing work; nested calls can safely run on worker threads.
Failures still propagate through the existing catch-unwind boundary. Regression
checks cover worker count, ordered results, task errors, panic recovery and
nested calls; the existing byte-identical cube tests remain.

Three paired 500-call micro-experiments measured fresh four-worker pool creation
at 150–307 ms versus 6–46 ms for a reused pool on this busy workstation. These
numbers establish pool-creation cost, not a whole-application speedup.

## Durable cache changes

Memory cache insertion no longer serializes bytes which it never stores.
Ordinary durable insertion still commits each write with the original durability
semantics. Only legacy JSONL migration batches writes into one transaction:
`open()` reports success after the complete validated import commits; malformed,
stale and invalid-digest records remain excluded; the last valid duplicate wins.
On failure the transaction rolls back and the original source remains available
for retry. No completion marker or new invalidation-sensitive data cache exists.

Three paired redb probes with 200 writes measured per-row commits at 742–844 ms
and a single commit at 2–12 ms. These are test-harness probes, not production
metrics. Reopen, source preservation, duplicate and corrupt-entry tests validate
the migration contract. No fsync/durability setting was relaxed.

## Local workflow

The dependency-free verifier package at `tools/check-local` compiles the existing
`src/bin/check_local.rs` without bootstrapping the engine/Nautilus dependency
graph. It executes the four policy scripts, all-target Clippy, then all Rust tests.
Clippy already typechecks all targets, so a separate `cargo check` was redundant.
The original engine `--bin check_local` remains callable for compatibility.

From repository root:

```sh
cargo run --locked --manifest-path v8-core/tools/check-local/Cargo.toml
cargo test --locked --manifest-path v8-core/Cargo.toml --lib FILTER
cargo test --locked --manifest-path v8-core/Cargo.toml
cargo run --locked --manifest-path v8-core/Cargo.toml --bin v8-core -- \
  h4-decomposition --tape research/tape/btcusdt-1h-12m/tape.jsonl --out /tmp/h4.txt
```

Use ordinary parallel test execution. The earlier audit measured serial execution
as slower; no concurrency throttle or sleep/timeout reduction was introduced.
Release/GPU checks remain explicit local risk-boundary operations. Old Python
source/tests remain frozen and were not edited.

## Measurement limitations

The audit's initial ~11-second warm suite included historical USD-M tests and
duplicated CLI test modules. Compare validation scope explicitly; removing USD-M
is an authorized retirement, not a semantics-neutral optimization. During this
implementation another task added Nautilus dependencies and switched Rust from
nightly to 1.98.0. Fresh dependency compilation and lock waiting cannot be
compared with the old cached compiler timings as a performance regression.
Final same-build timings and verification results are recorded below.
Speculative feature-index caches, altered numerical
algorithms and non-durable writes were not introduced: the audit did not establish
that they were safe or beneficial.

## Final measurements and verification

Measured on the same busy workstation with Rust 1.98.0 and the concurrently
introduced Nautilus 0.63 dependencies. Seconds below are wall / user CPU / system
CPU. These measurements do not establish a clean-build speedup over the original
audit's different compiler and dependency graph.

| Workflow | Measurements (seconds) | Result / scope |
|---|---|---|
| Retained test executables, three complete sweeps | 2.15 / 0.47 / 0.46; 0.96 / 0.48 / 0.45; 1.02 / 0.50 / 0.47 | All 684 tests pass each time; excludes Cargo/rustdoc and separately added Nautilus E2E |
| Library bodies, default concurrency | 0.81; 0.80; 0.84 | 468 pass; CLI no longer owns a second library suite |
| Library process, one thread | 1.69; 1.74 | 468 pass in both runs |
| Library process, four threads | 1.01; 1.08 | 468 pass in both runs |
| Library process, eleven threads | 0.85; 0.87 | 468 pass in both runs; no reason to reduce concurrency |
| Entire current Cargo suite, warm, `--no-fail-fast` | 3.17 / 1.94 / 0.64; 3.19 / 1.91 / 0.66 | **Fails the new Nautilus E2E**; 684 pass, one fails; Cargo freshness phases 0.17 / 0.16 s |
| Current Cargo suite after concurrent source edit | 13.11 / 9.87 / 5.44 | Includes 5.18 s compilation; excluded from warm figures; same E2E failure |
| Packaged verifier | 79.96 / 270.79 / 21.56 | Four policy audits and Clippy pass; test gate fails Nautilus E2E; includes 15.69 s Clippy and 57.14 s test build |
| Explicit H4 real-tape command | 2.94 / 1.08 / 0.05; 1.84 / 1.03 / 0.02 | Both succeed; byte-identical repeated output; sorted report lines match prior report exactly |

The new Nautilus test was not skipped or weakened: its `n_trades_admitted > 0`
assertion fails with `Nautilus should execute trades on historical tape`.
`--no-fail-fast` was used to verify all remaining targets despite that failure.
This is an open migration correctness issue, not a successful full-validation
result or a performance optimization. The default verifier still fails closed.
The test's temporary output directory was made unique and cleaned on drop to
avoid cross-process interference; its real-data and accounting assertions remain.

All 47 removed integration copies were reconciled by name against their retained
aggregate-suite counterparts. Outside authorized USD-M retirement and explicit
H4 report extraction, no original unique test disappeared. Cache migration,
scheduler failure/nesting, H4 missing-input, existing causality and byte-identical
execution checks pass. Root and crate-directory Cargo configuration both report
exactly `["-C", "llvm-args=--fp-contract=off"]`. Changed lines pass whitespace
checks. Frozen Python sources and tests remain unchanged.

Useful regression budgets for the **retained prebuilt** scope are library under
1.2 s and the complete executable sweep under 2.5 s on this host after startup
caches warm. These allow headroom above observed runs and are diagnostic budgets,
not hard timing assertions. No passing full-suite or fresh-build budget is claimed
for the unfinished Nautilus migration. Its corrected real execution must be
remeasured before setting that budget.

The original forensic report and compact implementation timing evidence are in
[`../reports/performance-audit-2026-09-08/`](../reports/performance-audit-2026-09-08/).
