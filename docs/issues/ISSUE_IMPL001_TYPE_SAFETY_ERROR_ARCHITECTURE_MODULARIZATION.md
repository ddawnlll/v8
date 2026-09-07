# [IMPL] Issue: Type Safety, Error Architecture, and Monolithic Codebase Modularization in v8-core

**Status:** RESOLVED & RATIFIED (D-119)
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `BEHAVIOR_PRESERVING_REFACTOR` / `CONTRACT_IMPLEMENTATION`  
**Labels:** `type:implementation`, `triage`, `risk:medium`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md` §1-3, `D-099`

---

## 1. Objective
Eliminate stringly-typed error and state representations (`Result<T, String>`, candidate state string comparisons) across `v8-core`, replacing them with an idiomatic, strongly-typed `V8CoreError` (`thiserror`) and type-state enums, while decomposing monolithic files (`state.rs` ~3.5k lines and `runloop.rs` ~2.4k lines) into focused, maintainable submodules without altering runtime semantics.

---

## 2. Owning Authority
- **Authority:** V8 Constitution Rule 1 (Codebase integrity and strict type contracts), `docs/WORK_ITEM_POLICY.md` (Anti-invention & Context-completeness).
- **Decisions:** `D-099` (Deterministic computation budget and maintainability).

---

## 3. Current State
- `v8-core/src/scheduler.rs:73` and various helper functions use `Result<T, String>` for error propagation, preventing compile-time pattern matching and error taxonomy classification.
- `v8-core/src/candidate.rs:25-35` relies on raw string equality checks for candidate lifecycle state transitions instead of compile-time verified enums.
- `v8-core/src/state.rs` (3,461 lines) and `v8-core/src/runloop.rs` (2,417 lines) contain tightly coupled logic (indicators, episode steps, state transitions) in single monolithic files, increasing cognitive load and merge conflict risks.

---

## 4. Required End State
1. **`V8CoreError` Architecture:**
   - Define a comprehensive `V8CoreError` enum in `v8-core/src/error.rs` using `thiserror`.
   - Update `scheduler.rs`, `runloop.rs`, and related modules to return `Result<T, V8CoreError>`.
2. **Type-State Lifecycle Enums:**
   - Replace string comparisons in `candidate.rs` with strongly-typed `CandidateState` enums and exhaustive matching.
3. **Submodule Decomposition:**
   - Decompose `state.rs` into a `state/` submodule directory (`indicators.rs`, `market_state.rs`, `mod.rs`).
   - Decompose `runloop.rs` into a `runloop/` submodule directory (`step.rs`, `replay.rs`, `mod.rs`), preserving public API exports.
4. **Behavioral Parity:**
   - All existing tests in `v8-core` must pass without regressions.

---

## 5. Expected File / Module Surface
- `v8-core/src/error.rs` [NEW]
- `v8-core/src/scheduler.rs` [MODIFY]
- `v8-core/src/candidate.rs` [MODIFY]
- `v8-core/src/state.rs` -> `v8-core/src/state/` [REFACTOR] <!-- AUDIT-DOC-PATHS: PLANNED_MODULE `v8-core/src/state/` is the directory this issue's REFACTOR step creates; the pre-refactor path is the one that exists today. -->
- `v8-core/src/runloop.rs` -> `v8-core/src/runloop/` [REFACTOR] <!-- AUDIT-DOC-PATHS: PLANNED_MODULE `v8-core/src/runloop/` is the directory this issue's REFACTOR step creates; the pre-refactor path is the one that exists today. -->
- `v8-core/src/lib.rs` / `v8-core/src/main.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml -- -D warnings
.venv/bin/python tools/audit_python_boundary.py
```

---

## 7. Required Evidence Artifacts
- Successful compilation and test receipt from `cargo test --manifest-path v8-core/Cargo.toml`.

---

## 8. Non-Goals / Forbidden Scope
- Modifying quantitative mathematical formulas, execution algorithms, or trading rules.
- Modifying `src/v8/` or `tests/` (Python boundary locked).

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Strongly-Typed Error Propagation:** Replace all `Result<T, String>` with `Result<T, V8CoreError>` in core compute modules.
  * *Authority:* V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md` §1.
- **R2 — Enum-Driven State Transitions:** Convert candidate lifecycle state transitions from string matching to type-state enums.
  * *Authority:* V8 Constitution Rule 1.
- **R3 — Modularization:** Break down monolithic files (`state.rs`, `runloop.rs`) into clean submodules while maintaining bitwise / behavioral parity.
  * *Authority:* `docs/WORK_ITEM_POLICY.md` §3 (`BEHAVIOR_PRESERVING_REFACTOR`).

### 12. Existing Types / Interfaces to Reuse
- Reuse existing data structs (`Candidate`, `MarketState`, `EpisodeReceipt`).
- Reuse existing CLI interface and command definitions.

### 13. Mathematical / Semantic Invariants
- **I1:** Refactored modules must produce 100% identical outputs for any given tape input.
- **I2:** Error conversions must preserve context and underlying cause.

### 14. Canonical Failure Semantics
- Errors mapped to concrete variants: `V8CoreError::SchedulerError`, `V8CoreError::StateTransitionError`, `V8CoreError::IoError`.

### 15. Dependency Map
```text
Existing candidate.rs / state.rs / runloop.rs
  -> NEW error.rs (V8CoreError)
  -> REFACTORED state/ submodules
  -> REFACTORED runloop/ submodules
  -> Public re-exports via lib.rs
```

### 16. Ambiguity / OPEN_PIN Triggers
- If any refactoring alters mathematical calculation outputs or test fixtures, STOP immediately and log an `OPEN_PIN`.
