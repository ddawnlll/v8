# Issue (KZ-015 / GOV-001): Alpha-Before-Sizing, No-Hard-Router & Anti-Pruning Governance Guardrails

## 1. Context & Normative Traceability
- **R1:** Enforce the "Alpha-Before-Sizing" invariant: forbid Kelly leverage scaling or dynamic sizing on uncertified signals (p-value uncorrected / zero gross edge).
- **R2:** Enforce the "No-Hard-Router" invariant: prohibit hard binary gating of breakout experts based on delayed regime indicators; require soft Bayesian context weighting.
- **R3:** Enforce the "Anti-Pruning" invariant: forbid silent deletion or filtering of experts based on in-sample DEV PnL (prevents selection bias).
- **Traceability:** D-025, D-043, D-044, D-123; arXiv:2402.05272, arXiv:2608.01494.

## 2. Reused Types & Existing Contracts
- `v8_core::evaluation::MultipleTestingCorrection`, `v8_core::allocator::RiskBudget`.

## 3. Mathematical & Semantic Invariants
- **I1:** Fractional Kelly $f^* \le 0.25$ and only enabled when Holm-Bonferroni certified $p \le 0.05$.
- **I2:** All 28 registered sensors remain active and evaluable; pruning allowed only on structural data absence (`DATA_BLOCKED`).
- **I3:** Outputs must emit `governance_guardrail_receipt.json`.

## 4. Canonical Failure Semantics
- Any attempt to apply aggressive sizing or binary pruning without certification fails closed.

## 5. Dependency & Composition Topology
- Predecessors: Issue #205 (MEGA-001), Issue #209 (ALLOC-001).
- Successors: Issue #210 (VERIFY-001).
