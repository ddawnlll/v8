# [IMPL] Issue #KZ-001: Expert Forensics & Multi-Tag Failure Taxonomy

**Status:** READY / PATCHED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `risk:forensics-attribution`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §2.1–2.2, `HYPOTHESIS_LAB_PROTOCOL.md` §1–4, `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, `LEARNING_PROTOCOL.md` §1–4, arXiv:2603.29086.

---

## 1. Objective
Implement deterministic financial, execution, and regime forensics (`ExpertForensics`, `RegimeForensics`, `ForensicAssessment`, `FailureTag`, `EvidenceValidity`, `ReplicationStatus`) in pure Rust within `v8-core/src/kaizen/diagnosis.rs` (or `forensics.rs`), establishing the foundational diagnostic layer that decomposes gross edge from friction without mutating active strategies.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §2 (Forensic Attribution & Multi-Tag Failure Taxonomy).
- **Hypothesis Protocol Authority:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](file:///Users/hootie/src/v8/docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §2 (Dependence units, effective sample size, and attribution validity gates).
- **Evidence Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](file:///Users/hootie/src/v8/docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4.
- **Learning Safety Protocol:** [`docs/protocols/LEARNING_PROTOCOL.md`](file:///Users/hootie/src/v8/docs/protocols/LEARNING_PROTOCOL.md) §1–4.
- **Cost Model Literature:** arXiv:2603.29086 (*Execution Cost Realism and Algorithmic Ranking Invariance*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` produces execution traces and ledgers, but lacks a typed multi-tag diagnostic classifier.
- When an expert incurs a negative net return, it is treated as an undifferentiated failure rather than separating empirical gross underperformance (`ObservedGrossNegative`) from friction drag (`CostDominated`), regime breakdown (`RegimeFragile`), or validity failure (`AttributionUnsafe`).
- Trade counts were historically treated as IID observations rather than utilizing dependence-aware effective episode units.

---

## 5. Required End State
1. **Multi-Tag Forensic Assessment:**
   ```rust
   pub enum FailureTag {
       ObservedGrossNegative,
       CostDominated,
       ParameterFragile,
       RegimeFragile,
   }

   pub enum EvidenceValidity {
       Valid,
       AttributionUnsafe { execution_share: f64, population_divergence_p: f64 },
       InsufficientEvidence { observed_events: u64, effective_episodes: f64 },
   }

   pub enum ReplicationStatus {
       CandidateForReplication,
       Unviable,
       PendingInvestigation,
   }

   pub struct ForensicAssessment {
       pub expert_id: ExpertId,
       pub variant_id: VariantId,
       pub tags: Vec<FailureTag>,
       pub validity: EvidenceValidity,
       pub replication_status: ReplicationStatus,
       pub gross_r: f64,
       pub fee_r: f64,
       pub slippage_r: f64,
       pub funding_r: f64,
       pub net_r: f64,
       pub regime_breakdown: Vec<RegimeForensics>,
   }
   ```
2. **Dependence-Aware Evidence Requirements:**
   Replaces naive trade counts with `EvidenceRequirement { min_events: u64, min_effective_episodes: f64, dependence_unit: String }` using block bootstrap / effective sample counts from `HYPOTHESIS_LAB_PROTOCOL.md`.
3. **Attribution Validity Separation:**
   `AttributionUnsafe` is classified as an `EvidenceValidity` gate (based on `execution_share` and executed vs rejected population divergence), not conflated with strategy economic failure tags.
4. **Epistemic Modesty:**
   $\text{Gross } R < 0.0$ is tagged as `ObservedGrossNegative` (empirical sample result), without making ontologically unprovable claims of absolute directional alpha absence.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/mod.rs
v8-core/src/kaizen/diagnosis.rs (or forensics.rs)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying multi-label capability: an expert with `gross > 0, net < 0`, regime collapse in chop, and high parameter sensitivity simultaneously receives `[CostDominated, RegimeFragile, ParameterFragile]`.
3. Test verifying `AttributionUnsafe` validity gate fires on high population divergence without falsely tagging strategy signal logic as broken.
4. Test verifying `InsufficientEvidence` triggers when effective episodes are below threshold, leaving replication status as `PendingInvestigation`.
5. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test logs confirming multi-tag assignment and validity gate separation.

---

## 9. Non-Goals / Forbidden Scope
- Does not modify or mute existing active experts in `v8-core/src/experts/`.
- Does not alter venue simulation rules.
- Does not open frozen OOS.

---

## 10. Guards
- [ ] Multi-tag classification: failure tags are not mutually exclusive.
- [ ] Validity failures (`AttributionUnsafe`, `InsufficientEvidence`) are isolated from strategy diagnostic tags.
- [ ] Dependence units and effective sample sizes are used instead of naive trade counts.

---

## 11. Normative Traceability
- **R1 — Multi-Tag Diagnostic Architecture:** Implements `FailureTag` vector supporting overlapping failure modes.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §2.2.
- **R2 — Evidence Validity Gate:** Evaluates `AttributionUnsafe` and `InsufficientEvidence` as data validity filters.  
  *Authority:* `HYPOTHESIS_LAB_PROTOCOL.md` §2; `KAIZEN_ENGINE_SPEC.md` §2.2.
- **R3 — Read-Only Diagnostic Invariance:** Diagnostic outputs cannot mutate live decision plane state.  
  *Authority:* `V8_CONSTITUTION.md` Rule 15; `LEARNING_PROTOCOL.md` §1.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::cashflow::EconomicCashflow`
- `v8-core::evaluation::TradeRow`
- `v8-core::statistics::Multiplicity`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Multi-Label Consistency:** $\text{Tags}(E) \subseteq \{\text{ObservedGrossNegative}, \text{CostDominated}, \text{ParameterFragile}, \text{RegimeFragile}\}$.
- **I2 — Validity Precondition:** $\text{Validity}(E) \neq \text{Valid} \implies \text{ReplicationStatus}(E) \neq \text{CandidateForReplication}$.

---

## 14. Canonical Failure Semantics
- Incomplete trade record $\implies$ `Err(ForensicsError::IncompleteTelemetry)`.

---

## 15. Dependency Map
```text
Evaluation Evidence / Trade Logs
              │
              ▼
    [KZ-001: Expert Forensics]
              │
              ▼
    [KZ-002: Hypothesis Registry]
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If effective sample size formula conflicts between `statistics.rs` and `HYPOTHESIS_LAB_PROTOCOL.md`, open `OPEN_PIN`.
