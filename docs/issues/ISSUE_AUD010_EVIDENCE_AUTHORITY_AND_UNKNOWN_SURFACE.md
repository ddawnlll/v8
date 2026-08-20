# [GOV] Issue #AUD-010: Epistemic, Authority & Certification Taxonomy Alignment (F22, F23)

**Status:** READY / AMENDED  
**Issue Type:** `GOVERNANCE`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:governance`, `triage`, `rust`, `P1`, `methodology`  
**Owning Authority:** `V8_CONSTITUTION.md` Rule 12 (`NO_ECONOMIC_CLAIM`), `TARGET_ORACLE_SPEC.md` §7, §16, `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, arXiv:2606.27570 (P036), arXiv:2607.20093 (P037).  
**Relationships:** Global governance taxonomy governing all audit reports and receipts.

---

## 1. Objective
Formalize and pin the 4 orthogonal epistemic and authority dimensions in `v8-core` (`VerificationDimension`, `EconomicEvidenceStage`, `CounterfactualAuthority`, `StatisticalVerdict`) to prevent parallel taxonomy invention, establish formal `UNKNOWN` reason-code surfaces, and ensure report badges strictly comply with Constitution Rule 12.

---

## 2. Owning Authority
- **Constitution:** [`docs/V8_CONSTITUTION.md`](docs/V8_CONSTITUTION.md) Rule 12 (`NO_ECONOMIC_CLAIM`).
- **Oracle Taxonomy:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §7 (Evidence Levels), §16 (Authority Hierarchy).
- **Evidence Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4.
- **Academic Literature:**
  - `P036` (arXiv:2606.27570): *Auditing AI Investment Recommendations as Executable Actions*.
  - `P037` (arXiv:2607.20093): *Retail Trader's Ruin: An Anatomy of Popular Signal Failure*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Reports headline "28 EXPERTS CERTIFIED", risking conflation between code contract compliance, empirical parity verification, and economic trading edge.
- Epistemic statuses must not be treated as set containment hierarchies (`Identified \subset PartialInterval ...`), but as mutually distinct categorical states across 4 orthogonal axes.

---

## 5. Required End State
1. **Four Orthogonal Taxonomy Axes:**
   - **Axis 1: `VerificationDimension`**
     - `CONTRACT_VERIFIED`: Satisfies unit test and type invariants.
     - `IMPLEMENTATION_PARITY`: Satisfies D-116 differential parity against independent reference engine.
     - `METAMORPHIC_INVARIANT`: Satisfies PIT temporal non-interference and permutation invariance.
   - **Axis 2: `EconomicEvidenceStage`**
     - `RECOVERABLE_WITHIN_CLASS`
     - `PROMOTABLE_WITHIN_CONTRACT`
     - `SHADOW_SUPPORTED`
     - `LIVE_SUPPORTED` (Default for unpromoted: `NO_ECONOMIC_CLAIM`).
   - **Axis 3: `CounterfactualAuthority`**
     - `IDENTIFIED`
     - `PARTIALLY_IDENTIFIED`
     - `MODEL_DERIVED`
     - `NOT_IDENTIFIABLE`
   - **Axis 4: `StatisticalVerdict`**
     - `SUPPORTED`
     - `REFUTED`
     - `INCONCLUSIVE_UNDERPOWERED`
2. **UNKNOWN Attribution Surface:**
   - Explicitly records reason-code distributions (`MISSING_DECISION_TIME_DATA`, `NON_IDENTIFIABLE_FILL`, `INSUFFICIENT_SUPPORT`, `MODEL_ONLY_COUNTERFACTUAL`).
   - Emits `authority_surface.parquet` and `unknown_reasons.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/authority_surface.rs
v8-core/src/oracle/taxonomy.rs
v8-core/src/report.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Report rendering test confirming that zero uncertified strategies display `ECONOMICALLY_SUPPORTED`.
3. Orthogonality test: verifying that the 4 taxonomy axes operate independently without conflation.
4. Schema validation for `authority_surface.parquet`.

---

## 8. Required Evidence Artifacts
- `authority_surface.parquet`
- `unknown_reasons.json`
- `power_materiality.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not invent parallel badge hierarchies outside the 4 pinned dimensions.

---

## 10. Guards
- [ ] Every audit report badge must declare which of the 4 orthogonal axes it represents.
- [ ] No uncertified expert may emit an economic edge claim under Rule 12.

---

## 11. Normative Traceability
- **R1 — Tripartite Authority Hierarchy:** Pins 4 orthogonal taxonomy axes.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §7, §16; `V8_CONSTITUTION.md` Rule 12.
- **R2 — Statistical Power Separation:** Separates underpowered tests from negative refutations.  
  *Authority:* arXiv:2607.20093 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::oracle::taxonomy::AuthorityLevel`
- `v8-core::oracle::taxonomy::Identifiability`
- `v8-core::evaluation::authority_surface`
- `v8-core::report`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Orthogonal Product Space:** $\text{AuditState} \in \text{VerificationDimension} \times \text{EconomicEvidenceStage} \times \text{CounterfactualAuthority} \times \text{StatisticalVerdict}$.

---

## 14. Canonical Failure Semantics
- Incomplete taxonomy specification $\implies$ `Err(AuthorityError::AmbiguousTaxonomyState)`.

---

## 15. Dependency Map
```text
[#178: Lineage DAG] + [#179: Independent Simulator]
                 │
                 ▼
     [Authority Surface Engine] ──► authority_surface.parquet / unknown_reasons.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If any report badge claims economic edge without certified WRC/DSR receipts, STOP and fail closed.
