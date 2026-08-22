# [PERF] Issue: Direct Symbol Indexing and Elimination of Linear String Scans in Replay Dispatch

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `BITWISE_PRESERVING_REFACTOR`  
**Labels:** `type:performance`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-083`, `D-099`

---

## 1. Objective
Replace $O(N_{\text{symbols}})$ linear string searches (`.find(|b| b.symbol == cell.symbol)`) across `dataset.bars` and `stores` inside inner cell replay loops with $O(1)$ integer symbol indexing (`SymbolId(u16)` or direct slice pointers).

---

## 2. Owning Authority
- **Authority:** `D-083` (Bounded view / index representation), `D-099` (Computation Budget Policy).
- **Target Performance Envelope:** Eliminate linear search overhead across multi-symbol replay batches (2x–4x speedup in dispatch loop).

---

## 3. Current State / Profile Baseline
- `v8-core/src/backend/simd.rs:77-86`: Inside `SimdBackend::evaluate`:
  ```rust
  for (cell, slot) in cells.iter().zip(output.iter_mut()) {
      let bars = dataset.bars.iter().find(|b| b.symbol == cell.symbol)...
      let store = self.stores.iter().find(|s| s.symbol == cell.symbol)...
  ```
- `v8-core/src/runloop.rs:962-970`: Inside `write_cube_reduced`, every candidate iterates over all stores and bars with string equality checks.
- In large batches (e.g. 500,000 cells across 100 symbols), this yields tens of millions of redundant string comparisons.

---

## 4. Required End State / Optimization Target
1. **Integer Symbol Identifier (`SymbolId`):**
   Assign a compact `SymbolId(u16)` to symbols during dataset construction.
2. **Direct Slice / Direct Index Lookup:**
   Store bars and feature stores in indexed arrays where `bars[symbol_id as usize]` provides instantaneous $O(1)$ memory dereference.
3. **Parity Preservation:**
   Zero semantic change to simulation evaluation.

---

## 5. Expected File / Module Surface
- `v8-core/src/data.rs` [MODIFY]
- `v8-core/src/backend/scalar.rs` [MODIFY]
- `v8-core/src/backend/simd.rs` [MODIFY]
- `v8-core/src/runloop.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
```

---

## 7. Required Evidence Artifacts
- Microbenchmark measuring dispatch latency on 100-symbol universe before and after integer symbol mapping.

---

## 8. Non-Goals / Forbidden Scope
- Changing symbol naming in user-facing JSON/columnar artifacts.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — $O(1)$ Symbol Lookup:** Symbol data resolution in replay batch must be $O(1)$.
  * *Authority:* `D-083`, `D-099`.

### 12. Existing Types / Interfaces to Reuse
- `Dataset`, `SymbolBars`, `FeatureStore`, `ReplayCell`.

### 13. Mathematical / Semantic Invariants
- `I1`: Replay output invariant under symbol indexing.

### 14. Canonical Failure Semantics
- Out-of-bounds `SymbolId` returns `V8CoreError::UnknownSymbol`.

### 15. Dependency Map
```text
Dataset (SymbolId Registry) -> ReplayCell(symbol_id) -> O(1) Index -> Kernel Replay
```

### 16. Ambiguity / OPEN_PIN Triggers
- None.
