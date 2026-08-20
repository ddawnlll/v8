# [IMPL] Issue #AUD-010: Evidence Authority, UNKNOWN Surface & Epistemic Honesty (F22, F23)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `methodology`  
**Owning Authority:** `V8_CONSTITUTION.md` Rule 12, `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, arXiv:2606.27570 (P036), arXiv:2607.20093 (P037).

---

## 1. Objective
Implement epistemic authority partitioning, formal `UNKNOWN` reason-code attribution surfaces, and statistical power / minimum detectable edge dashboards in pure Rust (`v8-core/src/evaluation/authority_surface.rs`), replacing ambiguous "28 EXPERTS CERTIFIED" claims with precise tripartite verification (`CONTRACT_CERTIFIED` vs `IMPLEMENTATION_VERIFIED` vs `ECONOMICALLY_SUPPORTED`).

---

## 2. Owning Authority
- **Constitution:** [`docs/V8_CONSTITUTION.md`](docs/V8_CONSTITUTION.md) Rule 12 (`NO_ECONOMIC_CLAIM`).
- **Evidence Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4.
- **Academic Literature:**
  - `P036` (arXiv:2606.27570): *Auditing AI Investment Recommendations as Executable Actions* (Executability vs economic outcome).
  - `P037` (arXiv:2607.20093): *Retail Trader's Ruin: An Anatomy of Popular Signal Failure* (Power & minimum detectable edge).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Reports headline "28 EXPERTS CERTIFIED", which risks conflating syntax/contract validation with economic profitability.
- Unsupported counterfactuals or ambiguous intrabar fills are sometimes outputted as zeros or silent drops rather than explicitly surfacing `UNKNOWN` / `MODEL_DERIVED` status.
- Null statistical results are not explicitly separated into `REFUTED` vs `INCONCLUSIVE_BECAUSE_UNDERPOWERED`.

---

## 5. Required End State
1. **Tripartite Certification Hierarchy:**
   - Explicit separation in reports and CLI receipts:
     - `CONTRACT_CERTIFIED`: Code satisfies interfaces, types, and mathematical invariants.
     - `IMPLEMENTATION_VERIFIED`: Passes differential parity and metamorphic tests.
     - `ECONOMICALLY_SUPPORTED`: Certified by multiplicity adjustments (WRC/DSR) and positive OOS return (default: `NO_ECONOMIC_CLAIM`).
2. **UNKNOWN Reason-Code Surface:**
   - Record distribution of `MISSING_DECISION_TIME_DATA`, `NON_IDENTIFIABLE_FILL`, `INSUFFICIENT_SUPPORT`, `MODEL_ONLY_COUNTERFACTUAL`.
   - Emits `authority_surface.parquet` and `unknown_reasons.json`.
3. **Statistical Power & Materiality Dashboard:**
   - Separates `SUPPORTED`, `REFUTED`, and `UNDERPOWERED` verdicts.
   - Emits `power_materiality.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/mod.rs
v8-core/src/evaluation/authority_surface.rs
v8-core/src/report.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Report rendering test confirming that zero uncertified strategies display `ECONOMICALLY_SUPPORTED`.
3. UNKNOWN classification test verifying that unresolvable intrabar actions emit explicit reason codes.
4. Schema validation for `authority_surface.parquet`.

---

## 8. Required Evidence Artifacts
- `authority_surface.parquet`
- `unknown_reasons.json`
- `power_materiality.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not weaken multiple-testing significance thresholds.
- Does not emit economic edge claims without full WRC/DSR receipts.

---

## 10. Guards
- [ ] Epistemic labels must strictly comply with Constitution Rule 12.
- [ ] No unobserved or synthetic counterfactual may be labeled as `IDENTIFIED_FACT`.

---

## 11. Normative Traceability
- **R1 — Epistemic Honesty:** Explicit tripartite certification levels in all artifacts.  
  *Authority:* `V8_CONSTITUTION.md` Rule 12; arXiv:2606.27570 §3.
- **R2 — Power & Materiality Distinction:** Separates underpowered tests from negative refutations.  
  *Authority:* arXiv:2607.20093 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::oracle::taxonomy::AuthorityLevel`
- `v8-core::oracle::taxonomy::Identifiability`
- `v8-core::evaluation::html_report::HtmlReport`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Authority Hierarchy:** $\text{Identified} \subset \text{PartialInterval} \subset \text{ModelDerived} \subset \text{Unknown}$.
- **I2 — Power Equivalence:** $\text{Verdict} \in \{\text{Supported}, \text{Refuted}, \text{Underpowered}\}$.

---

## 14. Canonical Failure Semantics
- Ambiguous claim emitted $\implies$ `Err(AuthorityError::EpistemicViolation)`.

---

## 15. Dependency Map
```text
Evaluation Results + Oracle Authority
                 │
                 ▼
    [Authority Surface Engine] ──► authority_surface.parquet
                 │
                 ▼
    [Power & Materiality Audit] ──► power_materiality.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If any report badge displays "Certified" without qualifying the certification tier, STOP and open OPEN_PIN.
