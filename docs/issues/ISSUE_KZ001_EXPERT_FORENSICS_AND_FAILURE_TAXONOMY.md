# [IMPL] Issue #KZ-001: Expert Forensics & Failure Taxonomy

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `risk:forensics-attribution`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §2.1–2.2, `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, `LEARNING_PROTOCOL.md` §1–4, arXiv:2603.29086.

---

## 1. Objective
Implement deterministic financial, execution, and regime forensics (`ExpertForensics`, `RegimeForensics`, `FailureClass`) in pure Rust within the Kaizen subsystem (`v8-core/src/kaizen/diagnosis.rs` or `forensics.rs`), establishing the foundational diagnostic layer that decomposes gross edge from fee, slippage, funding friction, parameter fragility, and regime breakdown without mutating active strategies.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §2 (Forensic Attribution & Deterministic Failure Taxonomy).
- **Evidence Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](file:///Users/hootie/src/v8/docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4.
- **Learning Safety Protocol:** [`docs/protocols/LEARNING_PROTOCOL.md`](file:///Users/hootie/src/v8/docs/protocols/LEARNING_PROTOCOL.md) §1–4 (`Outcome data never mutates active Expert`).
- **Cost Model Literature:** arXiv:2603.29086 (*Execution Cost Realism and Algorithmic Ranking Invariance*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` produces cashflows and ledger files (`portfolio_receipt.json`, `economic-cashflow.jsonl`, `trades.parquet`), but lacks a typed, deterministic diagnostic classifier.
- When an expert incurs a negative net return (e.g. `macd_stoch_trend`: -45.29R), the system treats it as an undifferentiated failure rather than distinguishing between signal detection flaws ($\text{Gross } R < 0$) and execution friction drag ($\text{Gross } R > 0 \land \text{Net } R \le 0$).
- No typed failure taxonomy exists to guide subsequent hypothesis generation without trial-and-error mutation.

---

## 5. Required End State
1. **Typed Forensic Structures:**
   `ExpertForensics` and `RegimeForensics` capturing `gross_r`, `fee_r`, `slippage_r`, `funding_r`, `net_r`, `trade_count`, `turnover`, `execution_share`, `mean_mae_r`, `mean_mfe_r`, `break_even_cost_bps`, and per-regime slices.
2. **Deterministic Failure Classification:**
   `FailureClass` enum mapping:
   - `GrossNegative`: Directional edge absent before costs ($\text{Gross } R < 0$).
   - `CostDominated`: Gross edge positive, but friction drag renders $\text{Net } R \le 0$.
   - `ParameterFragile`: Performance collapses under local threshold perturbations.
   - `RegimeFragile`: Catastrophic loss in specific volatility/trend habitats while positive in others.
   - `AttributionUnsafe`: High veto rate or slot contention.
   - `InsufficientEvidence`: $N < N_{\min}$ (default 30 trades).
   - `CandidateForReplication`: Positive after full costs.
3. **Pure Diagnostic Boundary:**
   Zero direct mutation of active runtime state; classification is solely an evidence input to the Kaizen hypothesis compiler.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/mod.rs
v8-core/src/kaizen/diagnosis.rs (or forensics.rs)
tests/test_kaizen_forensics.rs (or unit tests in module)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying `gross = -0.18, fees = 0.05, net = -0.23` yields `FailureClass::GrossNegative`.
3. Test verifying `gross = +0.14, fees = 0.15, slippage = 0.04, net = -0.05` yields `FailureClass::CostDominated`.
4. Test verifying $N < 30$ yields `FailureClass::InsufficientEvidence`.
5. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test execution logs proving deterministic taxonomy classification.
- Updated `RUNLOG.md` entry documenting module addition.

---

## 9. Non-Goals / Forbidden Scope
- Does not modify or mute existing active experts in `v8-core/src/experts/`.
- Does not change simulator execution rules or venue contracts.
- Does not open frozen OOS.

---

## 10. Guards
- [ ] No active expert parameters are modified.
- [ ] Classification logic is 100% deterministic with no floating-point ambiguity.
- [ ] Python oracle boundary remains frozen.

---

## 11. Normative Traceability
- **R1 — Forensic Metric Ingestion:** Ingests realized gross returns, fees, slippage, and funding drag per expert.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §2.1; `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §5.
- **R2 — Deterministic Taxonomy:** Implements 7-class failure taxonomy without floating-point hysteresis.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §2.2; `LEARNING_PROTOCOL.md` §3.
- **R3 — Read-Only Diagnostic Invariance:** Diagnostic outputs are immutable records and cannot trigger live strategy modification.  
  *Authority:* `V8_CONSTITUTION.md` Rule 15; `LEARNING_PROTOCOL.md` §1.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::cashflow::EconomicCashflow`
- `v8-core::evaluation::TradeRow` / `v8-core::evaluation::surfaces::TradeOutcomeInput`
- `v8-core::usdm_sim::UsdmSimulationReceipt`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Net Conservation:** $\text{Net } R \equiv \text{Gross } R - (\text{Fee } R + \text{Slippage } R + \text{Funding } R)$.
- **I2 — Threshold Determinism:** $\text{Gross } R < 0.0 \implies \text{GrossNegative}$ strictly precedes friction analysis.
- **I3 — Small Sample Abstention:** $N < N_{\min} \implies \text{InsufficientEvidence}$, preventing premature hypothesis triggering.

---

## 14. Canonical Failure Semantics
- Incomplete trade record $\implies$ `Err(ForensicsError::IncompleteTelemetry)`.
- Non-convergent cashflow $\implies$ Fail closed; expert marked `AttributionUnsafe`.

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
- If fee accounting definition diverges from `VenueContract`, STOP and open `OPEN_PIN`.
