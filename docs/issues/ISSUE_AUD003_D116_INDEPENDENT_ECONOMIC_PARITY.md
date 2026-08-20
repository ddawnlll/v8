# [IMPL] Issue #AUD-003: D-116 True Independent Economic Parity & Implementation Risk (F04)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `risk`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §11, Decision `D-116`, arXiv:2603.20319 (P001).

---

## 1. Objective
Implement a truly independent secondary reference simulator and differential reconciliation harness (`v8-core/src/usdm_sim/differential.rs`), moving D-116 from internal self-consistency unit tests to true engine-differential testing as formalized in arXiv:2603.20319 (*P001*), emitting `EngineSensitivity`, `ImplementationUncertaintyInterval`, and `ConclusionStability` receipts.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §11 (D-116 Independent Engine Verification).
- **Decision Authority:** `D-116` (Differential execution verification).
- **Academic Literature:**
  - `P001` (arXiv:2603.20319): *Implementation Risk in Portfolio Backtesting: A Previously Unquantified Source of Error* (Differential backtesting & implementation uncertainty).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The report marks D-116 as `PASS` based on internal `cashflow::tests` and `usdm_sim::tests`.
- Under the rigorous definitions of P001, executing Rust tests against the same Rust modules proves internal arithmetic consistency, not independent implementation invariance.
- Differences in discrete order step rounding, margin rounding, fee compounding, and liquidation sequence across independent engines can diverge strategy outcomes.

---

## 5. Required End State
1. **Independent Reference Simulator Harness:**
   - Standalone reference implementation modeling Binance USD-M matching and margin rules without sharing internal allocator/cashflow helper structs.
2. **Order-by-Order Differential Ledger:**
   - Emits `differential_economic_ledger.jsonl` matching fill quantities, fill prices, commission amounts, funding payments, initial/maintenance margin, liquidation trigger points, and terminal wallet equity.
3. **Implementation Uncertainty Metrics:**
   - Compute `EngineSensitivity`, `ImplementationUncertaintyInterval`, and `ConclusionStability` emitted to `implementation_risk.json`.
   - Any divergence exceeding 1e-6 USDT on identical deterministic input triggers failure.

---

## 6. Expected File / Module Surface
```text
v8-core/src/usdm_sim/mod.rs
v8-core/src/usdm_sim/differential.rs
v8-core/src/audit/differential_engine.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Differential reconciliation test verifying 100% agreement across 10,000 synthetic + real trades.
3. `implementation_risk.json` generated with `ConclusionStability: Stable`.
4. Automated gate blocking PR if differential error $> 0.0001\%$.

---

## 8. Required Evidence Artifacts
- `implementation_risk.json`
- `differential_economic_ledger.jsonl`

---

## 9. Non-Goals / Forbidden Scope
- Does not replace primary optimized runtime engine in `v8-core/src/usdm_sim/`.
- Does not change exchange rules or VIP tiers.

---

## 10. Guards
- [ ] Reference engine MUST NOT share internal state or helper structs with the primary simulator.
- [ ] D-116 status in reports MUST reflect differential comparison, not self-consistency unit tests.

---

## 11. Normative Traceability
- **R1 — Independent Differential Parity:** Full transaction-level equivalence against an isolated reference implementation.  
  *Authority:* `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §11; Decision `D-116`.
- **R2 — Implementation Uncertainty Quantification:** Emits `implementation_risk.json` under P001 framework.  
  *Authority:* arXiv:2603.20319 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::usdm_sim::PortfolioReceipt`
- `v8-core::cashflow::EconomicCashflow`
- `v8-core::venue::VenueContract`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Cashflow Differential Invariant:** $\forall t, |\text{Wallet}_{\text{Primary}}(t) - \text{Wallet}_{\text{Ref}}(t)| < \epsilon$.
- **I2 — Ranking Invariance:** $\text{Rank}_{\text{Primary}}(\text{Policies}) == \text{Rank}_{\text{Ref}}(\text{Policies})$.

---

## 14. Canonical Failure Semantics
- Implementation divergence detected $\implies$ `Err(SimError::DifferentialParityFailure)`.

---

## 15. Dependency Map
```text
Order Stream / Market Tape
           │
     ┌─────┴─────┐
     ▼           ▼
[Primary Engine] [Independent Ref Engine]
     │           │
     └─────┬─────┘
           ▼
[Differential Reconciliation] ──► implementation_risk.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If Binance VIP fee rounding or funding calculation rule is ambiguous between specs, STOP and open OPEN_PIN.
