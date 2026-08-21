# Issue #216 (KZ-009 / CAP-001): Quantization-Aware Risk Budgeting & Micro-Lot Feasibility

**Status:** RESOLVED & RATIFIED (D-123, D-126)

## 1. Context & Normative Traceability
- **R1:** Ingest exchange venue lot discretization rules (`step_size`, `min_qty`, `min_notional`) as direct allocator inputs.
- **R2:** Calculate $MinimumExecutableRisk_{USDT} = StepSize \times |Entry - Stop| + Costs$.
- **R3:** Distinguish legitimate risk-protection rejections from avoidable quantization losses. Minimize avoidable opportunity loss ($ExecutableOpportunityLoss_{rounding} \to 0$) without violating capital preservation bounds.
- **Traceability:** D-109, D-110, D-123, `VENUE_AND_CAPITAL_SIMULATION_SPEC` §3, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`.

## 2. Reused Types & Existing Contracts
- `v8_core::venue::VenueContract`, `v8_core::account::AccountState`, `v8_core::usdm_sim::CapitalViabilityRecord`.

## 3. Mathematical & Semantic Invariants
- **I1:** Allocator must never silently round quantity up if resulting risk exceeds $AllowedCampaignRisk$.
- **I2:** Legitimate risk budget rejections are strictly preserved; only false quantization dropouts are eliminated.
- **I3:** Outputs must emit `quantization_feasibility.parquet` and `avoidable_quantization_loss_receipt.json`.

## 4. Canonical Failure Semantics
- If minimum lot risk strictly exceeds maximum allowed account risk budget, emit explicit `EXCEEDS_CAPITAL_RISK_BUDGET` (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: #215 (CAMP-001).
- Successors: #217 (ALLOC-001), #219 (COST-001).
