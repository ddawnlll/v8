# [IMPL] Issue #AUD-007: True Joint 4D Regime Cube & 1h Binned Funding Seasonality (F09, F10, F11)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P1`, `methodology`  
**Owning Authority:** `EVALUATION_EVIDENCE_SYSTEM.md` §2–5 (4D Regime Partitioning), `KAIZEN_ENGINE_SPEC.md` §2, arXiv:2606.31251 (P012), arXiv:2509.11844 (P014), arXiv:2607.09426 (P016).  
**Relationships:** Depends on #178 (Lineage DAG), #180A.

---

## 1. Objective
Replace 1D marginal slice reporting with a fully orthogonal joint conditional 4D regime cube ($\text{Expert} \times \text{Trend} \times \text{Volatility} \times \text{Volume} \times \text{Funding}$), calculate unbiased regime interaction terms with multiplicity adjustments, implement online structural change / drift monitoring, and audit 1h-binned funding clock seasonality in pure Rust (`v8-core/src/evaluation/regime_cube.rs`).

---

## 2. Owning Authority
- **Primary Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §2–5 (4D Regime Partitioning).
- **Kaizen Engine:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](docs/protocols/KAIZEN_ENGINE_SPEC.md) §2.
- **Academic Literature:**
  - `P012` (arXiv:2606.31251): *Regime-Conditional Distributional Comparison of Trading Strategies*.
  - `P014` (arXiv:2509.11844): *ProteuS: Simulating Concept Drift in Financial Markets*.
  - `P016` (arXiv:2607.09426): *The Quarter-Hour Effect: Microstructure Seasonality*.

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The report currently presents 1D marginal slices without orthogonal joint conditioning.
- Audit gates must not bias towards requiring non-zero interaction; $H_0: \beta_{\text{interaction}} = 0$ is a valid empirical outcome.
- On current 1h OHLCV tape, sub-hour $\pm 30$m microstructure seasonality is unresolvable; funding seasonality must be binned to 1h intervals.

---

## 5. Required End State
1. **Joint 4D Regime Cube:**
   - Compute joint cell matrix: $\text{Cell}(e, \text{trend}, \text{vol}, \text{volume}, \text{funding})$.
   - Each cell carries: $N$, $N_{\text{eff}}$, Gross $R$, Net USDT, Win Rate, Profit Factor, Stationary Bootstrap 95% CI.
   - Emits `expert_joint_regime.parquet`.
2. **Unbiased Interaction Modeling:**
   - Compute interaction parameters, standard errors, and multiplicity-corrected p-values emitted to `regime_interactions.json` regardless of sign or significance.
3. **1h Binned Funding Clock Seasonality:**
   - Evaluates 8-hour funding intervals (00:00, 08:00, 16:00 UTC) at 1h resolution.
   - *(Note: Sub-hour microstructure resolution $\pm 15$m is deferred as DATA_BLOCKED until sequenced trade tape is integrated).*
   - Emits `funding_clock.parquet` and `drift_monitor.jsonl`.

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
2. Orthogonality test: verifying all joint 4D cells partition the population completely.
3. Unbiased emission test: interaction statistics and uncertainty intervals are emitted for all cells.
4. Schema validation for `expert_joint_regime.parquet`.

---

## 8. Required Evidence Artifacts
- `expert_joint_regime.parquet`
- `regime_interactions.json`
- `drift_monitor.jsonl`
- `funding_clock.parquet`

---

## 9. Non-Goals / Forbidden Scope
- Does not require interactions to be non-zero to pass the audit gate.
- Does not claim sub-hour microstructure resolution on 1h bar data.

---

## 10. Guards
- [ ] Cells with low effective sample size must be explicitly flagged with `INSUFFICIENT_SUPPORT`.
- [ ] 4D regime cells must strictly use point-in-time features without lookahead.

---

## 11. Normative Traceability
- **R1 — Joint 4D Regime Partitioning:** Replaces marginal slices with joint cube.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §3; arXiv:2606.31251 §2.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::quant::Regime4D`
- `v8-core::kaizen::diagnosis::RegimeForensics`
- `v8-core::evaluation::TradeRow`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Partition Completeness:** $\sum_{\text{cells}} N_{\text{cell}} \equiv N_{\text{total}}$.

---

## 14. Canonical Failure Semantics
- Incomplete cell partition $\implies$ `Err(RegimeError::PartitionMismatch)`.

---

## 15. Dependency Map
```text
[#178: Lineage DAG] + [#180A: PIT Non-Interference]
                 │
                 ▼
     [Joint 4D Regime Engine] ──► expert_joint_regime.parquet / regime_interactions.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If regime classification boundaries shift dynamically between timeframes, STOP and open OPEN_PIN.
