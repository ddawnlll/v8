# Issue #210 (KZ-011 / VERIFY-001): End-to-End Campaign Verification & 05-Feb Mega Attack Reproduction

## 1. Context & Normative Traceability
- **R1:** Replay the complete 12-month tape and specifically the 05–06 Feb 2026 BTC episode (Bars 5250–5310).
- **R2:** Verify that the 191 candidate signals execute as a single unified `BTC_CAMPAIGN` without lot rounding lockout.
- **R3:** Prove Tail Capture Efficiency $TCE \ge 0.65$ on the 62.8K $\to$ 70.5K rebound and positive net monetary returns across the tape.
- **R4:** Generate bit-exact Kaizen snapshot `CAMPAIGN_RED_APPLE_FINAL` with full SHA-256 fingerprint receipts.
- **Traceability:** D-112, D-113, D-123, D-124, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`.

## 2. Reused Types & Existing Contracts
- All unified pipeline contracts (`v8-core/src/runloop.rs`, `v8-core/src/simulator.rs`, `v8-core/src/allocator.rs`).

## 3. Mathematical & Semantic Invariants
- **I1:** 100% deterministic bit-exact replay verified across independent runs.
- **I2:** Total admitted trades in 05-Feb episode $> 0$ with $RealizedPnL > 0$.
- **I3:** Outputs must emit `campaign_final_alpha_receipt.json` and update `PILOT_TRACKING_RECORD.md`.

## 4. Canonical Failure Semantics
- Any non-deterministic hash mismatch or uncertified statistical claim aborts verification (fail closed).

## 5. Dependency & Composition Topology
- Predecessors: Issue #205, #206, #207, #208, #209.
- Successors: None (Milestone Completion Gate).
