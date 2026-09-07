# [PERF] Issue: Elimination of Per-Bar `HistBar.event_id` Heap Allocation and Repeated History Cloning in Runloop

**Status:** PROPOSED  
**Issue Type:** `PERFORMANCE`  
**Change Class:** `PERF_OPTIMIZATION` / `HOT_PATH_ALLOCATION`  
**Labels:** `type:performance`, `triage`, `risk:low`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`, `D-083` (Representation Rule: borrowed views over owned buffers)

---

## 1. Objective
Eliminate redundant per-bar heap allocation of `HistBar.event_id: String` and per-expert vector cloning (`hist.clone()`) during the simulation and runloop step phases. Transition `HistBar` to zero-copy borrowed slices or interned identifier slices, ensuring that evaluating multiple active experts over a sliding historical window performs zero heap allocations per bar.

---

## 2. Owning Authority
- **Authority:** `D-083` ("Representation rule: a layer receives a borrowed view of data it does not own. Copying a window out of an owned buffer is a defect unless the copy is the output"), V8 Constitution Rule 1 (`AUTHORITATIVE_RUNTIME`).
- **Target Performance Envelope:** Reduce simulation per-bar memory churn by **>90%** and reduce runloop execution time in multi-expert evaluation by **3x–5x**.

---

## 3. Current State / Profile Baseline
- In `v8-core/src/state.rs:3700-3717`:
  ```rust
  pub struct HistBar {
      pub event_id: String,
      pub open: f64,
      pub high: f64,
      pub low: f64,
      pub close: f64,
      pub ema_fast: f64,
      pub ema_slow: f64,
  }

  pub fn history_bars(store: &FeatureStore, t: usize, depth: usize) -> Vec<HistBar> {
      ...
      for (k, j) in (win_lo..t).enumerate() {
          out.push(HistBar {
              event_id: store.event_ids[j].clone(), // Heap String allocation!
              ...
          });
      }
      out
  }
  ```
- In `v8-core/src/usdm_sim.rs:552, 595, 659`:
  ```rust
  let expert_hist = if *allows_hist { hist.clone() } else { Vec::new() };
  ```
- For a single 1-year hourly simulation (8,760 bars) with depth 128 and 10 active experts:
  - Each bar allocates a `Vec<HistBar>` of 128 elements, each cloning a heap-allocated `String`.
  - Then, each of the 10 experts performs `hist.clone()`, allocating another 128 `String` instances.
  - Total heap allocations per symbol-year: **8,760 * 128 * 11 ≈ 12,300,000 heap allocations**.
  - This severely degrades CPU cache locality and triggers continuous jemalloc / system allocator locks on multi-core systems.

---

## 4. Required End State / Optimization Target
1. **Zero-Copy Borrowed HistBar View:**
   Transition `HistBar<'a>` to borrow the slice from `FeatureStore`:
   ```rust
   pub struct HistBar<'a> {
       pub event_id: &'a str,
       pub open: f64,
       pub high: f64,
       pub low: f64,
       pub close: f64,
       pub ema_fast: f64,
       pub ema_slow: f64,
   }
   ```
   Or represent historical views as borrowed slice views over the columnar store:
   `pub struct HistorySlice<'a> { store: &'a FeatureStore, start: usize, end: usize }`
2. **Elimination of Per-Expert Cloning:**
   Pass borrowed slices `&[HistBar]` or `HistorySlice<'_>` to expert evaluation functions (`Expert::evaluate(&self, feats: &FeatMap, hist: &[HistBar])`), completely eliminating `hist.clone()`.
3. **Scratch Buffer Re-use for Windowing:**
   If a contiguous slice of `HistBar` is needed, reuse a per-thread or runloop-allocated `Vec<HistBar<'a>>` scratch buffer via `.clear()` rather than re-allocating `Vec::with_capacity(d)` on every bar.

---

## 5. Expected File / Module Surface
- `v8-core/src/state.rs` [MODIFY]
- `v8-core/src/usdm_sim.rs` [MODIFY]
- `v8-core/src/runloop.rs` [MODIFY]
- `v8-core/src/experts/base.rs` [MODIFY]
- `v8-core/src/experts/*.rs` (adjust expert call signatures to borrowed history) [MODIFY]

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
- Microbenchmark comparing bar processing throughput before and after zero-copy history borrowing.
- Verification receipt that `test_af_t12_system_proving_ground_exercises_full_pipeline` and `usdm_sim` output exact bit-for-bit identical trade results.

---

## 8. Anti-Invention & Invariant Declarations
- Must preserve exact floating-point outputs and event order.
- Must strictly comply with `D-083` (borrowed views over owned buffers).
