# [PERF] Issue: Incremental Dataset Hashing and Elimination of Eager JSON Serialization in Cache Hot Path

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `MEMORY_BOUND_IMPROVEMENT`  
**Labels:** `type:performance`, `triage`, `risk:medium`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-080`, `D-099`, `D-120`

---

## 1. Objective
Eliminate eager, full-tape JSON serialization (`serde_json::Value::Array`) during `data_hash` calculation in `write_cube_reduced`, replacing it with precomputed streaming cryptographic digests (`BLAKE3`/`SHA-256`) computed during tape ingestion.

---

## 2. Owning Authority
- **Authority:** `D-080` (Ledger tiering & representation), `D-099` (Computation Budget Policy), `D-120` (Multi-digest cryptographic architecture).
- **Target Performance Envelope:** Reduce `write_cube_reduced` preparation time from ~200–500 ms to < 0.1 ms (instantaneous cache key generation).

---

## 3. Current State / Profile Baseline
- `v8-core/src/runloop.rs:1073-1089`: To build the `data_hash` for the Outcome Cube DAG cache key, `write_cube_reduced` converts every `TapeRow` in `ds.rows` into a `serde_json::Value` tree:
  ```rust
  let data_hash = hash::hash_value(&Value::Array(
      ds.rows.iter().map(|r| serde_json::json!({ ... })).collect(),
  ));
  ```
- For a dataset with 50,000–100,000 tape rows, this eagerly constructs hundreds of thousands of heap-allocated JSON objects, creating severe latency spikes, memory inflation, and allocator fragmentation.

---

## 4. Required End State / Optimization Target
1. **Streaming Incremental Dataset Digest:**
   Calculate and store the cryptographic `data_hash` once during dataset loading (`data::Dataset::from_rows` / `TapeReader`) via incremental streaming hashing (`BLAKE3`/`SHA-256`).
2. **Zero-Allocation Cache Key Formulation:**
   `canonical_key` generation in `write_cube_reduced` must reuse precalculated `ds.data_hash` without touching individual rows or serializing JSON.
3. **Parity Preservation:**
   Cache hit/miss behavior and hash reproducibility must remain consistent across runs.

---

## 5. Expected File / Module Surface
- `v8-core/src/data.rs` [MODIFY]
- `v8-core/src/hash.rs` [MODIFY]
- `v8-core/src/cache.rs` [MODIFY]
- `v8-core/src/runloop.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
```

---

## 7. Required Evidence Artifacts
- Latency benchmarks of `write_cube_reduced` on 100,000-row datasets before and after streaming hash integration.

---

## 8. Non-Goals / Forbidden Scope
- Changing cache key collision resistance or invalidating valid cached entries without format version updates.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Incremental Digest:** Dataset hash must be computed in a single streaming pass ($O(N)$ with $O(1)$ auxiliary RAM).
  * *Authority:* `D-099`, `D-120`.

### 12. Existing Types / Interfaces to Reuse
- `Dataset`, `CacheStore`, `hash::Canon`, `hash::hash_value`.

### 13. Mathematical / Semantic Invariants
- `I1`: Identical dataset inputs produce identical deterministic `data_hash` values.

### 14. Canonical Failure Semantics
- Ingestion errors fail immediately with `V8CoreError::IngestionError`.

### 15. Dependency Map
```text
Tape Ingestion -> Streaming Hasher -> Dataset.data_hash -> Cache Key Generator -> CacheStore
```

### 16. Ambiguity / OPEN_PIN Triggers
- If binary hash encoding deviates from legacy JSON string digests, update `hash_encoding` version in artifact metadata in conformance with D-080.
