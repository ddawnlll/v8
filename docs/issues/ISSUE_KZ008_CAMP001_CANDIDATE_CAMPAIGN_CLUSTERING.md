# Issue #207 (KZ-008 / CAMP-001): Multi-Sensor Candidate-to-Campaign Aggregation & Clustering

## 1. Context & Normative Traceability
- **R1:** Implement `CampaignCluster` engine in `v8-core/src/candidate.rs` to group concurrent multi-expert triggers under a single latent market event.
- **R2:** Replace destructive dedup suppression with cumulative evidence strength scoring.
- **R3:** Allocate single position exposure per instrument campaign rather than 4x linear risk stacking.
- **Traceability:** D-108, D-123, `CANDIDATE_LIFECYCLE_SPEC` §1.1, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`.

## 2. Reused Types & Existing Contracts
- `v8_core::candidate::CandidateDraft`, `v8_core::candidate::CandidateState`, `v8_core::analysis::VetoRecord`.

## 3. Mathematical & Semantic Invariants
- **I1:** Multiple concurrent sensor activations within window $W$ collapse to 1 execution slot.
- **I2:** Evidence strength $S_{camp} \ge 1.0$, boosting allocation confidence without exceeding maximum heat caps.
- **I3:** Outputs must emit `campaign_evidence_ledger.jsonl` and `cluster_redundancy.json`.

## 4. Canonical Failure Semantics
- Ambiguous multi-directional conflict (LONG + SHORT at same bar) forces evidence neutral state (fail safe).

## 5. Dependency & Composition Topology
- Predecessors: Issue #205 (MEGA-001).
- Successors: Issue #208 (CAP-001), Issue #209 (ALLOC-001).
