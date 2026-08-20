# [IMPL] Issue #AUD-004A: Point-in-Time Temporal Fault Injection & Non-Interference (F05)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `SIMULATION_TRUTH_SPEC.md` §3 (PIT Availability & Clocks), `TARGET_ORACLE_SPEC.md` §6.2, arXiv:2607.04958 (P007).  
**Relationships:** Depends on #178 (Lineage DAG), #179 (Parity).

---

## 1. Objective
Implement formal Point-in-Time (PIT) temporal fault-injection and metamorphic future-perturbation tests in pure Rust (`v8-core/src/evaluation/temporal.rs`), ensuring decision-time features and candidate generation are invariant to future bar modifications and that any future-known field hard-fails immediately.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/SIMULATION_TRUTH_SPEC.md`](docs/contracts/SIMULATION_TRUTH_SPEC.md) §3 (PIT Availability Time vs Event Time).
- **Oracle Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §6.2 (Look-ahead rejection).
- **Academic Literature:**
  - `P007` (arXiv:2607.04958): *Look-Ahead-Freedom as Temporal Non-Interference: A Verifiable Correctness Property for Backtesting and Agentic Trading Pipelines*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` separates bar close times from available times, but lacks an automated metamorphic fault-injection harness to systematically verify lookahead non-interference across all 28 expert feature pipelines.

---

## 5. Required End State
1. **Metamorphic Perturbation Engine:**
   - For every timestamp $t$, perturb any bar $t' > t$ (e.g. inject extreme high/low prices, altered volumes).
   - Verify that:
     $$\text{State}(t \mid \text{PerturbedTape}_{>t}) \equiv \text{State}(t \mid \text{OriginalTape})$$
     $$\text{Decision}(t \mid \text{PerturbedTape}_{>t}) \equiv \text{Decision}(t \mid \text{OriginalTape})$$
2. **Hard-Fail on Future-Known Fields:**
   - Accessing any unclosed bar or feature with availability time $t_{\text{avail}} > t_{\text{decision}}$ triggers a hard panic/error.
3. **Temporal Non-Interference Receipt:**
   - Emits `temporal_noninterference_receipt.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/mod.rs
v8-core/src/evaluation/temporal.rs
v8-core/src/state.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Metamorphic test: 0 candidate hash differences across 1,000 future perturbation rounds.
3. Fault-injection test: accessing future data deliberately triggers an immediate fail-closed error.

---

## 8. Required Evidence Artifacts
- `temporal_noninterference_receipt.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not change indicator parameter values.
- Does not evaluate cross-asset transfer (covered in F25).

---

## 10. Guards
- [ ] No feature calculation may consume bar $t$ before bar $t$ is closed.
- [ ] Availability time must be strictly distinct from event timestamp.

---

## 11. Normative Traceability
- **R1 — Temporal Non-Interference:** $F(I_t) \equiv F(I_t \cup \Delta_{>t})$.  
  *Authority:* `SIMULATION_TRUTH_SPEC.md` §3.1; arXiv:2607.04958 §2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::state::MarketState`
- `v8-core::candidate::Candidate`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Non-Interference Invariant:** $\frac{\partial \text{Decision}(t)}{\partial \text{Bar}(t+k)} \equiv 0 \quad \forall k > 0$.

---

## 14. Canonical Failure Semantics
- Future timestamp detected $\implies$ `Err(TemporalError::FutureDataLeakage)`.

---

## 15. Dependency Map
```text
[#178: Lineage DAG]
         │
         ▼
[Perturbation Engine] ──► [Temporal Invariance Check] ──► temporal_noninterference_receipt.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If any multi-timeframe feature calculation requires interpolating unclosed higher-interval bars, STOP and open OPEN_PIN.
