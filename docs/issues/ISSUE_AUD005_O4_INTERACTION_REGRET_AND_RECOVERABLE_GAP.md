# [IMPL] Issue #AUD-005: O4 Interaction-Aware Regret & Recoverable-vs-Hindsight Gap (F20)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `risk`  
**Owning Authority:** `TARGET_ORACLE_SPEC.md` §16, §19, `REGRET_SYSTEM_SPEC.md` §1–6, arXiv:2606.29018 (P023), arXiv:2606.08791 (P024).

---

## 1. Objective
Implement interaction-aware, non-additive O4 Regret decomposition (`Structural`, `Detection`, `Selection`, `Execution`, `Allocation`, `Policy`) and the 4-stage Recoverable-vs-Hindsight Opportunity Waterfall (`HindsightOpportunity → PITRecoverable → Selectable → Promotable`) in pure Rust (`v8-core/src/analysis/regret_o4.rs`), ensuring theoretical hindsight profits ($+490R$) are properly partitioned into realistically actionable edge vs unreachable oracle artifacts.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §16 (Regret Ontology), §19 (O4 Decomposition).
- **Regret Specification:** [`docs/contracts/REGRET_SYSTEM_SPEC.md`](docs/contracts/REGRET_SYSTEM_SPEC.md) §1–6.
- **Academic Literature:**
  - `P023` (arXiv:2606.29018): *Liquidity-Based Audit of AI and Algorithmic Trading Strategies* (Cost vs impact regret).
  - `P024` (arXiv:2606.08791): *Evaluating AI Investment Strategies* (Dynamic regret decomposition).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Regret analysis currently computes isolated scalar differences between oracle ceilings and candidate outcomes.
- Regret is treated as approximately additive, ignoring covariance and interaction terms between execution slippage, portfolio heat allocation vetoes, and sizing quantization.
- No formal waterfall filters hindsight theoretical gains by point-in-time recoverability.

---

## 5. Required End State
1. **Interaction-Aware O4 Regret Decomposition:**
   - Decomposes total regret $\mathcal{R}_{\text{total}} = \mathcal{R}_{\text{structural}} + \mathcal{R}_{\text{detection}} + \mathcal{R}_{\text{selection}} + \mathcal{R}_{\text{execution}} + \mathcal{R}_{\text{allocation}} + \mathcal{I}_{\text{interaction}}$.
   - Emits `o4_regret_decomposition.parquet` and `regret_assumption_ledger.json`.
2. **Actionable Recoverability Waterfall:**
   - Stages:
     1. $\text{HindsightOpportunity}$: Absolute global upper bound $V^*(S_t)$.
     2. $\text{PITRecoverable}$: Upper bound given strictly causal, point-in-time available information.
     3. $\text{Selectable}$: Opportunities admissible under venue execution rules and capital constraints.
     4. $\text{Promotable}$: Opportunities passing multiplicity and multiple-testing gates.
   - Emits `recoverable_gap_waterfall.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/analysis/mod.rs
v8-core/src/analysis/regret_o4.rs
v8-core/src/oracle/utility.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Exact mathematical identity check: $\sum \mathcal{R}_i + \mathcal{I} \equiv V^* - \text{RealizedPnL}$.
3. Waterfall monotonicity check: $\text{Promotable} \le \text{Selectable} \le \text{PITRecoverable} \le \text{HindsightOpportunity}$.

---

## 8. Required Evidence Artifacts
- `o4_regret_decomposition.parquet`
- `regret_assumption_ledger.json`
- `recoverable_gap_waterfall.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not claim unreachable hindsight profit as realizable trading edge.
- Does not modify existing regret phase 1–3 legacy parity tables.

---

## 10. Guards
- [ ] Regret identities must explicitly state assumptions and error terms under non-stationarity.
- [ ] The waterfall must never allow Promotable > PITRecoverable.

---

## 11. Normative Traceability
- **R1 — O4 Regret Partitioning:** Implements non-separable interaction-aware regret matrix.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §16; arXiv:2606.08791 §3.
- **R2 — Recoverability Waterfall:** Explicit separation of hindsight artifacts from actionable alpha.  
  *Authority:* `REGRET_SYSTEM_SPEC.md` §4.2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::analysis::outcome::OutcomeClass`
- `v8-core::oracle::authority::OracleOutcome`
- `v8-core::regret::Action`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Total Regret Identity:** $\mathcal{R}_{\text{total}} = V^*(S_t) - U(\pi_{\text{realized}})$.
- **I2 — Monotonic Waterfall:** $\text{Vol}(\text{Promotable}) \subseteq \text{Vol}(\text{Selectable}) \subseteq \text{Vol}(\text{PITRecoverable})$.

---

## 14. Canonical Failure Semantics
- Regret residual non-zero $\implies$ `Err(RegretError::DecompositionInconsistency)`.

---

## 15. Dependency Map
```text
Target Oracle (V*) + Realized Execution
                   │
                   ▼
         [O4 Regret Engine] ──► o4_regret_decomposition.parquet
                   │
                   ▼
       [Recoverability Waterfall] ──► recoverable_gap_waterfall.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If interaction term formulation diverges from covariance-penalty models, STOP and open OPEN_PIN.
