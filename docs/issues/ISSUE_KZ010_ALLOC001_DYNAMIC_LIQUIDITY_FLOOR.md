# Issue #217 (KZ-010 / ALLOC-001): Boyd Dynamic Liquidity Floor & Elastic Capital Router

**Status:** RESOLVED & RATIFIED (D-123)

## 1. Context & Normative Traceability
- **R1:** Implement $CashFloor_t = \max(VenueFloor_t, MarginStress_t, NextTradeFloor_t, FeeFundingBuffer_t)$ in `v8-core/src/allocator.rs`.
- **R2:** Dynamically modulate deployable equity ($DeployableEquity_t = Equity_t - CashFloor_t$) based on portfolio state and campaign evidence.
- **R3:** Reject static 80% cash lockup dogma; verify that cash reserve is an emergent optimization outcome rather than an arbitrary input constant.
- **Traceability:** D-110, D-123, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md`; arXiv:1603.06183, arXiv:1705.00109.

## 2. Reused Types & Existing Contracts
- `v8_core::portfolio::PortfolioState`, `v8_core::account::AccountState`, `v8_core::allocator::RiskBudget`.

## 3. Mathematical & Semantic Invariants
- **I1:** $CashFloor_t \ge 0.0$ and $DeployableEquity_t \le Equity_t$.
- **I2:** Margin stress multiplier must prevent catastrophic liquidation under 3$\sigma$ adverse moves.
- **I3:** Outputs must emit `dynamic_liquidity_surface.parquet` and `deployable_equity_ledger.jsonl`.

## 4. Canonical Failure Semantics
- If wallet equity falls below physical venue maintenance margin, freeze all new entries (fail safe).

## 5. Dependency & Composition Topology
- Predecessors: #215 (CAMP-001), #216 (CAP-001).
- Successors: #221 (PORT-001), #222 (GOV-001), #218 (VERIFY-001).
