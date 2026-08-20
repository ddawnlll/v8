# [RESEARCH] Issue #AUD-009B: Scenario-Based Capital Ruin & Slippage-at-Risk (F17, F18)

**Status:** READY / PROPOSED  
**Issue Type:** `RESEARCH`  
**Change Class:** `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:research`, `triage`, `rust`, `P1`, `risk`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §10, arXiv:2608.01494 (P025), arXiv:2603.09164 (P021).  
**Relationships:** Depends on #185 (AUD-009A); SaR blocked on L2 order book depth.

---

## 1. Objective
Investigate bootstrap/scenario-based capital ruin distributions and evaluate the Slippage-at-Risk (SaR) liquidity tail risk framework in pure Rust (`v8-core/src/usdm_sim/scenario_ruin.rs`), separating identified historical path ruin from stochastic recovery probability.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §10 (Capital Dynamics & Collateral Risk).
- **Academic Literature:**
  - `P025` (arXiv:2608.01494): *Conformal Kelly in Fractional Sizing*.
  - `P021` (arXiv:2603.09164): *Slippage-at-Risk (SaR): A Forward-Looking Liquidity Risk Framework*.

---

## 3. Change Class
`NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- A single deterministic historical path cannot yield a true "probability of ruin" without resampling or scenario perturbation.
- Slippage-at-Risk (SaR) tail diagnostics require order book depth data; on 1h OHLCV tape, SaR is restricted to synthetic stress modeling.

---

## 5. Required End State
1. **Resampling-Based Ruin Distribution:**
   - Execute 1,000 stationary block bootstrap resamples of the trade sequence across varying initial capital levels.
   - Estimate empirical $\hat{\mathbb{P}}(\text{Ruin} \mid E_0)$ and expected time-to-ruin confidence intervals.
2. **Slippage-at-Risk Stress Engine:**
   - Compute $95\%$ and $99\%$ tail slippage under forced liquidation cascades (tagged `MODEL_DERIVED`).
3. **Artifact Generation:**
   - Emits `scenario_ruin_distribution.parquet` and `slippage_at_risk.json`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/usdm_sim/scenario_ruin.rs
v8-core/src/usdm_sim/mod.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Bootstrap ruin estimator verifies monotonicity against capital scaling.
3. All SaR outputs on bar data are explicitly tagged `MODEL_DERIVED`.

---

## 8. Required Evidence Artifacts
- `scenario_ruin_distribution.parquet`
- `slippage_at_risk.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not claim empirical liquidity tail truth without full L2 depth data.

---

## 10. Guards
- [ ] Bootstrap ruin distributions must not be conflated with the single observed historical backtest path.

---

## 11. Normative Traceability
- **R1 — Scenario Ruin Analysis:** Resampling-based ruin quantification.  
  *Authority:* `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §10; arXiv:2608.01494 §3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::statistics::reality_check::select_block_size`
- `v8-core::account::AccountState`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Stochastic Ruin Bound:** $\mathbb{P}(\text{Ruin} \mid E_1) \le \mathbb{P}(\text{Ruin} \mid E_0) \quad \forall E_1 > E_0$.

---

## 14. Canonical Failure Semantics
- Insufficient bootstrap samples $\implies$ `Record(RuinEstimationStatus::InsufficientBootstrapReplications)`.

---

## 15. Dependency Map
```text
[#185: AUD-009A Capital Viability]
                 │
                 ▼
   [Scenario Ruin Engine] ──► scenario_ruin_distribution.parquet / slippage_at_risk.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If trade sequence dependence violates block bootstrap stationarity assumptions, notify and open OPEN_PIN.
