# Issue #205 (KZ-006 / MEGA-001): Extreme Move Detection, Lead-Time & Sensor Recall Benchmark

## 1. Context & Normative Traceability
- **R1:** Label all extreme 24h market episodes in the 12-month tape where $|Z_{24h}| \ge 3.0\sigma$ (including 05–06 Feb 2026 crash and rebound).
- **R2:** Audit all 28 registered sensors on pre-move lead-time windows ($T-12h, T-8h, T-4h, T-2h, T-1h$).
- **R3:** Measure Large-Move Recall, Directional Accuracy, and False Alarm Rate per sensor without mutating expert execution paths.
- **Traceability:** D-123, D-124, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`, `TARGET_ORACLE_SPEC.md` §12.

## 2. Reused Types & Existing Contracts
- `v8_core::oracle::OracleCoverageRecord`, `v8_core::candidate::CandidateDraft`, `MarketState`.

## 3. Mathematical & Semantic Invariants
- **I1:** Lead-time audit must strictly use Point-in-Time information available at or before observation clock $t$.
- **I2:** Synthetic excursion offset is forbidden (Constitution Rule 12).
- **I3:** Outputs must emit `mega_move_recall.parquet` and `sensor_lead_time.json` tagged with `NO_ECONOMIC_CLAIM`.

## 4. Canonical Failure Semantics
- If tape lacks price history for a given horizon $h$, return explicit absence `None` (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: None (Foundation for Campaign).
- Successors: Issue #206 (EXIT-001), Issue #207 (CAMP-001).
