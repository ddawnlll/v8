# [PERF] Issue: Integration Test Harness Consolidation and Mach-O Linker Contention Elimination

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `BUILD_CONFIGURATION`  
**Labels:** `type:performance`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-099` (Computation Budget Policy)

---

## 1. Objective
Consolidate the 14 separate integration test executables under `v8-core/tests/*.rs` into a unified test harness module structure (`tests/integration/mod.rs` or single runner binary), eliminating the creation and sequential linkage of 14+ independent Mach-O binaries on Apple Silicon and Linux during test execution.

---

## 2. Owning Authority
- **Authority:** `D-099` (Computation Budget Policy), V8 Constitution Rule 1 (`AUTHORITATIVE_RUNTIME`).
- **Target Performance Envelope:** Reduce total linking time during `cargo test` from 40–70 seconds down to < 4 seconds (10x+ linker speedup).

---

## 3. Current State / Profile Baseline
- `v8-core/tests/` contains 14 independent top-level `.rs` test files:
  1. `ai_agent_tevv_sabotage.rs`
  2. `assurance_fabric_sabotage.rs`
  3. `causal_future_shock.rs`
  4. `continuous_certificate_lifecycle.rs`
  5. `d150_epistemic_succession_sabotage.rs`
  6. `d153_benchmark_fabric_sabotage.rs`
  7. `d153_minerva_and_dashboard_test.rs`
  8. `data_role_holdout_burn.rs`
  9. `policy_evidence_profile_adversarial.rs`
  10. `production_growth_contract.rs`
  11. `research_validity_diagnostics.rs`
  12. `system_proving_ground.rs`
  13. `world_foundry_isolation.rs`
  14. `world_foundry_v2_falsification.rs`
- In Cargo, every file directly inside `tests/` is compiled as a distinct crate and linked as a standalone binary executable.
- Each test binary independently links against `v8-core`, Arrow (59.3), Parquet, Redb, Serde, and Blake3.
- On macOS (M3 Mac Pro), Apple's default `ld64` linker operates single-threaded per binary. Linking 14 test binaries + 1 lib test binary + 2 `src/bin` executables forces **17–18 separate Mach-O link invocations**, consuming 100% CPU and creating massive disk I/O churn even when only a single test file was touched.

---

## 4. Required End State / Optimization Target
1. **Single Integration Test Binary:**
   Consolidate all integration test suites into submodules under a single entry point:
   - `tests/integration_tests.rs` (main integration test entrypoint)
   - `tests/integration/*.rs` (individual test suite modules)
2. **Single Linker Invocation:**
   A single test binary links all integration tests in one pass, reducing linker overhead from 14 passes to 1 pass.
3. **Optional Alternative Linker Support:**
   Document and support `mold` (Linux) / `sold` or `lld` where available in `.cargo/config.toml` for additional linking speedup.
4. **Complete Test Suite Parity:**
   All 14 test suites run with exact name preservation (`cargo test --test integration_tests <filter>`).

---

## 5. Expected File / Module Surface
- `v8-core/tests/integration_tests.rs` [NEW]
- `v8-core/tests/integration/` [NEW / REORGANIZE]
- `v8-core/tests/*.rs` (top-level separate files transitioned to module files) [DELETE / MOVE]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml --tests
cargo test --manifest-path v8-core/Cargo.toml --test integration_tests
```

---

## 7. Required Evidence Artifacts
- Linker time comparison (`cargo test --no-run`) before and after consolidation.
- Test count verification showing identical test cases discovered and executed.

---

## 8. Non-Goals / Forbidden Scope
- Changing test assertions, tolerances, or test logic.
- Deleting or disabling any existing constitutional sabotage or verification suites.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Single-Binary Integration Harness:** All integration test files must link within a single test executable.
  * *Authority:* `D-099`.
- **R2 — Zero Test Loss:** 100% of existing tests must execute and pass under the consolidated harness.
  * *Authority:* `docs/WORK_ITEM_POLICY.md`.

### 12. Existing Types / Interfaces to Reuse
- Existing test functions and modules in `v8-core/tests/`.

### 13. Mathematical / Semantic Invariants
- `I1`: Zero change in test outcomes, logs, or assertion coverage.

### 14. Canonical Failure Semantics
- Any test assertion failure fails the test run identically.

### 15. Dependency Map
```text
tests/integration_tests.rs
 ├── mod ai_agent_tevv_sabotage
 ├── mod assurance_fabric_sabotage
 ├── mod causal_future_shock
 ...
 └── mod world_foundry_v2_falsification
```

### 16. Ambiguity / OPEN_PIN Triggers
- None.
