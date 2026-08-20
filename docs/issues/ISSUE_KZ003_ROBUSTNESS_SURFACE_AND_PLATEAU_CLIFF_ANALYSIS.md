# [IMPL] Issue #KZ-003: Robustness Surface & Plateau/Cliff Analysis

**Status:** READY / PATCHED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `risk:robustness-stability`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §4, `EVALUATION_EVIDENCE_SYSTEM.md` §4 (`robustness/`), arXiv:2603.09219 (AlgoXpert).

---

## 1. Objective
Implement parameter robustness surface analysis and plateau/cliff evaluation (`RobustnessCampaign`, `PlateauCriterion`, `RobustnessPoint`, `RobustnessVerdict`) across a **finite preregistered lattice of neighborhood points** in pure Rust, replacing single-metric peak optimization with multi-dimensional utility plateau analysis and robust cliff vetoes.

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
- `v8-core` lacks a formal plateau vs cliff decision engine.
- Prior designs hardcoded single-metric Sharpe ratios as an absolute ontology, which fails when evaluating multi-objective Utility Contracts or when peak Sharpe approaches zero ($\frac{\text{Sharpe}_{\text{peak}} - \text{Sharpe}_{\text{neighbor}}}{\text{Sharpe}_{\text{peak}}} \to \infty$).
- Previous descriptions referenced "continuous" neighborhood surfaces, conflicting with discrete, finite preregistration requirements.

---

## 5. Required End State
1. **Utility-Contract Plateau Criterion:**
   ```rust
   pub struct PlateauCriterion {
       pub primary_utility: MetricId, // e.g. "net_expectancy_r" or "economic_utility"
       pub utility_floor: f64,       // e.g. > 0.0 after full costs
       pub secondary_stability_metric: Option<MetricId>, // e.g. "sharpe"
       pub alpha: Option<f64>,       // e.g. >= 0.90 * peak_utility
   }
   ```
2. **Finite Preregistered Lattice:**
   Campaigns operate over a strictly discrete, bounded parameter grid $\mathcal{L} = \{\theta_1, \theta_2, \dots, \theta_k\}$, never unbounded continuous searches.
3. **Robust Relative Drop with Floor Fallback:**
   Relative degradation to neighbors uses an absolute floor fallback $\epsilon_{\text{floor}}$:
   $$\text{RelativeDrop} = \frac{U_{\text{peak}} - U_{\text{neighbor}}}{\max(U_{\text{peak}}, \epsilon_{\text{floor}})}$$
   preventing numeric explosions when $U_{\text{peak}} \approx 0$.
4. **Cliff Veto:**
   Assigns `RobustnessVerdict::Cliff` and vetos candidates whose lattice neighbors collapse catastrophically.
5. **Typed Verdicts:**
   `Plateau`, `Cliff`, `NonViable`, `InsufficientN`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/robustness.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying plateau classification when all criteria in `PlateauCriterion` (utility floor + alpha peak fraction) hold across adjacent lattice points.
3. Test verifying cliff veto when immediate neighbor drops $> \text{threshold}$, utilizing $\epsilon_{\text{floor}}$ when peak is near zero.
4. Test verifying that negative utility lattice points receive `RobustnessVerdict::NonViable`.
5. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test logs verifying finite lattice plateau/cliff detection with $\epsilon_{\text{floor}}$ protection.

---

## 9. Non-Goals / Forbidden Scope
- Does not run unbounded continuous exploration grids.
- Does not treat isolated peak Sharpe as proof of edge without neighborhood stability.

---

## 10. Guards
- [ ] Evaluation must occur on a finite preregistered lattice.
- [ ] Relative drop calculations must use an $\epsilon_{\text{floor}}$ fallback.
- [ ] Plateau criteria must be configurable via `PlateauCriterion` (Utility Contract).

---

## 11. Normative Traceability
- **R1 — Finite Lattice Surface Evaluation:** Evaluates discrete, preregistered parameter grids.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §4; `HYPOTHESIS_LAB_PROTOCOL.md` §2.
- **R2 — Utility-Contract Plateau Rule:** Evaluates multi-dimensional utility floors and stability metrics.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §4; arXiv:2603.09219.
- **R3 — Robust Cliff Veto with Floor Protection:** Detects knife-edge collapses without division-by-zero defects.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §4; arXiv:2603.09219.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::kaizen::hypothesis::ChallengerFamilySpec`
- `v8-core::kaizen::robustness`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Finite Grid:** $|\mathcal{L}| \in [2, K_{\max}]$, strictly indexed.
- **I2 — Cliff Veto:** $\text{RelativeDrop}(\theta, \theta_{\text{neighbor}}) > \delta_{\max} \implies \text{RobustnessVerdict::Cliff}$.

---

## 14. Canonical Failure Semantics
- Point with $N < N_{\min} \implies \text{RobustnessVerdict::InsufficientN}$.
- Point failing utility floor $\implies \text{RobustnessVerdict::NonViable}$.

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
- If parameter distance in high-dimensional lattices requires custom metric tensors, open `OPEN_PIN`.
