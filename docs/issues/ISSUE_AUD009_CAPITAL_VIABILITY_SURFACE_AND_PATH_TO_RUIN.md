# [IMPL] Issue #AUD-009: Capital State, Viability Surface, Path-to-Ruin & Sizing (F17, F18)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `risk`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §5, §10, arXiv:2608.01494 (P025), arXiv:2605.05089 (P027), arXiv:2603.09164 (P021).

---

## 1. Objective
Implement the multi-tier Capital Viability Surface ($100 to $5,000 equity sweep), Path-to-Ruin / Capital Hysteresis diagnostics, and Slippage-at-Risk (SaR) tail stress models in pure Rust (`v8-core/src/usdm_sim/capital_viability.rs`), solving the under-capitalization trap (32,428 `QUANTITY_ROUNDS_TO_ZERO` rejections) and formalizing capital-state dependencies.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §5 (Risk Allocation), §10 (Capital Dynamics).
- **Academic Literature:**
  - `P025` (arXiv:2608.01494): *Conformal Kelly: Prediction Intervals in Fractional Sizing*.
  - `P027` (arXiv:2605.05089): *Dynamic Collateral Control for Perpetual Trading* (Capital hysteresis & collateral state).
  - `P021` (arXiv:2603.09164): *Slippage-at-Risk (SaR): A Forward-Looking Liquidity Risk Framework*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Baseline runs show 32,428 `QUANTITY_ROUNDS_TO_ZERO` rejections because fixed fractional sizing ($f_{\text{risk}} = 0.5\%$) on degraded capital fails Binance's 5.0 USDT minimum notional filter ($0.001 \text{ BTC} \times \$60,000 = \$60 \text{ min notional}$).
- The system lacks a formalized `CriticalCapitalThreshold` showing the minimum initial equity required to avoid the under-capitalization death spiral.
- Forced liquidation stress and tail slippage are not evaluated beyond standard margin ratio triggers.

---

## 5. Required End State
1. **Capital Viability Surface:**
   - Multi-tier initial equity sweep: $[\$100, \$250, \$500, \$1,000, \$2,500, \$5,000, \$10,000]$.
   - Computes: Survival Probability, Tradable Share %, Rounding Rejection %, Terminal CAGR, and Capital Efficiency.
   - Emits `capital_viability_surface.parquet`.
2. **Path-to-Ruin & Capital Hysteresis Analysis:**
   - Evaluates: $\text{Time to 50\% Drawdown}$, $\text{First Economically Disabled State}$, and lost opportunity cost from shrunken capital.
   - Emits `path_to_ruin.json`.
3. **Slippage-at-Risk (SaR) Engine:**
   - Computes $95\%$ and $99\%$ tail slippage under forced liquidation and depth collapse scenarios.
   - Emits `slippage_at_risk.json` and `liquidation_stress.parquet`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/usdm_sim/mod.rs
v8-core/src/usdm_sim/capital_viability.rs
v8-core/src/allocator.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Monotonicity check: tradable share % must increase monotonically with initial equity.
3. Path-to-ruin solver verification against known mathematical discrete random walks.
4. Parquet output validation for `capital_viability_surface.parquet`.

---

## 8. Required Evidence Artifacts
- `capital_viability_surface.parquet`
- `path_to_ruin.json`
- `slippage_at_risk.json`
- `liquidation_stress.parquet`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify exchange step sizes or tick sizes.
- Does not allow sizing to bypass venue margin brackets.

---

## 10. Guards
- [ ] Position sizing must always be audited after edge validation, never assumed to create edge.
- [ ] No trade request may violate exchange `minNotional` rules.

---

## 11. Normative Traceability
- **R1 — Capital State Dependency:** Models path-dependent opportunity set under finite collateral.  
  *Authority:* `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §10; arXiv:2605.05089 §3.
- **R2 — Tail Liquidity Diagnostics:** Emits SaR and liquidation stress metrics.  
  *Authority:* arXiv:2603.09164 §4.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::account::AccountState`
- `v8-core::allocator::RiskBudgetAllocator`
- `v8-core::venue::VenueContract`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Critical Capital Boundary:** $E_{\text{crit}} = \frac{\text{MinNotional} \times \Delta P_{\text{stop}}}{P \times f_{\text{risk}}}$.
- **I2 — Collateral Solvency:** $\text{AvailableBalance} \ge 0 \implies \text{MarginRatio} < 100\%$.

---

## 14. Canonical Failure Semantics
- Equity below critical boundary $\implies$ `Record(RejectionReason::UnderCapitalizedTerminalTrap)`.

---

## 15. Dependency Map
```text
Account Balance State + Venue Filters
                 │
                 ▼
     [Capital Viability Sweep] ──► capital_viability_surface.parquet
                 │
                 ▼
     [Path-to-Ruin / SaR Audit] ──► path_to_ruin.json / slippage_at_risk.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If fractional Kelly formulas produce leverage recommendations exceeding venue bracket limits, clamp to bracket and notify.
