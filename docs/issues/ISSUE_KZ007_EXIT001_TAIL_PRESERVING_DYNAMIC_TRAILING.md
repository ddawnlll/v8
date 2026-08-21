# Issue #214 (KZ-007 / EXIT-001): Tail-Preserving Dynamic Trailing Exit Challenger

**Status:** RESOLVED & RATIFIED (D-123, D-126)

## 1. Context & Normative Traceability
- **R1:** Freeze candidate entry set across all evaluation horizons (zero entry mutations).
- **R2:** Establish the historical 1R take-profit as the comparative baseline (responsible for clipping favorable right-tail excursion).
- **R3:** Evaluate competing exit challenger arms: `[Static_1R (Baseline), Static_2R, Static_3R, No_TP, Chandelier_ATR, EMA_4h_Trail, Hybrid_Trail]`.
- **R4:** Quantify Tail Capture Efficiency ($TCE = \sum RealizedMove / \sum MFE$) and maximum giveback across multi-event historical episodes.
- **Traceability:** D-047, D-123, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`, `VENUE_AND_CAPITAL_SIMULATION_SPEC` §9.

## 2. Reused Types & Existing Contracts
- `v8_core::simulator::OpenPosition`, `v8_core::simulator::StepResult`, `v8_core::types::RiskGeometry`.

## 3. Mathematical & Semantic Invariants
- **I1:** $TCE \in [0.0, 1.0]$.
- **I2:** Exit decision must evaluate strictly on bar close or within-bar tick crossing without lookahead.
- **I3:** Outputs must emit `tail_capture_efficiency.parquet` and `exit_challenger_comparison.json`.

## 4. Canonical Failure Semantics
- If trailing stop level is invalid or non-positive, fallback to structural initial stop (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: #213 (MEGA-001).
- Successors: #220 (SCALE-001), #218 (VERIFY-001).
