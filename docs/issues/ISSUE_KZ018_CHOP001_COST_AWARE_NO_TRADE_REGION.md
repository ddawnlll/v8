# Issue #KZ-018: CHOP-001 — Cost-Aware No-Trade Region & Churn Suppression

**Status:** RESOLVED & RATIFIED (D-126)
**Priority:** P0 (Survival / Churn Elimination)  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC` §10, `WORK_ITEM_POLICY.md` v1.2, `v8-core/src/kaizen/chop_suppression.rs`  
**Academic References:** arXiv:2606.00060 (Cost-aware execution thresholds in BTC trading), arXiv:2407.13547 (Optimal No-Trade Regions under Transaction Costs), arXiv:1308.5658 (Optimal Turnover-Friction Trade-off), arXiv:1705.00109 (Boyd Multi-Period Optimization).

---

## 1. Problem Statement & Root Cause

The 12-month BTCUSDT audit revealed catastrophic capital exhaustion ($10,000 \to \$5.88$) driven by **$3,959.82 in fee drag across 2,628 micro-trades** in choppy, non-directional regimes (A08 Whipsaw Hell). The system fired unconstrained setup triggers where expected gross moves were smaller than roundtrip taker fees and slippage, leading to continuous churning.

---

## 2. Production Invariant Contract

A candidate trade or campaign is admitted **IFF**:
$$\text{ExpectedMarginalUtility}_{\text{after\_cost}} > \text{MinimumOpportunityThreshold}$$
$$\text{AND } \text{Campaign is materially different from recent failed campaigns (cooldown active)}$$
$$\text{AND } \text{Expected incremental edge justifies turnover friction.}$$

### Deterministic Baseline Arms (No fitted opaque router)
- **A0:** Current unsuppressed baseline behavior.
- **A1:** Cost-only feasibility gate ($\text{Expected Excursion} \ge 2.5 \times \text{Friction}$).
- **A2:** Episode re-entry cooldown suppression (8-bar lockout after failed campaign in same direction).
- **A3:** Expansion-quality gate (volatility compression release threshold).
- **A4:** A1 + A2.
- **A5:** A1 + A2 + A3 (Full Composite No-Trade Region).

---

## 3. Verification & Reconciliation Plan

1. Execute pure Rust unit and integration tests (`cargo test --manifest-path v8-core/Cargo.toml`).
2. Run on certified real tape `research/tape/btcusdt-1h-12m/tape.jsonl`.
3. Track metrics: Trades/year, Turnover, Total Friction USDT, Net PnL, Profit Factor, Max Drawdown, Mega-Event Recall.
