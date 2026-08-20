# [IMPL] Issue #AUD-004B: Complete Research Search Lineage & Multiplicity Ledger (F06)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `TARGET_ORACLE_SPEC.md` §14.1 (Research Choices & Family Boundaries), `HYPOTHESIS_LAB_PROTOCOL.md` §1–4, arXiv:1905.05023 (P003), arXiv:2512.12924 (P011).  
**Relationships:** Depends on #178 (Lineage DAG), #180A.

---

## 1. Objective
Implement complete research search-lineage tracking in pure Rust (`v8-core/src/kaizen/research_debt.rs`, `search_ledger.rs`), ensuring that all tried grammar variants, parameter permutations, objective adjustments, and pruned/discarded challenger candidates are permanently retained for uncompromised Multiple-Testing, PBO, and DSR calculations.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §14.1 (Explicit Research Choice Tracking).
- **Hypothesis Protocol:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §1–4 (Search-Family Completeness).
- **Academic Literature:**
  - `P003` (arXiv:1905.05023): *Avoiding Backtesting Overfitting by Covariance-Penalties* (PBO & selection bias).
  - `P011` (arXiv:2512.12924): *Interpretable Hypothesis-Driven Trading* (Search-family accounting).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core/src/kaizen/research_debt.rs` tracks dual-counter trial ledgers, but does not yet record full parameter grid configurations for pruned and early-stopped variants.
- Without a complete-family ledger, Probability of Backtest Overfitting (PBO) and Deflated Sharpe Ratio (DSR) understate the true trial debt.

---

## 5. Required End State
1. **Complete Family Ledger:**
   - Every candidate exploration records: `research_choice_id`, `family_id`, `parameter_payload`, `evaluation_status` (`SURVIVED | PRUNED | FALSIFIED`), `performance_summary`.
   - Emits `research_family_ledger.jsonl`.
2. **Multiple-Testing Multiplicity Summary:**
   - Computes total trials, effective search family dimensions, and family covariance matrices.
   - Emits `multiple_testing.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/mod.rs
v8-core/src/kaizen/research_debt.rs
v8-core/src/evaluation/multiple_testing.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Ledger completeness check: $N_{\text{ledger}} \equiv N_{\text{survived}} + N_{\text{discarded}}$.
3. PBO calculation verification against full ledger vs pruned subset.

---

## 8. Required Evidence Artifacts
- `research_family_ledger.jsonl`
- `multiple_testing.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify parameter search ranges during production validation.

---

## 10. Guards
- [ ] No evaluated parameter variation may be deleted or omitted from the ledger.
- [ ] Multiplicity corrections must use full family size $N_{\text{ledger}}$.

---

## 11. Normative Traceability
- **R1 — Search Family Completeness:** Preserves complete history of search choices.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §14.1; arXiv:1905.05023 §3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::kaizen::research_debt::GlobalTrialLedger`
- `v8-core::kaizen::challenger::ChallengerVariant`
- `v8-core::statistics::Multiplicity`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Conservation of Trials:** $N_{\text{total\_trials}} = N_{\text{admitted}} + N_{\text{rejected\_pruned}}$.

---

## 14. Canonical Failure Semantics
- Incomplete trial accounting $\implies$ `Err(MultiplicityError::UnaccountedTrialDebt)`.

---

## 15. Dependency Map
```text
Challenger Engine / Sweep Engine
               │
               ▼
   [Research Family Ledger] ──► research_family_ledger.jsonl
               │
               ▼
   [Multiplicity Engine] ──► multiple_testing.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If parameter ranges change dynamically during evaluation without generating a new `family_id`, STOP and open OPEN_PIN.
