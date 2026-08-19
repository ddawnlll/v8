# [IMPL] Issue #KZ-003: Robustness Surface & Plateau/Cliff Analysis

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `risk:robustness-stability`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §4, `EVALUATION_EVIDENCE_SYSTEM.md` §4 (`robustness/`), arXiv:2603.09219 (AlgoXpert).

---

## 1. Objective
Implement parameter robustness surface analysis and plateau/cliff evaluation (`RobustnessCampaign`, `RobustnessPoint`, `RobustnessVerdict`) in pure Rust, replacing isolated knife-edge parameter optimization with broad neighborhood stability analysis and automated cliff vetoes based on the AlgoXpert framework.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §4 (DEV Robustness Surfaces).
- **Evaluation Evidence Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](file:///Users/hootie/src/v8/docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §4 (`robustness/parameter_surface.parquet`).
- **Robustness Literature:** arXiv:2603.09219 (*AlgoXpert: Finding Parameter Plateaus and Preventing Fragility Cliffs*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- `v8-core` has `evaluation::surfaces` generating cost/exit grids, but lacks a typed plateau vs cliff decision engine.
- A candidate variant that scores a high Sharpe ratio on a narrow parameter spike can currently look superior to a robust variant sitting in a broad, stable performance plateau.

---

## 5. Required End State
1. **Robustness Campaign Evaluation:**
   `RobustnessCampaign` evaluating candidate parameter arrays across continuous neighborhood points.
2. **Plateau Detection:**
   Identifies parameter bands where $\text{Sharpe}(\theta) \ge \alpha \times \text{PeakSharpe}$ ($\alpha = 0.85\text{--}0.90$) across adjacent parameter steps.
3. **Cliff Veto:**
   Assigns `RobustnessVerdict::Cliff` and vetos any candidate whose immediate neighbors exhibit catastrophic performance degradation ($> 30\text{--}50\%$ drop).
4. **Typed Verdicts:**
   `Plateau`, `Cliff`, `NonViable`, `InsufficientN`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/robustness.rs (or evaluation/surfaces.rs extension)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying that a candidate with stable neighbor performance ($\le 15\%$ drop) receives `RobustnessVerdict::Plateau`.
3. Test verifying that a peak with a steep adjacent drop ($> 50\%$) receives `RobustnessVerdict::Cliff`.
4. Test verifying that negative expectancy points receive `RobustnessVerdict::NonViable`.
5. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test logs verifying plateau/cliff detection.
- Parquet schema compatibility receipt for `parameter_surface.parquet`.

---

## 9. Non-Goals / Forbidden Scope
- Does not hardcode paper-specific constants as universal laws; parameters are configured via `RobustnessCampaign`.
- Does not run multi-thousand variant adaptive sweeps without trial debt accounting.

---

## 10. Guards
- [ ] Fragile parameter spikes must be vetoed (`Cliff`).
- [ ] Minimum trade count per point must be enforced (`InsufficientN`).
- [ ] No unbounded parameter searching.

---

## 11. Normative Traceability
- **R1 — Continuous Surface Evaluation:** Ingests neighborhood parameter evaluation points.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §4; `EVALUATION_EVIDENCE_SYSTEM.md` §4.
- **R2 — Plateau Selection Rule:** Selects regions meeting the fractional peak Sharpe criterion.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §4; arXiv:2603.09219.
- **R3 — Cliff Veto Rule:** Rejects knife-edge optimums with neighbor drop exceeding threshold.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §4; arXiv:2603.09219.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::kaizen::hypothesis::ChallengerFamilySpec`
- `v8-core::evaluation::surfaces`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Plateau Continuity:** $\text{Plateau}(\theta) \implies \forall \theta' \in \mathcal{N}(\theta), \text{NetExpectancy}(\theta') > 0 \land \text{Sharpe}(\theta') \ge \alpha \times \text{Peak}$.
- **I2 — Cliff Veto:** $\exists \theta' \in \mathcal{N}(\theta) \text{ s.t. } \frac{\text{Sharpe}(\theta) - \text{Sharpe}(\theta')}{\text{Sharpe}(\theta)} > \delta_{\max} \implies \text{Cliff}$.

---

## 14. Canonical Failure Semantics
- Point with $N < N_{\min} \implies \text{RobustnessVerdict::InsufficientN}$.
- Point with negative net return $\implies \text{RobustnessVerdict::NonViable}$.

---

## 15. Dependency Map
```text
[KZ-002: Hypothesis & Challenger]
             │
             ▼
[KZ-003: Robustness Surface]
             │
             ▼
[KZ-004: Purged WFA & OOS Gate]
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If neighbor distance metric is ambiguous for non-numeric parameters, open `OPEN_PIN`.
