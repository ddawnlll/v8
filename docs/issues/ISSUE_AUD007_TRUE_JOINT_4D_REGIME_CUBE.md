# [IMPL] Issue #AUD-007: True Joint 4D Regime Cube & Drift/Seasonality Monitoring (F09, F10, F11)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `methodology`  
**Owning Authority:** `EVALUATION_EVIDENCE_SYSTEM.md` §2–5, `KAIZEN_ENGINE_SPEC.md` §2, arXiv:2606.31251 (P012), arXiv:2509.11844 (P014), arXiv:2607.09426 (P016).

---

## 1. Objective
Replace 1D marginal slice reporting with a fully orthogonal joint conditional 4D regime cube ($\text{Expert} \times \text{Trend} \times \text{Volatility} \times \text{Volume} \times \text{Funding}$), integrate regime interaction terms, online structural change / drift monitoring, and clock-phase funding seasonality in pure Rust (`v8-core/src/evaluation/regime_cube.rs`).

---

## 2. Owning Authority
- **Primary Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §2–5 (4D regime partitioning).
- **Kaizen Engine:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](docs/protocols/KAIZEN_ENGINE_SPEC.md) §2.
- **Academic Literature:**
  - `P012` (arXiv:2606.31251): *Regime-Conditional Distributional Comparison of Trading Strategies* (Joint regime distributions).
  - `P014` (arXiv:2509.11844): *ProteuS: Simulating Concept Drift in Financial Markets* (Structural change benchmarks).
  - `P016` (arXiv:2607.09426): *The Quarter-Hour Effect* (Funding & clock-phase microstructure seasonality).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The evaluation report presents separate 1D marginal slices (`Trend_BearTrend`, `Vol_HighVol`, `Funding_NeutralFunding`), while `Volume` is omitted from headers.
- Marginal slices fail to reveal interactions (e.g. an expert may thrive in Bull + LowVol but fail catastrophically in Bull + ShockVol).
- No online structural change-point tracking or 8-hour funding boundary seasonality analysis exists.

---

## 5. Required End State
1. **Joint 4D Regime Cube Engine:**
   - Compute joint cell matrix: $\text{Cell}(e, \text{trend}, \text{vol}, \text{volume}, \text{funding})$.
   - Each cell carries: $N$, $N_{\text{eff}}$, Gross $R$, Net USDT, Win Rate, Profit Factor, Bootstrap 95% CI.
   - Emits `expert_joint_regime.parquet` and `regime_interactions.json`.
2. **Concept Drift / Change-Point Monitor:**
   - Rolling detector monitoring alpha decay, expectancy half-life, and detection delay.
   - Emits `drift_monitor.jsonl` and `known_break_benchmark.json`.
3. **Funding Clock Seasonality:**
   - Binned analysis around standardized 8h funding settlement timestamps ($t - 30\text{m}$ to $t + 30\text{m}$).
   - Emits `funding_clock.parquet` and `time_of_day.parquet`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/mod.rs
v8-core/src/evaluation/regime_cube.rs
v8-core/src/quant.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Orthogonality test: verifying all non-empty 4D cells sum exactly to the total population.
3. Interaction significance test verifying non-zero cross-terms.
4. Parquet schema validation for `expert_joint_regime.parquet`.

---

## 8. Required Evidence Artifacts
- `expert_joint_regime.parquet`
- `regime_interactions.json`
- `drift_monitor.jsonl`
- `funding_clock.parquet`
- `time_of_day.parquet`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify market feature calculation logic in `quant.rs`.
- Does not dynamically switch trading strategies during backtest runs.

---

## 10. Guards
- [ ] 4D regime cells must use point-in-time state without future window leakage.
- [ ] Cells with $N_{\text{eff}} < 10$ must be flagged as `INSUFFICIENT_SUPPORT`.

---

## 11. Normative Traceability
- **R1 — Joint Regime Partitioning:** Replaces marginal tables with full joint interaction cube.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §3; arXiv:2606.31251 §2.
- **R2 — Drift Monitoring:** Implements online change-point detection.  
  *Authority:* arXiv:2509.11844 §3; arXiv:2607.16106 §2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::quant::Regime4D`
- `v8-core::kaizen::diagnosis::RegimeForensics`
- `v8-core::evaluation::TradeRow`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Partition Completeness:** $\sum_{\text{cells}} N_{\text{cell}} \equiv N_{\text{total}}$.
- **I2 — Effective Sample Bound:** $N_{\text{eff}} \le N_{\text{obs}}$.

---

## 14. Canonical Failure Semantics
- Incomplete cell partition $\implies$ `Err(RegimeError::PartitionMismatch)`.

---

## 15. Dependency Map
```text
Trade Stream + 4D PIT State
             │
             ▼
    [Joint 4D Regime Cube] ──► expert_joint_regime.parquet
             │
             ▼
    [Drift / Clock Monitor] ──► drift_monitor.jsonl / funding_clock.parquet
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If volume classification quantile boundaries are undefined in higher intervals, open OPEN_PIN.
