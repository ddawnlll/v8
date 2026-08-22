# [PERF] Issue: Zero-Allocation Feature and State Projection in Per-Bar Runloop

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `MEMORY_BOUND_IMPROVEMENT`  
**Labels:** `type:performance`, `triage`, `risk:medium`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-083`, `D-099`

---

## 1. Objective
Eliminate per-bar `HashMap<String, state::Feature>` allocations and cloning inside the main evaluation runloop (`v8-core/src/runloop.rs:431-435`), transitioning to a fixed-array / zero-allocation slice-based feature projection model.

---

## 2. Owning Authority
- **Authority:** `D-083` (Borrowed view and zero-copy representation), `D-099` (Computation Budget Policy), `MARKET_STATE_CONTRACT`.
- **Target Performance Envelope:** Reduce per-bar feature preparation and dispatch overhead from ~12–18 ms down to < 0.5 ms per bar (10x–25x speedup in evaluation loop).

---

## 3. Current State / Profile Baseline
- `v8-core/src/runloop.rs:431-435`: On every bar $i$ for every symbol, the runloop executes:
  ```rust
  let feats = state::state_features(store, t, as_of, req.history_depth);
  let mut map: HashMap<String, state::Feature> = HashMap::new();
  for f in &feats {
      map.insert(f.name.clone(), f.clone());
  }
  ```
- For an 8,760-bar single-symbol run, this allocates and destroys 8,760 hash maps and clones 674,520 `Feature` structs containing heap-allocated `String` fields.
- For 28 experts evaluated per bar, `ProjectedFeatures` performs repeated string lookup against this temporary map.

---

## 4. Required End State / Optimization Target
1. **Fixed Array / Index-Based Feature Representation:**
   Represent feature sets using contiguous arrays (`[f64; 77]`) or dense struct layouts indexed by `FeatureId` enum rather than string keys.
2. **Zero Heap Allocation in Per-Bar Loop:**
   Expert feature projection (`FeatMap`, `ProjectedFeatures`) must operate purely on borrowed slices `&[f64]` with 0 heap allocations per bar.
3. **Parity Preservation:**
   Feature values emitted to downstream expert logic must remain bit-identical.

---

## 5. Expected File / Module Surface
- `v8-core/src/state.rs` [MODIFY]
- `v8-core/src/features.rs` [MODIFY]
- `v8-core/src/experts/base.rs` [MODIFY]
- `v8-core/src/runloop.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
```

---

## 7. Required Evidence Artifacts
- Heap allocation profiling (e.g. `dhat` or allocation counter) confirming zero heap allocations per bar during `runloop::evaluate`.

---

## 8. Non-Goals / Forbidden Scope
- Changing feature definitions or math.
- Modifying expert decision boundaries.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Zero-Allocation State Loop:** Per-bar feature evaluation must not allocate on the heap.
  * *Authority:* `D-083`, `D-099`.

### 12. Existing Types / Interfaces to Reuse
- `FeatureStore`, `FeatMap`, `FEATURE_NAMES`.

### 13. Mathematical / Semantic Invariants
- `I1`: Bit-exact match for all 77 feature values.

### 14. Canonical Failure Semantics
- Absent/unwarmed features map cleanly to `Option::None` or `NaN` as specified in `MARKET_STATE_CONTRACT`.

### 15. Dependency Map
```text
FeatureStore -> Fixed Slice [f64; 77] -> ProjectedFeatures -> Expert Evaluator
```

### 16. Ambiguity / OPEN_PIN Triggers
- If any dynamic expert requires custom feature names not present in `FEATURE_NAMES`, register them in the canonical table.
