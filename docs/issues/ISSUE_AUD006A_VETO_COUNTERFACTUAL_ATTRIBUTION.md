# [IMPL] Issue #AUD-006A: Veto Counterfactual Attribution with Epistemic Authority Tags (F19, F27)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `risk`  
**Owning Authority:** `REGRET_SYSTEM_SPEC.md` §3–5 (Admission Veto Regret), `TARGET_ORACLE_SPEC.md` §7, §16, arXiv:2608.08405 (P026), arXiv:2606.29018 (P023).  
**Relationships:** Depends on #178 (Lineage DAG).

---

## 1. Objective
Implement counterfactual economic attribution for runtime candidate admission vetoes (`EXISTING_EXPOSURE_CONFLICT`, `PORTFOLIO_HEAT_EXCEEDED`) and deduplication suppressions at the `Candidate` entity level in pure Rust (`v8-core/src/analysis/veto_attribution.rs`), tagging every counterfactual outcome with its rigorous `CounterfactualAuthority` status (`IDENTIFIED`, `PARTIALLY_IDENTIFIED`, `MODEL_DERIVED`, `NOT_IDENTIFIABLE`).

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/REGRET_SYSTEM_SPEC.md`](docs/contracts/REGRET_SYSTEM_SPEC.md) §3–5 (Veto Regret & Counterfactual Valuation).
- **Oracle Taxonomy:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §7, §16 (Epistemic Authority Hierarchy).
- **Academic Literature:**
  - `P026` (arXiv:2608.08405): *Robustness or Crowding: Experimental Design for Trading Strategy Capacity*.
  - `P023` (arXiv:2606.29018): *Liquidity-Based Audit of AI and Algorithmic Trading Strategies*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Admission vetoes currently suppress candidates without recording counterfactual paths, making it impossible to audit whether risk gates protected capital (`avoided_loss`) or blocked valid alpha (`missed_profit`).
- Counterfactual calculations must not assume exact, identified truth where market feedback or intrabar paths make the outcome partially identified or model-derived.

---

## 5. Required End State
1. **Candidate-Level Veto Attribution:**
   - For every rejected `Candidate`:
     - Record: `candidate_id`, `expert_id`, `veto_reason`, `avoided_loss_usdt`, `missed_profit_usdt`, `net_gate_value_usdt`.
     - Explicitly tag: `authority_status`: `IDENTIFIED | PARTIALLY_IDENTIFIED | MODEL_DERIVED | NOT_IDENTIFIABLE`.
   - Emits `veto_attribution.parquet`.
2. **Dedup Suppression Regret Audit:**
   - Compare 14,766 suppressed duplicate candidates against admitted parent candidates to evaluate if signal redundancy carried higher win rates.
   - Emits `dedup_regret.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/analysis/mod.rs
v8-core/src/analysis/veto_attribution.rs
v8-core/src/runloop.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Authority tag coverage: 100% of counterfactual rows carry a valid `CounterfactualAuthority` label.
3. Balance isolation: counterfactual tracking never mutates active simulation account balances.

---

## 8. Required Evidence Artifacts
- `veto_attribution.parquet`
- `dedup_regret.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not disable concurrency gates in production execution.

---

## 10. Guards
- [ ] Vetoed entities must be referenced as `Candidate`, never `Trade`.
- [ ] Model-derived counterfactuals must not be labeled as `IDENTIFIED`.

---

## 11. Normative Traceability
- **R1 — Veto Counterfactual Valuation:** Calculates defensive efficiency with epistemic authority tagging.  
  *Authority:* `REGRET_SYSTEM_SPEC.md` §3.4; `TARGET_ORACLE_SPEC.md` §16.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::candidate::Candidate`
- `v8-core::oracle::taxonomy::Identifiability`
- `v8-core::cashflow::EconomicCashflow`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Gate Net Value:** $\text{NetGateValue} = \sum \text{AvoidedLoss} - \sum \text{MissedProfit}$.

---

## 14. Canonical Failure Semantics
- Ambiguous counterfactual authority $\implies$ `Record(AuthorityStatus::NotIdentifiable)`.

---

## 15. Dependency Map
```text
Candidate Queue / Risk Gates
              │
              ▼
    [Veto Tracker Engine] ──► veto_attribution.parquet / dedup_regret.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If intrabar trajectory ambiguity prevents exact counterfactual bounding, assign `PARTIALLY_IDENTIFIED` bounds and proceed.
