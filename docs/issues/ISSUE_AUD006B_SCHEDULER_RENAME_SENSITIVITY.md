# [IMPL] Issue #AUD-006B: Current R-ALLOC Scheduler Rename Sensitivity Audit (F19)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `risk`  
**Owning Authority:** `COMPUTE_SCHEDULING_SPEC.md` §6.2 (Dispatch Determinism & Tie-Breaks), Decision `D-008` (Ranker Gating), arXiv:2608.08405 (P026).  
**Relationships:** Depends on #178 (Lineage DAG).

---

## 1. Objective
Implement a permutation audit harness in pure Rust (`v8-core/src/scheduler/rename_audit.rs`) to measure portfolio allocation and terminal PnL sensitivity under the *current* `R-ALLOC` policy when Expert IDs are semantically renamed (perturbing the `sha1(expert_id)` tie-break order).

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/COMPUTE_SCHEDULING_SPEC.md`](docs/contracts/COMPUTE_SCHEDULING_SPEC.md) §6.2 (Tie-Break Mechanics).
- **Decision Authority:** `D-008` (Ranker gating & contention ordering).
- **Academic Literature:**
  - `P026` (arXiv:2608.08405): *Robustness or Crowding: Experimental Design for Trading Strategy Capacity*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- When multiple candidates compete for a limited exposure slot, ties are currently broken deterministically using `sha1(expert_id)`.
- Decision Register tracks that changing expert names can alter the execution sequence between behaviorally identical experts.
- An empirical audit is required to measure the exact magnitude of this sensitivity under current production settings without assuming a nonexistent optimal ranker.

---

## 5. Required End State
1. **Permutation Harness:**
   - Execute $N=100$ semantic renaming permutations of active expert identifiers.
   - For each permutation, execute full portfolio simulation.
2. **Sensitivity Metrics:**
   - Measure: $\min(\text{TerminalPnL})$, $\max(\text{TerminalPnL})$, $\sigma(\text{TerminalPnL})$, slot capture churn %.
   - Emits `scheduler_rename_sensitivity.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/scheduler/mod.rs
v8-core/src/scheduler/rename_audit.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Permutation test executing cleanly and producing a deterministic sensitivity interval.
3. Verification that sensitivity metrics are emitted regardless of whether variance is zero or non-zero.

---

## 8. Required Evidence Artifacts
- `scheduler_rename_sensitivity.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify runtime dispatch tie-break rules in this audit issue.

---

## 10. Guards
- [ ] Must evaluate the current baseline `R-ALLOC` policy, not a hypothetical ranker.

---

## 11. Normative Traceability
- **R1 — Dispatch Permutation Measurement:** Measures portfolio drift from hash-order tie breaks.  
  *Authority:* `COMPUTE_SCHEDULING_SPEC.md` §6.2; Decision `D-008`.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::scheduler::BatchWorker`
- `v8-core::runloop::RunloopConfig`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Bounded Sensitivity Interval:** $\Delta \text{PnL}_{\text{range}} = \max_{\pi} \text{PnL}(\pi) - \min_{\pi} \text{PnL}(\pi)$.

---

## 14. Canonical Failure Semantics
- Inconsistent permutation execution $\implies$ `Err(SchedulerError::NonDeterministicDispatch)`.

---

## 15. Dependency Map
```text
Scheduler Dispatch Queue
           │
           ▼
 [Permutation Engine] ──► scheduler_rename_sensitivity.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If identical runs produce different PnL without renaming, STOP and report non-determinism defect.
