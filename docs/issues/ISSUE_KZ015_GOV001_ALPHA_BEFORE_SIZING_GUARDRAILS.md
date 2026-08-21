# Issue #222 (KZ-015 / GOV-001): Alpha-Before-Sizing, Context Gating & Anti-Selection-Bias Governance Guardrails

**Status:** RESOLVED & RATIFIED (D-123)

## 1. Context & Normative Traceability
- **R1:** Enforce the "Alpha-Before-Sizing" invariant: forbid Kelly leverage scaling or aggressive sizing on uncertified signals. Require certified multiplicity adjustment (D-044 / D-046) before risk expansion.
- **R2:** Evaluate context routing options (`NO_CONTEXT`, `SOFT_CONTEXT`, `HARD_CONTEXT`) via paired replay without dogmatic assumptions; hard routing requires proof of zero large-move recall degradation.
- **R3:** Enforce the "Anti-Selection-Bias" invariant: forbid silent deletion or pruning of experts based on in-sample DEV PnL. Allow retirement to `RETIRED/FALSIFIED` status only after multi-window OOS negative expectancy and mechanism falsification.
- **Traceability:** D-025, D-043, D-044, D-046, D-123; arXiv:2402.05272, arXiv:2608.01494.

## 2. Reused Types & Existing Contracts
- `v8_core::evaluation::MultipleTestingCorrection`, `v8_core::allocator::RiskBudget`.

## 3. Mathematical & Semantic Invariants
- **I1:** Fractional Kelly $f^* \le 0.25$ and only enabled when certified under registered multiplicity authorities.
- **I2:** All 28 registered sensors evaluate in dev runs; pruning requires explicit multi-OOS falsification receipts.
- **I3:** Outputs must emit `governance_guardrail_receipt.json`.

## 4. Canonical Failure Semantics
- Any attempt to apply uncertified sizing or arbitrary developer pruning fails closed.

## 5. Dependency & Composition Topology
- Predecessors: #213 (MEGA-001), #217 (ALLOC-001).
- Successors: #218 (VERIFY-001).
