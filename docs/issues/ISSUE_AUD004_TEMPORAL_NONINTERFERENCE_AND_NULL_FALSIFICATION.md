# [IMPL] Issue #AUD-004: Temporal Non-Interference, Search Lineage & Null-World Falsification (F05, F06, F08)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `SIMULATION_TRUTH_SPEC.md` §1–5, `HYPOTHESIS_LAB_PROTOCOL.md` §1–4, arXiv:2607.04958 (P007), arXiv:2604.15531 (P002), arXiv:1905.05023 (P003).

---

## 1. Objective
Implement formal temporal non-interference verification (look-ahead freedom), complete search-lineage tracking (recording all failed/discarded variants for true PBO/DSR calculations), and full-pipeline null-world falsification in pure Rust (`v8-core/src/evaluation/temporal.rs`, `falsification.rs`), establishing mathematical guarantees against future leakage and selection bias.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/SIMULATION_TRUTH_SPEC.md`](docs/contracts/SIMULATION_TRUTH_SPEC.md) §1–5 (PIT availability & non-interference).
- **Hypothesis Protocol:** [`docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`](docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md) §1–4 (Search-lineage completeness & falsification).
- **Academic Literature:**
  - `P007` (arXiv:2607.04958): *Look-Ahead-Freedom as Temporal Non-Interference* (Formal verification of PIT clocks).
  - `P002` (arXiv:2604.15531): *Spurious Predictability in Financial Machine Learning* (Workflow-level null falsification).
  - `P003` (arXiv:1905.05023): *Avoiding Backtesting Overfitting by Covariance-Penalties* (PBO diagnostics).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` separates bar closing time from feature calculation time, but lacks formal future-perturbation metamorphic tests that systematically prove decision invariance when future bars are modified.
- Optimization runs do not always persist failed/aborted challenger variants, distorting multiplicity and PBO penalties.
- Pipeline lack automated placebo/null-world falsification runs that verify the system finds 0 edges on martingale data.

---

## 5. Required End State
1. **Temporal Non-Interference Certificate:**
   - Future-perturbation metamorphic tests: perturbing any bar at $t' > t$ MUST NOT alter the candidate hash, feature values, or decision outcome at time $t$. Emits `temporal_noninterference_receipt.json`.
2. **Complete Search-Family Ledger:**
   - Emits `research_family_ledger.jsonl` and `multiple_testing.json` recording every candidate evaluated, including failed/pruned configurations, ensuring full-family PBO and DSR calculations.
3. **Null-World / Workflow Falsification Battery:**
   - Executes entire research workflow on: (1) Martingale random walks, (2) Shuffled direction series, (3) Timestamp-shifted placebo series.
   - Emits `null_world_falsification.json`. The pipeline MUST return `NO_ECONOMIC_CLAIM` across all placebo worlds.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/mod.rs
v8-core/src/evaluation/temporal.rs
v8-core/src/evaluation/falsification.rs
v8-core/src/kaizen/research_debt.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Metamorphic test verifying zero state change under future data perturbation.
3. Null-world falsification test passing with 0 false positive edge claims.
4. PBO calculation verification against complete search-family ledger.

---

## 8. Required Evidence Artifacts
- `temporal_noninterference_receipt.json`
- `research_family_ledger.jsonl`
- `multiple_testing.json`
- `null_world_falsification.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify market feature definitions.
- Does not change expert core logic.

---

## 10. Guards
- [ ] No candidate evaluation may be omitted from `research_family_ledger.jsonl`.
- [ ] Future data perturbation tests must run as part of CI gates.

---

## 11. Normative Traceability
- **R1 — Temporal Non-Interference:** $F(I_t) \equiv F(I_t \cup \Delta_{>t})$.  
  *Authority:* `SIMULATION_TRUTH_SPEC.md` §3.1; arXiv:2607.04958 §2.
- **R2 — Workflow Null Falsification:** $\mathbb{P}(\text{Reject } H_0 \mid \text{NullWorld}) \le \alpha$.  
  *Authority:* `HYPOTHESIS_LAB_PROTOCOL.md` §3; arXiv:2604.15531 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::state::MarketState`
- `v8-core::kaizen::research_debt::GlobalTrialLedger`
- `v8-core::statistics::Multiplicity`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Non-Interference Invariant:** $\frac{\partial \text{Decision}(t)}{\partial \text{Bar}(t + k)} = 0 \quad \forall k > 0$.
- **I2 — Family Completeness:** $N_{\text{trials}} = N_{\text{survived}} + N_{\text{discarded}}$.

---

## 14. Canonical Failure Semantics
- Lookahead leakage detected $\implies$ `Err(TemporalError::LookaheadViolation)`.

---

## 15. Dependency Map
```text
Market Tape / Perturbation Engine
              │
              ▼
   [Temporal Non-Interference] ──► temporal_noninterference_receipt.json
              │
              ▼
   [Null-World Falsification] ──► null_world_falsification.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If any indicator window relies on unclosed current bar data without explicit point-in-time timestamping, STOP and open OPEN_PIN.
