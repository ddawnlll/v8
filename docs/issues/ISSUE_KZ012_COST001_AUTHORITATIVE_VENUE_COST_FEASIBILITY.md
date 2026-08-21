# Issue #219 (KZ-012 / COST-001): Authoritative Venue Cost, Slippage & Excess Cost Feasibility

**Status:** RESOLVED & RATIFIED (D-123)

## 1. Context & Normative Traceability
- **R1:** Eliminate hardcoded cost constants; compute authoritative transaction cost from venue tier schedules in basis points (bps) plus observed fill-vs-mid slippage distributions.
- **R2:** Convert basis-point friction to setup-specific R-multiples using the candidate's declared risk unit ($Cost_R = Cost_{bps} \times EntryPrice / RiskUnit$).
- **R3:** Enforce the RM-11 Economic Feasibility Gate: emit $FEASIBILITY\_VETO$ when $ExpectedEdge_{after\_cost} \le 0$ or when breakeven win rate strictly exceeds empirical capability.
- **Traceability:** D-062, D-063, D-111, `VENUE_AND_CAPITAL_SIMULATION_SPEC` §3–5; arXiv:1705.00109 (Boyd Multi-Period Trading).

## 2. Reused Types & Existing Contracts
- `v8_core::venue::VenueContract`, `v8_core::usdm_sim::MakerModel`, `v8_core::types::RoundTripCost`.

## 3. Mathematical & Semantic Invariants
- **I1:** Realized net utility must strictly account for maker/taker fee tiers and adverse fill markouts.
- **I2:** Zero trades permitted when expected net margin is strictly dominated by round-trip transaction costs.
- **I3:** Outputs must emit `authoritative_cost_surface.parquet` and `excess_cost_feasibility.json`.

## 4. Canonical Failure Semantics
- If fee schedule is unknown or uncertified, fallback to highest taker fee tier (15 bps) converted dynamically to setup R units (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: #216 (CAP-001).
- Successors: #218 (VERIFY-001).
