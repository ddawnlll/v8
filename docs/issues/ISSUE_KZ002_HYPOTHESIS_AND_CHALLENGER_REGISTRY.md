# [IMPL] Issue #KZ-002: Hypothesis & Challenger Registry

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `risk:hypothesis-governance`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §3, `HYPOTHESIS_LAB_PROTOCOL.md` §1–4, `LEARNING_PROTOCOL.md` §1–4, arXiv:2606.01650.

---

## 1. Objective
Implement the immutable Hypothesis and Challenger Registry (`ResearchFinding`, `HypothesisRecord`, `ChallengerFamilySpec`, `FindingGenerator`, `HypothesisGenerator`, `GlobalTrialLedger`) in pure Rust, enforcing the strict invariant $\text{OBSERVATION} \neq \text{CHANGE}, \text{OBSERVATION} \longrightarrow \text{HYPOTHESIS}$ and tracking lifetime research trial debt.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §3 (Hypothesis & Challenger Registry).
- **Hypothesis Protocol:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](file:///Users/hootie/src/v8/docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §1–4.
- **Multiple Testing / Post-Selection Sharpe:** arXiv:2606.01650 (*Post-Selection Inference and Overfitting Penalties in Quantitative Strategy Search*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Research findings and retrospective observations currently lack a typed, machine-verifiable contract that prevents direct strategy mutation.
- When an engineer or agent evaluates an idea, trial counts are not globally incremented, risking unpenalized multiple-testing inflation (Bailey PBO failure).
- Challenger parameter families are not formally bounded before experimentation starts.

---

## 5. Required End State
1. **Finding & Hypothesis Types:**
   `ResearchFinding` and `HypothesisRecord` capturing parent run/expert lineage, failure class, target metrics, falsification rules, and parameter search bounds.
2. **Type-System Invariant Boundary:**
   `FindingGenerator` and `HypothesisGenerator` traits whose return types are strictly isolated from the live decision plane (cannot write to active expert states).
3. **Global Trial Accounting:**
   `GlobalTrialLedger` recording every evaluated candidate variant to maintain an accurate denominator for Deflated Sharpe Ratio (DSR) and White's Reality Check (WRC).

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/hypothesis.rs
v8-core/src/kaizen/challenger.rs
v8-core/src/kaizen/research_debt.rs (or registry.rs)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying that a finding compiled from a `CostDominated` failure generates a hypothesis proposing volatility/churn gating with discrete parameter candidates.
3. Test verifying that trial debt monotonically increases by the total count of evaluated candidates ($N_{\text{trials}} \mathrel{+}= |\text{Candidates}|$).
4. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test verification logs.
- Serialized `HypothesisRecord` JSON representation matching `v8.kaizen.engine.v1`.

---

## 9. Non-Goals / Forbidden Scope
- Does not automatically promote or activate challengers into the live execution plane.
- Does not run continuous or online weight updates.

---

## 10. Guards
- [ ] Active strategy state cannot be mutated by findings or hypotheses.
- [ ] Search grids must be finite and discrete (no unbounded continuous exploration without trial accounting).
- [ ] Every evaluated variant increments the trial debt ledger.

---

## 11. Normative Traceability
- **R1 — Immutable Hypothesis Records:** Compiles findings into schema-validated, immutable `HypothesisRecord` structs.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §3.1; `HYPOTHESIS_LAB_PROTOCOL.md` §2.
- **R2 — Falsification Rules:** Every hypothesis must carry an explicit, measurable falsification rule.  
  *Authority:* `V8_CONSTITUTION.md` Rule 1, 5; `KAIZEN_ENGINE_SPEC.md` §3.1.
- **R3 — Lifetime Trial Accounting:** Maintains global trial debt across all exploratory evaluations.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §3.2; `EVALUATION_EVIDENCE_SYSTEM.md` §2; arXiv:2606.01650.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::kaizen::forensics::{ExpertId, VariantId, FailureClass}`
- `v8-core::statistics::Multiplicity`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Observation != Change:** Finding $\to$ Hypothesis Proposal $\to$ Challenger Specification $\mathrel{\not\to}$ Live State Mutation.
- **I2 — Monotonic Trial Debt:** For any search family $\mathcal{F}$, $\text{LifetimeTrials}_{t+1} = \text{LifetimeTrials}_t + |\mathcal{F}|$.

---

## 14. Canonical Failure Semantics
- Empty falsification rule $\implies$ `Err(HypothesisError::UnfalsifiableClaim)`.
- Continuous unbounded parameter grid $\implies$ `Err(HypothesisError::UnboundedSearchSpace)`.

---

## 15. Dependency Map
```text
[KZ-001: Expert Forensics]
             │
             ▼
[KZ-002: Hypothesis & Challenger Registry]
             │
             ▼
[KZ-003: Robustness Surface]
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If trial debt persistence conflicts with historical `.audit/` format, open `OPEN_PIN`.
