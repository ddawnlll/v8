# [RESEARCH] Issue #AUD-008: L1/L2 Tape Identifiability for Passive Execution & Maker TCA (F13, F14, F16, F29)

**Status:** DATA-BLOCKED / RESEARCH  
**Issue Type:** `RESEARCH`  
**Change Class:** `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:research`, `triage`, `rust`, `P1`, `execution`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §6, §8, `TARGET_ORACLE_SPEC.md` §8 (Identifiability Bounds), arXiv:2502.18625 (P017), arXiv:2409.12721 (P018).  
**Relationships:** Blocked on sequenced trade tape / L2 depth.

---

## 1. Objective
Investigate whether the available market data tape supports non-parametric or empirical identification of passive limit order fill probability ($P_{\text{fill}}$), queue position dynamics, and post-fill adverse selection markouts, and determine the empirical boundary between `IDENTIFIED`, `MODEL_DERIVED_STRESS_ONLY`, and `NOT_IDENTIFIABLE` passive execution claims.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §6 (TCA & Friction), §8 (Order Execution Fidelity).
- **Oracle Identifiability:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §8 (Execution Authority Bounds).
- **Academic Literature:**
  - `P017` (arXiv:2502.18625): *The Market Maker's Dilemma: Fill Probability vs Post-Fill Returns*.
  - `P018` (arXiv:2409.12721): *Market Simulation under Adverse Selection*.

---

## 3. Change Class
`NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The runtime currently uses 1h OHLCV bar data. Under `TARGET_ORACLE_SPEC.md` §8, bar data alone cannot identify queue priority, partial fills, or microsecond adverse selection without making unsupported model assumptions.
- Any passive maker model evaluated on bar data must remain strictly labeled `MODEL_DERIVED_STRESS_ONLY` until calibrated on high-resolution tick/trade data.

---

## 5. Required End State
1. **Identifiability Diagnostic Harness:**
   - Evaluates whether available tape supports:
     - (A) Non-parametric fill bounding via Brownian bridge touch probabilities.
     - (B) Post-fill return trajectories at $+1$, $+5$, $+10$ bar markout horizons.
2. **Outcome Classification:**
   - Emit `maker_identifiability_receipt.json` certifying whether passive execution is:
     - `PASS`: Adequate empirical calibration supported by data.
     - `DATA_BLOCKED`: Data resolution insufficient for causal claim; restricted to sensitivity stress.
3. **Artifact Generation:**
   - Emits `maker_identifiability_receipt.json` and `markouts.parquet`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/usdm_sim/maker_model.rs
v8-core/src/analysis/markouts.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Zero passive profit claims emitted without explicit `MODEL_DERIVED` authority labels on 1h tape.
3. Markout trajectory evaluation verifies that post-fill return curves are recorded objectively.

---

## 8. Required Evidence Artifacts
- `maker_identifiability_receipt.json`
- `markouts.parquet`

---

## 9. Non-Goals / Forbidden Scope
- Does not grant unconditional maker execution authority on OHLCV-only tape.
- Does not substitute 0.02% maker fee without modeling adverse selection markouts.

---

## 10. Guards
- [ ] Fee substitution alone is strictly forbidden under Rule 12 and `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §8.3.

---

## 11. Normative Traceability
- **R1 — Execution Identifiability:** Requires explicit data authority for passive claims.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §8.3; arXiv:2502.18625 §2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::oracle::taxonomy::AuthorityLevel`
- `v8-core::oracle::taxonomy::Identifiability`
- `v8-core::venue::VenueContract`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Model Derived Constraint:** $\text{DataType} = \text{OHLCV} \implies \text{Authority}(\text{PassiveFill}) \equiv \text{ModelDerived}$.

---

## 14. Canonical Failure Semantics
- Insufficient tape resolution $\implies$ `Record(ExecutionIdentifiability::DataBlocked)`.

---

## 15. Dependency Map
```text
Sequenced Market Tape / Bar Data
               │
               ▼
   [Maker Identifiability Harness] ──► maker_identifiability_receipt.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If passive alpha claim is made without accompanying markout analysis, STOP and fail closed.
