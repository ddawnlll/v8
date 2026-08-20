# [RESEARCH] Issue #AUD-005B: O5 Decision-Time Recoverability Challenger (F20)

**Status:** READY / PROPOSED  
**Issue Type:** `RESEARCH`  
**Change Class:** `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:research`, `triage`, `rust`, `P0`, `risk`  
**Owning Authority:** `TARGET_ORACLE_SPEC.md` §12 (Decision-Time Recoverability), §17 (Reconciliation Protocols), arXiv:2606.29018 (P023).  
**Relationships:** Depends on #181 (AUD-005A).

---

## 1. Objective
Design and evaluate the O5 Decision-Time Recoverability Challenger in pure Rust (`v8-core/src/oracle/recoverability.rs`), formalizing the 4-stage canonical recoverability chain ($\text{HindsightOpportunity} \ne \text{DecisionTimeRecoverableOpportunity} \ne \text{PromotablePolicy} \ne \text{LiveSupportedPolicy}$) to isolate actionable alpha from unreachable hindsight theoretical gains.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §12.1–12.4 (Decision-Time Recoverability vs Hindsight Ceiling), §17.
- **Academic Literature:**
  - `P023` (arXiv:2606.29018): *Liquidity-Based Audit of AI and Algorithmic Trading Strategies* (Recoverability & regret).

---

## 3. Change Class
`NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Strategy performance is frequently contrasted directly against the unconstrained Hindsight Oracle ceiling $V^*(S_t)$, which includes trades only identifiable with post-event future information.
- A causal decision-time recoverability policy is needed to quantify what fraction of the $+490R$ Oracle ceiling was realistically discoverable point-in-time.

---

## 5. Required End State
1. **Canonical 4-Stage Recoverability Chain:**
   $$\text{HindsightOpportunity} \longrightarrow \text{DecisionTimeRecoverable} \longrightarrow \text{PromotablePolicy} \longrightarrow \text{LiveSupportedPolicy}$$
   - **Stage 1 (Hindsight Opportunity):** Dynamic programming global maximum $V^*(S_t)$.
   - **Stage 2 (PIT Recoverable Opportunity):** Optimal policy using strictly point-in-time identifiable feature filtrations.
   - **Stage 3 (Promotable Policy):** Policy admissible under certified multiple-testing and risk constraints.
   - **Stage 4 (Live-Supported Policy):** Executable policy verified under exchange order book and capital friction.
2. **Artifact Generation:**
   - Emits `recoverability_chain.parquet` and `recoverable_gap_waterfall.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/oracle/mod.rs
v8-core/src/oracle/recoverability.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Monotonic subset property check: $\text{LiveSupported} \subseteq \text{Promotable} \subseteq \text{PITRecoverable} \subseteq \text{HindsightOpportunity}$.
3. Parquet schema validation for `recoverability_chain.parquet`.

---

## 8. Required Evidence Artifacts
- `recoverability_chain.parquet`
- `recoverable_gap_waterfall.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not promote unverified policies to live execution.

---

## 10. Guards
- [ ] At no point may $\text{PITRecoverable} > \text{HindsightOpportunity}$.

---

## 11. Normative Traceability
- **R1 — Recoverability Waterfall:** Implements canonical 4-stage recoverability chain.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §12.2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::oracle::authority::OracleOutcome`
- `v8-core::oracle::taxonomy::AuthorityLevel`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Recoverability Monotonicity:** $U(\text{Live}) \le U(\text{Promotable}) \le U(\text{PITRecoverable}) \le V^*(S_t)$.

---

## 14. Canonical Failure Semantics
- Inverted stage ordering $\implies$ `Err(RecoverabilityError::MonotonicityViolation)`.

---

## 15. Dependency Map
```text
[#181: AUD-005A O4 Regret Engine]
               │
               ▼
   [Recoverability Challenger] ──► recoverability_chain.parquet / recoverable_gap_waterfall.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If PIT recoverability filter introduces circular lookahead dependencies, STOP and escalate OPEN_PIN.
