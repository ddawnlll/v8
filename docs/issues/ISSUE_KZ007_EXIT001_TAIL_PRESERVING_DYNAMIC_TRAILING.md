# Issue #206 (KZ-007 / EXIT-001): Tail-Preserving Dynamic Trailing Exit Challenger

## 1. Context & Normative Traceability
- **R1:** Freeze the candidate entry set across all evaluation horizons (zero entry mutations).
- **R2:** Evaluate competing exit challenger arms: `[Static_1R, Static_2R, Static_3R, No_TP, Chandelier_ATR, EMA_4h_Trail, Hybrid_Trail]`.
- **R3:** Quantify Tail Capture Efficiency (TCE = $\sum RealizedMove / \sum MFE$) and maximum giveback on 05–06 Feb 2026 BTC moves.
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
- Predecessors: Issue #205 (MEGA-001).
- Successors: Issue #210 (VERIFY-001).
