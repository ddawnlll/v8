# ACCP Report: AUD_CANCER_001 (BSR)
**Status:** complete | **Generated:** 2026-08-21T22:45:00Z

## Metadata
- Plan ID: `MEGA_001`
- Agent: `v8-audit-agent` (quantitative_auditor)
- Confidence: `high`

## Bug Findings / Scope
### `BG001`: KANSER-01: Lot Quantization Paralysis (QUANTITY_ROUNDS_TO_ZERO)
- **Priority:** `P0` | **Severity:** `critical`
- **Observed:** 32,428 candidates rejected because fixed 0.5% risk on sub-$1000 equity is below 0.001 BTC lot step.
- **Minimal Fix:** Deploy Quantization-Aware Risk Budgeting & Boyd Dynamic Liquidity Floor.

### `BG002`: KANSER-02: Tail Clipping Exit Geometry (Fixed 2R TP)
- **Priority:** `P1` | **Severity:** `high`
- **Observed:** 79% of target exits continued beyond +2R with average post-exit MFE of +4.5R.
- **Minimal Fix:** Implement Tail-Preserving Dynamic Trailing Exit Challenger.

### `BG003`: KANSER-03: Expert Funnel Collapse & Contention Chaos
- **Priority:** `P1` | **Severity:** `high`
- **Observed:** 42,647 triggers led to 14,766 dedup suppressions and only 2 admitted trades.
- **Minimal Fix:** Candidate-to-Campaign Clustering Engine.
