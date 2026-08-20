# [IMPL] Issue #AUD-005A: O4 Isolated, Marginal & Interaction Regret Attribution (F20)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `risk`  
**Owning Authority:** `TARGET_ORACLE_SPEC.md` §11 (Regret Foundations), §19 (O4 Decomposition Architecture), arXiv:2606.29018 (P023), arXiv:2606.08791 (P024).  
**Relationships:** Depends on #178 (Lineage DAG), #180A.

---

## 1. Objective
Implement the authoritative, non-additive O4 Regret Attribution framework in pure Rust (`v8-core/src/analysis/regret_o4.rs`), calculating component effects (`Detection`, `Representation`, `Selection`, `Geometry`, `Execution`, `Allocation`) via the canonical 4-part structure (`ISOLATED_COMPONENT_EFFECT`, `MARGINAL_COMPONENT_EFFECT`, `INTERACTION_EFFECT`, `TOTAL_POLICY_GAP`) without forcing flawed additive identities.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §11.1–11.5 (Regret Foundations), §19 (O4 Isolated & Marginal Decomposition).
- **Regret System Specification:** [`docs/contracts/REGRET_SYSTEM_SPEC.md`](docs/contracts/REGRET_SYSTEM_SPEC.md) §1–6.
- **Academic Literature:**
  - `P023` (arXiv:2606.29018): *Liquidity-Based Audit of AI and Algorithmic Trading Strategies* (Cost vs impact regret).
  - `P024` (arXiv:2606.08791): *Evaluating AI Investment Strategies* (Dynamic regret decomposition).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Regret analysis currently lacks explicit isolated vs marginal effect separation across all six canonical domains: `Detection`, `Representation`, `Selection`, `Geometry`, `Execution`, `Allocation`.
- The rejected naive additive sum $R_{\text{total}} = \sum R_i$ is discarded in favor of the canonical v1 isolated/marginal/interaction model.

---

## 5. Required End State
1. **Canonical O4 Regret Partitioning:**
   - For each canonical domain $d \in \{\text{Detection}, \text{Representation}, \text{Selection}, \text{Geometry}, \text{Execution}, \text{Allocation}\}$:
     - Compute $\text{IsolatedEffect}(d) = U(S \setminus \{d\}) - U(S)$.
     - Compute $\text{MarginalEffect}(d) = U(S) - U(\{d\})$.
   - Compute $\text{TotalPolicyGap} = V^*(S_t) - U(\pi_{\text{realized}})$.
   - Compute $\text{InteractionEffect} = \text{TotalPolicyGap} - \sum \text{IsolatedEffects}$.
2. **Artifact Generation:**
   - Emits `o4_regret_decomposition.parquet` and `regret_assumption_ledger.json`.

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
2. Canonical domain coverage: all 6 domains evaluated without omissions.
3. Isolated, marginal, and interaction matrices verified on synthetic and historical trade traces.

---

## 8. Required Evidence Artifacts
- `o4_regret_decomposition.parquet`
- `regret_assumption_ledger.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not enforce simple additive sums (explicitly rejected by TARGET §11).
- Does not implement Shapley/path-specific causal decompositions (deferred to v1.1+).

---

## 10. Guards
- [ ] Assumptions governing interaction separability must be written to `regret_assumption_ledger.json`.
- [ ] Total policy gap must equal the difference between Oracle ceiling $V^*$ and realized net utility.

---

## 11. Normative Traceability
- **R1 — O4 Isolated & Marginal Attribution:** Implements canonical 4-component regret structure.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §11, §19; arXiv:2606.08791 §3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::analysis::outcome::OutcomeClass`
- `v8-core::oracle::authority::OracleOutcome`
- `v8-core::regret::Action`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Total Policy Gap:** $\text{Gap}_{\text{total}} = V^*(S_t) - U(\pi_{\text{realized}})$.
- **I2 — Interaction Identity:** $\mathcal{I} = \text{Gap}_{\text{total}} - \sum_{d} \text{Isolated}(d)$.

---

## 14. Canonical Failure Semantics
- Incomplete component attribution $\implies$ `Err(RegretError::IncompleteDomainDecomposition)`.

---

## 15. Dependency Map
```text
[#178: Lineage DAG] + [#180A: PIT Non-Interference]
                 │
                 ▼
       [O4 Regret Engine] ──► o4_regret_decomposition.parquet / regret_assumption_ledger.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If interaction effects exceed total policy gap by $>200\%$, record `HIGH_INTERACTION_REGRET` and escalate OPEN_PIN.
