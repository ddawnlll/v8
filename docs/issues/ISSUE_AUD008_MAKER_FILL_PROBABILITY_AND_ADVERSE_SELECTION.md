# [IMPL] Issue #AUD-008: Maker Fill Probability × Adverse Selection Frontier & Markouts (F13, F14, F16, F29)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `execution`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §6–8, arXiv:2502.18625 (P017), arXiv:2409.12721 (P018), arXiv:2603.24137 (P019), arXiv:2608.04373 (P032).

---

## 1. Objective
Implement passive limit order (Maker) simulation incorporating joint fill probability ($P_{\text{fill}}$), queue position dynamics, post-fill adverse selection markouts, and state-dependent transaction cost surfaces in pure Rust (`v8-core/src/usdm_sim/maker_model.rs`), preventing naive fee-substitution and identifying viable passive alpha.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §6 (TCA & Friction), §8 (Order Execution Fidelity).
- **Academic Literature:**
  - `P017` (arXiv:2502.18625): *The Market Maker's Dilemma: Navigating Fill Probability vs. Post-Fill Returns*.
  - `P018` (arXiv:2409.12721): *Market Simulation under Adverse Selection*.
  - `P019` (arXiv:2603.24137): *Bridging the Reality Gap in Limit Order Book Simulation*.
  - `P032` (arXiv:2608.04373): *Public Trader Identity: Adverse Selection and Return Predictability*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` currently applies unconditional Taker fees (VIP0: 0.05% entry + 0.05% exit = 0.10% roundtrip) to all expert signals.
- In 1h/15m timeframes, taker friction consumes otherwise positive gross alpha.
- Simply swapping fees to 0.02% maker without modeling queue position, fill rates, and adverse selection ("winner's curse") is invalid and overestimates passive performance.

---

## 5. Required End State
1. **Maker Fill Probability & Queue Model:**
   - Joint model: $P_{\text{fill}}(\Delta p, \text{volatility}, \text{volume}, \text{queue\_percentile})$.
   - Intrabar touch vs fill resolution. Emits `maker_fill_markout.parquet`.
2. **Post-Fill Markout Distribution:**
   - 1-bar, 5-bar, 10-bar forward post-fill return curves to quantify adverse selection penalty. Emits `markouts.parquet`.
3. **Queue Sensitivity & Cost Surface:**
   - State-dependent transaction cost engine based on volume/volatility stress. Emits `queue_sensitivity.parquet` and `cost_surface.parquet`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/usdm_sim/mod.rs
v8-core/src/usdm_sim/maker_model.rs
v8-core/src/analysis/markouts.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Adverse selection test: verifying that higher fill probability in trending regimes coincides with higher initial adverse markout.
3. Queue sensitivity test: verifying fill rate decreases monotonically with queue depth.
4. Parquet output validation for markout trajectories.

---

## 8. Required Evidence Artifacts
- `maker_fill_markout.parquet`
- `markouts.parquet`
- `queue_sensitivity.parquet`
- `cost_surface.parquet`

---

## 9. Non-Goals / Forbidden Scope
- Does not grant unconditional maker execution authority without sequenced L2/trade tape evidence.
- Does not replace taker baseline in production runs.

---

## 10. Guards
- [ ] No maker profit claim may be made from fee schedule alone without calibrated fill and adverse selection penalties.
- [ ] When L2 queue data is unavailable, passive claims must be flagged as `MODEL_DERIVED`.

---

## 11. Normative Traceability
- **R1 — Joint Fill / Adverse Selection Modeling:** Enforces joint $P_{\text{fill}} \times \text{Markout}$ frontier.  
  *Authority:* `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §8.3; arXiv:2502.18625 §2.
- **R2 — State-Dependent Cost Surfaces:** Frictional stress varies with volatility/spread.  
  *Authority:* arXiv:2507.09196 §3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::venue::VenueContract`
- `v8-core::cashflow::EconomicCashflow`
- `v8-core::quant::BrownianBridgeAmbiguity`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Monotonic Distance Fill:** $\frac{\partial P_{\text{fill}}}{\partial (\text{distance})} \le 0$.
- **I2 — Net Maker Utility:** $\mathbb{E}[U_{\text{maker}}] = P_{\text{fill}} \times (\text{Gross} - \text{Fee}_{\text{maker}} - \text{AdverseMarkout}) - (1 - P_{\text{fill}}) \times \text{OpportunityCost}$.

---

## 14. Canonical Failure Semantics
- Zero fill under adverse movement $\implies$ `Record(FillStatus::UnfilledAdverseMove)`.

---

## 15. Dependency Map
```text
Order Stream + Market Microstructure
                 │
                 ▼
       [Maker Queue Engine] ──► maker_fill_markout.parquet
                 │
                 ▼
     [Post-Fill Markout Audit] ──► markouts.parquet
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If adverse selection exceeds gross signal expectancy in $>80\%$ of passive fills, flag `UNVIABLE_PASSIVE_ALPHA` and notify.
