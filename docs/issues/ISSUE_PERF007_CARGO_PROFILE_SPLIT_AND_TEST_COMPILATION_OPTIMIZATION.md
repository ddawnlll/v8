# [PERF] Issue: Cargo Profile Split and Elimination of Whole-Crate Optimization in Dev and Test Profiles

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `BUILD_CONFIGURATION`  
**Labels:** `type:performance`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-099` (Computation Budget Policy)

---

## 1. Objective
Eliminate redundant and expensive whole-crate LLVM optimization passes (`opt-level = 2`) on workspace code and unit/integration tests during iterative development (`cargo check`, `cargo test`, `cargo build`), switching workspace dev code to `opt-level = 0` while selectively optimizing heavy third-party dependencies (`arrow`, `parquet`, `redb`, `serde`) via package-level overrides.

---

## 2. Owning Authority
- **Authority:** `D-099` (Computation Budget Policy — "Checks must not waste developer time or machine compute"), V8 Constitution Rule 1 (`AUTHORITATIVE_RUNTIME`).
- **Target Performance Envelope:** Reduce incremental build and test compile time by **70%–80%** (from 30–60+ seconds per incremental change down to < 5 seconds).

---

## 3. Current State / Profile Baseline
- `v8-core/Cargo.toml:37-39`:
  ```toml
  [profile.dev]
  opt-level = 2
  debug = 1
  ```
- Cargo defaults to inheriting `test` profile settings from `dev`.
- Because `opt-level = 2` is set globally for `dev`:
  1. Every invocation of `cargo test` forces LLVM to run full optimization passes (inlining, loop vectorization, dead-code elimination, alias analysis) on all 14 integration test crates and internal modules on every minor edit.
  2. Incremental test compilation on an M3 Max / M3 Pro consumes 100% CPU across multiple cores for over 45 seconds for a 1-line change.
  3. No package-level split exists, so developers pay the cost of optimizing both the rapidly-changing application code and external dependencies simultaneously.

---

## 4. Required End State / Optimization Target
1. **Workspace Fast Compilation (`opt-level = 0`):**
   Set `[profile.dev] opt-level = 0` so that workspace crates compile instantly without heavy LLVM codegen passes.
2. **Dependency-Only Optimization:**
   Introduce package-level override for third-party dependencies:
   ```toml
   [profile.dev.package."*"]
   opt-level = 2
   ```
   This ensures heavy mathematical / columnar libraries (`arrow-array`, `parquet`, `redb`, `blake3`) remain fast at runtime without penalizing workspace compilation latency.
3. **Dedicated Test Profile Definition:**
   Explicitly configure `[profile.test]` to preserve fast edit-compile-test loops while keeping incremental compilation enabled.

---

## 5. Expected File / Module Surface
- `v8-core/Cargo.toml` [MODIFY]
- `.cargo/config.toml` (if linker/compiler flag tuning needed) [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml --lib
```

---

## 7. Required Evidence Artifacts
- Timing comparison of clean and incremental builds before and after profile split (`cargo build --timings`).
- Verification that all test suites pass with identical bitwise results under the new profile.

---

## 8. Non-Goals / Forbidden Scope
- Altering `[profile.release]` settings (`opt-level = 3`, `lto = "thin"`, `codegen-units = 1` remain untouched).
- Changing `--fp-contract=off` or numeric floating-point contracts.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Fast Developer Inner Loop:** Incremental compilation time for unit tests must complete in < 5 seconds on reference Apple Silicon / Linux workstations.
  * *Authority:* `D-099` (§2 Inner loop ergonomics).
- **R2 — Parity Invariance:** Execution semantics and outputs of all tests under `dev`/`test` profile must match existing behavior bit-for-bit.
  * *Authority:* `PARITY_AND_IDENTITY_SPEC`.

### 12. Existing Types / Interfaces to Reuse
- Cargo profile configuration schema in `v8-core/Cargo.toml`.

### 13. Mathematical / Semantic Invariants
- `I1`: Zero divergence in numerical calculations (IEEE-754 bit-parity preserved).

### 14. Canonical Failure Semantics
- Build configuration failures fail closed during `cargo check`.

### 15. Dependency Map
```text
Cargo.toml -> [profile.dev] (opt-level=0)
           -> [profile.dev.package."*"] (opt-level=2)
           -> Fast workspace rebuilds + performant third-party crates
```

### 16. Ambiguity / OPEN_PIN Triggers
- None.
