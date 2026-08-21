# Issue (KZ-012 / COST-001): Authoritative Venue Cost, Slippage & Excess Cost Feasibility

## 1. Context & Normative Traceability
- **R1:** Eliminate the arbitrary 0.07R / 0.10R default cost assumption; bind authoritative Binance USD-M VIP/Tier maker & taker fee schedules.
- **R2:** Implement quadratic and square-root market impact slippage models ($Slippage \propto \sigma \sqrt{Q / V}$).
- **R3:** Enforce the RM-11 Excess Cost Feasibility Gate ($w_{min} > w_{realized}$ or $Cost_R > 0.125R \implies FEASIBILITY\_VETO$).
- **Traceability:** D-062, D-063, D-111, `VENUE_AND_CAPITAL_SIMULATION_SPEC` §3–5; arXiv:1705.00109 (Boyd Multi-Period Trading).

## 2. Reused Types & Existing Contracts
- `v8_core::venue::VenueContract`, `v8_core::usdm_sim::MakerModel`, `v8_core::types::RoundTripCost`.

## 3. Mathematical & Semantic Invariants
- **I1:** Realized net utility must strictly account for maker/taker fee tiers and adverse fill markouts.
- **I2:** Zero trades permitted when expected net margin is strictly dominated by round-trip transaction costs.
- **I3:** Outputs must emit `authoritative_cost_surface.parquet` and `excess_cost_feasibility.json`.

## 4. Canonical Failure Semantics
- If fee schedule is unknown or uncertified, fallback to highest taker bracket (0.15R) (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: Issue #208 (CAP-001).
- Successors: Issue #210 (VERIFY-001).
