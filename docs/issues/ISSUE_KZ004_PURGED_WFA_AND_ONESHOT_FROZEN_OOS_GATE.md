# [IMPL] Issue #KZ-004: Purged WFA & One-Shot Frozen OOS Gate

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `risk:validation-integrity`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §5, `V8_CONSTITUTION.md` Rule 5, 11, `EVALUATION_EVIDENCE_SYSTEM.md` §3, arXiv:2602.10785.

---

## 1. Objective
Implement Purged Walk-Forward Analysis (`WfaSpec`, `WfaFoldReceipt`, `WfaCampaignVerdict`) with majority pass requirements and catastrophic drawdown vetoes, paired with a cryptographic One-Shot Holdout Burning Registry (`HoldoutBurnReceipt`, `HoldoutBurnRegistry`) in pure Rust, ensuring OOS data can never be re-used or curve-fitted.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §5 (Purged WFA & One-Shot Frozen OOS Burn).
- **Constitution:** [`docs/charter/V8_CONSTITUTION.md`](file:///Users/hootie/src/v8/docs/charter/V8_CONSTITUTION.md) Rule 5 (`Frozen out-of-sample comparison`), Rule 11 (`Multiplicity controls and untouched chronological evaluation`).
- **Validation Geometry Literature:** arXiv:2602.10785 (*Walk-Forward Optimization Window Selection and Out-of-Sample Reliability*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` supports chronological evaluation, but lacks an automated purged multi-fold WFA campaign harness with explicit fold receipts and catastrophic veto enforcement.
- Frozen out-of-sample datasets are protected by convention, but lack an enforceable cryptographic hardware/software burn registry that mechanically raises an error if an agent attempts to re-evaluate the same OOS hash.

---

## 5. Required End State
1. **Purged WFA Engine:**
   `WfaSpec` supporting parameterized `train_bars`, `purge_bars`, `test_bars`, `step_bars`, `min_pass_fraction`, and `max_allowable_fold_drawdown_r`.
2. **Majority Pass with Catastrophic Veto:**
   `WfaCampaignVerdict` requiring majority fold success, but failing immediately (`FailCatastrophicVeto`) if any individual fold suffers a catastrophic drawdown breach.
3. **Validation Geometry Trial Accounting:**
   Window combinations (e.g. 90/30 vs 180/30) logged as formal research choices into the trial debt ledger.
4. **Cryptographic Holdout Burn Registry:**
   `HoldoutBurnRegistry` recording `HoldoutBurnReceipt` upon evaluation. Attempting to evaluate the same `(experiment_id, dataset_hash)` twice returns `Err(HoldoutError::AlreadyBurned)`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/validation.rs (or experiment.rs)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying that a single catastrophic drawdown fold overrides a 4/5 pass rate, failing the WFA campaign.
3. Test verifying that re-registering an already-evaluated `(experiment_id, dataset_hash)` raises `HoldoutError::AlreadyBurned`.
4. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test logs validating catastrophic veto and holdout burn failure paths.
- Sample serialized `HoldoutBurnReceipt`.

---

## 9. Non-Goals / Forbidden Scope
- Does not allow repairing a rejected hypothesis on frozen OOS.
- Does not modify historical baseline datasets.

---

## 10. Guards
- [ ] Holdouts must be burned irreversibly upon evaluation.
- [ ] Catastrophic drawdown in any fold must veto the entire WFA campaign.
- [ ] No lookahead leakage between train and test windows (purge interval enforced).

---

## 11. Normative Traceability
- **R1 — Chronological Purged Folds:** Executes walk-forward intervals with leakage-safe purge buffers.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §5.1; `V8_CONSTITUTION.md` Rule 5.
- **R2 — Catastrophic Veto Invariant:** Vetos any strategy exhibiting tail drawdown collapse in any single fold.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §5.1; arXiv:2603.09219.
- **R3 — One-Shot Holdout Burning:** Mechanically prohibits holdout re-use.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §5.2; `V8_CONSTITUTION.md` Rule 11, 15.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::experiment::ExperimentManifest`
- `v8-core::data::TimeRange`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Purge Separation:** $\text{End}(\text{Train}) + \text{PurgeBars} \le \text{Start}(\text{Test})$.
- **I2 — Catastrophic Veto:** $\exists f \in \text{Folds} \text{ s.t. } \text{Drawdown}(f) > \text{MaxDD}_{\text{allowable}} \implies \text{Campaign Verdict} = \text{FAIL}$.
- **I3 — Irreversible Burn:** $\text{Eval}(E, D_{\text{OOS}}) \implies \text{Burned}(E, D_{\text{OOS}}) = \text{true}$; subsequent calls return `AlreadyBurned`.

---

## 14. Canonical Failure Semantics
- Holdout re-query $\implies$ `Err(HoldoutError::AlreadyBurned)`.
- WFA Catastrophic breach $\implies$ `WfaCampaignVerdict::FailCatastrophicVeto`.

---

## 15. Dependency Map
```text
[KZ-003: Robustness Surface]
             │
             ▼
[KZ-004: Purged WFA & One-Shot OOS Burn]
             │
             ▼
[Registry Promotion Decision]
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If OOS hash verification cannot be performed deterministically on disk, open `OPEN_PIN`.
