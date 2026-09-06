# [PERF] Issue: Zero-Allocation Scratch Buffering in Block-Bootstrap Reality Check and Detrended Null

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `MEMORY_BOUND_IMPROVEMENT`  
**Labels:** `type:performance`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-083`, `D-099` (Computation Budget Policy)

---

## 1. Objective
Eliminate repetitive per-resample heap allocations (`Vec<usize>` and `Vec<f64>`) inside statistical resampling loops (`reality_check_p_value`, `block_bootstrap_means`, and `block_bootstrap_indices`), replacing them with pre-allocated scratch buffers reused across all $N_{\text{resamples}}$ draws.

---

## 2. Owning Authority
- **Authority:** `D-083` (Representation rule / zero-copy views), `D-099` (Computation Budget Policy), `STATISTICAL_RIGOR_SPEC`.
- **Target Performance Envelope:** Reduce White 2000 Reality Check and Detrended Null evaluation latency by **5x–8x** (e.g. from ~800 ms down to < 100 ms for 2,000 resamples across multi-configuration families).

---

## 3. Current State / Profile Baseline
- `v8-core/src/statistics/reality_check.rs:134-142`:
  In `block_bootstrap_indices`, every single resample call allocates a fresh `Vec<usize>`:
  ```rust
  let mut out: Vec<usize> = Vec::with_capacity(n + bs);
  ```
- `v8-core/src/statistics/reality_check.rs:221-230`:
  In `reality_check_p_value`, inside the `for _ in 0..n_resamples` loop:
  ```rust
  let idx = block_bootstrap_indices(n, block_size, &mut rng)?;
  for (ci, (_, series)) in episode_net_r.iter().enumerate() {
      let drawn: Vec<f64> = idx.iter().map(|&i| series[i]).collect(); // Fresh Vec allocated every round!
      let stat = fsum(&drawn) / nf - means[ci];
  }
  ```
- For $N_{\text{resamples}} = 2,000$ and $K = 10$ configurations:
  $2,000 \times 10 = 20,000$ heap vector allocations and frees per statistical p-value evaluation.
- `block_bootstrap_means` has an identical heap allocation pattern on every resample iteration.

---

## 4. Required End State / Optimization Target
1. **Reusable In-Place Index Buffer:**
   Refactor `block_bootstrap_indices` to populate a caller-provided mutable slice buffer (`&mut [usize]`) without allocating.
2. **Reusable Resample Draw Buffer:**
   Allocate a single reusable `Vec<f64>` scratch buffer before the resample loop, overwriting values in place rather than calling `.collect()` on every configuration and iteration.
3. **Exact RNG Sequence & Parity Preservation:**
   The exact sequence of MT19937 RNG draws and `fsum` arguments remains identical, ensuring 100% bitwise parity with existing outputs.

---

## 5. Expected File / Module Surface
- `v8-core/src/statistics/reality_check.rs` [MODIFY]
- `v8-core/src/statistics/detrended.rs` [MODIFY]
- `v8-core/src/statistics/mod.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml -- reality_check
cargo test --manifest-path v8-core/Cargo.toml -- detrended
```

---

## 7. Required Evidence Artifacts
- Microbenchmarks of `reality_check_p_value` before and after scratch buffer refactoring.
- Parity confirmation that p-values and argmax configurations remain identical.

---

## 8. Non-Goals / Forbidden Scope
- Changing the MT19937 seed flow or block sampling logic.
- Approximating `fsum` with a standard fold (Shewchuk compensated summation contract remains strictly enforced).

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Zero-Allocation Resample Loop:** Inner iterations of block-bootstrap sampling must allocate 0 bytes on the heap.
  * *Authority:* `D-083`, `D-099`.
- **R2 — Bitwise Determinism:** Outputs must match existing CPython oracle parity tests exactly.
  * *Authority:* `PARITY_AND_IDENTITY_SPEC` §3.

### 12. Existing Types / Interfaces to Reuse
- `RealityCheckResult`, `MT19937`, `fsum`.

### 13. Mathematical / Semantic Invariants
- `I1`: Compound null recentering and max-statistic logic bit-for-bit identical.

### 14. Canonical Failure Semantics
- Zero/empty series or degenerate block size fail closed identically.

### 15. Dependency Map
```text
reality_check_p_value
 ├── ScratchBuffer::indices: Vec<usize> (allocated once)
 ├── ScratchBuffer::draw: Vec<f64> (allocated once)
 └── Reused across 1..N_resamples with fsum
```

### 16. Ambiguity / OPEN_PIN Triggers
- None.
