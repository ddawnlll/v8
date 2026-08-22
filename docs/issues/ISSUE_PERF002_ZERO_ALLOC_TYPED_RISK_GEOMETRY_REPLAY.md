# [PERF] Issue: Zero-Allocation Typed Risk Geometry in Hot-Path Replay Kernel

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `BITWISE_PRESERVING_REFACTOR`  
**Labels:** `type:performance`, `triage`, `risk:medium`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-083`, `D-099`

---

## 1. Objective
Eliminate dynamic `serde_json::Map<String, Value>` allocations and repeated string-key hash table queries (`geom_f64`, `geom_i64`, `has_geom`) inside the per-bar hot simulation path (`ScalarKernel::step`, `ScalarKernel::exit_loop`, `ScalarKernel::exit_loop_simd`), replacing them with a flat, contiguous, zero-allocation typed `RiskGeometry` struct.

---

## 2. Owning Authority
- **Authority:** `D-083` (Representation rule / bounded view), `D-099` (Computation Budget Policy), `COMPUTE_CORE_SPEC` §4.
- **Target Performance Envelope:** Reduce per-cell replay latency from ~3.5–6.0 µs down to < 0.2 µs (15x–30x speedup in replay kernel).

---

## 3. Current State / Profile Baseline
- `v8-core/src/simulator.rs:30-62`: `Draft.risk_geometry` is defined as `serde_json::Map<String, Value>`.
- `v8-core/src/backend/scalar.rs:162-280`: In `ScalarKernel::step()`, every single bar step dynamically looks up `"target_r"`, `"stop_r"`, `"expiry_bars"`, `"stop_ref"`, `"time_exit_bars"`, `"breakeven_roll_at_mfe_r"`, `"trail_stop_atr"`, `"scale_out_ratio"` via string queries on the heap-allocated map.
- Additionally, `validate_geometry(draft)` is invoked redundantly on every bar step inside `step()`.
- Profiling reveals >100M string hash map lookups in a standard 250,000-cell sweep.

---

## 4. Required End State / Optimization Target
1. **Typed Flat Struct:**
   Define a contiguous, `Copy`-able `RiskGeometry` struct with declared optional and scalar fields (`target_r: Option<f64>`, `stop_r: Option<f64>`, `expiry_bars: usize`, `stop_ref: Option<f64>`, etc.).
2. **Zero String Hashing on Hot Path:**
   All field accesses inside `step()` and `exit_loop()` must compile down to direct struct field offsets (0 CPU memory allocation, 0 string hashing).
3. **Admission-Only Validation:**
   Ensure geometry validation runs strictly at candidate admission / cell generation, eliminating per-bar redundant validation while maintaining fail-closed semantics.
4. **Exact Parity Preservation:**
   $100\%$ bit-identical outcome matching against legacy golden replay outcomes.

---

## 5. Expected File / Module Surface
- `v8-core/src/simulator.rs` [MODIFY]
- `v8-core/src/backend/scalar.rs` [MODIFY]
- `v8-core/src/backend/simd.rs` [MODIFY]
- `v8-core/src/candidate.rs` [MODIFY]
- `v8-core/src/regret.rs` [MODIFY]
- `v8-core/src/runloop.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml -- test_replay_parity
```

---

## 7. Required Evidence Artifacts
- Microbenchmark comparing `ScalarKernel::run` and `SimdKernel::run` throughput (cells/sec) before and after typed geometry refactoring.

---

## 8. Non-Goals / Forbidden Scope
- Altering the mathematical semantics of fill policies, gap handling, or pyramiding logic.
- Loosening floating-point precision contracts (`fp-contract=off` remains mandatory).

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Zero-Allocation Geometry Access:** All geometry lookups in `step()` must execute with $O(1)$ memory access and 0 heap allocations.
  * *Authority:* `D-083`, `D-099`.
- **R2 — Parity Invariance:** Outcome outputs (`net_r`, `mae_r`, `mfe_r`, `endpoint`) must match existing outputs bit-for-bit.
  * *Authority:* `COMPUTE_CORE_SPEC` §4.

### 12. Existing Types / Interfaces to Reuse
- `Draft`, `FillPolicy`, `Outcome`, `Pos`.

### 13. Mathematical / Semantic Invariants
- `I1`: Bit-exact equality across all test cases (`Outcome` fields identical).

### 14. Canonical Failure Semantics
- Non-positive risk units or invalid geometry definitions fail closed returning `V8CoreError::InvalidGeometry`.

### 15. Dependency Map
```text
Candidate Draft -> Typed RiskGeometry -> ScalarKernel / SimdKernel -> Outcome
```

### 16. Ambiguity / OPEN_PIN Triggers
- If any dynamic expert emits unmodeled ad-hoc keys in `risk_geometry`, declare a formal schema extension rather than falling back to unconstrained JSON maps.
