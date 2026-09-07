# [PERF] Issue: Multi-Core Parallelism in Bootstrap Resampling, Reality Check, and Monte Carlo Projections

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `CONCURRENCY_PARALLELISM`  
**Labels:** `type:performance`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-099` (Computation Budget Policy)

---

## 1. Objective
Introduce deterministic data-parallel execution using `rayon` for heavy CPU-bound resample loops (White 2000 Reality Check, Detrended Null, Stationary Block Bootstrap, and Monte Carlo capital outcome projections). Ensure full multi-core saturation on modern high-core-count developer and server workstations (such as Apple Silicon M-series and multi-core AMD/Intel servers) without breaking bit-exact determinism or reproducibility contracts.

---

## 2. Owning Authority
- **Authority:** `D-099` (Computation Budget Policy), V8 Constitution Rule 1 (`AUTHORITATIVE_RUNTIME`).
- **Target Performance Envelope:** Accelerate statistical validation and projection phases by **N-fold** proportional to available CPU physical cores (on an M3 Max / Pro: 8x–12x speedup in WRC bootstrap and Monte Carlo generation).

---

## 3. Current State / Profile Baseline
- In `v8-core/src/statistics/reality_check.rs:225-240`:
  ```rust
  for _ in 0..n_resamples { // Default 2,000 resamples
      let idx = block_bootstrap_indices(n, block_size, &mut rng)?;
      for (ci, (_, series)) in episode_net_r.iter().enumerate() {
          let drawn: Vec<f64> = idx.iter().map(|&i| series[i]).collect();
          let stat = fsum(&drawn) / nf - means[ci];
          ...
      }
  }
  ```
- In `v8-core/src/benchmark/projection.rs:218-245`:
  ```rust
  for _ in 0..num_paths { // Default 1,000+ paths
      // Sequential trajectory simulation
  }
  ```
- In `v8-core/src/world/generator.rs` and `world_foundry_v2_falsification.rs`:
  - Stationary bootstrap generation runs sequentially in a single-threaded loop.
- **Problem:** On an M3 Pro / Max (12–16 cores), all of these intensive computational routines execute on a single core, leaving 90%+ of hardware capacity idle while running tests or verification audits for minutes.

---

## 4. Required End State / Optimization Target
1. **Deterministic Parallel Bootstrap Execution:**
   Utilize `rayon::prelude::*` for resample iterations. Determinism is preserved by deriving per-iteration seeded PRNGs (`ChaCha8Rng` or seed derived from parent seed + iteration index), ensuring bit-exact parity regardless of core count or scheduling order.
2. **Parallel Monte Carlo Path Simulation:**
   Parallelize path generation in `simulate_monte_carlo_futures` using `par_iter()`.
3. **Opt-in Feature or Safe Default:**
   Add `rayon` to `v8-core/Cargo.toml` as a standard dependency or core runtime feature. Ensure non-blocking fallbacks for single-threaded environments if requested via `--threads 1`.

---

## 5. Expected File / Module Surface
- `v8-core/Cargo.toml` [MODIFY]
- `v8-core/src/statistics/reality_check.rs` [MODIFY]
- `v8-core/src/benchmark/projection.rs` [MODIFY]
- `v8-core/src/world/reverse_stress.rs` [MODIFY]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml
python3 tools/audit_synthetic_leakage.py
python3 tools/audit_economic_claim.py
```

---

## 7. Required Evidence Artifacts
- Core scaling benchmark showing linear or near-linear scaling from 1 to N cores.
- Determinism receipt verifying that running with 1, 4, 8, or 16 threads produces identical output hashes and p-values.

---

## 8. Anti-Invention & Invariant Declarations
- Rule 12 (`NO_ECONOMIC_CLAIM`) and Rule 13 determinism invariants must strictly hold.
- Thread scheduling must not affect PRNG draw sequence or terminal floating-point sums.
