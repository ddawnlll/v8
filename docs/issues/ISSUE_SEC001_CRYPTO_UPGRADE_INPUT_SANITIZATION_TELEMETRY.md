# [IMPL] Issue: Cryptographic Hashing Upgrade, Path Traversal Sanitization, and Structured Telemetry

**Status:** OPEN  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `CORRECTNESS_SEMANTICS`  
**Labels:** `type:implementation`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1 & Rule 5 (Anti-hallucination / verifiable receipts), `docs/WORK_ITEM_POLICY.md`

---

## 1. Objective
Upgrade legacy SHA-1 hashing to modern collision-resistant BLAKE3 / SHA-256 in `v8-core/src/hash.rs`, enforce strict canonical path traversal sanitization on CLI input arguments in `v8-core/src/main.rs`, and integrate `tracing` / `metrics` facades for structured telemetry and profiling.

---

## 2. Owning Authority
- **Authority:** V8 Constitution Rule 1 & Rule 5 (Deterministic verifiable audit trails and verifiable receipts).
- **Decisions:** `D-099` (Profiling and observability budgets).

---

## 3. Current State
- `v8-core/src/hash.rs:1-50` utilizes SHA-1 for artifact and receipt hashing.
- `v8-core/src/main.rs:97-120` reads file paths without canonicalizing against a safe root working directory.
- `v8-core/Cargo.toml` lacks `tracing` and `metrics` crates, leaving long batch simulations and server runloops without structured span/metric instrumentation.

---

## 4. Required End State
1. **Cryptographic Hashing:**
   - Migrate hashing utilities to `blake3` (for ultra-fast internal integrity) and `sha2` (SHA-256 for external receipt interoperability).
2. **Path Sanitization:**
   - Add safe path resolution helpers using `std::fs::canonicalize` and boundary validation.
3. **Telemetry & Profiling:**
   - Add `tracing` and `metrics` dependencies to `v8-core/Cargo.toml`.
   - Instrument `runloop` steps and episode simulations with info/debug spans.

---

## 5. Expected File / Module Surface
- `v8-core/Cargo.toml` [MODIFY]
- `v8-core/src/hash.rs` [MODIFY]
- `v8-core/src/main.rs` [MODIFY]
- `v8-core/src/telemetry.rs` [NEW]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml -- -D warnings
```

---

## 7. Required Evidence Artifacts
- Unit test suite verifying BLAKE3/SHA-256 determinism and path traversal sanitization rejection tests.

---

## 8. Non-Goals / Forbidden Scope
- Breaking existing golden receipt hashes without a documented migration receipt.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Cryptographic Upgrades:** Replace SHA-1 with BLAKE3/SHA-256 for receipt generation.
  * *Authority:* V8 Constitution Rule 5.
- **R2 — Path Sanitization:** Ensure all CLI path parameters fail closed if outside permissible workspace bounds.
  * *Authority:* V8 Constitution Rule 1.
- **R3 — Telemetry Facade:** Provide zero-overhead tracing infrastructure.
  * *Authority:* `D-099`.

### 12. Existing Types / Interfaces to Reuse
- Reuse `v8-core::hash` module functions and existing CLI error handlers.

### 13. Mathematical / Semantic Invariants
- **I1:** Hashes generated from the same byte stream must be 100% deterministic and bit-for-bit identical across runs.

### 14. Canonical Failure Semantics
- Path traversal violations return `V8CoreError::InvalidPathError` / `CANONICAL_REFUSAL`.

### 15. Dependency Map
```text
Existing main.rs / hash.rs
  -> NEW blake3 / sha2 / tracing dependencies
  -> Refactored hash functions & path validation checks
```

### 16. Ambiguity / OPEN_PIN Triggers
- If existing audit verification tooling relies on legacy SHA-1 string length, provide backwards compatibility adapter or escalate OPEN_PIN.
