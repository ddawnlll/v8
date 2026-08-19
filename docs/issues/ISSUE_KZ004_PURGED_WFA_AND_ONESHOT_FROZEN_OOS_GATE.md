# [IMPL] Issue #KZ-004: Purged WFA & Atomic One-Shot Frozen OOS Gate

**Status:** READY / PATCHED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `risk:validation-integrity`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §5, `HYPOTHESIS_LAB_PROTOCOL.md` §1–4, `V8_CONSTITUTION.md` Rule 5, 11, `EVALUATION_EVIDENCE_SYSTEM.md` §3, arXiv:2602.10785.

---

## 1. Objective
Implement Purged Walk-Forward Analysis (`WfaSpec`, `WfaFoldReceipt`, `WfaCampaignVerdict`) with paired baseline improvement tracking and catastrophic drawdown vetoes, combined with an atomic dataset-level One-Shot Holdout Burning State Machine (`HoldoutAccessKey`, `HoldoutState`, `HoldoutBurnRegistry`) in pure Rust, ensuring that the V8 evaluator fail-closed rejects any secondary access to frozen out-of-sample data.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §5 (Purged WFA & Atomic One-Shot Frozen OOS Burn).
- **Hypothesis Protocol Authority:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](file:///Users/hootie/src/v8/docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §3–4 (Paired OOS delta vs simpler incumbent baseline).
- **Constitution:** [`docs/charter/V8_CONSTITUTION.md`](file:///Users/hootie/src/v8/docs/charter/V8_CONSTITUTION.md) Rule 5, 11, 15.
- **Validation Geometry Literature:** arXiv:2602.10785 (*Walk-Forward Optimization Window Selection, Trial Accounting, and Out-of-Sample Reliability*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` lacks an automated purged multi-fold WFA campaign harness measuring paired improvement against a fixed baseline with catastrophic veto logic.
- Naive holdout registry designs indexed burns by `(experiment_id, dataset_hash)`, which allowed trivial bypasses (generating a new `experiment_id` to re-query the same holdout).
- Previous designs attempted to burn holdouts *after* evaluation, risking leaked data access if a process crashed mid-run.

---

## 5. Required End State
1. **Paired-Delta Purged WFA:**
   `WfaFoldReceipt` capturing:
   - `fold_id`, `train_range`, `purge_range`, `test_range`, `chosen_variant`
   - `baseline_utility`, `challenger_utility`
   - `paired_delta` ($U_{\text{challenger}} - U_{\text{baseline}}$)
   - `paired_uncertainty` (clustered standard error / bootstrap interval)
   - `max_drawdown_r`, `cost_drag_r`, `verdict` (`FoldVerdict::Pass | FailNegativeDelta | FailCatastrophicDrawdown`).
2. **Majority Pass with Catastrophic Veto:**
   `WfaCampaignVerdict` requires majority fold paired-delta success, but fails closed immediately (`FailCatastrophicVeto`) if any fold breaches the maximum allowable drawdown ceiling.
3. **Atomic Reserve-Before-Access Holdout State Machine:**
   ```rust
   pub enum HoldoutState {
       Untouched,
       ReservedAndBurned,
       Completed,
       FailedAfterBurn,
   }

   pub struct HoldoutAccessKey {
       pub holdout_id: String,
       pub dataset_hash: String,
       pub research_lineage_id: String,
   }
   ```
   **Access Ordering Invariant:**
   $$\text{Atomic State Transition: } \text{Untouched} \longrightarrow \text{ReservedAndBurned} \longrightarrow \text{Release OOS Bytes} \longrightarrow \text{Evaluation} \longrightarrow \text{Completed}$$
   If evaluation fails or aborts, state transitions to `FailedAfterBurn`. Re-opening any holdout with state $\neq \text{Untouched}$ is fail-closed rejected with `Err(HoldoutError::AlreadyBurned)`.
4. **Validation Geometry Trial Accounting:**
   Combinations of train/test windows (e.g. 90/30 vs 180/30) are registered into the global trial debt ledger (arXiv:2602.10785).
5. **Evaluator Authority Boundary:**
   The V8-authorized evaluation harness enforces fail-closed rejection of secondary access across the entire repository.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/validation.rs (or experiment.rs)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying paired-delta WFA: challenger must beat baseline net utility in majority of folds.
3. Test verifying catastrophic veto: a single fold drawdown violation overrides a 4/5 pass rate.
4. Test verifying atomic holdout burn: once reserved, attempting to access the dataset under any `experiment_id` or lineage returns `HoldoutError::AlreadyBurned`.
5. Test verifying crash resilience: a holdout in `FailedAfterBurn` state cannot be re-opened.
6. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test logs validating catastrophic veto, paired-delta calculation, and atomic holdout burn.
- Serialized `HoldoutBurnReceipt` schema verification.

---

## 9. Non-Goals / Forbidden Scope
- Does not allow repairing a rejected hypothesis on frozen OOS.
- Does not claim physical OS-level file deletion (protection is enforced via V8 evaluator fail-closed authority).

---

## 10. Guards
- [ ] Holdouts must transition to `ReservedAndBurned` BEFORE data bytes are released.
- [ ] Burn semantics are keyed to the physical dataset hash, preventing bypass via new experiment IDs.
- [ ] WFA verdicts must evaluate paired improvement against the incumbent baseline.

---

## 11. Normative Traceability
- **R1 — Paired Purged WFA Engine:** Computes paired-delta against fixed baseline across purged folds.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §5.1; `HYPOTHESIS_LAB_PROTOCOL.md` §3–4.
- **R2 — Catastrophic Veto Rule:** Vetos strategies with catastrophic drawdown in any individual fold.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §5.1; arXiv:2603.09219.
- **R3 — Atomic Dataset-Level Holdout Burn:** Irreversibly burns dataset access upon reservation.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §5.2; `V8_CONSTITUTION.md` Rule 5, 11, 15.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::experiment::ExperimentManifest`
- `v8-core::data::TimeRange`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Paired Advantage:** $\text{FoldPass} \iff \Delta U_{\text{paired}} > 0 \land \text{MaxDD} \le \text{MaxDD}_{\text{allowable}}$.
- **I2 — Atomic Burn:** $\text{State}(D) \neq \text{Untouched} \implies \text{Access}(D) = \text{Err}(\text{AlreadyBurned})$.

---

## 14. Canonical Failure Semantics
- Re-query of burned holdout $\implies$ `Err(HoldoutError::AlreadyBurned)`.
- WFA Catastrophic breach $\implies$ `WfaCampaignVerdict::FailCatastrophicVeto`.

---

## 15. Dependency Map
```text
[KZ-003: Robustness Surface]
             │
             ▼
[KZ-004: Purged WFA & Atomic OOS Burn]
             │
             ▼
[Registry Promotion Decision]
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If holdout burn state persistence requires a distributed locking mechanism, open `OPEN_PIN`.
