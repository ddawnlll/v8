# [IMPL] Issue #AUD-009A: Static Capital Viability Constraint Envelope (F18)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `risk`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §5 (Risk Allocation), §10 (Capital Dynamics), Decision `D-110`, arXiv:2605.05089 (P027).  
**Relationships:** Depends on #178 (Lineage DAG), #179 (Parity).

---

## 1. Objective
Implement the multi-tier Capital Viability Surface and deterministic Capital Constraint Envelope in pure Rust (`v8-core/src/usdm_sim/capital_viability.rs`), solving the under-capitalization trap (32,428 `QUANTITY_ROUNDS_TO_ZERO` rejections) by evaluating the exact multi-constraint critical equity threshold:
$$E_{\text{crit}} = \max\left(E_{\text{step}}, E_{\text{notional}}, E_{\text{margin}}, E_{\text{leverage}}, E_{\text{heat}}\right)$$

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §5 (Discretization & Allocation Rules), §10 (Capital State Transitions).
- **Decision Authority:** `D-110` (4-part State Ontology).
- **Academic Literature:**
  - `P027` (arXiv:2605.05089): *Dynamic Collateral Control for Perpetual Trading* (Capital state & collateral constraints).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- On a $1,000 USDT account, when equity drops below critical boundaries, fixed fractional sizing ($f_{\text{risk}} = 0.5\%$) produces risk budgets below the legal lot step ($0.001 \text{ BTC}$) or minimum notional ($5.0 \text{ USDT}$), causing 32,428 silent candidate rejections.
- The critical capital boundary is a composite envelope of multiple discrete exchange rules, not a single scalar formula.

---

## 5. Required End State
1. **Multi-Constraint Capital Envelope:**
   For a candidate with entry price $P$, stop distance $\Delta P_{\text{stop}}$, risk fraction $f_{\text{risk}}$, and leverage $L$:
   - $E_{\text{step}} = \frac{\text{StepSize} \times \Delta P_{\text{stop}}}{f_{\text{risk}}}$
   - $E_{\text{notional}} = \frac{\text{MinNotional} \times \Delta P_{\text{stop}}}{P \times f_{\text{risk}}}$
   - $E_{\text{margin}} = \frac{\text{MinNotional}}{L}$
   - $E_{\text{crit}} = \max\left(E_{\text{step}}, E_{\text{notional}}, E_{\text{margin}}\right)$
2. **Capital Viability Sweep:**
   - Evaluates initial equity tiers: $[\$100, \$250, \$500, \$1,000, \$2,500, \$5,000, \$10,000]$.
   - Emits: $\text{TradableSharePct}$, $\text{RoundingRejections}$, $\text{TerminalEquity}$, $\text{MaxDrawdown}$, $\text{RuinOccurred}(\text{bool})$, $\text{TimeToRuin}$.
   - Emits `capital_viability_surface.parquet` and `path_to_ruin.json`.

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
2. Exact constraint matching: verifying that $E < E_{\text{crit}}$ rejects with the precise matching canonical reason code (`QUANTITY_ROUNDS_TO_ZERO`, `MIN_NOTIONAL_REJECTED`, or `INSUFFICIENT_AVAILABLE_BALANCE`).
3. Monotonicity: Tradable Share % increases monotonically with initial equity.

---

## 8. Required Evidence Artifacts
- `capital_viability_surface.parquet`
- `path_to_ruin.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify Binance USD-M contract parameters.
- Does not claim stochastic survival probability on a single deterministic historical path.

---

## 10. Guards
- [ ] Available balance and margin ratio must be tracked as separate state variables.
- [ ] No trade may bypass Binance lot size discretization.

---

## 11. Normative Traceability
- **R1 — Critical Capital Envelope:** Enforces multi-constraint capital boundaries.  
  *Authority:* `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §5.2, §10.1.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::account::AccountState`
- `v8-core::allocator::RiskBudgetAllocator`
- `v8-core::venue::VenueContract`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Envelope Definition:** $E_{\text{crit}} \equiv \max(E_{\text{step}}, E_{\text{notional}}, E_{\text{margin}})$.

---

## 14. Canonical Failure Semantics
- Equity below threshold $\implies$ `Record(AllocationRejection::InsufficientAvailableBalance)` or `QuantityRoundsToZero`.

---

## 15. Dependency Map
```text
[#178: Lineage DAG] + [#179: Independent Simulator]
                 │
                 ▼
    [Capital Viability Sweep] ──► capital_viability_surface.parquet / path_to_ruin.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If tiered leverage bracket changes the maintenance margin during position scaling, apply tiered schedule strictly.
