# Issue #218 (KZ-011 / VERIFY-001): End-to-End Campaign Verification & Multi-Window Falsification Gate

**Status:** RESOLVED & RATIFIED (D-123, D-126)

## 1. Context & Normative Traceability
- **R1:** Replay the complete 12-month tape and evaluate the 05–06 Feb 2026 BTC episode (Bars 5250–5310) as an empirical diagnostic case study.
- **R2:** Verify that candidate signals execute as unified campaigns without false quantization dropouts and under authoritative VIP transaction friction.
- **R3:** True Acceptance Proof: Evaluate the integrated pipeline against independent, frozen multi-window OOS partitions to prevent single-event overfitting to 05-Feb.
- **R4:** Generate bit-exact Kaizen snapshot `CAMPAIGN_RED_APPLE_FINAL` with full SHA-256 fingerprint receipts.
- **Traceability:** D-112, D-113, D-123, D-124, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`.

## 2. Reused Types & Existing Contracts
- All unified pipeline contracts (`v8-core/src/runloop.rs`, `v8-core/src/simulator.rs`, `v8-core/src/allocator.rs`).

## 3. Mathematical & Semantic Invariants
- **I1:** 100% deterministic bit-exact replay verified across independent runs.
- **I2:** Realized monetary utility must demonstrate statistical significance across the multi-window holdout.
- **I3:** Outputs must emit `campaign_final_alpha_receipt.json` and update `PILOT_TRACKING_RECORD.md`.

## 4. Canonical Failure Semantics
- Any non-deterministic hash mismatch or uncertified statistical claim aborts verification (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: #213, #214, #215, #216, #217, #219, #220, #221, #222, #223.
- Successors: None (Milestone Gate).
