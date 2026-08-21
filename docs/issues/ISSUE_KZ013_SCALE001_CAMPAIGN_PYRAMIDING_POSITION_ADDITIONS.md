# Issue (KZ-013 / SCALE-001): Campaign Pyramiding, Midpoint Stops & Position Additions

## 1. Context & Normative Traceability
- **R1:** Unlock the P2 `pyramid_add_rules` infrastructure in `v8-core/src/simulator.rs` conforming to D-047.
- **R2:** Implement evidence-based position additions: allow second/third tranches only when existing position is in positive MFE ($MFE \ge +1.5R$) and trailing stop is rolled to breakeven or beyond.
- **R3:** Enforce `midpoint_stop` and maximum campaign exposure caps to prevent risk concentration while riding mega trends.
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
- Predecessors: Issue #206 (EXIT-001), Issue #207 (CAMP-001).
- Successors: Issue #210 (VERIFY-001).
