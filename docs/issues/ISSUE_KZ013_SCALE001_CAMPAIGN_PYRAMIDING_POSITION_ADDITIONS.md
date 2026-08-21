# Issue #220 (KZ-013 / SCALE-001): Campaign Pyramiding, Midpoint Stops & Position Additions

**Status:** RESOLVED & RATIFIED (D-123)

## 1. Context & Normative Traceability
- **R1:** Unlock the P2 `pyramid_add_rules` infrastructure in `v8-core/src/simulator.rs` conforming to D-047.
- **R2:** Implement evidence-based position additions: evaluate registered confirmation threshold arms ($\tau_{add} \in \{0.5R, 1.0R, 1.5R\}$) conditioned on positive running excursion ($MFE > 0$) and advance of stop level to breakeven or beyond.
- **R3:** Enforce strict anti-martingale invariant: adding to losing or invalidated positions is strictly forbidden.
- **R4:** Apply `midpoint_stop` and maximum campaign heat caps to prevent risk concentration while riding mega trends.
- **Traceability:** D-047, D-123, `CANDIDATE_LIFECYCLE_SPEC` §4, `docs/contracts/SIMULATION_TRUTH_SPEC.md` §3.

## 2. Reused Types & Existing Contracts
- `v8_core::simulator::OpenPosition`, `v8_core::simulator::PositionAction`, `v8_core::types::PyramidRule`.

## 3. Mathematical & Semantic Invariants
- **I1:** Total campaign risk after addition must never exceed initial trade unit risk ($Heat_{total} \le Heat_{initial}$ after breakeven stop roll).
- **I2:** Pyramiding is forbidden on losing or unconfirmed positions (anti-martingale invariant).
- **I3:** Outputs must emit `pyramid_campaign_ledger.jsonl` and `pyramid_attribution.parquet`.

## 4. Canonical Failure Semantics
- If position is not strictly in positive profit or stop cannot be advanced, reject addition (fail safe).

## 5. Dependency & Composition Topology
- Predecessors: #214 (EXIT-001), #215 (CAMP-001).
- Successors: #218 (VERIFY-001).
