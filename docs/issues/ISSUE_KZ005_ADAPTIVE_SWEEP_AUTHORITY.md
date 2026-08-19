# [GOV/IMPL] Issue #KZ-005: Adaptive Sweep Authority & Stopped e-BH Gate

**Status:** BLOCKED_BY_O032 / PATCHED  
**Issue Type:** `GOVERNANCE` / `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION`  
**Labels:** `type:governance`, `triage`, `rust`, `methodology`, `risk:multiplicity-authority`  
**Owning Authority:** `KAIZEN_ENGINE_SPEC.md` §6, `OPEN_DECISIONS.md` O-032, arXiv:2502.08539, arXiv:2009.02824, arXiv:2210.01948.

---

## 1. Objective
Formalize the gating authority and fail-closed architecture for multi-variant sweep execution (`SweepMode::FixedSample` vs `SweepMode::AdaptiveSequential`), ensuring that adaptive sequential early-stopping remains strictly `BLOCKED_BY_O032` until anytime-valid stopped e-BH local/global filtration contracts under cross-variant adaptive stopping are mathematically resolved.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/protocols/KAIZEN_ENGINE_SPEC.md`](file:///Users/hootie/src/v8/docs/protocols/KAIZEN_ENGINE_SPEC.md) §6 (Adaptive Sweep Gate).
- **Open Decision:** [`docs/decisions/OPEN_DECISIONS.md`](file:///Users/hootie/src/v8/docs/decisions/OPEN_DECISIONS.md) `O-032` (*Anytime-valid sequential error control for candidate sweeps*).
- **Stopped e-BH Literature:** arXiv:2502.08539 (Wang, Dandapanthula, Ramdas: *On Local and Global Filtration Dependencies in Sequential Multiple Testing with Stopped e-Processes*).
- **Safe Testing Literature:** arXiv:2009.02824 (*e-BH procedure for FDR control under arbitrary dependence*); arXiv:2210.01948 (*Safe Anytime-Valid Inference via Test Martingales*).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION`

---

## 4. Current State
- Adaptive sequential search (e.g. multi-armed bandits, successive halving) offers compute efficiency, and e-BH provides false discovery rate (FDR) control under arbitrary dependence for fixed e-values.
- However, as Wang–Dandapanthula–Ramdas (arXiv:2502.08539) establish: **Shared-tape dependence does not by itself invalidate e-BH. The unresolved issue is whether each local e-process remains valid with respect to the global filtration induced by cross-variant adaptive stopping.**
- `O-032` remains an open decision in the V8 monograph; without a certified non-negative test supermartingale and filtration contract, adaptive stopping cannot guarantee FDR control.

---

## 5. Required End State
1. **Sweep Mode Enum:**
   `SweepMode` offering:
   - `FixedSample`: Pre-declared, finite sample size with full trial debt accounting and post-hoc family-wise error rate / DSR control. (ENABLED).
   - `AdaptiveSequential`: Sequential early-stopping under stopped e-BH. (BLOCKED).
2. **Fail-Closed Enforcement:**
   Any invocation of `SweepMode::AdaptiveSequential` must fail closed with `Err(SweepError::SequentialEvidenceAuthorityMissing)` / `BLOCKED_BY_O032`.
3. **Formal Unblocking Criteria (O-032 Gate):**
   Adaptive sequential sweep may be unlocked ONLY when:
   - Non-negative test supermartingale / e-process construction is proven valid under the financial return null.
   - Global filtration contract across cross-variant adaptive stopping rules is specified.
   - Repeated Monte Carlo simulation confirms empirical $\text{FDR} \le \alpha$ under adaptive stopping.
   - Reference oracle parity is established in Rust.

---

## 6. Expected File / Module Surface
```text
v8-core/src/kaizen/adaptive.rs (or sweep.rs)
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Test verifying that `SweepMode::FixedSample` evaluates with trial debt accounting.
3. Test verifying that `SweepMode::AdaptiveSequential` fails closed with `SweepError::SequentialEvidenceAuthorityMissing`.
4. `.venv/bin/python tools/audit_python_boundary.py` remains green.

---

## 8. Required Evidence Artifacts
- Unit test logs confirming fail-closed error emission on adaptive invocation.
- Formal resolution checklist for O-032.

---

## 9. Non-Goals / Forbidden Scope
- Does not implement uncertified heuristic early-stopping that bypasses FDR control.
- Does not bypass `O-032` requirements.

---

## 10. Guards
- [ ] `AdaptiveSequential` must fail closed until all 7 O-032 criteria are certified.
- [ ] `FixedSample` must register all candidate trials in the global research debt ledger.

---

## 11. Normative Traceability
- **R1 — Sweep Mode Definition:** Defines `FixedSample` vs `AdaptiveSequential`.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §6; `SWEEP_PROTOCOL.md` §1.
- **R2 — Fail-Closed Safety Gate:** Returns typed error on adaptive mode pending O-032 resolution.  
  *Authority:* `KAIZEN_ENGINE_SPEC.md` §6; `OPEN_DECISIONS.md` O-032; arXiv:2502.08539.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::kaizen::research_debt::GlobalTrialLedger`
- `v8-core::statistics::reality_check`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Anytime-Valid Safety:** No adaptive stopping without an approved test supermartingale.
- **I2 — Fail-Closed Default:** $\text{Mode} = \text{AdaptiveSequential} \land \text{Authority} = \text{Uncertified} \implies \text{Err}(\text{BLOCKED\_BY\_O032})$.

---

## 14. Canonical Failure Semantics
- Invocation without certified authority $\implies$ `Err(SweepError::SequentialEvidenceAuthorityMissing)`.

---

## 15. Dependency Map
```text
[O-032 Theoretical Resolution]
              │
              ▼
[KZ-005: Adaptive Sweep Gate] ──► (Currently Fail-Closed)
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If any external component attempts to bypass the fail-closed check, STOP and escalate `OPEN_PIN`.
