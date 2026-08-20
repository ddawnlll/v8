# [IMPL] Issue #AUD-001: Oracle Independence & Anti-Tautology Negative Controls (F01)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `TARGET_ORACLE_SPEC.md` §5 (Opportunity Grammar), §17.5 (Coverage Reconciliation), §18.2 (Receipt Certification), arXiv:2604.15531 (P002), arXiv:2605.04004 (P010).  
**Relationships:** Depends on #178 (Population Lineage DAG).

---

## 1. Objective
Implement deterministic negative-control harnesses and metamorphic tests in pure Rust (`v8-core/src/oracle/independence.rs`) to empirically verify that the Opportunity Universe $U_v(t)$ is generated strictly independently of active Expert proposals, eliminating potential circularity/tautology where $N_{\text{opp}} = 27,881$ coincided with deduped candidate counts.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §5.1–5.8 (Opportunity Grammar & Independence), §17.5 (Reconciliation Integrity), §18.2 (Receipt Certification).
- **Truth Specification:** [`docs/contracts/SIMULATION_TRUTH_SPEC.md`](docs/contracts/SIMULATION_TRUTH_SPEC.md) §1–4.
- **Academic Literature:**
  - `P002` (arXiv:2604.15531): *Spurious Predictability in Financial Machine Learning* (Negative controls & workflow falsification).
  - `P010` (arXiv:2605.04004): *Structural Limits of OHLCV-Based Intraday Signals* (Signal falsification batteries).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- In current baseline runs, the audit report shows 42,647 setups with 14,766 dedup suppressions ($42,647 - 14,766 = 27,881$), while Target Oracle reports $N_{\text{opp}} = 27,881$ with 100% Proposal Coverage.
- While grammar mutation is intended to be independent, there is no formal metamorphic test verifying that removing or mutating Experts leaves $N_{\text{opp}}$ invariant, or that deliberately unrepresentable grammar patterns yield `representational_coverage < 1.0`.

---

## 5. Required End State
1. **Oracle Independence Verification Harness:**
   - Implement `OracleIndependenceReceipt` emitted to `oracle_independence_receipt.json`.
   - Implement `NegativeControlUniverse` outputted to `negative_control_universe.parquet`.
2. **Metamorphic Test Suite:**
   - **Test 1 (Population Invariance under Removal):** When any subset of active experts $E' \subset E$ is evaluated, $N_{\text{opp}}(U_v)$ remains bit-identical and strictly constant:
     $$N_{\text{opp}}(E') = N_{\text{opp}}(E)$$
   - **Test 2 (Unique-Contribution Coverage Drop):** Coverage drop upon removing an expert subset $E \setminus E'$ equals exactly the fraction of opportunities uniquely covered by that subset:
     $$\Delta \text{Coverage}(E \setminus E') = \frac{|\text{opportunities uniquely covered by } (E \setminus E')|}{|U_v|}$$
     *(Note: If removed experts only proposed redundant opportunities, coverage remains unchanged).*
   - **Test 3 (Synthetic Unrepresentable Grammar):** Inject synthetic grammar candidates disjoint from all active expert templates. Verify that `representational_coverage < 1.0` and `unrepresented_clusters` is correctly populated with cluster IDs.
   - **Test 4 (Permutation Independence):** Verify $U_v$ identity is invariant to the evaluation order of expert templates.

---

## 6. Expected File / Module Surface
```text
v8-core/src/oracle/mod.rs
v8-core/src/oracle/coverage.rs
v8-core/src/oracle/independence.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Unit tests confirming $N_{\text{opp}}$ invariance under arbitrary Expert subset removal.
3. Unit tests verifying unique-contribution coverage decrease formula.
4. Unit tests verifying synthetic gap detection with `representational_coverage < 1.0`.
5. Artifact generation: `oracle_independence_receipt.json` emitted with status `INDEPENDENCE_VERIFIED`.

---

## 8. Required Evidence Artifacts
- `oracle_independence_receipt.json`
- `negative_control_universe.parquet`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify expert trading logic or active signal rules.
- Does not alter raw market tape feeds.

---

## 10. Guards
- [ ] Opportunity Grammar population generation MUST execute without reading `ExpertEval` outputs.
- [ ] Coverage receipts MUST retain `claim: NO_ECONOMIC_CLAIM` under Rule 12.

---

## 11. Normative Traceability
- **R1 — Grammar Independence:** $U_v(t)$ is a pure function of $(I_t, \text{GrammarRegistry})$, strictly disjoint from $\text{Proposals}(E)$.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §5.1.
- **R2 — Negative Control Verification:** Emits verifiable receipts proving empirical non-circularity.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §17.5; arXiv:2604.15531 §3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::oracle::opportunity::GrammarCandidate`
- `v8-core::oracle::coverage::CoverageReceipt`
- `v8-core::oracle::taxonomy::OracleRefusal`
- `v8-core::oracle::artifacts::OpportunityUniverseVersion`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Invariance Invariant:** $\forall E' \subseteq E, \quad N_{\text{opp}}(U_v \mid E') \equiv N_{\text{opp}}(U_v \mid E)$.
- **I2 — Unique Coverage Invariant:** $\text{Coverage}(E) - \text{Coverage}(E') = \frac{|\{o \in U_v : \text{CoveredBy}(o, E) \land \neg\text{CoveredBy}(o, E')\}|}{|U_v|}$.
- **I3 — Gap Sensitivity:** $\exists g \in U_v \setminus \text{Proposals}(E) \implies \text{Coverage} < 1.0 \land |\text{UnrepresentedClusters}| > 0$.

---

## 14. Canonical Failure Semantics
- Circular dependency detected $\implies$ `Err(OracleRefusal::InvalidInformationState)`.

---

## 15. Dependency Map
```text
[#178: Population Lineage DAG]
              │
              ▼
Grammar Registry / Market Tape
              │
              ▼
    [Opportunity Universe] ──(Disjoint)──► [Expert Proposals]
              │                                    │
              └───────────────┬────────────────────┘
                              ▼
                  [Coverage Reconciliation] ──► oracle_independence_receipt.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If grammar candidate generation requires expert state reflection, STOP and escalate OPEN_PIN.
