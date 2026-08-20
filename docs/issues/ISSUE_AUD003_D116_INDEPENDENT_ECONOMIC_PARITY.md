# [IMPL] Issue #AUD-003: D-116 Independent Simulator Parity & Implementation Risk (F04)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `risk`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §10.2 (Independent Engine Parity), Decision `D-116`, arXiv:2603.20319 (P001).  
**Relationships:** Depends on #178 (Population Lineage DAG).

---

## 1. Objective
Implement an independent secondary reference simulator and order-by-order differential reconciliation harness in pure Rust (`v8-core/src/usdm_sim/differential.rs`), establishing true engine-differential testing as required by Decision `D-116` and arXiv:2603.20319 (*P001*), enforcing exact normative tolerance thresholds and evaluating implementation stability.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §10.2 (D-116 Independent Simulator Verification).
- **Decision Authority:** `D-116` (Dual simulator differential certification).
- **Academic Literature:**
  - `P001` (arXiv:2603.20319): *Implementation Risk in Portfolio Backtesting: A Previously Unquantified Source of Error* (Differential testing & implementation uncertainty).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The report currently marks D-116 as `PASS` based on internal `cashflow::tests` and `usdm_sim::tests`.
- Executing tests against the same Rust codebase confirms self-consistency, not independent implementation parity.
- Differential verification requires comparing against an isolated reference implementation with contract-pinned tolerance limits.

---

## 5. Required End State
1. **Independent Reference Simulator:**
   - Standalone reference implementation modeling Binance USD-M matching and margin state without sharing internal helper modules.
2. **Order-by-Order Differential Ledger:**
   - Emits `differential_economic_ledger.jsonl` matching fill quantities, fill prices, fees, funding payments, initial/maintenance margin, and wallet balances.
3. **Contract-Pinned Tolerance Invariants (D-116 §10.2):**
   - **Quantity:** Exact ($0.0$ difference).
   - **Commission / Fee Drag:** $|\Delta \text{Fee}| \le 1.0 \times 10^{-6}$ USDT.
   - **Funding Cashflow:** $|\Delta \text{Funding}| \le 1.0 \times 10^{-6}$ USDT.
   - **Terminal Wallet Balance:** $|\Delta \text{Wallet}| \le 1.0 \times 10^{-4}$ USDT.
4. **Implementation Risk Evaluation:**
   - Emits `implementation_risk.json` reporting:
     - `EngineSensitivity`
     - `ImplementationUncertaintyInterval`
     - `ConclusionStability`: Evaluated as `STABLE | UNSTABLE | INCONCLUSIVE`.  
       *(Note: Finding `UNSTABLE` is a valid, successful completion of the audit check; it blocks economic certification without failing the audit issue).*

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
2. Differential reconciliation test verifying tolerance compliance on test dataset.
3. Generation of `implementation_risk.json` with valid `ConclusionStability` state.
4. Report output updated to show D-116 status derived from differential ledger comparisons.

---

## 8. Required Evidence Artifacts
- `implementation_risk.json`
- `differential_economic_ledger.jsonl`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify primary simulation rules or fee constants.
- Does not force `ConclusionStability == STABLE` if the engines diverge.

---

## 10. Guards
- [ ] Reference engine MUST NOT share mutable state or helper types with primary engine.
- [ ] Tolerance thresholds must strictly match D-116 §10.2 (exact qty, 1e-6 fees/funding, 1e-4 wallet).

---

## 11. Normative Traceability
- **R1 — Independent Engine Differential Parity:** Order-by-order differential ledger matching within D-116 tolerances.  
  *Authority:* `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §10.2; Decision `D-116`.
- **R2 — Implementation Uncertainty Quantification:** Emits `implementation_risk.json`.  
  *Authority:* arXiv:2603.20319 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::usdm_sim::PortfolioReceipt`
- `v8-core::cashflow::EconomicCashflow`
- `v8-core::venue::VenueContract`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Quantity Parity:** $\Delta \text{Qty} \equiv 0.0$.
- **I2 — Fee Parity:** $|\Delta \text{Fee}| \le 10^{-6}\text{ USDT}$.
- **I3 — Funding Parity:** $|\Delta \text{Funding}| \le 10^{-6}\text{ USDT}$.
- **I4 — Wallet Parity:** $|\Delta \text{Wallet}| \le 10^{-4}\text{ USDT}$.

---

## 14. Canonical Failure Semantics
- Divergence exceeding D-116 threshold $\implies$ `Record(DifferentialVerdict::TolerancesExceeded)`.

---

## 15. Dependency Map
```text
[#178: Population Lineage DAG]
              │
              ▼
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
