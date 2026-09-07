# [PERF] Issue: Zero-Copy Memmap Streaming Tape Reader and High-Throughput Binary IPC

**Status:** RESOLVED & RATIFIED (D-121)
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `CONTRACT_IMPLEMENTATION`  
**Labels:** `type:performance`, `triage`, `risk:high`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-099`

---

## 1. Objective
Replace memory-inefficient, eager in-RAM tape ingestion (`Vec<TapeRow>`) with a zero-copy, chunked memory-mapped reader (`memmap2`), and eliminate internal JSON serialization overhead in intermediate runloop operations via zero-copy binary serialization (Bincode/FlatBuffers).

---

## 2. Owning Authority
- **Authority:** V8 Constitution Rule 1, `D-099` (High throughput compute budget).
- **Target Performance Envelope:** OOM-free processing of 50GB+ tick tapes in sub-100MB resident memory (RSS).

---

## 3. Current State
- `v8-core/src/data.rs:1-120` reads entire tape files into a standard heap-allocated `Vec<TapeRow>`. Large datasets cause excessive RAM usage, garbage collection/allocator thrashing, and potential OOM crashes.
- `v8-core/src/runloop.rs:82-125` performs JSON serialization for internal state transfers and intermediate steps, introducing heavy CPU allocation overhead in the hot simulation path.

---

## 4. Required End State
1. **Zero-Copy Chunked Streaming Reader:**
   - Implement `TapeReader` using `memmap2` and iterator-based chunking to stream rows without loading entire datasets into memory.
2. **Binary IPC & State Transfer:**
   - Replace intermediate JSON encoding/decoding in the hot simulation loop with `bincode` / zero-copy binary encodings.
3. **Parity Preservation:**
   - Ensure identical numeric simulation results between the legacy reader and the streaming reader.

---

## 5. Expected File / Module Surface
- `v8-core/Cargo.toml` [MODIFY]
- `v8-core/src/data.rs` [MODIFY]
- `v8-core/src/runloop.rs` [MODIFY]
- `v8-core/benches/` [NEW / MODIFY] <!-- AUDIT-DOC-PATHS: PLANNED_MODULE `v8-core/benches/` is the directory this issue creates; it does not exist before the work lands. -->

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
cargo bench --manifest-path v8-core/Cargo.toml
```

---

## 7. Required Evidence Artifacts
- Benchmark report comparing memory footprint (RSS) and throughput (ticks/sec) before and after optimization.

---

## 8. Non-Goals / Forbidden Scope
- Changing the schema or interpretation of `TapeRow` fields.
- Introducing synthetic data into evaluation pipelines.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Streaming Reader:** Memory consumption must remain bounded ($O(1)$ RAM complexity relative to tape file size).
  * *Authority:* `D-099`.
- **R2 — High-Throughput Intermediate State:** Hot-path simulation serialization must use zero-copy binary formats.
  * *Authority:* `D-099`.

### 12. Existing Types / Interfaces to Reuse
- Reuse `TapeRow`, `MarketState`, `Candle` definitions.

### 13. Mathematical / Semantic Invariants
- **I1:** Ticks/rows streamed via `memmap2` must preserve strict timestamp ordering and identical float precision.

### 14. Canonical Failure Semantics
- Malformed tape chunks return `V8CoreError::CorruptTapeHeader` or `V8CoreError::IoError`.

### 15. Dependency Map
```text
Raw Tape File
  -> memmap2 Mmap
  -> Streaming TapeIterator
  -> Hot Path (Bincode Binary State)
  -> Simulation Outcome
```

### 16. Ambiguity / OPEN_PIN Triggers
- If binary serialization format causes breaking changes to externally consumed JSON audit artifacts, retain JSON only at the boundary/export layer.
