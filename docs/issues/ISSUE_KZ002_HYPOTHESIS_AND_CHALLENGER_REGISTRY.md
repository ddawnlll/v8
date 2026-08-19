# [IMPL] Issue #KZ-002: Hypothesis & Challenger Registry

**Status:** READY / PATCHED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `risk:hypothesis-governance`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §3, `HYPOTHESIS_LAB_PROTOCOL.md` §1–4, `LEARNING_PROTOCOL.md` §1–4, arXiv:2606.01650.

---

## 1. Objective
Implement the immutable Hypothesis and Challenger Registry (`ResearchFinding`, `HypothesisRecord`, `ChallengerFamilySpec`, `FindingGenerator`, `HypothesisGenerator`, `GlobalTrialLedger`) in pure Rust, enforcing the strict invariant $\text{OBSERVATION} \neq \text{CHANGE}, \text{OBSERVATION} \longrightarrow \text{HYPOTHESIS}$, separating research choices from evaluation attempts, and recording selection/covariance lineage for multiple testing accounting.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §3 (Hypothesis & Challenger Registry).
- **Hypothesis Protocol:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](file:///Users/hootie/src/v8/docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §1–4.
- **Multiple Testing & Selection Lineage Literature:** arXiv:2606.01650 (*Post-Selection Inference, Covariance Lineage, and Overfitting Penalties in Quantitative Strategy Search*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Observations and retrospective findings lack a typed compiler into immutable research hypotheses.
- Prior designs conflated deterministic execution runs with research choices, failing to distinguish between rerunning the same frozen code in CI versus exploring new parameter configurations.
- Covariance structures across candidate returns are needed alongside raw trial counts to evaluate true multiple-testing penalties under post-selection inference.

---

## 5. Required End State
1. **Finding & Hypothesis Types:**
   `ResearchFinding` and `HypothesisRecord` capturing parent lineage, failure tags, target metrics, quantified falsification rules, and finite challenger bounds.
2. **Unprescriptive Hypothesis Generation:**
   `HypothesisGenerator` produces valid falsifiable hypotheses from findings (e.g. fee reduction, holding duration, entry filter, or timing adjustment for `CostDominated`) without hardcoding arbitrary hypothesis solutions into test fixtures.
3. **Research Choice vs Evaluation Attempt Accounting:**
   - `ResearchChoiceId`: Increments global research debt ($+1$) ONLY when a new materially-selected variant or parameter configuration is introduced.
   - `EvaluationAttemptId`: Tracks CI/reproducibility executions ($+1$), leaving research debt unchanged for identical deterministic replays.
4. **Rich Lineage Ledger (`GlobalTrialLedger`):**
   Records: `family_id`, `variant_id`, `dataset_lineage`, `parameter_lineage`, `selection_lineage`, `return_series_covariance_ref`, `research_choice_id`, and `evaluation_attempts`.
5. **Type-System Invariant:**
   Zero direct mutation path from findings or hypotheses to active runtime expert state.

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
2. Test verifying: `ForensicAssessment` $\to$ valid `HypothesisRecord` emitted $\to$ zero runtime mutation possible.
3. Test verifying: evaluating 10 distinct variants increases `research_choice_count` by 10; rerunning the same variant 5 times increases `evaluation_attempts` by 5 while `research_choice_count` remains 1.
4. Test verifying ledger stores parameter lineage and covariance references.
5. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test verification logs for lineage tracking and trial debt isolation.

---

## 9. Non-Goals / Forbidden Scope
- Does not automatically promote or activate challengers into the live execution plane.
- Does not run unbounded continuous exploration grids without discrete trial registration.

---

## 10. Guards
- [ ] Active strategy state cannot be mutated by findings or hypotheses.
- [ ] Rerunning existing frozen code does NOT inflate research trial debt.
- [ ] Covariance references and selection lineage must be preserved in the trial ledger.

---

## 11. Normative Traceability
- **R1 — Immutable Hypothesis Records:** Compiles findings into schema-validated `HypothesisRecord` structs.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §3.1; `HYPOTHESIS_LAB_PROTOCOL.md` §2.
- **R2 — Dual-Counter Research Accounting:** Separates `ResearchChoiceId` from `EvaluationAttemptId`.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §3.2; arXiv:2606.01650.
- **R3 — Covariance & Lineage Preservation:** Records candidate correlation and parameter ancestry for DSR adjustments.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §2; arXiv:2606.01650.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::kaizen::forensics::{ExpertId, VariantId, FailureTag, ForensicAssessment}`
- `v8-core::statistics::Multiplicity`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Observation != Change:** $\text{Observation} \to \text{Hypothesis} \mathrel{\not\to} \text{LiveMutation}$.
- **I2 — Idempotent Debt under Replay:** $\text{VariantHash}(V_1) = \text{VariantHash}(V_2) \implies \Delta \text{ResearchDebt} = 0$.

---

## 14. Canonical Failure Semantics
- Unfalsifiable claim $\implies$ `Err(HypothesisError::UnfalsifiableClaim)`.
- Unbounded continuous search $\implies$ `Err(HypothesisError::UnboundedSearchSpace)`.

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
- If covariance matrix storage format causes performance bottlenecks, open `OPEN_PIN`.
