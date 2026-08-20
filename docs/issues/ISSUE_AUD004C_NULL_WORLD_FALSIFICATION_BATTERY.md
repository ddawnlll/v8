# [RESEARCH] Issue #AUD-004C: Null-World & Placebo Workflow Falsification Battery (F08)

**Status:** READY / PROPOSED  
**Issue Type:** `RESEARCH`  
**Change Class:** `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:research`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `HYPOTHESIS_LAB_PROTOCOL.md` §3 (Workflow Falsification), arXiv:2604.15531 (P002), arXiv:2607.20093 (P037).  
**Relationships:** Depends on #180A, #187 (AUD-004B).

---

## 1. Objective
Design and execute a full-pipeline empirical falsification battery on zero-predictability and placebo environments (Martingale random walks, shuffled direction series, timestamp-shifted series), evaluating whether the internal promotion statistic controls Type-I false discovery rate at $\mathbb{P}(\text{False Discovery} \mid H_0) \le \alpha$.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §3 (Null World Falsification).
- **Academic Literature:**
  - `P002` (arXiv:2604.15531): *Spurious Predictability in Financial Machine Learning* (Workflow-level null falsification).
  - `P037` (arXiv:2607.20093): *Retail Trader's Ruin: An Anatomy of Popular Signal Failure* (Positive vs negative controls).

---

## 3. Change Class
`NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The research pipeline does not have an automated synthetic placebo harness to measure the empirical false-positive rate of candidate selection across thousands of noise-only realizations.

---

## 5. Required End State
1. **Placebo Reference Classes:**
   - (A) Continuous Martingale Geometric Brownian Motion series.
   - (B) Shuffled-direction bar series with preserved volatility structure.
   - (C) Timestamp-shifted microstructure series.
2. **False-Discovery Evaluation:**
   - Run entire discovery + validation pipeline on 1,000 placebo runs.
   - Evaluate empirical error rate $\hat{\alpha} = \frac{\text{Internal Promoted Candidates}}{1,000}$.
   - Verify $\hat{\alpha} \le \alpha_{\text{target}}$ (e.g. $0.05$).
3. **Artifact Generation:**
   - Emits `null_world_falsification.json` with empirical rejection rates and test calibration stats.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/falsification.rs
v8-core/src/evaluation/mod.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Empirical false discovery rate satisfies $\hat{\alpha} \le 0.05$ under target $\alpha=0.05$.
3. All placebo outputs remain strictly labeled `claim: NO_ECONOMIC_CLAIM`.

---

## 8. Required Evidence Artifacts
- `null_world_falsification.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify production strategy parameters based on synthetic null performance.

---

## 10. Guards
- [ ] Synthetic placebo runs must never enter live findings ledgers or production evaluation manifests.

---

## 11. Normative Traceability
- **R1 — Null-World Falsification:** $\mathbb{P}(\text{Promote} \mid H_0) \le \alpha$.  
  *Authority:* `HYPOTHESIS_LAB_PROTOCOL.md` §3; arXiv:2604.15531 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::statistics::detrended::DetrendedNull`
- `v8-core::statistics::reality_check::RealityCheck`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Type-I Error Bound:** $\mathbb{E}[\mathbf{1}_{\{\text{Promote}\}} \mid H_0] \le \alpha$.

---

## 14. Canonical Failure Semantics
- Calibrated error exceeds nominal $\alpha \implies$ `Record(FalsificationVerdict::ExcessFalseDiscoveryRate)`.

---

## 15. Dependency Map
```text
Placebo Generator (Martingale / Shuffled)
                   │
                   ▼
     [Full Research Pipeline]
                   │
                   ▼
     [Empirical Error Audit] ──► null_world_falsification.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If placebo series generation method diverges from Aronson/White stationary bootstrap assumptions, open OPEN_PIN.
