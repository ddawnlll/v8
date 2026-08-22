# [PERF] Issue: Zero-Allocation Predicate IR Evaluation and Indicator Precomputation in FeatureStore

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `MEMORY_BOUND_IMPROVEMENT`  
**Labels:** `type:performance`, `triage`, `risk:medium`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-083`, `D-099`, `PREDICATE_IR_SPEC`

---

## 1. Objective
Eliminate redundant per-step indicator recalculations (e.g. `stoch_k` in `live_feature`) and heap allocations in `history_window` during predicate thesis evaluation, replacing them with fully precomputed indicator series and zero-copy ring-buffer slice views.

---

## 2. Owning Authority
- **Authority:** `D-083` (Representation rule), `D-099` (Computation Budget Policy), `PREDICATE_IR_SPEC`.
- **Target Performance Envelope:** Reduce thesis evaluation time from ~1.5 µs to < 0.05 µs (30x speedup).

---

## 3. Current State / Profile Baseline
- `v8-core/src/state.rs:3347-3360`: In `live_feature`, whenever `stoch_k` is evaluated for candidate post-entry thesis validation, `stoch(highs, lows, closes, 14)` is computed from scratch across the full history `..t`.
- `v8-core/src/state.rs:3384-3400`: `history_window` allocates a brand new `Vec<[f64; 6]>` on the heap every single time a window aggregation is evaluated by the compiled predicate IR.
- In long-running exit walks, this generates massive CPU churn and memory pressure.

---

## 4. Required End State / Optimization Target
1. **Precomputed `stoch_k` / Indicator Series:**
   Precompute `stoch_k` series in `FeatureStore` during initial feature build (just like `rsi`, `macd`, `ema`).
2. **Zero-Allocation History Views:**
   Provide zero-copy borrowed slice views or fixed stack-allocated buffers for `history_window` rather than heap `Vec` allocations.
3. **Parity Preservation:**
   Predicate evaluation boolean output must match the oracle identically on every bar.

---

## 5. Expected File / Module Surface
- `v8-core/src/state.rs` [MODIFY]
- `v8-core/src/experts/predicate.rs` [MODIFY]
- `v8-core/src/backend/scalar.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
```

---

## 7. Required Evidence Artifacts
- Microbenchmarks of compiled predicate IR evaluation before and after precomputation and zero-allocation view refactoring.

---

## 8. Non-Goals / Forbidden Scope
- Changing predicate grammar or thesis invalidation logic.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Precomputed Indicators:** All state features used in predicate evaluation must be precomputed in $O(N)$ tape ingestion.
  * *Authority:* `D-099`, `PREDICATE_IR_SPEC`.
- **R2 — Zero-Allocation History View:** Windowed history queries in predicate IR must not allocate on the heap.
  * *Authority:* `D-083`.

### 12. Existing Types / Interfaces to Reuse
- `FeatureStore`, `FeatCtx`, `predicate::IR`.

### 13. Mathematical / Semantic Invariants
- `I1`: Bit-exact identity of indicator values and thesis validity flags.

### 14. Canonical Failure Semantics
- Unwarmed indicator windows fail open as specified in `PREDICATE_IR_SPEC`.

### 15. Dependency Map
```text
FeatureStore (Precomputed Stoch & Indicators) -> Zero-Copy FeatCtx -> Predicate IR -> Thesis Validity
```

### 16. Ambiguity / OPEN_PIN Triggers
- None.
