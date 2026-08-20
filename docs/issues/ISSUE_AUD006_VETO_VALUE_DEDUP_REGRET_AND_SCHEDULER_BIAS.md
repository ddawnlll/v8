# [IMPL] Issue #AUD-006: Veto Economic Value, Dedup Suppression Regret & Scheduler Bias (F19, F27)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `risk`  
**Owning Authority:** `COMPUTE_SCHEDULING_SPEC.md` §4–7, `REGRET_SYSTEM_SPEC.md` §3–5, arXiv:2608.08405 (P026), arXiv:2606.29018 (P023).

---

## 1. Objective
Implement counterfactual economic attribution for runtime vetoes (`EXISTING_EXPOSURE_CONFLICT`, `PORTFOLIO_HEAT_EXCEEDED`), audit the opportunity loss / regret of the 14,766 deduplication suppressions, and test scheduler tie-break permutation invariance (`sha1(expert_id)` vs semantic renaming) in pure Rust (`v8-core/src/scheduler/bias_audit.rs`).

---

## 2. Owning Authority
- **Scheduling Specification:** [`docs/contracts/COMPUTE_SCHEDULING_SPEC.md`](docs/contracts/COMPUTE_SCHEDULING_SPEC.md) §4–7 (Tie-break ordering, dispatch determinism).
- **Regret Specification:** [`docs/contracts/REGRET_SYSTEM_SPEC.md`](docs/contracts/REGRET_SYSTEM_SPEC.md) §3–5.
- **Academic Literature:**
  - `P026` (arXiv:2608.08405): *Robustness or Crowding: Experimental Design for Trading Strategy Capacity*.
  - `P023` (arXiv:2606.29018): *Liquidity-Based Audit of AI and Algorithmic Trading Strategies* (Contention & crowding).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Admission vetoes suppress candidates to enforce portfolio heat and concurrency limits, but there is no counterfactual tracking of whether the vetoed candidates would have produced profit or loss (`avoided_loss` vs `missed_profit`).
- 14,766 duplicate setups were suppressed at the front of the pipeline without measuring if duplicate signals carried higher signal conviction or different exit timing.
- Slot conflicts are broken by `sha1(expert_id)`, which is deterministic but economically arbitrary. Renaming an expert could change portfolio PnL.

---

## 5. Required End State
1. **Veto Economic Attribution:**
   - For every vetoed trade, compute counterfactual path: $\text{avoided\_loss\_usdt}$, $\text{missed\_profit\_usdt}$, $\text{net\_gate\_value\_usdt}$.
   - Emits `veto_attribution.parquet`.
2. **Dedup Suppression Regret Audit:**
   - Compare suppressed duplicate episodes against admitted parent episodes. Emits `dedup_regret.json`.
3. **Scheduler Tie-Break Invariance Test:**
   - Execute permutation metamorphic test: semantically rename Expert IDs and verify if portfolio allocation and terminal PnL change.
   - Emits `scheduler_bias_receipt.json` quantifying scheduler-induced allocation drift.

---

## 6. Expected File / Module Surface
```text
v8-core/src/scheduler/mod.rs
v8-core/src/scheduler/bias_audit.rs
v8-core/src/runloop.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Veto counterfactual attribution tests confirming exact balance matching.
3. Dedup comparison analysis verifying whether duplicate clustering correlates with higher expected return.
4. Permutation test generating `scheduler_bias_receipt.json`.

---

## 8. Required Evidence Artifacts
- `veto_attribution.parquet`
- `dedup_regret.json`
- `scheduler_bias_receipt.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not change live runtime priority ordering during this audit phase.
- Does not disable concurrency protections.

---

## 10. Guards
- [ ] Veto counterfactuals must be strictly sandboxed and never mutate live account balances.
- [ ] Scheduler bias tests must be fully deterministic and reproducible.

---

## 11. Normative Traceability
- **R1 — Veto Counterfactual Value:** Quantifies defensive efficiency of risk gates.  
  *Authority:* `REGRET_SYSTEM_SPEC.md` §3.4.
- **R2 — Dispatch Permutation Robustness:** Quantifies sensitivity to arbitrary hash tie-breaks.  
  *Authority:* `COMPUTE_SCHEDULING_SPEC.md` §6.2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::scheduler::BatchWorker`
- `v8-core::runloop::RunloopConfig`
- `v8-core::candidate::Candidate`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Gate Value Identity:** $\text{NetGateValue} = \sum \text{AvoidedLoss} - \sum \text{MissedProfit}$.
- **I2 — Tie-Break Stability:** $\Delta \text{PnL}_{\text{rename}} < \text{Threshold}$ under optimal ranker.

---

## 14. Canonical Failure Semantics
- Scheduler drift exceeds tolerance $\implies$ `Warn(SchedulerWarning::HashOrderSensitivity)`.

---

## 15. Dependency Map
```text
Dispatch Scheduler / Candidate Queue
                 │
                 ▼
       [Veto Value Tracker] ──► veto_attribution.parquet
                 │
                 ▼
     [Scheduler Bias Harness] ──► scheduler_bias_receipt.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If tie-breaking order causes $>5\%$ terminal equity variation on identical data, STOP and escalate OPEN_PIN.
